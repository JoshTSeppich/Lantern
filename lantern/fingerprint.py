"""
lantern/fingerprint.py — Methodology A: canonical fingerprint tuple sequence.

Pure function: AX-tree ProbeRecords → ordered list of (role, state_bitmap,
landmark) tuples. No Playwright dependency; consumes data structures
produced by probe.py.
"""

from __future__ import annotations

from typing import NamedTuple

from pydantic import BaseModel, ConfigDict, Field

from lantern import vocab


class ProbeRecord(BaseModel):
    """Raw probe output per focused element (Part 4 Step 1).

    Frozen contract — any change requires a new contracts(probe-record): freeze.
    Fields preserve CDP's raw output; normalization happens in `probe_to_tuple`
    via `vocab.properties_to_bitmap` and `vocab.normalize_role`.
    """

    model_config = ConfigDict(frozen=True)

    ax_role: str | None = None
    ax_properties: dict[str, object] = Field(default_factory=dict)
    ancestor_ax_roles: list[str] = Field(default_factory=list)
    accessible_name: str | None = None
    tag_name: str | None = None


class FingerprintTuple(NamedTuple):
    """Single entry in a canonical fingerprint (Part 4 Step 1). Hashable, tuple-ordered."""

    role: str            # canonical role from vocab.ROLES, or 'generic'
    state_bitmap: int    # 8-bit, per vocab.StateBit
    landmark: str        # HTML-tag landmark from vocab.LANDMARKS


def resolve_landmark(ancestor_ax_roles: list[str]) -> str:
    """Return the nearest-ancestor HTML-tag landmark, or 'none' if none found.

    Input is expected in nearest-first order (as produced by an AX tree parentId
    walk). First landmark-role encountered wins.
    """
    for role in ancestor_ax_roles:
        lm = vocab.ax_role_to_landmark(role)
        if lm is not None:
            return lm
    return vocab.LANDMARK_NONE


def probe_to_tuple(record: ProbeRecord) -> FingerprintTuple:
    """Convert a single ProbeRecord to its canonical FingerprintTuple. Pure."""
    return FingerprintTuple(
        role=vocab.normalize_role(record.ax_role),
        state_bitmap=vocab.properties_to_bitmap(record.ax_properties),
        landmark=resolve_landmark(record.ancestor_ax_roles),
    )


def fingerprint(records: list[ProbeRecord]) -> list[FingerprintTuple]:
    """Convert an ordered sequence of ProbeRecords to a canonical fingerprint.

    Order-preserving, deterministic. This is the A+B static fingerprint that
    Methodology A reads and distance.py compares.
    """
    return [probe_to_tuple(r) for r in records]
