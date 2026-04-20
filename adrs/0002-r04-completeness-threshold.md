# ADR 0002 — R0.4 Completeness condition (ii) operational threshold ("~0% delta")

**Status:** Accepted
**Date:** 2026-04-20
**Authored:** Pre-L-01, per operator direction (2026-04-20). Originally flagged as UNKNOWN in ADR 0001 and deferred to a pre-L-09 ADR; promoted forward now because the threshold is a rubric-operationalization decision that does not depend on L-07 cluster output and can be pinned earlier without leaking evidence into the rubric.
**Related but distinct:** ADR 0003 (dynamic/static class labels, post-L-07) stays queued. The two UNKNOWNs from ADR 0001 have different dependency shapes; this ADR resolves only the threshold.

## Context

LANTERN.md Part 5 § Completeness criterion § Condition (ii) states:

> **Condition (ii) — static classes:** the three-pass probe produces ~0% delta — this is the correct-null behavior. Spurious state-transition elements on static content indicate Methodology D is noisy. The operational threshold for "~0%" is pinned in a pre-L-09 ADR (before the completeness harness runs) and frozen thereafter.

"~0%" is not empirically evaluable. It needs an operational definition before the completeness harness (L-09) runs. If the threshold is pinned after evidence arrives, it will be tuned to make the data pass — textbook rubric-drift (BUILD.md §R4 `rubric-drift`, §1.8 "Stop when done").

Pre-registration discipline: authoring this ADR now, before any A+B+C+D probe runs anywhere in the project, means no data has touched the threshold.

Condition (ii) applies **per-site** during the completeness harness (L-09) to each site whose cluster is labeled static-class (labeling happens in ADR 0003, post-L-07). A "delta" is the set-count difference between the A+B+C+D three-pass probe's focusable element set and the A+B-only single-pass probe's set on the same site. Methodology D should only **add** elements (state-revealed); negative deltas are a separate defect (flagged at harness time, out of scope for this ADR).

## Decision

**Per-site pass threshold for R0.4 condition (ii):**

  `M ≤ max(2, ceil(0.05 × N))`

