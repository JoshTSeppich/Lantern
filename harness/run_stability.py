"""
L-06 stability harness — 10 sites × 5 visits × 2 UA × 2 session-state = 200 probes.

Per LANTERN.md Part 5 § Stability criterion and BUILD.md §R3 L-06.

Pre-registration discipline:
  - harness/sites_stability.yaml MUST be committed before this script runs
    (see chore(L-06) commit). Script reads the site list; changes after
    evidence collection are rubric-drift events per §R4.
  - rubric is frozen in LANTERN.md Part 5 § Stability criterion:
    Pass <20%, Soft Pass 20-40%, Fail >40% within-site / cross-site at 95p.
  - metric: Levenshtein on the static_fingerprint role-sequence tuples.
    Normalized by max(len_a, len_b) to produce a [0,1] value comparable
    across fingerprint sizes — see `report.py` for full operationalization.

Known probe.py limitation acknowledged in sites_stability.yaml:
  session_state='warm' currently behaves equivalently to 'fresh' (each
  probe() creates a fresh BrowserContext). The 2-session-state dimension
  is therefore a duplicate axis in this run; the 200-probe count is
  preserved so the pooled distance statistics have adequate sample size.

Output:
  data/fingerprints/{cell_id}.json  — per-probe raw artifact (status=ok or error)
  data/stability/run_{timestamp}.log — progress log

Usage:
  uv run python harness/run_stability.py

Resumable: per-cell JSON files that already exist are skipped, enabling
safe resume after a crash or interrupt.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# `lantern` is not pip-installed (pyproject has [tool.uv] package=false); pytest
# picks it up via `pythonpath=['.']` but direct `uv run python` does not. Prepend
# the repo root so `from lantern...` resolves.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from playwright.sync_api import sync_playwright

from lantern.probe import ProbeConfig, probe


USER_AGENTS: dict[str, str] = {
    "desktop-chrome-mac": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    ),
    "mobile-safari-ios": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
}

SESSION_STATES: list[str] = ["fresh", "warm"]
VISITS_PER_CELL: int = 5

HARNESS_DIR = Path(__file__).parent
REPO_ROOT = HARNESS_DIR.parent
DATA_ROOT = REPO_ROOT / "data"


def main() -> int:
    sites_path = HARNESS_DIR / "sites_stability.yaml"
    with sites_path.open() as f:
        sites_data = yaml.safe_load(f)
    sites = sites_data["sites"]

    fingerprints_dir = DATA_ROOT / "fingerprints"
    log_dir = DATA_ROOT / "stability"
    fingerprints_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    log_file = log_dir / f"run_{timestamp}.log"

    def log(msg: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        print(line, flush=True)
        with log_file.open("a") as lf:
            lf.write(line + "\n")

    total_target = len(sites) * VISITS_PER_CELL * len(USER_AGENTS) * len(SESSION_STATES)
    log(
        f"L-06 stability run starting: {len(sites)} sites × {VISITS_PER_CELL} visits × "
        f"{len(USER_AGENTS)} UA × {len(SESSION_STATES)} session = {total_target} probes"
    )

    total_done = 0
    total_ok = 0
    total_fail = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for site in sites:
                site_id = site["id"]
                url = site["url"]
                category = site["category"]

                for ua_key, ua_str in USER_AGENTS.items():
                    for session in SESSION_STATES:
                        for visit in range(1, VISITS_PER_CELL + 1):
                            cell_id = (
                                f"{site_id}__ua-{ua_key}__session-{session}__v{visit}"
                            )
                            out_path = fingerprints_dir / f"{cell_id}.json"

                            if out_path.exists():
                                log(f"SKIP {cell_id}")
                                total_done += 1
                                continue

                            start_wall = time.monotonic()
                            try:
                                result = probe(
                                    url,
                                    browser,
                                    ProbeConfig(user_agent=ua_str, session_state=session),
                                )
                                payload = {
                                    "cell_id": cell_id,
                                    "site_id": site_id,
                                    "category": category,
                                    "url": url,
                                    "ua": ua_key,
                                    "session": session,
                                    "visit": visit,
                                    "status": "ok",
                                    "fingerprint": [list(t) for t in result.fingerprint],
                                    "fingerprint_hash": result.fingerprint_hash(),
                                    "fingerprint_size": len(result.fingerprint),
                                    "element_context_count": len(result.element_contexts),
                                    "timing": result.timing.model_dump(),
                                }
                                out_path.write_text(json.dumps(payload, indent=2))
                                total_ok += 1
                                log(
                                    f"OK   {cell_id} fp_size={len(result.fingerprint)} "
                                    f"elapsed={result.timing.total_elapsed_ms}ms "
                                    f"({total_done + 1}/{total_target})"
                                )
                            except Exception as e:
                                elapsed = int((time.monotonic() - start_wall) * 1000)
                                payload = {
                                    "cell_id": cell_id,
                                    "site_id": site_id,
                                    "category": category,
                                    "url": url,
                                    "ua": ua_key,
                                    "session": session,
                                    "visit": visit,
                                    "status": "error",
                                    "error_type": type(e).__name__,
                                    "error_message": str(e)[:500],
                                    "elapsed_before_failure_ms": elapsed,
                                }
                                out_path.write_text(json.dumps(payload, indent=2))
                                total_fail += 1
                                log(
                                    f"FAIL {cell_id} error={type(e).__name__} "
                                    f"elapsed={elapsed}ms ({total_done + 1}/{total_target})"
                                )

                            total_done += 1
        finally:
            browser.close()

    log(
        f"Stability run complete. ok={total_ok} fail={total_fail} "
        f"total={total_done}/{total_target}"
    )
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
