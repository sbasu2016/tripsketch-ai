"""
itinerary_checker.py — Post-generation validation for itinerary quality.

After an itinerary is generated (by Claude or mock), this module checks
whether the output actually respects the user's stated preferences.
Returns a list of warnings for any mismatches found.

This is NOT about JSON schema validation (parser.py handles that).
This is about *semantic* correctness — does the itinerary make sense
given what the user asked for?
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Time-block ordering for early/late checks
# ---------------------------------------------------------------------------
TIME_BLOCK_ORDER = ["Morning", "Lunch", "Afternoon", "Dinner", "Evening"]

# Keywords that suggest a preference for late starts
LATE_START_KEYWORDS = [
    "start late", "late morning", "sleep in", "no early",
    "not a morning person", "late riser", "no morning",
]

# Keywords that suggest the trip ends early on the last day
EARLY_END_KEYWORDS = [
    "end early", "early afternoon", "leave early", "flight in the afternoon",
    "depart early", "checkout early", "last day short", "half day",
    "ends at lunch", "leave by lunch", "afternoon flight", "evening flight",
]

# Common dietary preference keywords and what they imply
DIETARY_KEYWORDS = {
    "vegetarian": ["vegetarian", "veggie", "no meat", "meat-free", "meatless"],
    "vegan": ["vegan", "plant-based", "plant based", "no animal"],
    "halal": ["halal"],
    "kosher": ["kosher"],
    "gluten-free": ["gluten-free", "gluten free", "no gluten", "celiac"],
    "seafood-free": ["no seafood", "seafood allergy", "allergic to seafood", "no fish"],
    "dairy-free": ["dairy-free", "dairy free", "no dairy", "lactose"],
}

# Meal items that clearly violate dietary preferences
DIETARY_VIOLATIONS = {
    "vegetarian": [
        "steak", "beef", "pork", "chicken", "lamb", "duck", "bacon",
        "ribs", "brisket", "sausage", "salami", "ham", "turkey",
        "tonkatsu", "yakitori chicken", "pulled pork", "wagyu",
    ],
    "vegan": [
        "steak", "beef", "pork", "chicken", "lamb", "duck", "cheese",
        "cream", "butter", "egg", "milk", "yogurt", "honey",
        "tonkatsu", "yakitori", "kaiseki",
    ],
    "halal": ["pork", "bacon", "ham", "prosciutto", "salami", "lard"],
    "kosher": ["pork", "bacon", "ham", "shellfish", "shrimp", "lobster", "crab"],
    "gluten-free": ["ramen", "pasta", "bread", "pizza", "noodle", "soba", "udon"],
    "seafood-free": [
        "sushi", "sashimi", "fish", "shrimp", "lobster", "crab",
        "oyster", "clam", "mussel", "octopus", "squid", "uni",
    ],
}


# ---------------------------------------------------------------------------
# Helper: detect keywords in notes
# ---------------------------------------------------------------------------
def _notes_contain(notes: str, keywords: list) -> bool:
    """Check if any keyword phrase appears in the notes (case-insensitive)."""
    notes_lower = notes.lower()
    return any(kw in notes_lower for kw in keywords)


def _detect_dietary_preferences(notes: str) -> list:
    """Return a list of dietary preference names found in the notes."""
    found = []
    for pref_name, keywords in DIETARY_KEYWORDS.items():
        if _notes_contain(notes, keywords):
            found.append(pref_name)
    return found


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------
def check_late_start(itinerary: dict, notes: str) -> list:
    """
    If the user indicated they start late, warn about any Morning
    items on any day.
    """
    warnings = []
    if not _notes_contain(notes, LATE_START_KEYWORDS):
        return warnings

    for day in itinerary.get("days", []):
        day_num = day.get("day_number", "?")
        for item in day.get("items", []):
            if item.get("time_block") == "Morning":
                warnings.append(
                    f"Day {day_num}: '{item.get('title', '?')}' is a Morning item, "
                    f"but the user prefers late starts."
                )
    return warnings


def check_early_end(itinerary: dict, notes: str) -> list:
    """
    If the user indicated their trip ends early on the last day,
    warn about Dinner or Evening items on the final day.
    """
    warnings = []
    if not _notes_contain(notes, EARLY_END_KEYWORDS):
        return warnings

    days = itinerary.get("days", [])
    if not days:
        return warnings

    last_day = days[-1]
    day_num = last_day.get("day_number", "?")

    for item in last_day.get("items", []):
        block = item.get("time_block", "")
        if block in ("Dinner", "Evening"):
            warnings.append(
                f"Day {day_num} (last day): '{item.get('title', '?')}' is a {block} item, "
                f"but the user said the trip ends early."
            )
    return warnings


def check_dietary_preferences(itinerary: dict, notes: str) -> list:
    """
    If the user stated dietary preferences, check all meal items
    for obvious violations (e.g. steak for a vegetarian).
    """
    warnings = []
    preferences = _detect_dietary_preferences(notes)
    if not preferences:
        return warnings

    for day in itinerary.get("days", []):
        day_num = day.get("day_number", "?")
        for item in day.get("items", []):
            if item.get("type") != "meal":
                continue

            title_lower = item.get("title", "").lower()
            desc_lower = item.get("description", "").lower()
            combined = f"{title_lower} {desc_lower}"

            for pref in preferences:
                violations = DIETARY_VIOLATIONS.get(pref, [])
                for v in violations:
                    if v in combined:
                        warnings.append(
                            f"Day {day_num}: '{item.get('title', '?')}' may conflict "
                            f"with {pref} preference (found '{v}' in description)."
                        )
                        break  # one violation per pref per item is enough

    return warnings


def check_trip_length(itinerary: dict, requested_days: int) -> list:
    """Check that the number of days matches what was requested."""
    warnings = []
    actual = len(itinerary.get("days", []))
    if actual != requested_days:
        warnings.append(
            f"Requested {requested_days} days but itinerary has {actual} days."
        )
    return warnings


def check_destination(itinerary: dict, requested_dest: str) -> list:
    """Check that the itinerary destination matches the request."""
    warnings = []
    actual = itinerary.get("destination", "").lower()
    requested = requested_dest.lower()
    # Check if the requested destination appears in the actual
    if requested and requested not in actual:
        warnings.append(
            f"Requested destination '{requested_dest}' but itinerary says "
            f"'{itinerary.get('destination', '?')}'."
        )
    return warnings


def check_rainy_day(itinerary: dict, notes: str) -> list:
    """
    If rainy day mode was activated (detected via notes), warn about
    clearly outdoor activities.
    """
    warnings = []
    # Only trigger if the exact rainy-day instruction was injected by the app.
    # This avoids false positives from words like "train" or "terrain".
    rainy_markers = [
        "important: it will be rainy",
        "strongly prefer indoor activities",
    ]
    if not _notes_contain(notes, rainy_markers):
        return warnings

    outdoor_keywords = [
        "hike", "hiking", "park", "garden", "beach", "waterfront",
        "river walk", "viewpoint", "sunrise", "sunset walk",
        "outdoor", "open-air", "open air",
    ]

    for day in itinerary.get("days", []):
        day_num = day.get("day_number", "?")
        for item in day.get("items", []):
            if item.get("type") == "meal":
                continue
            combined = f"{item.get('title', '')} {item.get('description', '')}".lower()
            for kw in outdoor_keywords:
                if kw in combined:
                    warnings.append(
                        f"Day {day_num}: '{item.get('title', '?')}' appears to be "
                        f"an outdoor activity ('{kw}'), but rainy day mode is on."
                    )
                    break

    return warnings


# ---------------------------------------------------------------------------
# Geographic proximity check
# ---------------------------------------------------------------------------
import math

# Maximum comfortable distance (km) between consecutive items in a day.
# Beyond this, the traveler is probably wasting time in transit.
MAX_COMFORTABLE_KM = 8.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in km."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def check_proximity(itinerary: dict, max_km: float = MAX_COMFORTABLE_KM) -> list:
    """
    Check that consecutive items within each day are geographically
    close to each other. Flags pairs that exceed max_km apart.

    Items are ordered by time block: Morning → Lunch → Afternoon →
    Dinner → Evening. Within the same time block, items are checked
    in the order they appear.
    """
    warnings = []
    block_order = {b: i for i, b in enumerate(TIME_BLOCK_ORDER)}

    for day in itinerary.get("days", []):
        day_num = day.get("day_number", "?")
        items = day.get("items", [])

        # Sort items by time block order, then by original position
        sorted_items = sorted(
            items,
            key=lambda x: (block_order.get(x.get("time_block", "Morning"), 0),),
        )

        # Filter to items that have valid coordinates
        located = [
            it for it in sorted_items
            if it.get("latitude", 0) != 0 and it.get("longitude", 0) != 0
        ]

        # Check consecutive pairs
        for i in range(len(located) - 1):
            a = located[i]
            b = located[i + 1]

            dist = _haversine_km(
                a["latitude"], a["longitude"],
                b["latitude"], b["longitude"],
            )

            if dist > max_km:
                warnings.append(
                    f"Day {day_num}: '{a.get('title', '?')}' → "
                    f"'{b.get('title', '?')}' is {dist:.1f} km apart. "
                    f"Consider reordering to reduce travel time."
                )

    return warnings


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def validate_itinerary(
    itinerary: dict,
    requested_destination: str = "",
    requested_days: int = 0,
    notes: str = "",
) -> list:
    """
    Run all post-generation checks and return a list of warning strings.

    An empty list means no issues were found.
    """
    warnings = []

    if requested_destination:
        warnings.extend(check_destination(itinerary, requested_destination))

    if requested_days > 0:
        warnings.extend(check_trip_length(itinerary, requested_days))

    if notes:
        warnings.extend(check_late_start(itinerary, notes))
        warnings.extend(check_early_end(itinerary, notes))
        warnings.extend(check_dietary_preferences(itinerary, notes))
        warnings.extend(check_rainy_day(itinerary, notes))

    # Always check geographic proximity
    warnings.extend(check_proximity(itinerary))

    return warnings
