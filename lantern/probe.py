"""
lantern/probe.py — Playwright orchestration for Lantern probing.

Wires L-01 through L-04 together against a real Chromium browser. The
caller supplies a live `Browser` (from `playwright.sync_api`) and a URL;
`probe()` returns a `ProbeResult` containing:

  - raw AX tree (validated through `AXNode` pydantic models)
  - tab-ordered AX node IDs (collected via Playwright keyboard traversal)
  - dom_tags (backendDOMNodeId → HTML tag, from CDP `DOM.describeNode`)
  - element_contexts (grouping inputs, from `getComputedStyle` + DOM walk)
  - endpoints (via `endpoints.extract_endpoints`)
  - fingerprint (via `fingerprint.fingerprint`)
  - grouping (via `grouping.build_grouping_map`)
  - timing metrics

L-05 phase-transition claims (per operator directive 2026-04-20; see
test docstrings for test-site evidence):

  Claim 1 — Full-shape AX tree fidelity.
    KNOWN on tests/fixtures/probe/simple.html and deferred.html: CDP
    `Accessibility.getFullAXTree` returns nodes whose fields are either
    in `AXNode.model_fields` or in `KNOWN_EXTRA_FIELDS_ON_AX_NODE` (the
    documented set of CDP fields we don't parse but recognize).
    MODELED for real-world sites: not empirically verified across
    commercial pages; ADR + schema expansion required if L-06 stability
    harness discovers new CDP fields.
    UNKNOWN for rare Chromium builds / cross-frame content / custom
    element roles we haven't exercised.

  Claim 2 — Tab-order post-settling determinism.
    KNOWN on deferred.html after networkidle + 2000ms settle: tab order
    is deterministic across repeated probe runs and includes all
    setTimeout-inserted focusable elements that complete within the
    settle window.
    MODELED for pages whose async rendering exceeds settle_ms: we have
    not empirically measured what happens to elements inserted at
    t > 2000ms. They will be missed in the tab traversal by construction
    of the protocol — this is a probe-protocol limit, not a probe bug.
    UNKNOWN for pages with infinite requestAnimationFrame updates or
    ever-firing setInterval that never allows networkidle — L-SPIKE-04
    flagged this as the "in-transition" classification surface, not
    resolved here.

STUB — L-05 red. Implementation lands in green(L-05).
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from lantern.endpoints import AXNode, extract_endpoints
from lantern.fingerprint import FingerprintTuple, ProbeRecord, fingerprint
from lantern.grouping import ElementDOMContext, ElementGrouping, build_grouping_map


# -------------------------------------------------------------------------
# Measurement-surface defaults (Part 5 Measurement Surface Freeze)
# -------------------------------------------------------------------------

DEFAULT_USER_AGENT: str = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)
DEFAULT_VIEWPORT_WIDTH: int = 1440
DEFAULT_VIEWPORT_HEIGHT: int = 900
DEFAULT_TAB_DEPTH_CAP: int = 200
DEFAULT_SETTLE_MS: int = 2000

# CDP fields that appear on AX nodes and are intentionally not parsed by
# `lantern.endpoints.AXNode`. If CDP ships a field outside both this set
# and AXNode.model_fields, L-05 Claim 1 fails and an ADR + schema expansion
# is required (not silent coercion).
KNOWN_EXTRA_FIELDS_ON_AX_NODE: frozenset[str] = frozenset({
    "chromeRole",       # Chrome-specific internal role
    "description",      # AXValue — not used by fingerprint/grouping
    "value",            # AXValue — current form-control value
    "ignoredReasons",   # list of reasons for `ignored`
    "frameId",          # cross-frame marker
})


class ProbeConfig(BaseModel):
    """Frozen config for a single probe invocation."""

    model_config = ConfigDict(frozen=True)

    user_agent: str = DEFAULT_USER_AGENT
    viewport_width: int = DEFAULT_VIEWPORT_WIDTH
    viewport_height: int = DEFAULT_VIEWPORT_HEIGHT
    session_state: Literal["fresh", "warm"] = "fresh"
    tab_depth_cap: int = DEFAULT_TAB_DEPTH_CAP
    settle_ms: int = DEFAULT_SETTLE_MS


class ProbeTiming(BaseModel):
    """Wall-clock timings for a probe run, in milliseconds."""

    model_config = ConfigDict(frozen=True)

    total_elapsed_ms: int
    networkidle_wait_ms: int
    settle_wait_ms: int
    ax_tree_ms: int
    tab_traversal_ms: int


class ProbeResult(BaseModel):
    """Complete output of a probe run.

    Carries both the raw data (ax_tree, tab_order_ax_ids, dom_tags,
    element_contexts) and the composed pipeline output (endpoints,
    fingerprint, grouping). The raw data is retained so downstream
    consumers (L-06 stability harness, L-09 completeness harness) can
    reprocess without re-running the probe.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    url: str
    config: ProbeConfig
    timing: ProbeTiming
    ax_tree: list[AXNode]
    tab_order_ax_ids: list[str]
    dom_tags: dict[int, str]
    element_contexts: list[ElementDOMContext]
    endpoints: list[ProbeRecord]
    fingerprint: list[FingerprintTuple] = Field(default_factory=list)
    grouping: dict[str, ElementGrouping]

    def fingerprint_hash(self) -> str:
        """SHA-256 over the canonical fingerprint — the Part 4 Step 8 / §R2.1 hash."""
        canonical = [list(t) for t in self.fingerprint]
        return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


def probe(url: str, browser: Any, config: ProbeConfig | None = None) -> ProbeResult:
    """Run a full probe against `url` using `browser` (`playwright.sync_api.Browser`).

    Caller owns the browser lifetime; probe creates and closes a fresh
    context per invocation. session_state="fresh" (default) guarantees
    no cookies/localStorage across probes; "warm" reuses context state
    only within a single `probe()` call (Lantern is stateless across
    calls per §R2.3).
    """
    raise NotImplementedError("L-05 stub")
