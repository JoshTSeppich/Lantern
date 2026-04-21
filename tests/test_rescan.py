"""Tests for lantern.rescan — Methodology D three-pass protocol + poke-selection policy."""

from __future__ import annotations

import pytest

from lantern import rescan
from lantern.endpoints import AXNode
from lantern.fingerprint import FingerprintTuple, ProbeRecord
from lantern.grouping import ElementDOMContext, ElementGrouping, build_grouping_map
from lantern.probe import ProbeConfig, ProbeResult, ProbeTiming
from lantern.rescan import (
    MAX_NAV_LINKS_TO_POKE,
    PokeCandidate,
    PokeOutcome,
    RescanResult,
    rescan as rescan_fn,
    select_poke_endpoints,
)
from lantern.vocab import StateBit


# -------------------------------------------------------------------------
# select_poke_endpoints — policy tests on synthetic ProbeResult
# -------------------------------------------------------------------------

def _make_probe_result(
    *,
    endpoints: list[ProbeRecord],
    fingerprint: list[FingerprintTuple],
    element_contexts: list[ElementDOMContext],
) -> ProbeResult:
    """Build a minimal ProbeResult for policy testing. AX tree, dom_tags, tab_order,
    and grouping are filled with whatever shapes keep the model valid."""
    return ProbeResult(
        url="http://example/",
        config=ProbeConfig(),
        timing=ProbeTiming(
            total_elapsed_ms=0,
            networkidle_wait_ms=0,
            settle_wait_ms=0,
            ax_tree_ms=0,
            tab_traversal_ms=0,
        ),
        ax_tree=[],
        tab_order_ax_ids=[],
        dom_tags={},
        element_contexts=element_contexts,
        endpoints=endpoints,
        fingerprint=fingerprint,
        grouping=build_grouping_map(element_contexts),
    )


def _pr(role: str, name: str, ancestors: list[str], props: dict | None = None) -> ProbeRecord:
    return ProbeRecord(
        ax_role=role,
        ax_properties=props or {},
        ancestor_ax_roles=ancestors,
        accessible_name=name,
        tag_name=None,
    )


def _ctx(
    eid: str,
    form: str | None = None,
    aria: dict[str, str] | None = None,
) -> ElementDOMContext:
    return ElementDOMContext(
        element_id=eid,
        aria_attributes=aria or {},
        form_ancestor_id=form,
        layout_group_id=None,
        focusable=True,
    )


class TestSelectButtonInMain:
    def test_picks_buttons_in_main(self):
        endpoints = [
            _pr("button", "save", ["main", "WebArea"]),
            _pr("button", "cancel", ["main", "WebArea"]),
            _pr("link", "home", ["navigation", "WebArea"]),  # not a button
            _pr("button", "tweet", ["navigation", "WebArea"]),  # not in main
        ]
        fingerprint = [
            FingerprintTuple("button", 0, "main"),
            FingerprintTuple("button", 0, "main"),
            FingerprintTuple("link", 0, "nav"),
            FingerprintTuple("button", 0, "nav"),
        ]
        contexts = [_ctx(f"e{i}") for i in range(4)]
        result = _make_probe_result(
            endpoints=endpoints, fingerprint=fingerprint, element_contexts=contexts
        )

        cands = select_poke_endpoints(result)
        names = [c.accessible_name for c in cands]
        reasons = [c.selection_reason for c in cands if c.selection_reason == "button-in-main"]
        assert "save" in names
        assert "cancel" in names
        assert "tweet" not in names  # not in main
        assert len(reasons) == 2


class TestSelectLinkInNav:
    def test_picks_links_in_nav(self):
        endpoints = [_pr("link", f"link-{i}", ["navigation", "WebArea"]) for i in range(3)]
        fingerprint = [FingerprintTuple("link", 0, "nav") for _ in range(3)]
        contexts = [_ctx(f"e{i}") for i in range(3)]
        result = _make_probe_result(
            endpoints=endpoints, fingerprint=fingerprint, element_contexts=contexts
        )

        cands = select_poke_endpoints(result)
        reasons = [c.selection_reason for c in cands]
        assert reasons.count("link-in-nav") == 3

    def test_cap_at_max_nav_links_to_poke(self):
        """Policy (b): up to 10 links in nav, in tab order. Extras beyond cap dropped."""
        n = MAX_NAV_LINKS_TO_POKE + 5  # 15 links
        endpoints = [_pr("link", f"link-{i}", ["navigation", "WebArea"]) for i in range(n)]
        fingerprint = [FingerprintTuple("link", 0, "nav") for _ in range(n)]
        contexts = [_ctx(f"e{i}") for i in range(n)]
        result = _make_probe_result(
            endpoints=endpoints, fingerprint=fingerprint, element_contexts=contexts
        )

        cands = select_poke_endpoints(result)
        nav_link_reasons = [c for c in cands if c.selection_reason == "link-in-nav"]
        assert len(nav_link_reasons) == MAX_NAV_LINKS_TO_POKE
        # First 10 by tab order
        assert [c.accessible_name for c in nav_link_reasons] == [f"link-{i}" for i in range(10)]


