"""
L-SPIKE-03 — getComputedStyle cost benchmark

Per BUILD.md §R3 L-SPIKE-03: verify that computing styles for 200 focusable
elements stays under a 2-second wall-clock total. If it exceeds, flag and
investigate alternatives (layout-parent-only snapshot, deferred snapshot,
skip).

Claims verified:
  1. Fixture exposes exactly 200 focusable elements.
  2. In-browser wall-clock cost of one getComputedStyle snapshot per
     element (reading ~10 properties relevant to Methodology C layout
     grouping) stays under 2000 ms across multiple passes.

Pinned Playwright: 1.58.0 (see pyproject.toml, BUILD.md §R1.2).
"""

from __future__ import annotations

import json
import sys
import time
from importlib.metadata import version
from pathlib import Path
from statistics import median

from playwright.sync_api import sync_playwright

FIXTURE = Path(__file__).parent / "fixture.html"
TARGET_ELEMENT_COUNT = 200
CAP_MS = 2000
PASSES = 5  # plus one warm-up


BENCHMARK_SCRIPT = """
() => {
    const els = document.querySelectorAll('button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])');
    const start = performance.now();
    // Read a realistic set of properties Grouping.py will care about
    // (layout-grid / flex grouping — Part 3 Methodology C, Part 4 Step 2).
    let sampleFirst = null;
    for (let i = 0; i < els.length; i++) {
        const cs = window.getComputedStyle(els[i]);
        const rec = {
            display: cs.display,
            position: cs.position,
            gridColumn: cs.gridColumn,
            gridRow: cs.gridRow,
            flexDirection: cs.flexDirection,
            flexBasis: cs.flexBasis,
            width: cs.width,
            height: cs.height,
            margin: cs.margin,
            padding: cs.padding,
        };
        if (i === 0) sampleFirst = rec;
    }
    const end = performance.now();
    return {
        element_count: els.length,
        elapsed_ms: end - start,
        per_element_us: ((end - start) * 1000) / els.length,
        sample_first: sampleFirst,
    };
}
"""


def main() -> int:
    pw_version = version("playwright")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            page.goto(FIXTURE.as_uri())
            page.wait_for_load_state("networkidle")
            page.wait_for_function("window.__fixtureReady === true")

            # Warm-up to pay any JIT / first-call overhead
            py_warmup_start = time.perf_counter()
            warmup = page.evaluate(BENCHMARK_SCRIPT)
            py_warmup_elapsed_ms = (time.perf_counter() - py_warmup_start) * 1000

            runs: list[dict] = []
            py_roundtrips_ms: list[float] = []
            for _ in range(PASSES):
                py_start = time.perf_counter()
                run = page.evaluate(BENCHMARK_SCRIPT)
                py_elapsed_ms = (time.perf_counter() - py_start) * 1000
                runs.append(run)
                py_roundtrips_ms.append(py_elapsed_ms)
        finally:
            browser.close()

    in_browser_ms = [r["elapsed_ms"] for r in runs]
    per_element_us = [r["per_element_us"] for r in runs]
    count = runs[0]["element_count"]

    results = {
        "spike_id": "L-SPIKE-03",
        "playwright_version": pw_version,
        "fixture_path": str(FIXTURE),
        "target_element_count": TARGET_ELEMENT_COUNT,
        "observed_element_count": count,
        "cap_ms": CAP_MS,
        "passes": PASSES,
        "properties_read_per_element": 10,
        "property_names_read": [
            "display", "position", "gridColumn", "gridRow",
            "flexDirection", "flexBasis", "width", "height", "margin", "padding",
        ],
        "warmup_in_browser_ms": warmup["elapsed_ms"],
        "warmup_py_roundtrip_ms": py_warmup_elapsed_ms,
        "in_browser_ms_per_pass": in_browser_ms,
        "py_roundtrip_ms_per_pass": py_roundtrips_ms,
        "in_browser_min_ms": min(in_browser_ms),
        "in_browser_median_ms": median(in_browser_ms),
        "in_browser_max_ms": max(in_browser_ms),
        "per_element_us_median": median(per_element_us),
        "sample_first_element_styles": runs[0]["sample_first"],
    }

    element_count_ok = count == TARGET_ELEMENT_COUNT
    cap_ok = max(in_browser_ms) < CAP_MS
    all_green = element_count_ok and cap_ok
    results["claim_1_element_count"] = element_count_ok
    results["claim_2_under_cap_ms"] = cap_ok
    results["verdict"] = "GREEN" if all_green else "RED"

    out = Path(__file__).parent / "spike_results.json"
    out.write_text(json.dumps(results, indent=2))

    # Console summary
    print("L-SPIKE-03 — getComputedStyle cost benchmark")
    print("=" * 60)
    print(f"Playwright: {pw_version}")
    print(f"Fixture: {FIXTURE}")
    print(f"Element count: {count} (target: {TARGET_ELEMENT_COUNT})")
    print(f"Cap: {CAP_MS} ms wall-clock total, in-browser")
    print(f"Passes: {PASSES} (plus 1 warm-up)")
    print(f"Properties read per element: 10 (display, position, gridColumn, gridRow, flexDirection, flexBasis, width, height, margin, padding)")
    print()
    print(f"Warm-up:      in-browser {warmup['elapsed_ms']:.2f} ms | py roundtrip {py_warmup_elapsed_ms:.2f} ms")
    print(f"Measured (in-browser ms per pass): {[f'{x:.2f}' for x in in_browser_ms]}")
    print(f"  min:    {min(in_browser_ms):.2f} ms")
    print(f"  median: {median(in_browser_ms):.2f} ms")
    print(f"  max:    {max(in_browser_ms):.2f} ms")
    print(f"Per-element median: {median(per_element_us):.1f} µs")
    print(f"Py roundtrip (ms per pass): {[f'{x:.2f}' for x in py_roundtrips_ms]}")
    print()
    print(f"[{'KNOWN' if element_count_ok else 'FAIL'}] Claim 1 — Fixture exposes {TARGET_ELEMENT_COUNT} focusable elements: {element_count_ok}")
    print(f"[{'KNOWN' if cap_ok else 'FAIL'}] Claim 2 — Max in-browser elapsed < {CAP_MS} ms: {cap_ok}")
    print()
    print(f"VERDICT: {results['verdict']}")
    print(f"Results: {out}")
    return 0 if all_green else 1


if __name__ == "__main__":
    sys.exit(main())
