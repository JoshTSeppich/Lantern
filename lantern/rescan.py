"""
lantern/rescan.py — Methodology D: three-pass state-change protocol.

Per LANTERN.md Part 3 Methodology D + Part 4 Step 4 + R0.2 (poke-selection
policy pinned as measurement surface):

  Pass 1 (Scan):   tab-traverse initial page → F₀ + candidate endpoints
  Pass 2 (Poke):   for each candidate, reload page, click candidate,
                   wait networkidle + settle_ms (cap 8s total), check URL
  Pass 3 (Rescan): if URL unchanged, tab-traverse again → F₁;
                   compute delta = F₁ \\ F₀ (added + removed tuples)
                   if URL changed, record as navigation endpoint, no rescan

Poke-selection policy (frozen at LANTERN.md Part 4 Step 3 + R0.2):
  (a) all elements with role 'button' inside 'main'
  (b) all elements with role 'link' inside 'nav' landmark (up to 10, tab order)
  (c) first element with role 'textbox' inside a form
  (d) any element with 'aria-haspopup' set
  Dedup by (role, accessible_name_hash, landmark).

Assumption documented: endpoints[i] and element_contexts[i] refer to the
same DOM element (tab-order aligned with DOM-order for pages without
positive tabindex). Holds on fixtures and most real-world sites;
positive-tabindex sites are an untested edge case — flag in L-09 report
if encountered.

STUB — L-08 red. Implementation lands in green(L-08).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from lantern.fingerprint import FingerprintTuple
from lantern.probe import ProbeConfig, ProbeResult


POKE_SETTLE_CAP_MS: int = 8000  # LANTERN.md Part 4 Step 4
MAX_NAV_LINKS_TO_POKE: int = 10  # LANTERN.md Part 4 Step 3 (b)


class PokeCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    landmark: str
    accessible_name: str | None
    tab_order_index: int
    dedup_key: str
    selection_reason: Literal[
        "button-in-main",
        "link-in-nav",
        "first-textbox-in-form",
        "aria-haspopup",
    ]


class PokeOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    candidate: PokeCandidate
    kind: Literal["navigation", "state_change", "no_change", "error"]
    destination_url: str | None = None
    pre_fingerprint_size: int
    post_fingerprint_size: int | None = None
    delta_added: list[FingerprintTuple] = Field(default_factory=list)
    delta_removed: list[FingerprintTuple] = Field(default_factory=list)
    elapsed_ms: int = 0
    error_message: str | None = None


class RescanTiming(BaseModel):
    model_config = ConfigDict(frozen=True)

    total_elapsed_ms: int
    initial_probe_ms: int
    poke_count: int
    poke_total_ms: int


class RescanResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    url: str
    config: ProbeConfig
    initial_probe: ProbeResult
    poke_candidates: list[PokeCandidate]
    outcomes: list[PokeOutcome]
    timing: RescanTiming

    def state_transition_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for o in self.outcomes:
            summary[o.kind] = summary.get(o.kind, 0) + 1
        return summary


def select_poke_endpoints(initial: ProbeResult) -> list[PokeCandidate]:
    raise NotImplementedError("L-08 stub")


def rescan(url: str, browser: Any, config: ProbeConfig | None = None) -> RescanResult:
    raise NotImplementedError("L-08 stub")
