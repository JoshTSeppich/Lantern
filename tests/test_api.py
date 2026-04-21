"""Tests for lantern.api — classify() public surface per R2.1."""

from __future__ import annotations

import pytest

from lantern import hints as hints_mod
from lantern.api import LanternResult, classify


@pytest.fixture(autouse=True)
def reset_llm_call():
    hints_mod.set_llm_call(None)
    yield
    hints_mod.set_llm_call(None)


class TestLanternResultContract:
    """R2.1: frozen dataclass, exact field set."""

    def test_fields(self):
        r = LanternResult(
            shape_id="cluster-2",
            confidence=0.83,
            hints=["a", "b"],
            fingerprint_hash="abcd",
            elapsed_ms=1234,
        )
        assert r.shape_id == "cluster-2"
        assert r.confidence == 0.83
        assert r.hints == ["a", "b"]
        assert r.fingerprint_hash == "abcd"
        assert r.elapsed_ms == 1234

    def test_frozen(self):
        r = LanternResult(
            shape_id="cluster-0", confidence=0.9, hints=[],
            fingerprint_hash="", elapsed_ms=0,
        )
        with pytest.raises(Exception):
            r.shape_id = "cluster-9"  # type: ignore[misc]

    def test_no_pydantic_dependency_exposed(self):
        """Frozen dataclass per R2.1, not pydantic BaseModel — keeps Sherpa's
        import surface minimal. Verifies by negative check."""
        from dataclasses import is_dataclass
        assert is_dataclass(LanternResult)


class TestClassifyIntegration:
    """End-to-end classify() against the local fixture HTTP server + stub LLM."""

    @pytest.fixture(scope="class")
    def simple_url(self, http_fixture_server: str) -> str:
        return f"{http_fixture_server}/simple.html"

    def test_classify_returns_result(self, simple_url: str):
        # No LLM configured → hints should be empty
        result = classify(simple_url, timeout_ms=60_000)
        assert isinstance(result, LanternResult)
        assert result.shape_id  # non-empty (either 'unknown' or 'cluster-<N>')
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.hints, list)
        assert result.fingerprint_hash
        assert result.elapsed_ms > 0

    def test_classify_with_stub_llm_produces_hints(self, simple_url: str):
        captured: list[str] = []

        def stub(prompt: str) -> str:
            captured.append(prompt)
            return "- Focus the username input first\n- Submit button reveals validation errors"

        hints_mod.set_llm_call(stub)
        result = classify(simple_url, timeout_ms=60_000)

        # Only get hints if classification was above confidence threshold
        if result.shape_id != "unknown":
            assert len(captured) == 1
            # Hints substituted shape_id into the prompt
            assert result.shape_id in captured[0]
            # Returned hints parsed from stub output
            assert len(result.hints) == 2
        else:
            # Unknown shape → no LLM call, hints empty
            assert result.hints == []

    def test_classify_unknown_shape_returns_empty_hints(self, simple_url: str):
        """When confidence < CONFIDENCE_THRESHOLD, hints should be empty
        regardless of LLM config (per LANTERN.md Part 4 Step 6)."""
        hints_mod.set_llm_call(lambda p: "- should not be used")

        result = classify(simple_url, timeout_ms=60_000)
        if result.shape_id == "unknown":
            assert result.hints == []

    def test_classify_soft_fallthrough_on_probe_error(self):
        """Invalid URL → classify() raises; Sherpa's integration (R2.2) catches
        the exception and proceeds blind. classify() itself does not swallow."""
        with pytest.raises(Exception):
            classify("http://127.0.0.1:1/nonexistent", timeout_ms=5_000)

    def test_classify_deterministic_on_simple_fixture(self, simple_url: str):
        """Two classify() calls on the same URL produce the same fingerprint_hash."""
        r1 = classify(simple_url, timeout_ms=60_000)
        r2 = classify(simple_url, timeout_ms=60_000)
        assert r1.fingerprint_hash == r2.fingerprint_hash
        assert r1.shape_id == r2.shape_id
