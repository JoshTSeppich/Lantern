"""
lantern/endpoints.py — Methodology B: tab-order endpoint discovery (AX tree → ProbeRecord).

Pure transformation layer: given AX-tree data (as produced by CDP
`Accessibility.getFullAXTree`) plus a tab-ordered sequence of AX node IDs
(as produced by a Playwright keyboard-driven traversal), produce an
ordered list of `ProbeRecord` ready for `fingerprint.py`.

No Playwright dependency — tab traversal itself is the caller's job
(`lantern.probe` in L-05). Responsibilities handled here:
  - AX node → ProbeRecord shape transformation
  - Ancestor AX-role chain walk (for landmark resolution in fingerprint)
  - Endpoint validity filtering (ignored, missing backendDOMNodeId)
  - Full-cycle termination (body-return and already-seen — L-SPIKE-01)
  - Accessible-name truncation (64 chars, lowercase) per Part 4 Step 1

STUB — L-03 red. Implementation lands in green(L-03).
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from lantern.fingerprint import ProbeRecord


ACCESSIBLE_NAME_MAX_LEN: Final[int] = 64
ANCESTOR_WALK_CAP: Final[int] = 100


class AXValue(BaseModel):
    """CDP AXValue payload. Frozen."""
    model_config = ConfigDict(frozen=True)
    type: str
    value: object | None = None


class AXProperty(BaseModel):
    """CDP AXProperty — {name, value: AXValue}. Frozen."""
    model_config = ConfigDict(frozen=True)
    name: str
    value: AXValue


class AXNode(BaseModel):
    """CDP AX tree node (subset of Accessibility.AXNode). Frozen."""
    model_config = ConfigDict(frozen=True)
    nodeId: str
    role: AXValue | None = None
    name: AXValue | None = None
    properties: list[AXProperty] = Field(default_factory=list)
    backendDOMNodeId: int | None = None
    parentId: str | None = None
    childIds: list[str] = Field(default_factory=list)
    ignored: bool = False


def walk_ancestor_roles(
    node: AXNode,
    ax_nodes_by_id: dict[str, AXNode],
) -> list[str]:
    raise NotImplementedError("L-03 stub")


def is_valid_endpoint(node: AXNode) -> bool:
    raise NotImplementedError("L-03 stub")


def ax_node_to_probe_record(
    node: AXNode,
    ax_nodes_by_id: dict[str, AXNode],
    tag_name: str | None = None,
) -> ProbeRecord:
    raise NotImplementedError("L-03 stub")


def extract_endpoints(
    tab_ordered_node_ids: list[str],
    ax_tree: list[AXNode],
    dom_tags: dict[int, str] | None = None,
) -> list[ProbeRecord]:
    raise NotImplementedError("L-03 stub")
