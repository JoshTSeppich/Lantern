"""Tests for lantern.vocab — state bitmap, role and landmark vocabularies."""

from __future__ import annotations

import pytest

from lantern import vocab
from lantern.vocab import StateBit


class TestStateBitmapPositions:
    """Per contracts(state-bitmap) freeze bcb2b8d — bit positions pinned."""

    def test_canonical_names_count_is_8(self):
        assert len(vocab.STATE_FIELD_NAMES) == 8

    def test_canonical_names_are_all_lowercase(self):
        for name in vocab.STATE_FIELD_NAMES:
            assert name == name.lower()

    def test_all_8_canonical_names_present(self):
        assert vocab.STATE_FIELD_NAMES == frozenset({
            "expanded", "haspopup", "selected", "checked",
            "disabled", "required", "invalid", "readonly",
        })

    def test_bit_positions_pinned(self):
        assert int(StateBit.EXPANDED) == 1
        assert int(StateBit.HASPOPUP) == 2
        assert int(StateBit.SELECTED) == 4
        assert int(StateBit.CHECKED)  == 8
        assert int(StateBit.DISABLED) == 16
        assert int(StateBit.REQUIRED) == 32
        assert int(StateBit.INVALID)  == 64
        assert int(StateBit.READONLY) == 128


class TestNormalizeAxPropertyName:
    """ADR 0004 — lowercase-on-ingest for CDP property names."""

    @pytest.mark.parametrize("cdp_name,expected", [
        # Exact lowercase matches — all 7 fields that L-SPIKE-02 verified lowercase
        ("expanded", "expanded"),
        ("selected", "selected"),
        ("checked",  "checked"),
        ("disabled", "disabled"),
        ("required", "required"),
        ("invalid",  "invalid"),
        ("readonly", "readonly"),
        # L-SPIKE-02 mismatch — CDP returns hasPopup (camelCase); ADR 0004 Option A normalizes
        ("hasPopup", "haspopup"),
        ("haspopup", "haspopup"),
        # Defensive cases: varied casing
        ("EXPANDED", "expanded"),
        ("HasPopup", "haspopup"),
        ("ChEcKeD",  "checked"),
        # Non-bitmap CDP properties → None
        ("focusable",    None),
        ("keyshortcuts", None),
        ("atomic",       None),
        ("",             None),
    ])
    def test_normalize_cases(self, cdp_name: str, expected: str | None):
        assert vocab.normalize_ax_property_name(cdp_name) == expected


class TestCollapseStateValue:
    """L-SPIKE-02 secondary observation — CDP returns booleans, tristate tokens, or string values."""

    @pytest.mark.parametrize("value,expected", [
        (True,          True),
        (False,         False),
        ("true",        True),
        ("false",       False),
        ("mixed",       True),     # tristate — checkbox indeterminate
        ("menu",        True),     # token — aria-haspopup="menu"
        ("listbox",     True),     # token — aria-haspopup="listbox"
        ("",            False),
        (None,          False),
        ("undefined",   False),
        ("0",           False),
        (1,             True),
        (0,             False),
    ])
    def test_collapse_cases(self, value: object, expected: bool):
        assert vocab.collapse_state_value(value) is expected


