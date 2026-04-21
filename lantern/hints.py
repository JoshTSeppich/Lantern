"""
lantern/hints.py — hint generation per LANTERN.md Part 4 Step 7 + R0.5.

Loads one of two pre-registered prompt variants (`terse` / `explicit`) from
`lantern/prompts/`, renders it with shape + probe inputs, calls a
pluggable LLM, and parses the output into ≤5 bullets ≤40 tokens each
(hint length cap per LANTERN.md Part 5 Measurement Surface Freeze).

The LLM call is caller-provided. Lantern does not bundle an Anthropic
(or any other) LLM client — per R2.2, the hint-generation LLM's temperature,
model, and max_tokens are pinned to Sherpa's production values at
integration time. Two ways to provide the LLM call:

  1. Pass `llm_call=` directly to `generate_hints()`.
  2. Configure module-level default via `set_llm_call(fn)` at startup;
     any subsequent `generate_hints()` with no `llm_call` argument uses
     the default.

If neither is set, `generate_hints()` returns an empty list (soft
fallthrough — Sherpa runs blind, consistent with R2.2's integration
pattern).

STUB — L-11 red. Implementation lands in green(L-11).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Final, Literal


PROMPTS_DIR: Final[Path] = Path(__file__).parent / "prompts"

PROMPT_PATHS: Final[dict[str, Path]] = {
    "terse":    PROMPTS_DIR / "hint_generation_terse.md",
    "explicit": PROMPTS_DIR / "hint_generation_explicit.md",
}

MAX_HINTS: Final[int] = 5
MAX_TOKENS_PER_HINT: Final[int] = 40  # approximated as whitespace-delimited words


# Module-level LLM-call configuration. None by default → soft fallthrough.
_llm_call: Callable[[str], str] | None = None


def set_llm_call(fn: Callable[[str], str] | None) -> None:
    """Configure the default LLM-call function used by generate_hints().

    Passing `None` resets to the default (returns empty hints)."""
    raise NotImplementedError("L-11 stub")


def get_llm_call() -> Callable[[str], str] | None:
    """Read the current module-level LLM-call function (for introspection)."""
    raise NotImplementedError("L-11 stub")


def load_prompt_template(variant: Literal["terse", "explicit"]) -> str:
    """Load a prompt template, stripping the HTML comment header."""
    raise NotImplementedError("L-11 stub")


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
    """Fill prompt template placeholders with the shape + probe inputs."""
    raise NotImplementedError("L-11 stub")


def parse_hints_output(raw: str) -> list[str]:
    """Extract bullet lines from raw LLM output; enforce MAX_HINTS and
    MAX_TOKENS_PER_HINT post-hoc. Lines not matching '- <text>' are dropped."""
    raise NotImplementedError("L-11 stub")


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

    If neither `llm_call=` nor `set_llm_call()` is configured, returns []."""
    raise NotImplementedError("L-11 stub")
