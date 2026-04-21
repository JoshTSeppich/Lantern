# L-06 Stability Report

**Verdict: SOFT PASS** (ratio 0.3719, in [0.20, 0.40) per LANTERN.md Part 5)

**Decision: proceed to L-07** with the caveats enumerated below. Per LANTERN.md Part 5 § Investigation verdict mapping, a Soft-Pass Stability is compatible with continuing the investigation — the outcome documents session-state as a required input (for L-06 this reduces to "documents the within-site variance contributor"). L-07 will collect discrimination evidence against the same probe protocol; inherited caveats below should be folded into L-07's read-out.

## Caveats inherited by L-07

1. **40% of probes failed (80 / 200).** Four sites produced zero usable data across all 20 cells each:
   - `e-commerce-01` (REI sale) — 20× `Error` (fast-fail < 1s per cell; consistent with connection-level refusal, possibly bot-detection or Cloudflare challenge)
   - `news-01` (Ars Technica science) — 20× `TimeoutError`
   - `news-02` (The Verge tech) — 20× `TimeoutError`
   - `saas-02` (Asana login) — 20× `TimeoutError` (SPA-routing networkidle delay was flagged as an expected observation at run-launch; this probe empirically realizes it)

   Net: 6 sites contributed data. L-07's 30-site discrimination corpus (5 per category × 6 categories) must account for this baseline failure rate when selecting sites — expect ≥30% of picks to fail and pre-register a replacement policy or a larger initial pool. This is a site-selection pragmatic for L-07, not a rubric adjustment for L-06.

2. **Wikipedia (misc-01) drove 100% of the within-site variance.** Five of six surviving sites show perfect within-site stability (`0.0000` at 95p across all 190 pairs per site). Wikipedia's within-site 95p is `0.3719` — the single non-zero contributor to the pooled 95p. Plausible mechanisms (not empirically isolated here; flag for L-07 observation if Wikipedia-class sites are probed again): dynamic article-header widgets ("featured article," "on this day," edit-count), language-selector ordering variance, or reference-list render-time ordering. `misc-01`'s `fp_size=199` places it one below the `DEFAULT_TAB_DEPTH_CAP=200`, so tab-depth saturation is not the mechanism (the cap would show up as right-censored variance, not as 0.3719-magnitude differences).

3. **HN (forum-01) saturated the tab-depth cap on all 20 probes** (`fp_size == 200`). Perfect within-site stability is nevertheless observed (`0.0000`), implying the cap-truncated prefix of HN's traversal is itself deterministic. L-07 / L-08 should read HN's fingerprint as `first-200-focusable-in-tab-order`, not `complete-page-focusable-set`. If a discrimination-cluster assignment hinges on HN's full structure, raise the cap with an ADR — do not tune silently.

4. **Wikipedia's O4 numbers show a small fresh-warm vs same-session asymmetry** (`fresh-warm mean = 0.1859` < `fresh-fresh mean = 0.2066`). This is the only site where O4 is non-zero anywhere, and the asymmetry is small (within the magnitude of Wikipedia's general within-site noise). It is noted, not investigated — if L-07 reveals a meaningful warm-state signal, revisit probe.py's warm implementation. Not grounds to tune L-06's verdict.

5. **SaaS-login artificial-closeness flag** (pre-registered 2026-04-20) did not produce cross-category distortion here because `saas-02` failed 100% — only `saas-01` contributed SaaS data. The flag remains relevant for L-07 where discrimination clustering may pull SaaS logins into a marketing-landing cluster; the flag's empirical test moves to L-07.

## Levenshtein distance fidelity note

The pooled cross-site 95p `1.0000` means: for 5% of cross-site probe pairs, the normalized Levenshtein distance is at maximum (the two fingerprints share zero common subsequence after alignment). This is consistent with the probe set containing genuinely distinct shape classes (HN's link-list, Wikipedia's content-article, Stripe's marketing landing, Linear's login form, Tesla's product grid, Tailwind's docs-marketing) — cross-site distance saturates because the fingerprints are structurally unrelated at their 95p.

The ratio `0.3719 / 1.0000 = 0.3719` is driven almost entirely by Wikipedia's within-site 95p. If Wikipedia were dropped, the pooled within-site 95p would collapse to `0.0000` and the ratio would be `0.0000` → Pass. This counterfactual is recorded for transparency; it is NOT acted on — dropping a pre-registered site post-evidence is the textbook rubric-drift failure (§R4 `rubric-drift`). Wikipedia stays.



## Probe accounting

- Probes recorded: 200
- Probes succeeded (status=ok): 120
- Probes failed (status=error): 80
- Sites with at least one ok probe: 6
- Within-site ok-pairs: 1140
- Cross-site ok-pairs: 6000

## Pooled metrics (normalized Levenshtein)

- Within-site 95th percentile: 0.3719
- Cross-site 95th percentile: 1.0000
- Ratio (within / cross) at 95p: 0.3719

