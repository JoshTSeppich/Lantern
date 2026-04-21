# L-07 Discrimination Report

**Verdict: SOFT PASS** (k_optimal=5 in Pass range [4, 8]; mean category majority 0.6214 in Soft Pass range (0.50, 0.70]; mixed-tier resolves to SOFT PASS per pre-registered operationalization at 32f5f43)

**Decision: proceed to L-08** with the caveats enumerated below. Per LANTERN.md Part 5 § Investigation verdict mapping, the tabulated branches cover Pass/Fail on Discrimination but leave Soft Pass implicit. Applying the same Soft-Pass-means-proceed-with-caveats pattern that L-06 followed (operator 2026-04-21): continue to Completeness (L-09 after L-08 `rescan.py` lands), name the substantive findings below in the inherited caveat list, and let downstream tickets confirm whether the shape-cluster-vs-operator-category gap is a Methodology-D concern or a category-label concern.

## Primary substantive finding

**Operator categories and shape-based clusters do not align 1:1.** This is not a probe bug — it is what the methodology is *for*. Two clusters are category-pure; two clusters are heterogeneous; one is a singleton.

| cluster | size | composition pattern | majority | interpretation |
|---:|---:|---|---:|---|
| 0 | 1 | Tesla Shop only | 1.0000 | Singleton product page. Most distinctive shape in the corpus. |
| 1 | 4 | HN + Lobsters + Tailwind + RFC 8259 | 0.50 (forum) | **Dense-link-list shape class.** HN and Lobsters are aggregators (forum); Tailwind's marketing landing and the RFC page both present as long lists of links/anchors. Shape-based clustering found "pages dominated by repeated link rows" as a real class, ignoring our forum/marketing/misc labels. |
| 2 | 2 | GitHub login + Vercel login | 1.0000 (saas) | **Minimal-login shape class.** Pre-registered `saas-login-artificial-closeness` flag (2026-04-20) partially vindicated: login pages on strict-server-rendered stacks cluster together. |
| 3 | 14 | marketing/misc/ecom/news mix | 0.3571 (marketing) | **Dominant cluster.** 14 of 29 sites. Marketing-like hero-plus-nav-plus-callouts structure swallows Wikipedia articles, small e-commerce landings, a few news front pages, and most marketing pages. The declared category doesn't predict membership here. |
| 4 | 8 | saas-login / SE-forum / MDN / ecom / news / Fastly / Slack | 0.2500 (saas) | **Heterogeneous.** Lowest majority (25%). Linear login + Slack signin here, not in cluster 2 — login-shape split across two clusters. |

Clusters 0, 1, 2 are interpretable as shape classes. Cluster 3 is a big catch-all that hints the A+B+C fingerprint is *under-discriminating* on medium-complexity pages. Cluster 4 is the heterogeneous residual.

**The L-06 SaaS-login artificial-closeness flag is partially vindicated.** Cluster 2 captures GitHub + Vercel login — two server-rendered logins cluster as shape-pure. But Linear login (d03) and Slack signin (d21) landed in cluster 4 (heterogeneous), not cluster 2. Different login stacks cluster differently — the SaaS-login-shape is not monolithic. This is a substantive finding: "what 'SaaS dashboard shape' means when the authenticated surface is out-of-scope" depends on the login stack's server-rendered-vs-SPA architecture, not on the vendor's product category.

## Caveats inherited by L-08 / L-09

1. **Failure rate stayed high (11/40 = 27.5%).** Down from L-06's 40% but still substantial. 4/7 news sites failed (d08 Slashdot, d14 NPR, d26 AP, d32 BBC); 3/7 SaaS sites failed (d15 GitLab, d27 Trello, d39 Stripe dashboard); 2/7 ecom failed (d25 Nintendo, d37 Uniqlo); 2/6 forum failed (d23 Unix SE, d35 Super User). Marketing and misc categories reached 100% success. L-08/L-09's corpus remains the 29 survivors — no retries, no substitutions.

