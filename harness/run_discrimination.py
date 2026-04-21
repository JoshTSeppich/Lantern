"""
L-07 discrimination harness — 40 sites × 1 probe per site.

Per LANTERN.md Part 5 § Discrimination criterion, BUILD.md §R3 L-07, and
operator 2026-04-21 pre-registration rules:
  - 40-site pool pre-registered in sites_discrimination.yaml
  - 1 probe per site (no UA/session dimension)
  - Take first 30 ok in site-ID-sorted order (mechanical filter)
  - Halt if fewer than 25 survive (corpus insufficiency ADR)
  - 200-endpoint cap remains frozen (no mid-investigation tuning)
  - Desktop Chrome UA (matches LANTERN.md Part 5 Measurement Surface
    Freeze primary probe)

Output:
  data/fingerprints_discrimination/{site_id}.json — per-site probe artifact
  data/discrimination/run_{timestamp}.log — progress log

Usage:
  uv run python harness/run_discrimination.py

Resumable: existing per-site JSONs are skipped.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# `lantern` not pip-installed; see note in run_stability.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from playwright.sync_api import sync_playwright

from lantern.probe import DEFAULT_USER_AGENT, ProbeConfig, probe


HARNESS_DIR = Path(__file__).parent
REPO_ROOT = HARNESS_DIR.parent
DATA_ROOT = REPO_ROOT / "data"


def main() -> int:
    sites_path = HARNESS_DIR / "sites_discrimination.yaml"
    with sites_path.open() as f:
        sites_data = yaml.safe_load(f)
    sites = sites_data["sites"]

    fingerprints_dir = DATA_ROOT / "fingerprints_discrimination"
    log_dir = DATA_ROOT / "discrimination"
    fingerprints_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    log_file = log_dir / f"run_{timestamp}.log"

    def log(msg: str) -> None:
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        print(line, flush=True)
        with log_file.open("a") as lf:
            lf.write(line + "\n")

    log(
        f"L-07 discrimination run starting: {len(sites)} sites × 1 probe each = {len(sites)} probes"
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
                out_path = fingerprints_dir / f"{site_id}.json"

                if out_path.exists():
                    log(f"SKIP {site_id}")
                    total_done += 1
                    continue

                start_wall = time.monotonic()
                try:
                    result = probe(
                        url,
                        browser,
                        ProbeConfig(user_agent=DEFAULT_USER_AGENT, session_state="fresh"),
                    )
                    payload = {
                        "site_id": site_id,
                        "category": category,
                        "url": url,
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
                        f"OK   {site_id} fp_size={len(result.fingerprint)} "
                        f"elapsed={result.timing.total_elapsed_ms}ms "
                        f"({total_done + 1}/{len(sites)})"
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
                        f"FAIL {site_id} error={type(e).__name__} "
                        f"elapsed={elapsed}ms ({total_done + 1}/{len(sites)})"
                    )

                total_done += 1
        finally:
            browser.close()

    log(f"Discrimination run complete. ok={total_ok} fail={total_fail} total={total_done}/{len(sites)}")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
