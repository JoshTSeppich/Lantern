# L-SPIKE-04 — Mutation observer + settlement detection

**Status:** ✅ GREEN
**Date:** 2026-04-20
**Playwright (pinned, per BUILD.md §R1.2):** `1.58.0`
**Chromium build (via `playwright install chromium`):** Chrome Headless Shell 145.0.7632.6 (playwright chromium-headless-shell v1208)
**Python:** 3.12.13 (uv-managed)

## Why this spike ran second (ranking note)

Ranked **#2** by severity and **higher** in probability of failure than L-SPIKE-02 — so why did L-SPIKE-02 run first?

**Because the scope-down path here is architected.** A RED outcome on L-SPIKE-04 does not halt the investigation. It invokes LANTERN.md Part 5 Completeness criterion's pre-registered Fail branch: drop Methodology D, proceed with A+B+C only. `rescan.py` is removed from the pipeline; `fingerprint.py` / `endpoints.py` / `grouping.py` continue. The investigation remains viable; the thesis narrows to "probe-library-as-classifier, no state-transition inference."

By contrast, L-SPIKE-02's failure (state-bitmap shape mismatch) had **no scope-down path** — the A+B+C static fingerprint is the backbone of every later phase. A L-SPIKE-02 surprise before `fingerprint.py` wired in was catastrophic-to-rework; a L-SPIKE-04 surprise is a documented pivot.

