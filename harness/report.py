"""
L-06 stability report — computes rubric metrics from data/fingerprints/.

OPERATIONALIZATION (pre-registered in this docstring before any probe runs):

  1. Metric: normalized Levenshtein distance (raw Levenshtein / max(|a|, |b|))
     on the static_fingerprint role-sequence tuples. Normalization is
     required because fingerprints across sites have different sizes and
     raw Levenshtein would be dominated by size difference rather than
     structural difference.

  2. Within-site pairs: all C(20, 2) = 190 ordered-unordered pairs per
     site, pooled across all 10 sites.

  3. Cross-site pairs: all pairs where the two probes are from different
     sites, pooled across all 10 sites.

  4. Within-site-p95 = 95th percentile of pooled within-site distances.
     Cross-site-p95 = 95th percentile of pooled cross-site distances.

  5. Verdict (per LANTERN.md Part 5 § Stability criterion):
        Pass      — within-site-p95 / cross-site-p95  <  0.20
        Soft Pass — within-site-p95 / cross-site-p95 in [0.20, 0.40)
        Fail      — within-site-p95 / cross-site-p95  ≥  0.40

  6. Percentile interpolation: linear (numpy-compatible "linear" method).
     For N values, k = (N-1) * (p/100); floor(k) and ceil(k) give the
     bracketing indices; return sv[f] + (sv[c] - sv[f]) * (k - f).

Pre-evidence commitment: this operationalization is frozen in this
docstring on the same commit as sites_stability.yaml (chore(L-06)). If a
later rerun would produce a different verdict under a different
operationalization, that is a finding, not a tuning opportunity.

Outputs:
  - Prints the scorecard to stdout.
  - Writes adrs/L-06-stability-report.md with the full report body.

Usage:
  uv run python harness/report.py
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

# `lantern` not pip-installed; see note in run_stability.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lantern.distance import levenshtein_normalized


HARNESS_DIR = Path(__file__).parent
REPO_ROOT = HARNESS_DIR.parent
FINGERPRINTS_DIR = REPO_ROOT / "data" / "fingerprints"
REPORT_PATH = REPO_ROOT / "adrs" / "L-06-stability-report.md"


def load_probes() -> list[dict]:
    probes: list[dict] = []
    if not FINGERPRINTS_DIR.exists():
        return probes
    for f in sorted(FINGERPRINTS_DIR.glob("*.json")):
        with f.open() as fp:
            data = json.load(fp)
        if data.get("status") == "ok":
            data["_fingerprint_tuples"] = [tuple(t) for t in data["fingerprint"]]
            probes.append(data)
    return probes


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    sv = sorted(values)
    if len(sv) == 1:
        return sv[0]
    k = (len(sv) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sv) - 1)
    if f == c:
        return sv[f]
    return sv[f] + (sv[c] - sv[f]) * (k - f)


def main() -> int:
    probes = load_probes()
    if not probes:
        print("No OK probes found in data/fingerprints/. Run run_stability.py first.")
        return 2

    # Load all probe data (including errors) for error accounting
    all_files = sorted(FINGERPRINTS_DIR.glob("*.json"))
    all_loaded = []
    for f in all_files:
        with f.open() as fp:
            all_loaded.append(json.load(fp))
    n_ok = sum(1 for d in all_loaded if d.get("status") == "ok")
    n_err = sum(1 for d in all_loaded if d.get("status") == "error")

    # Group ok probes by site
    by_site: dict[str, list[dict]] = {}
    for p in probes:
        by_site.setdefault(p["site_id"], []).append(p)

    # Within-site pairs
    within_per_site: dict[str, list[float]] = {}
    pooled_within: list[float] = []
    for site_id, site_probes in by_site.items():
        dists = [
            levenshtein_normalized(a["_fingerprint_tuples"], b["_fingerprint_tuples"])
            for a, b in combinations(site_probes, 2)
        ]
        within_per_site[site_id] = dists
        pooled_within.extend(dists)

    # Cross-site pairs
    pooled_cross: list[float] = []
    for a, b in combinations(probes, 2):
        if a["site_id"] == b["site_id"]:
            continue
        pooled_cross.append(
            levenshtein_normalized(a["_fingerprint_tuples"], b["_fingerprint_tuples"])
        )

    within_p95 = percentile(pooled_within, 95)
    cross_p95 = percentile(pooled_cross, 95)
    ratio = within_p95 / cross_p95 if cross_p95 and cross_p95 > 0 else float("nan")

    verdict: str
    if ratio != ratio:  # NaN
        verdict = "UNDETERMINED (cross-site p95 is zero or no cross-site pairs)"
    elif ratio < 0.20:
        verdict = "PASS"
    elif ratio < 0.40:
        verdict = "SOFT PASS"
    else:
        verdict = "FAIL"

    lines: list[str] = [
        "# L-06 Stability Report",
        "",
        f"**Verdict: {verdict}**",
        "",
        "## Probe accounting",
        "",
        f"- Probes recorded: {len(all_loaded)}",
        f"- Probes succeeded (status=ok): {n_ok}",
        f"- Probes failed (status=error): {n_err}",
        f"- Sites with at least one ok probe: {len(by_site)}",
        f"- Within-site ok-pairs: {len(pooled_within)}",
        f"- Cross-site ok-pairs: {len(pooled_cross)}",
        "",
        "## Pooled metrics (normalized Levenshtein)",
        "",
        f"- Within-site 95th percentile: {within_p95:.4f}",
        f"- Cross-site 95th percentile: {cross_p95:.4f}",
        f"- Ratio (within / cross) at 95p: {ratio:.4f}",
        "",
        "## Rubric (frozen in LANTERN.md Part 5 § Stability criterion)",
        "",
        "| Verdict | Ratio threshold |",
        "|---|---|",
        "| Pass | < 0.20 |",
        "| Soft Pass | 0.20 – 0.40 |",
        "| Fail | ≥ 0.40 |",
        "",
        "## Per-site within-site 95p",
        "",
        "| Site | Category | Ok probes | Pairs | Within-site 95p |",
        "|---|---|---:|---:|---:|",
    ]
    for site_id in sorted(by_site.keys()):
        probes_count = len(by_site[site_id])
        category = by_site[site_id][0]["category"]
        dists = within_per_site[site_id]
        p95 = percentile(dists, 95) if dists else float("nan")
        lines.append(
            f"| {site_id} | {category} | {probes_count} | {len(dists)} | {p95:.4f} |"
        )

    # Per-site failure breakdown
    errors_by_site: dict[str, list[dict]] = {}
    for d in all_loaded:
        if d.get("status") == "error":
            errors_by_site.setdefault(d["site_id"], []).append(d)
    if errors_by_site:
        lines.extend([
            "",
            "## Per-site failure breakdown",
            "",
            "| Site | Failed probes | Example error |",
            "|---|---:|---|",
        ])
        for site_id in sorted(errors_by_site.keys()):
            fails = errors_by_site[site_id]
            example = fails[0].get("error_type", "?")
            lines.append(f"| {site_id} | {len(fails)} | {example} |")

    report = "\n".join(lines) + "\n"
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report)

    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
