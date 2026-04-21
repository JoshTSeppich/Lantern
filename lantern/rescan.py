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
"""

from __future__ import annotations

import hashlib
import time
from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from lantern.endpoints import AXNode, extract_endpoints
from lantern.fingerprint import FingerprintTuple, ProbeRecord, fingerprint as build_fingerprint
from lantern.probe import (
    ProbeConfig,
    ProbeResult,
    _resolve_markers,
    _tab_traverse,
    probe,
)
from lantern.vocab import StateBit


_LANDMARK_TO_SELECTOR: dict[str, str] = {
    "main":   "main, [role='main']",
    "nav":    "nav, [role='navigation']",
    "header": "header, [role='banner']",
    "footer": "footer, [role='contentinfo']",
    "aside":  "aside, [role='complementary']",
}


def _scope_for_landmark(page: Any, landmark: str) -> Any:
    """Playwright locator scoped to the given landmark; falls back to the page itself."""
    selector = _LANDMARK_TO_SELECTOR.get(landmark)
    if selector is None:
        return page
    return page.locator(selector).first


def _multiset_delta(
    f0: list[FingerprintTuple],
    f1: list[FingerprintTuple],
) -> tuple[list[FingerprintTuple], list[FingerprintTuple]]:
    """Multiset difference of two fingerprint sequences.

    A tuple that appears 3 times in F₀ and 5 times in F₁ contributes 2 to
    delta_added (not 0 as set-diff would). This matches 'delta = F₁ \\ F₀ at
    matching positions' (Part 4 Step 4 point 7) — set-level diff would
    collapse duplicate (role, state_bitmap, landmark) tuples that are common
    on pages with many same-role elements.
    """
    c0 = Counter(f0)
    c1 = Counter(f1)
    added: list[FingerprintTuple] = []
    removed: list[FingerprintTuple] = []
    for tup, n1 in c1.items():
        n0 = c0.get(tup, 0)
        if n1 > n0:
            added.extend([tup] * (n1 - n0))
    for tup, n0 in c0.items():
        n1 = c1.get(tup, 0)
        if n0 > n1:
            removed.extend([tup] * (n0 - n1))
    return added, removed


POKE_SETTLE_CAP_MS: int = 8000
MAX_NAV_LINKS_TO_POKE: int = 10


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


# -------------------------------------------------------------------------
# Poke selection
# -------------------------------------------------------------------------

def _dedup_key(role: str, name: str | None, landmark: str) -> str:
    name_raw = name or ""
    name_hash = hashlib.sha256(name_raw.encode()).hexdigest()[:12]
    return f"{role}|{name_hash}|{landmark}"


def select_poke_endpoints(initial: ProbeResult) -> list[PokeCandidate]:
    """Apply LANTERN.md Part 4 Step 3 poke-selection policy.

    Returns candidates in tab order (stable). Dedup by dedup_key preserves
    the first-seen selection_reason per unique key, prioritizing by policy
    order (a)→(b)→(c)→(d).
    """
    endpoints = initial.endpoints
    fingerprint = initial.fingerprint
    contexts = initial.element_contexts

    # Tab-order alignment: endpoints[i] ↔ fingerprint[i]. For element_contexts,
    # we assume alignment on well-formed pages (no positive tabindex); if
    # len(contexts) != len(endpoints), align by prefix (best-effort) so the
    # policy's form-ancestor check falls back to "no form" for unaligned
    # elements.
    def ctx_for(i: int) -> object:
        return contexts[i] if i < len(contexts) else None

    candidates: dict[str, PokeCandidate] = {}

    def _maybe_add(i: int, reason: str) -> None:
        ep = endpoints[i]
        tup = fingerprint[i]
        key = _dedup_key(tup.role, ep.accessible_name, tup.landmark)
        if key in candidates:
            return  # preserve first-seen reason per policy order
        candidates[key] = PokeCandidate(
            role=tup.role,
            landmark=tup.landmark,
            accessible_name=ep.accessible_name,
            tab_order_index=i,
            dedup_key=key,
            selection_reason=reason,  # type: ignore[arg-type]
        )

    # (a) all buttons in main
    for i, tup in enumerate(fingerprint):
        if tup.role == "button" and tup.landmark == "main":
            _maybe_add(i, "button-in-main")

    # (b) all links in nav (up to MAX_NAV_LINKS_TO_POKE, in tab order)
    nav_link_added = 0
    for i, tup in enumerate(fingerprint):
        if tup.role == "link" and tup.landmark == "nav":
            if nav_link_added >= MAX_NAV_LINKS_TO_POKE:
                break
            before = len(candidates)
            _maybe_add(i, "link-in-nav")
            if len(candidates) > before:
                nav_link_added += 1

    # (c) first textbox in a form
    for i, tup in enumerate(fingerprint):
        if tup.role != "textbox":
            continue
        ctx = ctx_for(i)
        if ctx is None:
            continue
        # ctx.form_ancestor_id is not None → inside a form
        if getattr(ctx, "form_ancestor_id", None) is None:
            continue
        _maybe_add(i, "first-textbox-in-form")
        break  # "first" — only one

    # (d) any element with aria-haspopup set (HASPOPUP bit in state_bitmap)
    for i, tup in enumerate(fingerprint):
        if tup.state_bitmap & int(StateBit.HASPOPUP):
            _maybe_add(i, "aria-haspopup")

    # Preserve tab order in the output
    return sorted(candidates.values(), key=lambda c: c.tab_order_index)


# -------------------------------------------------------------------------
# Per-poke execution
# -------------------------------------------------------------------------

def _execute_poke(
    url: str,
    candidate: PokeCandidate,
    f0: list[FingerprintTuple],
    browser: Any,
    config: ProbeConfig,
) -> PokeOutcome:
    start_wall = time.monotonic()
    context = browser.new_context(
        user_agent=config.user_agent,
        viewport={"width": config.viewport_width, "height": config.viewport_height},
    )
    try:
        page = context.new_page()
        cdp = context.new_cdp_session(page)
        cdp.send("DOM.enable")
        cdp.send("Accessibility.enable")

        if config.session_state == "fresh":
            context.clear_cookies()

        page.goto(url)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(config.settle_ms)

        # Find target via Playwright's ARIA-aware role locator, scoped to the
        # candidate's landmark. Avoids marker-index alignment brittleness (which
        # would break when `extract_endpoints` filters ignored/no-backend nodes,
        # desynchronizing positions across the markers list and the endpoints
        # list). name matching is case-insensitive substring (Playwright default).
        pre_url = page.url
        scope = _scope_for_landmark(page, candidate.landmark)
        try:
            if candidate.accessible_name:
                target = scope.get_by_role(candidate.role, name=candidate.accessible_name)
            else:
                target = scope.get_by_role(candidate.role)
            target.first.click(timeout=5000)
        except Exception as e:
            return PokeOutcome(
                candidate=candidate,
                kind="error",
                pre_fingerprint_size=len(f0),
                elapsed_ms=int((time.monotonic() - start_wall) * 1000),
                error_message=f"click failed: {type(e).__name__}: {str(e)[:120]}",
            )

        # Settle: networkidle + settle_ms, capped at POKE_SETTLE_CAP_MS total
        remaining_for_networkidle = max(1, POKE_SETTLE_CAP_MS - config.settle_ms)
        try:
            page.wait_for_load_state("networkidle", timeout=remaining_for_networkidle)
        except Exception:
            pass  # settle timeout is not a probe failure
        page.wait_for_timeout(config.settle_ms)

        post_url = page.url
        elapsed_ms = int((time.monotonic() - start_wall) * 1000)

        if post_url != pre_url:
            return PokeOutcome(
                candidate=candidate,
                kind="navigation",
                destination_url=post_url,
                pre_fingerprint_size=len(f0),
                post_fingerprint_size=None,
                elapsed_ms=elapsed_ms,
            )

        # Reset focus before F₁ tab traversal. After the click, the clicked
        # element has focus. _tab_traverse's `document.body.focus()` is a no-op
        # on non-focusable body (body has no tabindex by default), so the first
        # Tab would move to the element AFTER the clicked one — skipping
        # elements before it in tab order and spuriously reporting them as
        # delta_removed. Explicitly blur, set tabindex=-1 on body so it becomes
        # programmatically focusable, then focus body so the next Tab lands on
        # the first focusable element.
        page.evaluate(
            "() => {"
            "  if (document.activeElement && document.activeElement !== document.body) {"
            "    try { document.activeElement.blur(); } catch (e) {}"
            "  }"
            "  if (!document.body.hasAttribute('tabindex')) {"
            "    document.body.setAttribute('tabindex', '-1');"
            "  }"
            "  document.body.focus();"
            "}"
        )

        # Rescan: tab-traverse + AX tree for F₁
        new_markers = _tab_traverse(page, config.tab_depth_cap)
        new_ax_raw = cdp.send("Accessibility.getFullAXTree")
        new_ax_tree = [AXNode.model_validate(n) for n in new_ax_raw.get("nodes", [])]
        new_tab_order, new_dom_tags = _resolve_markers(cdp, new_markers, new_ax_tree)
        new_endpoints = extract_endpoints(new_tab_order, new_ax_tree, dom_tags=new_dom_tags)
        f1 = build_fingerprint(new_endpoints)

        delta_added, delta_removed = _multiset_delta(f0, f1)

        kind = "state_change" if (delta_added or delta_removed) else "no_change"
        return PokeOutcome(
            candidate=candidate,
            kind=kind,
            pre_fingerprint_size=len(f0),
            post_fingerprint_size=len(f1),
            delta_added=delta_added,
            delta_removed=delta_removed,
            elapsed_ms=int((time.monotonic() - start_wall) * 1000),
        )
    finally:
        context.close()


# -------------------------------------------------------------------------
# Top-level rescan orchestrator
# -------------------------------------------------------------------------

def rescan(url: str, browser: Any, config: ProbeConfig | None = None) -> RescanResult:
    cfg = config or ProbeConfig()
    overall_start = time.monotonic()

    initial_start = time.monotonic()
    initial = probe(url, browser, cfg)
    initial_ms = int((time.monotonic() - initial_start) * 1000)

    candidates = select_poke_endpoints(initial)

    poke_start = time.monotonic()
    outcomes: list[PokeOutcome] = []
    for candidate in candidates:
        outcome = _execute_poke(url, candidate, list(initial.fingerprint), browser, cfg)
        outcomes.append(outcome)
    poke_ms = int((time.monotonic() - poke_start) * 1000)

    total_ms = int((time.monotonic() - overall_start) * 1000)

    return RescanResult(
        url=url,
        config=cfg,
        initial_probe=initial,
        poke_candidates=candidates,
        outcomes=outcomes,
        timing=RescanTiming(
            total_elapsed_ms=total_ms,
            initial_probe_ms=initial_ms,
            poke_count=len(candidates),
            poke_total_ms=poke_ms,
        ),
    )
