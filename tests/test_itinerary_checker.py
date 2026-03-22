"""
test_itinerary_checker.py — Tests for utils/itinerary_checker.py

Verifies that the post-generation validator catches mismatches between
user preferences and itinerary content:
  - Late start preferences vs morning items
  - Early end preferences vs evening items on last day
  - Dietary preferences vs meal descriptions
  - Trip length mismatch
  - Destination mismatch
  - Rainy day mode vs outdoor activities
"""

import pytest
from utils.itinerary_checker import (
    validate_itinerary,
    check_late_start,
    check_early_end,
    check_dietary_preferences,
    check_trip_length,
    check_destination,
    check_rainy_day,
    _detect_dietary_preferences,
)


# ---------------------------------------------------------------------------
# Helpers: build test itineraries
# ---------------------------------------------------------------------------
def _item(title="Test", time_block="Morning", item_type="activity", description=""):
    return {
        "title": title,
        "time_block": time_block,
        "type": item_type,
        "description": description,
        "estimated_cost": 0,
        "location_name": title,
    }


def _day(day_number, items):
    return {"day_number": day_number, "theme": f"Day {day_number}", "items": items}


def _itinerary(destination="Kyoto, Japan", days=None):
    if days is None:
        days = []
    return {
        "destination": destination,
        "trip_length_days": len(days),
        "days": days,
    }


# =========================================================================
# LATE START TESTS
# =========================================================================
class TestLateStart:
    def test_flags_morning_items_when_late_start(self):
        itin = _itinerary(days=[
            _day(1, [_item("Temple Visit", "Morning"), _item("Lunch Spot", "Lunch", "meal")]),
        ])
        warnings = check_late_start(itin, "I like to start late mornings")
        assert len(warnings) == 1
        assert "Morning" in warnings[0]
        assert "Temple Visit" in warnings[0]

    def test_no_warnings_when_no_late_preference(self):
        itin = _itinerary(days=[
            _day(1, [_item("Temple Visit", "Morning")]),
        ])
        warnings = check_late_start(itin, "I love early mornings")
        assert len(warnings) == 0

    def test_flags_all_morning_items_across_days(self):
        itin = _itinerary(days=[
            _day(1, [_item("Shrine", "Morning")]),
            _day(2, [_item("Market", "Morning"), _item("Museum", "Afternoon")]),
        ])
        warnings = check_late_start(itin, "We sleep in every day")
        assert len(warnings) == 2

    def test_no_warning_for_afternoon_items(self):
        itin = _itinerary(days=[
            _day(1, [_item("Museum", "Afternoon"), _item("Dinner", "Dinner", "meal")]),
        ])
        warnings = check_late_start(itin, "I start late mornings")
        assert len(warnings) == 0

    def test_various_late_keywords(self):
        itin = _itinerary(days=[_day(1, [_item("Walk", "Morning")])])
        for phrase in ["sleep in", "not a morning person", "no early mornings", "late riser"]:
            warnings = check_late_start(itin, phrase)
            assert len(warnings) >= 1, f"Failed to detect: '{phrase}'"


