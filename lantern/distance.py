"""
lantern/distance.py — distance metrics for Lantern fingerprints.

Three distance functions per LANTERN.md Part 4 Step 6:

  - levenshtein       — primary, edit distance on role-sequence fingerprints
  - jaccard           — secondary (tiebreak), set distance on state-transition
                        endpoint kinds
  - size_of_delta     — tertiary (further tiebreak), absolute size difference

Each has a normalized variant (`_normalized`) bounded to [0, 1] per the
distance-metric contract in LANTERN.md Part 5 Measurement Surface Freeze.

Pure functions, deterministic, operate on hashable inputs.

STUB — L-02 red. Implementation lands in green(L-02).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Hashable


def levenshtein(a: Sequence[Hashable], b: Sequence[Hashable]) -> int:
    raise NotImplementedError("L-02 stub")


def levenshtein_normalized(a: Sequence[Hashable], b: Sequence[Hashable]) -> float:
    raise NotImplementedError("L-02 stub")


def jaccard(a: set[Hashable] | frozenset[Hashable], b: set[Hashable] | frozenset[Hashable]) -> float:
    raise NotImplementedError("L-02 stub")


def size_of_delta(a: Sequence | set | frozenset, b: Sequence | set | frozenset) -> int:
    raise NotImplementedError("L-02 stub")


def size_of_delta_normalized(a: Sequence | set | frozenset, b: Sequence | set | frozenset) -> float:
    raise NotImplementedError("L-02 stub")
