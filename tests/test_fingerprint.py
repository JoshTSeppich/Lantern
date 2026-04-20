"""Tests for lantern.fingerprint — Methodology A canonical tuple sequence."""

from __future__ import annotations

import pytest

from lantern import fingerprint as fp
from lantern import vocab
from lantern.vocab import StateBit


def make_record(
    ax_role: str | None = "button",
    ax_properties: dict[str, object] | None = None,
    ancestor_ax_roles: list[str] | None = None,
    accessible_name: str | None = "",
    tag_name: str | None = "button",
) -> fp.ProbeRecord:
    return fp.ProbeRecord(
        ax_role=ax_role,
        ax_properties=ax_properties or {},
        ancestor_ax_roles=ancestor_ax_roles or [],
        accessible_name=accessible_name,
        tag_name=tag_name,
    )


class TestProbeRecordContract:
    """ProbeRecord is the frozen probe output format (LANTERN.md §1.4; pydantic per spec)."""

    def test_minimal_record_valid(self):
        r = fp.ProbeRecord(ax_role="button")
        assert r.ax_role == "button"
        assert r.ax_properties == {}
        assert r.ancestor_ax_roles == []

    def test_all_fields_roundtrip(self):
        r = fp.ProbeRecord(
            ax_role="checkbox",
            ax_properties={"checked": "true"},
            ancestor_ax_roles=["main"],
            accessible_name="remember me",
            tag_name="input",
        )
        assert r.ax_role == "checkbox"
        assert r.ax_properties == {"checked": "true"}
        assert r.ancestor_ax_roles == ["main"]
        assert r.accessible_name == "remember me"
        assert r.tag_name == "input"


class TestResolveLandmark:
    def test_no_ancestors_is_none(self):
        assert fp.resolve_landmark([]) == "none"

    def test_all_non_landmark_ancestors_is_none(self):
        assert fp.resolve_landmark(["button", "link", "list", "listitem"]) == "none"

    def test_nearest_landmark_wins(self):
        # Ancestors passed nearest-first (as resolved via AX tree parent walk)
        assert fp.resolve_landmark(["main", "navigation"]) == "main"
        assert fp.resolve_landmark(["navigation", "main"]) == "nav"

    def test_non_landmark_then_landmark(self):
        # First few ancestors are non-landmarks; first landmark encountered wins
        assert fp.resolve_landmark(["list", "listitem", "navigation"]) == "nav"

    @pytest.mark.parametrize("ancestor,expected_tag", [
        (["main"],          "main"),
        (["navigation"],    "nav"),
        (["banner"],        "header"),
        (["contentinfo"],   "footer"),
        (["complementary"], "aside"),
    ])
    def test_each_landmark_type(self, ancestor: list[str], expected_tag: str):
        assert fp.resolve_landmark(ancestor) == expected_tag


class TestProbeToTuple:
    def test_basic_button_no_state_in_main(self):
        rec = make_record(ax_role="button", ancestor_ax_roles=["main"])
        t = fp.probe_to_tuple(rec)
        assert t.role == "button"
        assert t.state_bitmap == 0
        assert t.landmark == "main"

    def test_unknown_role_becomes_generic(self):
        rec = make_record(ax_role="my-custom-role")
        t = fp.probe_to_tuple(rec)
        assert t.role == "generic"

    def test_none_role_becomes_generic(self):
        rec = make_record(ax_role=None)
        t = fp.probe_to_tuple(rec)
        assert t.role == "generic"

    def test_hasPopup_camelcase_via_normalization(self):
        """L-SPIKE-02 regression through fingerprint pipeline."""
        rec = make_record(ax_role="button", ax_properties={"hasPopup": "menu"})
        t = fp.probe_to_tuple(rec)
        assert t.state_bitmap & int(StateBit.HASPOPUP) != 0

    def test_tristate_checked_via_collapse(self):
        rec = make_record(ax_role="checkbox", ax_properties={"checked": "true"})
        t = fp.probe_to_tuple(rec)
        assert t.state_bitmap & int(StateBit.CHECKED) != 0

    def test_no_landmark_ancestors_landmark_is_none(self):
        rec = make_record(ancestor_ax_roles=[])
        t = fp.probe_to_tuple(rec)
        assert t.landmark == "none"

    def test_fingerprint_tuple_is_hashable(self):
        # Required: tuples feed Levenshtein as alphabet elements (L-02).
        rec = make_record(ax_role="button")
        t = fp.probe_to_tuple(rec)
        assert hash(t) == hash(t)
        _ = {t}  # should not raise


class TestFingerprint:
    def test_empty_input_empty_output(self):
        assert fp.fingerprint([]) == []

    def test_determinism(self):
        """Property test: same input → same output. Part 4 Step 1."""
        records = [
            make_record(ax_role="button", ancestor_ax_roles=["main"]),
            make_record(ax_role="link", ancestor_ax_roles=["navigation"]),
            make_record(ax_role="textbox", ax_properties={"required": True}),
        ]
        f1 = fp.fingerprint(records)
        f2 = fp.fingerprint(records)
        f3 = fp.fingerprint(records)
        assert f1 == f2 == f3

    def test_order_preservation(self):
        """Property test: input order preserved in output. Part 4 Step 1."""
        r1 = make_record(ax_role="button")
        r2 = make_record(ax_role="link")
        r3 = make_record(ax_role="textbox")

        forward = fp.fingerprint([r1, r2, r3])
        assert [t.role for t in forward] == ["button", "link", "textbox"]

        reverse = fp.fingerprint([r3, r2, r1])
        assert [t.role for t in reverse] == ["textbox", "link", "button"]

        # Different orders → different fingerprints
        assert forward != reverse

    def test_state_bitmap_correctness_end_to_end(self):
        """Property test: state bitmap correctness through the pipeline. Part 4 Step 1 + ADR 0004."""
        rec = make_record(
            ax_role="button",
            ax_properties={"hasPopup": "menu", "disabled": True, "expanded": False},
        )
        [t] = fp.fingerprint([rec])
        assert t.state_bitmap & int(StateBit.HASPOPUP) != 0   # set via camelCase
        assert t.state_bitmap & int(StateBit.DISABLED) != 0   # set via native bool
        assert t.state_bitmap & int(StateBit.EXPANDED) == 0   # not set (value False)

    def test_many_records_preserves_length(self):
        records = [make_record(ax_role="button") for _ in range(200)]
        out = fp.fingerprint(records)
        assert len(out) == 200

    def test_landmark_resolution_in_pipeline(self):
        """Landmark from ancestor_ax_roles flows through fingerprint unchanged."""
        records = [
            make_record(ax_role="button", ancestor_ax_roles=["main"]),
            make_record(ax_role="link",   ancestor_ax_roles=["navigation"]),
            make_record(ax_role="link",   ancestor_ax_roles=["complementary"]),
            make_record(ax_role="link",   ancestor_ax_roles=["button"]),  # no landmark ancestor
        ]
        out = fp.fingerprint(records)
        assert [t.landmark for t in out] == ["main", "nav", "aside", "none"]
