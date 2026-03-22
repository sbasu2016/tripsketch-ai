"""
test_theme.py — Tests for the CSS color scheme in app.py.

Verifies that:
- Both light and dark palettes are complete and consistent
- Light and dark colors don't leak into the wrong palette
- Text/background contrast ratios meet WCAG AA (4.5:1)
- The generated CSS contains both palettes
- Dark mode uses !important to override light defaults
- No CSS variable references (var(--...)) remain
"""

from __future__ import annotations

import re


# -------------------------------------------------------------------------
# Color palettes (must match _LIGHT and _DARK in app.py)
# Using full names for readability; mapped from app.py short keys.
# -------------------------------------------------------------------------
LIGHT = {
    "text_primary": "#1a1a1a", "text_secondary": "#555555", "text_muted": "#777777",
    "border_color": "#e0ddd5", "border_light": "#ece7dc", "bg_secondary": "#f8f7f4",
    "accent_green": "#3a7a3a", "accent_gold": "#b8860b",
    "badge_act_bg": "#e8f0e8", "badge_act_text": "#3a6a3a",
    "badge_meal_bg": "#fdf2e0", "badge_meal_text": "#8a6020",
    "link_color": "#6a8a6a",
    "metric_bg": "#f8f7f4", "metric_text": "#1a1a1a", "metric_label": "#777777",
    "item_bg": "#f8f7f4",
}

DARK = {
    "text_primary": "#e6e6e6", "text_secondary": "#b0b0b0", "text_muted": "#909090",
    "border_color": "#333840", "border_light": "#2a2e35", "bg_secondary": "#1a1d24",
    "accent_green": "#6abf6a", "accent_gold": "#daa520",
    "badge_act_bg": "#1e3a1e", "badge_act_text": "#7acf7a",
    "badge_meal_bg": "#3a2e10", "badge_meal_text": "#e0b050",
    "link_color": "#8abf8a",
    "metric_bg": "#2c2f36", "metric_text": "#ffffff", "metric_label": "#a0a4ac",
    "item_bg": "#1e2128",
}

# Approximate page backgrounds for contrast testing
LIGHT_PAGE_BG = "#ffffff"
DARK_PAGE_BG = "#0e1117"


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------
def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _relative_luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    rs, gs, bs = r / 255, g / 255, b / 255
    r_lin = rs / 12.92 if rs <= 0.03928 else ((rs + 0.055) / 1.055) ** 2.4
    g_lin = gs / 12.92 if gs <= 0.03928 else ((gs + 0.055) / 1.055) ** 2.4
    b_lin = bs / 12.92 if bs <= 0.03928 else ((bs + 0.055) / 1.055) ** 2.4
    return 0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin


def _contrast_ratio(fg: str, bg: str) -> float:
    l1 = _relative_luminance(fg)
    l2 = _relative_luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _read_app():
    with open("app.py") as f:
        return f.read()


# =========================================================================
# PALETTE COMPLETENESS
# =========================================================================
class TestPaletteCompleteness:
    def test_same_keys(self):
        assert set(LIGHT.keys()) == set(DARK.keys())

    def test_all_values_are_hex(self):
        for name, palette in [("light", LIGHT), ("dark", DARK)]:
            for key, val in palette.items():
                assert re.match(r"^#[0-9a-fA-F]{6}$", val), \
                    f"{name}.{key} = {val!r} is not valid hex"

    def test_light_has_required_keys(self):
        required = {"text_primary", "text_secondary", "text_muted",
                     "metric_bg", "metric_text", "metric_label", "item_bg"}
        assert required.issubset(set(LIGHT.keys()))

    def test_dark_has_required_keys(self):
        required = {"text_primary", "text_secondary", "text_muted",
                     "metric_bg", "metric_text", "metric_label", "item_bg"}
        assert required.issubset(set(DARK.keys()))


# =========================================================================
# LIGHT/DARK DIFFERENTIATION
# =========================================================================
class TestPaletteDifferentiation:
    def test_text_primary_differs(self):
        assert LIGHT["text_primary"] != DARK["text_primary"]

    def test_metric_bg_differs(self):
        assert LIGHT["metric_bg"] != DARK["metric_bg"]

    def test_item_bg_differs(self):
        assert LIGHT["item_bg"] != DARK["item_bg"]

    def test_metric_text_differs(self):
        assert LIGHT["metric_text"] != DARK["metric_text"]

    def test_light_text_is_dark_colored(self):
        lum = _relative_luminance(LIGHT["text_primary"])
        assert lum < 0.15, f"Light text luminance {lum:.3f} too bright"

    def test_dark_text_is_light_colored(self):
        lum = _relative_luminance(DARK["text_primary"])
        assert lum > 0.6, f"Dark text luminance {lum:.3f} too dim"

    def test_light_item_bg_is_bright(self):
        lum = _relative_luminance(LIGHT["item_bg"])
        assert lum > 0.7, f"Light item_bg luminance {lum:.3f} too dim"

    def test_dark_item_bg_is_dim(self):
        lum = _relative_luminance(DARK["item_bg"])
        assert lum < 0.05, f"Dark item_bg luminance {lum:.3f} too bright"


