# ADR 0005 — L-09 harness rescan sampling cap

**Status:** Accepted
**Date:** 2026-04-21
**Pre-L-09 harness run; post-ADR 0003 (`e022e77`).**

## Context

ADR 0003 finalized L-09 Completeness evaluation (labels + aggregation). Cost estimate at **29 sites × ~15 candidates × ~20 s/poke ≈ 2.4 hours** exceeds operator's 2-hour flag threshold (2026-04-21 operator spec):

> Per-site rescan can be expensive — N pokes per site × settlement-window-per-poke × 29 sites. If wall-clock estimate exceeds 2 hours, flag before starting and propose a sampling strategy as ADR (e.g., poke first K endpoints, not all). Do not silently sample without ADR.

Sampling deviates from the poke-selection policy's literalism (LANTERN.md Part 4 Step 3: "all elements with role `button` inside `main`", "all elements with role `link` inside `nav` [up to 10]", etc.). Per R0.2 the policy is pinned as measurement surface; any deviation is drift-adjacent.

The policy already embeds an internal cap: `MAX_NAV_LINKS_TO_POKE = 10` on link-in-nav (rescan.py at `b3a8be7`). The sampling cap extends this capping principle to the total candidate set after policy selection.

## Decision

**K = 10 candidates per site, maximum**, applied in `harness/run_completeness.py` **AFTER** `select_poke_endpoints` returns. The `select_poke_endpoints` contract and the R0.2 poke-selection policy are **UNCHANGED** — the cap is a harness-side operational parameter only.

Ordering under the cap: take the first K candidates in the order `select_poke_endpoints` returns them. That function already orders by policy priority (a → b → c → d) then by `tab_order_index` within each selection reason. So the first K are, in order:

1. button-in-main candidates (policy a) in tab order
2. link-in-nav candidates (policy b) in tab order, already bounded by `MAX_NAV_LINKS_TO_POKE = 10` within (b)
3. The single first-textbox-in-form candidate (policy c), if any
4. haspopup candidates (policy d) in tab order

K applies to the TOTAL across all four reasons. Excess candidates are recorded in the per-site JSON but not invoked on.

## Rationale

- **K = 10 matches the frozen `MAX_NAV_LINKS_TO_POKE = 10`** (Part 4 Step 3 at R0 `54258a1`, rescan.py at `b3a8be7`). Symmetric, audit-friendly. "Keep two caps equal" reduces cognitive load for future readers.
- **Wall-clock estimate collapses to ~1.6 hours** (`29 × 10 × ~20 s`), comfortably under the 2-hour threshold.
- **Anti-D bias from the K cap partially offsets the pro-D bias** from ADR 0003's per-poke-sum M (double-count across pokes). A Pass verdict that survives K-cap truncation AND M-double-counting is a robust Pass; a Fail verdict under K-cap-restriction + M-double-count is strong evidence against D.
- **Policy-order (vs interleaved or randomized)** preserves the policy's priority signal. Buttons-in-main get first-dibs, matching the methodology's intuition that they are the high-information endpoints.

## Considered alternatives

| K | Est. wall-clock | Decision |
|---|---|---|
| 8 | ~1.3 h | Rejected — unnecessarily constrains dynamic-class sites with many buttons. |
| **10** | **~1.6 h** | **Accepted.** |
| 12 | ~1.9 h | Rejected — at the edge; risk of exceeding 2 h on a slow day. |
| 15 | ~2.4 h | Rejected — doesn't meaningfully sample (rare that sites exceed 15). |

Alternative orderings:

| Scheme | Decision |
|---|---|
| **Policy priority (a → b → c → d), tab order within reason** | **Accepted.** |
| Per-selection-reason sub-caps (max 5 button-in-main, 10 link, 1 textbox, 3 haspopup) | Rejected — more tuning parameters = more drift surface; K=10 total is simpler. |
| Interleaved (one of each reason in rotation) | Rejected — loses the policy-priority signal. |
| Randomized (seeded) | Rejected — unnecessary noise; mechanical sort is more auditable. |

## Consequences

- `run_completeness.py` applies the cap in harness code; `rescan.py` stays frozen at `b3a8be7`.
- Per-site saved JSON records both `all_candidates_count` and `selected_candidates_count` for audit transparency on cap-triggered truncation.
- Any Pass verdict under the cap is robust; a Fail on a high-candidate site may reflect cap truncation rather than genuine absence of state change. The L-09 report must document this possibility per cluster.
- If L-09 verdict is Soft Pass or Fail and operator wants to re-run without cap for dynamic clusters specifically, that is a follow-on harness run with its own ADR — not a drift of this one.

## Confidence

- K = 10 selection: **KNOWN** (defensible choice, documented rationale).
- Wall-clock estimate: **MODELED** — based on L-06/L-07 per-probe latency. Actual may vary with site responsiveness; flag if run exceeds 2 h anyway.
- Whether K=10 captures enough of each site's state-change surface to support the 25 % dynamic-cluster threshold: **MODELED** — the pro-D M-sum plus anti-D K-cap offset argues robustness either way; empirical check is L-09.

## Cross-references

- R0.2 — poke-selection policy pinned as measurement surface (unchanged)
- ADR 0003 — L-09 completeness pre-registration (labels + aggregation)
- `rescan.py` at `b3a8be7` — `select_poke_endpoints` + `rescan()` public surface
- LANTERN.md Part 4 Step 3 — canonical `MAX_NAV_LINKS_TO_POKE = 10` precedent
