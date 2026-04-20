"""
lantern/vocab.py — WAI-ARIA roles, landmarks, state bitmap, and normalization boundary.

Per LANTERN.md Part 4 Step 1 and ADR 0004 (state-bitmap normalization).
This module is the single normalization boundary between CDP AX-tree
output and Lantern's canonical vocabulary — AX property-name casing
drift and CDP tristate/token value shapes both collapse here.

STUB — L-01 red. Contract surfaces (StateBit, STATE_FIELD_NAMES, LANDMARKS,
ROLES, ROLE_GENERIC, LANDMARK_NONE) are declared to expose the shape the
tests assert; function implementations raise NotImplementedError.
Implementation lands in green(L-01).
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


STATE_FIELD_NAMES: Final[frozenset[str]] = frozenset({
    "expanded", "haspopup", "selected", "checked",
    "disabled", "required", "invalid", "readonly",
})


# ---------------------------------------------------------------------
# Landmark vocabulary (Part 4 Step 1)
# ---------------------------------------------------------------------

LANDMARK_NONE: Final[str] = "none"
LANDMARKS: Final[frozenset[str]] = frozenset({
    "main", "nav", "header", "footer", "aside", LANDMARK_NONE,
})


# ---------------------------------------------------------------------
# Role vocabulary (WAI-ARIA 1.2)
# ---------------------------------------------------------------------

ROLE_GENERIC: Final[str] = "generic"
ROLES: Final[frozenset[str]] = frozenset()  # populated in green(L-01)


# ---------------------------------------------------------------------
# Normalization functions — implementations in green(L-01)
# ---------------------------------------------------------------------

def normalize_ax_property_name(cdp_name: str) -> str | None:
    raise NotImplementedError("L-01 stub")


def collapse_state_value(cdp_value: object) -> bool:
    raise NotImplementedError("L-01 stub")


def properties_to_bitmap(properties: dict[str, object]) -> int:
    raise NotImplementedError("L-01 stub")


def ax_role_to_landmark(ax_role: str) -> str | None:
    raise NotImplementedError("L-01 stub")


def normalize_role(role: str | None) -> str:
    raise NotImplementedError("L-01 stub")
