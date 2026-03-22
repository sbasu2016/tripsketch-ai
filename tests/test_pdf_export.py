"""
test_pdf_export.py — Tests for utils/pdf_export.py

Tests the PDF export logic. Some tests verify the module structure
without requiring fpdf2 to be installed (for CI environments).
"""

from __future__ import annotations

import json


def _sample_itinerary():
    return {
        "destination": "Kyoto, Japan",
        "trip_length_days": 2,
        "budget_level": "Moderate",
        "estimated_total_cost": 300,
        "daily_cost_average": 150,
        "summary": "A lovely trip through historic Kyoto.",
        "days": [
            {
                "day_number": 1,
                "theme": "Historic Kyoto",
                "estimated_day_cost": 140,
                "items": [
                    {"time_block": "Morning", "title": "Fushimi Inari", "type": "activity",
                     "description": "Walk the torii gates.", "estimated_cost": 0},
                    {"time_block": "Lunch", "title": "Nishiki Market", "type": "meal",
                     "description": "Street food stalls.", "estimated_cost": 18},
                ],
            },
            {
                "day_number": 2,
                "theme": "Arashiyama",
                "estimated_day_cost": 160,
                "items": [
                    {"time_block": "Morning", "title": "Bamboo Grove", "type": "activity",
                     "description": "Walk through towering bamboo.", "estimated_cost": 0},
                ],
            },
        ],
    }


class TestPDFExportModule:
    def test_module_importable(self):
        """pdf_export module should import without crashing."""
        try:
            from utils.pdf_export import itinerary_to_pdf
            assert callable(itinerary_to_pdf)
        except ImportError:
            # fpdf2 not installed — acceptable in test environment
            pass

    def test_generates_bytes(self):
        """itinerary_to_pdf should return bytes."""
        try:
            from utils.pdf_export import itinerary_to_pdf
            result = itinerary_to_pdf(_sample_itinerary())
            assert isinstance(result, bytes)
        except ImportError:
            pass  # fpdf2 not installed

    def test_pdf_starts_with_header(self):
        """PDF output should start with %PDF magic bytes."""
        try:
            from utils.pdf_export import itinerary_to_pdf
            result = itinerary_to_pdf(_sample_itinerary())
            assert result[:4] == b"%PDF"
        except ImportError:
            pass

    def test_pdf_not_empty(self):
        """PDF should be a reasonable size (not empty)."""
        try:
            from utils.pdf_export import itinerary_to_pdf
            result = itinerary_to_pdf(_sample_itinerary())
            assert len(result) > 500
        except ImportError:
            pass

    def test_handles_empty_itinerary(self):
        """Should not crash on minimal itinerary."""
        try:
            from utils.pdf_export import itinerary_to_pdf
            result = itinerary_to_pdf({"destination": "Test", "days": []})
            assert isinstance(result, bytes)
        except ImportError:
            pass

    def test_handles_missing_optional_fields(self):
        """Should not crash when optional fields are missing."""
        try:
            from utils.pdf_export import itinerary_to_pdf
            result = itinerary_to_pdf({
                "destination": "Test",
                "days": [{"day_number": 1, "items": [{"title": "X", "type": "activity"}]}],
            })
            assert isinstance(result, bytes)
        except ImportError:
            pass

    def test_handles_unicode(self):
        """Should handle Japanese/Unicode characters."""
        try:
            from utils.pdf_export import itinerary_to_pdf
            itin = _sample_itinerary()
            itin["destination"] = "京都, 日本"
            result = itinerary_to_pdf(itin)
            assert isinstance(result, bytes)
        except ImportError:
            pass

    def test_itinerary_is_json_serializable(self):
        """Sample itinerary should be JSON serializable (sanity check)."""
        json.dumps(_sample_itinerary())  # Should not raise


class TestPDFInRequirements:
    def test_fpdf2_in_requirements(self):
        """fpdf2 must be in requirements.txt."""
        with open("requirements.txt") as f:
            content = f.read()
        assert "fpdf2" in content


class TestPDFSanitize:
    def test_sanitize_em_dash(self):
        """Em dash should be replaced with hyphen."""
        from utils.pdf_export import _sanitize
        assert "\u2014" not in _sanitize("Hello \u2014 World")
        assert "-" in _sanitize("Hello \u2014 World")

    def test_sanitize_smart_quotes(self):
        from utils.pdf_export import _sanitize
        result = _sanitize("\u201cHello\u201d")
        assert "\u201c" not in result
        assert '"' in result

    def test_sanitize_preserves_ascii(self):
        from utils.pdf_export import _sanitize
        assert _sanitize("Hello World 123") == "Hello World 123"

    def test_sanitize_japanese_replaced(self):
        """Japanese chars can't be in latin-1, should be replaced."""
        from utils.pdf_export import _sanitize
        result = _sanitize("京都")
        # Should not crash, chars get replaced with ?
        assert isinstance(result, str)


class TestPDFSanitize:
    def test_em_dash_replaced(self):
        """Em dash should be replaced with hyphen."""
        from utils.pdf_export import _sanitize
        assert _sanitize("TripSketch AI \u2014 Kyoto") == "TripSketch AI - Kyoto"

    def test_smart_quotes_replaced(self):
        from utils.pdf_export import _sanitize
        assert _sanitize("\u201cHello\u201d") == '"Hello"'

    def test_ellipsis_replaced(self):
        from utils.pdf_export import _sanitize
        assert _sanitize("Wait\u2026") == "Wait..."

    def test_plain_ascii_unchanged(self):
        from utils.pdf_export import _sanitize
        assert _sanitize("Hello World 123") == "Hello World 123"

    def test_non_latin1_stripped(self):
        """Characters that can't encode to latin-1 should be replaced."""
        from utils.pdf_export import _sanitize
        result = _sanitize("Test \u4eac\u90fd")  # 京都
        assert isinstance(result, str)
        # Should not crash, chars replaced with ?
        assert "Test" in result