class TestSelectFirstTextboxInForm:
    def test_first_textbox_in_form_picked(self):
        endpoints = [
            _pr("button", "submit", ["main", "WebArea"]),
            _pr("textbox", "username", ["main", "WebArea"]),
            _pr("textbox", "password", ["main", "WebArea"]),
        ]
        fingerprint = [
            FingerprintTuple("button", 0, "main"),
            FingerprintTuple("textbox", 0, "main"),
            FingerprintTuple("textbox", 0, "main"),
        ]
        # username and password are inside form 'login-form'; submit is also in it
        contexts = [
            _ctx("submit", form="login-form"),
            _ctx("username", form="login-form"),
            _ctx("password", form="login-form"),
        ]
        result = _make_probe_result(
            endpoints=endpoints, fingerprint=fingerprint, element_contexts=contexts
        )

        cands = select_poke_endpoints(result)
        textbox_cands = [c for c in cands if c.selection_reason == "first-textbox-in-form"]
        # Only ONE textbox candidate — the first one
        assert len(textbox_cands) == 1
        assert textbox_cands[0].accessible_name == "username"

    def test_textbox_not_in_form_not_picked(self):
        endpoints = [_pr("textbox", "search", ["main", "WebArea"])]
        fingerprint = [FingerprintTuple("textbox", 0, "main")]
        contexts = [_ctx("search", form=None)]  # no form ancestor
        result = _make_probe_result(
            endpoints=endpoints, fingerprint=fingerprint, element_contexts=contexts
        )

        cands = select_poke_endpoints(result)
        textbox_cands = [c for c in cands if c.selection_reason == "first-textbox-in-form"]
        assert textbox_cands == []


class TestSelectAriaHaspopup:
    def test_any_aria_haspopup_picked(self):
        endpoints = [
            _pr("button", "menu", ["navigation", "WebArea"], props={"hasPopup": "menu"}),
            _pr("combobox", "country", ["main", "WebArea"], props={"hasPopup": "listbox"}),
            _pr("button", "plain", ["main", "WebArea"]),
        ]
        fingerprint = [
            FingerprintTuple("button", int(StateBit.HASPOPUP), "nav"),
            FingerprintTuple("combobox", int(StateBit.HASPOPUP), "main"),
            FingerprintTuple("button", 0, "main"),
        ]
        contexts = [_ctx(f"e{i}") for i in range(3)]
        result = _make_probe_result(
            endpoints=endpoints, fingerprint=fingerprint, element_contexts=contexts
        )

        cands = select_poke_endpoints(result)
        haspopup_cands = [c for c in cands if c.selection_reason == "aria-haspopup"]
        names = {c.accessible_name for c in haspopup_cands}
        assert "menu" in names
        assert "country" in names
        assert "plain" not in names


class TestDedup:
    def test_dedup_by_role_name_landmark(self):
        """A button that satisfies both 'button-in-main' AND 'aria-haspopup' → one candidate."""
        endpoints = [
            _pr("button", "menu", ["main", "WebArea"], props={"hasPopup": "menu"}),
        ]
        fingerprint = [FingerprintTuple("button", int(StateBit.HASPOPUP), "main")]
        contexts = [_ctx("e0")]
        result = _make_probe_result(
            endpoints=endpoints, fingerprint=fingerprint, element_contexts=contexts
        )

        cands = select_poke_endpoints(result)
        # dedup by (role, name_hash, landmark) — one instance even though it matches 2 rules
        assert len(cands) == 1

    def test_duplicate_named_buttons_deduplicated(self):
        """Two buttons with same role+name+landmark → keep one."""
        endpoints = [
            _pr("button", "close", ["main", "WebArea"]),
            _pr("button", "close", ["main", "WebArea"]),
        ]
        fingerprint = [
            FingerprintTuple("button", 0, "main"),
            FingerprintTuple("button", 0, "main"),
        ]
        contexts = [_ctx("e0"), _ctx("e1")]
        result = _make_probe_result(
            endpoints=endpoints, fingerprint=fingerprint, element_contexts=contexts
        )

        cands = select_poke_endpoints(result)
        assert len(cands) == 1


