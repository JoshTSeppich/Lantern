"""
L-SPIKE-04 — Mutation observer + settlement detection

Per BUILD.md §R3 L-SPIKE-04 (settlement defined as 'networkidle + 2000ms +
no mutations in observer for 500ms, capped at 8s total') and operator
tight spec (2026-04-20), verify the detector can reliably distinguish
three post-click states — not collapse them to binary:

  1. settled-post-state-change — mutations fired, then 500ms quiet
  2. unchanged-by-interaction — no mutations at all; click had no effect
  3. in-transition — mutations still firing when cap is hit

Plus characterize two failure modes (not just avoid):

  - false-negative — state change happened but observer missed it
    (probed by Case C: progressive mutation, 3×200ms)
  - false-positive — no real state change but observer fired (false delta)
    (probed by Case B: click on button with no handler)

Ranked #2 (behind L-SPIKE-02) despite higher probability of failure
because the scope-down path is architected: L-SPIKE-04 RED invokes
LANTERN.md Part 5 Completeness Fail branch → drop Methodology D and
proceed with A+B+C only. That scope-down-ability is what made it
acceptable to sequence this spike after L-SPIKE-02.

Pinned Playwright: 1.58.0 (see pyproject.toml, BUILD.md §R1.2).
"""

from __future__ import annotations

import json
import sys
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

FIXTURE = Path(__file__).parent / "fixture.html"

# Settlement definition from BUILD.md §R3 L-SPIKE-04
QUIET_MS = 500
CAP_MS_DEFAULT = 8000

DETECTOR_JS = """
async ({selector, quietMs, capMs}) => {
    return new Promise((resolve) => {
        const mutations = [];
        const startTime = performance.now();
        let lastMutationTime = null;

        const observer = new MutationObserver((records) => {
            for (const r of records) {
                mutations.push({
                    type: r.type,
                    target: r.target.nodeName || null,
                    added: r.addedNodes.length,
                    removed: r.removedNodes.length,
                    attr: r.attributeName || null,
                    ts_ms: performance.now() - startTime,
                });
            }
            lastMutationTime = performance.now();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            characterData: true,
        });

        const btn = document.querySelector(selector);
        const clickTime = performance.now();
        btn.click();

        const tick = () => {
            const now = performance.now();
            const elapsed = now - startTime;
            const referenceTime = lastMutationTime || clickTime;
            const quietElapsed = now - referenceTime;

            if (elapsed >= capMs) {
                observer.disconnect();
                let state;
                if (mutations.length === 0) {
                    state = 'unchanged-by-interaction';
                } else if (quietElapsed >= quietMs) {
                    state = 'settled-post-state-change';
                } else {
                    state = 'in-transition';
                }
                resolve({
                    state,
                    cap_hit: true,
                    mutation_count: mutations.length,
                    elapsed_ms: elapsed,
                    quiet_elapsed_at_resolution_ms: quietElapsed,
                    mutations: mutations.slice(0, 20),
                    mutations_truncated: mutations.length > 20,
                });
                return;
            }

            if (quietElapsed >= quietMs) {
                observer.disconnect();
                const state = mutations.length === 0 ? 'unchanged-by-interaction' : 'settled-post-state-change';
                resolve({
                    state,
                    cap_hit: false,
                    mutation_count: mutations.length,
                    elapsed_ms: elapsed,
                    quiet_elapsed_at_resolution_ms: quietElapsed,
                    mutations: mutations.slice(0, 20),
                    mutations_truncated: mutations.length > 20,
                });
                return;
            }

            setTimeout(tick, 50);
        };

        setTimeout(tick, 50);
    });
}
"""

