"""
test_proximity.py — Tests for geographic proximity checking.

Verifies that the validator flags consecutive items within a day
that are too far apart, and correctly handles edge cases like
missing coordinates, single items, and items within range.
"""

import pytest
from utils.itinerary_checker import check_proximity, _haversine_km


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _item(title, time_block, lat, lng, item_type="activity"):
    return {
        "title": title,
        "time_block": time_block,
        "type": item_type,
        "description": "",
        "estimated_cost": 0,
        "location_name": title,
        "latitude": lat,
        "longitude": lng,
    }


def _day(day_number, items):
    return {"day_number": day_number, "theme": f"Day {day_number}", "items": items}


def _itinerary(days):
    return {"destination": "Test City", "days": days}


# ---------------------------------------------------------------------------
# Haversine function tests
# ---------------------------------------------------------------------------
class TestHaversine:
    def test_same_point_is_zero(self):
        assert _haversine_km(35.0, 135.0, 35.0, 135.0) == 0.0

    def test_known_distance(self):
        """Fushimi Inari to Kiyomizu-dera is about 3.2 km."""
        dist = _haversine_km(34.9671, 135.7727, 34.9949, 135.7850)
        assert 2.5 < dist < 4.0, f"Expected ~3.2 km, got {dist:.1f}"

    def test_far_apart(self):
        """Kyoto to Tokyo is about 370 km."""
        dist = _haversine_km(35.0116, 135.7681, 35.6762, 139.6503)
        assert 350 < dist < 400, f"Expected ~370 km, got {dist:.0f}"

    def test_short_distance(self):
        """Two points 100m apart should be ~0.1 km."""
        dist = _haversine_km(35.0000, 135.0000, 35.0009, 135.0000)
        assert dist < 0.2, f"Expected ~0.1 km, got {dist:.3f}"


# ---------------------------------------------------------------------------
# Proximity check — items close together (no warnings)
# ---------------------------------------------------------------------------
class TestProximityClose:
    def test_all_items_close(self):
        """Items in the same Kyoto neighborhood — no warnings."""
        itin = _itinerary([
            _day(1, [
                _item("Fushimi Inari", "Morning", 34.9671, 135.7727),
                _item("Tofukuji Temple", "Lunch", 34.9761, 135.7726),
                _item("Kiyomizu-dera", "Afternoon", 34.9949, 135.7850),
            ]),
        ])
        warnings = check_proximity(itin)
        assert len(warnings) == 0

    def test_single_item_no_warning(self):
        itin = _itinerary([_day(1, [_item("Temple", "Morning", 35.0, 135.0)])])
        warnings = check_proximity(itin)
        assert len(warnings) == 0

    def test_empty_day_no_warning(self):
        itin = _itinerary([_day(1, [])])
        warnings = check_proximity(itin)
        assert len(warnings) == 0


# ---------------------------------------------------------------------------
# Proximity check — items far apart (should warn)
# ---------------------------------------------------------------------------
class TestProximityFar:
    def test_flags_far_apart_items(self):
        """Arashiyama (west) to Fushimi Inari (south) is ~13 km."""
        itin = _itinerary([
            _day(1, [
                _item("Bamboo Grove", "Morning", 35.0170, 135.6713),
                _item("Fushimi Inari", "Afternoon", 34.9671, 135.7727),
            ]),
        ])
        warnings = check_proximity(itin)
        assert len(warnings) == 1
        assert "Bamboo Grove" in warnings[0]
        assert "Fushimi Inari" in warnings[0]
        assert "km" in warnings[0]

    def test_flags_cross_city_jump(self):
        """North Kyoto (Kinkakuji) to south Kyoto (Fushimi) is ~10 km."""
        itin = _itinerary([
            _day(1, [
                _item("Kinkaku-ji", "Morning", 35.0394, 135.7292),
                _item("Fushimi Inari", "Lunch", 34.9671, 135.7727),
            ]),
        ])
        warnings = check_proximity(itin)
        assert len(warnings) >= 1

    def test_multiple_far_jumps(self):
        """Three items all far apart — should get 2 warnings."""
        itin = _itinerary([
            _day(1, [
                _item("North Kyoto", "Morning", 35.0394, 135.7292),
                _item("South Kyoto", "Lunch", 34.9671, 135.7727),
                _item("West Kyoto", "Afternoon", 35.0170, 135.6713),
            ]),
        ])
        warnings = check_proximity(itin)
        assert len(warnings) >= 2

    def test_only_last_pair_far(self):
        """First two close, last one far — should get 1 warning."""
        itin = _itinerary([
            _day(1, [
                _item("Nishiki Market", "Morning", 35.0050, 135.7650),
                _item("Pontocho", "Lunch", 35.0046, 135.7710),
                _item("Arashiyama", "Afternoon", 35.0170, 135.6713),
            ]),
        ])
        warnings = check_proximity(itin)
        assert len(warnings) == 1
        assert "Arashiyama" in warnings[0]