# =========================================================================
# EARLY END TESTS
# =========================================================================
class TestEarlyEnd:
    def test_flags_dinner_on_last_day(self):
        itin = _itinerary(days=[
            _day(1, [_item("Temple", "Morning")]),
            _day(2, [_item("Farewell Dinner", "Dinner", "meal")]),
        ])
        warnings = check_early_end(itin, "My trip ends early afternoon on the last day")
        assert len(warnings) == 1
        assert "Farewell Dinner" in warnings[0]

    def test_flags_evening_on_last_day(self):
        itin = _itinerary(days=[
            _day(1, [_item("Walk", "Evening")]),
            _day(2, [_item("Night Market", "Evening")]),
        ])
        warnings = check_early_end(itin, "I leave early on the last day")
        assert len(warnings) == 1
        assert "Night Market" in warnings[0]

    def test_no_warning_for_non_last_day(self):
        itin = _itinerary(days=[
            _day(1, [_item("Dinner Out", "Dinner", "meal")]),
            _day(2, [_item("Quick Lunch", "Lunch", "meal")]),
        ])
        warnings = check_early_end(itin, "End early on the last day")
        assert len(warnings) == 0

    def test_no_warning_without_preference(self):
        itin = _itinerary(days=[
            _day(1, [_item("Late Night", "Evening")]),
        ])
        warnings = check_early_end(itin, "No special timing needs")
        assert len(warnings) == 0

    def test_flags_both_dinner_and_evening(self):
        itin = _itinerary(days=[
            _day(1, [_item("Lunch", "Lunch", "meal")]),
            _day(2, [
                _item("Final Dinner", "Dinner", "meal"),
                _item("Night Walk", "Evening"),
            ]),
        ])
        warnings = check_early_end(itin, "afternoon flight on the last day")
        assert len(warnings) == 2

    def test_various_early_end_keywords(self):
        itin = _itinerary(days=[_day(1, [_item("X", "Evening")])])
        for phrase in ["flight in the afternoon", "depart early", "half day", "leave by lunch"]:
            warnings = check_early_end(itin, phrase)
            assert len(warnings) >= 1, f"Failed to detect: '{phrase}'"


# =========================================================================
# DIETARY PREFERENCE TESTS
# =========================================================================
class TestDietaryPreferences:
    def test_detects_vegetarian(self):
        prefs = _detect_dietary_preferences("I'm vegetarian, no meat please")
        assert "vegetarian" in prefs

    def test_detects_vegan(self):
        prefs = _detect_dietary_preferences("We are vegan")
        assert "vegan" in prefs

    def test_detects_halal(self):
        prefs = _detect_dietary_preferences("Halal food only")
        assert "halal" in prefs

    def test_detects_gluten_free(self):
        prefs = _detect_dietary_preferences("I'm celiac, need gluten-free options")
        assert "gluten-free" in prefs

    def test_detects_multiple(self):
        prefs = _detect_dietary_preferences("I'm vegan and gluten-free")
        assert "vegan" in prefs
        assert "gluten-free" in prefs

    def test_no_dietary_preference(self):
        prefs = _detect_dietary_preferences("I like spicy food")
        assert len(prefs) == 0

    def test_flags_steak_for_vegetarian(self):
        itin = _itinerary(days=[
            _day(1, [_item("Wagyu Steak House", "Dinner", "meal", "Premium wagyu beef steak")]),
        ])
        warnings = check_dietary_preferences(itin, "I'm vegetarian")
        assert len(warnings) >= 1
        assert "vegetarian" in warnings[0].lower() or "steak" in warnings[0].lower()

    def test_flags_tonkatsu_for_vegetarian(self):
        itin = _itinerary(days=[
            _day(1, [_item("Tonkatsu Maisen", "Lunch", "meal", "Deep-fried pork cutlet")]),
        ])
        warnings = check_dietary_preferences(itin, "Vegetarian meals preferred")
        assert len(warnings) >= 1

    def test_flags_pork_for_halal(self):
        itin = _itinerary(days=[
            _day(1, [_item("Pulled Pork BBQ", "Dinner", "meal", "Slow-smoked pork ribs")]),
        ])
        warnings = check_dietary_preferences(itin, "We need halal food")
        assert len(warnings) >= 1

    def test_flags_ramen_for_gluten_free(self):
        itin = _itinerary(days=[
            _day(1, [_item("Ippudo Ramen", "Lunch", "meal", "Rich tonkotsu ramen")]),
        ])
        warnings = check_dietary_preferences(itin, "Gluten-free please, I have celiac")
        assert len(warnings) >= 1

    def test_flags_sushi_for_seafood_free(self):
        itin = _itinerary(days=[
            _day(1, [_item("Tsukiji Sushi", "Lunch", "meal", "Fresh sushi and sashimi")]),
        ])
        warnings = check_dietary_preferences(itin, "No seafood, seafood allergy")
        assert len(warnings) >= 1

    def test_no_warning_for_safe_meal(self):
        itin = _itinerary(days=[
            _day(1, [_item("Veggie Café", "Lunch", "meal", "Fresh salads and smoothies")]),
        ])
        warnings = check_dietary_preferences(itin, "I'm vegetarian")
        assert len(warnings) == 0

    def test_only_checks_meal_items(self):
        """Activities should NOT be checked for dietary violations."""
        itin = _itinerary(days=[
            _day(1, [_item("Beef Museum", "Morning", "activity", "Learn about Kobe beef history")]),
        ])
        warnings = check_dietary_preferences(itin, "I'm vegetarian")
        assert len(warnings) == 0

    def test_checks_description_not_just_title(self):
        itin = _itinerary(days=[
            _day(1, [_item("Local Restaurant", "Dinner", "meal", "Famous for their grilled chicken skewers")]),
        ])
        warnings = check_dietary_preferences(itin, "Vegetarian only")
        assert len(warnings) >= 1


