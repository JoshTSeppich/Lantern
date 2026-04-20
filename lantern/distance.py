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
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Hashable


def levenshtein(a: Sequence[Hashable], b: Sequence[Hashable]) -> int:
    """Classic Levenshtein edit distance. O(|a| * |b|) time, O(min(|a|,|b|)) space."""
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr[j] = min(
                curr[j - 1] + 1,        # insertion
                prev[j] + 1,            # deletion
                prev[j - 1] + cost,     # substitution (or match)
            )
        prev = curr
    return prev[-1]


def levenshtein_normalized(a: Sequence[Hashable], b: Sequence[Hashable]) -> float:
    """Levenshtein / max(|a|, |b|), bounded to [0, 1]. Both-empty → 0 by convention."""
    m = max(len(a), len(b))
    if m == 0:
        return 0.0
    return levenshtein(a, b) / m


def jaccard(a: set[Hashable] | frozenset[Hashable], b: set[Hashable] | frozenset[Hashable]) -> float:
    """Jaccard distance: 1 - |A ∩ B| / |A ∪ B|. Native [0, 1]. Both-empty → 0."""
    union = a | b
    if not union:
        return 0.0
    return 1.0 - len(a & b) / len(union)


def size_of_delta(a: Sequence | set | frozenset, b: Sequence | set | frozenset) -> int:
    """Absolute size difference. Tertiary tiebreak."""
    return abs(len(a) - len(b))


def size_of_delta_normalized(a: Sequence | set | frozenset, b: Sequence | set | frozenset) -> float:
    """size_of_delta / max(|a|, |b|), bounded to [0, 1]. Both-empty → 0."""
    m = max(len(a), len(b))
    if m == 0:
        return 0.0
    return size_of_delta(a, b) / m