Severity × probability reasoning table (original in `spikes/L-SPIKE-02-ax-tree/README.md`, reproduced here for this spike's context):

|  | L-SPIKE-02 (AX tree) | L-SPIKE-04 (mutation observer) |
|---|---|---|
| Downstream blocks | `fingerprint.py` + `grouping.py` | `rescan.py` only |
| Scope-down path | **None** | **Completeness Fail branch** (LANTERN.md Part 5) |
| Failure mode if RED | Silent data-shape mismatch → whole fingerprint unreliable | Noisy / unreliable deltas → caught by Completeness; investigation narrows but survives |
| Probability | Moderate | Higher (timing heuristics are fragile by nature) |

Severity-as-tiebreaker → L-SPIKE-02 first. The L-SPIKE-02 finding (`hasPopup` camelCase drift, resolved via ADR 0004) validated the priority. L-SPIKE-04 then ran and passed with comfortable margin — but the ordering was not contingent on either outcome.

## Scope

Per BUILD.md §R3 L-SPIKE-04 + operator tight spec 2026-04-20, verify:

1. **Three-state distinction** — the settlement detector reliably classifies every click outcome as one of:
   - `settled-post-state-change` — mutations fired, then 500 ms quiet within cap
   - `unchanged-by-interaction` — no mutations at all; click had no effect
   - `in-transition` — mutations still firing when cap is hit
   — **not** collapsed into a binary "settled yes/no."

2. **Settlement window definition** from LANTERN.md Part 4 Step 4 + BUILD.md §R3 — `networkidle + 2000ms + no mutations in observer for 500ms, capped at 8s total` — holds on a fixture exercising each of the three states. Claim-per-state, KNOWN/MODELED/UNKNOWN each.

3. **Failure modes characterized** (not just avoided):
   - `false-negative` — state change happened but observer missed it → probed by Case C (progressive mutation)
   - `false-positive` — no real state change but observer fired → probed by Case B (no-op)

This is the gate for `lantern/rescan.py` (Methodology D, L-08). If RED, rescan.py is not implemented; ADR 0005 (proposed) invokes Completeness Fail branch.

## Fixture

`fixture.html` — four buttons, each eliciting a different mutation pattern:

| Case | Button | Handler | Expected pattern |
|---|---|---|---|
| **A** | `#btn-state-change`  | `classList.remove('hidden')` on `#panel-A`                           | one attribute mutation, fires immediately |
| **B** | `#btn-no-op`         | *(none — intentionally no handler)*                                   | zero mutations |
| **C** | `#btn-progressive`   | 3 × `appendChild` at `0 / 200 / 400 ms`                               | three childList mutations, spread across ~400 ms |
| **D** | `#btn-continuous`    | `setInterval(appendChild, 100)` — fires forever                       | continuous 100 ms mutations, never quiets |

## Detector algorithm

Injected via `page.evaluate` (defined in `spike.py` as `DETECTOR_JS`). For each case:

1. Attach `MutationObserver` to `document.body` with `{childList, subtree, attributes, characterData}`. Start clock.
2. Record each mutation with timestamp. On every mutation callback, update `lastMutationTime`.
3. Click the target button. Poll every 50 ms:
   - If `elapsed >= capMs`: resolve with `cap_hit = true`. Classification by mutation state at that instant (see §Classification below).
   - If `(now - (lastMutationTime || clickTime)) >= quietMs`: resolve with `cap_hit = false`. Quiet window satisfied.
   - Else continue polling.
4. Disconnect observer on resolve.

### Classification (resolve-time)

- `mutation_count == 0` → `unchanged-by-interaction`
- `cap_hit == true AND quiet_elapsed < quietMs` → `in-transition`
- Otherwise (`mutation_count > 0 AND quiet_elapsed >= quietMs`, whether cap was hit or not) → `settled-post-state-change`

The **reference time** for `quiet_elapsed` is `lastMutationTime` if any mutation has fired, otherwise `clickTime`. This is what makes the quiet window correctly **reset on each new mutation** — the key invariant Case C probes.

## Results — verified claims (KNOWN)

| Case | Observed state | Mutations | Elapsed (ms) | cap_hit | Result |
|---|---|---:|---:|---|---|
| **A** (happy-path)          | `settled-post-state-change` | 1  | 512.4  | no  | PASS |
| **B** (false-positive probe)| `unchanged-by-interaction`  | 0  | 511.9  | no  | PASS |
| **C** (false-negative probe)| `settled-post-state-change` | 3  | 920.5  | no  | PASS |
| **D** (cap-boundary)        | `in-transition`             | 30 | 2049.6 | yes | PASS |

All four cases within their expected ranges (state match, mutation count bounds, elapsed bounds).

### Claim 1 — **KNOWN** — Three states distinguishable

Observed state set: `{settled-post-state-change, unchanged-by-interaction, in-transition}`. All three classifications fired exactly once (once per intended case). The detector does not collapse to a binary.

### Claim 2 — **KNOWN** — Happy path (Case A)

One-shot attribute mutation → one observer callback → 500 ms quiet → resolved at 512 ms. Overhead above 500 ms: 12 ms (polling granularity + microtask roundtrip). Classification matches expectation exactly.

### Claim 3 — **KNOWN** — False-positive probe (Case B) passes

Clicking a handler-less button fired exactly **zero** mutations. Detector correctly classified as `unchanged-by-interaction` (not `settled-post-state-change`). No false-positive observed — the observer distinguishes "no mutations happened" from "mutations happened and settled."

This is a stronger claim than "no mutations fired" — it also verifies that *when* no mutations fire, the detector does not silently fall through to a generic "settled" state that conflates the two.

### Claim 4 — **KNOWN** — False-negative probe (Case C) passes

Three mutations fired at ~0 / 200 / 400 ms. Observer recorded all three. Detector resolved at **920 ms** — consistent with last mutation at ~400 ms plus 500 ms quiet window plus ~20 ms polling overhead. A broken detector that did not reset the quiet window on each new mutation would have resolved near 500 ms with `mutation_count == 1`, silently missing mutations 2 and 3. Neither occurred.

The `920 ms` elapsed is the empirical evidence that the 500 ms quiet window successfully **reset** after each of three mutations — without the reset, elapsed would have been either ~500 ms (premature) or ≥ 1400 ms (if reset were from first-mutation-time instead of last). 920 ms is the precise expected value.

### Claim 5 — **KNOWN** — Cap-boundary (Case D) passes

Continuous mutations at 100 ms interval. Cap reduced to **2000 ms** for spike runtime efficiency (default 8000 ms; the cap-handling logic is independent of the cap value). Detector hit cap at 2049 ms with 30 mutations accumulated and `quiet_elapsed < 500 ms` → classified as `in-transition`. Did not fall through to `settled-post-state-change` (which would require quiet window satisfied) or `unchanged-by-interaction` (which would require mutation_count == 0).

This confirms the three-state distinction is preserved at cap, not just at quiet-window resolution.

## What this spike does NOT verify

Labeled MODELED or UNKNOWN per BUILD.md §1.2.

- **Real-world noise level.** Fixture is hermetic — no ads, no analytics, no background fetches. Real sites may have background mutations unrelated to the click (setInterval counters, animation frames, web sockets). These will show up as "mutations" in the observer window and may push a click with no semantic state change into `settled-post-state-change` classification. **MODELED** — `rescan.py` will need a noise-filter heuristic (e.g., mutation-target-subtree filtering, or pre-click baseline mutation-rate subtraction). Not implemented here; flagged for L-08 design.
- **Mutation-target filtering.** The observer watches the full document subtree. For production use, `rescan.py` may want to restrict the subtree (e.g., only the `<main>` landmark) to reduce noise. **MODELED** — the narrower observation is a superset constraint; the settlement-detection logic itself is unchanged.
- **Animation frame / CSS transition settling.** Some sites use CSS transitions after a state change; DOM mutations fire once but visual state continues transitioning. **MODELED** — not tested. The 2000 ms post-networkidle wait is the existing buffer for this; if transitions exceed 2 s the current definition would capture them within the observer window.
- **Browser-level rAF batching of mutations.** Some browser engines batch multiple DOM mutations into a single callback. This affects `mutation_count` but not state classification. **MODELED** — Chrome does not batch across microtask boundaries; observed count matches intended count across all four cases.
- **Shadow DOM.** Mutations inside open shadow trees require separate observers; closed shadow DOM is opaque. **UNKNOWN** — fixture has no shadow trees.
- **Click handlers with async work (fetch, promise chains).** Case C tests `setTimeout` scheduling, but real-world async may involve `fetch(...).then(...)` that resolves after the cap. Detector would classify as `unchanged-by-interaction` or `settled-post-state-change` (depending on timing) without distinguishing "async still pending." **MODELED** — this is a known limit of observer-only detection; combining with `networkidle` wait (already in the settlement definition) addresses fetch-pending cases.
- **Non-Chromium browsers.** Out of scope per LANTERN.md Part 4 Step 0.

## Downstream — unblocked

- `lantern/rescan.py` (Methodology D, L-08) — unblocked on the spike side. L-08 still sequentially gated on L-07 Pass (discrimination) per §R3.
- `lantern/vocab.py` / `lantern/fingerprint.py` (L-01) — not dependent on this spike; already unblocked after ADR 0004 + R0.7 + state-bitmap freeze.
- `lantern/grouping.py` (L-04) — not dependent; cleared on spike side after L-SPIKE-03.

**All four spikes GREEN (L-SPIKE-01, -03, -04) or GREEN-via-ADR (L-SPIKE-02 + ADR 0004).** The spike gate for L-01 is clear. L-01 (vocab.py + fingerprint.py) may now begin per §R3.

## How to re-run

```bash
uv run python spikes/L-SPIKE-04-mutation-observer/spike.py
```

Exit code 0 = GREEN, 1 = RED. Each RED case's `checks` dict in `spike_results.json` identifies which expectation fell out of bounds (`state_match` / `count_min_ok` / `count_max_ok` / `elapsed_min_ok` / `elapsed_max_ok`).

## Re-verification triggers (per BUILD.md §R1.2)

- `playwright` version bump
- Chromium binary change affecting `MutationObserver` semantics or `performance.now` resolution
- `fixture.html` edit (fixture is part of the measurement surface)
- LANTERN.md Part 4 Step 4 settlement-definition change (quiet-window or cap adjustment → re-run with new values)

## RED-branch protocol (what happens if a future re-run fails)

If a future re-verification run goes RED — e.g., because Chromium changes `MutationObserver` semantics or the fixture begins producing flaky timings — the decision tree is:

1. Investigate whether the failure is **classification-correctness** (three-state distinction broken) or **timing-bounds** (state is correct but elapsed_ms drifted outside expected range).
2. **Timing drift only:** treat as a measurement-surface refresh. Update expected ranges with justification; re-commit as `refactor(L-SPIKE-04):` — not a scope-down trigger.
3. **Classification-correctness failure:** invoke ADR (numbered post-ADR 0004). The ADR decides between (a) detector-algorithm fix (e.g., a better quiet-window heuristic) or (b) **Completeness Fail scope-down** per LANTERN.md Part 5 — drop Methodology D, `rescan.py` not implemented, investigation narrows to A+B+C.

## Artifacts

- `fixture.html` — 4-case fixture (known change, no-op, progressive 3×200ms, continuous)
- `spike.py` — 4-case harness + inline detector; exits 0=GREEN / 1=RED
- `spike_results.json` — machine-readable per-case detector output, checks, expected ranges
- `README.md` — this document
