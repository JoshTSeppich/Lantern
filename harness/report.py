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

OBSERVATION SECTIONS (pre-registered per operator 2026-04-20, while the
first harness run was in flight but BEFORE any data was inspected):

  O1. Per-site error rate — bot blocks, timeouts, cookie-consent failures
      bucketed by error_type per site. Counts only; does not influence
      verdict.

  O2. Per-site elapsed_ms distribution — min, median, max, p95 of
      timing.total_elapsed_ms for ok probes, per site. Sanity-checks
      whether settle_ms=2000 holds for SPA-heavy sites.

  O3. 200-endpoint cap saturation — which sites produced at least one
      probe with fingerprint_size == DEFAULT_TAB_DEPTH_CAP (200). A
      saturated probe indicates the tab-depth cap truncated the tab
      traversal before termination, which biases the fingerprint.

  O4. Session-state warm-vs-fresh sanity check — within-site mean
      distance stratified by pair type (fresh-fresh, warm-warm,
      fresh-warm). Given probe.py's known limitation (warm currently
      == fresh in implementation), expect these three means to be
      indistinguishable. If fresh-warm ≠ fresh-fresh materially, that's
      a surprise finding for post-L-06 investigation.

These four are observations, NOT rubric inputs. They land in the report
whatever the Pass/Soft-Pass/Fail verdict is.

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
from lantern.probe import DEFAULT_TAB_DEPTH_CAP


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

    # -----------------------------------------------------------------
    # Observation sections O1–O4 (pre-registered 2026-04-20; see docstring)
    # -----------------------------------------------------------------

    # O1 — Per-site error rate bucketed by error_type
    from collections import Counter
    errors_by_site: dict[str, list[dict]] = {}
    for d in all_loaded:
        if d.get("status") == "error":
            errors_by_site.setdefault(d["site_id"], []).append(d)
    ok_by_site: dict[str, int] = {}
    total_by_site: dict[str, int] = {}
    for d in all_loaded:
        sid = d.get("site_id", "?")
        total_by_site[sid] = total_by_site.get(sid, 0) + 1
        if d.get("status") == "ok":
            ok_by_site[sid] = ok_by_site.get(sid, 0) + 1

    lines.extend([
        "",
        "## O1 — Per-site error rate (pre-registered observation)",
        "",
        "| Site | Ok / Total | Error types |",
        "|---|---:|---|",
    ])
    for site_id in sorted(total_by_site.keys()):
        total = total_by_site[site_id]
        ok = ok_by_site.get(site_id, 0)
        err_types = Counter(e["error_type"] for e in errors_by_site.get(site_id, []))
        err_label = ", ".join(f"{k}×{v}" for k, v in err_types.most_common()) or "—"
        lines.append(f"| {site_id} | {ok}/{total} | {err_label} |")

    # O2 — Per-site elapsed_ms distribution (ok probes only)
    lines.extend([
        "",
        "## O2 — Per-site `timing.total_elapsed_ms` distribution (ok probes)",
        "",
        "Sanity-checks whether `settle_ms=2000` holds; SPA-heavy sites may push the tail. Units: milliseconds.",
        "",
        "| Site | n | min | median | p95 | max |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for site_id in sorted(by_site.keys()):
        elapsed = [p["timing"]["total_elapsed_ms"] for p in by_site[site_id]]
        if not elapsed:
            continue
        lines.append(
            f"| {site_id} | {len(elapsed)} | {min(elapsed)} | "
            f"{int(percentile(elapsed, 50))} | {int(percentile(elapsed, 95))} | {max(elapsed)} |"
        )

    # O3 — 200-endpoint cap saturation
    cap_saturated_sites: list[tuple[str, int, int]] = []
    for site_id, site_probes in by_site.items():
        sizes = [p["fingerprint_size"] for p in site_probes]
        saturated_count = sum(1 for s in sizes if s >= DEFAULT_TAB_DEPTH_CAP)
        if saturated_count > 0:
            cap_saturated_sites.append((site_id, saturated_count, len(site_probes)))

    lines.extend([
        "",
        f"## O3 — 200-endpoint cap saturation (DEFAULT_TAB_DEPTH_CAP={DEFAULT_TAB_DEPTH_CAP})",
        "",
    ])
    if cap_saturated_sites:
        lines.extend([
            "Sites where at least one probe hit the tab-depth cap. A capped probe truncated the traversal before body-return / already-seen; its fingerprint is biased (right-censored).",
            "",
            "| Site | Saturated probes | Total ok probes |",
            "|---|---:|---:|",
        ])
        for site_id, sat, tot in sorted(cap_saturated_sites):
            lines.append(f"| {site_id} | {sat} | {tot} |")
    else:
        lines.append("No probe hit the 200-endpoint cap. All traversals terminated naturally.")

    # O4 — Session-state warm-vs-fresh sanity check
    # For each site, compute mean within-site normalized Levenshtein
    # stratified by pair type.
    lines.extend([
        "",
        "## O4 — Session-state `warm` vs `fresh` sanity check",
        "",
        "Mean within-site normalized-Levenshtein, stratified by pair type. probe.py's known limitation (warm currently == fresh in implementation) predicts the three means to be indistinguishable. Material separation of fresh–warm from fresh–fresh and warm–warm would be a surprise finding.",
        "",
        "| Site | fresh–fresh (n) | warm–warm (n) | fresh–warm (n) |",
        "|---|---|---|---|",
    ])
    for site_id in sorted(by_site.keys()):
        site_probes = by_site[site_id]
        ff, ww, fw = [], [], []
        for a, b in combinations(site_probes, 2):
            d = levenshtein_normalized(a["_fingerprint_tuples"], b["_fingerprint_tuples"])
            a_s, b_s = a["session"], b["session"]
            if a_s == "fresh" and b_s == "fresh":
                ff.append(d)
            elif a_s == "warm" and b_s == "warm":
                ww.append(d)
            else:
                fw.append(d)

        def fmt(xs: list[float]) -> str:
            if not xs:
                return "— (0)"
            mean = sum(xs) / len(xs)
            return f"{mean:.4f} ({len(xs)})"

        lines.append(
            f"| {site_id} | {fmt(ff)} | {fmt(ww)} | {fmt(fw)} |"
        )

    # Category-boundary findings flagged at run-launch (operator 2026-04-20)
    lines.extend([
        "",
        "## Known findings (flagged pre-run, 2026-04-20)",
        "",
        "1. **saas-01 + saas-02 both are login pages** (Linear + Asana). Login form shapes are structurally near-identical regardless of underlying product: two inputs + submit button dominate the fingerprint. Cross-site-within-SaaS distance will be artificially low. Not a rubric problem (rubric pools cross-site across ALL different-site pairs, not per-category), but a shape-class boundary signal: if L-07 discrimination clusters SaaS logins with marketing-landing forms rather than as their own class, that is a substantive finding about what 'SaaS dashboard shape' means when the authenticated surface is out of scope per LANTERN.md Part 5.",
        "",
        "2. **Forum category has 1 site (HN), not 2.** No within-category cross-site comparison possible for forum; the uneven distribution documented in `sites_stability.yaml` acknowledges this. L-07's 5-sites-per-category design fills the gap.",
        "",
        "3. **probe.py `session_state='warm'` currently == `'fresh'`** (fresh BrowserContext per probe, no cross-probe cookie retention). Observation O4 above is the sanity check: three within-site pair-type means are expected indistinguishable.",
        "",
        "Cookie banners on EU-served responses, SPA routing-induced networkidle delay, and near-zero within-site variance on HN/Wikipedia were named as expected observations at run-launch (operator 2026-04-20). They land here as observations, never as rubric-relaxation evidence.",
    ])

    report = "\n".join(lines) + "\n"
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report)

    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
