from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    pets = db.relationship("Pet", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Pet(db.Model):
    __tablename__ = "pets"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    species = db.Column(db.String(50), default="Dog")  # Dog, Cat, etc.
    breed = db.Column(db.String(100), default="")
    age = db.Column(db.Integer, default=1)
    weight_kg = db.Column(db.Float, default=0.0)
    photo_url = db.Column(db.String(300), default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    statuses = db.relationship("PetStatus", backref="pet", lazy=True, cascade="all, delete-orphan")
    feeding_logs = db.relationship("FeedingLog", backref="pet", lazy=True, cascade="all, delete-orphan")
    schedules = db.relationship("FeedingSchedule", backref="pet", lazy=True, cascade="all, delete-orphan")


class PetStatus(db.Model):
    """Track pet health and behavior status over time."""
    __tablename__ = "pet_statuses"
    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey("pets.id"), nullable=False)
    status_type = db.Column(db.String(50), nullable=False)  # sick, timid, not_eating, energetic, normal, etc.
    description = db.Column(db.Text, default="")
    severity = db.Column(db.Integer, default=1)  # 1-5 scale
    recorded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)


class FeedingSchedule(db.Model):
    __tablename__ = "feeding_schedules"
    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey("pets.id"), nullable=False)
    feed_time = db.Column(db.String(10), nullable=False)  # HH:MM format (24h)
    is_active = db.Column(db.Boolean, default=True)
    portion_size = db.Column(db.Float, default=1.0)  # multiplier
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class FeedingLog(db.Model):
    __tablename__ = "feeding_logs"
    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey("pets.id"), nullable=False)
    feed_type = db.Column(db.String(20), nullable=False)  # "Scheduled" or "Manual"
    portion_size = db.Column(db.Float, default=1.0)
    fed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    notes = db.Column(db.Text, default="")
