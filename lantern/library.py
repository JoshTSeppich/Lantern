"""
lantern/library.py — pattern library + nearest-neighbor lookup (Methodology A).

Per LANTERN.md Part 4 Step 6 + R0.1 (library is the OUTPUT of discrimination,
not an input). The shipped default library is bootstrapped from L-07
discrimination at 9c16385 and stored as a package resource at
lantern/library_data/l07.json.

Distance: normalized Levenshtein on static role-sequence tuples (primary per
Part 4 Step 6). Secondary/tertiary tiebreaks (Jaccard, size-of-delta) are
not used here because the library's representative shapes lack state-
transition data — classify() omits Methodology D per the R2.1 latency
budget; see api.py for the scope decision.

Confidence formula per Part 4 Step 6:
    confidence = 1 - (nearest_distance / max_observed_distance_in_library)
For normalized Levenshtein bounded to [0, 1], `max_observed_distance_in_library`
collapses to 1.0 (the metric's range), so confidence = 1 - nearest_distance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from lantern.distance import levenshtein_normalized


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
        return f"cluster-{self.cluster_id}"


class Library(BaseModel):
    """Pattern library — nearest-neighbor lookup across a set of LibraryShapes."""

    model_config = ConfigDict(frozen=True)

    shapes: list[LibraryShape]

    @classmethod
    def from_json(cls, path: Path) -> "Library":
        with path.open() as f:
            raw = json.load(f)
        shapes = [LibraryShape.model_validate(s) for s in raw]
        return cls(shapes=shapes)

    @classmethod
    def default(cls) -> "Library":
        return cls.from_json(_DEFAULT_LIBRARY_PATH)

    def nearest(self, fingerprint: list) -> tuple[str, float]:
        """Find nearest shape and return `(shape_id, confidence)`.

        If the query fingerprint is empty OR the library is empty,
        returns `(UNKNOWN_SHAPE_ID, 0.0)`. Otherwise finds the shape
        with the lowest normalized Levenshtein distance to the query;
        if the resulting confidence is below `CONFIDENCE_THRESHOLD`,
        returns `(UNKNOWN_SHAPE_ID, confidence)`.
        """
        if not self.shapes or not fingerprint:
            return UNKNOWN_SHAPE_ID, 0.0

        # Normalize query to tuple-of-hashables for Levenshtein
        query = [tuple(t) for t in fingerprint]

        best_shape: LibraryShape | None = None
        best_distance = float("inf")
        for shape in self.shapes:
            # Empty representative → skip (can't compute meaningful distance)
            if not shape.representative_fingerprint:
                continue
            rep = [tuple(t) for t in shape.representative_fingerprint]
            d = levenshtein_normalized(query, rep)
            if d < best_distance:
                best_distance = d
                best_shape = shape

        if best_shape is None:
            return UNKNOWN_SHAPE_ID, 0.0

        confidence = 1.0 - best_distance
        if confidence < CONFIDENCE_THRESHOLD:
            return UNKNOWN_SHAPE_ID, confidence
        return best_shape.shape_id, confidence

    def get_shape(self, shape_id: str) -> LibraryShape | None:
        """Look up a shape by canonical shape_id ('cluster-<N>'). Unknown → None."""
        if not shape_id.startswith("cluster-"):
            return None
        try:
            cid = int(shape_id.removeprefix("cluster-"))
        except ValueError:
            return None
        for shape in self.shapes:
            if shape.cluster_id == cid:
                return shape
        return None
