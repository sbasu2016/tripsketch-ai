"""
test_parser.py — Tests for utils/parser.py

Covers: valid JSON, markdown fences, missing fields, empty days,
malformed JSON, default filling, and item validation.
"""

import pytest
import json
from utils.parser import parse_itinerary, ItineraryParseError, ItineraryValidationError


def _minimal():
    return {
        "destination": "Tokyo",
        "trip_length_days": 1,
        "estimated_total_cost": 100,
        "daily_cost_average": 100,
        "days": [
            {
                "day_number": 1,
                "items": [
                    {"title": "Visit temple", "type": "activity"}
                ],
            }
        ],
    }


class TestParseValid:
    def test_basic_parse(self):
        result = parse_itinerary(json.dumps(_minimal()))
        assert result["destination"] == "Tokyo"
        assert len(result["days"]) == 1

    def test_strips_markdown_fences(self):
        raw = f"```json\n{json.dumps(_minimal())}\n```"
        result = parse_itinerary(raw)
        assert result["destination"] == "Tokyo"

    def test_strips_preamble_text(self):
        raw = f"Here is your plan:\n\n{json.dumps(_minimal())}\n\nEnjoy!"
        result = parse_itinerary(raw)
        assert result["destination"] == "Tokyo"

    def test_fills_top_level_defaults(self):
        result = parse_itinerary(json.dumps(_minimal()))
        assert result.get("summary") == ""
        assert result.get("pace") == "Balanced"
        assert result.get("travel_style") == []

    def test_fills_item_defaults(self):
        result = parse_itinerary(json.dumps(_minimal()))
        item = result["days"][0]["items"][0]
        assert item.get("time_block") == "Morning"
        assert item.get("estimated_cost") == 0
        assert item.get("description") == ""
        assert item.get("latitude") == 0.0
        assert item.get("longitude") == 0.0

    def test_fills_day_defaults(self):
        result = parse_itinerary(json.dumps(_minimal()))
        day = result["days"][0]
        assert "theme" in day
        assert day.get("estimated_day_cost") == 0

    def test_preserves_existing_fields(self):
        data = _minimal()
        data["summary"] = "A great trip"
        data["days"][0]["items"][0]["description"] = "Beautiful temple"
        result = parse_itinerary(json.dumps(data))
        assert result["summary"] == "A great trip"
        assert result["days"][0]["items"][0]["description"] == "Beautiful temple"


class TestParseMalformed:
    def test_no_json_at_all(self):
        with pytest.raises(ItineraryParseError, match="No JSON object"):
            parse_itinerary("This is just plain text.")

    def test_invalid_json_syntax(self):
        with pytest.raises(ItineraryParseError):
            parse_itinerary('{"destination": "Tokyo" "bad": :::}')

    def test_empty_string(self):
        with pytest.raises(ItineraryParseError):
            parse_itinerary("")

    def test_only_fences(self):
        with pytest.raises(ItineraryParseError):
            parse_itinerary("```json\n```")


class TestValidationErrors:
    def test_missing_destination(self):
        data = _minimal()
        del data["destination"]
        with pytest.raises(ItineraryValidationError, match="destination"):
            parse_itinerary(json.dumps(data))

    def test_missing_days(self):
        data = _minimal()
        del data["days"]
        with pytest.raises(ItineraryValidationError, match="days"):
            parse_itinerary(json.dumps(data))

    def test_empty_days_list(self):
        data = _minimal()
        data["days"] = []
        with pytest.raises(ItineraryValidationError, match="at least one day"):
            parse_itinerary(json.dumps(data))

    def test_days_not_a_list(self):
        data = _minimal()
        data["days"] = "not a list"
        with pytest.raises(ItineraryValidationError):
            parse_itinerary(json.dumps(data))

    def test_day_missing_items(self):
        data = _minimal()
        del data["days"][0]["items"]
        with pytest.raises(ItineraryValidationError, match="items"):
            parse_itinerary(json.dumps(data))

    def test_items_not_a_list(self):
        data = _minimal()
        data["days"][0]["items"] = "not a list"
        with pytest.raises(ItineraryValidationError, match="must be a list"):
            parse_itinerary(json.dumps(data))

    def test_item_missing_title(self):
        data = _minimal()
        del data["days"][0]["items"][0]["title"]
        with pytest.raises(ItineraryValidationError, match="title"):
            parse_itinerary(json.dumps(data))

    def test_item_missing_type(self):
        data = _minimal()
        del data["days"][0]["items"][0]["type"]
        with pytest.raises(ItineraryValidationError, match="type"):
            parse_itinerary(json.dumps(data))


# =========================================================================
# JSON REPAIR TESTS
# =========================================================================
class TestJSONRepair:
    """Test auto-repair of common LLM JSON errors."""

    def test_trailing_comma_object(self):
        """Trailing comma before } should be removed."""
        from utils.parser import _repair_json
        result = json.loads(_repair_json('{"a": 1, "b": 2,}'))
        assert result == {"a": 1, "b": 2}

    def test_trailing_comma_array(self):
        """Trailing comma before ] should be removed."""
        from utils.parser import _repair_json
        result = json.loads(_repair_json('{"a": [1, 2,]}'))
        assert result == {"a": [1, 2]}

    def test_missing_comma_between_objects(self):
        """Missing comma between } { should be added."""
        from utils.parser import _repair_json
        result = json.loads(_repair_json('[{"a":1} {"b":2}]'))
        assert result == [{"a": 1}, {"b": 2}]

    def test_normal_json_unchanged(self):
        """Valid JSON should pass through repair without modification."""
        from utils.parser import _repair_json
        good = '{"a": 1, "b": [1, 2]}'
        assert json.loads(_repair_json(good)) == json.loads(good)

    def test_nested_trailing_commas(self):
        """Nested trailing commas should all be fixed."""
        from utils.parser import _repair_json
        s = '{"a": {"b": 1,}, "c": [1, 2,],}'
        result = json.loads(_repair_json(s))
        assert result == {"a": {"b": 1}, "c": [1, 2]}

    def test_truncated_json_still_fails(self):
        """Truncated JSON can't be repaired — should raise ItineraryParseError."""
        with pytest.raises(ItineraryParseError):
            parse_itinerary(
                '{"destination": "Kyoto", "days": [{"day_number": 1, "items": [{"title": "Temp'
            )

    def test_repair_then_parse_succeeds(self):
        """An itinerary with a trailing comma should be repaired and parsed."""
        good = json.dumps(_minimal())
        # Add trailing comma to make it invalid
        bad = good[:-1] + ",}"
        result = parse_itinerary(bad)
        assert result["destination"] == "Tokyo"

    def test_missing_comma_between_items(self):
        """Missing comma between array items should be repaired."""
        from utils.parser import _repair_json
        s = '[{"a":1}\n{"b":2}]'
        result = json.loads(_repair_json(s))
        assert len(result) == 2

    def test_multiple_trailing_commas(self):
        """Multiple trailing commas in different places."""
        from utils.parser import _repair_json
        s = '{"items": [{"a": 1,}, {"b": 2,},],}'
        result = json.loads(_repair_json(s))
        assert len(result["items"]) == 2
