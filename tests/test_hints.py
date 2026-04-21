"""Tests for lantern.hints — prompt loading + LLM orchestration + output parsing."""

from __future__ import annotations

import pytest

from lantern import hints as hints_mod
from lantern.hints import (
    MAX_HINTS,
    MAX_TOKENS_PER_HINT,
    generate_hints,
    get_llm_call,
    load_prompt_template,
    parse_hints_output,
    render_prompt,
    set_llm_call,
)


@pytest.fixture(autouse=True)
def reset_llm_call():
    """Ensure each test starts with no default LLM call."""
    set_llm_call(None)
    yield
    set_llm_call(None)


class TestLoadPromptTemplate:
    def test_terse_loads(self):
        t = load_prompt_template("terse")
        assert "{shape_id}" in t
        assert "{confidence}" in t
        # HTML comment header stripped
        assert "<!--" not in t

    def test_explicit_loads(self):
        t = load_prompt_template("explicit")
        assert "{shape_id}" in t
        assert "{confidence}" in t
        assert "<!--" not in t
        assert "Role" in t or "role" in t  # scaffolded sections present


class TestRenderPrompt:
    def test_substitutes_all_placeholders(self):
        template = load_prompt_template("terse")
        rendered = render_prompt(
            template,
            shape_id="cluster-2",
            shape_description="minimal-login",
            confidence=0.83,
            element_summary="4 buttons, 2 textboxes in form",
            state_transitions_summary="",
            task="Sign in",
        )
        assert "cluster-2" in rendered
        assert "0.83" in rendered
        assert "minimal-login" in rendered
        assert "{shape_id}" not in rendered  # fully substituted


class TestParseHintsOutput:
    def test_empty_input(self):
        assert parse_hints_output("") == []

    def test_single_bullet(self):
        assert parse_hints_output("- First hint") == ["First hint"]

    def test_multiple_bullets(self):
        raw = "- First hint\n- Second hint\n- Third hint"
        assert parse_hints_output(raw) == ["First hint", "Second hint", "Third hint"]

    def test_truncates_to_max_hints(self):
        raw = "\n".join(f"- Hint {i}" for i in range(MAX_HINTS + 3))
        parsed = parse_hints_output(raw)
        assert len(parsed) == MAX_HINTS

    def test_truncates_tokens_per_hint(self):
        long_hint = "word " * (MAX_TOKENS_PER_HINT + 10)
        raw = f"- {long_hint.strip()}"
        parsed = parse_hints_output(raw)
        assert len(parsed) == 1
        assert len(parsed[0].split()) <= MAX_TOKENS_PER_HINT

    def test_ignores_non_bullet_lines(self):
        raw = "Preamble text\n- Real hint\nTrailing commentary"
        assert parse_hints_output(raw) == ["Real hint"]

    def test_ignores_wrong_bullet_style(self):
        """Asterisk bullets and numbered lists are not recognized as valid bullets."""
        raw = "* Asterisk bullet\n1. Numbered\n- Real dash bullet"
        assert parse_hints_output(raw) == ["Real dash bullet"]


class TestLlmCallConfig:
    def test_default_is_none(self):
        assert get_llm_call() is None

    def test_set_and_get(self):
        def stub(prompt: str) -> str:
            return "- stub"

        set_llm_call(stub)
        assert get_llm_call() is stub

    def test_reset_to_none(self):
        set_llm_call(lambda p: "- x")
        set_llm_call(None)
        assert get_llm_call() is None


class TestGenerateHints:
    def _inputs(self) -> dict:
        return dict(
            shape_id="cluster-2",
            shape_description="minimal-login",
            confidence=0.83,
            element_summary="4 buttons, 2 textboxes in form",
            state_transitions_summary="",
            task="Sign in",
        )

    def test_no_llm_configured_returns_empty(self):
        assert generate_hints(**self._inputs()) == []

    def test_explicit_llm_call_used(self):
        captured_prompts: list[str] = []

        def stub(prompt: str) -> str:
            captured_prompts.append(prompt)
            return "- Look for username and password fields\n- Submit button is in the form footer"

        result = generate_hints(**self._inputs(), llm_call=stub)
        assert len(result) == 2
        assert "username" in result[0]
        assert len(captured_prompts) == 1
        assert "cluster-2" in captured_prompts[0]

    def test_module_level_llm_call_used_when_no_explicit(self):
        set_llm_call(lambda p: "- Module-level hint")
        result = generate_hints(**self._inputs())
        assert result == ["Module-level hint"]

    def test_explicit_argument_overrides_module_default(self):
        set_llm_call(lambda p: "- Module-level hint")
        result = generate_hints(
            **self._inputs(),
            llm_call=lambda p: "- Explicit arg hint",
        )
        assert result == ["Explicit arg hint"]

    def test_variant_selection(self):
        captured: list[str] = []

        def stub(prompt: str) -> str:
            captured.append(prompt)
            return "- hint"

        generate_hints(**self._inputs(), variant="terse", llm_call=stub)
        generate_hints(**self._inputs(), variant="explicit", llm_call=stub)

        assert len(captured) == 2
        # Explicit variant should be noticeably longer (scaffolded sections)
        assert len(captured[1]) > len(captured[0]) * 2

    def test_output_truncated_to_5_bullets_and_40_tokens(self):
        def stub(prompt: str) -> str:
            long_word = "word " * 50
            return "\n".join(f"- {long_word}" for _ in range(10))

        result = generate_hints(**self._inputs(), llm_call=stub)
        assert len(result) <= MAX_HINTS
        for hint in result:
            assert len(hint.split()) <= MAX_TOKENS_PER_HINT