TEST_CASES: list[dict[str, Any]] = [
    {
        "id": "A",
        "selector": "#btn-state-change",
        "description": "Reveal hidden panel (one-shot DOM mutation — classList.remove). Happy path baseline.",
        "expected_state": "settled-post-state-change",
        "expected_mutation_count_min": 1,
        "expected_mutation_count_max": 3,
        "expected_elapsed_ms_min": 500,
        "expected_elapsed_ms_max": 800,
        "cap_ms": CAP_MS_DEFAULT,
        "probes_failure_mode": "happy-path — verifies observer catches a real attribute mutation and declares settled after 500ms quiet.",
    },
    {
        "id": "B",
        "selector": "#btn-no-op",
        "description": "Click button with no handler. Probes false-positive.",
        "expected_state": "unchanged-by-interaction",
        "expected_mutation_count_min": 0,
        "expected_mutation_count_max": 0,
        "expected_elapsed_ms_min": 500,
        "expected_elapsed_ms_max": 800,
        "cap_ms": CAP_MS_DEFAULT,
        "probes_failure_mode": "false-positive — observer must register 0 mutations; detector must classify as unchanged-by-interaction (not settled-post-state-change).",
    },
    {
        "id": "C",
        "selector": "#btn-progressive",
        "description": "Fire 3 mutations at 0/200/400 ms. Probes false-negative (quiet-window reset).",
        "expected_state": "settled-post-state-change",
        "expected_mutation_count_min": 3,
        "expected_mutation_count_max": 5,
        "expected_elapsed_ms_min": 800,
        "expected_elapsed_ms_max": 1300,
        "cap_ms": CAP_MS_DEFAULT,
        "probes_failure_mode": "false-negative — broken detector would settle after the first 500ms quiet window, missing mutations 2 and 3. Verifies quiet window RESETS on each new mutation rather than measuring from a fixed reference point.",
    },
    {
        "id": "D",
        "selector": "#btn-continuous",
        "description": "Continuous mutations every 100ms. Probes cap-boundary in-transition classification.",
        "expected_state": "in-transition",
        "expected_mutation_count_min": 15,
        "expected_mutation_count_max": None,
        "expected_elapsed_ms_min": 1950,
        "expected_elapsed_ms_max": 2200,
        "cap_ms": 2000,  # reduced from 8000ms default for spike runtime efficiency
        "probes_failure_mode": "cap-boundary — ongoing mutations must be classified as in-transition (not settled-post-state-change, not unchanged-by-interaction). Verifies the three-state distinction holds at cap.",
    },
]


