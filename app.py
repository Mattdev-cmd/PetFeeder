# ── AI Chatbox Endpoint ─────────────────────────────────────────────
from ai_engine import openrouter_chat
"""
Automatic Pet Feeder Dashboard — Flask Application
Runs on Raspberry Pi 3 with servo motor and ultrasonic sensor.
"""

import atexit
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, redirect, url_for, request, jsonify, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from config import Config
from models import db, User, Pet, PetStatus, FeedingSchedule, FeedingLog
from ai_engine import get_feeding_suggestion, get_next_feeding_time, format_time_12h, extract_portion_multiplier
from hardware import feeder

# ── App setup ────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# ── AI Chatbox Endpoint ─────────────────────────────────────────────
@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    history = data.get("history", [])
    if not message:
        return jsonify({"error": "No message provided."}), 400
    reply = openrouter_chat(message, history)
    return jsonify({"reply": reply})

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ── Scheduler for automatic feeding ─────────────────────────────────────────

scheduler = BackgroundScheduler(daemon=True)


def check_and_feed():
    """Run every minute — check if any scheduled feeding is due."""
    with app.app_context():
        now = feeder.get_rtc_time()
        # Allow a ±1 minute window for matching scheduled times
        current_minutes = now.hour * 60 + now.minute
        window = [f"{((current_minutes + offset) // 60) % 24:02d}:{((current_minutes + offset) % 60):02d}" for offset in (-1, 0, 1)]
        schedules = FeedingSchedule.query.filter(FeedingSchedule.feed_time.in_(window), FeedingSchedule.is_active == True).all()
        for sched in schedules:
            feeder.dispense_food(sched.portion_size)
            log = FeedingLog(
                pet_id=sched.pet_id,
                feed_type="Scheduled",
                portion_size=sched.portion_size,
            )
            db.session.add(log)
            logger.info(f"Scheduled feeding for pet {sched.pet_id} at {sched.feed_time}")
        if schedules:
            db.session.commit()


scheduler.add_job(check_and_feed, "interval", minutes=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())
atexit.register(lambda: feeder.cleanup())


# ── Auth routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists.", "error")
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ── Dashboard ────────────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    pet = Pet.query.filter_by(user_id=current_user.id).first()
    if not pet:
        return redirect(url_for("add_pet"))

    schedules = FeedingSchedule.query.filter_by(pet_id=pet.id, is_active=True).all()
    logs = FeedingLog.query.filter_by(pet_id=pet.id).order_by(FeedingLog.fed_at.desc()).limit(10).all()
    active_statuses = PetStatus.query.filter_by(pet_id=pet.id, is_active=True).all()

    # AI suggestions
    ai = get_feeding_suggestion(pet, active_statuses, logs, schedules)

    # Next feeding
    next_time_24 = get_next_feeding_time(schedules)
    next_time_display = format_time_12h(next_time_24)

    # Food level
    food_level = feeder.get_food_level()
    food_label = feeder.get_food_level_label(food_level)

    # Current schedule for the form
    current_schedule = schedules[0] if schedules else None

    return render_template(
        "dashboard.html",
        user=current_user,
        pet=pet,
        schedules=schedules,
        logs=logs,
        active_statuses=active_statuses,
        ai=ai,
        next_time=next_time_display,
        next_time_raw=next_time_24 or "",
        food_level=food_level,
        food_label=food_label,
        current_schedule=current_schedule,
        format_time_12h=format_time_12h,
    )


# ── Pet management ───────────────────────────────────────────────────────────

@app.route("/add-pet", methods=["GET", "POST"])
@login_required
def add_pet():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        species = request.form.get("species", "Dog").strip()
        if species == "Other":
            custom_species = request.form.get("custom_species", "").strip()
            if custom_species:
                species = custom_species
        breed = request.form.get("breed", "").strip()
        age_years = int(request.form.get("age_years", 0) or 0)
        age_months = int(request.form.get("age_months", 0) or 0)
        total_months = age_years * 12 + age_months
        weight = float(request.form.get("weight", 0) or 0)
        photo_url = request.form.get("photo_url", "").strip()

        if not name:
            flash("Pet name is required.", "error")
        else:
            pet = Pet(
                user_id=current_user.id,
                name=name,
                species=species,
                breed=breed,
                age=total_months,
                weight_kg=weight,
                photo_url=photo_url,
            )
            db.session.add(pet)
            db.session.commit()
            flash(f"{name} has been added!", "success")
            return redirect(url_for("dashboard"))
    return render_template("add_pet.html")


