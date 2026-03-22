"""
validators.py — Input validation for trip planning form fields.

Keeps validation logic out of the UI layer so it can be tested
independently and reused across different interfaces.
"""

from __future__ import annotations

VALID_BUDGET_LEVELS = ["Budget", "Moderate", "Premium", "Luxury"]
VALID_PACES = ["Relaxed", "Balanced", "Packed"]

MAX_TRIP_DAYS = 14
MIN_TRIP_DAYS = 1
MAX_INTERESTS = 5
MAX_NOTES_CHARS = 500
MAX_MUST_SEE_CHARS = 200


class ValidationError(Exception):
    """Raised when user input fails validation."""
    pass


def validate_destination(destination: str) -> str:
    """Validate and clean the destination string."""
    cleaned = destination.strip()
    if not cleaned:
        raise ValidationError("Destination is required.")
    if len(cleaned) < 2:
        raise ValidationError("Destination must be at least 2 characters.")
    if len(cleaned) > 100:
        raise ValidationError("Destination must be under 100 characters.")
    return cleaned


def validate_trip_length(days: int) -> int:
    """Validate trip length is within allowed range."""
    if not isinstance(days, int):
        raise ValidationError("Trip length must be a whole number.")
    if days < MIN_TRIP_DAYS:
        raise ValidationError(f"Trip must be at least {MIN_TRIP_DAYS} day.")
    if days > MAX_TRIP_DAYS:
        raise ValidationError(f"Trip cannot exceed {MAX_TRIP_DAYS} days.")
    return days


def validate_budget_level(level: str) -> str:
    """Validate budget level is a known tier."""
    if level not in VALID_BUDGET_LEVELS:
        raise ValidationError(
            f"Invalid budget level '{level}'. "
            f"Choose from: {', '.join(VALID_BUDGET_LEVELS)}"
        )
    return level


def validate_pace(pace: str) -> str:
    """Validate trip pace is a known option."""
    if pace not in VALID_PACES:
        raise ValidationError(
            f"Invalid pace '{pace}'. "
            f"Choose from: {', '.join(VALID_PACES)}"
        )
    return pace


def validate_interests(interests: list) -> list:
    """Validate interests list length."""
    if len(interests) > MAX_INTERESTS:
        raise ValidationError(f"Select up to {MAX_INTERESTS} interests.")
    return interests


def validate_notes(notes: str) -> str:
    """Validate optional notes length."""
    if len(notes) > MAX_NOTES_CHARS:
        raise ValidationError(
            f"Notes must be under {MAX_NOTES_CHARS} characters "
            f"(currently {len(notes)})."
        )
    return notes


def validate_must_see(must_see: str) -> str:
    """Validate must-see places length."""
    if len(must_see) > MAX_MUST_SEE_CHARS:
        raise ValidationError(
            f"Must-see places must be under {MAX_MUST_SEE_CHARS} characters "
            f"(currently {len(must_see)})."
        )
    return must_see


def validate_all(
    destination: str,
    trip_length_days: int,
    budget_level: str,
    pace: str,
    interests: list,
) -> dict:
    """
    Run all validators and return a cleaned dict of inputs.
    Raises ValidationError on the first failure.
    """
    return {
        "destination": validate_destination(destination),
        "trip_length_days": validate_trip_length(trip_length_days),
        "budget_level": validate_budget_level(budget_level),
        "pace": validate_pace(pace),
        "interests": validate_interests(interests),
    }