# ---------------------------------------------------------------------------
# Proximity check — ordering by time block
# ---------------------------------------------------------------------------
class TestProximityOrdering:
    def test_orders_by_time_block(self):
        """Items entered out of order should still be checked in time order."""
        itin = _itinerary([
            _day(1, [
                _item("Dinner Place", "Dinner", 34.9671, 135.7727),
                _item("Morning Temple", "Morning", 35.0394, 135.7292),
                _item("Lunch Spot", "Lunch", 35.0350, 135.7300),
            ]),
        ])
        warnings = check_proximity(itin)
        # Morning (north) → Lunch (north, close) → Dinner (south, far)
        # Should flag Lunch → Dinner, not Morning → Dinner
        far_warnings = [w for w in warnings if "Dinner Place" in w]
        assert len(far_warnings) >= 1


# ---------------------------------------------------------------------------
# Proximity check — missing coordinates
# ---------------------------------------------------------------------------
class TestProximityMissingCoords:
    def test_skips_items_without_coords(self):
        """Items with 0,0 coordinates should be ignored, not flagged."""
        itin = _itinerary([
            _day(1, [
                _item("Temple", "Morning", 35.0, 135.0),
                _item("Unknown Place", "Lunch", 0, 0),
                _item("Café", "Afternoon", 35.001, 135.001),
            ]),
        ])
        warnings = check_proximity(itin)
        assert len(warnings) == 0  # Temple → Café are close


# ---------------------------------------------------------------------------
# Proximity check — multi-day
# ---------------------------------------------------------------------------
class TestProximityMultiDay:
    def test_checks_each_day_independently(self):
        """Far items on different days should NOT trigger warnings."""
        itin = _itinerary([
            _day(1, [_item("North", "Morning", 35.04, 135.73)]),
            _day(2, [_item("South", "Morning", 34.97, 135.77)]),
        ])
        warnings = check_proximity(itin)
        assert len(warnings) == 0

    def test_flags_within_day_not_across(self):
        """Only flag proximity issues within the same day."""
        itin = _itinerary([
            _day(1, [
                _item("A", "Morning", 35.04, 135.73),
                _item("B", "Afternoon", 34.97, 135.77),  # far from A
            ]),
            _day(2, [
                _item("C", "Morning", 35.00, 135.76),
                _item("D", "Afternoon", 35.001, 135.761),  # close to C
            ]),
        ])
        warnings = check_proximity(itin)
        assert len(warnings) == 1  # only Day 1


# ---------------------------------------------------------------------------
# Custom threshold
# ---------------------------------------------------------------------------
class TestProximityThreshold:
    def test_custom_max_km(self):
        """With a very tight threshold, even close items should warn."""
        itin = _itinerary([
            _day(1, [
                _item("A", "Morning", 35.000, 135.000),
                _item("B", "Lunch", 35.010, 135.010),  # ~1.4 km apart
            ]),
        ])
        warnings = check_proximity(itin, max_km=1.0)
        assert len(warnings) == 1

    def test_very_generous_threshold(self):
        """With a huge threshold, nothing should warn."""
        itin = _itinerary([
            _day(1, [
                _item("A", "Morning", 35.04, 135.73),
                _item("B", "Afternoon", 34.97, 135.77),
            ]),
        ])
        warnings = check_proximity(itin, max_km=50.0)
        assert len(warnings) == 0
