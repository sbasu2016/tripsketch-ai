"""
test_validators.py — Tests for utils/validators.py

Covers: destination, trip length, budget, pace, interests,
notes character limit, and must-see character limit.
"""

from __future__ import annotations

import pytest
from utils.validators import (
    validate_destination, validate_trip_length, validate_budget_level,
    validate_pace, validate_interests, validate_notes, validate_must_see,
    validate_all, ValidationError,
    MAX_NOTES_CHARS, MAX_MUST_SEE_CHARS,
)


class TestValidateDestination:
    def test_valid(self):
        assert validate_destination("Kyoto, Japan") == "Kyoto, Japan"

    def test_strips_whitespace(self):
        assert validate_destination("  Tokyo  ") == "Tokyo"

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_destination("")

    def test_too_short_raises(self):
        with pytest.raises(ValidationError):
            validate_destination("X")

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_destination("A" * 101)


class TestValidateTripLength:
    def test_valid(self):
        assert validate_trip_length(4) == 4

    def test_min(self):
        assert validate_trip_length(1) == 1

    def test_max(self):
        assert validate_trip_length(14) == 14

    def test_zero_raises(self):
        with pytest.raises(ValidationError):
            validate_trip_length(0)

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_trip_length(15)


class TestValidateBudget:
    def test_valid(self):
        assert validate_budget_level("Moderate") == "Moderate"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            validate_budget_level("Super Cheap")


class TestValidatePace:
    def test_valid(self):
        assert validate_pace("Packed") == "Packed"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            validate_pace("Insane")


class TestValidateInterests:
    def test_valid(self):
        assert validate_interests(["Temples", "Markets"]) == ["Temples", "Markets"]

    def test_too_many_raises(self):
        with pytest.raises(ValidationError):
            validate_interests(["a", "b", "c", "d", "e", "f"])


class TestValidateNotes:
    def test_empty_ok(self):
        assert validate_notes("") == ""

    def test_normal_ok(self):
        notes = "We are vegan and want to see cherry blossoms"
        assert validate_notes(notes) == notes

    def test_at_limit_ok(self):
        notes = "x" * MAX_NOTES_CHARS
        assert validate_notes(notes) == notes

    def test_over_limit_raises(self):
        with pytest.raises(ValidationError, match="500"):
            validate_notes("x" * (MAX_NOTES_CHARS + 1))

    def test_way_over_limit_raises(self):
        with pytest.raises(ValidationError):
            validate_notes("x" * 2000)


class TestValidateMustSee:
    def test_empty_ok(self):
        assert validate_must_see("") == ""

    def test_normal_ok(self):
        places = "Fushimi Inari, Nishiki Market, Kinkaku-ji"
        assert validate_must_see(places) == places

    def test_at_limit_ok(self):
        places = "x" * MAX_MUST_SEE_CHARS
        assert validate_must_see(places) == places

    def test_over_limit_raises(self):
        with pytest.raises(ValidationError, match="200"):
            validate_must_see("x" * (MAX_MUST_SEE_CHARS + 1))


class TestValidateAll:
    def test_valid_inputs(self):
        result = validate_all("Kyoto", 4, "Moderate", "Balanced", ["Temples"])
        assert result["destination"] == "Kyoto"
        assert result["trip_length_days"] == 4

    def test_first_failure_raises(self):
        with pytest.raises(ValidationError):
            validate_all("", 4, "Moderate", "Balanced", [])


class TestCharLimitsConstants:
    """Verify the limits are set to expected values."""

    def test_notes_limit_is_500(self):
        assert MAX_NOTES_CHARS == 500

    def test_must_see_limit_is_200(self):
        assert MAX_MUST_SEE_CHARS == 200

    def test_notes_exactly_one_over_raises(self):
        """501 chars should fail."""
        with pytest.raises(ValidationError):
            validate_notes("a" * 501)

    def test_must_see_exactly_one_over_raises(self):
        """201 chars should fail."""
        with pytest.raises(ValidationError):
            validate_must_see("a" * 201)

    def test_notes_exactly_at_limit_passes(self):
        """500 chars should pass."""
        assert len(validate_notes("a" * 500)) == 500

    def test_must_see_exactly_at_limit_passes(self):
        """200 chars should pass."""
        assert len(validate_must_see("a" * 200)) == 200

    def test_notes_well_over_limit_raises(self):
        """1000 chars should fail — no max_chars on input anymore."""
        with pytest.raises(ValidationError):
            validate_notes("a" * 1000)

    def test_must_see_well_over_limit_raises(self):
        """500 chars should fail — no max_chars on input anymore."""
        with pytest.raises(ValidationError):
            validate_must_see("a" * 500)

    def test_notes_error_message_contains_count(self):
        """Error message should show the current character count."""
        try:
            validate_notes("a" * 600)
            assert False, "Should have raised"
        except ValidationError as e:
            assert "600" in str(e)
            assert "500" in str(e)


class TestCharCounterCSS:
    """Verify the CSS hides Streamlit's built-in counter."""

    def test_css_hides_input_instructions(self):
        with open("app.py") as f:
            content = f.read()
        assert "InputInstructions" in content
        assert "display: none" in content


class TestUIDefaults:
    """Verify destination has no pre-filled value and mock mode is hidden."""

    def test_no_prefilled_destination(self):
        """Destination should not have Kyoto or any pre-filled value."""
        with open("app.py") as f:
            content = f.read()
        # Should not have value="Kyoto, Japan" or any value= on destination
        assert 'value="Kyoto' not in content

    def test_mock_mode_not_visible(self):
        """Mock mode radio should not be shown to users."""
        with open("app.py") as f:
            content = f.read()
        assert '"mock", "claude"' not in content
        assert "Generation mode" not in content

    def test_mode_hardcoded_to_claude(self):
        """Mode should be hardcoded to claude."""
        with open("app.py") as f:
            content = f.read()
        assert 'mode = "claude"' in content

    def test_mock_mode_still_works_internally(self):
        """Mock mode should still work in llm_service for tests."""
        from services.itinerary_service import create_itinerary
        result = create_itinerary(
            destination="Tokyo",
            trip_length_days=1,
            budget_level="Budget",
            travel_style=[],
            interests=[],
            pace="Balanced",
            mode="mock",
        )
        assert result["destination"] == "Tokyo"
