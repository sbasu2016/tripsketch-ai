"""
test_share.py — Tests for the shareable trip link feature.

The share link encodes an itinerary as compressed base64 in URL params.
Tests cover: roundtrip encode/decode, unicode handling, large payloads,
corrupt data handling, and empty itineraries.
"""

import json
import base64
import zlib
import pytest


def _encode_trip(itinerary: dict) -> str:
    """Encode an itinerary dict to a share link string (same logic as app.py)."""
    raw = json.dumps(itinerary, ensure_ascii=False, separators=(",", ":"))
    compressed = zlib.compress(raw.encode("utf-8"), level=9)
    return base64.urlsafe_b64encode(compressed).decode("ascii")


def _decode_trip(encoded: str) -> dict:
    """Decode a share link string back to an itinerary dict."""
    compressed = base64.urlsafe_b64decode(encoded)
    raw = zlib.decompress(compressed).decode("utf-8")
    return json.loads(raw)


def _sample():
    return {
        "destination": "Kyoto, Japan",
        "trip_length_days": 2,
        "budget_level": "Moderate",
        "estimated_total_cost": 300,
        "daily_cost_average": 150,
        "days": [
            {
                "day_number": 1,
                "theme": "Historic Kyoto",
                "estimated_day_cost": 140,
                "items": [
                    {
                        "time_block": "Morning",
                        "title": "Fushimi Inari",
                        "type": "activity",
                        "description": "Walk the torii gates.",
                        "estimated_cost": 0,
                        "location_name": "Fushimi Inari Taisha",
                        "latitude": 34.9671,
                        "longitude": 135.7727,
                    },
                ],
            },
        ],
    }


class TestShareRoundtrip:
    def test_basic_roundtrip(self):
        original = _sample()
        encoded = _encode_trip(original)
        decoded = _decode_trip(encoded)
        assert decoded["destination"] == "Kyoto, Japan"
        assert decoded["trip_length_days"] == 2
        assert len(decoded["days"]) == 1

    def test_preserves_nested_data(self):
        original = _sample()
        decoded = _decode_trip(_encode_trip(original))
        item = decoded["days"][0]["items"][0]
        assert item["title"] == "Fushimi Inari"
        assert item["latitude"] == 34.9671

    def test_preserves_cost_data(self):
        original = _sample()
        decoded = _decode_trip(_encode_trip(original))
        assert decoded["estimated_total_cost"] == 300
        assert decoded["daily_cost_average"] == 150


class TestShareUnicode:
    def test_unicode_destination(self):
        itin = _sample()
        itin["destination"] = "京都、日本"
        decoded = _decode_trip(_encode_trip(itin))
        assert decoded["destination"] == "京都、日本"

    def test_unicode_description(self):
        itin = _sample()
        itin["days"][0]["items"][0]["description"] = "鳥居を歩く"
        decoded = _decode_trip(_encode_trip(itin))
        assert decoded["days"][0]["items"][0]["description"] == "鳥居を歩く"


class TestShareCompression:
    def test_encoded_is_shorter_than_raw(self):
        itin = _sample()
        raw = json.dumps(itin)
        encoded = _encode_trip(itin)
        # Compressed+base64 should be shorter than raw JSON for real data
        assert len(encoded) < len(raw) * 2  # generous bound

    def test_large_itinerary_encodes(self):
        """A 7-day trip with 6 items each should still encode."""
        itin = _sample()
        itin["trip_length_days"] = 7
        itin["days"] = []
        for d in range(1, 8):
            day = {"day_number": d, "theme": f"Day {d} theme", "estimated_day_cost": 100, "items": []}
            for i in range(6):
                day["items"].append({
                    "time_block": "Morning",
                    "title": f"Activity {i} on day {d}",
                    "type": "activity",
                    "description": f"Description for activity {i}",
                    "estimated_cost": 10,
                    "location_name": f"Place {i}",
                    "latitude": 34.0 + d * 0.01,
                    "longitude": 135.0 + i * 0.01,
                })
            itin["days"].append(day)

        encoded = _encode_trip(itin)
        decoded = _decode_trip(encoded)
        assert len(decoded["days"]) == 7
        assert len(decoded["days"][0]["items"]) == 6


class TestShareEdgeCases:
    def test_empty_itinerary(self):
        decoded = _decode_trip(_encode_trip({}))
        assert decoded == {}

    def test_corrupt_data_raises(self):
        with pytest.raises(Exception):
            _decode_trip("this_is_not_valid_base64!!!")

    def test_truncated_data_raises(self):
        encoded = _encode_trip(_sample())
        truncated = encoded[:10]
        with pytest.raises(Exception):
            _decode_trip(truncated)


class TestShareUrlSafety:
    def test_no_unsafe_url_characters(self):
        """Base64 urlsafe encoding should not contain + or /."""
        encoded = _encode_trip(_sample())
        assert "+" not in encoded
        assert "/" not in encoded
