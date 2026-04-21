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
  lookup → hint generation → return LanternResult. Strict reading puts
  rescan (Methodology D) inside the classify() pipeline.

  §R2.1's default `timeout_ms=8000` budget is incompatible with full rescan
  (per L-08/L-09 evidence, rescan takes 30s-2min per URL even at K=10 poke
  cap). Either the default budget or the Part-4 flow is wrong for the
  production surface.

  L-11 resolves toward §R2.1's latency budget: `classify()` performs
  initial probe (Step 1) + grouping (Step 2) + library lookup (Step 6) +
  hint generation (Step 7). It does NOT perform poke selection (Step 3)
  or rescan (Steps 4-5) at classify() time. `state_transitions_summary`
  passed to the hint prompt is therefore an empty string.

  Effect on hints: prompts receive shape_id + shape_description +
  confidence + element_summary from the initial probe. The
  state-transition dimension LANTERN.md Part 4 Step 7 enumerates is
  omitted from the hint generator's inputs.

  L-09 Completeness PASS validated Methodology D's noise-floor behavior
  across clusters; rescan stays a research artifact active through
  L-12/L-14 for library enrichment and offline analysis, but does not
  run in the production classify() path.

  This trade-off is flagged in the L-14 audit checklist and in the
  commit body for contracts(L-11/public): freeze. A future ADR could
  enrich the library pre-shipment with per-cluster state_transitions
  summaries (derived from offline rescan on representative sites),
  which would let hints.py feed state-transition context to the prompt
  without per-call rescan latency. Not addressed in L-11 scope.

STUB — L-11 red. Implementation lands in green(L-11).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class LanternResult:
    """§R2.1 Sherpa-facing contract. Frozen dataclass."""
    shape_id: str
    confidence: float
    hints: list[str]
    fingerprint_hash: str
    elapsed_ms: int


def classify(
    url: str,
    session_state: Literal["fresh", "warm"] = "fresh",
    timeout_ms: int = 8000,
) -> LanternResult:
    """Classify the page at `url` and return a `LanternResult`.

    Per R2.1's frozen signature. `session_state` and `timeout_ms` semantics
    match LANTERN.md Part 5 Measurement Surface Freeze. `timeout_ms` is a
    budget hint; Playwright's internal timeouts drive actual cutoff
    behavior. If classify() exceeds `timeout_ms`, callers see a
    `TimeoutError` raised; Sherpa's R2.2 pattern is to soft-fallthrough to
    blind execution on any exception.
    """
    raise NotImplementedError("L-11 stub")
