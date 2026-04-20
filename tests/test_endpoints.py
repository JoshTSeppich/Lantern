"""Tests for lantern.endpoints — Methodology B AX-tree → ProbeRecord transformation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lantern import endpoints
from lantern.endpoints import AXNode, AXProperty, AXValue
from lantern.fingerprint import ProbeRecord
from lantern.vocab import StateBit


FIXTURE_BASIC = Path(__file__).parent / "fixtures" / "ax_tree_basic.json"


# -------------------------------------------------------------------------
# Input-shape pydantic models
# -------------------------------------------------------------------------

class TestAXValueContract:
    def test_minimal_valid(self):
        v = AXValue(type="role", value="button")
        assert v.type == "role"
        assert v.value == "button"

    def test_value_may_be_none(self):
        v = AXValue(type="computedString", value=None)
        assert v.value is None

    def test_frozen(self):
        v = AXValue(type="role", value="button")
        with pytest.raises(Exception):
            v.value = "link"  # type: ignore[misc]


class TestAXNodeContract:
    def test_minimal_valid(self):
        n = AXNode(nodeId="1")
        assert n.nodeId == "1"
        assert n.role is None
        assert n.properties == []
        assert n.childIds == []
        assert n.ignored is False

    def test_full_roundtrip(self):
        n = AXNode(
            nodeId="n1",
            role=AXValue(type="role", value="button"),
            name=AXValue(type="computedString", value="Submit"),
            properties=[
                AXProperty(name="expanded", value=AXValue(type="booleanOrUndefined", value=True)),
            ],
            backendDOMNodeId=42,
            parentId="parent",
            childIds=["c1", "c2"],
            ignored=False,
        )
        assert n.backendDOMNodeId == 42
        assert len(n.properties) == 1
        assert n.properties[0].name == "expanded"


# -------------------------------------------------------------------------
# walk_ancestor_roles
# -------------------------------------------------------------------------

def _node(nid: str, role: str | None = None, parent: str | None = None) -> AXNode:
    return AXNode(
        nodeId=nid,
        role=AXValue(type="role", value=role) if role is not None else None,
        parentId=parent,
    )


class TestWalkAncestorRoles:
    def test_no_parent_returns_empty(self):
        n = _node("root", "main")
        assert endpoints.walk_ancestor_roles(n, {"root": n}) == []

    def test_single_parent(self):
        parent = _node("p", "main")
        child = _node("c", "button", parent="p")
        tree = {"p": parent, "c": child}
        assert endpoints.walk_ancestor_roles(child, tree) == ["main"]

    def test_three_deep_chain(self):
        gp = _node("gp", "WebArea")
        p = _node("p", "navigation", parent="gp")
        c = _node("c", "link", parent="p")
        tree = {"gp": gp, "p": p, "c": c}
        assert endpoints.walk_ancestor_roles(c, tree) == ["navigation", "WebArea"]

    def test_missing_parent_stops_walk(self):
        orphan = _node("c", "button", parent="missing-parent")
        tree = {"c": orphan}  # parent not in map
        assert endpoints.walk_ancestor_roles(orphan, tree) == []

    def test_parent_without_role_is_skipped(self):
        parent = _node("p", role=None, parent=None)
        child = _node("c", "button", parent="p")
        tree = {"p": parent, "c": child}
        # Parent exists but has no role → not appended, walk continues
        assert endpoints.walk_ancestor_roles(child, tree) == []

    def test_cap_protects_against_cycles(self):
        # Build a cycle of 3 nodes a → b → c → a (shouldn't happen in real AX trees,
        # but the walk must terminate regardless).
        a = _node("a", "generic", parent="b")
        b = _node("b", "generic", parent="c")
        c = _node("c", "generic", parent="a")
        tree = {"a": a, "b": b, "c": c}
        out = endpoints.walk_ancestor_roles(a, tree)
        # Should terminate at ANCESTOR_WALK_CAP; all roles are 'generic'
        assert len(out) == endpoints.ANCESTOR_WALK_CAP


# -------------------------------------------------------------------------
# is_valid_endpoint
# -------------------------------------------------------------------------

class TestIsValidEndpoint:
    def test_ignored_node_invalid(self):
        n = AXNode(nodeId="1", backendDOMNodeId=10, ignored=True)
        assert endpoints.is_valid_endpoint(n) is False

    def test_no_backend_dom_node_id_invalid(self):
        n = AXNode(nodeId="1", backendDOMNodeId=None, ignored=False)
        assert endpoints.is_valid_endpoint(n) is False

    def test_valid(self):
        n = AXNode(nodeId="1", backendDOMNodeId=10, ignored=False)
        assert endpoints.is_valid_endpoint(n) is True


# -------------------------------------------------------------------------
# ax_node_to_probe_record
# -------------------------------------------------------------------------

class TestAxNodeToProbeRecord:
    def test_minimal_node(self):
        n = AXNode(nodeId="1", role=AXValue(type="role", value="button"), backendDOMNodeId=10)
        rec = endpoints.ax_node_to_probe_record(n, {"1": n})
        assert isinstance(rec, ProbeRecord)
        assert rec.ax_role == "button"
        assert rec.ax_properties == {}
        assert rec.ancestor_ax_roles == []
        assert rec.accessible_name is None
        assert rec.tag_name is None

    def test_properties_extracted(self):
        n = AXNode(
            nodeId="1",
            role=AXValue(type="role", value="button"),
            properties=[
                AXProperty(name="expanded", value=AXValue(type="booleanOrUndefined", value=True)),
                AXProperty(name="hasPopup", value=AXValue(type="token", value="menu")),
            ],
            backendDOMNodeId=10,
        )
        rec = endpoints.ax_node_to_probe_record(n, {"1": n})
        assert rec.ax_properties == {"expanded": True, "hasPopup": "menu"}

    def test_hasPopup_regression_flows_through_fingerprint(self):
        """L-SPIKE-02 permanent tripwire: hasPopup camelCase must flow endpoints → fingerprint → bitmap."""
        from lantern import fingerprint as fp

        n = AXNode(
            nodeId="1",
            role=AXValue(type="role", value="button"),
            properties=[AXProperty(name="hasPopup", value=AXValue(type="token", value="menu"))],
            backendDOMNodeId=10,
        )
        rec = endpoints.ax_node_to_probe_record(n, {"1": n})
        tup = fp.probe_to_tuple(rec)
        assert tup.state_bitmap & int(StateBit.HASPOPUP) != 0

    def test_accessible_name_truncated_and_lowercased(self):
        long_name = "A" * 100
        n = AXNode(
            nodeId="1",
            role=AXValue(type="role", value="button"),
            name=AXValue(type="computedString", value=long_name),
            backendDOMNodeId=10,
        )
        rec = endpoints.ax_node_to_probe_record(n, {"1": n})
        assert rec.accessible_name is not None
        assert len(rec.accessible_name) == 64
        assert rec.accessible_name == "a" * 64

    def test_empty_accessible_name_is_none(self):
        n = AXNode(
            nodeId="1",
            role=AXValue(type="role", value="button"),
            name=AXValue(type="computedString", value=""),
            backendDOMNodeId=10,
        )
        rec = endpoints.ax_node_to_probe_record(n, {"1": n})
        assert rec.accessible_name is None

    def test_ancestor_chain(self):
        root = _node("r", "WebArea")
        main = _node("m", "main", parent="r")
        btn = AXNode(
            nodeId="b",
            role=AXValue(type="role", value="button"),
            name=AXValue(type="computedString", value="Click"),
            backendDOMNodeId=10,
            parentId="m",
        )
        tree = {"r": root, "m": main, "b": btn}
        rec = endpoints.ax_node_to_probe_record(btn, tree)
        assert rec.ancestor_ax_roles == ["main", "WebArea"]

    def test_tag_name_passed_through(self):
        n = AXNode(nodeId="1", role=AXValue(type="role", value="button"), backendDOMNodeId=10)
        rec = endpoints.ax_node_to_probe_record(n, {"1": n}, tag_name="button")
        assert rec.tag_name == "button"


# -------------------------------------------------------------------------
# extract_endpoints
# -------------------------------------------------------------------------

def _valid_leaf(nid: str, role: str, name: str, backend: int, parent: str | None) -> AXNode:
    return AXNode(
        nodeId=nid,
        role=AXValue(type="role", value=role),
        name=AXValue(type="computedString", value=name),
        backendDOMNodeId=backend,
        parentId=parent,
    )


class TestExtractEndpoints:
    def test_empty_tab_order_empty_output(self):
        assert endpoints.extract_endpoints([], []) == []

    def test_single_valid_endpoint(self):
        root = _node("r", "WebArea")
        btn = _valid_leaf("b", "button", "Go", 10, "r")
        out = endpoints.extract_endpoints(["b"], [root, btn])
        assert len(out) == 1
        assert out[0].ax_role == "button"
        assert out[0].accessible_name == "go"

    def test_skips_ignored_node(self):
        root = _node("r", "WebArea")
        btn = _valid_leaf("b", "button", "Go", 10, "r")
        ignored = AXNode(nodeId="i", role=AXValue(type="role", value="generic"),
                         backendDOMNodeId=11, parentId="r", ignored=True)
        out = endpoints.extract_endpoints(["i", "b"], [root, ignored, btn])
        # ignored is skipped; btn still produced
        assert len(out) == 1
        assert out[0].ax_role == "button"

    def test_skips_node_missing_backend_id(self):
        root = _node("r", "WebArea")
        btn = _valid_leaf("b", "button", "Go", 10, "r")
        orphan = AXNode(nodeId="o", role=AXValue(type="role", value="button"),
                        backendDOMNodeId=None, parentId="r")
        out = endpoints.extract_endpoints(["o", "b"], [root, orphan, btn])
        assert len(out) == 1
        assert out[0].ax_role == "button"

    def test_body_return_terminates(self):
        root = AXNode(nodeId="root", role=AXValue(type="role", value="WebArea"), backendDOMNodeId=1)
        btn1 = _valid_leaf("b1", "button", "One", 10, "root")
        btn2 = _valid_leaf("b2", "button", "Two", 11, "root")
        out = endpoints.extract_endpoints(["b1", "root", "b2"], [root, btn1, btn2])
        # body-return at root → stop, btn2 not included
        assert len(out) == 1
        assert out[0].accessible_name == "one"

    def test_already_seen_terminates(self):
        root = _node("r", "WebArea")
        btn1 = _valid_leaf("b1", "button", "One", 10, "r")
        btn2 = _valid_leaf("b2", "button", "Two", 11, "r")
        # b1 appears twice — second occurrence triggers cycle termination
        out = endpoints.extract_endpoints(["b1", "b2", "b1"], [root, btn1, btn2])
        assert len(out) == 2
        assert [r.accessible_name for r in out] == ["one", "two"]

    def test_dom_tags_populate_tag_name(self):
        root = _node("r", "WebArea")
        btn = _valid_leaf("b", "button", "Go", 10, "r")
        out = endpoints.extract_endpoints(["b"], [root, btn], dom_tags={10: "button"})
        assert out[0].tag_name == "button"

    def test_missing_node_id_skipped(self):
        root = _node("r", "WebArea")
        btn = _valid_leaf("b", "button", "Go", 10, "r")
        # 'unknown' id not in tree → silently skipped
        out = endpoints.extract_endpoints(["unknown", "b"], [root, btn])
        assert len(out) == 1

    def test_order_preserved(self):
        root = _node("r", "WebArea")
        a = _valid_leaf("a", "link", "A", 10, "r")
        b = _valid_leaf("b", "button", "B", 11, "r")
        c = _valid_leaf("c", "textbox", "C", 12, "r")
        out = endpoints.extract_endpoints(["a", "b", "c"], [root, a, b, c])
        assert [rec.ax_role for rec in out] == ["link", "button", "textbox"]


# -------------------------------------------------------------------------
# Fixture JSON roundtrip (§R3 L-03 requirement)
# -------------------------------------------------------------------------

class TestFixtureRoundtrip:
    def _load_fixture(self) -> dict:
        with FIXTURE_BASIC.open("r") as f:
            return json.load(f)

    def _parse_ax_tree(self, raw: list[dict]) -> list[AXNode]:
        return [AXNode.model_validate(n) for n in raw]

    def test_basic_fixture_produces_expected_records(self):
        data = self._load_fixture()
        ax_tree = self._parse_ax_tree(data["ax_tree"])
        tab_order = data["tab_order_node_ids"]
        dom_tags = {int(k): v for k, v in data["dom_tags"].items()}

        out = endpoints.extract_endpoints(tab_order, ax_tree, dom_tags=dom_tags)

        expected = data["expected"]
        assert len(out) == expected["probe_record_count"]
        assert [rec.ax_role for rec in out] == expected["ordered_ax_roles"]
        assert [rec.accessible_name for rec in out] == expected["ordered_accessible_names"]

    def test_basic_fixture_hasPopup_flows_through(self):
        """Permanent L-SPIKE-02 tripwire: fixture's btn1 carries hasPopup — must land in final bitmap."""
        from lantern import fingerprint as fp

        data = self._load_fixture()
        ax_tree = self._parse_ax_tree(data["ax_tree"])
        tab_order = data["tab_order_node_ids"]
        out = endpoints.extract_endpoints(tab_order, ax_tree)

        # Find the button record
        btn_rec = next(r for r in out if r.ax_role == "button")
        tup = fp.probe_to_tuple(btn_rec)
        assert tup.state_bitmap & int(StateBit.HASPOPUP) != 0, (
            "Fixture's btn1 hasPopup='menu' must reach the HASPOPUP bit in the fingerprint."
        )

    def test_basic_fixture_button_landmark_is_main(self):
        data = self._load_fixture()
        ax_tree = self._parse_ax_tree(data["ax_tree"])
        tab_order = data["tab_order_node_ids"]
        out = endpoints.extract_endpoints(tab_order, ax_tree)

        from lantern import fingerprint as fp
        btn_rec = next(r for r in out if r.ax_role == "button")
        tup = fp.probe_to_tuple(btn_rec)
        assert tup.landmark == "main"
