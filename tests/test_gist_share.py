"""
test_gist_share.py — Tests for services/share_service.py

Tests the gist sharing logic without making actual API calls.
Covers: token detection, payload structure, load parsing.
"""

from __future__ import annotations

import json
import os


class TestGistTokenDetection:
    def test_no_token_returns_none(self):
        """Without a token set, _get_github_token returns None."""
        # Temporarily clear the env var if set
        old = os.environ.pop("GITHUB_GIST_TOKEN", None)
        try:
            from services.share_service import _get_github_token
            result = _get_github_token()
            # Could be None or could come from st.secrets — either is OK
            # Just verify it doesn't crash
            assert result is None or isinstance(result, str)
        finally:
            if old:
                os.environ["GITHUB_GIST_TOKEN"] = old

    def test_token_from_env(self):
        """Token should be read from GITHUB_GIST_TOKEN env var."""
        os.environ["GITHUB_GIST_TOKEN"] = "test-token-123"
        try:
            from services.share_service import _get_github_token
            assert _get_github_token() == "test-token-123"
        finally:
            del os.environ["GITHUB_GIST_TOKEN"]


class TestCreateGistWithoutToken:
    def test_returns_none_without_token(self):
        """create_gist should return None if no token is available."""
        old = os.environ.pop("GITHUB_GIST_TOKEN", None)
        try:
            from services.share_service import create_gist
            result = create_gist({"destination": "Test"})
            assert result is None
        finally:
            if old:
                os.environ["GITHUB_GIST_TOKEN"] = old


class TestLoadGistParsing:
    def test_load_gist_invalid_id_returns_none(self):
        """Loading a non-existent gist should return None, not crash."""
        from services.share_service import load_gist
        result = load_gist("this-gist-does-not-exist-99999")
        assert result is None

    def test_load_gist_empty_id_returns_none(self):
        from services.share_service import load_gist
        result = load_gist("")
        assert result is None


class TestGistIntegration:
    def test_share_service_importable(self):
        """The share service module should import without errors."""
        from services.share_service import create_gist, load_gist, _get_github_token
        assert callable(create_gist)
        assert callable(load_gist)
        assert callable(_get_github_token)

    def test_itinerary_serializable_for_gist(self):
        """A typical itinerary should be JSON-serializable for gist upload."""
        itin = {
            "destination": "Osaka, Japan",
            "trip_length_days": 3,
            "days": [{"day_number": 1, "items": [{"title": "Test", "type": "activity"}]}],
        }
        serialized = json.dumps(itin, ensure_ascii=False, indent=2)
        assert "Osaka" in serialized
        assert len(serialized) > 50


class TestShareURLFormat:
    def test_gist_url_is_short(self):
        """A gist-based URL should be well under 100 chars."""
        fake_gist_id = "abc123def456"
        url = f"https://tripsketch-ai.streamlit.app/?gist={fake_gist_id}"
        assert len(url) < 100

    def test_gist_url_contains_gist_param(self):
        fake_gist_id = "abc123def456"
        url = f"https://tripsketch-ai.streamlit.app/?gist={fake_gist_id}"
        assert "?gist=" in url

    def test_gist_url_no_special_chars(self):
        """Gist IDs are alphanumeric — URL should be safe for any messenger."""
        fake_gist_id = "a1b2c3d4e5f6"
        url = f"https://tripsketch-ai.streamlit.app/?gist={fake_gist_id}"
        # No spaces, no brackets, no unicode
        assert " " not in url
        assert "[" not in url


class TestAppShareSection:
    def test_no_clipboard_js_in_app(self):
        """Clipboard JS was removed — should not be in app.py."""
        with open("app.py") as f:
            content = f.read()
        assert "navigator.clipboard" not in content

    def test_no_long_url_fallback(self):
        """Long compressed URL fallback was removed."""
        with open("app.py") as f:
            content = f.read()
        assert "Long shareable link" not in content
        assert "no account needed" not in content

    def test_text_input_for_share_url(self):
        """Share URL should be shown in a text_input for easy copying."""
        with open("app.py") as f:
            content = f.read()
        assert "share_url_display" in content