# =========================================================================
# TRIP LENGTH TESTS
# =========================================================================
class TestTripLength:
    def test_matching_length(self):
        itin = _itinerary(days=[_day(1, []), _day(2, []), _day(3, [])])
        warnings = check_trip_length(itin, 3)
        assert len(warnings) == 0

    def test_too_few_days(self):
        itin = _itinerary(days=[_day(1, []), _day(2, [])])
        warnings = check_trip_length(itin, 4)
        assert len(warnings) == 1
        assert "4" in warnings[0] and "2" in warnings[0]

    def test_too_many_days(self):
        itin = _itinerary(days=[_day(i, []) for i in range(1, 8)])
        warnings = check_trip_length(itin, 5)
        assert len(warnings) == 1


# =========================================================================
# DESTINATION TESTS
# =========================================================================
class TestDestination:
    def test_matching_destination(self):
        itin = _itinerary(destination="Kyoto, Japan")
        warnings = check_destination(itin, "Kyoto")
        assert len(warnings) == 0

    def test_mismatched_destination(self):
        itin = _itinerary(destination="Tokyo, Japan")
        warnings = check_destination(itin, "Paris")
        assert len(warnings) == 1
        assert "Paris" in warnings[0]

    def test_case_insensitive(self):
        itin = _itinerary(destination="KYOTO, JAPAN")
        warnings = check_destination(itin, "kyoto")
        assert len(warnings) == 0


# =========================================================================
# RAINY DAY TESTS
# =========================================================================
# The exact text injected by app.py when rainy day mode is toggled on:
_RAINY_NOTE = "IMPORTANT: It will be rainy. Strongly prefer indoor activities — museums, covered markets, indoor workshops, cafés, galleries, aquariums, cooking classes. Avoid outdoor hiking, parks, and open-air sightseeing."


