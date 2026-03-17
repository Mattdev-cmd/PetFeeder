"""
AI Engine for Pet Feeder — Chatbot integration with OpenRouter and feeding pattern analysis.
Requires: https://openrouter.ai/ API key
"""

import requests
from config import Config

def openrouter_chat(message, history=None, model="gpt-3.5-turbo"):
    """
    Send a message to OpenRouter AI and return the response.
    Args:
        message (str): The user's message.
        history (list): Optional list of previous messages for context.
        model (str): OpenRouter model name (default: gpt-3.5-turbo)
    Returns:
        str: OpenRouter's reply or error message.
    """
    api_key = Config.OPENROUTER_API_KEY
    if not api_key or api_key == "YOUR_OPENROUTER_API_KEY_HERE":
        return "[OpenRouter API key not set. Get one at https://openrouter.ai/]"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    messages = []
    if history:
        for i, msg in enumerate(history):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": msg})
    messages.append({"role": "user", "content": message})
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[OpenRouter API error: {e}]"


from datetime import datetime, timedelta, timezone


# ── Status-based feeding rules ──────────────────────────────────────────────

STATUS_FEEDING_ADJUSTMENTS = {
    "sick": {
        "portion_modifier": 0.7,
        "frequency_note": "Feed smaller portions more frequently when sick.",
        "vet_urgency": 3,
    },
    "not_eating": {
        "portion_modifier": 0.5,
        "frequency_note": "Pet is not eating well. Try smaller portions and monitor closely.",
        "vet_urgency": 4,
    },
    "timid": {
        "portion_modifier": 0.9,
        "frequency_note": "Pet seems anxious. Feed in a calm, quiet environment.",
        "vet_urgency": 1,
    },
    "vomiting": {
        "portion_modifier": 0.5,
        "frequency_note": "Withhold food for 12 hours, then offer bland diet in small amounts.",
        "vet_urgency": 4,
    },
    "lethargic": {
        "portion_modifier": 0.8,
        "frequency_note": "Reduced energy detected. Monitor food intake carefully.",
        "vet_urgency": 3,
    },
    "diarrhea": {
        "portion_modifier": 0.6,
        "frequency_note": "Provide bland, easily digestible food in small portions.",
        "vet_urgency": 3,
    },
    "overweight": {
        "portion_modifier": 0.8,
        "frequency_note": "Reduce portions slightly. Consider more exercise.",
        "vet_urgency": 2,
    },
    "energetic": {
        "portion_modifier": 1.1,
        "frequency_note": "Pet is very active. Slightly larger portions may help.",
        "vet_urgency": 0,
    },
    "normal": {
        "portion_modifier": 1.0,
        "frequency_note": "Pet appears healthy. Maintain regular feeding schedule.",
        "vet_urgency": 0,
    },
}

# Species-based daily feeding guidelines (cups per day, by weight range in kg)
SPECIES_GUIDELINES = {
    "Dog": [
        (0, 5, 0.5, 1.0),    # toy breeds
        (5, 10, 1.0, 1.5),
        (10, 25, 1.5, 2.5),
        (25, 45, 2.5, 3.5),
        (45, 100, 3.5, 5.0),
    ],
    "Cat": [
        (0, 3, 0.25, 0.5),
        (3, 5, 0.5, 0.75),
        (5, 8, 0.75, 1.0),
        (8, 15, 1.0, 1.25),
    ],
}


