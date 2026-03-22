"""
parser.py — Parse and validate LLM-generated itinerary JSON.

Handles common LLM quirks: markdown fences, trailing text, preamble.
Validates required fields and fills safe defaults for missing optional
fields so downstream code never hits KeyError.
"""

from __future__ import annotations

import json
import re


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class ItineraryParseError(Exception):
    """Raised when raw LLM output cannot be parsed as JSON at all."""
    pass


class ItineraryValidationError(Exception):
    """Raised when parsed JSON is missing required structure."""
    pass


# ---------------------------------------------------------------------------
# Required field sets
# ---------------------------------------------------------------------------
REQUIRED_TOP_LEVEL = {
    "destination", "trip_length_days", "days",
    "estimated_total_cost", "daily_cost_average",
}
REQUIRED_DAY_FIELDS = {"day_number", "items"}
REQUIRED_ITEM_FIELDS = {"title", "type"}


# ---------------------------------------------------------------------------
# JSON cleaning
# ---------------------------------------------------------------------------
def _clean_llm_json(raw: str) -> str:
    """
    Strip markdown fences, preamble, and postamble to isolate the JSON.

    LLMs frequently wrap output in ```json ... ``` or include
    conversational text around the actual object.
    """
    # Remove ```json ... ``` or ``` ... ``` wrappers
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = cleaned.strip()

    # Find outermost { ... } boundaries
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ItineraryParseError(
            "No JSON object found in LLM response. "
            "The model may have returned plain text instead of JSON."
        )

    return cleaned[start : end + 1]


# ---------------------------------------------------------------------------
# Default fillers
# ---------------------------------------------------------------------------
def _fill_item_defaults(item: dict, day_num: int) -> dict:
    """Fill missing optional fields with safe defaults."""
    item.setdefault("time_block", "Morning")
    item.setdefault("title", "Untitled Activity")
    item.setdefault("type", "activity")
    item.setdefault("description", "")
    item.setdefault("estimated_cost", 0)
    item.setdefault("location_name", item.get("title", "Unknown"))
    item.setdefault("latitude", 0.0)
    item.setdefault("longitude", 0.0)
    return item


def _fill_day_defaults(day: dict) -> dict:
    """Fill missing optional day-level fields."""
    day.setdefault("theme", f"Day {day.get('day_number', '?')}")
    day.setdefault("estimated_day_cost", 0)
    return day


def _fill_top_defaults(data: dict) -> dict:
    """Fill missing optional top-level fields."""
    data.setdefault("summary", "")
    data.setdefault("budget_level", "Moderate")
    data.setdefault("travel_style", [])
    data.setdefault("interests", [])
    data.setdefault("pace", "Balanced")
    return data


def _repair_json(s: str) -> str:
    """
    Attempt to fix common JSON errors produced by LLMs:
    - Trailing commas before } or ]
    - Missing commas between elements
    - Single quotes instead of double quotes (careful with apostrophes)
    """
    # Remove trailing commas: ,} or ,]
    s = re.sub(r",\s*([}\]])", r"\1", s)

    # Fix missing comma between }"  or ]"  (object/array end followed by new key)
    s = re.sub(r"(\})\s*(\{)", r"\1,\2", s)
    s = re.sub(r"(\])\s*(\{)", r"\1,\2", s)

    # Fix missing comma between "value"\n"key" patterns
    s = re.sub(r'(")\s*\n\s*(")', r'\1,\n\2', s)

    # Fix missing comma between number and "key" patterns
    s = re.sub(r'(\d)\s*\n\s*(")', r'\1,\n\2', s)

    return s


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def parse_itinerary(raw: str) -> dict:
    """
    Parse raw LLM text into a validated itinerary dict.

    Steps:
      1. Strip markdown fences and preamble.
      2. Parse JSON (with auto-repair on failure).
      3. Validate required structure.
      4. Fill safe defaults for missing optional fields.

    Raises
    ------
    ItineraryParseError — if the text isn't valid JSON.
    ItineraryValidationError — if required structure is missing.
    """
    json_str = _clean_llm_json(raw)

    # First attempt: parse as-is
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Second attempt: auto-repair common LLM errors
        try:
            repaired = _repair_json(json_str)
            data = json.loads(repaired)
        except json.JSONDecodeError as exc:
            raise ItineraryParseError(
                f"LLM returned invalid JSON: {exc}"
            ) from exc

    # --- Validate top-level fields ---
    missing = REQUIRED_TOP_LEVEL - set(data.keys())
    if missing:
        raise ItineraryValidationError(
            f"Itinerary missing required fields: {missing}"
        )

    if not isinstance(data["days"], list) or len(data["days"]) == 0:
        raise ItineraryValidationError(
            "Itinerary must contain at least one day."
        )

    # --- Validate and fill each day ---
    for i, day in enumerate(data["days"]):
        day_missing = REQUIRED_DAY_FIELDS - set(day.keys())
        if day_missing:
            raise ItineraryValidationError(
                f"Day {i + 1} missing required fields: {day_missing}"
            )

        if not isinstance(day["items"], list):
            raise ItineraryValidationError(
                f"Day {i + 1}: 'items' must be a list."
            )

        _fill_day_defaults(day)

        for j, item in enumerate(day["items"]):
            item_missing = REQUIRED_ITEM_FIELDS - set(item.keys())
            if item_missing:
                raise ItineraryValidationError(
                    f"Day {i + 1}, item {j + 1} missing: {item_missing}"
                )
            _fill_item_defaults(item, day.get("day_number", i + 1))

    _fill_top_defaults(data)

    return data