2. **News is underrepresented** (3 of 7 survived: d02 Wikipedia-current-events, d20 Reuters, d38 ProPublica). None of the surviving news sites clustered together — d02 and d38 joined the marketing-like cluster 3; d20 joined the heterogeneous cluster 4. News-as-a-shape-class did not emerge from the evidence. If L-09 Completeness evaluation requires stable news-class labels, flag that news didn't cluster as a distinct shape in L-07.

3. **Cluster 3 is too large (14/29 = 48%).** Dominating cluster suggests the A+B+C static fingerprint under-discriminates on medium-complexity pages. Plausible mechanisms (not isolated here; flag for L-08/L-09 observation): (a) role vocabulary collapses many distinct CMS/framework outputs into the same coarse role sequence; (b) landmark vocabulary of 5 HTML tags is too coarse to separate "marketing hero" from "Wikipedia article intro"; (c) state bitmap is mostly zero on content-heavy static pages, contributing little signal. Methodology D's state-transitions (L-08) may provide the separation that the static fingerprint lacks.

4. **HN (d05-forum-01) still saturates the 200-endpoint cap** and clustered with Lobsters (uncapped). Cap-frozen per operator 2026-04-21; the clustering result is consistent with truncation being a stable-enough fingerprint prefix.

5. **Shape-cluster labeling is an open question.** Per R0.1 the library is the output of this discrimination. The 5 emergent clusters produce a library with 5 shapes (see `data/clusters/l07_library.json`, gitignored per §R1.1). Naming them ("dense-link-list", "minimal-login", "marketing-catch-all", "heterogeneous", "singleton-product") is interpretive, not algorithmic. For L-08/L-09 scorecards, the cluster IDs (0..4) are the stable reference; category-majority labels are informational.

6. **ADR 0003 scope sharpens.** The pre-L-09 dynamic/static class-label ADR (queued from ADR 0001) now has concrete clusters to label. Per the cluster interpretations above:
     - Cluster 0 (Tesla product page): **dynamic** — product listings reveal variant-selectors.
     - Cluster 1 (dense-link-list): **static** — link aggregators don't state-transition on click; links navigate away.
     - Cluster 2 (minimal-login): **dynamic** — form submission reveals validation errors + post-login state.
     - Cluster 3 (marketing-catch-all): **mixed** — contains both Wikipedia-article (static) and marketing hero (often dynamic with modals). May need further splitting.
     - Cluster 4 (heterogeneous): **mixed** — not coherent enough to label as a unit. Flag for pre-L-09 investigation.
   These are proposals to be committed as ADR 0003 alongside the operational threshold (ADR 0002 already committed).

## Silhouette stability sanity check

The silhouette score landscape is relatively flat in the range k=4..9 (all between 0.27 and 0.29). k_optimal=5 wins by a small margin over k=7 (0.2876 vs 0.2859). This means the cluster structure is moderately stable — the corpus doesn't have strongly-preferred discrete k. If L-08/L-09 evidence later suggests k=7 produces better-aligned clusters with operator categories, that would be a finding about the silhouette metric's resolution on this corpus, not grounds to retune the selector.

## Corpus accounting

- Probes attempted: 40
- Probes ok: 29
- Probes failed: 11
- Corpus (first-30-ok mechanical filter): 29

## Silhouette-based cluster-count selection

| k | silhouette |
|---:|---:|
| 2 | 0.1157 |
| 3 | 0.1925 |
| 4 | 0.2794 |
| 5 | 0.2876 ← k_optimal |
| 6 | 0.2841 |
| 7 | 0.2859 |
| 8 | 0.2693 |
| 9 | 0.2838 |
| 10 | 0.2670 |
| 11 | 0.2553 |
| 12 | 0.2454 |

**k_optimal = 5** (argmax silhouette; tiebreak = smaller k)

## Cluster composition at k_optimal

- Clusters: 5
- Mean category majority: 0.6214
- Min category majority:  0.2500
- Max category majority:  1.0000

