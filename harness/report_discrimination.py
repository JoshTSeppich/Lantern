"""
L-07 discrimination report — clustering + rubric evaluation.

PRE-REGISTERED OPERATIONALIZATION (committed pre-evidence in this docstring,
per operator 2026-04-21 directive "Clustering algorithm, linkage method,
distance threshold selection — all pinned pre-evidence in report.py
docstring"):

  1. Mechanical filter: load all probes from data/fingerprints_discrimination/,
     sort by site_id ascending, take first 30 with status=='ok'. If fewer than
     25 survive, halt and print corpus-insufficiency signal (no clustering,
     no verdict — ADR required).

  2. Distance metric: normalized Levenshtein distance on static_fingerprint
     role-sequence tuples (per `lantern.distance.levenshtein_normalized`).
     Matches the A+B+C static-fingerprint-only clustering constraint from
     R0.3 (Methodology D output excluded — anti-circularity).

  3. Clustering algorithm: hierarchical agglomerative with average (UPGMA)
     linkage. Implemented in-module (no scipy/sklearn dep) — O(N^3) for
     N≤30 is negligible. Returns full merge history.

  4. Cluster-count selection: silhouette-based. Enumerate k ∈ {2, 3, ..., 12}.
     For each k, cut dendrogram at k clusters and compute mean silhouette
     score. Pick k_optimal = argmax over the range. If tie, prefer smaller k.
     Range [2, 12] brackets the rubric's Pass (4-8) and Soft Pass (3 or 9-12)
     bands symmetrically plus 2 as a sanity-lower-bound.

  5. Category majority: for each cluster, `majority = max_category_count /
     cluster_size`. Report: min, mean, max across clusters. Rubric reads
     "category-majority >70%" as mean across clusters (operationalization
     pinned here; alternative readings — min across clusters, weighted mean
     by cluster size — produce different thresholds but are not the chosen
     interpretation).

  6. Verdict:
       Pass      — 4 ≤ k_optimal ≤ 8 AND mean_category_majority > 0.70
       Soft Pass — k_optimal ∈ {3, 9, 10, 11, 12}
                   AND 0.50 < mean_category_majority ≤ 0.70,
                   OR one dimension Pass-level and the other Soft-level
       Fail      — k_optimal < 3 or > 12,
                   OR mean_category_majority ≤ 0.50

  7. Silhouette implementation: for each point i with own-cluster A,
        a(i) = mean distance to other points in A
        b(i) = min over other clusters B of mean distance from i to B
        s(i) = (b(i) - a(i)) / max(a(i), b(i))
      Overall score = mean s(i). Singleton clusters have s(i) = 0 by
      convention (no in-cluster structure).

Any later rerun producing a different verdict under different
hyperparameters (different linkage, non-silhouette k selection, expanded k
range, or alternative majority reading) is a finding, not a tuning
opportunity. The pin here is binding.

Outputs:
  - Prints scorecard to stdout.
  - Writes adrs/L-07-discrimination-report.md with the full report body.
  - Writes data/clusters/l07_library.json with the bootstrapped shape
    library (one shape per cluster, with member site_ids + representative
    fingerprint). data/ is gitignored per §R1.1 — the library is
    regeneratable; the report is the committed audit trail.

Usage:
  uv run python harness/report_discrimination.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

# `lantern` not pip-installed; see note in run_stability.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lantern.distance import levenshtein_normalized


HARNESS_DIR = Path(__file__).parent
REPO_ROOT = HARNESS_DIR.parent
FINGERPRINTS_DIR = REPO_ROOT / "data" / "fingerprints_discrimination"
CLUSTERS_DIR = REPO_ROOT / "data" / "clusters"
REPORT_PATH = REPO_ROOT / "adrs" / "L-07-discrimination-report.md"


K_RANGE = range(2, 13)  # inclusive 2..12


# ---------------------------------------------------------------------
# Clustering primitives (no scipy/sklearn dep)
# ---------------------------------------------------------------------

def distance_matrix(fingerprints: list[list[tuple]]) -> list[list[float]]:
    n = len(fingerprints)
    mat = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = levenshtein_normalized(fingerprints[i], fingerprints[j])
            mat[i][j] = d
            mat[j][i] = d
    return mat


def agglomerative_average_linkage(
    distances: list[list[float]],
) -> list[tuple[tuple[int, ...], tuple[int, ...], float]]:
    """Average-linkage hierarchical clustering. Returns merge history
    (cluster_a_members_tuple, cluster_b_members_tuple, distance_at_merge)."""
    n = len(distances)
    clusters: list[tuple[int, ...]] = [(i,) for i in range(n)]
    merges: list[tuple[tuple[int, ...], tuple[int, ...], float]] = []

    while len(clusters) > 1:
        best = (float("inf"), -1, -1)
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                total = 0.0
                for a in clusters[i]:
                    for b in clusters[j]:
                        total += distances[a][b]
                d = total / (len(clusters[i]) * len(clusters[j]))
                if d < best[0]:
                    best = (d, i, j)
        d, i, j = best
        merged = tuple(sorted(clusters[i] + clusters[j]))
        merges.append((clusters[i], clusters[j], d))
        new_clusters = [c for k, c in enumerate(clusters) if k not in (i, j)]
        new_clusters.append(merged)
        clusters = new_clusters

    return merges


def cut_to_k(
    merges: list[tuple[tuple[int, ...], tuple[int, ...], float]],
    n: int,
    k: int,
) -> list[tuple[int, ...]]:
    """Reconstruct cluster assignment at exactly k clusters by replaying
    (n - k) merges in order."""
    if k <= 0 or k > n:
        raise ValueError(f"k={k} out of range [1, {n}]")
    clusters: list[tuple[int, ...]] = [(i,) for i in range(n)]
    steps = n - k
    for idx in range(steps):
        a, b, _ = merges[idx]
        ia = next(i for i, c in enumerate(clusters) if c == a)
        ib = next(i for i, c in enumerate(clusters) if c == b)
        merged = tuple(sorted(clusters[ia] + clusters[ib]))
        clusters = [c for _i, c in enumerate(clusters) if _i not in (ia, ib)]
        clusters.append(merged)
    return clusters


def clusters_to_assignment(clusters: list[tuple[int, ...]], n: int) -> list[int]:
    """Convert cluster membership list to per-point cluster-index assignment."""
    assignment = [0] * n
    for cid, members in enumerate(clusters):
        for m in members:
            assignment[m] = cid
    return assignment


def silhouette_score(
    distances: list[list[float]],
    assignment: list[int],
) -> float:
    n = len(distances)
    clusters_by_id: dict[int, list[int]] = {}
    for i, cid in enumerate(assignment):
        clusters_by_id.setdefault(cid, []).append(i)
    if len(clusters_by_id) < 2:
        return 0.0

    s_values: list[float] = []
    for i in range(n):
        own = assignment[i]
        own_members = [j for j in clusters_by_id[own] if j != i]
        if not own_members:
            s_values.append(0.0)
            continue
        a_i = sum(distances[i][j] for j in own_members) / len(own_members)
        b_i = float("inf")
        for other_cid, other_members in clusters_by_id.items():
            if other_cid == own:
                continue
            mean_other = sum(distances[i][j] for j in other_members) / len(other_members)
            if mean_other < b_i:
                b_i = mean_other
        if b_i == float("inf"):
            s_values.append(0.0)
        else:
            denom = max(a_i, b_i)
            s_values.append((b_i - a_i) / denom if denom > 0 else 0.0)
    return sum(s_values) / n


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> int:
    if not FINGERPRINTS_DIR.exists():
        print(f"Missing {FINGERPRINTS_DIR}. Run run_discrimination.py first.")
        return 2

    all_files = sorted(FINGERPRINTS_DIR.glob("*.json"))
    all_loaded: list[dict] = []
    for f in all_files:
        with f.open() as fp:
            all_loaded.append(json.load(fp))

    # Mechanical filter per operator 2026-04-21: first 30 ok, site-ID sorted
    ok_probes = sorted(
        [d for d in all_loaded if d.get("status") == "ok"],
        key=lambda d: d["site_id"],
    )
    survivors = ok_probes[:30]

    n_total = len(all_loaded)
    n_ok = len(ok_probes)
    n_err = sum(1 for d in all_loaded if d.get("status") == "error")
    n_in_corpus = len(survivors)

    # Halt path: <25 survivors → corpus insufficiency
    corpus_insufficient = n_in_corpus < 25

    # -------------------------------------------------------------
    # Prepare report
    # -------------------------------------------------------------
    lines: list[str] = ["# L-07 Discrimination Report", ""]

    if corpus_insufficient:
        lines.extend([
            "**Verdict: HALT — corpus insufficiency**",
            "",
            f"- Probes attempted: {n_total}",
            f"- Probes ok: {n_ok}",
            f"- Probes failed: {n_err}",
            f"- Corpus after mechanical first-30-ok filter: {n_in_corpus}",
            "",
            f"Per operator 2026-04-21 rule: if fewer than 25 survive, halt "
            f"before clustering. Author an ADR on corpus insufficiency.",
            "",
            "The thesis does not get a retry on corpus. This is a halt.",
            "",
        ])
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text("\n".join(lines) + "\n")
        print("\n".join(lines))
        return 3  # distinct exit code for corpus-insufficient halt

    # Extract fingerprint sequences
    site_ids = [p["site_id"] for p in survivors]
    categories = [p["category"] for p in survivors]
    fingerprints = [[tuple(t) for t in p["fingerprint"]] for p in survivors]

    # Compute distance matrix and cluster
    dmat = distance_matrix(fingerprints)
    merges = agglomerative_average_linkage(dmat)

    # Enumerate k ∈ [2, 12], compute silhouette, pick k_optimal
    k_scores: dict[int, float] = {}
    assignments_by_k: dict[int, list[int]] = {}
    for k in K_RANGE:
        if k > len(survivors):
            continue
        clusters_k = cut_to_k(merges, len(survivors), k)
        assignment = clusters_to_assignment(clusters_k, len(survivors))
        score = silhouette_score(dmat, assignment)
        k_scores[k] = score
        assignments_by_k[k] = assignment

    k_optimal = max(k_scores, key=lambda k: (k_scores[k], -k))  # argmax score, tiebreak smaller k
    optimal_assignment = assignments_by_k[k_optimal]

    # Cluster composition + category majority
    optimal_clusters: dict[int, list[int]] = {}
    for i, cid in enumerate(optimal_assignment):
        optimal_clusters.setdefault(cid, []).append(i)

    cluster_majority: dict[int, float] = {}
    cluster_majority_category: dict[int, str] = {}
    for cid, members in optimal_clusters.items():
        cats = [categories[m] for m in members]
        top_cat, top_count = Counter(cats).most_common(1)[0]
        cluster_majority[cid] = top_count / len(members)
        cluster_majority_category[cid] = top_cat

    mean_majority = sum(cluster_majority.values()) / len(cluster_majority)
    min_majority = min(cluster_majority.values())
    max_majority = max(cluster_majority.values())

    # Verdict per rubric
    k_in_pass = 4 <= k_optimal <= 8
    k_in_soft = k_optimal == 3 or 9 <= k_optimal <= 12
    majority_pass = mean_majority > 0.70
    majority_soft = 0.50 < mean_majority <= 0.70

    if k_in_pass and majority_pass:
        verdict = "PASS"
    elif (k_in_pass or k_in_soft) and (majority_pass or majority_soft):
        verdict = "SOFT PASS"
    else:
        verdict = "FAIL"

    # Assemble report
    lines.extend([
        f"**Verdict: {verdict}**",
        "",
        "## Corpus accounting",
        "",
        f"- Probes attempted: {n_total}",
        f"- Probes ok: {n_ok}",
        f"- Probes failed: {n_err}",
        f"- Corpus (first-30-ok mechanical filter): {n_in_corpus}",
        "",
        "## Silhouette-based cluster-count selection",
        "",
        "| k | silhouette |",
        "|---:|---:|",
    ])
    for k in sorted(k_scores.keys()):
        marker = " ← k_optimal" if k == k_optimal else ""
        lines.append(f"| {k} | {k_scores[k]:.4f}{marker} |")

    lines.extend([
        "",
        f"**k_optimal = {k_optimal}** (argmax silhouette; tiebreak = smaller k)",
        "",
        "## Cluster composition at k_optimal",
        "",
        f"- Clusters: {len(optimal_clusters)}",
        f"- Mean category majority: {mean_majority:.4f}",
        f"- Min category majority:  {min_majority:.4f}",
        f"- Max category majority:  {max_majority:.4f}",
        "",
        "| cluster | size | majority category | majority | members |",
        "|---:|---:|---|---:|---|",
    ])
    for cid in sorted(optimal_clusters.keys()):
        members = optimal_clusters[cid]
        member_ids = ", ".join(site_ids[m] for m in sorted(members))
        lines.append(
            f"| {cid} | {len(members)} | {cluster_majority_category[cid]} | "
            f"{cluster_majority[cid]:.4f} | {member_ids} |"
        )

    lines.extend([
        "",
        "## Rubric (frozen in LANTERN.md Part 5 § Discrimination criterion)",
        "",
        "| Verdict | k | category-majority (mean) |",
        "|---|---|---|",
        "| Pass | 4–8 | > 0.70 |",
        "| Soft Pass | 3 or 9–12 | 0.50 – 0.70 |",
        "| Fail | 1–2 or > 12 | ≤ 0.50 |",
        "",
        "## Per-site category and cluster assignment",
        "",
        "| site_id | declared category | cluster | cluster majority category |",
        "|---|---|---:|---|",
    ])
    for i in sorted(range(len(survivors)), key=lambda i: site_ids[i]):
        lines.append(
            f"| {site_ids[i]} | {categories[i]} | {optimal_assignment[i]} | "
            f"{cluster_majority_category[optimal_assignment[i]]} |"
        )

    # L-06 context findings per operator 2026-04-21
    lines.extend([
        "",
        "## L-06 context inherited (operator 2026-04-21)",
        "",
        "Two L-06 findings reframe the L-07 read-out:",
        "",
        "- **Probe success at L-06 was binary** (6/10 clean ok, 4/10 total fail; zero intermediate). Failure mode is deterministic, not stochastic — the first-30-ok mechanical filter is correct because retries would not help. If L-07 shows a similar binary distribution, the 40-site over-provision pattern (7/7/7/7/6/6) is the right corpus-robustness strategy.",
        "- **Five of six L-06-surviving sites had perfect within-site stability.** The L-06 Soft-Pass verdict (ratio 0.3719) was driven entirely by Wikipedia. On sites where the probe protocol works at all, within-site determinism is near-perfect — the methodology is stronger than the L-06 Soft-Pass headline suggests. L-07's discrimination test sits on top of that within-site-determinism floor.",
        "",
        "## Library bootstrap",
        "",
        "Per R0.1, the library does not exist prior to the discrimination test; it is the output of the discrimination test. One shape per cluster, written to data/clusters/l07_library.json (gitignored per §R1.1; regeneratable). Each shape records its cluster_id, member site_ids, majority category, and a representative fingerprint (the member whose mean-distance-to-other-members is lowest).",
    ])

    report_text = "\n".join(lines) + "\n"
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_text)

    # Library bootstrap
    CLUSTERS_DIR.mkdir(parents=True, exist_ok=True)
    library = []
    for cid in sorted(optimal_clusters.keys()):
        members = optimal_clusters[cid]
        # Pick representative: member with lowest mean distance to other members
        if len(members) == 1:
            rep_idx = members[0]
        else:
            best_rep = members[0]
            best_mean = float("inf")
            for m in members:
                others = [o for o in members if o != m]
                mean_d = sum(dmat[m][o] for o in others) / len(others)
                if mean_d < best_mean:
                    best_mean = mean_d
                    best_rep = m
            rep_idx = best_rep
        library.append({
            "cluster_id": cid,
            "size": len(members),
            "majority_category": cluster_majority_category[cid],
            "majority_ratio": cluster_majority[cid],
            "member_site_ids": sorted([site_ids[m] for m in members]),
            "representative_site_id": site_ids[rep_idx],
            "representative_fingerprint": [list(t) for t in fingerprints[rep_idx]],
        })
    (CLUSTERS_DIR / "l07_library.json").write_text(json.dumps(library, indent=2))

    print(report_text)
    return 0 if verdict != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
