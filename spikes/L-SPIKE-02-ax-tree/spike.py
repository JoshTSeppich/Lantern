"""
L-SPIKE-02 — CDP `Accessibility.getFullAXTree` coverage

Verifies that CDP surfaces:

  (A) each of the eight state-bitmap fields from LANTERN.md Part 4 Step 1
      — expanded | haspopup | selected | checked | disabled | required |
      invalid | readonly — under the exact property-name the
      state-bitmap contract assumes. One fixture element per field
      (plus native/ARIA duplicates where applicable).

  (B) landmark ancestry traversal for each of the five HTML-tag
      landmarks named in Part 4 Step 1 — main / nav / header / footer /
      aside. Verified by picking an ID'd descendant of each landmark,
      resolving its AX node, walking parentId up, and confirming the
      expected AX-role-landmark appears in the ancestor chain.

Halt-and-flag conditions (user directive 2026-04-20):
  - any state-bitmap field not surfaced by CDP under the expected
    property-name on at least one fixture element
  - CDP returns a property-name or value-shape different from what
    Part 4 Step 1's bitmap enumeration assumes
  - any landmark missing from the AX tree
  - any descendant's ancestry chain missing the expected landmark role

A halt-and-flag is a successful spike outcome per BUILD.md §R4 — the
spike script exits RED and the README documents the gap requiring
ADR + refreeze before fingerprint.py begins.

Pinned Playwright: 1.58.0 (see pyproject.toml, BUILD.md §R1.2).
"""

from __future__ import annotations

import json
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

FIXTURE = Path(__file__).parent / "fixture.html"

# ----------------------------------------------------------------------
# Contract — Part 4 Step 1 state-bitmap fields and fixture element ids
# ----------------------------------------------------------------------

STATE_FIELD_EXPECTATIONS: dict[str, list[str]] = {
    "expanded": ["state-expanded"],
    "haspopup": ["state-haspopup"],
    "selected": ["state-selected"],
    "checked":  ["state-checked-native", "state-checked-aria"],
    "disabled": ["state-disabled-native", "state-disabled-aria"],
    "required": ["state-required-native", "state-required-aria"],
    "invalid":  ["state-invalid"],
    "readonly": ["state-readonly-native", "state-readonly-aria"],
}

# ----------------------------------------------------------------------
# Contract — Part 4 Step 1 landmark HTML tags mapped to CDP AX roles
# ----------------------------------------------------------------------

LANDMARK_EXPECTATIONS: dict[str, dict[str, str]] = {
    "main":   {"dom_id": "main-content",  "ax_role": "main"},
    "nav":    {"dom_id": "primary-nav",   "ax_role": "navigation"},
    "header": {"dom_id": "page-header",   "ax_role": "banner"},
    "footer": {"dom_id": "page-footer",   "ax_role": "contentinfo"},
    "aside":  {"dom_id": "sidebar",       "ax_role": "complementary"},
}

ANCESTRY_DESCENDANTS: dict[str, str] = {
    "main-heading":   "main",
    "nav-link-1":     "nav",
    "banner-heading": "header",
    "sidebar-para":   "aside",
    "footer-para":    "footer",
}


def parse_dom_attrs(flat: list[str]) -> dict[str, str]:
    """CDP DOM.Node.attributes is a flat list [name1, val1, name2, val2, ...]. Convert to dict."""
    out: dict[str, str] = {}
    for i in range(0, len(flat) - 1, 2):
        out[flat[i]] = flat[i + 1]
    return out


def extract_property_value(prop_value: dict[str, Any]) -> Any:
    """CDP AXValue has {type, value, relatedNodes?}. Return the .value payload."""
    if prop_value is None:
        return None
    return prop_value.get("value")


def build_fixture_map(cdp, nodes: list[dict]) -> dict[str, dict]:
    """Map fixture-element id → AX node, by resolving each node's backendDOMNodeId."""
    fixture_map: dict[str, dict] = {}
    for node in nodes:
        backend_id = node.get("backendDOMNodeId")
        if backend_id is None:
            continue
        try:
            described = cdp.send("DOM.describeNode", {"backendNodeId": backend_id})
        except Exception:
            continue
        attrs = parse_dom_attrs(described.get("node", {}).get("attributes", []))
        dom_id = attrs.get("id")
        if dom_id:
            fixture_map[dom_id] = node
    return fixture_map