| cluster | size | majority category | majority | members |
|---:|---:|---|---:|---|
| 0 | 1 | e-commerce | 1.0000 | d01-ecom-01 |
| 1 | 4 | forum | 0.5000 | d05-forum-01, d10-mkt-02, d11-forum-02, d30-misc-05 |
| 2 | 2 | saas | 1.0000 | d09-saas-02, d33-saas-06 |
| 3 | 14 | marketing | 0.3571 | d02-news-01, d04-mkt-01, d06-misc-01, d07-ecom-02, d12-misc-02, d13-ecom-03, d16-mkt-03, d22-mkt-04, d24-misc-04, d28-mkt-05, d29-forum-05, d34-mkt-06, d36-misc-06, d38-news-07 |
| 4 | 8 | saas | 0.2500 | d03-saas-01, d17-forum-03, d18-misc-03, d19-ecom-04, d20-news-04, d21-saas-04, d31-ecom-06, d40-mkt-07 |

## Rubric (frozen in LANTERN.md Part 5 § Discrimination criterion)

| Verdict | k | category-majority (mean) |
|---|---|---|
| Pass | 4–8 | > 0.70 |
| Soft Pass | 3 or 9–12 | 0.50 – 0.70 |
| Fail | 1–2 or > 12 | ≤ 0.50 |

## Per-site category and cluster assignment

| site_id | declared category | cluster | cluster majority category |
|---|---|---:|---|
| d01-ecom-01 | e-commerce | 0 | e-commerce |
| d02-news-01 | news | 3 | marketing |
| d03-saas-01 | saas | 4 | saas |
| d04-mkt-01 | marketing | 3 | marketing |
| d05-forum-01 | forum | 1 | forum |
| d06-misc-01 | misc | 3 | marketing |
| d07-ecom-02 | e-commerce | 3 | marketing |
| d09-saas-02 | saas | 2 | saas |
| d10-mkt-02 | marketing | 1 | forum |
| d11-forum-02 | forum | 1 | forum |
| d12-misc-02 | misc | 3 | marketing |
| d13-ecom-03 | e-commerce | 3 | marketing |
| d16-mkt-03 | marketing | 3 | marketing |
| d17-forum-03 | forum | 4 | saas |
| d18-misc-03 | misc | 4 | saas |
| d19-ecom-04 | e-commerce | 4 | saas |
| d20-news-04 | news | 4 | saas |
| d21-saas-04 | saas | 4 | saas |
| d22-mkt-04 | marketing | 3 | marketing |
| d24-misc-04 | misc | 3 | marketing |
| d28-mkt-05 | marketing | 3 | marketing |
| d29-forum-05 | forum | 3 | marketing |
| d30-misc-05 | misc | 1 | forum |
| d31-ecom-06 | e-commerce | 4 | saas |
| d33-saas-06 | saas | 2 | saas |
| d34-mkt-06 | marketing | 3 | marketing |
| d36-misc-06 | misc | 3 | marketing |
| d38-news-07 | news | 3 | marketing |
| d40-mkt-07 | marketing | 4 | saas |

## L-06 context inherited (operator 2026-04-21)

Two L-06 findings reframe the L-07 read-out:

- **Probe success at L-06 was binary** (6/10 clean ok, 4/10 total fail; zero intermediate). Failure mode is deterministic, not stochastic — the first-30-ok mechanical filter is correct because retries would not help. If L-07 shows a similar binary distribution, the 40-site over-provision pattern (7/7/7/7/6/6) is the right corpus-robustness strategy.
- **Five of six L-06-surviving sites had perfect within-site stability.** The L-06 Soft-Pass verdict (ratio 0.3719) was driven entirely by Wikipedia. On sites where the probe protocol works at all, within-site determinism is near-perfect — the methodology is stronger than the L-06 Soft-Pass headline suggests. L-07's discrimination test sits on top of that within-site-determinism floor.

## Library bootstrap

Per R0.1, the library does not exist prior to the discrimination test; it is the output of the discrimination test. One shape per cluster, written to data/clusters/l07_library.json (gitignored per §R1.1; regeneratable). Each shape records its cluster_id, member site_ids, majority category, and a representative fingerprint (the member whose mean-distance-to-other-members is lowest).
