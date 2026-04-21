# L-12 Pause — Lantern side complete, Sherpa-side readiness required to proceed

**Status:** PAUSE. Lantern side done through L-11 public-surface freeze.
**Date:** 2026-04-21
**Blocking condition:** Sherpa's executor must be ready to consume `lantern.classify()` AND Sherpa's frozen task corpus must be available for pre-registration.
**Unblocking signal:** operator direction + commit SHA pointing at a Sherpa release where (a) the executor has a call site for `lantern.classify()` gated by the R2.2 soft-fallthrough exception handler, and (b) the utility test's 20-task corpus is frozen at a named Sherpa commit.

## Investigation state at pause

- **49 commits** on `main` (`26b01f6` → `a639fcf`).
- **259/259 tests passing** — all L-01..L-11 modules green + frozen, plus the L-08 rescan + L-11 classify integration tests exercising real Chromium via the local HTTP fixture server (conftest.http_fixture_server).
- **Four spike gates** verified (L-SPIKE-01 `09ac2c7`, L-SPIKE-02 `9492e89` RED→ADR 0004, L-SPIKE-03 `4cf0181`, L-SPIKE-04 `97a0a44`).
- **Public surface frozen** at `a639fcf` (`contracts(L-11/public): freeze`). `classify()` and `LanternResult` match R2.1 verbatim.
- **Library shipped** as package resource at `lantern/library_data/l07.json`, bootstrapped from L-07 at `9c16385`.
- **Six ADRs committed**: 0001 (pre-registration), 0002 (R0.4 threshold), 0003 (L-09 labels + aggregation), 0004 (hasPopup normalization), 0005 (L-09 K=10 sampling cap), 0006 (N=0 → INDETERMINATE gap-fill).

## Verdict tracker

| Phase | Verdict | Evidence commit |
|---|---|---|
| Stability (L-06) | Soft Pass (ratio 0.3719) | `594e42e` |
| Discrimination (L-07) | Soft Pass (k=5, mean majority 0.6214) | `9c16385` |
| Completeness (L-09) | PASS (post-ADR-0006: 2/3 evaluated clusters Pass, strict majority) | `38dd6bf` |
| Utility (L-12) | **pending** | — |

LANTERN.md Part 5 § Investigation verdict mapping does not explicitly tabulate Soft-Pass propagation. Interpretation used throughout the investigation (operator direction 2026-04-20, 2026-04-21): Soft Pass is "proceed with caveats" — NOT an automatic downgrade. L-14 Part (a) resolves whether Soft Pass / Soft Pass / Pass / ??? converges to *Full Lantern justified*, *Scope-down*, or *Research Artifact* once Utility evidence is in.

## Why pause here — the pre-registration simultaneity requirement

L-12 is the first cross-repo step in the investigation. It needs two things to co-land at pre-registration:

1. **Lantern's 10 held-out sites.** Must be sites NOT present in the L-06 or L-07 corpus (so the library wasn't bootstrapped from them). Lantern's side supplies this list.
2. **Sherpa's 20-task corpus.** Must be a frozen snapshot of Sherpa's task catalog at a named Sherpa commit SHA. Sherpa's side supplies this list.

Both MUST be committed in a single pre-registration commit BEFORE the utility harness runs. The simultaneity is not incidental — it's the drift protection.

If the held-out sites are picked first and Sherpa's task list is appended later, Sherpa's tasks could (consciously or not) be shaped to match the sites — or vice versa. That would post-hoc-fit utility evidence to prompt quality or library coverage. R0.5 flagged this exact risk when mandating the dual-variant-plus-decision-table setup, and the same logic applies to the corpus pair.

A stub L-12 harness committed pre-Sherpa would require guessing either the sites or the tasks, creating exactly the drift surface the protection forbids. That's why this pause does not build harness scaffolding.

## Resumption protocol

When Sherpa's executor is ready to consume `lantern.classify()`:

