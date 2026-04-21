"""
lantern/api.py — the public surface per LANTERN.md Part 6 / BUILD.md §R2.1.

  classify(url, session_state='fresh', timeout_ms=8000) -> LanternResult

`LanternResult` is the frozen dataclass Sherpa imports. All other types in
Lantern are pydantic for internal rigor, but the external contract uses
`@dataclass(frozen=True)` per §R2.1 to keep Sherpa's dependency surface
small (no pydantic import needed on Sherpa's side).

Scope decision for L-11 (documented as an investigation finding — flagged
for L-14 audit):

  LANTERN.md Part 4 Steps 0-8 describe the full probe flow: initial scan →
  grouping → poke selection → poke + rescan → shape assembly → library
  lookup → hint generation → return LanternResult. A strict reading puts
  rescan (Methodology D) inside the classify() pipeline.

  §R2.1's default `timeout_ms=8000` is incompatible with full rescan (per
  L-08/L-09 evidence, rescan takes 30s-2min per URL even at K=10 poke cap).

  L-11 resolves toward §R2.1's latency budget: `classify()` performs
  initial probe (Step 1) + grouping (Step 2 — performed by probe.py) +
  library lookup (Step 6) + hint generation (Step 7). It does NOT perform
  poke selection (Step 3) or rescan (Steps 4-5) at classify() time.
  `state_transitions_summary` passed to the hint prompt is therefore an
  empty string.

  L-09 Completeness PASS validated Methodology D's noise-floor behavior;
  rescan.py stays a research artifact active through L-12/L-14 (library
  enrichment, offline analysis) but does not run in the production
  classify() path. Flagged in contracts(L-11/public) commit body for
  L-14 audit.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from lantern import hints as hints_mod
from lantern.library import CONFIDENCE_THRESHOLD, Library, UNKNOWN_SHAPE_ID
from lantern.probe import ProbeConfig, probe


_DEFAULT_LIBRARY: Library | None = None


def _library() -> Library:
    """Lazy-load and memoize the default library."""
    global _DEFAULT_LIBRARY
    if _DEFAULT_LIBRARY is None:
        _DEFAULT_LIBRARY = Library.default()
    return _DEFAULT_LIBRARY


@dataclass(frozen=True)
class LanternResult:
    """§R2.1 Sherpa-facing contract. Frozen dataclass (NOT pydantic)."""
    shape_id: str
    confidence: float
    hints: list[str]
    fingerprint_hash: str
    elapsed_ms: int


def _summarize_elements(probe_result) -> str:
    """Terse text summary of the probe's initial fingerprint + names."""
    from collections import Counter
    fp = probe_result.fingerprint
    endpoints = probe_result.endpoints
    roles = Counter(t.role for t in fp)
    landmarks = Counter(t.landmark for t in fp)
    top_names = [ep.accessible_name for ep in endpoints if ep.accessible_name][:8]
    role_str = ", ".join(f"{r}×{c}" for r, c in roles.most_common())
    lm_str = ", ".join(f"{lm}×{c}" for lm, c in landmarks.most_common())
    names_str = "; ".join(top_names) if top_names else "(no accessible names)"
    return (
        f"{len(fp)} focusable elements; roles: {role_str}; "
        f"landmarks: {lm_str}; top names: {names_str}"
    )


def classify(
    url: str,
    session_state: Literal["fresh", "warm"] = "fresh",
    timeout_ms: int = 8000,
) -> LanternResult:
    """Classify the page at `url` and return a `LanternResult`.

    Pipeline: initial probe → library nearest-neighbor → hint generation
    (when confidence >= CONFIDENCE_THRESHOLD). Per L-11 scope (see module
    docstring), rescan (Methodology D) is NOT invoked in classify().

    `timeout_ms` is a budget hint. Playwright's internal timeouts drive
    actual cutoff behavior; classify() raises on any Playwright error or
    internal exception, and Sherpa's R2.2 pattern is to soft-fallthrough
    to blind execution.
    """
    start = time.monotonic()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            probe_result = probe(url, browser, ProbeConfig(session_state=session_state))
        finally:
            browser.close()

    # Library match (Methodology A)
    lib = _library()
    shape_id, confidence = lib.nearest(probe_result.fingerprint)

    # Hint generation (Part 4 Step 7) — only when above confidence threshold
    hints: list[str] = []
    if shape_id != UNKNOWN_SHAPE_ID and confidence >= CONFIDENCE_THRESHOLD:
        shape = lib.get_shape(shape_id)
        if shape is not None:
            shape_description = (
                f"majority category {shape.majority_category} "
                f"(size {shape.size}, majority ratio {shape.majority_ratio:.2f})"
            )
            element_summary = _summarize_elements(probe_result)
            # state_transitions_summary left empty per L-11 scope decision
            hints = hints_mod.generate_hints(
                shape_id=shape_id,
                shape_description=shape_description,
                confidence=confidence,
                element_summary=element_summary,
                state_transitions_summary="",
                task="",
            )

    elapsed_ms = int((time.monotonic() - start) * 1000)

    return LanternResult(
        shape_id=shape_id,
        confidence=confidence,
        hints=hints,
        fingerprint_hash=probe_result.fingerprint_hash(),
        elapsed_ms=elapsed_ms,
    )
