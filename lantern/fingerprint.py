"""
lantern/fingerprint.py — Methodology A: canonical fingerprint tuple sequence.

Pure function: AX-tree ProbeRecords → ordered list of (role, state_bitmap, landmark)
tuples. No Playwright dependency; consumes data structures produced by probe.py.

STUB — L-01 red. Implementation lands in green(L-01).
"""

from __future__ import annotations

from typing import NamedTuple


class ProbeRecord:
    """Stub for pydantic model; implemented in green(L-01)."""
    def __init__(self, **kwargs: object) -> None:
        raise NotImplementedError("L-01 stub")


class FingerprintTuple(NamedTuple):
    """Single entry in a canonical fingerprint. Part 4 Step 1."""
    role: str
    state_bitmap: int
    landmark: str


def resolve_landmark(ancestor_ax_roles: list[str]) -> str:
    raise NotImplementedError("L-01 stub")


def probe_to_tuple(record: "ProbeRecord") -> FingerprintTuple:
    raise NotImplementedError("L-01 stub")


def fingerprint(records: list["ProbeRecord"]) -> list[FingerprintTuple]:
    raise NotImplementedError("L-01 stub")