def verify_state_coverage(fixture_map: dict[str, dict]) -> dict[str, dict]:
    """For each of the 8 bitmap fields, verify at least one fixture element has the field surfaced."""
    results: dict[str, dict] = {}
    for field, element_ids in STATE_FIELD_EXPECTATIONS.items():
        per_element = []
        for eid in element_ids:
            node = fixture_map.get(eid)
            if node is None:
                per_element.append({
                    "element_id": eid,
                    "status": "element_absent_from_ax_tree",
                    "ignored": None,
                    "role": None,
                    "surfaced_property": None,
                    "surfaced_value": None,
                    "all_property_names": [],
                })
                continue
            props = {p["name"]: extract_property_value(p.get("value")) for p in node.get("properties", [])}
            if field in props:
                per_element.append({
                    "element_id": eid,
                    "status": "surfaced",
                    "ignored": node.get("ignored", False),
                    "role": (node.get("role") or {}).get("value"),
                    "surfaced_property": field,
                    "surfaced_value": props[field],
                    "all_property_names": sorted(props.keys()),
                })
            else:
                per_element.append({
                    "element_id": eid,
                    "status": "field_not_surfaced_on_element",
                    "ignored": node.get("ignored", False),
                    "role": (node.get("role") or {}).get("value"),
                    "surfaced_property": None,
                    "surfaced_value": None,
                    "all_property_names": sorted(props.keys()),
                })
        field_covered = any(r["status"] == "surfaced" for r in per_element)
        results[field] = {
            "field_covered": field_covered,
            "elements": per_element,
        }
    return results


def verify_landmark_coverage(fixture_map: dict[str, dict]) -> dict[str, dict]:
    """Each of 5 landmark HTML tags must have its expected AX role surfaced on the matching fixture element."""
    results: dict[str, dict] = {}
    for html_tag, exp in LANDMARK_EXPECTATIONS.items():
        node = fixture_map.get(exp["dom_id"])
        if node is None:
            results[html_tag] = {
                "status": "landmark_element_absent_from_ax_tree",
                "dom_id": exp["dom_id"],
                "expected_ax_role": exp["ax_role"],
                "actual_ax_role": None,
                "ignored": None,
            }
            continue
        actual_role = (node.get("role") or {}).get("value")
        ignored = node.get("ignored", False)
        if actual_role == exp["ax_role"] and not ignored:
            status = "surfaced"
        elif actual_role != exp["ax_role"]:
            status = "role_mismatch"
        else:  # ignored
            status = "ignored_by_ax_tree"
        results[html_tag] = {
            "status": status,
            "dom_id": exp["dom_id"],
            "expected_ax_role": exp["ax_role"],
            "actual_ax_role": actual_role,
            "ignored": ignored,
        }
    return results


def verify_ancestry_traversal(fixture_map: dict[str, dict], nodes: list[dict]) -> dict[str, dict]:
    """For each ID'd descendant, walk parentId up and confirm expected landmark AX role is an ancestor."""
    by_node_id = {n["nodeId"]: n for n in nodes}
    results: dict[str, dict] = {}
    for descendant_id, landmark_tag in ANCESTRY_DESCENDANTS.items():
        expected_role = LANDMARK_EXPECTATIONS[landmark_tag]["ax_role"]
        node = fixture_map.get(descendant_id)
        if node is None:
            results[descendant_id] = {
                "status": "descendant_absent_from_ax_tree",
                "landmark_tag": landmark_tag,
                "expected_ancestor_role": expected_role,
                "ancestor_roles_walked": [],
            }
            continue
        walked = []
        current = node
        hops = 0
        while current and current.get("parentId") and hops < 100:
            parent = by_node_id.get(current["parentId"])
            if not parent:
                break
            role = (parent.get("role") or {}).get("value")
            if role:
                walked.append(role)
            current = parent
            hops += 1
        found = expected_role in walked
        results[descendant_id] = {
            "status": "ancestor_found" if found else "ancestor_missing",
            "landmark_tag": landmark_tag,
            "expected_ancestor_role": expected_role,
            "ancestor_roles_walked": walked,
        }
    return results


