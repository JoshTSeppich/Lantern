# L-09 Completeness Report

**Completeness verdict: PASS**

## Scoring summary

- Evaluated clusters: 3 of 5 (Cluster 4 label INDETERMINATE per ADR 0003; additionally any cluster with all sites INDETERMINATE per ADR 0006 is excluded)
- Clusters at Pass: 2
- Clusters at Pass or Soft Pass: 3
- Halt trigger (dynamic-cluster fail → scope-down Methodology D): no

## Per-cluster verdicts

| cluster | label | size | n_pass | n_fail | n_indet | n_eval | pass_rate | verdict | majority category |
|---:|---|---:|---:|---:|---:|---:|---:|---|---|
| 0 | dynamic | 1 | 0 | 0 | 1 | 0 | — | INDETERMINATE | e-commerce |
| 1 | static | 4 | 4 | 0 | 0 | 4 | 1.0000 | PASS | forum |
| 2 | dynamic | 2 | 1 | 1 | 0 | 2 | 0.5000 | SOFT PASS | saas |
| 3 | static | 14 | 12 | 2 | 0 | 14 | 0.8571 | PASS | marketing |
| 4 | indeterminate | 8 | 0 | 0 | 8 | 0 | — | EXCLUDED | saas |

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

| cluster | site_id | label | N | M | threshold | verdict | reason |
|---:|---|---|---:|---:|---|---|---|
| 0 | d01-ecom-01 | dynamic | 0 | 0 | M/N>=0.25 | INDETERMINATE | N=0 un-probeable site (ADR 0006) |
| 1 | d05-forum-01 | static | 200 | 0 | M<=max(2, ceil(0.05*200))=10 | PASS | M=0 vs threshold=max(2, ceil(0.05*200))=10 |
| 1 | d10-mkt-02 | static | 102 | 0 | M<=max(2, ceil(0.05*102))=6 | PASS | M=0 vs threshold=max(2, ceil(0.05*102))=6 |
| 1 | d11-forum-02 | static | 200 | 0 | M<=max(2, ceil(0.05*200))=10 | PASS | M=0 vs threshold=max(2, ceil(0.05*200))=10 |
| 1 | d30-misc-05 | static | 169 | 0 | M<=max(2, ceil(0.05*169))=9 | PASS | M=0 vs threshold=max(2, ceil(0.05*169))=9 |
| 2 | d09-saas-02 | dynamic | 13 | 6 | M/N>=0.25 | PASS | M/N=0.4615 vs threshold=0.25 |
| 2 | d33-saas-06 | dynamic | 14 | 3 | M/N>=0.25 | FAIL | M/N=0.2143 vs threshold=0.25 |
| 3 | d02-news-01 | static | 198 | 171 | M<=max(2, ceil(0.05*198))=10 | FAIL | M=171 vs threshold=max(2, ceil(0.05*198))=10 |
| 3 | d04-mkt-01 | static | 154 | 48 | M<=max(2, ceil(0.05*154))=8 | FAIL | M=48 vs threshold=max(2, ceil(0.05*154))=8 |
| 3 | d06-misc-01 | static | 198 | 0 | M<=max(2, ceil(0.05*198))=10 | PASS | M=0 vs threshold=max(2, ceil(0.05*198))=10 |
| 3 | d07-ecom-02 | static | 40 | 0 | M<=max(2, ceil(0.05*40))=2 | PASS | M=0 vs threshold=max(2, ceil(0.05*40))=2 |
| 3 | d12-misc-02 | static | 198 | 0 | M<=max(2, ceil(0.05*198))=10 | PASS | M=0 vs threshold=max(2, ceil(0.05*198))=10 |
| 3 | d13-ecom-03 | static | 132 | 0 | M<=max(2, ceil(0.05*132))=7 | PASS | M=0 vs threshold=max(2, ceil(0.05*132))=7 |
| 3 | d16-mkt-03 | static | 102 | 2 | M<=max(2, ceil(0.05*102))=6 | PASS | M=2 vs threshold=max(2, ceil(0.05*102))=6 |
| 3 | d22-mkt-04 | static | 189 | 0 | M<=max(2, ceil(0.05*189))=10 | PASS | M=0 vs threshold=max(2, ceil(0.05*189))=10 |
| 3 | d24-misc-04 | static | 74 | 0 | M<=max(2, ceil(0.05*74))=4 | PASS | M=0 vs threshold=max(2, ceil(0.05*74))=4 |
| 3 | d28-mkt-05 | static | 100 | 0 | M<=max(2, ceil(0.05*100))=5 | PASS | M=0 vs threshold=max(2, ceil(0.05*100))=5 |
| 3 | d29-forum-05 | static | 200 | 0 | M<=max(2, ceil(0.05*200))=10 | PASS | M=0 vs threshold=max(2, ceil(0.05*200))=10 |
| 3 | d34-mkt-06 | static | 72 | 0 | M<=max(2, ceil(0.05*72))=4 | PASS | M=0 vs threshold=max(2, ceil(0.05*72))=4 |
| 3 | d36-misc-06 | static | 198 | 0 | M<=max(2, ceil(0.05*198))=10 | PASS | M=0 vs threshold=max(2, ceil(0.05*198))=10 |
| 3 | d38-news-07 | static | 188 | 0 | M<=max(2, ceil(0.05*188))=10 | PASS | M=0 vs threshold=max(2, ceil(0.05*188))=10 |
| 4 | d03-saas-01 | indeterminate | 7 | 0 | n/a | EXCLUDED | cluster label is indeterminate (ADR 0003) |
| 4 | d17-forum-03 | indeterminate | 7 | 0 | n/a | EXCLUDED | cluster label is indeterminate (ADR 0003) |
| 4 | d18-misc-03 | indeterminate | 2 | 0 | n/a | EXCLUDED | cluster label is indeterminate (ADR 0003) |
| 4 | d19-ecom-04 | indeterminate | 4 | 0 | n/a | EXCLUDED | cluster label is indeterminate (ADR 0003) |
| 4 | d20-news-04 | indeterminate | 1 | 0 | n/a | EXCLUDED | cluster label is indeterminate (ADR 0003) |
| 4 | d21-saas-04 | indeterminate | 7 | 0 | n/a | EXCLUDED | cluster label is indeterminate (ADR 0003) |
| 4 | d31-ecom-06 | indeterminate | 4 | 0 | n/a | EXCLUDED | cluster label is indeterminate (ADR 0003) |
| 4 | d40-mkt-07 | indeterminate | 6 | 0 | n/a | EXCLUDED | cluster label is indeterminate (ADR 0003) |

## Halt-rule assessment (BUILD.md §R3 L-09)

**No FAIL on evaluated clusters.** No halt, no scope-down.

Investigation proceeds per the Completeness verdict above.

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
