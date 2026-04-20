"""
L-SPIKE-01 — Tab order + document.activeElement readback

Verifies three claims from BUILD.md §R3 L-SPIKE-01:
  1. Playwright `page.keyboard.press('Tab')` produces a deterministic focus
     traversal on a fixture page with 20 focusable elements of varying types.
  2. `document.activeElement` always resolves (never null/undefined) after Tab.
  3. Full-cycle termination is detectable by returning to `document.body`
     or by element-already-seen detection.

Pinned Playwright: 1.58.0 (see pyproject.toml, BUILD.md §R1.2).

Exit code 0 if all claims verified (GREEN), 1 otherwise (RED).
Results dumped to `spike_results.json` in this directory.
"""

from __future__ import annotations

import json
import sys
from importlib.metadata import version
from pathlib import Path

from playwright.sync_api import sync_playwright

FIXTURE = Path(__file__).parent / "fixture.html"
MAX_TABS = 50  # safety cap; fixture has 20 focusable elements
PASSES = 3


def capture_active_element(page) -> dict | None:
    """Return a descriptor of `document.activeElement`, or None if absent."""
    return page.evaluate(
        """
        () => {
            const el = document.activeElement;
            if (!el) return null;
            return {
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                role: el.getAttribute('role') || null,
                aria_label: el.getAttribute('aria-label') || null,
                type: el.getAttribute('type') || null,
                tabindex: el.getAttribute('tabindex') || null,
                text_snippet: (el.textContent || '').trim().slice(0, 40),
            };
        }
        """
    )


def element_key(el: dict) -> str:
    """Stable key for an element descriptor, for deduplication and comparison."""
    if el.get("id"):
        return f"id:{el['id']}"
    parts = [el["tag"], el.get("role") or "", el.get("aria_label") or "", el.get("type") or "", el.get("text_snippet") or ""]
    return "|".join(parts)


def run_single_pass(page) -> dict:
    """Tab through the page up to MAX_TABS times. Record the sequence and termination mode."""
    page.evaluate("() => document.body.focus()")

    sequence: list[dict] = []
    seen_keys: list[str] = []
    returned_to_body = False
    cycle_detected_at_press: int | None = None
    any_null_active: bool = False

    for i in range(1, MAX_TABS + 1):
        page.keyboard.press("Tab")
        el = capture_active_element(page)

        if el is None:
            any_null_active = True
            sequence.append({"press": i, "active": None})
            continue

        sequence.append({"press": i, "active": el})

        if el["tag"] == "body":
            returned_to_body = True
            break

        k = element_key(el)
        if k in seen_keys:
            cycle_detected_at_press = i
            break
        seen_keys.append(k)

    return {
        "sequence": sequence,
        "unique_keys_visited": seen_keys,
        "num_unique": len(seen_keys),
        "returned_to_body": returned_to_body,
        "cycle_detected_at_press": cycle_detected_at_press,
        "any_null_active": any_null_active,
    }


def main() -> int:
    pw_version = version("playwright")

    results: dict = {
        "spike_id": "L-SPIKE-01",
        "playwright_version": pw_version,
        "fixture_path": str(FIXTURE),
        "max_tabs_per_pass": MAX_TABS,
        "num_passes": PASSES,
        "passes": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for _ in range(PASSES):
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.goto(FIXTURE.as_uri())
                page.wait_for_load_state("networkidle")
                results["passes"].append(run_single_pass(page))
                page.close()
        finally:
            browser.close()

    # Claim 1 — determinism: all passes produce the same sequence of unique keys.
    keys_per_pass = [p_["unique_keys_visited"] for p_ in results["passes"]]
    deterministic = all(k == keys_per_pass[0] for k in keys_per_pass[1:])
    results["claim_1_deterministic"] = deterministic

    # Claim 2 — activeElement always resolves: no pass saw a null active element.
    any_null = any(p_["any_null_active"] for p_ in results["passes"])
    results["claim_2_active_element_always_resolves"] = not any_null

    # Claim 3 — termination detectable: each pass terminated via body-return OR cycle-detection.
    termination_modes = [
        {
            "returned_to_body": p_["returned_to_body"],
            "cycle_detected_at_press": p_["cycle_detected_at_press"],
            "terminated": p_["returned_to_body"] or p_["cycle_detected_at_press"] is not None,
        }
        for p_ in results["passes"]
    ]
    results["termination_modes_per_pass"] = termination_modes
    termination_detectable = all(m["terminated"] for m in termination_modes)
    results["claim_3_termination_detectable"] = termination_detectable

    all_green = deterministic and (not any_null) and termination_detectable
    results["verdict"] = "GREEN" if all_green else "RED"

    out_path = Path(__file__).parent / "spike_results.json"
    out_path.write_text(json.dumps(results, indent=2))

    # Console summary
    print("L-SPIKE-01 — Tab order + activeElement readback")
    print("=" * 60)
    print(f"Playwright version: {pw_version}")
    print(f"Fixture: {FIXTURE}")
    print(f"Passes: {PASSES}, Max Tab presses per pass: {MAX_TABS}")
    print()
    for idx, (p_, mode) in enumerate(zip(results["passes"], termination_modes), start=1):
        print(
            f"Pass {idx}: {p_['num_unique']} unique elements, "
            f"returned_to_body={mode['returned_to_body']}, "
            f"cycle_at_press={mode['cycle_detected_at_press']}"
        )
    print()
    print(f"[{'KNOWN' if deterministic else 'FAIL'}] Claim 1 — Tab order deterministic across {PASSES} passes: {deterministic}")
    print(f"[{'KNOWN' if not any_null else 'FAIL'}] Claim 2 — document.activeElement always resolves: {not any_null}")
    print(f"[{'KNOWN' if termination_detectable else 'FAIL'}] Claim 3 — Full-cycle termination detectable: {termination_detectable}")
    print()
    print(f"VERDICT: {results['verdict']}")
    print(f"Results: {out_path}")

    return 0 if all_green else 1


if __name__ == "__main__":
    sys.exit(main())
