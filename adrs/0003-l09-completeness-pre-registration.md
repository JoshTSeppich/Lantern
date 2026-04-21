# ADR 0003 — L-09 Completeness pre-registration bundle

**Status:** Accepted
**Date:** 2026-04-21
**Authored:** Pre-L-09 harness run; post-L-08 (rescan.py frozen at `b3a8be7`). Originally queued as UNKNOWN in ADR 0001 and extended in scope at L-07 read-out (operator 2026-04-21) to cover both (a) cluster labels and (b) class-level aggregation.

## Context

LANTERN.md Part 5 § Completeness criterion — as refactored by R0.4 — requires per-shape-class evaluation against two conditions:

- **(i)** dynamic classes: Methodology D discovers ≥ 25 % more focusable elements than single-pass on ≥ 70 % of sites in the class.
- **(ii)** static classes: D produces ~0 % delta (correct-null).

Three pre-L-09 decisions make the rubric evaluable:

1. **Operational threshold for "~0 % delta"** in (ii) — committed at `27dfcd3` as ADR 0002 — `M ≤ max(2, ⌈0.05 × N⌉)`.
2. **Dynamic-vs-static label per L-07 cluster** — committed here, part (a).
3. **Class-level aggregation rule** — how per-site verdicts within a cluster aggregate to a cluster verdict; how cluster verdicts aggregate to an investigation-level Completeness verdict — committed here, part (b).

All three must be committed BEFORE the L-09 rescan harness runs. Drift between this commit and the L-09 verdict commit is rubric-drift (§R4, §1.8). Self-check Q7 on the L-09 verdict commit is the bright line.

## Part (a) — Per-cluster dynamic/static labels

L-07 discrimination produced 5 clusters at `k_optimal=5` (see `adrs/L-07-discrimination-report.md`, `9c16385`). Labels are frozen pre-evidence.

### Cluster 0 — Tesla Shop (singleton) → DYNAMIC

**Size 1.** Member: `d01-ecom-01` (Tesla Shop, Shopify-backed).

**Label: dynamic.** **Epistemic basis: theory-grounded.** Product listings are the canonical example in LANTERN.md Part 3 Methodology D ("the donation-round-up button only appears after you add to cart. The size selector is disabled until you pick a color"). Variant-selector state reveal is the archetypal dynamic shape class; Methodology D is named for catching it.

### Cluster 1 — dense-link-list → STATIC

**Size 4.** Members: `d05-forum-01` (HN), `d10-mkt-02` (Tailwind), `d11-forum-02` (Lobsters), `d30-misc-05` (RFC 8259).

**Label: static.** **Epistemic basis: theory-grounded.** Link-row pages exhibit link-click-navigates behavior: a click on a link triggers a URL change, which LANTERN.md Part 4 Step 4 point 5 classifies as a navigation endpoint (not a state-change endpoint). Navigation endpoints contribute no `delta_added` (per rescan.py at `b3a8be7`). Therefore a cluster whose members are dominated by link-click-navigate behavior should produce near-zero per-site M by construction.

### Cluster 2 — minimal-login → DYNAMIC

**Size 2.** Members: `d09-saas-02` (GitHub login), `d33-saas-06` (Vercel login).

**Label: dynamic.** **Epistemic basis: theory-grounded.** Login forms are standard state-revealers: field focus triggers validation messages (via `aria-describedby` pointing to error regions), submit buttons enable/disable as required fields fill, required-field markers appear after blur on empty. These are exactly the state-revealed endpoints Methodology D is designed to catch.

### Cluster 3 — marketing-catch-all → STATIC (plurality-grounded)

**Size 14.** Majority category: marketing (5/14 = 35.7 %, a plurality — not a majority). Members: `d02-news-01` (Wikipedia Current Events), `d04-mkt-01` (Stripe), `d06-misc-01` (Wikipedia Accessibility), `d07-ecom-02` (Shopify themes), `d12-misc-02` (Wikipedia Python), `d13-ecom-03` (Allbirds), `d16-mkt-03` (Vercel marketing), `d22-mkt-04` (Supabase), `d24-misc-04` (Python docs), `d28-mkt-05` (PyTorch), `d29-forum-05` (Tildes), `d34-mkt-06` (Next.js), `d36-misc-06` (Wiktionary), `d38-news-07` (ProPublica).

