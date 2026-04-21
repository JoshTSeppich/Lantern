"""
L-09 completeness report — applies ADR 0003 (cluster labels + aggregation) +
ADR 0002 (static-class threshold) + ADR 0006 (N=0 → INDETERMINATE) to L-09
rescan evidence.

Pre-registered operationalization (pinned via ADR 0003 + ADR 0002 pre-evidence;
ADR 0006 added post-L-09-evidence as a rubric gap-fill, NOT tuning — see
adrs/0006-n-zero-indeterminate.md):

  Per-site metric:
    N = initial_fingerprint_size from L-07 probe
        (data/fingerprints_discrimination/{site_id}.json, `fingerprint_size`)
    M = sum(len(outcome.delta_added) for outcome in L-09 rescan
            if outcome.kind == 'state_change')
        (data/completeness_pairs/{site_id}.json, `m_delta_sum`)

  Per-site verdict (per ADR 0003 + ADR 0002 + ADR 0006):
    L-09 status != 'ok'   → FAIL (site errored at harness level)
    N == 0                → INDETERMINATE (un-probeable; ADR 0006)
    Dynamic cluster       → PASS iff M / N >= 0.25
    Static cluster        → PASS iff M <= max(2, ceil(0.05 * N))

  Per-cluster verdict (ADR 0003 part b, amended by ADR 0006 denominator):
    n_evaluable = n_pass + n_fail    (INDETERMINATE sites excluded)
    cluster_pass_rate = n_pass / n_evaluable
    Pass      — pass_rate >= 0.70
    Soft Pass — 0.50 <= pass_rate < 0.70
    Fail      — pass_rate < 0.50
    INDETERMINATE — n_evaluable == 0 (all members un-probeable; ADR 0006)

  Investigation-level Completeness verdict (over clusters that are neither
  ADR-0003-label-INDETERMINATE nor ADR-0006-cluster-INDETERMINATE):
    PASS      — n_pass      > n_evaluated/2
    SOFT PASS — n_pass_soft > n_evaluated/2 AND NOT PASS
    FAIL      — otherwise

  Halt rule (BUILD.md §R3 L-09):
    FAIL on dynamic clusters → scope-down (drop Methodology D).
    FAIL on static clusters only → finding, not scope-down.
    INDETERMINATE dynamic clusters do NOT trigger scope-down (per ADR 0006).
    Mixed → per-cluster breakdown.

Outputs:
  - Prints scorecard to stdout.
  - Writes adrs/L-09-completeness-report.md with full report body.

Usage:
  uv run python harness/report_completeness.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

# `lantern` not pip-installed; see note in run_stability.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


HARNESS_DIR = Path(__file__).parent
REPO_ROOT = HARNESS_DIR.parent
DATA_ROOT = REPO_ROOT / "data"
L07_PROBES_DIR = DATA_ROOT / "fingerprints_discrimination"
L07_LIBRARY_PATH = DATA_ROOT / "clusters" / "l07_library.json"
L09_PAIRS_DIR = DATA_ROOT / "completeness_pairs"
REPORT_PATH = REPO_ROOT / "adrs" / "L-09-completeness-report.md"


# ADR 0003 part (a) — cluster labels pinned pre-evidence
CLUSTER_LABELS: dict[int, str] = {
    0: "dynamic",         # Tesla Shop singleton — theory-grounded
    1: "static",          # dense-link-list — theory-grounded
    2: "dynamic",         # minimal-login — theory-grounded
    3: "static",          # marketing-catch-all — plurality-grounded
    4: "indeterminate",   # heterogeneous — EXCLUDED from verdict
}

# ADR 0003 part (b) + ADR 0002 thresholds
DYNAMIC_PASS_RATIO: float = 0.25   # M/N >= this for dynamic per-site pass
STATIC_FLOOR: int = 2              # ADR 0002: M <= max(2, ceil(0.05 * N))
STATIC_PCT: float = 0.05
CLUSTER_PASS_RATE_PASS: float = 0.70
CLUSTER_PASS_RATE_SOFT: float = 0.50


def static_threshold(n: int) -> int:
    """ADR 0002: M <= max(2, ceil(0.05 * N))."""
    return max(STATIC_FLOOR, math.ceil(STATIC_PCT * n))


def _load_l07_n_by_site() -> dict[str, int]:
    """Map site_id → N (L-07 fingerprint_size) from data/fingerprints_discrimination/."""
    n_by_site: dict[str, int] = {}
    for f in sorted(L07_PROBES_DIR.glob("*.json")):
        with f.open() as fp:
            d = json.load(fp)
        if d.get("status") == "ok":
            n_by_site[d["site_id"]] = d["fingerprint_size"]
    return n_by_site


def _load_library() -> list[dict]:
    with L07_LIBRARY_PATH.open() as f:
        return json.load(f)


def _load_l09_by_site() -> dict[str, dict]:
    l09: dict[str, dict] = {}
    for f in sorted(L09_PAIRS_DIR.glob("*.json")):
        with f.open() as fp:
            d = json.load(fp)
        l09[d["site_id"]] = d
    return l09


def _per_site_verdict(
    cluster_label: str, n: int, m: int, l09_status: str
) -> tuple[str, str]:
    """Return (verdict, reason) per ADR 0003 part (b) + ADR 0006.

    Verdict ∈ {'PASS', 'FAIL', 'INDETERMINATE'}.
    """
    if l09_status != "ok":
        return "FAIL", f"l09 status={l09_status}"
    if n == 0:
        return "INDETERMINATE", "N=0 un-probeable site (ADR 0006)"
    if cluster_label == "dynamic":
        ratio = m / n
        verdict = "PASS" if ratio >= DYNAMIC_PASS_RATIO else "FAIL"
        return verdict, f"M/N={ratio:.4f} vs threshold={DYNAMIC_PASS_RATIO}"
    if cluster_label == "static":
        threshold = static_threshold(n)
        verdict = "PASS" if m <= threshold else "FAIL"
        return verdict, f"M={m} vs threshold=max(2, ceil(0.05*{n}))={threshold}"
    if cluster_label == "indeterminate":
        # ADR 0003 Cluster 4 — no per-site verdict; cluster is excluded from aggregation
        return "EXCLUDED", "cluster label is indeterminate (ADR 0003)"
    return "FAIL", f"unexpected cluster label {cluster_label}"


def _cluster_verdict(pass_rate: float) -> str:
    if pass_rate >= CLUSTER_PASS_RATE_PASS:
        return "PASS"
    if pass_rate >= CLUSTER_PASS_RATE_SOFT:
        return "SOFT PASS"
    return "FAIL"


def main() -> int:
    if not L09_PAIRS_DIR.exists():
        print(f"Missing {L09_PAIRS_DIR}. Run run_completeness.py first.")
        return 2
    if not L07_LIBRARY_PATH.exists():
        print(f"Missing {L07_LIBRARY_PATH}. Re-run report_discrimination.py.")
        return 2

    library = _load_library()
    n_by_site = _load_l07_n_by_site()
    l09_by_site = _load_l09_by_site()

    if not l09_by_site:
        print("No L-09 rescan pairs found. Run run_completeness.py first.")
        return 2

    # -----------------------------------------------------------------
    # Per-cluster evaluation
    # -----------------------------------------------------------------

    cluster_results: list[dict] = []
    for cluster in library:
        cid = cluster["cluster_id"]
        members = cluster["member_site_ids"]
        label = CLUSTER_LABELS.get(cid, "?")

        per_site: list[dict] = []
        n_pass_sites = 0
        n_fail_sites = 0
        n_indeterminate_sites = 0

        for site_id in members:
            n = n_by_site.get(site_id)
            l09 = l09_by_site.get(site_id)
            if n is None or l09 is None:
                per_site.append({
                    "site_id": site_id,
                    "verdict": "FAIL",
                    "reason": "missing_data",
                    "N": n,
                    "M": None,
                    "l09_status": None,
                })
                n_fail_sites += 1
                continue
            m = l09.get("m_delta_sum", 0)
            l09_status = l09.get("status", "unknown")
            verdict, reason = _per_site_verdict(label, n, m, l09_status)
            per_site.append({
                "site_id": site_id,
                "verdict": verdict,
                "reason": reason,
                "N": n,
                "M": m,
                "l09_status": l09_status,
            })
            if verdict == "PASS":
                n_pass_sites += 1
            elif verdict == "FAIL":
                n_fail_sites += 1
            else:  # INDETERMINATE
                n_indeterminate_sites += 1

        # ADR 0006: denominator is n_evaluable (PASS + FAIL), not cluster_size
        n_evaluable = n_pass_sites + n_fail_sites
        if label == "indeterminate":
            verdict = "EXCLUDED"  # ADR 0003 Cluster 4
            pass_rate = 0.0
        elif n_evaluable == 0:
            verdict = "INDETERMINATE"  # ADR 0006 — all sites un-probeable
            pass_rate = 0.0
        else:
            pass_rate = n_pass_sites / n_evaluable
            verdict = _cluster_verdict(pass_rate)

        cluster_results.append({
            "cluster_id": cid,
            "label": label,
            "size": len(members),
            "n_pass": n_pass_sites,
            "n_fail": n_fail_sites,
            "n_indeterminate": n_indeterminate_sites,
            "n_evaluable": n_evaluable,
            "pass_rate": pass_rate,
            "verdict": verdict,
            "majority_category": cluster["majority_category"],
            "per_site": per_site,
        })

    # -----------------------------------------------------------------
    # Investigation-level verdict:
    #   - Exclude clusters with label 'indeterminate' (ADR 0003 Cluster 4)
    #   - Exclude clusters with verdict 'INDETERMINATE' (ADR 0006, all members un-probeable)
    # -----------------------------------------------------------------

    evaluated = [
        c for c in cluster_results
        if c["label"] != "indeterminate" and c["verdict"] != "INDETERMINATE"
    ]
    n_evaluated = len(evaluated)
    n_pass = sum(1 for c in evaluated if c["verdict"] == "PASS")
    n_pass_soft = sum(1 for c in evaluated if c["verdict"] in ("PASS", "SOFT PASS"))

    if n_pass > n_evaluated / 2:
        completeness_verdict = "PASS"
    elif n_pass_soft > n_evaluated / 2:
        completeness_verdict = "SOFT PASS"
    else:
        completeness_verdict = "FAIL"

    # Halt-rule diagnostics
    fail_dyn = [c for c in evaluated if c["label"] == "dynamic" and c["verdict"] == "FAIL"]
    fail_static = [c for c in evaluated if c["label"] == "static" and c["verdict"] == "FAIL"]
    scope_down_trigger = bool(fail_dyn)

    # -----------------------------------------------------------------
    # Assemble report
    # -----------------------------------------------------------------

    lines: list[str] = [
        "# L-09 Completeness Report",
        "",
        f"**Completeness verdict: {completeness_verdict}**",
        "",
        "## Scoring summary",
        "",
        f"- Evaluated clusters: {n_evaluated} of {len(cluster_results)} (Cluster 4 label INDETERMINATE per ADR 0003; additionally any cluster with all sites INDETERMINATE per ADR 0006 is excluded)",
        f"- Clusters at Pass: {n_pass}",
        f"- Clusters at Pass or Soft Pass: {n_pass_soft}",
        f"- Halt trigger (dynamic-cluster fail → scope-down Methodology D): {'YES' if scope_down_trigger else 'no'}",
        "",
        "## Per-cluster verdicts",
        "",
        "| cluster | label | size | n_pass | n_fail | n_indet | n_eval | pass_rate | verdict | majority category |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for c in cluster_results:
        pass_rate_cell = f"{c['pass_rate']:.4f}" if c["n_evaluable"] > 0 else "—"
        lines.append(
            f"| {c['cluster_id']} | {c['label']} | {c['size']} | {c['n_pass']} | "
            f"{c['n_fail']} | {c['n_indeterminate']} | {c['n_evaluable']} | "
            f"{pass_rate_cell} | {c['verdict']} | {c['majority_category']} |"
        )

    lines.extend([
        "",
        "## Rubric (ADR 0003 part (b) + ADR 0002)",
        "",
        "Per-site verdict:",
        "- Dynamic cluster: site passes iff `M / N >= 0.25` (R0.4 (i))",
        "- Static cluster:  site passes iff `M <= max(2, ceil(0.05 * N))` (ADR 0002)",
        "- L-09 error → per-site FAIL",
        "",
        "Per-cluster verdict:",
        "- Pass:      pass_rate >= 0.70",
        "- Soft Pass: 0.50 <= pass_rate < 0.70",
        "- Fail:      pass_rate < 0.50",
        "",
        "Investigation-level verdict (over evaluated clusters, Cluster 4 excluded):",
        "- PASS:      `n_pass > n_evaluated / 2`",
        "- SOFT PASS: `n_pass_soft > n_evaluated / 2 AND NOT PASS`",
        "- FAIL:      otherwise",
        "",
        "## Per-site detail",
        "",
        "| cluster | site_id | label | N | M | threshold | verdict | reason |",
        "|---:|---|---|---:|---:|---|---|---|",
    ])
    for c in cluster_results:
        for s in c["per_site"]:
            threshold_desc: str
            if c["label"] == "dynamic":
                threshold_desc = f"M/N>={DYNAMIC_PASS_RATIO}"
            elif c["label"] == "static" and s["N"] is not None:
                threshold_desc = f"M<=max(2, ceil(0.05*{s['N']}))={static_threshold(s['N'])}"
            else:
                threshold_desc = "n/a"
            lines.append(
                f"| {c['cluster_id']} | {s['site_id']} | {c['label']} | "
                f"{s['N']} | {s['M']} | {threshold_desc} | "
                f"{s['verdict']} | {s['reason']} |"
            )

    lines.extend([
        "",
        "## Halt-rule assessment (BUILD.md §R3 L-09)",
        "",
    ])
    if scope_down_trigger:
        lines.extend([
            "**Completeness FAIL on dynamic cluster(s) → SCOPE-DOWN TRIGGERED.**",
            "",
            f"Failed dynamic clusters: {[c['cluster_id'] for c in fail_dyn]}",
            "",
            "Per LANTERN.md Part 5 Investigation verdict mapping + BUILD.md §R3 L-09,",
            "Lantern scopes down to A+B+C only: Methodology D is dropped from the",
            "production pipeline. rescan.py remains committed as a research artifact;",
            "it does not ship with the classify() public surface.",
            "",
            "This is the architected scope-down branch that made L-SPIKE-04 acceptable",
            "at rank-2 behind L-SPIKE-02 (operator 2026-04-20). D was spike-first despite",
            "higher failure probability precisely because this exit is pre-registered.",
        ])
    elif fail_static:
        lines.extend([
            "**Static cluster FAIL(s) without dynamic-cluster FAIL.**",
            "",
            f"Failed static clusters: {[c['cluster_id'] for c in fail_static]}",
            "",
            "Per LANTERN.md Part 5 verdict mapping, static-cluster FAIL is a finding",
            "about Methodology D's noise floor on static content — NOT a scope-down",
            "trigger. D is retained; investigate the noise source separately.",
        ])
    else:
        lines.extend([
            "**No FAIL on evaluated clusters.** No halt, no scope-down.",
            "",
            "Investigation proceeds per the Completeness verdict above.",
        ])

    lines.extend([
        "",
        "## Cluster 4 observation (INDETERMINATE, excluded from verdict)",
        "",
        "Per ADR 0003 part (a), Cluster 4 is heterogeneous (saas plurality 25%;",
        "no meaningful majority). Forcing a dynamic/static label would be dishonest.",
        "Its per-site delta distribution is documented here for observation only —",
        "does NOT contribute to the Pass/Soft/Fail arithmetic above.",
        "",
        "| site_id | declared category | L-07 N | L-09 M | L-09 status |",
        "|---|---|---:|---:|---|",
    ])
    indeterminate_clusters = [c for c in cluster_results if c["label"] == "indeterminate"]
    for c in indeterminate_clusters:
        for s in c["per_site"]:
            # Look up category from L-09 data if available
            l09 = l09_by_site.get(s["site_id"], {})
            cat = l09.get("category", "?")
            lines.append(
                f"| {s['site_id']} | {cat} | {s['N']} | {s['M']} | {s['l09_status']} |"
            )

    report = "\n".join(lines) + "\n"
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report)
    print(report)

    if scope_down_trigger:
        return 3  # distinct exit: scope-down
    if completeness_verdict == "FAIL":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
