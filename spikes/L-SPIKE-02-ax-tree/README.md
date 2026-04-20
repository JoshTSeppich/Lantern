# L-SPIKE-02 — CDP `Accessibility.getFullAXTree` coverage

**Status:** 🚩 **RED — HALT AND FLAG**
**Date:** 2026-04-20
**Playwright (pinned, per BUILD.md §R1.2):** `1.58.0`
**Chromium build (via `playwright install chromium`):** Chrome Headless Shell 145.0.7632.6 (playwright chromium-headless-shell v1208)
**Python:** 3.12.13 (uv-managed)

---

## Why this spike ran first (severity × probability rationale)

L-SPIKE-02 was ranked ahead of L-SPIKE-04 (operator's prior) because **severity dominates when probability is comparable**.

|  | L-SPIKE-02 (AX tree) | L-SPIKE-04 (mutation observer + settlement) |
|---|---|---|
| Downstream blocks | `fingerprint.py` **and** `grouping.py` | `rescan.py` only |
| Scope-down path | **None** — A+B+C fingerprint is the backbone of every later phase | Architected: L-09 condition (i) failure → drop Methodology D, ship A+B+C |
| Failure mode | Silent data-shape mismatch → degraded fingerprint → unreliable clustering | Noisy/unreliable deltas → caught by L-09 correct-null condition |
| Probability of a surprise | Moderate — AX tree is mature CDP surface but ARIA-state property names have known casing/taxonomy drift | High — timing heuristics are fragile by nature |

L-SPIKE-04 is **more likely to surprise**, but L-SPIKE-02 being wrong is **more expensive** — the thesis leans on the A+B+C static fingerprint and there is no graceful scope-down. Severity as tiebreaker → run L-SPIKE-02 first so any shape mismatch is found before fingerprint.py and grouping.py start.

That prior was validated by this spike's outcome: a shape mismatch was indeed found (see below). Running second would have meant discovering it after fingerprint.py was already wired in — exactly the expensive-rework scenario the re-rank was meant to prevent.

---

## Scope

Per BUILD.md §R3 L-SPIKE-02 + operator directive 2026-04-20:

- **(A) State-bitmap coverage.** Verify CDP's `Accessibility.getFullAXTree` surfaces each of the **eight** state-bitmap fields enumerated in LANTERN.md Part 4 Step 1 individually: `expanded | haspopup | selected | checked | disabled | required | invalid | readonly`. At least one fixture element per field; native and ARIA forms tested where applicable.
- **(B) Landmark coverage.** Verify all **five** HTML-tag landmarks from Part 4 Step 1 (`main / nav / header / footer / aside`) appear in the AX tree with the expected AX role.
- **(C) Landmark ancestry traversal.** For one ID'd descendant per landmark, walk `parentId` upward and confirm the expected landmark AX-role appears in the ancestor chain.

Halt condition (user-specified): any field missing, any shape different from what Part 4 Step 1 assumes → halt; flag as state-bitmap contract break; require ADR + refreeze before `fingerprint.py` begins.

This is the gate for `lantern/fingerprint.py` (Methodology A) and `lantern/grouping.py` (Methodology C). Both remain blocked.

## Results

AX tree size for the fixture: **131 nodes**, of which **24 fixture-ID'd elements** resolved to AX nodes.

### Claim B — landmark coverage: ✅ **KNOWN (5/5)**

| HTML tag | Fixture DOM id | Expected AX role | Actual AX role | Ignored? |
|---|---|---|---|---|
| `<main>`   | `#main-content` | `main`          | `main`          | no |
| `<nav>`    | `#primary-nav`  | `navigation`    | `navigation`    | no |
| `<header>` | `#page-header`  | `banner`        | `banner`        | no |
| `<footer>` | `#page-footer`  | `contentinfo`   | `contentinfo`   | no |
| `<aside>`  | `#sidebar`      | `complementary` | `complementary` | no |

The HTML-tag → AX-role mapping is the standard WAI-ARIA mapping (mature, stable). `fingerprint.py` will normalize AX-role back to the Part 4 Step 1 HTML-tag vocabulary using this mapping.

### Claim C — ancestry traversal: ✅ **KNOWN (5/5)**

Each ID'd descendant's `parentId` chain contained the expected landmark AX role within ≤ 10 hops:

| Descendant | Landmark (HTML) | Expected ancestor role | Status |
|---|---|---|---|
| `#main-heading`   | `<main>`   | `main`          | found |
| `#nav-link-1`     | `<nav>`    | `navigation`    | found |
| `#banner-heading` | `<header>` | `banner`        | found |
| `#sidebar-para`   | `<aside>`  | `complementary` | found |
| `#footer-para`    | `<footer>` | `contentinfo`   | found |

### Claim A — state-bitmap coverage: ⚠️ **7/8 KNOWN, 1/8 MISMATCH**

| Part 4 Step 1 field | Surfaced? | Property name CDP returned | Example element | Example value |
|---|---|---|---|---|
| `expanded` | KNOWN | `expanded` | `#state-expanded`         | `True`   |
| **`haspopup`** | **MISMATCH** | **`hasPopup` (camelCase)** | `#state-haspopup` | (see below) |
| `selected` | KNOWN | `selected` | `#state-selected`         | `True`   |
| `checked`  | KNOWN | `checked`  | `#state-checked-native`   | `'true'` (tristate-as-string) |
| `disabled` | KNOWN | `disabled` | `#state-disabled-native`  | `True`   |
| `required` | KNOWN | `required` | `#state-required-native`  | `True`   |
| `invalid`  | KNOWN | `invalid`  | `#state-invalid`          | `'true'` (token-as-string) |
| `readonly` | KNOWN | `readonly` | `#state-readonly-native`  | `True`   |

All eight states' *data* is present in CDP's AX tree. For seven fields the property name matches Part 4 Step 1 exactly. For `haspopup`, **CDP uses `hasPopup` (camelCase) while Part 4 Step 1 enumerates `haspopup` (lowercase).** This is a shape difference, not a coverage gap.

Secondary observation: `checked` and `invalid` return string values (`'true'`) where Part 4 Step 1's "8-bit field encoding: 0 for unset" wording implies boolean. This is a tristate/token-vs-boolean distinction that `fingerprint.py` will need to normalize (truthiness-collapse), but the **property name** matches in both cases — that concern is implementation-internal, not a contract break.

---

## Halt rationale & required ADR

Per operator directive (2026-04-20): "If CDP returns partial coverage **or different field shapes** than Part 4 Step 1 assumes, halt and flag — that's a state-bitmap contract break requiring ADR + refreeze before fingerprint.py begins."

Casing (`haspopup` vs `hasPopup`) qualifies as a different field shape. The coverage itself is complete — the data is there — but the property *name* the contract enumerates does not match the name CDP returns. Silently lowercasing in `fingerprint.py` would be one valid resolution, but choosing it implicitly (rather than via ADR) is exactly the "silent drift" §1.4 and §R7 prohibit.

### Decision required: pick one path via ADR 0004 (proposed)

**Option A — normalize in code, keep Part 4 Step 1 as-is.**
- `fingerprint.py` / `vocab.py` lowercases every AX property name before bitmap-lookup.
- ADR explicitly authorizes this normalization as the state-bitmap matching strategy.
- Part 4 Step 1 is unchanged.
- Pro: Part 4 Step 1 stays clean / human-readable.
- Con: the normalization is a bridge that must hold for *every* AX property we ever care about; future fields (e.g., `selected` → if CDP ever surfaces `Selected`) are covered automatically but the bridge is an invisible dependency.

**Option B — refreeze Part 4 Step 1 to match CDP's exact casing.**
- LANTERN.md Part 4 Step 1 changes: `haspopup` → `hasPopup`.
- `vocab.py` encodes property names verbatim as CDP returns them.
- Pro: no normalization layer; contract matches reality 1:1.
- Con: Part 4 Step 1 mixes cases (`expanded`, `hasPopup`, `selected`, …) which reads inconsistently. Other CDP properties outside our bitmap may surface in inconsistent casing too.

**Option C — refreeze Part 4 Step 1 to a stricter mapping table.**
- Part 4 Step 1 replaces the 8 lowercase names with an explicit `{our_bitmap_name: cdp_property_name}` mapping.
- `vocab.py` encodes the mapping.
- Pro: every case-mismatch is documented in Part 4 Step 1 itself; future fields that CDP adds with weird casing get an explicit row, not an implicit lowercase bridge.
- Con: more verbose in Part 4 Step 1.

My reading favors **Option A** on simplicity grounds (lowercase-on-ingest is the kind of normalization we'd want anyway for robustness against future CDP camelCase additions), but this is an operator decision per §R7. Do not select an option in code before the ADR is committed.

---

## What this spike does NOT verify (out of scope / deferred)

- **The full CDP property vocabulary.** Only the 8 state-bitmap fields and 5 landmark roles were checked. Other CDP properties (`focusable`, `focused`, `editable`, `atomic`, `live`, `keyshortcuts`, etc.) are visible in `spike_results.json` but not validated against any contract. LANTERN.md does not claim them.
- **Value-type normalization.** `checked` and `invalid` return string tokens where Part 4 Step 1's "0 for unset" wording implies boolean. Truthiness collapse will be `fingerprint.py`'s responsibility; not tested here.
- **AX tree across dynamic state changes.** The spike reads the tree once on a static fixture. State-change behavior is L-SPIKE-04's domain.
- **Role vocabulary beyond landmarks.** WAI-ARIA 1.2 has ~80 roles; this spike verifies only the 5 landmark roles. L-01's vocab.py tests will cover the full vocabulary against a broader fixture.
- **Non-ID'd AX nodes.** 131 total AX nodes existed; only the 24 nodes with resolvable DOM `id` attributes were cross-referenced. Decoy/layout nodes were not individually audited; they don't affect the fingerprint.

## Downstream — currently BLOCKED

- `lantern/fingerprint.py` (Methodology A) — blocked until ADR resolves the `haspopup`/`hasPopup` mismatch.
- `lantern/grouping.py` (Methodology C) — blocked on L-SPIKE-03 (computed-style cost) + this spike's resolution.
- `lantern/vocab.py` — blocked; encodes the state-bitmap contract, which is the thing that needs to refreeze (or not) per the ADR decision.

## How to re-run

```bash
uv run python spikes/L-SPIKE-02-ax-tree/spike.py
```

Exit code 0 = GREEN, 1 = RED (current state).

## Re-verification triggers (per BUILD.md §R1.2)

- `playwright` version bump
- Chromium binary change affecting CDP AX semantics (in particular, any change to the `Accessibility` domain's property-name casing)
- `fixture.html` edit
- ADR 0004 landing — this spike must re-run against the post-ADR contract to confirm the chosen resolution matches reality

## Artifacts

- `fixture.html` — 20+ elements spanning 8 state fields × multiple forms and 5 landmarks with ID'd descendants
- `spike.py` — CDP spike; exits 0=GREEN / 1=RED
- `spike_results.json` — machine-readable full output (all state fields, all landmarks, all ancestry chains, all CDP property names surfaced per fixture-ID'd node)
- `README.md` — this document

## Flag raised

🚩 **`HUMAN REVIEW: state-bitmap-contract-break`** (BUILD.md §R4 category, narrowing "rubric-drift" to the state-bitmap specifically)

- **Finding:** CDP surfaces `hasPopup` (camelCase) for `aria-haspopup`; Part 4 Step 1 enumerates `haspopup` (lowercase). 7/8 other state fields match Part 4 Step 1 exactly. Data is present; shape differs.
- **Consequence:** `fingerprint.py` and `grouping.py` cannot begin. ADR 0004 must select between Option A (normalize in code), Option B (refreeze field name), or Option C (refreeze to explicit mapping table).
- **Not improvised:** no code change was made to "work around" this; the halt is the deliverable per §1.6 and §R7.
