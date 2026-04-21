# L-09 Completeness Report

**Completeness verdict: SOFT PASS (ratio-level)**
**Scope-down trigger: YES — fires via Cluster 0 FAIL (read Primary Caveat below before acting)**

## Primary caveat

**The scope-down trigger for Methodology D is fired by a singleton cluster (Cluster 0, n=1) whose sole member (Tesla Shop, `d01-ecom-01`) has `N = 0` — i.e., the site produced a zero-focusable-element fingerprint at both L-07 (`057c86e`) and L-09.** The site appears to serve a blank or bot-challenge page to our Playwright client; it was probed as `e-commerce-02` at L-06 (`594e42e`) with a non-zero fingerprint and perfect within-site stability, so the N=0 behavior emerged between 2026-04-20 and 2026-04-21 (most likely an anti-bot detection change on Tesla's side).

Under the pre-registered rubric (ADR 0003 part (b), ADR 0002), `M / N = 0 / 0 → treated as 0.0 → 0.0 < 0.25 → FAIL`. That rule produces Cluster 0 FAIL, which per BUILD.md §R3 L-09 + LANTERN.md Part 5 verdict mapping triggers scope-down on Methodology D.

**Mechanical rubric application stands.** Per operator 2026-04-21 ("If Fail: halt per §R3. Don't improvise remediation"), this report applies the pre-registered rule without post-hoc adjustment. The scope-down trigger is reported as fired.

However, the epistemic weight of a 1-site cluster driven entirely by an un-probeable site is low. A remediation PATH exists (operator direction required): **a new ADR could reclassify Cluster 0 as INDETERMINATE alongside Cluster 4 on the grounds that `N = 0` makes the cluster un-evaluable.** Under that reclassification, n_evaluated would drop to 3 (Clusters 1, 2, 3), the halt trigger would not fire, and the Completeness verdict would become PASS via strict majority of 3 (`n_pass = 2` vs evaluated 3 — actually that doesn't give PASS either, it's 2/3 = 0.67 which is short of strict majority). Let me re-work:

- Under `n_evaluated = 3`: n_pass = 2 (Clusters 1, 3), n_pass_soft = 3 (Clusters 1, 2, 3). Strict majority is `> 1.5` → `n_pass = 2` ≥ 2 → PASS.

So reclassifying Cluster 0 as INDETERMINATE flips the investigation verdict from SOFT PASS (with scope-down) to PASS (no scope-down). This is a real remediation option, not a cosmetic one.

**This remediation is not taken here.** It requires operator direction + a new ADR explicitly addressing the N=0 case. The pre-registered rubric stands as-is in this report; Cluster 0 FAIL is reported; scope-down trigger is reported.

See the "Remediation options" section at the end of this report for detail.



## Scoring summary

- Evaluated clusters (ADR 0003 part (a)): 4 of 5 (Cluster 4 INDETERMINATE excluded)
- Clusters at Pass: 2
- Clusters at Pass or Soft Pass: 3
- Halt trigger (dynamic-cluster fail → scope-down Methodology D): YES

## Per-cluster verdicts

| cluster | label | size | n_pass | pass_rate | verdict | majority category |
|---:|---|---:|---:|---:|---|---|
| 0 | dynamic | 1 | 0 | 0.0000 | FAIL | e-commerce |
| 1 | static | 4 | 4 | 1.0000 | PASS | forum |
| 2 | dynamic | 2 | 1 | 0.5000 | SOFT PASS | saas |
| 3 | static | 14 | 12 | 0.8571 | PASS | marketing |
| 4 | indeterminate | 8 | 0 | 0.0000 | EXCLUDED | saas |

## Rubric (ADR 0003 part (b) + ADR 0002)

Per-site verdict:
- Dynamic cluster: site passes iff `M / N >= 0.25` (R0.4 (i))
- Static cluster:  site passes iff `M <= max(2, ceil(0.05 * N))` (ADR 0002)
- L-09 error → per-site FAIL

Per-cluster verdict:
- Pass:      pass_rate >= 0.70
- Soft Pass: 0.50 <= pass_rate < 0.70
- Fail:      pass_rate < 0.50

Investigation-level verdict (over evaluated clusters, Cluster 4 excluded):
- PASS:      `n_pass > n_evaluated / 2`
- SOFT PASS: `n_pass_soft > n_evaluated / 2 AND NOT PASS`
- FAIL:      otherwise

## Per-site detail

| cluster | site_id | label | N | M | threshold | passed | reason |
|---:|---|---|---:|---:|---|---|---|
| 0 | d01-ecom-01 | dynamic | 0 | 0 | M/N>=0.25 | no | M/N=0.0000 vs threshold=0.25 |
| 1 | d05-forum-01 | static | 200 | 0 | M<=max(2, ceil(0.05*200))=10 | yes | M=0 vs threshold=max(2, ceil(0.05*200))=10 |
| 1 | d10-mkt-02 | static | 102 | 0 | M<=max(2, ceil(0.05*102))=6 | yes | M=0 vs threshold=max(2, ceil(0.05*102))=6 |
| 1 | d11-forum-02 | static | 200 | 0 | M<=max(2, ceil(0.05*200))=10 | yes | M=0 vs threshold=max(2, ceil(0.05*200))=10 |
| 1 | d30-misc-05 | static | 169 | 0 | M<=max(2, ceil(0.05*169))=9 | yes | M=0 vs threshold=max(2, ceil(0.05*169))=9 |
| 2 | d09-saas-02 | dynamic | 13 | 6 | M/N>=0.25 | yes | M/N=0.4615 vs threshold=0.25 |
| 2 | d33-saas-06 | dynamic | 14 | 3 | M/N>=0.25 | no | M/N=0.2143 vs threshold=0.25 |
| 3 | d02-news-01 | static | 198 | 171 | M<=max(2, ceil(0.05*198))=10 | no | M=171 vs threshold=max(2, ceil(0.05*198))=10 |
| 3 | d04-mkt-01 | static | 154 | 48 | M<=max(2, ceil(0.05*154))=8 | no | M=48 vs threshold=max(2, ceil(0.05*154))=8 |
| 3 | d06-misc-01 | static | 198 | 0 | M<=max(2, ceil(0.05*198))=10 | yes | M=0 vs threshold=max(2, ceil(0.05*198))=10 |
| 3 | d07-ecom-02 | static | 40 | 0 | M<=max(2, ceil(0.05*40))=2 | yes | M=0 vs threshold=max(2, ceil(0.05*40))=2 |
| 3 | d12-misc-02 | static | 198 | 0 | M<=max(2, ceil(0.05*198))=10 | yes | M=0 vs threshold=max(2, ceil(0.05*198))=10 |
| 3 | d13-ecom-03 | static | 132 | 0 | M<=max(2, ceil(0.05*132))=7 | yes | M=0 vs threshold=max(2, ceil(0.05*132))=7 |
| 3 | d16-mkt-03 | static | 102 | 2 | M<=max(2, ceil(0.05*102))=6 | yes | M=2 vs threshold=max(2, ceil(0.05*102))=6 |
| 3 | d22-mkt-04 | static | 189 | 0 | M<=max(2, ceil(0.05*189))=10 | yes | M=0 vs threshold=max(2, ceil(0.05*189))=10 |
| 3 | d24-misc-04 | static | 74 | 0 | M<=max(2, ceil(0.05*74))=4 | yes | M=0 vs threshold=max(2, ceil(0.05*74))=4 |
| 3 | d28-mkt-05 | static | 100 | 0 | M<=max(2, ceil(0.05*100))=5 | yes | M=0 vs threshold=max(2, ceil(0.05*100))=5 |
| 3 | d29-forum-05 | static | 200 | 0 | M<=max(2, ceil(0.05*200))=10 | yes | M=0 vs threshold=max(2, ceil(0.05*200))=10 |
| 3 | d34-mkt-06 | static | 72 | 0 | M<=max(2, ceil(0.05*72))=4 | yes | M=0 vs threshold=max(2, ceil(0.05*72))=4 |
| 3 | d36-misc-06 | static | 198 | 0 | M<=max(2, ceil(0.05*198))=10 | yes | M=0 vs threshold=max(2, ceil(0.05*198))=10 |
| 3 | d38-news-07 | static | 188 | 0 | M<=max(2, ceil(0.05*188))=10 | yes | M=0 vs threshold=max(2, ceil(0.05*188))=10 |
| 4 | d03-saas-01 | indeterminate | 7 | 0 | n/a | no | unexpected cluster label indeterminate |
| 4 | d17-forum-03 | indeterminate | 7 | 0 | n/a | no | unexpected cluster label indeterminate |
| 4 | d18-misc-03 | indeterminate | 2 | 0 | n/a | no | unexpected cluster label indeterminate |
| 4 | d19-ecom-04 | indeterminate | 4 | 0 | n/a | no | unexpected cluster label indeterminate |
| 4 | d20-news-04 | indeterminate | 1 | 0 | n/a | no | unexpected cluster label indeterminate |
| 4 | d21-saas-04 | indeterminate | 7 | 0 | n/a | no | unexpected cluster label indeterminate |
| 4 | d31-ecom-06 | indeterminate | 4 | 0 | n/a | no | unexpected cluster label indeterminate |
| 4 | d40-mkt-07 | indeterminate | 6 | 0 | n/a | no | unexpected cluster label indeterminate |

## Halt-rule assessment (BUILD.md §R3 L-09)

**Completeness FAIL on dynamic cluster(s) → SCOPE-DOWN TRIGGERED.**

Failed dynamic clusters: [0]

Per LANTERN.md Part 5 Investigation verdict mapping + BUILD.md §R3 L-09,
Lantern scopes down to A+B+C only: Methodology D is dropped from the
production pipeline. rescan.py remains committed as a research artifact;
it does not ship with the classify() public surface.

This is the architected scope-down branch that made L-SPIKE-04 acceptable
at rank-2 behind L-SPIKE-02 (operator 2026-04-20). D was spike-first despite
higher failure probability precisely because this exit is pre-registered.

## Cluster 4 observation (INDETERMINATE, excluded from verdict)

Per ADR 0003 part (a), Cluster 4 is heterogeneous (saas plurality 25%;
no meaningful majority). Forcing a dynamic/static label would be dishonest.
Its per-site delta distribution is documented here for observation only —
does NOT contribute to the Pass/Soft/Fail arithmetic above.

| site_id | declared category | L-07 N | L-09 M | L-09 status |
|---|---|---:|---:|---|
| d03-saas-01 | saas | 7 | 0 | ok |
| d17-forum-03 | forum | 7 | 0 | ok |
| d18-misc-03 | misc | 2 | 0 | ok |
| d19-ecom-04 | e-commerce | 4 | 0 | ok |
| d20-news-04 | news | 1 | 0 | ok |
| d21-saas-04 | saas | 7 | 0 | ok |
| d31-ecom-06 | e-commerce | 4 | 0 | ok |
| d40-mkt-07 | marketing | 6 | 0 | ok |

All 8 Cluster-4 members produced `M = 0`. N values range from 1 (Reuters) to 7 (Linear login, Stack Overflow, Slack signin). Low N values are consistent with Cluster 4's heterogeneity — the sites in this cluster do not have rich static structures that the A+B+C fingerprint captures (some are SPA login pages that render minimal HTML before JS, others are pages that may themselves be partially bot-blocked or minimally rendered).

## Methodology D substantive findings

These findings do NOT alter the verdict; they are observations from the L-09 evidence that sharpen interpretation.

**Cluster 1 (static, theory-grounded) passed with no false positives.** All 4 members (HN, Lobsters, Tailwind, RFC 8259) produced `M = 0`. Zero spurious state_changes detected; link-click outcomes were categorized as `navigation`, which by construction contributes 0 to M. This vindicates the theory-grounded static label.

**Cluster 3 (static, plurality-grounded) passed at 85.7% with 2 substantive failures.** Wikipedia Current Events (`d02-news-01`, `M = 171`) and Stripe marketing (`d04-mkt-01`, `M = 48`) produced large deltas — sufficient to suggest these sites' shape is NOT actually static. The plurality-grounded label's weakness (pre-registered in ADR 0003) is empirically confirmed for these two members. Neither is grounds to flip the cluster's label post-hoc per ADR 0003; they are findings about cluster coherence at the A+B+C fingerprint resolution.

**Cluster 2 (dynamic, theory-grounded) SOFT PASSED at 50%.** GitHub login (`d09-saas-02`, `M/N = 0.4615`) comfortably cleared the 25% threshold. Vercel login (`d33-saas-06`, `M/N = 0.2143`) fell just under. Both are minimal-login shape but expose different state-change surface volumes under our K=10 poking. This is the expected shape-is-real-but-noisy pattern for a small cluster.

**Per-poke error rate was substantial on content-rich sites.** Many pokes (especially on Cluster-3 members with large N) returned `error` due to click-intercept or element-not-found when `get_by_role(...).first.click(...)` targeted an overlaid element. These errors contribute 0 to M (not state_change, not delta_added), so they don't inflate M — but they DO reduce the effective state-change observation opportunities per site. If a site has 10 pokes and 8 of them error, the site's M reflects only 2 actual rescan observations. Noted as a per-poke-noise finding; does not change the verdict.

**K = 10 sampling cap (ADR 0005) bit on 9 of 29 sites** (all_candidates_count > 10). On those sites, some selected_candidates were truncated from the full candidate list, ordered by policy priority (a→b→c→d). Sites where the cap bit: d02, d04, d06, d07, d12, d13, d16, d22, d24, d28, d29, d34, d36, d38 (reading from log). Most are Cluster 3 (marketing-catch-all), consistent with those sites having large candidate sets. The K=10 anti-D bias discussed in ADR 0005 partially offsets the pro-D bias of M-double-counting; Cluster 3's 85.7% pass rate remains robust under this offset.

## Remediation options

Triggered by the Primary Caveat above. Presented for operator decision; NOT applied in this report.

### Option A — Accept the scope-down trigger as-is

Mechanical rubric application. Cluster 0 FAIL → scope-down. Methodology D is dropped from the production pipeline; `rescan.py` remains a research artifact. This is the architected exit that made L-SPIKE-04 acceptable at rank-2 (operator 2026-04-20).

**Epistemic posture:** pre-registered rubric honored without post-hoc adjustment. Honest to the pre-registration discipline.

**Weakness:** the scope-down is triggered by one un-probeable site in a singleton cluster. The methodology wasn't meaningfully tested on Cluster 0; the FAIL verdict is a rule-application artifact, not a theory-under-test failing.

### Option B — Author a new ADR reclassifying Cluster 0 as INDETERMINATE

On the grounds that `N = 0` makes the cluster un-evaluable by the rubric (division-by-zero produces a non-finding, not a failure). Extend ADR 0003 or supersede it with a new ADR 0006 that adds an INDETERMINATE branch to per-site verdict logic when `N = 0`, and propagates it to cluster labels.

**Effect on verdict:** n_evaluated drops from 4 to 3 (Clusters 1, 2, 3). `n_pass = 2` (Clusters 1, 3). Strict majority of 3 requires `n_pass > 1.5` → `n_pass = 2` IS strict majority → **Completeness PASS**. Scope-down does NOT trigger.

**Epistemic posture:** acknowledges that an un-probeable site shouldn't count as Methodology-D failure. Defensible on first-principles.

**Weakness:** at the edge of "post-hoc remediation that the operator explicitly warned against" (2026-04-21: "Don't improvise remediation"). The N=0 edge case was not anticipated in ADR 0003; addressing it requires judgment about whether it qualifies as a pre-evidence correction vs post-evidence drift. The empirical site-state change (Tesla Shop 2026-04-20 → 2026-04-21) is a defensible non-Methodology cause.

### Option C — Expand the L-09 corpus with a replacement for d01-ecom-01

Pick a replacement dynamic-ecommerce site that probes with N > 0, run an additional rescan on it, re-score Cluster 0.

**Effect on verdict:** depends on the replacement site's M. A site with meaningful state-change would likely pass Cluster 0; a site without would also produce Cluster 0 FAIL with better epistemic weight.

**Epistemic posture:** extends the corpus post-L-07, which is textbook rubric-drift for the L-07 corpus. Least defensible.

**Weakness:** violates pre-registration on corpus; requires a full retreat on L-07's "no retry on corpus" pre-registration. Would require unwinding multiple earlier commitments.

### Recommendation

**Option B** looks cleanest if operator wants to avoid scope-down despite the rule-application FAIL. The N=0 case is narrow and defensible as a pre-registration gap rather than a theory-under-test failure. An ADR 0006 adding "N = 0 → per-site verdict INDETERMINATE" is a small addition that handles this class of un-probeable site cleanly for future phases (L-12 utility) too.

**Option A** is the path if operator wants to honor the mechanical rubric strictly. The architected scope-down is exactly the kind of exit L-SPIKE-04 was gated on.

**Option C** is likely not a good path — the corpus-expansion precedent is expensive.

This report applies **neither A nor B nor C** — it reports the verdict as pre-registered and surfaces the options. Operator decides.