def main() -> int:
    pw_version = version("playwright")
    results: dict[str, Any] = {
        "spike_id": "L-SPIKE-04",
        "playwright_version": pw_version,
        "fixture_path": str(FIXTURE),
        "settlement_definition": (
            f"networkidle + 2000ms + no mutations in observer for {QUIET_MS}ms, "
            f"capped at {CAP_MS_DEFAULT}ms total (Case D uses a reduced cap of 2000ms for spike runtime)"
        ),
        "quiet_ms": QUIET_MS,
        "cap_ms_default": CAP_MS_DEFAULT,
        "cases": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            for case in TEST_CASES:
                page = context.new_page()
                page.goto(FIXTURE.as_uri())
                page.wait_for_load_state("networkidle")
                page.wait_for_function("window.__fixtureReady === true")
                # Settlement step 2 per LANTERN.md Part 4 Step 4: networkidle + 2000ms
                time.sleep(2.0)

                detector_result = page.evaluate(
                    DETECTOR_JS,
                    {"selector": case["selector"], "quietMs": QUIET_MS, "capMs": case["cap_ms"]},
                )

                state_match = detector_result["state"] == case["expected_state"]
                count_min_ok = detector_result["mutation_count"] >= case["expected_mutation_count_min"]
                count_max = case.get("expected_mutation_count_max")
                count_max_ok = count_max is None or detector_result["mutation_count"] <= count_max
                elapsed_min_ok = detector_result["elapsed_ms"] >= case["expected_elapsed_ms_min"]
                elapsed_max_ok = detector_result["elapsed_ms"] <= case["expected_elapsed_ms_max"]
                case_pass = all([state_match, count_min_ok, count_max_ok, elapsed_min_ok, elapsed_max_ok])

                results["cases"].append({
                    "case_id": case["id"],
                    "description": case["description"],
                    "probes_failure_mode": case["probes_failure_mode"],
                    "selector": case["selector"],
                    "cap_ms_used": case["cap_ms"],
                    "expected": {
                        "state": case["expected_state"],
                        "mutation_count_min": case["expected_mutation_count_min"],
                        "mutation_count_max": case["expected_mutation_count_max"],
                        "elapsed_ms_min": case["expected_elapsed_ms_min"],
                        "elapsed_ms_max": case["expected_elapsed_ms_max"],
                    },
                    "detector_result": detector_result,
                    "checks": {
                        "state_match": state_match,
                        "count_min_ok": count_min_ok,
                        "count_max_ok": count_max_ok,
                        "elapsed_min_ok": elapsed_min_ok,
                        "elapsed_max_ok": elapsed_max_ok,
                    },
                    "case_pass": case_pass,
                })

                page.close()
        finally:
            browser.close()

    all_cases_pass = all(c["case_pass"] for c in results["cases"])
    observed_states = sorted({c["detector_result"]["state"] for c in results["cases"]})
    three_states_distinguished = set(observed_states) == {
        "settled-post-state-change", "unchanged-by-interaction", "in-transition",
    }
    case_A_pass = next(c["case_pass"] for c in results["cases"] if c["case_id"] == "A")
    case_B_pass = next(c["case_pass"] for c in results["cases"] if c["case_id"] == "B")
    case_C_pass = next(c["case_pass"] for c in results["cases"] if c["case_id"] == "C")
    case_D_pass = next(c["case_pass"] for c in results["cases"] if c["case_id"] == "D")

    results["observed_states"] = observed_states
    results["claim_1_three_states_distinguished"] = three_states_distinguished
    results["claim_2_happy_path_A"] = case_A_pass
    results["claim_3_false_positive_probe_B"] = case_B_pass
    results["claim_4_false_negative_probe_C"] = case_C_pass
    results["claim_5_cap_boundary_D"] = case_D_pass
    results["claim_6_all_cases_pass"] = all_cases_pass
    all_green = three_states_distinguished and all_cases_pass
    results["verdict"] = "GREEN" if all_green else "RED"

    out = Path(__file__).parent / "spike_results.json"
    out.write_text(json.dumps(results, indent=2))

    # Console summary
    print("L-SPIKE-04 — Mutation observer + settlement detection")
    print("=" * 60)
    print(f"Playwright: {pw_version}")
    print(f"Settlement: {results['settlement_definition']}")
    print()
    for c in results["cases"]:
        label = "PASS" if c["case_pass"] else "FAIL"
        d = c["detector_result"]
        print(f"[{label}] Case {c['case_id']} — {c['description']}")
        print(f"         observed:  state={d['state']} mutations={d['mutation_count']} elapsed={d['elapsed_ms']:.1f}ms cap_hit={d['cap_hit']}")
        print(f"         expected:  state={c['expected']['state']} "
              f"mutations=[{c['expected']['mutation_count_min']}..{c['expected']['mutation_count_max']}] "
              f"elapsed=[{c['expected']['elapsed_ms_min']}..{c['expected']['elapsed_ms_max']}]")
        print(f"         failure mode probed: {c['probes_failure_mode']}")
        print()

    print(f"Observed states across cases: {observed_states}")
    print()
    print(f"[{'KNOWN' if three_states_distinguished else 'FAIL'}] Claim 1 — All three states distinguishable: {three_states_distinguished}")
    print(f"[{'KNOWN' if case_A_pass else 'FAIL'}] Claim 2 — Happy path (Case A) passes: {case_A_pass}")
    print(f"[{'KNOWN' if case_B_pass else 'FAIL'}] Claim 3 — False-positive probe (Case B) passes: {case_B_pass}")
    print(f"[{'KNOWN' if case_C_pass else 'FAIL'}] Claim 4 — False-negative probe (Case C) passes: {case_C_pass}")
    print(f"[{'KNOWN' if case_D_pass else 'FAIL'}] Claim 5 — Cap-boundary (Case D) passes: {case_D_pass}")
    print()
    print(f"VERDICT: {results['verdict']}")
    print(f"Results: {out}")

    if not all_green:
        print()
        print("SCOPE-DOWN TRIGGER (per operator directive 2026-04-20):")
        print("  L-SPIKE-04 RED invokes LANTERN.md Part 5 Completeness Fail branch.")
        print("  ADR required to formally drop Methodology D and proceed with A+B+C only.")
        print("  This is not a halt — the scope-down path is architected. rescan.py is")
        print("  dropped; fingerprint.py/endpoints.py/grouping.py proceed as A+B+C.")

    return 0 if all_green else 1


if __name__ == "__main__":
    sys.exit(main())
