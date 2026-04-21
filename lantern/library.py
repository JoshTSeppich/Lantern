"""
lantern/library.py — pattern library + nearest-neighbor lookup (Methodology A).

Per LANTERN.md Part 4 Step 6 + R0.1 (library is the OUTPUT of discrimination,
not an input). The shipped default library is bootstrapped from L-07
discrimination at 9c16385 and stored as a package resource at
lantern/library_data/l07.json (committed to the repo; not gitignored).

Public surface:
  - `CONFIDENCE_THRESHOLD = 0.6`  (Part 5 Measurement Surface Freeze)
  - `UNKNOWN_SHAPE_ID = 'unknown'`
  - `LibraryShape`  (pydantic, frozen)
  - `Library`       (loaded via Library.default() or Library.from_json(path))
  - `Library.nearest(fingerprint) -> (shape_id, confidence)`

Distance: normalized Levenshtein on the static fingerprint role-sequence
tuples (primary per LANTERN.md Part 4 Step 6). Secondary/tertiary metrics
(Jaccard, size-of-delta) are not used here because the library's
representative shapes lack state-transition data — classify() omits
Methodology D per the R2.1 latency budget (see api.py for the scope
decision).

Confidence formula per Part 4 Step 6:
    confidence = 1 - (nearest_distance / max_observed_distance_in_library)
For normalized Levenshtein in [0, 1], `max_observed_distance_in_library`
collapses to 1.0 (the metric's range), so confidence = 1 - nearest_distance.

STUB — L-11 red. Implementation lands in green(L-11).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field


CONFIDENCE_THRESHOLD: Final[float] = 0.6
UNKNOWN_SHAPE_ID: Final[str] = "unknown"

_LIBRARY_DATA_DIR: Final[Path] = Path(__file__).parent / "library_data"
_DEFAULT_LIBRARY_PATH: Final[Path] = _LIBRARY_DATA_DIR / "l07.json"


class LibraryShape(BaseModel):
    """One shape in the library — a cluster from L-07 discrimination."""

    model_config = ConfigDict(frozen=True)

    cluster_id: int
    size: int
    majority_category: str
    majority_ratio: float
    member_site_ids: list[str] = Field(default_factory=list)
    representative_site_id: str
    representative_fingerprint: list[list] = Field(default_factory=list)

    @property
    def shape_id(self) -> str:
        """Canonical shape_id used in LanternResult."""
        return f"cluster-{self.cluster_id}"


class Library(BaseModel):
    """Pattern library — nearest-neighbor lookup against a set of shapes."""

    model_config = ConfigDict(frozen=True)

    shapes: list[LibraryShape]

    @classmethod
    def from_json(cls, path: Path) -> "Library":
        raise NotImplementedError("L-11 stub")

    @classmethod
    def default(cls) -> "Library":
        raise NotImplementedError("L-11 stub")

    def nearest(self, fingerprint: list) -> tuple[str, float]:
        """Find nearest shape to `fingerprint` (list of FingerprintTuple or compatible).

        Returns `(shape_id, confidence)` where shape_id is `'unknown'` if
        confidence < CONFIDENCE_THRESHOLD, else `'cluster-<N>'`.
        """
        raise NotImplementedError("L-11 stub")

    def get_shape(self, shape_id: str) -> LibraryShape | None:
        """Look up a shape by canonical shape_id (e.g., 'cluster-2')."""
        raise NotImplementedError("L-11 stub")
