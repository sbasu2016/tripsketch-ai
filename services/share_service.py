"""
share_service.py — Share itineraries via GitHub Gist for short URLs.

Creates a secret gist with the itinerary JSON and returns the gist ID.
The app can then load the itinerary from ?gist=<id> query param.
"""

from __future__ import annotations

import json
import os


def _get_github_token() -> str | None:
    """Get GitHub token from env or Streamlit secrets."""
    token = os.getenv("GITHUB_GIST_TOKEN")
    if not token:
        try:
            import streamlit as st
            token = st.secrets.get("GITHUB_GIST_TOKEN")
        except Exception:
            pass
    return token


def create_gist(itinerary: dict) -> str | None:
    """
    Create a secret GitHub Gist with the itinerary JSON.

    Returns the gist ID (short string like 'abc123def456') or None on failure.
    """
    import urllib.request
    import urllib.error

    token = _get_github_token()
    if not token:
        return None

    dest = itinerary.get("destination", "trip")
    payload = json.dumps({
        "description": f"TripSketch AI — {dest}",
        "public": False,
        "files": {
            "tripsketch_itinerary.json": {
                "content": json.dumps(itinerary, ensure_ascii=False, indent=2),
            }
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.github.com/gists",
        data=payload,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "TripSketch-AI",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("id")
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        return None


def load_gist(gist_id: str) -> dict | None:
    """
    Load an itinerary from a GitHub Gist by ID.

    Returns the parsed itinerary dict or None on failure.
    """
    import urllib.request
    import urllib.error

    url = f"https://api.github.com/gists/{gist_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TripSketch-AI",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            files = data.get("files", {})
            content = None
            for file_info in files.values():
                content = file_info.get("content")
                break
            if content:
                return json.loads(content)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, Exception):
        pass

    return None
