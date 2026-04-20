"""
lantern/vocab.py — WAI-ARIA roles, landmarks, state bitmap, and normalization boundary.

Per LANTERN.md Part 4 Step 1 and ADR 0004 (state-bitmap normalization).
This module is the single normalization boundary between CDP AX-tree
output and Lantern's canonical vocabulary — AX property-name casing
drift and CDP tristate/token value shapes both collapse here.
"""

from __future__ import annotations

from enum import IntFlag
from typing import Final


# ---------------------------------------------------------------------
# State bitmap (Part 4 Step 1, bit positions frozen at bcb2b8d)
# ---------------------------------------------------------------------

class StateBit(IntFlag):
    EXPANDED = 1 << 0
    HASPOPUP = 1 << 1
    SELECTED = 1 << 2
    CHECKED  = 1 << 3
    DISABLED = 1 << 4
    REQUIRED = 1 << 5
    INVALID  = 1 << 6
    READONLY = 1 << 7


_STATE_BITS: Final[dict[str, StateBit]] = {
    "expanded": StateBit.EXPANDED,
    "haspopup": StateBit.HASPOPUP,
    "selected": StateBit.SELECTED,
    "checked":  StateBit.CHECKED,
    "disabled": StateBit.DISABLED,
    "required": StateBit.REQUIRED,
    "invalid":  StateBit.INVALID,
    "readonly": StateBit.READONLY,
}

STATE_FIELD_NAMES: Final[frozenset[str]] = frozenset(_STATE_BITS.keys())


# ---------------------------------------------------------------------
# Landmark vocabulary (Part 4 Step 1)
# AX-role → HTML-tag mapping verified by L-SPIKE-02 Claim B.
# ---------------------------------------------------------------------

LANDMARK_NONE: Final[str] = "none"
LANDMARKS: Final[frozenset[str]] = frozenset({
    "main", "nav", "header", "footer", "aside", LANDMARK_NONE,
})

_AX_ROLE_TO_LANDMARK: Final[dict[str, str]] = {
    "main":          "main",
    "navigation":    "nav",
    "banner":        "header",
    "contentinfo":   "footer",
    "complementary": "aside",
}


# ---------------------------------------------------------------------
# Role vocabulary (WAI-ARIA 1.2 — concrete roles only)
# ---------------------------------------------------------------------

ROLE_GENERIC: Final[str] = "generic"

ROLES: Final[frozenset[str]] = frozenset({
    # Document structure
    "application", "article", "blockquote", "caption", "cell", "columnheader",
    "definition", "deletion", "directory", "document", "emphasis", "feed",
    "figure", "generic", "group", "heading", "img", "insertion", "list",
    "listitem", "math", "meter", "none", "note", "paragraph", "presentation",
    "row", "rowgroup", "rowheader", "separator", "strong", "subscript",
    "superscript", "table", "term", "time", "toolbar", "tooltip",
    # Widgets
    "button", "checkbox", "gridcell", "link", "menuitem", "menuitemcheckbox",
    "menuitemradio", "option", "progressbar", "radio", "scrollbar",
    "searchbox", "slider", "spinbutton", "switch", "tab", "tabpanel",
    "textbox", "treeitem",
    # Composite widgets
    "combobox", "grid", "listbox", "menu", "menubar", "radiogroup",
    "tablist", "tree", "treegrid",
    # Landmarks
    "banner", "complementary", "contentinfo", "form", "main", "navigation",
    "region", "search",
    # Live regions
    "alert", "log", "marquee", "status", "timer",
    # Window
    "alertdialog", "dialog",
})


# ---------------------------------------------------------------------
# Normalization functions
# ---------------------------------------------------------------------

_FALSY_STRINGS: Final[frozenset[str]] = frozenset({"", "false", "undefined", "0"})


def normalize_ax_property_name(cdp_name: str) -> str | None:
    """Map a CDP AX property name to its canonical lowercase state-bitmap field
    name, or None if the property is not one of the 8 bitmap fields (ADR 0004).
    """
    lowered = cdp_name.lower()
    return lowered if lowered in STATE_FIELD_NAMES else None


def collapse_state_value(cdp_value: object) -> bool:
    """Truthiness-collapse a CDP AX property value to a 0/1 bit (L-SPIKE-02).

    Booleans pass through. Strings: falsy set ({'', 'false', 'undefined', '0'})
    → False; any other string → True (covers 'true', 'mixed', tokens like 'menu').
    None → False. Numeric values: bool(value).
    """
    if cdp_value is None:
        return False
    if isinstance(cdp_value, bool):
        return cdp_value
    if isinstance(cdp_value, str):
        return cdp_value.lower() not in _FALSY_STRINGS
    return bool(cdp_value)


def properties_to_bitmap(properties: dict[str, object]) -> int:
    """Convert a dict of CDP AX properties to the 8-bit state bitmap.

    Keys may be any casing; values may be bools, strings, or None. Properties
    outside the 8-field bitmap are ignored.
    """
    bitmap = 0
    for cdp_name, cdp_value in properties.items():
        canonical = normalize_ax_property_name(cdp_name)
        if canonical is None:
            continue
        if collapse_state_value(cdp_value):
            bitmap |= int(_STATE_BITS[canonical])
    return bitmap


def ax_role_to_landmark(ax_role: str) -> str | None:
    """Return the canonical HTML-tag landmark for a CDP AX role, or None."""
    return _AX_ROLE_TO_LANDMARK.get(ax_role)


def normalize_role(role: str | None) -> str:
    """Map a role to the canonical vocabulary. Unknown or None → 'generic'."""
    if role is None:
        return ROLE_GENERIC
    return role if role in ROLES else ROLE_GENERIC
