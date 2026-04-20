"""
lantern/vocab.py — WAI-ARIA roles, landmarks, state bitmap, and normalization boundary.

Per LANTERN.md Part 4 Step 1 and ADR 0004 (state-bitmap normalization).
This module is the single normalization boundary between CDP AX-tree
output and Lantern's canonical vocabulary — AX property-name casing
drift and CDP tristate/token value shapes both collapse here.

STUB — L-01 red. Implementation lands in green(L-01).
"""

from __future__ import annotations


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