where:
- **N** = count of focusable elements in the A+B-only single-pass fingerprint (the **baseline**; *not* the A+B+C+D three-pass count — measuring D's addition against a total that already includes D would be circular).
- **M** = count of new focusable elements discovered by the three-pass probe (the set difference `three_pass \ single_pass`).
- The `ceil` is applied to the 5% component so the threshold is always an integer. Example: N=41 → `ceil(0.05 × 41) = ceil(2.05) = 3` → threshold = `max(2, 3) = 3`.

A site passes condition (ii) iff `M ≤ max(2, ⌈0.05 × N⌉)`.

## Rationale

### Floor of 2 — small-site noise tolerance

On a small static page (N ≤ 20 focusable elements), a pure 5%-ceiling gives `⌈0.05 × 20⌉ = 1`, i.e., zero-element tolerance. Real-world small static pages sometimes have one legitimately-deferred element (a lazy-loaded iframe, a script-inserted widget) that Methodology D would catch. Calling a single such element a violation of "~0%" would be too aggressive.

Two is the smallest floor that tolerates single-element noise on small pages while still being tight enough that a truly interactive widget (click → modal → 3 new focusable elements) still fails the threshold and moves the site out of the static class (or flags the classification).

### Ceiling of 5% — large-site proportional slack

On a static page with N ≥ 100 elements (news front page, marketing landing with many links), background mutations scale with page size: embedded ad widgets, analytics-injected tracking pixels, layout-shift-induced focusable-count fluctuation. A pure absolute floor of 2 would fail most large static sites even when D is behaving correctly on the main content.

5% is the operational proxy for "close to zero." Below 5% is "noise-floor-consistent"; above 5% is "something structural is happening that a static-content classification should not tolerate."

### Crossover at N = 40

`max(2, ⌈0.05 × N⌉) = 2` for N ≤ 40, and scales linearly above that. N=40 maps approximately to "small landing page / article" vs "content-rich static page" — the crossover point is where proportional scaling takes over from the noise floor. This matches realistic static-site content distribution without needing empirical calibration.

### Neither bound depends on L-07 cluster output

Both `N` and `M` are per-site observables available at harness time. The only L-07-dependent decision is **which sites are in the static class** (ADR 0003). That dependency shape is different — which is why this ADR can land pre-L-01 while ADR 0003 must wait for L-07.

### Pre-evidence commitment

Authoring before L-01 writes any vocab.py or fingerprint.py code means no data can tune the threshold. If L-09 output clusters right at the threshold boundary on many sites, that is a **finding** (possibly a Methodology D tuning concern, possibly a classification concern for those sites), not grounds to adjust the threshold.

## Considered alternatives

| Alternative | Formula | Why rejected |
|---|---|---|
| Pure absolute | `M ≤ 2` | Fails most N≥50 static sites even when D is working correctly. Background noise scales with page size; a fixed 2 doesn't. |
| Pure percentage | `M ≤ ⌈0.05 × N⌉` | Fails small sites. N=10 static page with one legitimate lazy-loaded element has delta=1 > 0.5 → violation. Over-triggers on small sites. |
| Tighter (`max(1, 3%)`) | `M ≤ max(1, ⌈0.03 × N⌉)` | Floor of 1 is too brittle — any single observed mutation (including benign lazy-loads or focus-side-effect observer noise) fires a violation. Improvement in sensitivity is small, false-positive risk is higher. |
| Looser (`max(3, 10%)`) | `M ≤ max(3, ⌈0.1 × N⌉)` | Floor of 3 and ceiling of 10% both start admitting small-scale real state-transition surfaces (e.g., a collapsible FAQ that D legitimately reveals). A static-class site that hides a collapsible should probably be re-classified as dynamic, not pass a loose threshold. |
| Log-scaled | `M ≤ max(2, ⌈log₂ N⌉)` | Log grows slower than 5% in the realistic N range (e.g., N=100 → log₂=7 vs 5%=5; N=200 → log₂=8 vs 5%=10). Log is **tighter** on large sites than the 5% ceiling intends. Two-regime (floor + linear) is also easier to explain and audit. |

No alternative is strictly better across the static-site size distribution. Formula accepted without modification.

## Consequences

- R0.4 condition (ii) is operationally evaluable per-site on day one of L-09.
- `lantern/rescan.py` (L-08, Methodology D) can implement the three-pass protocol knowing the threshold its output is measured against. Scope unchanged — rescan computes the M delta; R0.4 evaluation applies the threshold at report time.
- `harness/run_completeness.py` (L-09) compiles a per-site table `(site_id, shape_class, N, M, threshold, pass)` without requiring L-09-time threshold decisions.
- Re-runs against the same fixed set of static-class sites produce deterministic pass/fail outcomes; no tuning latitude.
- Per-site evaluation is **additive** to R0.4's per-shape-class and per-category reporting — no table is replaced.

## Open — deferred

**Class-level aggregation of per-site pass/violation counts** into the R0.4 Pass / Soft Pass / Fail verdict for condition (ii) is *not* pinned here. R0.4's qualitative language — "marginally violated (documented exceptions, small-magnitude)" / "fails broadly" — needs its own operationalization (e.g., "class PASS if ≥90% of sites per-site-pass; SOFT PASS if 75-90%; FAIL otherwise"). That decision belongs to the same pre-L-09 ADR bundle as ADR 0003 (class labels) — both require L-07 output to be sensible.

This ADR pins the per-site threshold only. Aggregation is flagged as an open-at-pre-L-09 item, not an UNKNOWN blocking anything upstream.

## Confidence labels

- Per-site threshold formula `M ≤ max(2, ⌈0.05 × N⌉)`: **KNOWN** at this commit (definition).
- Threshold being "correct" for real static-site distributions: **MODELED** — pre-evidence choice based on structural reasoning (small-site noise floor, large-site proportional ceiling). Empirical performance is unknown until L-09 runs. Clustering-at-threshold is a finding, not grounds for adjustment.
- Class-level aggregation rule: **UNKNOWN** (deferred to pre-L-09 ADR bundle alongside ADR 0003).

## Cross-references

- ADR 0001 — pre-registration bundle; R0.4 introduced; this threshold flagged as UNKNOWN
- ADR 0003 (not yet authored) — dynamic/static class labels, post-L-07
- LANTERN.md Part 5 § Completeness criterion
- BUILD.md §R3 L-09 (completeness harness ticket)