1. **Single pre-registration commit** containing:
   - `harness/sites_utility.yaml` — 10 held-out sites with per-site justification (category, stability assumption, automation-compatibility note, NOT in L-06/L-07 corpora)
   - `harness/tasks_utility.yaml` — 20 tasks from Sherpa's frozen task corpus, with Sherpa commit SHA recorded at top of the file
   - `harness/run_utility.py` — harness iterating 20 tasks × 10 sites × 3 conditions (blind, variant-A, variant-B) = 600 runs. Calls `classify(url)` per site + renders hints via both prompt variants; calls pluggable `evaluate_task(task, url, hints) → bool` (Sherpa-provided at runtime per R2.2's temperature/model/max_tokens pinning).
   - `harness/report_utility.py` — applies `lantern/prompts/DECISION_TABLE.md` mechanically. Produces verdict per the 4×4 (Δ_A, Δ_B) matrix. Flags PVD if `D > 5 pts`.
   - Single commit message: `chore(L-12): pre-register utility corpus (10 sites + 20 Sherpa tasks at sherpa-<SHA>)`.
2. **Operator runs `run_utility.py`** against Sherpa's executor with the real Claude client wired up (Lantern's `hints.set_llm_call()` + Sherpa's evaluator). Estimated wall-clock: ~600 × ~20s/run ≈ 3.3 hours for the full matrix. Sampling cap (similar to ADR 0005's K=10 logic for L-09) may be needed if per-run latency exceeds estimate — if so, author `ADR 0007: L-12 utility sampling cap` BEFORE running, matching ADR 0005's template.
3. **Commit raw evidence** as `docs(L-12): utility harness run log (raw audit trail)`.
4. **Commit verdict ADR** as `adr(L-12): utility <VERDICT>` applying the DECISION_TABLE to the evidence. Verdict ∈ {PASS, SOFT PASS, FAIL, FAIL-HARMFUL, HALTED (PVD or library-staleness saturation)}.
5. **L-13 — Sherpa integration touch** (~1 day per §R3):
   - Add `lantern.classify()` call site to Sherpa's executor under R2.2's exception handler
   - Add `## Site shape context` header prepend
   - Re-run utility test against integrated Sherpa
   - Commit the Sherpa-side integration diff under Sherpa's repo + the Lantern-side `adr(L-13): Sherpa integration touch` here
6. **L-14 — Final ADR + cairn primitives compliance audit** (§R3 L-14):
   - Part (a): `adr(L-14): final verdict — <Full Lantern justified | Scope-down | Research Artifact>` citing every prior ticket and harness report
   - Part (b): cairn primitives compliance audit — confirm each §C0 primitive was enforced with specific evidence; document relaxations with rationale

## Audit items queued for L-14 (pre-committed for context-freshness)

These are findings captured now while the build is fresh in context; L-14 Part (a)/(b) may re-evaluate:

1. **`harness/dashboard.py` not built.** §1.5 specified a CLI renderer of `state.json` with named red-flag conditions. Not built. Per-ticket committed reports (`adrs/L-06-*`, `adrs/L-07-*`, `adrs/L-09-*`) filled the role. See companion draft `adrs/L-14-known-relaxation-dashboard.md`.

2. **hasPopup regression tripwire as durable §1.1 evidence.** L-SPIKE-02 (`9492e89`) found the `hasPopup`-vs-`haspopup` CDP casing gap pre-fingerprint.py. ADR 0004 (`999b371`) + R0.7 + `contracts(state-bitmap): re-freeze` resolved it. The regression test lives across `tests/test_vocab.py`, `tests/test_fingerprint.py`, `tests/test_endpoints.py`, and `tests/test_probe.py` — a cross-module permanent tripwire, not a one-time gate. §1.1 produced durable protection, not single-use verification.

3. **Methodology D omitted from `classify()` (L-11 scope decision).** `classify()` at `a639fcf` does initial probe + library match + hint generation; does NOT run rescan at classify() time. Two readings of LANTERN.md were incompatible (R2.1's 8000ms default budget vs Part 4 Steps 0-8 full flow); L-11 resolved toward R2.1's latency. `state_transitions_summary=""` fed to hint prompts. L-09 Completeness PASS independently validated D's noise-floor behavior; `rescan.py` stays active for L-12 offline library-enrichment (not used in this L-12 plan but available). Flagged explicitly in `contracts(L-11/public)` commit body.

4. **Cluster 0 (Tesla Shop) N=0 site-state artifact.** Documented in ADR 0006. Worth revisiting at L-14: if Tesla's anti-bot state flips back to exposing focusable elements between this pause and L-14, the Cluster 0 INDETERMINATE treatment would not change retroactively — ADR 0006 is a rubric-surface addition, not a site-state assumption. If the L-12 held-out sites include Tesla-like-behavior sites, ADR 0006 handles them identically without a new ADR.

5. **ADR 0005 K=10 cap at L-09 bit on ~14/29 sites.** Documented in L-09 report. No cluster verdict pivoted on the cap per L-09 evidence. If L-12 observes similar high-candidate sites, a parallel ADR 0007 L-12 sampling cap would follow ADR 0005's template.

## Signal to unpause

- Operator returns with Sherpa commit SHA + confirmed executor-ready-to-consume-`classify()` status
- Or: operator explicitly releases the simultaneity requirement with a documented justification (unlikely; don't expect this)

**Until then, no further commits on this branch.** The pause is itself the decision.
