"""
L-09 completeness harness — rescan the 29 L-07 surviving sites with a K=10
per-site sampling cap per ADR 0005.

Per BUILD.md §R3 L-09, LANTERN.md Part 5 § Completeness criterion, and
ADR 0003 (cluster labels + aggregation) + ADR 0005 (K=10 harness cap).

The L-07 corpus is read from data/fingerprints_discrimination/*.json
(status=='ok' after first-30-ok mechanical filter at L-07). Each site's
URL is taken from its L-07 probe artifact. Each rescan:

  1. probe(url) — initial scan; gives F₀ and the full candidate list from
     select_poke_endpoints.
  2. Cap candidates to K=10 in the order select_poke_endpoints returns
     (policy priority a→b→c→d, tab_order_index within each).
  3. For each capped candidate: _execute_poke (reload → click → settle
     → rescan for F₁ → multiset delta).
  4. Persist per-site artifact to data/completeness_pairs/{site_id}.json
     with BOTH all_candidates_count (pre-cap) and selected_candidates_count
     (post-cap) for audit transparency per ADR 0005.

Output:
  data/completeness_pairs/{site_id}.json  — per-site rescan artifact
  data/completeness/run_{timestamp}.log   — progress log

Resumable: existing per-site JSONs are skipped.

Usage:
  uv run python harness/run_completeness.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# `lantern` not pip-installed; see note in run_stability.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright

from lantern.probe import DEFAULT_USER_AGENT, ProbeConfig, probe
from lantern.rescan import (
    PokeOutcome,
    RescanResult,
    RescanTiming,
    _execute_poke,
    select_poke_endpoints,
)


CANDIDATE_CAP: int = 10  # ADR 0005

HARNESS_DIR = Path(__file__).parent
REPO_ROOT = HARNESS_DIR.parent
DATA_ROOT = REPO_ROOT / "data"
L07_PROBES_DIR = DATA_ROOT / "fingerprints_discrimination"
OUTPUT_DIR = DATA_ROOT / "completeness_pairs"
LOG_DIR = DATA_ROOT / "completeness"


def _load_l07_corpus() -> list[dict]:
    """Return the 29-site L-07 corpus sorted by site_id (status=='ok' only)."""
    if not L07_PROBES_DIR.exists():
        raise RuntimeError(
            f"{L07_PROBES_DIR} missing. Re-run run_discrimination.py to regenerate."
        )
    probes: list[dict] = []
    for f in sorted(L07_PROBES_DIR.glob("*.json")):
        with f.open() as fp:
            d = json.load(fp)
        if d.get("status") == "ok":
            probes.append(d)
    probes.sort(key=lambda d: d["site_id"])
    return probes


def _rescan_with_cap(
    url: str,
    browser,
    config: ProbeConfig,
    cap: int,
) -> tuple[RescanResult, int]:
    """Rescan with a post-selection candidate cap.

    Returns (RescanResult, all_candidates_count_before_cap).
    """
    overall_start = time.monotonic()

    initial_start = time.monotonic()
    initial = probe(url, browser, config)
    initial_ms = int((time.monotonic() - initial_start) * 1000)

    all_candidates = select_poke_endpoints(initial)
    all_count = len(all_candidates)
    selected = all_candidates[:cap]

    poke_start = time.monotonic()
    outcomes: list[PokeOutcome] = []
    for candidate in selected:
        outcome = _execute_poke(url, candidate, list(initial.fingerprint), browser, config)
        outcomes.append(outcome)
    poke_ms = int((time.monotonic() - poke_start) * 1000)

    total_ms = int((time.monotonic() - overall_start) * 1000)

    result = RescanResult(
        url=url,
        config=config,
        initial_probe=initial,
        poke_candidates=selected,
        outcomes=outcomes,
        timing=RescanTiming(
            total_elapsed_ms=total_ms,
            initial_probe_ms=initial_ms,
            poke_count=len(selected),
            poke_total_ms=poke_ms,
        ),
    )
    return result, all_count


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    log_file = LOG_DIR / f"run_{timestamp}.log"

    def log(msg: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        print(line, flush=True)
        with log_file.open("a") as lf:
            lf.write(line + "\n")

    corpus = _load_l07_corpus()
    log(f"L-09 completeness run starting: {len(corpus)} sites (L-07 survivors), K={CANDIDATE_CAP}")

    total_done = 0
    total_ok = 0
    total_fail = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for site in corpus:
                site_id = site["site_id"]
                url = site["url"]
                category = site["category"]
                out_path = OUTPUT_DIR / f"{site_id}.json"

                if out_path.exists():
                    log(f"SKIP {site_id}")
                    total_done += 1
                    continue

                start_wall = time.monotonic()
                try:
                    config = ProbeConfig(user_agent=DEFAULT_USER_AGENT, session_state="fresh")
                    rescan_result, all_count = _rescan_with_cap(
                        url, browser, config, CANDIDATE_CAP
                    )

                    # Extract per-site metrics up front for the report's convenience
                    n = len(rescan_result.initial_probe.fingerprint)
                    m = sum(
                        len(o.delta_added)
                        for o in rescan_result.outcomes
                        if o.kind == "state_change"
                    )
                    outcome_summary = rescan_result.state_transition_summary()

                    payload = {
                        "site_id": site_id,
                        "category": category,
                        "url": url,
                        "status": "ok",
                        "all_candidates_count": all_count,
                        "selected_candidates_count": len(rescan_result.poke_candidates),
                        "initial_fingerprint_size": n,
                        "m_delta_sum": m,
                        "outcome_summary": outcome_summary,
                        "timing": rescan_result.timing.model_dump(),
                        "outcomes": [
                            {
                                "candidate_dedup_key": o.candidate.dedup_key,
                                "candidate_reason": o.candidate.selection_reason,
                                "candidate_role": o.candidate.role,
                                "candidate_landmark": o.candidate.landmark,
                                "candidate_name": o.candidate.accessible_name,
                                "candidate_tab_order_index": o.candidate.tab_order_index,
                                "kind": o.kind,
                                "destination_url": o.destination_url,
                                "pre_fingerprint_size": o.pre_fingerprint_size,
                                "post_fingerprint_size": o.post_fingerprint_size,
                                "delta_added_count": len(o.delta_added),
                                "delta_removed_count": len(o.delta_removed),
                                "delta_added": [list(t) for t in o.delta_added],
                                "delta_removed": [list(t) for t in o.delta_removed],
                                "elapsed_ms": o.elapsed_ms,
                                "error_message": o.error_message,
                            }
                            for o in rescan_result.outcomes
                        ],
                    }
                    out_path.write_text(json.dumps(payload, indent=2))
                    total_ok += 1
                    log(
                        f"OK   {site_id} all_cand={all_count} selected={len(rescan_result.poke_candidates)} "
                        f"N={n} M={m} summary={outcome_summary} "
                        f"elapsed={rescan_result.timing.total_elapsed_ms}ms "
                        f"({total_done + 1}/{len(corpus)})"
                    )
                except Exception as e:
                    elapsed = int((time.monotonic() - start_wall) * 1000)
                    payload = {
                        "site_id": site_id,
                        "category": category,
                        "url": url,
                        "status": "error",
                        "error_type": type(e).__name__,
                        "error_message": str(e)[:500],
                        "elapsed_before_failure_ms": elapsed,
                    }
                    out_path.write_text(json.dumps(payload, indent=2))
                    total_fail += 1
                    log(
                        f"FAIL {site_id} error={type(e).__name__} elapsed={elapsed}ms "
                        f"({total_done + 1}/{len(corpus)})"
                    )

                total_done += 1
        finally:
            browser.close()

    log(
        f"Completeness run complete. ok={total_ok} fail={total_fail} "
        f"total={total_done}/{len(corpus)}"
    )
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
