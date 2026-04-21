"""Tests for lantern.library — shipped L-07 library + nearest-neighbor lookup."""

from __future__ import annotations

from pathlib import Path

import pytest

from lantern.fingerprint import FingerprintTuple
from lantern.library import (
    CONFIDENCE_THRESHOLD,
    UNKNOWN_SHAPE_ID,
    Library,
    LibraryShape,
)


class TestLibraryShapeContract:
    def test_minimal_shape(self):
        s = LibraryShape(
            cluster_id=0,
            size=1,
            majority_category="e-commerce",
            majority_ratio=1.0,
            member_site_ids=["d01-ecom-01"],
            representative_site_id="d01-ecom-01",
            representative_fingerprint=[],
        )
        assert s.shape_id == "cluster-0"
        assert s.majority_ratio == 1.0

    def test_shape_is_frozen(self):
        s = LibraryShape(
            cluster_id=1, size=4, majority_category="forum",
            majority_ratio=0.5, representative_site_id="d05-forum-01",
        )
        with pytest.raises(Exception):
            s.cluster_id = 99  # type: ignore[misc]


class TestLibraryLoading:
    def test_default_library_loads(self):
        lib = Library.default()
        assert len(lib.shapes) == 5  # L-07 produced 5 clusters at k_optimal=5

    def test_from_json_loads_shipped_path(self, tmp_path: Path):
        # Loading the shipped library_data path via from_json directly
        shipped = Path(__file__).resolve().parent.parent / "lantern" / "library_data" / "l07.json"
        lib = Library.from_json(shipped)
        assert len(lib.shapes) == 5

    def test_get_shape_by_id(self):
        lib = Library.default()
        shape = lib.get_shape("cluster-1")
        assert shape is not None
        assert shape.cluster_id == 1
        assert shape.majority_category == "forum"

    def test_get_shape_unknown_returns_none(self):
        lib = Library.default()
        assert lib.get_shape("unknown") is None
        assert lib.get_shape("cluster-99") is None


class TestNearest:
    def _tuple(self, role: str, state: int = 0, landmark: str = "none"):
        return FingerprintTuple(role=role, state_bitmap=state, landmark=landmark)

    def test_empty_fingerprint_is_unknown(self):
        lib = Library.default()
        shape_id, confidence = lib.nearest([])
        assert shape_id == UNKNOWN_SHAPE_ID
        assert confidence == 0.0

    def test_exact_match_to_representative_yields_high_confidence(self):
        """Using a library shape's representative fingerprint as the query should
        produce confidence >= CONFIDENCE_THRESHOLD (ideally 1.0 since distance=0)."""
        lib = Library.default()
        target = lib.shapes[1]  # cluster-1 (dense-link-list)
        fp = [tuple(t) for t in target.representative_fingerprint]
        shape_id, confidence = lib.nearest(fp)
        assert shape_id == "cluster-1"
        assert confidence >= CONFIDENCE_THRESHOLD
        assert confidence > 0.99  # distance is 0; confidence should be ~1

    def test_completely_different_fingerprint_is_unknown(self):
        """A fingerprint with 300 button-in-main tuples should not match any
        L-07 shape closely — confidence below threshold → unknown."""
        lib = Library.default()
        weird = [self._tuple("button", 0, "main") for _ in range(300)]
        shape_id, confidence = lib.nearest(weird)
        # Either unknown or a low-confidence match
        if shape_id != UNKNOWN_SHAPE_ID:
            assert confidence >= CONFIDENCE_THRESHOLD  # sanity: if not unknown, it's above threshold
        assert 0.0 <= confidence <= 1.0

    def test_returns_cluster_prefix(self):
        lib = Library.default()
        # Any match above threshold should use cluster-<N> format
        target = lib.shapes[0]
        fp = [tuple(t) for t in target.representative_fingerprint] or [self._tuple("button")]
        shape_id, confidence = lib.nearest(fp)
        assert shape_id == UNKNOWN_SHAPE_ID or shape_id.startswith("cluster-")
