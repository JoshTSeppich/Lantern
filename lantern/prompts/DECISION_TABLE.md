# L-12 Utility Decision Table — disambiguating prompt-failure from classification-failure

**Status:** Frozen pre-L-12-utility per R0.5.
**Committed with:** `hint_generation_terse.md` (variant A) and `hint_generation_explicit.md` (variant B) at the same commit.
**Any change before L-12 evidence is collected:** pre-evidence revision (allowed with justification). **After L-12 evidence is collected:** rubric-drift event per §R4.

## What this table does

L-12 utility tests 20 Sherpa tasks × 10 held-out sites × 3 conditions (blind, primed with variant A, primed with variant B) = 600 runs. Per-run outcome is binary pass/fail. The aggregate metrics feed this table; this table produces the investigation-level Utility verdict plus any triage flags.

## Metrics definitions

Let `N = 200` be the total number of (task, site) cells.

- `P_blind  = (# passed blind runs) / N`
- `P_A      = (# passed primed-with-variant-A runs) / N`
- `P_B      = (# passed primed-with-variant-B runs) / N`
- `Δ_A      = P_A - P_blind`    (points, so e.g. 0.12 = "12 pts")
- `Δ_B      = P_B - P_blind`
- `D        = |Δ_A - Δ_B|`       (variant divergence in pts)
- `p_A, p_B = McNemar paired p-values` (A vs blind, B vs blind respectively)

All pts expressed as proportion-delta × 100 (so "10 pts" = 0.10).

## Base rubric (LANTERN.md Part 5 § Utility criterion, amended by R0.5)

Per R0.5, the rubric applies **per variant**:

- **Pass:**      `Δ_v ≥ 10 pts AND p_v < 0.05` for each variant v ∈ {A, B}
- **Soft Pass:** `Δ_v in [5, 10) pts` on one or both variants, OR `p_v < 0.10` on both
- **Fail:**      no improvement on either variant (both `Δ_v < 5 pts`), or both degrade

Per R0.5 `HUMAN REVIEW: prompt-variant-disagreement` flag fires when `D > 5 pts`.

## Decision table

Columns: Δ_A band. Rows: Δ_B band. Each cell: (investigation verdict, flags to raise).

| | **Δ_B < 0** (hurts) | **Δ_B in [0, 5)** (no signal) | **Δ_B in [5, 10)** (moderate) | **Δ_B ≥ 10** (strong) |
|---|---|---|---|---|
| **Δ_A < 0** (hurts) | **FAIL + HARMFUL.** Both variants hurt Sherpa. Lantern causes regression. Scope-down: drop hint layer; investigate why hints degrade executor. | **FAIL + HARMFUL (A).** A hurts, B neutral. Variant A has a prompt-level issue producing actively bad hints. | **PVD (A-harmful).** B works, A hurts. Do NOT average — this is not moderate signal. Flag; halt utility verdict until prompt-A failure mode identified. | **PVD (A-harmful, B-strong).** Maximum divergence. Halt verdict. Investigate A's prompt before any decision. |
| **Δ_B in [0, 5)** | **FAIL + HARMFUL (B).** Symmetric with row 1 col 2. | **FAIL.** Neither variant helps. Classification AND/OR both prompts don't deliver value to Sherpa. Further disambiguation requires inspecting hint content per task (out-of-scope for utility verdict). Do NOT scope-down — this is "no signal", not "harm". | **PVD (B-flat).** A moderate, B flat. If `D > 5 pts`, flag PVD and halt utility verdict. If `D ≤ 5`, still FAIL (no pass threshold met on either). | **PVD (B-flat, A-strong).** A works strongly, B flat. Flag PVD, halt verdict. |
| **Δ_A in [5, 10)** | **FAIL + HARMFUL (A).** Symmetric. | **PVD (A-flat).** Symmetric with row 2 col 3. | **SOFT PASS** iff `D ≤ 5` AND (`p_A < 0.10` OR `p_B < 0.10`). Else PVD flag. | **PVD (A-mod, B-strong).** Both improve but divergence > 5 pts likely. Flag. |
| **Δ_A ≥ 10** | **FAIL + HARMFUL (A-strong, B-harm).** Symmetric. | **PVD (A-strong, B-flat).** Symmetric. | **PVD (A-strong, B-mod).** Symmetric. | **PASS** iff `p_A < 0.05` AND `p_B < 0.05` AND `D ≤ 5 pts`. If `D > 5`, flag PVD and downgrade to SOFT PASS with caveat; halt if uncertain whether ≥10 pts on both is genuine. |

## Interpretation playbook

### If PASS (both variants ≥10 pts, p<0.05, D≤5)

Classification works. Both prompts work and agree. Lantern is earning its integration.