class TestPropertiesToBitmap:
    def test_empty_dict_is_zero(self):
        assert vocab.properties_to_bitmap({}) == 0

    def test_unknown_keys_ignored(self):
        assert vocab.properties_to_bitmap({
            "focusable": True,
            "keyshortcuts": "Ctrl+S",
            "atomic": False,
        }) == 0

    def test_single_field_sets_correct_bit(self):
        assert vocab.properties_to_bitmap({"expanded": True}) == int(StateBit.EXPANDED)
        assert vocab.properties_to_bitmap({"disabled": True}) == int(StateBit.DISABLED)

    def test_haspopup_camelcase_normalizes(self):
        """L-SPIKE-02 regression: CDP's hasPopup must set the haspopup bit."""
        assert vocab.properties_to_bitmap({"hasPopup": "menu"}) == int(StateBit.HASPOPUP)

    def test_tristate_checked_collapses_to_true(self):
        """L-SPIKE-02 observation: <input checked> → CDP checked='true' (string, not bool)."""
        assert vocab.properties_to_bitmap({"checked": "true"}) == int(StateBit.CHECKED)

    def test_invalid_tristate_collapses(self):
        """L-SPIKE-02 observation: aria-invalid='true' → CDP invalid='true' (string)."""
        assert vocab.properties_to_bitmap({"invalid": "true"}) == int(StateBit.INVALID)

    def test_false_value_clears_bit(self):
        assert vocab.properties_to_bitmap({"expanded": False}) == 0
        assert vocab.properties_to_bitmap({"checked": "false"}) == 0

    def test_all_8_bits_set(self):
        props = {
            "expanded": True,
            "hasPopup": "menu",     # camelCase — must normalize
            "selected": True,
            "checked":  "true",     # tristate string — must collapse
            "disabled": True,
            "required": True,
            "invalid":  "true",     # tristate string — must collapse
            "readonly": True,
        }
        expected = (
            int(StateBit.EXPANDED) | int(StateBit.HASPOPUP) | int(StateBit.SELECTED)
            | int(StateBit.CHECKED) | int(StateBit.DISABLED) | int(StateBit.REQUIRED)
            | int(StateBit.INVALID) | int(StateBit.READONLY)
        )
        assert vocab.properties_to_bitmap(props) == expected

    def test_mixed_bits_independent(self):
        # expanded + disabled, nothing else
        expected = int(StateBit.EXPANDED) | int(StateBit.DISABLED)
        assert vocab.properties_to_bitmap({"expanded": True, "disabled": True}) == expected


class TestLandmarkMapping:
    """L-SPIKE-02 Claim B — AX role → HTML-tag landmark mapping."""

    @pytest.mark.parametrize("ax_role,html_tag", [
        ("main",          "main"),
        ("navigation",    "nav"),
        ("banner",        "header"),
        ("contentinfo",   "footer"),
        ("complementary", "aside"),
    ])
    def test_all_5_mappings(self, ax_role: str, html_tag: str):
        assert vocab.ax_role_to_landmark(ax_role) == html_tag

    def test_non_landmark_role_is_none(self):
        assert vocab.ax_role_to_landmark("button") is None
        assert vocab.ax_role_to_landmark("link") is None
        assert vocab.ax_role_to_landmark("") is None
        assert vocab.ax_role_to_landmark("region") is None   # region is a landmark in ARIA, but not in LANTERN's 5-tag vocabulary

    def test_landmark_vocabulary_is_6_tags(self):
        # 5 HTML landmarks + 'none'
        assert vocab.LANDMARKS == frozenset({"main", "nav", "header", "footer", "aside", "none"})
        assert vocab.LANDMARK_NONE == "none"


class TestRoleVocabulary:
    """WAI-ARIA 1.2 role vocabulary. Part 4 Step 1: unknown → 'generic'."""

    def test_common_widget_roles_present(self):
        for role in ("button", "link", "textbox", "checkbox", "tab", "menuitem",
                     "combobox", "slider", "radio"):
            assert role in vocab.ROLES

    def test_landmark_roles_present(self):
        for role in ("main", "navigation", "banner", "contentinfo", "complementary"):
            assert role in vocab.ROLES

    def test_generic_constant(self):
        assert vocab.ROLE_GENERIC == "generic"
        assert "generic" in vocab.ROLES

    def test_normalize_known_role_returns_self(self):
        assert vocab.normalize_role("button") == "button"
        assert vocab.normalize_role("textbox") == "textbox"

    def test_normalize_unknown_role_returns_generic(self):
        assert vocab.normalize_role("my-custom-role") == "generic"
        assert vocab.normalize_role("widget") == "generic"

    def test_normalize_none_returns_generic(self):
        assert vocab.normalize_role(None) == "generic"
