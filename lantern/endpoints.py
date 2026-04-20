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
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from lantern.fingerprint import ProbeRecord


ACCESSIBLE_NAME_MAX_LEN: Final[int] = 64
ANCESTOR_WALK_CAP: Final[int] = 100

# AX roles that terminate a tab traversal when re-encountered (body-return).
# "WebArea" is Chromium's role for document root; "RootWebArea" appears in some CDP versions.
_BODY_RETURN_ROLES: Final[frozenset[str]] = frozenset({"WebArea", "RootWebArea"})


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


def _role_string(node: AXNode) -> str | None:
    if node.role is None or node.role.value is None:
        return None
    return str(node.role.value)


def walk_ancestor_roles(
    node: AXNode,
    ax_nodes_by_id: dict[str, AXNode],
) -> list[str]:
    """Walk parentId chain; return ancestor AX roles, nearest-first.

    Stops at root (no parentId), missing parent, or ANCESTOR_WALK_CAP hops.
    Parents without an explicit role are skipped (not appended) but the walk
    continues through them.
    """
    roles: list[str] = []
    current: AXNode | None = node
    for _ in range(ANCESTOR_WALK_CAP):
        if current is None or current.parentId is None:
            break
        parent = ax_nodes_by_id.get(current.parentId)
        if parent is None:
            break
        role_val = _role_string(parent)
        if role_val is not None:
            roles.append(role_val)
        current = parent
    return roles


def is_valid_endpoint(node: AXNode) -> bool:
    """A node is a valid endpoint iff it is not ignored and has a backendDOMNodeId."""
    return not node.ignored and node.backendDOMNodeId is not None


def _extract_accessible_name(node: AXNode) -> str | None:
    if node.name is None or node.name.value is None:
        return None
    raw = str(node.name.value)
    if not raw:
        return None
    return raw[:ACCESSIBLE_NAME_MAX_LEN].lower()


def _extract_properties(node: AXNode) -> dict[str, object]:
    return {p.name: p.value.value for p in node.properties}


def ax_node_to_probe_record(
    node: AXNode,
    ax_nodes_by_id: dict[str, AXNode],
    tag_name: str | None = None,
) -> ProbeRecord:
    """Pure transformation: AXNode → ProbeRecord."""
    return ProbeRecord(
        ax_role=_role_string(node),
        ax_properties=_extract_properties(node),
        ancestor_ax_roles=walk_ancestor_roles(node, ax_nodes_by_id),
        accessible_name=_extract_accessible_name(node),
        tag_name=tag_name,
    )


def extract_endpoints(
    tab_ordered_node_ids: list[str],
    ax_tree: list[AXNode],
    dom_tags: dict[int, str] | None = None,
) -> list[ProbeRecord]:
    """Given a tab-ordered sequence of AX node IDs, produce the ordered list of
    ProbeRecord for each valid endpoint.

    Terminates at:
      - body-return (role in {WebArea, RootWebArea})
      - already-seen (same nodeId appears twice — L-SPIKE-01 fallback)

    Silently skips:
      - missing-from-tree node IDs
      - ignored nodes
      - nodes without backendDOMNodeId

    `dom_tags` maps backendDOMNodeId → HTML tag (from DOM.describeNode in the
    real probe). Optional; when absent, ProbeRecord.tag_name is None.
    """
    ax_nodes_by_id = {n.nodeId: n for n in ax_tree}
    records: list[ProbeRecord] = []
    seen: set[str] = set()

    for node_id in tab_ordered_node_ids:
        if node_id in seen:
            break
        seen.add(node_id)

        node = ax_nodes_by_id.get(node_id)
        if node is None:
            continue

        if _role_string(node) in _BODY_RETURN_ROLES:
            break

        if not is_valid_endpoint(node):
            continue

        tag = None
        if dom_tags is not None and node.backendDOMNodeId is not None:
            tag = dom_tags.get(node.backendDOMNodeId)

        records.append(ax_node_to_probe_record(node, ax_nodes_by_id, tag_name=tag))

    return records
