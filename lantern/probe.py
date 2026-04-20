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

KNOWN_EXTRA_FIELDS_ON_AX_NODE: frozenset[str] = frozenset({
    "chromeRole",
    "description",
    "value",
    "ignoredReasons",
    "frameId",
})


class ProbeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    user_agent: str = DEFAULT_USER_AGENT
    viewport_width: int = DEFAULT_VIEWPORT_WIDTH
    viewport_height: int = DEFAULT_VIEWPORT_HEIGHT
    session_state: Literal["fresh", "warm"] = "fresh"
    tab_depth_cap: int = DEFAULT_TAB_DEPTH_CAP
    settle_ms: int = DEFAULT_SETTLE_MS


class ProbeTiming(BaseModel):
    model_config = ConfigDict(frozen=True)
    total_elapsed_ms: int
    networkidle_wait_ms: int
    settle_wait_ms: int
    ax_tree_ms: int
    tab_traversal_ms: int


class ProbeResult(BaseModel):
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
        canonical = [list(t) for t in self.fingerprint]
        return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()


# -------------------------------------------------------------------------
# Internal JS — injected via page.evaluate at different probe phases
# -------------------------------------------------------------------------

_SETUP_TAB_TRACE_JS = """
() => {
    window.__probeMarkers = new Set();
    window.__probeTrace = [];
    window.__tabStatus = 'running';

    window.__markAndRecord = () => {
        const el = document.activeElement;
        if (!el || el === document.body || el === document.documentElement) {
            window.__tabStatus = 'body_return';
            return;
        }
        let marker = el.getAttribute('data-probe-marker');
        if (marker !== null && window.__probeMarkers.has(marker)) {
            window.__tabStatus = 'already_seen';
            return;
        }
        if (marker === null) {
            marker = 'pm-' + window.__probeTrace.length;
            el.setAttribute('data-probe-marker', marker);
        }
        window.__probeMarkers.add(marker);
        window.__probeTrace.push({
            marker: marker,
            tag: el.tagName.toLowerCase(),
            id: el.id || null,
        });
    };
    document.body.focus();
}
"""

_COLLECT_CONTEXTS_JS = """
() => {
    const markers = Array.from(document.querySelectorAll('[data-probe-marker]'));
    const layoutCounter = new Map();
    let nextLayoutId = 0;
    const formCounter = new Map();
    let nextFormId = 0;

    const getLayoutGroupId = (el) => {
        let a = el.parentElement;
        while (a) {
            const cs = window.getComputedStyle(a);
            if (cs.display === 'grid' || cs.display === 'flex' ||
                cs.display === 'inline-grid' || cs.display === 'inline-flex') {
                if (!layoutCounter.has(a)) {
                    layoutCounter.set(a, 'layout-' + nextLayoutId++);
                }
                return layoutCounter.get(a);
            }
            a = a.parentElement;
        }
        return null;
    };

    const getFormAncestorId = (el) => {
        let a = el.parentElement;
        while (a) {
            if (a.tagName === 'FORM') {
                if (!formCounter.has(a)) {
                    formCounter.set(a, a.id || 'form-auto-' + nextFormId++);
                }
                return formCounter.get(a);
            }
            a = a.parentElement;
        }
        return null;
    };

    const getAttrs = (el) => {
        const attrs = {};
        for (const a of el.attributes) {
            if (a.name === 'data-probe-marker') continue;
            if (a.name.startsWith('aria-') || a.name.startsWith('data-')) {
                attrs[a.name] = a.value;
            }
        }
        return attrs;
    };

    return markers.map(el => ({
        element_id: el.id || el.getAttribute('data-probe-marker'),
        aria_attributes: getAttrs(el),
        form_ancestor_id: getFormAncestorId(el),
        layout_group_id: getLayoutGroupId(el),
        focusable: true,
    }));
}
"""


def _tab_traverse(page: Any, cap: int) -> list[dict]:
    page.evaluate(_SETUP_TAB_TRACE_JS)
    for _ in range(cap):
        page.keyboard.press("Tab")
        page.evaluate("() => window.__markAndRecord()")
        status = page.evaluate("() => window.__tabStatus")
        if status != "running":
            break
    return page.evaluate("() => window.__probeTrace")