**Label: static.** **Epistemic basis: plurality-grounded, NOT theory-grounded.** This is weaker than Clusters 0/1/2. The label rests on "most members are marketing-like, and marketing landings are typically static." Future readers must treat this cluster's pass/fail result as contingent on the plurality label being correct.

If L-09 evidence on Cluster 3 shows many `state_change` deltas (members behaving dynamically), that is a finding about the cluster's coherence, **not grounds to flip the label post-hoc.** The label stays; the finding reframes the verdict.

### Cluster 4 — heterogeneous → INDETERMINATE (excluded)

**Size 8.** Majority category: saas (2/8 = 25 %, too low to be a meaningful plurality). Members: `d03-saas-01` (Linear login — SPA), `d17-forum-03` (Stack Overflow), `d18-misc-03` (MDN HTML docs), `d19-ecom-04` (Arc'teryx), `d20-news-04` (Reuters), `d21-saas-04` (Slack signin — SPA), `d31-ecom-06` (Indiegogo), `d40-mkt-07` (Fastly).

**Label: INDETERMINATE.** Forcing a dynamic-or-static label on this cluster would be dishonest — its shape-class is not coherent enough to support either reading. The cluster is held together by whatever the A+B+C fingerprint picked up, without a defensible theory or plurality justification.

**Cluster 4 is excluded from Completeness verdict scoring.** L-09 report SHALL still compute and document per-site delta distribution across Cluster 4 members as observation data, but that distribution does NOT contribute to Pass/Fail arithmetic.

This reduces the Completeness sample from 5 clusters to 4 evaluated (Clusters 0, 1, 2, 3), preserving epistemic honesty at a small statistical-power cost.

## Part (b) — Class-level aggregation rule

### Per-site metric

For each site in the L-09 corpus:

- **N** = `len(initial_probe.fingerprint)` on the site's L-07 probe (A+B single-pass baseline, already captured at L-07 `057c86e`).
- **M** = `sum(len(outcome.delta_added) for outcome in rescan_result.outcomes if outcome.kind == "state_change")` on the site's L-09 rescan run.

**Note on M — pro-D bias is deliberate.** This is a per-poke-sum, NOT a per-unique-element count. If two pokes both reveal the same fingerprint tuple, it contributes 2 to M. A Pass verdict is robust under this double-counting, and a Fail verdict under this bias is strong evidence that D's state-transitions aren't earning their cost. Alternative de-duplicating operationalizations are not chosen here.

### Per-site verdict

The verdict rule depends on the site's cluster label:

- **Dynamic cluster:** site passes iff `M / N ≥ 0.25` (R0.4 condition (i)).
- **Static cluster:** site passes iff `M ≤ max(2, ⌈0.05 × N⌉)` (ADR 0002 operationalization of R0.4 condition (ii)).

Sites that produce no valid L-09 rescan (Playwright errors, timeouts at the poke-level that leave M undefined) count as per-site FAIL in their cluster's tally. L-07's binary-failure finding means 100 %-fail sites already drop out before L-09 (they aren't in the 29-site corpus at all).

### Per-cluster verdict

- `cluster_pass_rate = (# sites in cluster that passed per-site) / cluster_size`
- **Pass:** `cluster_pass_rate ≥ 0.70`
- **Soft Pass:** `0.50 ≤ cluster_pass_rate < 0.70`
- **Fail:** `cluster_pass_rate < 0.50`

### Investigation-level Completeness verdict

Aggregates across the 4 evaluated clusters (0, 1, 2, 3). Cluster 4 is excluded from the arithmetic.

- `n_evaluated = 4`
- `n_pass = # clusters with Pass verdict`
- `n_pass_soft = # clusters with Pass or Soft Pass verdict`

- **Completeness PASS:** `n_pass > n_evaluated / 2` (strict majority of evaluated clusters at Pass). For `n_evaluated = 4`, this requires `n_pass ≥ 3`.
- **Completeness SOFT PASS:** `n_pass_soft > n_evaluated / 2` AND NOT PASS. For 4 clusters: `n_pass_soft ≥ 3` AND `n_pass < 3`.
- **Completeness FAIL:** otherwise. For 4 clusters: `n_pass_soft ≤ 2` OR a 2–2 tie that falls short of strict majority.

### Halt rule

Per BUILD.md §R3 L-09:

- **Completeness FAIL specifically on dynamic clusters (0 and/or 2):** triggers the architected scope-down — drop Methodology D, Lantern ships with A+B+C only.
- **Completeness FAIL on static clusters (1 and 3) only:** is a finding about D's noise floor on static content, not a scope-down trigger. Investigate separately; do not drop D on this branch.
- **Mixed-cluster FAIL:** follows the per-cluster breakdown — dynamic-cluster fails drive the scope-down; static-cluster fails become findings.

This halt structure is what made L-SPIKE-04 acceptable at rank-2 behind L-SPIKE-02 (operator 2026-04-20): a Methodology-D failure has an architected exit. The scope-down branch was pre-registered in LANTERN.md Part 5 § Investigation verdict mapping at R0 commit `54258a1` and remains available.

## Consequences

- L-09 report scores 4 clusters (0, 1, 2, 3), not 5. Cluster 4 gets an observation-only section.
- ADR 0002 + this ADR jointly operationalize Completeness evaluation fully. No further pre-L-09 ADR is required.
- L-08's rescan applies to all 29 L-07 survivors at L-09 run time; cluster membership per L-07's bootstrapped library (`data/clusters/l07_library.json`, gitignored per §R1.1) drives the scoring.
- Cost estimate for L-09 harness: 29 sites × ~15 candidates × ~20 s/poke ≈ 2.4 h — exceeds operator's 2 h flag threshold (2026-04-21). A separate ADR will pin a per-site sampling cap before the harness runs. This ADR does not address sampling.

## Pre-evidence commitment

This ADR lands BEFORE the L-09 rescan harness runs. Its commit SHA is the drift bright-line: any change to part (a) cluster labels, part (b) aggregation, or ADR 0002's threshold formula between this commit and the L-09 verdict commit is rubric-drift (§R4, §1.8). Self-check Q7 on the L-09 verdict must verify no such drift.

## Confidence

- Cluster 0/1/2 label theory basis: **KNOWN** (labels follow directly from LANTERN.md spec examples).
- Cluster 3 plurality basis: **MODELED** — marketing-dominated static assumption is structural; falsifiable by L-09 evidence, but the label does not flip on evidence.
- Cluster 4 INDETERMINATE exclusion from verdict: **KNOWN** by construction.
- Per-site M operationalization (pro-D-biased sum across state_change pokes): **KNOWN** (definition); pro-D bias **KNOWN** (documented).
- Per-cluster verdict thresholds (70 % / 50 %): **KNOWN** — match R0.4 Pass criterion's 70 % with Soft Pass at half.
- Investigation-level majority aggregation: **KNOWN** (strict majority of 4 evaluated clusters).
- Whether the labels + thresholds produce correct Pass/Soft/Fail for the 29-site L-07 corpus: **UNKNOWN** — this is what L-09 evidence resolves.

## Cross-references

- ADR 0001 — pre-registration bundle; flagged this decision as UNKNOWN
- ADR 0002 — static-class threshold operationalization
- `adrs/L-07-discrimination-report.md` (`9c16385`) — cluster assignments and composition
- LANTERN.md Part 5 § Completeness criterion, Part 5 § Investigation verdict mapping
- BUILD.md §R3 L-09, R0.4
- rescan.py at `b3a8be7` — PokeOutcome.delta_added is the source of per-site M