def main() -> int:
    pw_version = version("playwright")

    results: dict[str, Any] = {
        "spike_id": "L-SPIKE-02",
        "playwright_version": pw_version,
        "fixture_path": str(FIXTURE),
        "cdp_calls_used": ["DOM.enable", "Accessibility.enable", "Accessibility.getFullAXTree", "DOM.describeNode"],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            cdp = context.new_cdp_session(page)

            cdp.send("DOM.enable")
            cdp.send("Accessibility.enable")

            page.goto(FIXTURE.as_uri())
            page.wait_for_load_state("networkidle")

            ax = cdp.send("Accessibility.getFullAXTree")
            nodes: list[dict] = ax.get("nodes", [])
            results["ax_tree_node_count"] = len(nodes)

            fixture_map = build_fixture_map(cdp, nodes)
            results["fixture_element_ids_resolved"] = sorted(fixture_map.keys())

            results["state_coverage"]  = verify_state_coverage(fixture_map)
            results["landmark_coverage"] = verify_landmark_coverage(fixture_map)
            results["ancestry_traversal"] = verify_ancestry_traversal(fixture_map, nodes)
        finally:
            browser.close()

    # Verdict aggregation
    state_fields_covered = {f: v["field_covered"] for f, v in results["state_coverage"].items()}
    all_states_covered = all(state_fields_covered.values())
    missing_states = [f for f, covered in state_fields_covered.items() if not covered]

    landmarks_covered = {t: v["status"] == "surfaced" for t, v in results["landmark_coverage"].items()}
    all_landmarks_covered = all(landmarks_covered.values())
    missing_landmarks = [t for t, ok in landmarks_covered.items() if not ok]

    ancestry_covered = {d: v["status"] == "ancestor_found" for d, v in results["ancestry_traversal"].items()}
    all_ancestry_traversed = all(ancestry_covered.values())
    missing_ancestry = [d for d, ok in ancestry_covered.items() if not ok]

    all_green = all_states_covered and all_landmarks_covered and all_ancestry_traversed
    results["verdict"] = "GREEN" if all_green else "RED"
    results["claim_A_all_state_fields_covered"] = all_states_covered
    results["claim_B_all_landmarks_covered"] = all_landmarks_covered
    results["claim_C_all_ancestry_traversed"] = all_ancestry_traversed
    results["missing_state_fields"] = missing_states
    results["missing_landmarks"] = missing_landmarks
    results["missing_ancestry"] = missing_ancestry

    out_path = Path(__file__).parent / "spike_results.json"
    out_path.write_text(json.dumps(results, indent=2))

    # Console summary
    print("L-SPIKE-02 — Accessibility.getFullAXTree coverage")
    print("=" * 60)
    print(f"Playwright: {pw_version}")
    print(f"Fixture: {FIXTURE}")
    print(f"AX tree node count: {results['ax_tree_node_count']}")
    print(f"Fixture elements resolved from AX tree: {len(results['fixture_element_ids_resolved'])}")
    print()

    print("Claim A — state-bitmap field coverage (Part 4 Step 1):")
    for field, covered in state_fields_covered.items():
        label = "KNOWN" if covered else "MISSING"
        ex = results["state_coverage"][field]["elements"][0]
        if covered:
            detail = f"surfaced as '{ex['surfaced_property']}'={ex['surfaced_value']!r} on #{ex['element_id']}"
        else:
            checked_ids = ", ".join("#" + e["element_id"] for e in results["state_coverage"][field]["elements"])
            detail = f"absent — checked on {checked_ids}"
        print(f"  [{label:7s}] {field:9s} — {detail}")
    print()

    print("Claim B — landmark HTML-tag → AX-role coverage:")
    for tag, info in results["landmark_coverage"].items():
        label = "KNOWN" if info["status"] == "surfaced" else "MISSING"
        print(f"  [{label:7s}] <{tag}> on #{info['dom_id']} → expected role={info['expected_ax_role']}, actual={info['actual_ax_role']} (ignored={info['ignored']})")
    print()

    print("Claim C — descendant → landmark ancestry traversal:")
    for did, info in results["ancestry_traversal"].items():
        label = "KNOWN" if info["status"] == "ancestor_found" else "MISSING"
        print(f"  [{label:7s}] #{did} → ancestor role='{info['expected_ancestor_role']}' — status={info['status']}")
    print()

    print(f"VERDICT: {results['verdict']}")
    print(f"Results: {out_path}")
    if not all_green:
        print()
        print("HALT-AND-FLAG (per user directive 2026-04-20):")
        if missing_states:
            print(f"  - state-bitmap fields missing or under different property-name: {missing_states}")
            print("    → state-bitmap contract break; requires ADR + refreeze before fingerprint.py begins")
        if missing_landmarks:
            print(f"  - landmarks not surfaced: {missing_landmarks}")
        if missing_ancestry:
            print(f"  - ancestry traversal failed for: {missing_ancestry}")

    return 0 if all_green else 1


if __name__ == "__main__":
    sys.exit(main())