@app.route("/edit-pet", methods=["POST"])
@login_required
def edit_pet():
    pet = Pet.query.filter_by(user_id=current_user.id).first()
    if not pet:
        return redirect(url_for("add_pet"))

    pet.name = request.form.get("name", pet.name).strip()
    pet.species = request.form.get("species", pet.species).strip()
    pet.breed = request.form.get("breed", pet.breed).strip()
    age_years = int(request.form.get("age_years", pet.age // 12))
    age_months = int(request.form.get("age_months", pet.age % 12))
    pet.age = age_years * 12 + age_months
    pet.weight_kg = float(request.form.get("weight", pet.weight_kg) or pet.weight_kg)
    pet.photo_url = request.form.get("photo_url", pet.photo_url).strip()
    db.session.commit()
    flash("Pet details updated.", "success")
    return redirect(url_for("dashboard"))


# ── Pet Status ───────────────────────────────────────────────────────────────

@app.route("/api/pet-status", methods=["POST"])
@login_required
def add_pet_status():
    pet = Pet.query.filter_by(user_id=current_user.id).first()
    if not pet:
        return jsonify({"error": "No pet found"}), 404

    data = request.get_json()
    status_type = data.get("status_type", "").strip()
    description = data.get("description", "").strip()
    severity = int(data.get("severity", 1))

    if status_type not in (
        "sick", "not_eating", "timid", "vomiting", "lethargic",
        "diarrhea", "overweight", "energetic", "normal"
    ):
        return jsonify({"error": "Invalid status type"}), 400

    severity = max(1, min(5, severity))

    # Deactivate any existing status of same type
    PetStatus.query.filter_by(pet_id=pet.id, status_type=status_type, is_active=True).update(
        {"is_active": False}
    )

    status = PetStatus(
        pet_id=pet.id,
        status_type=status_type,
        description=description,
        severity=severity,
    )
    db.session.add(status)
    db.session.commit()

    # Return updated AI suggestions
    active = PetStatus.query.filter_by(pet_id=pet.id, is_active=True).all()
    logs = FeedingLog.query.filter_by(pet_id=pet.id).order_by(FeedingLog.fed_at.desc()).limit(10).all()
    schedules = FeedingSchedule.query.filter_by(pet_id=pet.id, is_active=True).all()
    ai = get_feeding_suggestion(pet, active, logs, schedules)

    return jsonify({
        "message": "Status recorded",
        "ai_suggestions": ai,
        "active_statuses": [
            {"id": s.id, "type": s.status_type, "severity": s.severity, "description": s.description}
            for s in active
        ],
    })


@app.route("/api/pet-status/<int:status_id>/resolve", methods=["POST"])
@login_required
def resolve_pet_status(status_id):
    pet = Pet.query.filter_by(user_id=current_user.id).first()
    if not pet:
        return jsonify({"error": "No pet found"}), 404

    status = PetStatus.query.filter_by(id=status_id, pet_id=pet.id).first()
    if not status:
        return jsonify({"error": "Status not found"}), 404

    status.is_active = False
    db.session.commit()
    return jsonify({"message": "Status resolved"})


# ── Feeding schedule ─────────────────────────────────────────────────────────

@app.route("/api/schedule", methods=["POST"])
@login_required
def save_schedule():
    pet = Pet.query.filter_by(user_id=current_user.id).first()
    if not pet:
        return jsonify({"error": "No pet found"}), 404

    data = request.get_json()
    feed_time = data.get("feed_time", "").strip()  # expected HH:MM (24h)
    portion = float(data.get("portion_size", 1.0))

    if not feed_time or ":" not in feed_time:
        return jsonify({"error": "Invalid time format"}), 400

    # Validate time
    parts = feed_time.split(":")
    if len(parts) != 2:
        return jsonify({"error": "Invalid time format"}), 400
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return jsonify({"error": "Invalid time range"}), 400

    schedule = FeedingSchedule(
        pet_id=pet.id,
        feed_time=feed_time,
        portion_size=portion,
    )
    db.session.add(schedule)
    db.session.commit()

    return jsonify({
        "message": "Schedule saved",
        "schedule": {
            "id": schedule.id,
            "feed_time": feed_time,
            "display_time": format_time_12h(feed_time),
            "portion_size": portion,
        },
    })


@app.route("/api/schedule/<int:schedule_id>", methods=["DELETE"])
@login_required
def delete_schedule(schedule_id):
    pet = Pet.query.filter_by(user_id=current_user.id).first()
    if not pet:
        return jsonify({"error": "No pet found"}), 404

    sched = FeedingSchedule.query.filter_by(id=schedule_id, pet_id=pet.id).first()
    if not sched:
        return jsonify({"error": "Schedule not found"}), 404

    db.session.delete(sched)
    db.session.commit()
    return jsonify({"message": "Schedule removed"})


# ── Manual feeding ───────────────────────────────────────────────────────────

@app.route("/api/feed-now", methods=["POST"])
@login_required
def feed_now():
    pet = Pet.query.filter_by(user_id=current_user.id).first()
    if not pet:
        return jsonify({"error": "No pet found"}), 404

    success = feeder.dispense_food(1.0)
    if success:
        log = FeedingLog(pet_id=pet.id, feed_type="Manual", portion_size=1.0)
        db.session.add(log)
        db.session.commit()
        return jsonify({
            "message": "Food dispensed!",
            "food_level": feeder.get_food_level(),
            "food_label": feeder.get_food_level_label(feeder.get_food_level()),
        })
    return jsonify({"error": "Failed to dispense food"}), 500


# ── Apply AI Recommendation to Schedule ─────────────────────────────────────

@app.route("/api/apply-ai-recommendation", methods=["POST"])
@login_required
def apply_ai_recommendation():
    """
    Apply the AI feeding suggestion to the pet's feeding schedule.
    Updates all active schedules with the recommended portion multiplier.
    """
    pet = Pet.query.filter_by(user_id=current_user.id).first()
    if not pet:
        return jsonify({"error": "No pet found"}), 404

    # Get current AI suggestions
    active_statuses = PetStatus.query.filter_by(pet_id=pet.id, is_active=True).all()
    logs = FeedingLog.query.filter_by(pet_id=pet.id).order_by(FeedingLog.fed_at.desc()).limit(10).all()
    schedules = FeedingSchedule.query.filter_by(pet_id=pet.id, is_active=True).all()
    
    ai_suggestions = get_feeding_suggestion(pet, active_statuses, logs, schedules)
    
    # Extract the portion multiplier from AI recommendation
    multiplier = extract_portion_multiplier(pet, ai_suggestions)
    
    if multiplier is None:
        return jsonify({
            "error": "Could not extract portion recommendation from AI suggestions",
            "portion_advice": ai_suggestions.get("portion_advice", "")
        }), 400
    
    # Update all active schedules with the new multiplier
    updated_count = 0
    for schedule in schedules:
        if schedule.is_active:
            schedule.portion_size = multiplier
            updated_count += 1
    
    if updated_count == 0:
        return jsonify({
            "error": "No active feeding schedules found. Create a schedule first.",
            "multiplier": multiplier
        }), 400
    
    db.session.commit()
    
    logger.info(f"Applied AI recommendation: portion multiplier {multiplier} to {updated_count} schedule(s) for pet {pet.id}")
    
    return jsonify({
        "message": f"Applied AI recommendation to {updated_count} feeding schedule(s)",
        "multiplier": multiplier,
        "schedules": [
            {
                "id": s.id,
                "feed_time": s.feed_time,
                "display_time": format_time_12h(s.feed_time),
                "portion_size": s.portion_size
            }
            for s in schedules
        ]
    })


# ── Food level endpoint ─────────────────────────────────────────────────────

@app.route("/api/food-level")
@login_required
def food_level():
    level = feeder.get_food_level()
    return jsonify({
        "level": level,
        "label": feeder.get_food_level_label(level),
    })


# ── Feeding logs ─────────────────────────────────────────────────────────────

@app.route("/api/feeding-logs")
@login_required
def feeding_logs():
    pet = Pet.query.filter_by(user_id=current_user.id).first()
    if not pet:
        return jsonify({"error": "No pet found"}), 404

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    per_page = min(per_page, 100)

    pagination = FeedingLog.query.filter_by(pet_id=pet.id)\
        .order_by(FeedingLog.fed_at.desc())\
        .paginate(page=page, per_page=per_page)

    return jsonify({
        "logs": [
            {
                "id": log.id,
                "type": log.feed_type,
                "portion": log.portion_size,
                "time": log.fed_at.strftime("%b %d, %I:%M %p") if log.fed_at else "",
                "notes": log.notes,
            }
            for log in pagination.items
        ],
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages,
    })


# ── AI suggestions endpoint ─────────────────────────────────────────────────

@app.route("/api/ai-suggestions")
@login_required
def ai_suggestions():
    pet = Pet.query.filter_by(user_id=current_user.id).first()
    if not pet:
        return jsonify({"error": "No pet found"}), 404

    active = PetStatus.query.filter_by(pet_id=pet.id, is_active=True).all()
    logs = FeedingLog.query.filter_by(pet_id=pet.id).order_by(FeedingLog.fed_at.desc()).limit(10).all()
    schedules = FeedingSchedule.query.filter_by(pet_id=pet.id, is_active=True).all()
    ai = get_feeding_suggestion(pet, active, logs, schedules)
    return jsonify(ai)


# ── Initialize DB ────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