Proceed to L-13 (Sherpa integration touch).

### If SOFT PASS (mixed pass/soft/moderate, convergent within 5 pts)

Lantern has a signal. The prompts aren't maximally tuned, but the classification is doing real work.

Proceed to L-13 with caveat noting the soft tier; utility ADR documents which of the two prompts had the larger delta (informational only — not re-tuning).

### If FAIL without PVD (both variants flat, convergent)

Neither prompt delivered useful hints. Two candidate explanations:

1. **Classification-failure:** Lantern is picking the wrong shape (or assigning "unknown" too often), so hints are generic/irrelevant.
2. **Prompt-failure (symmetric):** Both prompts are phrased in ways that don't help Sherpa regardless of classification correctness. Cross-variant agreement suggests this is less likely than classification-failure.

Diagnostic: check the `shape_id` distribution in the 200 primed runs. If ≥50 % of runs produced `shape_id = "unknown"`, classification-staleness flag (§R4 `library-staleness-at-integration`) fires. Otherwise, treat as classification-failure — investigate per-shape-class pass rates.

**Do NOT scope-down**. Lantern stands as research artifact; Sherpa integration does not ship. L-13 commits a revert diff.

### If PVD (any variant divergence > 5 pts)

**Halt the utility verdict** per R0.5. The variance between prompts says we cannot attribute the aggregate signal cleanly to classification quality.

Triage options (operator decision, ADR-driven):

1. **Prompt-variant-disagreement ADR**: pick the working variant as canonical, demote the failing one to "prompt quality finding", continue to L-13 with canonical prompt only. Requires ADR because this is post-evidence prompt selection, which R0.5 was specifically designed to prevent.
2. **Re-author prompts**: admit both variants are flawed; draft v2 of both; re-run utility. Requires full re-run; expensive.
3. **Accept PVD as investigation outcome**: the axis being tested (terseness vs explicitness) itself influences Sherpa's executor in a way the rubric couldn't predict. Document as a finding about prompt-sensitivity; verdict remains HALTED on the utility test; Lantern ships as research artifact pending clearer prompts. L-13 reverts.

### If HARMFUL (any variant < 0 pts)

Lantern's hints actively degrade Sherpa's executor for that variant. This is the worst case.

**Scope-down immediately**: the hints are not just neutral, they cause regressions. Remove the hint layer from Sherpa's executor; commit revert diff; proceed to L-14 (audit) with verdict FAIL-HARMFUL.

This is distinct from the L-09 Methodology-D scope-down (which drops D but keeps A+B+C hints). A FAIL-HARMFUL verdict on utility means Lantern's `classify()` output should not be consumed by Sherpa at all — either drop the hints layer entirely, or revert Lantern integration.

## Edge cases

### Unknown-shape saturation

If ≥ 50 % of primed runs produced `LanternResult.shape_id = "unknown"` with `hints = []`:

- Primed-with-empty-hints ≈ blind (per LANTERN.md Part 6 Sherpa-side change: soft-fallthrough when hints is empty).
- `Δ_A` and `Δ_B` will be suppressed mechanically toward 0 regardless of prompt quality.
- Raise `HUMAN REVIEW: library-staleness-at-integration` (§R4).
- Utility verdict cannot be fairly computed under this saturation. Halt.
- This is a classification-surface problem (library is too sparse for the held-out sites), not a prompt-quality problem. Prompts are not at fault.

### L-12 corpus includes sites that were L-09-INDETERMINATE

Per ADR 0006, sites with N=0 produce empty fingerprints. Their `classify()` returns `shape_id = "unknown"`, `hints = []`. These cells contribute to unknown-shape saturation (above). If the L-12 corpus has too many such sites, the utility test can't evaluate Lantern fairly. Corpus composition for L-12 should be checked pre-run for N=0 incidence — but that's L-12 harness's concern, not this table's.

### Confidence threshold filtering

`classify()` returns `hints = []` when `confidence < 0.6`. This filter runs before hint generation, so low-confidence library matches contribute to the unknown-shape-saturation path above. The threshold is frozen in LANTERN.md Part 5 § Measurement Surface Freeze; no tuning in L-12.

## Cross-references

- R0.5 — dual prompt variants, prompt-variant-disagreement flag, decision table requirement
- LANTERN.md Part 5 § Utility criterion — base rubric (Pass / Soft Pass / Fail thresholds)
- LANTERN.md Part 5 § Hint-generation prompts as measurement surface — prompts pinned pre-utility
- BUILD.md §R4 — flag categories (`prompt-variant-disagreement`, `library-staleness-at-integration`)
- §R3 L-12 — utility harness ticket
- §R3 L-13 — Sherpa integration touch ticket
