"""
test_url_compress.py — Tests for utils/url_compress.py

Covers: round-trip integrity, compression ratio, key minification,
field stripping, backwards compatibility, edge cases.
"""

from __future__ import annotations

import json
from utils.url_compress import (
    compress_itinerary, decompress_itinerary,
    _MINIFY, _EXPAND, _STRIP_ITEM_FIELDS,
)


def _sample_itinerary():
    return {
        "destination": "Osaka, Japan",
        "trip_length_days": 3,
        "budget_level": "Moderate",
        "travel_style": ["Culinary", "Culture"],
        "interests": ["Temples", "Street Food"],
        "pace": "Packed",
        "summary": "A packed 3-day Osaka adventure.",
        "estimated_total_cost": 450,
        "daily_cost_average": 150,
        "days": [
            {
                "day_number": 1,
                "theme": "Dotonbori District",
                "estimated_day_cost": 160,
                "items": [
                    {
                        "time_block": "Morning",
                        "title": "Osaka Castle",
                        "type": "activity",
                        "description": "Explore the iconic castle and surrounding park.",
                        "estimated_cost": 5,
                        "location_name": "Osaka Castle",
                        "latitude": 34.6873,
                        "longitude": 135.5262,
                    },
                    {
                        "time_block": "Lunch",
                        "title": "Takoyaki Stand",
                        "type": "meal",
                        "description": "Try the famous octopus balls at a local stall.",
                        "estimated_cost": 8,
                        "location_name": "Dotonbori Takoyaki",
                        "latitude": 34.6687,
                        "longitude": 135.5013,
                    },
                ],
            },
        ],
    }


class TestRoundTrip:
    def test_destination_preserved(self):
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        assert restored["destination"] == "Osaka, Japan"

    def test_trip_length_preserved(self):
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        assert restored["trip_length_days"] == 3

    def test_day_count_preserved(self):
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        assert len(restored["days"]) == 1

    def test_item_count_preserved(self):
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        assert len(restored["days"][0]["items"]) == 2

    def test_item_title_preserved(self):
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        assert restored["days"][0]["items"][0]["title"] == "Osaka Castle"

    def test_item_cost_preserved(self):
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        assert restored["days"][0]["items"][0]["estimated_cost"] == 5

    def test_item_type_preserved(self):
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        assert restored["days"][0]["items"][1]["type"] == "meal"

    def test_total_cost_preserved(self):
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        assert restored["estimated_total_cost"] == 450

    def test_theme_preserved(self):
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        assert restored["days"][0]["theme"] == "Dotonbori District"

    def test_summary_preserved(self):
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        assert "packed" in restored["summary"].lower()


class TestFieldStripping:
    def test_description_stripped(self):
        itin = _sample_itinerary()
        encoded = compress_itinerary(itin)
        # The compressed data should NOT contain full descriptions
        # (they're stripped before compression)
        restored = decompress_itinerary(encoded)
        # Description should be empty default
        assert restored["days"][0]["items"][0]["description"] == ""

    def test_coordinates_stripped(self):
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        # Coordinates should be defaults (0.0)
        assert restored["days"][0]["items"][0]["latitude"] == 0.0
        assert restored["days"][0]["items"][0]["longitude"] == 0.0

    def test_location_name_preserved(self):
        """location_name is kept for Google Maps links."""
        itin = _sample_itinerary()
        restored = decompress_itinerary(compress_itinerary(itin))
        assert restored["days"][0]["items"][0]["location_name"] == "Osaka Castle"


class TestCompression:
    def test_shorter_than_original(self):
        itin = _sample_itinerary()
        original = json.dumps(itin, separators=(",", ":"))
        encoded = compress_itinerary(itin)
        assert len(encoded) < len(original)

    def test_at_least_40_percent_smaller(self):
        """With key minification + field stripping, should be much smaller."""
        itin = _sample_itinerary()
        import zlib, base64
        old = base64.urlsafe_b64encode(
            zlib.compress(json.dumps(itin, separators=(",", ":")).encode(), 9)
        ).decode()
        new = compress_itinerary(itin)
        reduction = 100 - (len(new) * 100 // len(old))
        assert reduction >= 40, f"Only {reduction}% reduction"

    def test_url_safe_characters(self):
        itin = _sample_itinerary()
        encoded = compress_itinerary(itin)
        assert "+" not in encoded
        assert "/" not in encoded

    def test_realistic_trip_under_3000_chars(self):
        """A 4-day trip should compress to under 3000 chars."""
        with open("data/sample_trip.json") as f:
            itin = json.load(f)
        encoded = compress_itinerary(itin)
        assert len(encoded) < 3000, f"Got {len(encoded)} chars"


class TestKeyMappings:
    def test_minify_expand_round_trip(self):
        """Every minified key should expand back to the original."""
        for full_key, short_key in _MINIFY.items():
            assert _EXPAND[short_key] == full_key

    def test_no_duplicate_short_keys(self):
        """Short keys must be unique."""
        short_keys = list(_MINIFY.values())
        assert len(short_keys) == len(set(short_keys))


class TestEdgeCases:
    def test_empty_days(self):
        itin = {"destination": "Test", "days": []}
        restored = decompress_itinerary(compress_itinerary(itin))
        assert restored["destination"] == "Test"
        assert restored["days"] == []

    def test_unicode_destination(self):
        itin = {"destination": "京都", "days": []}
        restored = decompress_itinerary(compress_itinerary(itin))
        assert restored["destination"] == "京都"

    def test_empty_items(self):
        itin = {"destination": "X", "days": [{"day_number": 1, "items": []}]}
        restored = decompress_itinerary(compress_itinerary(itin))
        assert restored["days"][0]["items"] == []
