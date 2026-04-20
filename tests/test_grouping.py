"""Tests for lantern.grouping — Methodology C ARIA + layout grouping."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lantern import grouping
from lantern.grouping import ElementDOMContext, ElementGrouping


FIXTURE_FORM = Path(__file__).parent / "fixtures" / "grouping_form.json"


# -------------------------------------------------------------------------
# Input-shape contract
# -------------------------------------------------------------------------

class TestElementDOMContextContract:
    def test_minimal(self):
        c = ElementDOMContext(element_id="x")
        assert c.element_id == "x"
        assert c.aria_attributes == {}
        assert c.form_ancestor_id is None
        assert c.layout_group_id is None
        assert c.focusable is True

    def test_all_fields(self):
        c = ElementDOMContext(
            element_id="x",
            aria_attributes={"aria-labelledby": "y"},
            form_ancestor_id="form-1",
            layout_group_id="grid-1",
            focusable=False,
        )
        assert c.aria_attributes == {"aria-labelledby": "y"}
        assert c.form_ancestor_id == "form-1"
        assert c.layout_group_id == "grid-1"
        assert c.focusable is False

    def test_frozen(self):
        c = ElementDOMContext(element_id="x")
        with pytest.raises(Exception):
            c.element_id = "y"  # type: ignore[misc]


# -------------------------------------------------------------------------
# parse_idref_list
# -------------------------------------------------------------------------

class TestParseIdrefList:
    def test_empty_string(self):
        assert grouping.parse_idref_list("") == []

    def test_single_id(self):
        assert grouping.parse_idref_list("foo") == ["foo"]

    def test_space_separated(self):
        assert grouping.parse_idref_list("foo bar baz") == ["foo", "bar", "baz"]

    def test_collapses_whitespace(self):
        assert grouping.parse_idref_list("foo   bar") == ["foo", "bar"]
        assert grouping.parse_idref_list("  foo bar  ") == ["foo", "bar"]

    def test_tab_and_newline_separators(self):
        # HTML spec treats whitespace as space-separated for idref lists
        assert grouping.parse_idref_list("foo\tbar\nbaz") == ["foo", "bar", "baz"]


# -------------------------------------------------------------------------
# build_grouping_map — core relationship types
# -------------------------------------------------------------------------

def _el(
    eid: str,
    *,
    aria: dict[str, str] | None = None,
    form: str | None = None,
    grid: str | None = None,
    focusable: bool = True,
) -> ElementDOMContext:
    return ElementDOMContext(
        element_id=eid,
        aria_attributes=aria or {},
        form_ancestor_id=form,
        layout_group_id=grid,
        focusable=focusable,
    )


class TestAriaLabelledBy:
    def test_single_reference(self):
        els = [
            _el("input", aria={"aria-labelledby": "label"}),
            _el("label", focusable=False),
        ]
        m = grouping.build_grouping_map(els)
        assert m["input"].labelled_by == ["label"]

    def test_multiple_references(self):
        els = [
            _el("input", aria={"aria-labelledby": "l1 l2"}),
            _el("l1", focusable=False),
            _el("l2", focusable=False),
        ]
        m = grouping.build_grouping_map(els)
        assert m["input"].labelled_by == ["l1", "l2"]

    def test_dangling_reference_dropped(self):
        els = [
            _el("input", aria={"aria-labelledby": "missing"}),
        ]
        m = grouping.build_grouping_map(els)
        assert m["input"].labelled_by == []

    def test_mix_of_valid_and_dangling(self):
        els = [
            _el("input", aria={"aria-labelledby": "missing label"}),
            _el("label", focusable=False),
        ]
        m = grouping.build_grouping_map(els)
        assert m["input"].labelled_by == ["label"]


class TestAriaDescribedBy:
    def test_single_reference(self):
        els = [
            _el("input", aria={"aria-describedby": "hint"}),
            _el("hint", focusable=False),
        ]
        m = grouping.build_grouping_map(els)
        assert m["input"].described_by == ["hint"]


class TestAriaControls:
    def test_control_relationship(self):
        els = [
            _el("btn", aria={"aria-controls": "panel"}),
            _el("panel", focusable=False),
        ]
        m = grouping.build_grouping_map(els)
        assert m["btn"].controls == ["panel"]


class TestAriaOwns:
    def test_own_relationship(self):
        els = [
            _el("combo", aria={"aria-owns": "listbox"}),
            _el("listbox", focusable=False),
        ]
        m = grouping.build_grouping_map(els)
        assert m["combo"].owns == ["listbox"]


class TestAriaActiveDescendant:
    def test_single_active_descendant(self):
        els = [
            _el("combo", aria={"aria-activedescendant": "option-2"}),
            _el("option-2", focusable=False),
        ]
        m = grouping.build_grouping_map(els)
        assert m["combo"].active_descendant == "option-2"

    def test_dangling_active_descendant_is_none(self):
        els = [
            _el("combo", aria={"aria-activedescendant": "missing"}),
        ]
        m = grouping.build_grouping_map(els)
        assert m["combo"].active_descendant is None

    def test_absent_attribute_is_none(self):
        els = [_el("combo")]
        m = grouping.build_grouping_map(els)
        assert m["combo"].active_descendant is None


# -------------------------------------------------------------------------
# Form membership
# -------------------------------------------------------------------------

class TestFormMembership:
    def test_form_ancestor_propagated(self):
        els = [_el("input", form="form-login")]
        m = grouping.build_grouping_map(els)
        assert m["input"].form_ancestor == "form-login"

    def test_no_form_ancestor(self):
        els = [_el("btn")]
        m = grouping.build_grouping_map(els)
        assert m["btn"].form_ancestor is None


# -------------------------------------------------------------------------
# Spatial grouping
# -------------------------------------------------------------------------

class TestSpatialGrouping:
    def test_layout_group_propagated(self):
        els = [_el("btn", grid="form-grid-1")]
        m = grouping.build_grouping_map(els)
        assert m["btn"].spatial_group == "form-grid-1"

    def test_no_layout_group(self):
        els = [_el("btn")]
        m = grouping.build_grouping_map(els)
        assert m["btn"].spatial_group is None


# -------------------------------------------------------------------------
# Composition
# -------------------------------------------------------------------------

class TestComposition:
    def test_empty_input_empty_output(self):
        assert grouping.build_grouping_map([]) == {}

    def test_every_element_gets_an_entry(self):
        els = [_el("a"), _el("b"), _el("c")]
        m = grouping.build_grouping_map(els)
        assert set(m.keys()) == {"a", "b", "c"}

    def test_all_relationship_types_on_one_element(self):
        els = [
            _el("combo", aria={
                "aria-labelledby": "lbl",
                "aria-describedby": "desc",
                "aria-controls": "panel",
                "aria-owns": "listbox",
                "aria-activedescendant": "option",
            }, form="form-1", grid="grid-1"),
            _el("lbl", focusable=False),
            _el("desc", focusable=False),
            _el("panel", focusable=False),
            _el("listbox", focusable=False),
            _el("option", focusable=False),
        ]
        m = grouping.build_grouping_map(els)
        g = m["combo"]
        assert g.labelled_by == ["lbl"]
        assert g.described_by == ["desc"]
        assert g.controls == ["panel"]
        assert g.owns == ["listbox"]
        assert g.active_descendant == "option"
        assert g.form_ancestor == "form-1"
        assert g.spatial_group == "grid-1"


# -------------------------------------------------------------------------
# Fixture roundtrip (§R3 L-04 requirement)
# -------------------------------------------------------------------------

class TestFixtureRoundtrip:
    def _load(self) -> dict:
        with FIXTURE_FORM.open("r") as f:
            return json.load(f)

    def test_fixture_matches_expected_groupings(self):
        data = self._load()
        elements = [ElementDOMContext.model_validate(e) for e in data["elements"]]
        m = grouping.build_grouping_map(elements)

        for eid, expected in data["expected"].items():
            g = m[eid]
            assert g.labelled_by == expected["labelled_by"], f"{eid} labelled_by"
            assert g.described_by == expected["described_by"], f"{eid} described_by"
            assert g.controls == expected["controls"], f"{eid} controls"
            assert g.owns == expected["owns"], f"{eid} owns"
            assert g.active_descendant == expected["active_descendant"], f"{eid} active_descendant"
            assert g.form_ancestor == expected["form_ancestor"], f"{eid} form_ancestor"
            assert g.spatial_group == expected["spatial_group"], f"{eid} spatial_group"
