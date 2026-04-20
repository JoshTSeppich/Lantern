"""Tests for lantern.distance — Levenshtein, Jaccard, size-of-delta."""

from __future__ import annotations

import random

import pytest

from lantern import distance
from lantern.fingerprint import FingerprintTuple


# -------------------------------------------------------------------------
# Levenshtein
# -------------------------------------------------------------------------

class TestLevenshteinBasics:
    def test_identity(self):
        """d(a, a) == 0. Identity property."""
        assert distance.levenshtein("kitten", "kitten") == 0
        assert distance.levenshtein([], []) == 0
        assert distance.levenshtein([1, 2, 3], [1, 2, 3]) == 0

    def test_classic_example(self):
        """Canonical Levenshtein example: kitten → sitting is 3 edits (k→s, e→i, +g)."""
        assert distance.levenshtein("kitten", "sitting") == 3

    def test_empty_vs_nonempty(self):
        assert distance.levenshtein("", "abc") == 3
        assert distance.levenshtein("abc", "") == 3
        assert distance.levenshtein("", "x") == 1

    def test_single_insertion(self):
        assert distance.levenshtein("abc", "abcd") == 1
        assert distance.levenshtein("abc", "xabc") == 1
        assert distance.levenshtein("abc", "axbc") == 1

    def test_single_deletion(self):
        assert distance.levenshtein("abcd", "abc") == 1

    def test_single_substitution(self):
        assert distance.levenshtein("abc", "xbc") == 1

    def test_completely_different(self):
        assert distance.levenshtein("abc", "xyz") == 3


class TestLevenshteinSymmetry:
    """Property: d(a, b) == d(b, a) for all a, b."""

    @pytest.mark.parametrize("a,b", [
        ("abc", "def"),
        ("kitten", "sitting"),
        ("", "x"),
        ("hello world", "hello"),
        ("", ""),
        ("a", "a"),
        ([1, 2, 3], [4, 5, 6, 7]),
    ])
    def test_symmetry(self, a, b):
        assert distance.levenshtein(a, b) == distance.levenshtein(b, a)

    def test_symmetry_random(self):
        """Property test on random pairs."""
        rng = random.Random(42)
        alphabet = ["button", "link", "textbox", "checkbox", "generic"]
        for _ in range(100):
            la = rng.randint(0, 10)
            lb = rng.randint(0, 10)
            a = [rng.choice(alphabet) for _ in range(la)]
            b = [rng.choice(alphabet) for _ in range(lb)]
            assert distance.levenshtein(a, b) == distance.levenshtein(b, a)


class TestLevenshteinTriangleInequality:
    """Property: d(a, c) ≤ d(a, b) + d(b, c) for all triples."""

    @pytest.mark.parametrize("a,b,c", [
        ("abc", "abd", "abe"),
        ("", "a", "ab"),
        ("kitten", "sitting", "biting"),
        ("button", "link", "textbox"),
        ("", "", ""),
        ("hello", "", "world"),
    ])
    def test_triangle_inequality_handpicked(self, a, b, c):
        d_ac = distance.levenshtein(a, c)
        d_ab = distance.levenshtein(a, b)
        d_bc = distance.levenshtein(b, c)
        assert d_ac <= d_ab + d_bc, f"triangle failed: {a!r}, {b!r}, {c!r} → d(a,c)={d_ac} > {d_ab}+{d_bc}"

    def test_triangle_inequality_random(self):
        """Property test on random triples."""
        rng = random.Random(7)
        alphabet = ["a", "b", "c", "d", "e"]
        for _ in range(100):
            la = rng.randint(0, 8)
            lb = rng.randint(0, 8)
            lc = rng.randint(0, 8)
            a = [rng.choice(alphabet) for _ in range(la)]
            b = [rng.choice(alphabet) for _ in range(lb)]
            c = [rng.choice(alphabet) for _ in range(lc)]
            d_ac = distance.levenshtein(a, c)
            d_ab = distance.levenshtein(a, b)
            d_bc = distance.levenshtein(b, c)
            assert d_ac <= d_ab + d_bc, (
                f"triangle failed on random: a={a}, b={b}, c={c} → {d_ac} > {d_ab}+{d_bc}"
            )


class TestLevenshteinNormalized:
    def test_bounds(self):
        rng = random.Random(11)
        alphabet = ["x", "y", "z"]
        for _ in range(50):
            la = rng.randint(0, 10)
            lb = rng.randint(0, 10)
            a = [rng.choice(alphabet) for _ in range(la)]
            b = [rng.choice(alphabet) for _ in range(lb)]
            d = distance.levenshtein_normalized(a, b)
            assert 0.0 <= d <= 1.0, f"out of bounds: d({a}, {b}) = {d}"

    def test_both_empty(self):
        """d(∅, ∅) = 0 by convention (avoids 0/0)."""
        assert distance.levenshtein_normalized([], []) == 0.0
        assert distance.levenshtein_normalized("", "") == 0.0

    def test_identity_normalized(self):
        assert distance.levenshtein_normalized("abc", "abc") == 0.0

    def test_completely_different_normalized(self):
        # 3 substitutions / max(3,3) = 3/3 = 1.0
        assert distance.levenshtein_normalized("abc", "xyz") == 1.0


