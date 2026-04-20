"""
lantern/grouping.py — Methodology C: ARIA + layout grouping analyzer.

Given DOM-side context for each focusable element (ARIA relationship
attributes, form ancestor, computed-layout group), produce a typed
relationship graph per LANTERN.md Part 4 Step 2.

Input types (`ElementDOMContext`) are defined here and populated by
`lantern.probe` (L-05) from DOM queries + `getComputedStyle` calls
(whose cost was verified under the 2000ms cap by L-SPIKE-03).

Relationship kinds per Part 4 Step 2:
  - label             — aria-labelledby
  - describe          — aria-describedby
  - control           — aria-controls
  - own               — aria-owns
  - active-descendant — aria-activedescendant
  - form-member       — nearest <form> ancestor
  - spatial-group     — shared layout parent (CSS grid/flex container)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


ARIA_IDREF_LIST_ATTRS: tuple[str, ...] = (
    "aria-labelledby",
    "aria-describedby",
    "aria-controls",
    "aria-owns",
)

ARIA_IDREF_SINGLE_ATTR: str = "aria-activedescendant"


class ElementDOMContext(BaseModel):
    """DOM-side context for one element used in grouping analysis. Frozen."""

    model_config = ConfigDict(frozen=True)

    element_id: str
    aria_attributes: dict[str, str] = Field(default_factory=dict)
    form_ancestor_id: str | None = None
    layout_group_id: str | None = None
    focusable: bool = True


class ElementGrouping(BaseModel):
    """Typed relationships involving one focusable element. Frozen."""

    model_config = ConfigDict(frozen=True)

    element_id: str
    labelled_by: list[str] = Field(default_factory=list)
    described_by: list[str] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)
    owns: list[str] = Field(default_factory=list)
    active_descendant: str | None = None
    form_ancestor: str | None = None
    spatial_group: str | None = None


def parse_idref_list(value: str) -> list[str]:
    """Split a space-separated ARIA idref-list value into individual IDs.

    Per HTML spec, "whitespace" in idref-list attributes means any ASCII
    whitespace (space, tab, LF, CR, FF). str.split() with no arg collapses
    runs of whitespace and strips leading/trailing.
    """
    return value.split() if value else []


_ATTR_TO_GROUPING_LIST_FIELD: dict[str, str] = {
    "aria-labelledby":  "labelled_by",
    "aria-describedby": "described_by",
    "aria-controls":    "controls",
    "aria-owns":        "owns",
}


def build_grouping_map(
    elements: list[ElementDOMContext],
) -> dict[str, ElementGrouping]:
    """Build the grouping graph (Part 4 Step 2).

    For every element in the input, produce one ElementGrouping keyed by
    element_id. ARIA idref references are resolved against the input set;
    references to elements not in the input are silently dropped (dangling
    references to non-present elements are common — e.g., `aria-labelledby`
    pointing to a heading that isn't in the focusable probe set).
    """
    known_ids: set[str] = {e.element_id for e in elements}
    result: dict[str, ElementGrouping] = {}

    for el in elements:
        # Resolve each ARIA id-ref list attribute
        fields: dict[str, list[str]] = {
            field: [] for field in _ATTR_TO_GROUPING_LIST_FIELD.values()
        }
        for attr, field in _ATTR_TO_GROUPING_LIST_FIELD.items():
            raw = el.aria_attributes.get(attr, "")
            for ref in parse_idref_list(raw):
                if ref in known_ids:
                    fields[field].append(ref)

        # Resolve the single id-ref attribute
        active_raw = el.aria_attributes.get(ARIA_IDREF_SINGLE_ATTR, "")
        active_id = active_raw.strip() if active_raw else ""
        active_descendant = active_id if active_id in known_ids else None

        result[el.element_id] = ElementGrouping(
            element_id=el.element_id,
            labelled_by=fields["labelled_by"],
            described_by=fields["described_by"],
            controls=fields["controls"],
            owns=fields["owns"],
            active_descendant=active_descendant,
            form_ancestor=el.form_ancestor_id,
            spatial_group=el.layout_group_id,
        )

    return result
