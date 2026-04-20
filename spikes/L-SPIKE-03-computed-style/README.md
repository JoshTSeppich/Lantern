# L-SPIKE-03 — `getComputedStyle` cost benchmark

**Status:** ✅ GREEN
**Date:** 2026-04-20
**Playwright (pinned, per BUILD.md §R1.2):** `1.58.0`
**Chromium build (via `playwright install chromium`):** Chrome Headless Shell 145.0.7632.6 (playwright chromium-headless-shell v1208)
**Python:** 3.12.13 (uv-managed)

## Scope

Per BUILD.md §R3 L-SPIKE-03, verify that `getComputedStyle` snapshot cost on a page with 200 focusable elements stays under a 2-second wall-clock total. If it exceeds the cap, flag and investigate alternatives (layout-parent-only snapshot, deferred snapshot, skip).

This is the gate for `lantern/grouping.py` (Methodology C) to use computed styles for layout-grid spatial grouping — per LANTERN.md Part 3 Methodology C "the layout-grid assist" and Part 4 Step 2.

## Fixture

`fixture.html` — 200 `<button>` elements distributed across four layout-container types, with varied classes so the browser cannot trivially cache identical computed-style results:

| Container kind | Count | Container class     | Item class |
|---|---:|---|---|
| `display: grid`         | 50 | `.grid-container`         | `.class-a` |
| `display: grid`         | 50 | `.grid-container`         | `.class-b` |
| `display: flex`         | 50 | `.flex-container`         | `.class-c` |
| `display: block`        | 30 | `.block-container`        | `.class-d` |
| `display: inline-block` | 20 | `.inline-block-container` | `.class-a` |

Total: 200 focusable elements. Each button has a stable id `focusable-001` through `focusable-200`. Build is deterministic — the script runs on page load and sets `window.__fixtureReady = true` once generation completes.

## Method

`spike.py`:

1. Launch Playwright Chromium headless, viewport 1440×900.
2. `goto(file://.../fixture.html)`, wait for `networkidle`, wait for `window.__fixtureReady === true`.
3. Run one warm-up benchmark to absorb JIT / first-call overhead.
4. Run 5 measured passes. Each pass:
   - Inside `page.evaluate`, call `performance.now()`, iterate over all focusable elements (selector: `button, input, select, textarea, a[href], [tabindex]:not([tabindex="-1"])`), call `window.getComputedStyle(el)` on each, read 10 properties relevant to Methodology C layout-grid / flex grouping (`display`, `position`, `gridColumn`, `gridRow`, `flexDirection`, `flexBasis`, `width`, `height`, `margin`, `padding`), and call `performance.now()` again.
   - Return `(element_count, elapsed_ms, per_element_us, sample_first)`.
   - Python side also records roundtrip cost for reference.
5. Check: (claim 1) element count == 200, (claim 2) `max(in_browser_ms)` < 2000 ms.

The measurement is **in-browser wall-clock** — i.e., the cost `grouping.py` will actually pay, excluding CDP/Playwright roundtrip. Roundtrip is reported separately for context.

## Results — verified claims (KNOWN)

### Claim 1 — **KNOWN** — Fixture exposes 200 focusable elements

`document.querySelectorAll(...)` returned 200 elements across all 5 passes. Decoys and scaffolding (h1, containers themselves) are correctly excluded by the selector.

### Claim 2 — **KNOWN** — In-browser elapsed < 2000 ms per pass

| Pass | In-browser elapsed (ms) | Python roundtrip (ms) |
|---:|---:|---:|
| warm-up | 2.20 | 4.99 |
| 1 | 0.50 | 1.50 |
| 2 | 0.50 | 1.24 |
| 3 | 0.30 | 1.18 |
| 4 | 0.30 | 1.22 |
| 5 | 0.50 | 1.13 |

**In-browser min / median / max: 0.30 / 0.50 / 0.50 ms.** Max observed is **~4000× under the 2000 ms cap**. Per-element median: 2.5 µs (reading 10 properties per element).

The warm-up pass is ~4× slower than subsequent passes — expected JIT / first-invocation overhead. All measured passes are within the cap even if the warm-up were counted (2.20 ms ≪ 2000 ms).

## Interpretation & headroom

The cap exists to guard against a pathological case where computing styles for the full focusable set blocks a probe for seconds. Observed cost is 3–4 orders of magnitude below the cap. This means:

- **Methodology C's layout-grid assist is cheap.** Using `getComputedStyle` for every focusable element during the probe is well within budget; no premature optimization (deferred snapshot, layout-parent-only, skip) is warranted.
- **Scaling headroom:** even a real-world site with 10× the DOM complexity (1000+ focusable elements) or 10× the per-element cost (heavier layout, deeper cascades) would still land at ~50 ms — 40× under the cap. Lantern has room to grow the property set `grouping.py` reads if discrimination / completeness investigation needs more layout signal.
- **Cap is not a tuning knob.** It's a sanity bound, and observation confirms the sanity bound is nowhere near load-bearing. If a future real-world probe ever gets close to the cap, it is a signal of something abnormal (ad-injected DOM, MutationObserver storm, etc.) that grouping.py should flag, not silently proceed through.

## What this spike does NOT verify

Labeled MODELED or UNKNOWN per BUILD.md §1.2.

- **Real-world site cost:** MODELED. Fixture is small and hermetic. Sites with ad iframes, heavy CSS cascades, or a DOM with 2000+ nodes will be slower. The 4000× headroom argues strongly that even 100× cost inflation is safe, but this is inference, not direct measurement.
- **Cost under concurrent work:** MODELED. The page is idle during the benchmark. If the site is actively loading / animating / responding to the tab-traversal Methodology B is driving, computed-style calls may contend with layout. Not tested here.
- **Property-set sensitivity:** KNOWN for 10 properties (listed above). Reading more properties scales roughly linearly with the number of property reads. LANTERN.md does not yet pin the exact property list `grouping.py` will read; this spike used a plausible superset of grid/flex/position relevant properties.
- **Non-Chromium browsers:** UNKNOWN. Out of scope per Part 4 Step 0 (Chromium only).
- **Cost with Shadow DOM / web components:** UNKNOWN. Fixture has no shadow trees. `getComputedStyle` is well-defined for elements in open shadow DOM, but closed shadow DOM is opaque; fingerprint won't reach those elements anyway.

## How to re-run

```bash
uv run python spikes/L-SPIKE-03-computed-style/spike.py
```

Exit code 0 = GREEN, 1 = RED.

## Re-verification triggers (per BUILD.md §R1.2)

- `playwright` version bump
- Chromium binary change that affects style-resolution performance
- `fixture.html` edit
- `grouping.py` settling on a larger property list than the 10 used here (in which case the benchmark should be re-run with that list to confirm the cap still holds)

## Downstream consumers

- **`lantern/grouping.py`** (Methodology C) — layout-grid / flex spatial-grouping assist. Gated by this spike. Combined gate with L-SPIKE-02's ADR 0004 + freeze (both now clear) and L-03 (endpoints.py, gated on L-SPIKE-01 which is GREEN).

## Artifacts

- `fixture.html` — 200-button fixture, JS-generated, 5 layout container kinds
- `spike.py` — benchmark script, exits 0=GREEN / 1=RED
- `spike_results.json` — machine-readable per-pass timings and sampled computed-style values
- `README.md` — this document
