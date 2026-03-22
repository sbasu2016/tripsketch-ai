"""
url_compress.py — Compress and decompress itineraries for share URLs.

Strategy for shorter URLs:
1. Strip heavy fields (descriptions, coordinates, place_info) that
   aren't essential for viewing a shared itinerary summary.
2. Minify JSON keys to 1-2 char abbreviations.
3. Compress with zlib level 9 and base64url encode.

The shared view shows titles, types, costs, time blocks, day themes,
and trip metadata. The map won't render (no coordinates) but all the
itinerary content is there.
"""

from __future__ import annotations

import json
import zlib
import base64


# Key mappings: full key -> short key
_MINIFY = {
    "destination": "d",
    "trip_length_days": "tl",
    "budget_level": "bl",
    "travel_style": "ts",
    "interests": "it",
    "pace": "pc",
    "summary": "sm",
    "estimated_total_cost": "tc",
    "daily_cost_average": "da",
    "days": "dy",
    "day_number": "dn",
    "theme": "th",
    "estimated_day_cost": "dc",
    "items": "im",
    "time_block": "tb",
    "title": "t",
    "type": "tp",
    "estimated_cost": "c",
    "location_name": "ln",
}

# Reverse mapping: short key -> full key
_EXPAND = {v: k for k, v in _MINIFY.items()}

# Fields to strip from items (heavy, not needed for shared summary)
_STRIP_ITEM_FIELDS = {
    "description", "latitude", "longitude", "place_info",
}

# Fields to strip from top level
_STRIP_TOP_FIELDS = {
    "place_info",
}


def _minify_key(key: str) -> str:
    return _MINIFY.get(key, key)


def _expand_key(key: str) -> str:
    return _EXPAND.get(key, key)


def compress_itinerary(itinerary: dict) -> str:
    """
    Compress an itinerary dict into a URL-safe string.

    Strips heavy fields and minifies keys for maximum compression.
    Returns a base64url-encoded string.
    """
    # Build a lightweight copy
    mini = {}
    for k, v in itinerary.items():
        if k in _STRIP_TOP_FIELDS:
            continue
        if k == "days":
            mini_days = []
            for day in v:
                mini_day = {}
                for dk, dv in day.items():
                    if dk == "items":
                        mini_items = []
                        for item in dv:
                            mini_item = {}
                            for ik, iv in item.items():
                                if ik not in _STRIP_ITEM_FIELDS:
                                    mini_item[_minify_key(ik)] = iv
                            mini_items.append(mini_item)
                        mini_day[_minify_key(dk)] = mini_items
                    else:
                        mini_day[_minify_key(dk)] = dv
                mini_days.append(mini_day)
            mini[_minify_key(k)] = mini_days
        else:
            mini[_minify_key(k)] = v

    raw = json.dumps(mini, ensure_ascii=False, separators=(",", ":"))
    compressed = zlib.compress(raw.encode("utf-8"), level=9)
    return base64.urlsafe_b64encode(compressed).decode("ascii")


def decompress_itinerary(encoded: str) -> dict:
    """
    Decompress a URL-safe string back into an itinerary dict.

    Expands minified keys and fills defaults for stripped fields.
    """
    compressed = base64.urlsafe_b64decode(encoded)
    raw = zlib.decompress(compressed).decode("utf-8")
    mini = json.loads(raw)

    # Expand top-level keys
    expanded = {}
    for k, v in mini.items():
        full_key = _expand_key(k)
        if full_key == "days":
            exp_days = []
            for day in v:
                exp_day = {}
                for dk, dv in day.items():
                    full_dk = _expand_key(dk)
                    if full_dk == "items":
                        exp_items = []
                        for item in dv:
                            exp_item = {}
                            for ik, iv in item.items():
                                exp_item[_expand_key(ik)] = iv
                            # Fill defaults for stripped fields
                            exp_item.setdefault("description", "")
                            exp_item.setdefault("latitude", 0.0)
                            exp_item.setdefault("longitude", 0.0)
                            exp_item.setdefault("location_name",
                                                exp_item.get("title", ""))
                            exp_items.append(exp_item)
                        exp_day[full_dk] = exp_items
                    else:
                        exp_day[full_dk] = dv
                exp_days.append(exp_day)
            expanded[full_key] = exp_days
        else:
            expanded[full_key] = v

    return expanded