class TestLevenshteinOnFingerprintTuples:
    """The primary use case: Levenshtein on sequences of FingerprintTuple."""

    def test_same_fingerprint_distance_zero(self):
        a = [FingerprintTuple("button", 0, "main"), FingerprintTuple("link", 0, "nav")]
        b = [FingerprintTuple("button", 0, "main"), FingerprintTuple("link", 0, "nav")]
        assert distance.levenshtein(a, b) == 0

    def test_insertion_at_end(self):
        a = [FingerprintTuple("button", 0, "main")]
        b = [FingerprintTuple("button", 0, "main"), FingerprintTuple("link", 0, "nav")]
        assert distance.levenshtein(a, b) == 1

    def test_state_bitmap_changes_count_as_substitution(self):
        a = [FingerprintTuple("button", 0, "main")]
        b = [FingerprintTuple("button", 1, "main")]  # HASPOPUP bit set
        assert distance.levenshtein(a, b) == 1


# -------------------------------------------------------------------------
# Jaccard
# -------------------------------------------------------------------------

class TestJaccardBasics:
    def test_identity(self):
        s = frozenset({"nav", "change", "noop"})
        assert distance.jaccard(s, s) == 0.0

    def test_disjoint(self):
        assert distance.jaccard({"a", "b"}, {"c", "d"}) == 1.0

    def test_half_overlap(self):
        # |A∩B|=1, |A∪B|=3 → distance = 1 - 1/3 = 2/3
        assert distance.jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(2.0 / 3.0)

    def test_full_containment(self):
        # A ⊂ B: |A∩B|=|A|, |A∪B|=|B| → distance = 1 - |A|/|B|
        assert distance.jaccard({"a"}, {"a", "b", "c", "d"}) == pytest.approx(0.75)

    def test_both_empty(self):
        """d(∅, ∅) = 0 by convention (avoids 0/0)."""
        assert distance.jaccard(set(), set()) == 0.0

    def test_one_empty(self):
        """|∅ ∩ X| = 0, |∅ ∪ X| = |X|, distance = 1."""
        assert distance.jaccard({"a"}, set()) == 1.0
        assert distance.jaccard(set(), {"a"}) == 1.0


class TestJaccardSymmetry:
    @pytest.mark.parametrize("a,b", [
        ({"a", "b"}, {"b", "c"}),
        (set(), {"x"}),
        ({"a"}, {"a", "b", "c"}),
        (set(), set()),
    ])
    def test_symmetry(self, a, b):
        assert distance.jaccard(a, b) == distance.jaccard(b, a)

    def test_symmetry_random(self):
        rng = random.Random(42)
        universe = ["a", "b", "c", "d", "e", "f", "g"]
        for _ in range(50):
            a = frozenset(rng.sample(universe, k=rng.randint(0, len(universe))))
            b = frozenset(rng.sample(universe, k=rng.randint(0, len(universe))))
            assert distance.jaccard(a, b) == distance.jaccard(b, a)


class TestJaccardBounds:
    def test_bounds_random(self):
        rng = random.Random(13)
        universe = ["a", "b", "c", "d", "e"]
        for _ in range(50):
            a = frozenset(rng.sample(universe, k=rng.randint(0, len(universe))))
            b = frozenset(rng.sample(universe, k=rng.randint(0, len(universe))))
            d = distance.jaccard(a, b)
            assert 0.0 <= d <= 1.0, f"jaccard out of bounds on {a}, {b}: {d}"


# -------------------------------------------------------------------------
# Size-of-delta
# -------------------------------------------------------------------------

class TestSizeOfDelta:
    def test_same_length(self):
        assert distance.size_of_delta([1, 2, 3], [4, 5, 6]) == 0

    def test_different_length(self):
        assert distance.size_of_delta([1, 2], [1, 2, 3, 4]) == 2

    def test_one_empty(self):
        assert distance.size_of_delta([1, 2, 3], []) == 3

    def test_both_empty(self):
        assert distance.size_of_delta([], []) == 0

    def test_identity(self):
        """d(a, a) == 0 by size (this is identity-on-size, not identity-on-values)."""
        assert distance.size_of_delta([1, 2, 3], [1, 2, 3]) == 0

    def test_symmetry(self):
        assert distance.size_of_delta([1, 2], [1, 2, 3, 4]) == distance.size_of_delta(
            [1, 2, 3, 4], [1, 2]
        )

    def test_on_sets(self):
        assert distance.size_of_delta({"a", "b"}, {"c"}) == 1

    def test_on_strings(self):
        assert distance.size_of_delta("abc", "abcd") == 1


class TestSizeOfDeltaNormalized:
    def test_both_empty(self):
        assert distance.size_of_delta_normalized([], []) == 0.0

    def test_identity(self):
        assert distance.size_of_delta_normalized([1, 2, 3], [1, 2, 3]) == 0.0

    def test_complete_disparity(self):
        # One empty → 1.0
        assert distance.size_of_delta_normalized([1, 2, 3], []) == 1.0
        assert distance.size_of_delta_normalized([], [1, 2, 3]) == 1.0

    def test_half_size(self):
        # |a|=1, |b|=2 → delta=1, max=2 → 0.5
        assert distance.size_of_delta_normalized([1], [1, 2]) == 0.5

    def test_bounds_random(self):
        rng = random.Random(29)
        for _ in range(50):
            a = list(range(rng.randint(0, 20)))
            b = list(range(rng.randint(0, 20)))
            d = distance.size_of_delta_normalized(a, b)
            assert 0.0 <= d <= 1.0, f"size_of_delta_normalized out of bounds: {d}"