class TestEmptyResult:
    def test_no_candidates_from_empty_probe(self):
        result = _make_probe_result(endpoints=[], fingerprint=[], element_contexts=[])
        assert select_poke_endpoints(result) == []


# -------------------------------------------------------------------------
# End-to-end rescan on fixture page (real Chromium)
# -------------------------------------------------------------------------

class TestRescanEndToEnd:
    """Rescan against tests/fixtures/probe/rescan.html + rescan-other.html via the
    local HTTP fixture server. Exercises the three-pass protocol: initial scan,
    per-candidate poke+settle, rescan for F₁, URL-change detection for navigation."""

    @pytest.fixture(scope="class")
    def rescan_url(self, http_fixture_server: str) -> str:
        return f"{http_fixture_server}/rescan.html"

    @pytest.fixture(scope="class")
    def rescan_result(self, rescan_url: str, browser) -> RescanResult:
        return rescan_fn(rescan_url, browser)

    def test_initial_probe_produced_fingerprint(self, rescan_result: RescanResult):
        assert len(rescan_result.initial_probe.fingerprint) > 0

    def test_poke_candidates_found(self, rescan_result: RescanResult):
        assert len(rescan_result.poke_candidates) > 0
        # Expected: some buttons-in-main, some links-in-nav, a textbox, a haspopup
        reasons = {c.selection_reason for c in rescan_result.poke_candidates}
        assert "button-in-main" in reasons
        assert "link-in-nav" in reasons

    def test_outcomes_count_matches_candidates(self, rescan_result: RescanResult):
        assert len(rescan_result.outcomes) == len(rescan_result.poke_candidates)

    def test_reveal_button_produces_state_change(self, rescan_result: RescanResult):
        """rescan.html's btn-reveal reveals #revealed-panel which adds btn-inner and
        input-inner to the tab order. The rescan should detect this as state_change
        with a non-empty delta_added."""
        reveal_outcomes = [
            o for o in rescan_result.outcomes
            if o.candidate.accessible_name and "reveal" in o.candidate.accessible_name.lower()
        ]
        assert len(reveal_outcomes) == 1
        outcome = reveal_outcomes[0]
        assert outcome.kind == "state_change", (
            f"Expected state_change on btn-reveal, got {outcome.kind}. "
            f"delta_added={outcome.delta_added}, delta_removed={outcome.delta_removed}"
        )
        assert len(outcome.delta_added) > 0, "Expected at least one element to be revealed"

    def test_noop_button_produces_no_change(self, rescan_result: RescanResult):
        noop_outcomes = [
            o for o in rescan_result.outcomes
            if o.candidate.accessible_name and "nothing" in o.candidate.accessible_name.lower()
        ]
        assert len(noop_outcomes) == 1
        assert noop_outcomes[0].kind == "no_change"
        assert noop_outcomes[0].delta_added == []

    def test_external_link_produces_navigation(self, rescan_result: RescanResult):
        """rescan.html's nav-external goes to rescan-other.html — URL changes."""
        nav_outcomes = [
            o for o in rescan_result.outcomes
            if o.candidate.accessible_name and "navigate away" in o.candidate.accessible_name.lower()
        ]
        assert len(nav_outcomes) == 1
        outcome = nav_outcomes[0]
        assert outcome.kind == "navigation"
        assert outcome.destination_url is not None
        assert "rescan-other.html" in outcome.destination_url

    def test_rescan_deterministic_across_runs(self, rescan_url: str, browser):
        """Two independent rescan runs produce the same state_transition_summary."""
        r1 = rescan_fn(rescan_url, browser)
        r2 = rescan_fn(rescan_url, browser)
        assert r1.state_transition_summary() == r2.state_transition_summary()

    def test_timing_populated(self, rescan_result: RescanResult):
        assert rescan_result.timing.total_elapsed_ms > 0
        assert rescan_result.timing.poke_count == len(rescan_result.poke_candidates)
        assert rescan_result.timing.initial_probe_ms >= 0
