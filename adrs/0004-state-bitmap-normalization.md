# ADR 0004 — State-bitmap normalization boundary (Option A + annotation amendment)

**Status:** Accepted
**Date:** 2026-04-20
**Triggered by:** L-SPIKE-02 RED finding (`hasPopup` vs `haspopup` shape mismatch). See `spikes/L-SPIKE-02-ax-tree/README.md`.
**Blocks resolved:** `lantern/vocab.py`, `lantern/fingerprint.py`, `lantern/grouping.py` (L-01, L-04 gate cleared once R0.7 + freeze land).

## Context

L-SPIKE-02 verified that CDP's `Accessibility.getFullAXTree` surfaces all 8 state-bitmap fields named in LANTERN.md Part 4 Step 1 — but for one field (`haspopup` / `aria-haspopup`), CDP returns the property under the camelCase name `hasPopup`. The other 7 fields (`expanded`, `selected`, `checked`, `disabled`, `required`, `invalid`, `readonly`) match Part 4 Step 1's lowercase names exactly.

Per operator directive 2026-04-20, different field shapes halt and flag. L-SPIKE-02 committed RED at `9492e89` and did not improvise a workaround. This ADR resolves the halt.

A secondary observation from L-SPIKE-02 (not individually halting but relevant here): CDP surfaces some fields' *values* as tristate/token strings (`'true'` for `checked` on `<input type="checkbox" checked>`, `'true'` for `invalid` on `aria-invalid="true"`) rather than booleans. Part 4 Step 1's "0 for unset" wording implies a boolean → 0/1 projection. Value normalization (truthiness collapse) is already `fingerprint.py`'s responsibility; its normalization surface overlaps with whatever name-normalization we choose here.

## Options considered

### Option A — normalize AX property names on ingest in vocab.py; Part 4 Step 1 contract unchanged except for an annotation