## Rubric (frozen in LANTERN.md Part 5 § Stability criterion)

| Verdict | Ratio threshold |
|---|---|
| Pass | < 0.20 |
| Soft Pass | 0.20 – 0.40 |
| Fail | ≥ 0.40 |

## Per-site within-site 95p

| Site | Category | Ok probes | Pairs | Within-site 95p |
|---|---|---:|---:|---:|
| e-commerce-02 | e-commerce | 20 | 190 | 0.0000 |
| forum-01 | forum | 20 | 190 | 0.0000 |
| marketing-01 | marketing | 20 | 190 | 0.0000 |
| marketing-02 | marketing | 20 | 190 | 0.0000 |
| misc-01 | misc | 20 | 190 | 0.3719 |
| saas-01 | saas | 20 | 190 | 0.0000 |

## O1 — Per-site error rate (pre-registered observation)

| Site | Ok / Total | Error types |
|---|---:|---|
| e-commerce-01 | 0/20 | Error×20 |
| e-commerce-02 | 20/20 | — |
| forum-01 | 20/20 | — |
| marketing-01 | 20/20 | — |
| marketing-02 | 20/20 | — |
| misc-01 | 20/20 | — |
| news-01 | 0/20 | TimeoutError×20 |
| news-02 | 0/20 | TimeoutError×20 |
| saas-01 | 20/20 | — |
| saas-02 | 0/20 | TimeoutError×20 |

## O2 — Per-site `timing.total_elapsed_ms` distribution (ok probes)

Sanity-checks whether `settle_ms=2000` holds; SPA-heavy sites may push the tail. Units: milliseconds.

| Site | n | min | median | p95 | max |
|---|---:|---:|---:|---:|---:|
| e-commerce-02 | 20 | 2778 | 2831 | 2929 | 2967 |
| forum-01 | 20 | 3568 | 3663 | 3821 | 3855 |
| marketing-01 | 20 | 6245 | 6618 | 7663 | 7793 |
| marketing-02 | 20 | 4444 | 4624 | 4984 | 5123 |
| misc-01 | 20 | 4137 | 4272 | 4645 | 4684 |
| saas-01 | 20 | 3727 | 3974 | 4331 | 4736 |

## O3 — 200-endpoint cap saturation (DEFAULT_TAB_DEPTH_CAP=200)

Sites where at least one probe hit the tab-depth cap. A capped probe truncated the traversal before body-return / already-seen; its fingerprint is biased (right-censored).

| Site | Saturated probes | Total ok probes |
|---|---:|---:|
| forum-01 | 20 | 20 |

## O4 — Session-state `warm` vs `fresh` sanity check

Mean within-site normalized-Levenshtein, stratified by pair type. probe.py's known limitation (warm currently == fresh in implementation) predicts the three means to be indistinguishable. Material separation of fresh–warm from fresh–fresh and warm–warm would be a surprise finding.

| Site | fresh–fresh (n) | warm–warm (n) | fresh–warm (n) |
|---|---|---|---|
| e-commerce-02 | 0.0000 (45) | 0.0000 (45) | 0.0000 (100) |
| forum-01 | 0.0000 (45) | 0.0000 (45) | 0.0000 (100) |
| marketing-01 | 0.0000 (45) | 0.0000 (45) | 0.0000 (100) |
| marketing-02 | 0.0000 (45) | 0.0000 (45) | 0.0000 (100) |
| misc-01 | 0.2066 (45) | 0.2066 (45) | 0.1859 (100) |
| saas-01 | 0.0000 (45) | 0.0000 (45) | 0.0000 (100) |

## Known findings (flagged pre-run, 2026-04-20)

1. **saas-01 + saas-02 both are login pages** (Linear + Asana). Login form shapes are structurally near-identical regardless of underlying product: two inputs + submit button dominate the fingerprint. Cross-site-within-SaaS distance will be artificially low. Not a rubric problem (rubric pools cross-site across ALL different-site pairs, not per-category), but a shape-class boundary signal: if L-07 discrimination clusters SaaS logins with marketing-landing forms rather than as their own class, that is a substantive finding about what 'SaaS dashboard shape' means when the authenticated surface is out of scope per LANTERN.md Part 5.

2. **Forum category has 1 site (HN), not 2.** No within-category cross-site comparison possible for forum; the uneven distribution documented in `sites_stability.yaml` acknowledges this. L-07's 5-sites-per-category design fills the gap.

3. **probe.py `session_state='warm'` currently == `'fresh'`** (fresh BrowserContext per probe, no cross-probe cookie retention). Observation O4 above is the sanity check: three within-site pair-type means are expected indistinguishable.

Cookie banners on EU-served responses, SPA routing-induced networkidle delay, and near-zero within-site variance on HN/Wikipedia were named as expected observations at run-launch (operator 2026-04-20). They land here as observations, never as rubric-relaxation evidence.
