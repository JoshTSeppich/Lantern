<!--
Lantern hint generation — VARIANT A (terse).
Frozen 2026-04-21 per R0.5. Axis: terseness (vs hint_generation_explicit.md).
Pre-L-12-utility. Post-hoc quality concerns are findings, not drift
justifications.

Placeholders filled at call time by lantern.hints (L-11):
  {shape_id}                 — library shape ID, e.g. "cluster-2" or "minimal-login"
  {shape_description}        — one-line canonical description of the shape class
  {confidence}               — match confidence, 0.0 to 1.0
  {element_summary}          — textual summary of the static fingerprint + names
  {state_transitions_summary}— textual summary of rescan deltas (kinds + counts)
  {task}                     — optional task description; may be empty string

Output constraint enforced post-generation by hints.py: at most 5 bullets,
each ≤ 40 tokens. Bullets not matching "- <text>" format are dropped.
-->

The page below has been classified by Lantern as shape `{shape_id}` (confidence {confidence}).

Shape description: {shape_description}

Observed element summary:
{element_summary}

State-transition summary:
{state_transitions_summary}

Task the executor will attempt (may be empty): {task}

Produce up to 5 hints about where primary controls are, what interactions reveal new controls, and what to expect structurally. Each hint on its own line, starting with "- ", ≤ 40 tokens. No preamble, no trailing summary. Omit hints that would be redundant with a generic web-executor's defaults.