class TestRainyDay:
    def test_flags_outdoor_activities(self):
        itin = _itinerary(days=[
            _day(1, [
                _item("Sunrise Hike", "Morning", "activity", "Hike to the summit for sunrise views"),
                _item("Indoor Museum", "Afternoon", "activity", "World-class art collection"),
            ]),
        ])
        warnings = check_rainy_day(itin, _RAINY_NOTE)
        assert len(warnings) == 1
        assert "Sunrise Hike" in warnings[0]

    def test_flags_park_and_garden(self):
        itin = _itinerary(days=[
            _day(1, [
                _item("Shinjuku Gyoen", "Afternoon", "activity", "Expansive park and garden"),
                _item("River Walk", "Evening", "activity", "Stroll along the river walk at dusk"),
            ]),
        ])
        warnings = check_rainy_day(itin, _RAINY_NOTE)
        assert len(warnings) == 2

    def test_no_warning_for_indoor_activities(self):
        itin = _itinerary(days=[
            _day(1, [
                _item("National Museum", "Morning", "activity", "Explore ancient artifacts"),
                _item("Cooking Class", "Afternoon", "activity", "Learn to make local dishes"),
            ]),
        ])
        warnings = check_rainy_day(itin, _RAINY_NOTE)
        assert len(warnings) == 0

    def test_no_warning_without_rainy_mode(self):
        """User didn't toggle rainy mode — no warnings even for outdoor items."""
        itin = _itinerary(days=[
            _day(1, [_item("Beach Day", "Morning", "activity", "Relax on the beach")]),
        ])
        warnings = check_rainy_day(itin, "Looking forward to sunny weather!")
        assert len(warnings) == 0

    def test_no_false_positive_from_train(self):
        """The word 'train' contains 'rain' — must NOT trigger rainy day check."""
        itin = _itinerary(days=[
            _day(1, [_item("Beach Day", "Morning", "activity", "Relax on the beach")]),
        ])
        warnings = check_rainy_day(itin, "Take the train to the coast")
        assert len(warnings) == 0

    def test_no_false_positive_from_terrain(self):
        """The word 'terrain' contains 'rain' — must NOT trigger."""
        itin = _itinerary(days=[
            _day(1, [_item("Hike", "Morning", "activity", "Rough terrain ahead")]),
        ])
        warnings = check_rainy_day(itin, "The terrain is rocky but beautiful")
        assert len(warnings) == 0

    def test_meals_not_flagged(self):
        """Meals should not be flagged even if they mention outdoor seating."""
        itin = _itinerary(days=[
            _day(1, [_item("Riverside Café", "Lunch", "meal", "Outdoor riverside dining")]),
        ])
        warnings = check_rainy_day(itin, _RAINY_NOTE)
        assert len(warnings) == 0

    def test_flags_beach_and_waterfront(self):
        itin = _itinerary(days=[
            _day(1, [
                _item("Beach Stroll", "Morning", "activity", "Walk along the beach"),
                _item("Waterfront Pier", "Afternoon", "activity", "Visit the waterfront pier"),
            ]),
        ])
        warnings = check_rainy_day(itin, _RAINY_NOTE)
        assert len(warnings) == 2


# =========================================================================
# FULL VALIDATION (validate_itinerary entry point)
# =========================================================================
class TestFullValidation:
    def test_no_warnings_for_clean_itinerary(self):
        itin = _itinerary(destination="Kyoto, Japan", days=[
            _day(1, [
                _item("Museum", "Afternoon", "activity", "Art museum"),
                _item("Veggie Café", "Lunch", "meal", "Fresh salads"),
            ]),
        ])
        warnings = validate_itinerary(
            itin,
            requested_destination="Kyoto",
            requested_days=1,
            notes="I'm vegetarian and start late mornings",
        )
        assert len(warnings) == 0

    def test_catches_multiple_issues(self):
        itin = _itinerary(destination="Tokyo, Japan", days=[
            _day(1, [
                _item("Shrine", "Morning", "activity"),
                _item("Steak House", "Dinner", "meal", "Premium beef steak"),
            ]),
            _day(2, [
                _item("Night Market", "Evening"),
            ]),
        ])
        warnings = validate_itinerary(
            itin,
            requested_destination="Kyoto",
            requested_days=3,
            notes="Vegetarian, start late, end early on last day",
        )
        # Should catch: wrong destination, wrong day count, morning item
        # with late start, steak for vegetarian, evening on last day with
        # early end
        assert len(warnings) >= 4

    def test_empty_notes_no_crash(self):
        itin = _itinerary(destination="Kyoto", days=[_day(1, [])])
        warnings = validate_itinerary(itin, "Kyoto", 1, "")
        assert len(warnings) == 0

    def test_no_days_no_crash(self):
        itin = _itinerary(destination="Kyoto", days=[])
        warnings = validate_itinerary(itin, "Kyoto", 0, "")
        assert len(warnings) == 0