def get_feeding_suggestion(pet, active_statuses, feeding_logs, schedules):
    """
    Generate AI-based feeding suggestions for a pet.

    Returns a dict with:
      - suggested_times: list of recommended feed times
      - portion_advice: text about portion sizes
      - warnings: list of warning strings
      - overall_status: "good" | "caution" | "warning" | "critical"
    """
    suggestions = {
        "suggested_times": [],
        "portion_advice": "",
        "warnings": [],
        "overall_status": "good",
        "vet_recommendation": None,
    }

    # ── Determine portion modifier from current statuses ─────────────
    worst_urgency = 0
    combined_modifier = 1.0
    status_notes = []

    for status in active_statuses:
        info = STATUS_FEEDING_ADJUSTMENTS.get(status.status_type, STATUS_FEEDING_ADJUSTMENTS["normal"])
        combined_modifier = min(combined_modifier, info["portion_modifier"])
        status_notes.append(info["frequency_note"])
        worst_urgency = max(worst_urgency, info["vet_urgency"])

    # ── Species/weight-based baseline ────────────────────────────────
    species = pet.species or "Dog"
    weight = pet.weight_kg or 10.0
    guidelines = SPECIES_GUIDELINES.get(species, SPECIES_GUIDELINES["Dog"])
    base_cups_min, base_cups_max = 1.0, 2.0
    for low, high, cups_min, cups_max in guidelines:
        if low <= weight < high:
            base_cups_min, base_cups_max = cups_min, cups_max
            break

    adjusted_min = round(base_cups_min * combined_modifier, 2)
    adjusted_max = round(base_cups_max * combined_modifier, 2)

    suggestions["portion_advice"] = (
        f"Recommended daily intake: {adjusted_min}–{adjusted_max} cups/day "
        f"(adjusted for current status). Split across feeding times."
    )

    if status_notes:
        suggestions["warnings"] = list(set(status_notes))

    # ── Suggest feeding times ────────────────────────────────────────
    existing_times = [s.feed_time for s in schedules if s.is_active]
    if existing_times:
        suggestions["suggested_times"] = existing_times
    else:
        # Default suggestions based on species and age
        if species == "Cat":
            suggestions["suggested_times"] = ["07:00", "12:00", "18:00"]
        elif pet.age and pet.age < 1:
            suggestions["suggested_times"] = ["07:00", "11:00", "15:00", "19:00"]
        else:
            suggestions["suggested_times"] = ["08:00", "18:00"]

    # ── Analyze feeding pattern ──────────────────────────────────────
    now = datetime.now()
    recent_logs = [log for log in feeding_logs if log.fed_at and log.fed_at.replace(tzinfo=None) >= now - timedelta(days=3)]
    if len(recent_logs) == 0 and len(feeding_logs) > 0:
        suggestions["warnings"].append(
            "No feeding recorded in the last 3 days! Please check on your pet immediately."
        )
        worst_urgency = max(worst_urgency, 5)

    # ── Vet recommendation ───────────────────────────────────────────
    if worst_urgency >= 4:
        suggestions["vet_recommendation"] = (
            "URGENT: Based on your pet's current status, we strongly recommend "
            "visiting a veterinarian as soon as possible."
        )
        suggestions["overall_status"] = "critical"
    elif worst_urgency >= 3:
        suggestions["vet_recommendation"] = (
            "We recommend scheduling a veterinary visit within the next few days "
            "to check on your pet's health."
        )
        suggestions["overall_status"] = "warning"
    elif worst_urgency >= 2:
        suggestions["vet_recommendation"] = (
            "Consider a routine check-up at your next convenience."
        )
        suggestions["overall_status"] = "caution"
    else:
        suggestions["vet_recommendation"] = (
            "Your pet appears healthy! Regular annual check-ups are still recommended."
        )

    return suggestions


def get_next_feeding_time(schedules):
    """Return the next upcoming feeding time as a string, or None."""
    if not schedules:
        return None

    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute
    active = [s for s in schedules if s.is_active]
    if not active:
        return None

    upcoming = []
    for s in active:
        parts = s.feed_time.split(":")
        if len(parts) == 2:
            sched_minutes = int(parts[0]) * 60 + int(parts[1])
            upcoming.append((sched_minutes, s.feed_time))

    upcoming.sort(key=lambda x: x[0])

    # Find next time today
    for mins, time_str in upcoming:
        if mins > current_minutes:
            return time_str

    # Otherwise wrap to first time tomorrow
    if upcoming:
        return upcoming[0][1]

    return None


def format_time_12h(time_24h):
    """Convert '14:00' to '2:00 PM'."""
    if not time_24h:
        return "Not set"
    parts = time_24h.split(":")
    if len(parts) != 2:
        return time_24h
    hour, minute = int(parts[0]), int(parts[1])
    period = "AM" if hour < 12 else "PM"
    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour}:{minute:02d} {period}"


def extract_portion_multiplier(pet, suggestions):
    """
    Extract portion recommendation from AI suggestions and convert to multiplier.
    
    Args:
        pet: Pet object with species and weight
        suggestions: Dict from get_feeding_suggestion()
    
    Returns:
        float: Portion multiplier (1.0 = default portion)
            or None if no recommendation found
    
    Example:
        If recommendation is "1.5–2.0 cups/day" and default is 1.0 portions/day,
        returns 1.75 (average of 1.5 and 2.0)
    """
    import re
    
    portion_text = suggestions.get("portion_advice", "")
    if not portion_text:
        return None
    
    # Extract numbers from text like "1.2–2.0 cups/day"
    numbers = re.findall(r"(\d+\.\d+|\d+)", portion_text)
    if len(numbers) < 2:
        return None
    
    try:
        min_cups = float(numbers[0])
        max_cups = float(numbers[1])
        avg_cups = (min_cups + max_cups) / 2
        
        # Get baseline for this pet's species/weight
        species = pet.species or "Dog"
        weight = pet.weight_kg or 10.0
        
        guidelines = SPECIES_GUIDELINES.get(species, SPECIES_GUIDELINES["Dog"])
        baseline_min, baseline_max = 1.0, 2.0
        for low, high, cups_min, cups_max in guidelines:
            if low <= weight < high:
                baseline_min, baseline_max = cups_min, cups_max
                break
        
        baseline = (baseline_min + baseline_max) / 2
        
        # Calculate multiplier
        multiplier = round(avg_cups / baseline, 2) if baseline > 0 else 1.0
        return multiplier
    except (ValueError, IndexError):
        return None
