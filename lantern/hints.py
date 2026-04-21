"""
lantern/hints.py — hint generation per LANTERN.md Part 4 Step 7 + R0.5.

Loads one of two pre-registered prompt variants (`terse` / `explicit`) from
`lantern/prompts/`, renders it with shape + probe inputs, calls a pluggable
LLM, and parses the output into ≤5 bullets ≤40 tokens each (Part 5
Measurement Surface Freeze).

LLM call is caller-provided; Lantern doesn't bundle any LLM SDK. Per R2.2,
Sherpa wires up the actual Anthropic (or equivalent) client at integration
time with its own temperature/model/max_tokens values.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Final, Literal


PROMPTS_DIR: Final[Path] = Path(__file__).parent / "prompts"

PROMPT_PATHS: Final[dict[str, Path]] = {
    "terse":    PROMPTS_DIR / "hint_generation_terse.md",
    "explicit": PROMPTS_DIR / "hint_generation_explicit.md",
}

MAX_HINTS: Final[int] = 5
MAX_TOKENS_PER_HINT: Final[int] = 40

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->\s*", re.DOTALL)


# Module-level LLM-call configuration. None → soft fallthrough to empty hints.
_llm_call: Callable[[str], str] | None = None


def set_llm_call(fn: Callable[[str], str] | None) -> None:
    """Configure the default LLM-call function. `None` clears any existing."""
    global _llm_call
    _llm_call = fn


def get_llm_call() -> Callable[[str], str] | None:
    """Return the currently-configured default LLM-call function."""
    return _llm_call


def load_prompt_template(variant: Literal["terse", "explicit"]) -> str:
    """Load a prompt template, stripping the leading HTML comment header."""
    path = PROMPT_PATHS[variant]
    raw = path.read_text()
    # Strip the first HTML comment (contract-note preamble); body is the template
    body = _HTML_COMMENT_RE.sub("", raw, count=1)
    return body.strip()


def render_prompt(
    template: str,
    *,
    shape_id: str,
    shape_description: str,
    confidence: float,
    element_summary: str,
    state_transitions_summary: str,
    task: str = "",
) -> str:
    """Fill prompt template placeholders with shape + probe inputs."""
    return template.format(
        shape_id=shape_id,
        shape_description=shape_description,
        confidence=f"{confidence:.2f}",
        element_summary=element_summary,
        state_transitions_summary=state_transitions_summary,
        task=task,
    )


def parse_hints_output(raw: str) -> list[str]:
    """Extract '- <text>' bullet lines from raw LLM output.

    - Lines not starting with '- ' are ignored.
    - Asterisk bullets or numbered lists are NOT recognized.
    - Each bullet's word count capped at MAX_TOKENS_PER_HINT.
    - Total bullet count capped at MAX_HINTS.
    """
    bullets: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        text = stripped[2:].strip()
        words = text.split()
        if len(words) > MAX_TOKENS_PER_HINT:
            text = " ".join(words[:MAX_TOKENS_PER_HINT])
        bullets.append(text)
        if len(bullets) >= MAX_HINTS:
            break
    return bullets


def generate_hints(
    *,
    shape_id: str,
    shape_description: str,
    confidence: float,
    element_summary: str,
    state_transitions_summary: str = "",
    task: str = "",
    variant: Literal["terse", "explicit"] = "terse",
    llm_call: Callable[[str], str] | None = None,
) -> list[str]:
    """Generate hints for a classified shape.

    Uses `llm_call` if passed, else module-level default set by
    `set_llm_call()`. If neither is configured, returns `[]` — soft
    fallthrough matching R2.2's Sherpa-side exception handling.
    """
    fn = llm_call if llm_call is not None else _llm_call
    if fn is None:
        return []

    template = load_prompt_template(variant)
    prompt = render_prompt(
        template,
        shape_id=shape_id,
        shape_description=shape_description,
        confidence=confidence,
        element_summary=element_summary,
        state_transitions_summary=state_transitions_summary,
        task=task,
    )
    raw = fn(prompt)
    return parse_hints_output(raw)