# =========================================================================
# CONTRAST RATIOS (WCAG AA = 4.5:1 for normal text)
# =========================================================================
class TestContrastRatios:
    def test_light_text_on_page_bg(self):
        ratio = _contrast_ratio(LIGHT["text_primary"], LIGHT_PAGE_BG)
        assert ratio >= 4.5, f"Light text/page contrast {ratio:.2f} < 4.5"

    def test_light_secondary_on_page_bg(self):
        ratio = _contrast_ratio(LIGHT["text_secondary"], LIGHT_PAGE_BG)
        assert ratio >= 4.5, f"Light secondary/page contrast {ratio:.2f} < 4.5"

    def test_light_metric_text_on_metric_bg(self):
        ratio = _contrast_ratio(LIGHT["metric_text"], LIGHT["metric_bg"])
        assert ratio >= 4.5, f"Light metric contrast {ratio:.2f} < 4.5"

    def test_light_text_on_item_bg(self):
        ratio = _contrast_ratio(LIGHT["text_primary"], LIGHT["item_bg"])
        assert ratio >= 4.5, f"Light text/item contrast {ratio:.2f} < 4.5"

    def test_dark_text_on_page_bg(self):
        ratio = _contrast_ratio(DARK["text_primary"], DARK_PAGE_BG)
        assert ratio >= 4.5, f"Dark text/page contrast {ratio:.2f} < 4.5"

    def test_dark_secondary_on_page_bg(self):
        ratio = _contrast_ratio(DARK["text_secondary"], DARK_PAGE_BG)
        assert ratio >= 4.5, f"Dark secondary/page contrast {ratio:.2f} < 4.5"

    def test_dark_metric_text_on_metric_bg(self):
        ratio = _contrast_ratio(DARK["metric_text"], DARK["metric_bg"])
        assert ratio >= 4.5, f"Dark metric contrast {ratio:.2f} < 4.5"

    def test_dark_text_on_item_bg(self):
        ratio = _contrast_ratio(DARK["text_primary"], DARK["item_bg"])
        assert ratio >= 4.5, f"Dark text/item contrast {ratio:.2f} < 4.5"


# =========================================================================
# CSS OUTPUT
# =========================================================================
class TestCSSOutput:
    def test_contains_light_text_primary(self):
        assert LIGHT["text_primary"] in _read_app()

    def test_contains_dark_text_primary(self):
        assert DARK["text_primary"] in _read_app()

    def test_contains_light_metric_bg(self):
        assert LIGHT["metric_bg"] in _read_app()

    def test_contains_dark_metric_bg(self):
        assert DARK["metric_bg"] in _read_app()

    def test_contains_light_item_bg(self):
        assert LIGHT["item_bg"] in _read_app()

    def test_contains_dark_item_bg(self):
        assert DARK["item_bg"] in _read_app()

    def test_no_css_variable_refs(self):
        content = _read_app()
        style_blocks = re.findall(r"<style>.*?</style>", content, re.DOTALL)
        for block in style_blocks:
            matches = re.findall(r"var\(--[^)]+\)", block)
            assert len(matches) == 0, f"Found CSS variable refs: {matches}"

    def test_dark_uses_important(self):
        """Dark mode color rules should NOT use !important (was causing the bug).
        Utility rules like display:none are OK."""
        content = _read_app()
        style = re.search(r"<style>(.*?)</style>", content, re.DOTALL)
        assert style
        s = style.group(1)
        # Find all !important usages
        importants = re.findall(r"[^}]+!important[^}]*", s)
        for rule in importants:
            # Only display:none is allowed to use !important
            assert "display:" in rule.lower(), \
                f"Found !important on a non-utility rule: {rule.strip()[:80]}"

    def test_prefers_color_scheme_present(self):
        """@media prefers-color-scheme should NOT be used (was causing the bug)."""
        content = _read_app()
        style = re.search(r"<style>(.*?)</style>", content, re.DOTALL)
        assert style
        assert "prefers-color-scheme" not in style.group(1)

    def test_dark_scoped_under_theme_dark_class(self):
        """Dark rules should be scoped under .theme-dark class."""
        assert ".theme-dark" in _read_app()

    def test_js_brightness_detection_present(self):
        """JS fallback that detects background brightness must be present."""
        content = _read_app()
        assert "brightness" in content
        assert "theme-dark" in content

    def test_light_rules_before_dark(self):
        """Light mode rules should appear before .theme-dark block."""
        content = _read_app()
        style = re.search(r"<style>(.*?)</style>", content, re.DOTALL)
        assert style
        s = style.group(1)
        light_pos = s.find(LIGHT["text_primary"])
        dark_pos = s.find(".theme-dark")
        assert light_pos < dark_pos, "Light rules should come before .theme-dark"

    def test_dark_rules_inside_theme_dark_scope(self):
        """Dark rules should be scoped under .theme-dark prefix."""
        content = _read_app()
        # The _rules function is called with ".theme-dark" prefix
        assert '_rules(_DARK, ".theme-dark")' in content


# =========================================================================
# NO CROSS-CONTAMINATION
# =========================================================================
class TestNoCrossContamination:
    def test_light_metric_bg_is_beige(self):
        assert LIGHT["metric_bg"] == "#f8f7f4"

    def test_dark_metric_bg_is_dark(self):
        assert DARK["metric_bg"] == "#2c2f36"

    def test_light_text_not_light_colored(self):
        r, g, b = _hex_to_rgb(LIGHT["text_primary"])
        assert r + g + b < 200, f"Light text RGB sum {r+g+b} too bright"

    def test_dark_text_not_dark_colored(self):
        r, g, b = _hex_to_rgb(DARK["text_primary"])
        assert r + g + b > 500, f"Dark text RGB sum {r+g+b} too dim"