- `lantern/vocab.py` defines the canonical 8-name lowercase bitmap.
- `lantern/vocab.py` also defines (and owns) a normalization function: `normalize_ax_property_name(cdp_name: str) -> str | None` that lowercases the CDP property name and returns the canonical name if it matches the bitmap, else `None`.
- `fingerprint.py` feeds every AX property through `vocab.normalize_ax_property_name(...)` before bitmap-lookup.
- Part 4 Step 1 gets a one-sentence annotation (per the operator's amendment) explicitly naming `vocab.py` as the normalization boundary.

**Pros:**
- One normalization surface (`vocab.py`) owns both name-casing normalization and the value-truthiness collapse already required for `checked`/`invalid`. Adding name normalization alongside value normalization is nearly free.
- Part 4 Step 1 stays human-readable (all lowercase, no inconsistent casing).
- Future camelCase drifts from CDP (e.g., if a future Chromium renames `selected` → `Selected`) are automatically caught by the lowercase-on-ingest normalization — no spec edit needed.
- The annotation makes the normalization layer *visible* in Part 4 Step 1 itself, preventing the "silent bridge" failure mode (§1.6).

**Cons:**
- The normalization is a bridge whose correctness depends on the assumption that lowercasing resolves all case ambiguity. If CDP ever surfaces a property whose lowercase form *collides* with a different bitmap field (e.g., hypothetical `HasPopup` and `hasPopup` with different semantics — not currently the case), lowercase would conflate them. Low probability but not zero.
- One more piece of code to test.

### Option B — refreeze Part 4 Step 1 to match CDP's exact casing (`haspopup` → `hasPopup`)

- Part 4 Step 1 changes `haspopup` to `hasPopup` in the field enumeration.
- `vocab.py` encodes all 8 property names verbatim as CDP returns them.
- No lowercase-on-ingest normalization needed for names.

**Pros:**
- Contract matches CDP 1:1. No bridge.

**Cons:**
- Part 4 Step 1 mixes cases: `expanded`, `hasPopup`, `selected`, `checked`, `disabled`, `required`, `invalid`, `readonly`. Reads inconsistently.
- The 1:1-match argument partially collapses under scrutiny: CDP's *values* don't match 1:1 either (tristate tokens vs booleans). We'll normalize values regardless. Adding name normalization alongside is free. Claiming "no bridge" only narrows "bridge" to the name axis.
- If a *future* Chromium adds another camelCase field (say, `Selected` with a capital S in some edge case, or `aria-*` → camelCase property translations), Part 4 Step 1 needs another edit + refreeze every time. This is a drift trigger that will keep firing.

### Option C — refreeze Part 4 Step 1 as an explicit `{bitmap_name: cdp_property_name}` mapping table

- Part 4 Step 1 replaces the 8 lowercase names with a two-column table.
- `vocab.py` encodes the table and uses the CDP column as the source-of-truth for ingestion.

**Pros:**
- Every CDP/canonical-name mismatch is documented in Part 4 Step 1 itself, not in `vocab.py`.
- Future camelCase discoveries get explicit rows, not implicit lowercase bridges. Strongest insurance against Unknown Unknowns.

**Cons:**
- More verbose in Part 4 Step 1.
- Today, only 1 of 8 fields needs a non-identity mapping — 7/8 rows would be `{x: x}`. Insurance premium for one actual mismatch.

## Decision

**Option A + annotation amendment** (operator decision, 2026-04-20):

1. `lantern/vocab.py` is the single normalization boundary. It lowercases CDP property names on ingest, maps them to the canonical 8-name lowercase bitmap, and truthiness-collapses tristate/token values to the 0/1 bitmap bit at the same boundary.
2. LANTERN.md Part 4 Step 1 keeps the 8 canonical lowercase field names in its enumeration, and gains a one-sentence annotation naming `vocab.py` as the normalization boundary and citing this ADR and L-SPIKE-02.
3. `fingerprint.py` calls `vocab.normalize_ax_property_name(...)` — never accesses CDP-raw property names directly.

Applied via `revision(R0.7)` commit (Part 4 Step 1 annotation) + `contracts(state-bitmap): re-freeze` (clarification-freeze; contract *shape* did not change, but the normalization boundary is now explicit).

## Rationale bundle (operator-stated)

1. **`fingerprint.py` already has to normalize values** (CDP's tristate tokens for `checked` / `invalid` per L-SPIKE-02 secondary observation) — adding name normalization alongside value normalization is nearly free. The `vocab.py` normalization boundary becomes the single place any CDP-to-canonical-form bridge lives, whether for names or values.
2. **Option B's "match CDP 1:1" argument partially collapses** because *values* don't match 1:1 either. Choosing B would give the appearance of 1:1-ness along the name axis while still carrying a value-normalization bridge elsewhere. That would be worse than Option A, not better — it would spread normalization across multiple surfaces instead of concentrating it.
3. **Option C's mapping table is insurance against the spike's UNKNOWN** about other camelCase fields ("Whether other CDP properties outside our 8-field bitmap have similar camelCase drift" — explicitly flagged UNKNOWN in L-SPIKE-02's README). But the annotation amendment gives equivalent protection by making `vocab.py` the single named boundary where all such drifts land. Future discoveries are code changes in `vocab.py`, not spec edits to Part 4 Step 1. This keeps the spec stable while keeping the insurance.
4. **Revisit threshold:** if future bitmap expansion surfaces **three or more** camelCase drifts (i.e., three or more bitmap fields whose CDP name differs from the canonical lowercase form beyond simple lowercasing — e.g., `ariaSomething` or a re-ordered stem), re-evaluate and likely refactor to Option C. At 3+, the mapping-table verbosity starts earning its insurance premium and the "lowercase is sufficient" assumption is no longer defensible. Until then, Option A holds.

## Consequences

- L-SPIKE-02 halt is resolved; the spike's RED state remains committed at `9492e89` as the evidence trail. L-SPIKE-02 is NOT re-run after this ADR — the spike's findings are the input to the ADR, not output of it. If ever re-run (e.g., on Playwright bump), the RED finding is expected to reproduce (CDP still returns `hasPopup`); the pass/fail verdict of the spike can be updated post-L-01 to treat the mismatch as KNOWN-and-normalized rather than a halt, but that is a follow-on concern.
- `lantern/vocab.py` now has a defined scope: (a) canonical 8-name lowercase bitmap, (b) `normalize_ax_property_name(cdp_name) -> canonical | None`, (c) value-truthiness collapse for tristate/token values, (d) WAI-ARIA 1.2 role vocabulary and landmark HTML-tag → AX-role mapping (pre-existing).
- `lantern/fingerprint.py` must not access CDP-raw property names directly — it must route through `vocab.py`. This is testable: `tests/test_fingerprint.py` should include a regression test with a synthetic AX tree containing `hasPopup` and confirm the resulting bitmap has the haspopup bit set.
- L-01 (vocab.py + fingerprint.py) is unblocked. L-04 (grouping.py) remains gated on L-SPIKE-03.
- Part 4 Step 1's contract *shape* did not change — the 8-name enumeration is the same, the 0-for-unset encoding is the same. What changed is: the normalization boundary between CDP's raw output and the canonical bitmap is now explicitly named. Therefore the freeze that follows is a clarification-freeze, not a drift-freeze.
- Revisit trigger documented above (3+ camelCase drifts → refactor to Option C).

## Confidence labels

- L-SPIKE-02's direct observation of `hasPopup` vs `haspopup`: **KNOWN**
- 7/8 other state fields matching lowercase: **KNOWN**
- Option A resolving the mismatch via lowercase-on-ingest: **KNOWN** (trivial transformation, testable)
- Behavior of Option A on hypothetical future camelCase drifts: **MODELED** (assumes lowercasing resolves all ambiguity; defensible today, not guaranteed forever — hence the revisit threshold)
- Whether other CDP properties we *haven't* exercised have similar drift: **UNKNOWN** (L-SPIKE-02 scope-bounded to 8 fields; the normalization boundary is designed to absorb these if/when found)
- Value-truthiness collapse for `checked`/`invalid`: **MODELED** (L-SPIKE-02 observed the string values; collapse rule will be `bool(str_val in {"true", "mixed"})` or similar, pinned when `vocab.py` lands in L-01)

## Cross-references

- L-SPIKE-02 spike and README: `spikes/L-SPIKE-02-ax-tree/`
- R0.7 annotation commit: the commit this ADR lands in
- Freeze commit: follows R0.7, empty commit `contracts(state-bitmap): re-freeze`
- Applies to tickets: L-01 (vocab.py, fingerprint.py), L-04 (grouping.py), L-03 (endpoints.py — no state-bitmap dependency but shares the normalization boundary via vocab.py)
