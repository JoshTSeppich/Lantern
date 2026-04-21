# L-14 known relaxation (draft) — `harness/dashboard.py` not built

**Status:** DRAFT — does NOT replace L-14 Part (b).
**Date:** 2026-04-21 (authored at pause; L-14 Part (b) will run after L-13 completes or scope-down commits).
**Purpose:** Capture the `harness/dashboard.py` non-build now while context is fresh, so the eventual L-14 cairn primitives compliance audit has an accurate record of what happened rather than a retroactive reconstruction.

## What §1.5 specified vs what was built

BUILD.md §1.5 specified `harness/dashboard.py` as a CLI reading a `state.json` file and rendering live investigation state, with named red-flag conditions:

> A `harness/dashboard.py` CLI renders live investigation state. Fields from `state.json`:
> - Current ticket and phase
> - Spike status per L-SPIKE-NN (pending/green/red/failed)
> - Probe count per site per category
> - Cluster count and category-majority per cluster (post-discrimination)
> - Completeness delta per shape-class (post-completeness)
> - Utility pass-rate delta per prompt variant (post-utility)
>
> Dashboard flags red if:
> - Any spike is green but its downstream module lacks a frozen contract commit
> - Discrimination clusters violate pre-registered rubric
> - Completeness falls below soft-pass threshold on dynamic-class sites
> - Utility test shows prompt-variant disagreement >5 points (prompt-failure signal)

The CLI was not built. The `state.json` file was not authored. The red-flag conditions were not automated.

What substituted (in practice): per-ticket committed report files at `adrs/L-06-stability-report.md`, `adrs/L-07-discrimination-report.md`, `adrs/L-09-completeness-report.md`, each produced by its ticket's `report_*.py` script and committed alongside its raw run log as part of the ticket's ADR sequence. The substantive content §1.5 asked for (phase state, spike status, probe counts, cluster composition, completeness delta by shape class, prompt-variant disagreement flags) exists as committed markdown — but materialized as per-phase artifacts rather than a single live CLI view.

## Honest framing for L-14 Part (b)

The per-ticket report pattern emerged organically from the Cairn commit grammar discipline — specifically from `adr(L-NN): <verdict>` commits being where each phase's scorecard naturally landed. It was NOT a deliberate dashboard-replacement decision made at some point in the build. I simply never built `harness/dashboard.py`; the commit grammar happened to paper over the absence by producing ADR reports that contained the same information in a less-live form.

Three readings are possible for L-14 Part (b) to resolve:

1. **Relaxation with retroactive rationale.** §C0 explicitly allows relaxation: *"If any primitive was relaxed, document why."* The per-ticket report pattern genuinely met §1.5's intent (investigation state visibility with red-flag surfacing) even if it didn't meet the letter (CLI reading `state.json`). The rationale — that the commit-grammar discipline already produces an audit trail — is defensible. Verdict: documented relaxation, audit passes.

2. **Un-built scaffold with post-hoc justification.** The honest history is that I never intended to skip dashboard.py — I simply forgot or deprioritized it. The per-ticket reports that emerged are not a deliberate substitute; they're a convenient accident. Framing them as "the intended substitute" post-hoc would be retconning. Verdict: primitive gap, audit flags it, and whoever authored the build contract's §1.5 decides whether the gap is material given the evidence that the commit discipline captured the equivalent signal anyway.

3. **Gap that matters and should be filled.** The per-ticket reports are post-hoc artifacts; a live dashboard would have shown, in flight, problems like the L-06 40% probe-failure rate or the L-07 SaaS-login-cluster-2 artificial-closeness vindication — earlier and in a more triaging-friendly format. That earlier visibility might have shaped operator direction in real time. Verdict: gap is material; either fill it now (small scope) or document the forgone value in the L-14 audit.

My read: reading 2 is the most honest. I didn't deliberately substitute — I just didn't build it. Whether that constitutes a material gap depends on whether the operator values in-flight red-flag surfacing over end-of-phase reports, which is an operator judgment call, not a technical determination.

L-14 Part (b) has the full evidence trail (all ADRs, all commit messages, all report files) to pick the reading and document the audit finding. This draft is input to that process, not its conclusion.
