"""
lantern/grouping.py — Methodology C: ARIA + layout grouping analyzer.

Given DOM-side context for each focusable element (ARIA relationship
attributes, form ancestor, computed-layout group), produce a typed
relationship graph per LANTERN.md Part 4 Step 2.

Input types (`ElementDOMContext`) are defined here and populated by
`lantern.probe` (L-05) from DOM queries + `getComputedStyle` calls
(whose cost was verified under the 2000ms cap by L-SPIKE-03).

Relationship kinds per Part 4 Step 2:
  - label            — aria-labelledby
  - describe         — aria-describedby
  - control          — aria-controls
  - own              — aria-owns
  - active-descendant — aria-activedescendant
  - form-member      — nearest <form> ancestor
  - spatial-group    — shared layout parent (CSS grid/flex container)

STUB — L-04 red. Implementation lands in green(L-04).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ARIA attribute names whose values are space-separated ID-ref lists.
ARIA_IDREF_LIST_ATTRS: tuple[str, ...] = (
    "aria-labelledby",
    "aria-describedby",
    "aria-controls",
    "aria-owns",
)

# ARIA attribute whose value is a single ID-ref.
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
    """Typed relationships involving one focusable element. Frozen.

    All outgoing-ID lists (labelled_by/described_by/controls/owns) are
    filtered to targets that appear in the input element set — dangling
    ARIA references to non-present elements are silently dropped at
    grouping time; they are not errors, merely noise. `active_descendant`
    is similarly None if the reference doesn't resolve.
    """

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
    raise NotImplementedError("L-04 stub")


def build_grouping_map(
    elements: list[ElementDOMContext],
) -> dict[str, ElementGrouping]:
    raise NotImplementedError("L-04 stub")