def _resolve_markers(
    cdp: Any,
    markers: list[dict],
    ax_tree: list[AXNode],
) -> tuple[list[str], dict[int, str]]:
    """Map probe-marker-tagged DOM elements back to AX node IDs and DOM tags.

    One DOM.querySelector + DOM.describeNode per marker. For 200 markers
    that's ~400 CDP round-trips; under local network latency this is
    sub-second per probe (observed).
    """
    backend_to_ax_id: dict[int, str] = {}
    for node in ax_tree:
        if node.backendDOMNodeId is not None:
            backend_to_ax_id[node.backendDOMNodeId] = node.nodeId

    doc = cdp.send("DOM.getDocument")
    doc_node_id = doc["root"]["nodeId"]

    ax_ids: list[str] = []
    dom_tags: dict[int, str] = {}
    for entry in markers:
        marker = entry.get("marker")
        if not marker:
            continue
        qs = cdp.send(
            "DOM.querySelector",
            {"nodeId": doc_node_id, "selector": f"[data-probe-marker='{marker}']"},
        )
        dom_node_id = qs.get("nodeId")
        if not dom_node_id:
            continue
        described = cdp.send("DOM.describeNode", {"nodeId": dom_node_id})
        info = described.get("node", {})
        backend = info.get("backendNodeId")
        if backend is None:
            continue
        raw_tag = info.get("nodeName")
        if raw_tag:
            dom_tags[backend] = raw_tag.lower()
        ax_id = backend_to_ax_id.get(backend)
        if ax_id is not None:
            ax_ids.append(ax_id)

    return ax_ids, dom_tags


def probe(url: str, browser: Any, config: ProbeConfig | None = None) -> ProbeResult:
    """Run a full probe against `url` using `browser` (a `playwright.sync_api.Browser`).

    Caller owns the browser lifetime; probe creates and closes a fresh
    BrowserContext per invocation.
    """
    cfg = config or ProbeConfig()
    overall_start = time.monotonic()

    context = browser.new_context(
        user_agent=cfg.user_agent,
        viewport={"width": cfg.viewport_width, "height": cfg.viewport_height},
    )
    try:
        page = context.new_page()
        cdp = context.new_cdp_session(page)
        cdp.send("DOM.enable")
        cdp.send("Accessibility.enable")

        if cfg.session_state == "fresh":
            context.clear_cookies()

        page.goto(url)

        ni_start = time.monotonic()
        page.wait_for_load_state("networkidle")
        networkidle_wait_ms = int((time.monotonic() - ni_start) * 1000)

        settle_start = time.monotonic()
        page.wait_for_timeout(cfg.settle_ms)
        settle_wait_ms = int((time.monotonic() - settle_start) * 1000)

        ax_start = time.monotonic()
        ax_raw = cdp.send("Accessibility.getFullAXTree")
        ax_tree = [AXNode.model_validate(n) for n in ax_raw.get("nodes", [])]
        ax_tree_ms = int((time.monotonic() - ax_start) * 1000)

        tab_start = time.monotonic()
        markers = _tab_traverse(page, cfg.tab_depth_cap)
        tab_traversal_ms = int((time.monotonic() - tab_start) * 1000)

        tab_order_ax_ids, dom_tags = _resolve_markers(cdp, markers, ax_tree)

        contexts_raw = page.evaluate(_COLLECT_CONTEXTS_JS)
        element_contexts = [ElementDOMContext.model_validate(c) for c in contexts_raw]

        endpoints_list = extract_endpoints(
            tab_order_ax_ids, ax_tree, dom_tags=dom_tags
        )
        fp = fingerprint(endpoints_list)
        grouping_map = build_grouping_map(element_contexts)

        total_elapsed_ms = int((time.monotonic() - overall_start) * 1000)

        return ProbeResult(
            url=url,
            config=cfg,
            timing=ProbeTiming(
                total_elapsed_ms=total_elapsed_ms,
                networkidle_wait_ms=networkidle_wait_ms,
                settle_wait_ms=settle_wait_ms,
                ax_tree_ms=ax_tree_ms,
                tab_traversal_ms=tab_traversal_ms,
            ),
            ax_tree=ax_tree,
            tab_order_ax_ids=tab_order_ax_ids,
            dom_tags=dom_tags,
            element_contexts=element_contexts,
            endpoints=endpoints_list,
            fingerprint=fp,
            grouping=grouping_map,
        )
    finally:
        context.close()
