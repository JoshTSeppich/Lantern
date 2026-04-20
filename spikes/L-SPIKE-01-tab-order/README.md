# L-SPIKE-01 — Tab order + `document.activeElement`

**Status:** GREEN
**Date:** 2026-04-20
**Playwright version (pinned, per BUILD.md §R1.2):** `1.58.0`
**Chromium build (via `playwright install chromium`):** Chrome Headless Shell 145.0.7632.6 (playwright chromium-headless-shell v1208)
**Python:** 3.12.13 (uv-managed)

## Scope

Per BUILD.md §R3 L-SPIKE-01, verify that:

1. Playwright `page.keyboard.press('Tab')` produces a **deterministic** focus traversal on a fixture page with 20 focusable elements of varying types (button, link, input, custom widget with `tabindex`).
2. `document.activeElement` **always resolves** after each Tab press.
3. **Full-cycle termination is detectable** by returning to `document.body` or by element-already-seen detection.

This is the gate for `lantern/endpoints.py` (Methodology B). The module can begin implementation once this spike is green.

## Fixture

`fixture.html` exposes:

- **20 focusable elements** with stable IDs `focusable-01` through `focusable-20`, spanning:
  - 4 links (`<a href>`) — `focusable-01`, `focusable-02`, `focusable-16`, `focusable-17`
  - 5 buttons (`<button>`) — `focusable-03`, `focusable-04`, `focusable-18`, `focusable-20`, and one `<input type="submit">` at `focusable-19`
  - 6 form inputs of varied types — `text`, `password`, `email`, `number`, `checkbox`, `radio` (`focusable-05` through `focusable-10`)
  - `<select>` at `focusable-11`
  - `<textarea>` at `focusable-12`
  - 3 custom widgets with `tabindex="0"` — `role="button"`, `role="combobox"` (with `aria-haspopup`), and a plain `<span tabindex="0">` (`focusable-13`, `focusable-14`, `focusable-15`)
- **4 non-focusable decoys** that should be skipped by Tab:
  - `<button disabled>`
  - `<div tabindex="-1">`
  - a plain `<div>` with no tabindex
  - decoys are labeled `.decoy` in the stylesheet for visual inspection

Landmarks (`nav`, `main`, `footer`) and form grouping are present so the fixture also exercises semantics relevant to future spikes (L-SPIKE-02 AX tree) — but those are not in scope here.

## Method

`spike.py`:

1. Launch Playwright Chromium headless, viewport 1440×900.
2. For each of 3 passes:
   - Open a new page, `goto(file://.../fixture.html)`, wait for `networkidle`.
   - Focus `document.body` explicitly to start from a known state.
   - Press `Tab` up to 50 times. After each press, read `document.activeElement` via `page.evaluate(...)` and record `(tag, id, role, aria-label, type, tabindex, text-snippet)`.
   - Terminate the pass when either: (a) `activeElement` returns to `document.body`, or (b) an element key is re-encountered.
3. Compare the three passes pairwise for deterministic ordering. Check every Tab press produced a non-null active element. Check each pass terminated via one of the two detection modes.
4. Write `spike_results.json` and exit 0 (GREEN) or 1 (RED).

## Results — verified claims (KNOWN)

All three passes produced the identical sequence:

| Press | activeElement.id |
|-------|-------------------|
| 1  | `focusable-01` |
| 2  | `focusable-02` |
| … | … |
| 20 | `focusable-20` |
| 21 | *(body — termination)* |

### Claim 1 — **KNOWN** — Tab order is deterministic

Three passes produced three identical sequences of 20 unique focusable elements in DOM order (`focusable-01` → `focusable-20`). No observed non-determinism.

### Claim 2 — **KNOWN** — `document.activeElement` always resolves

Across 3 passes × up to 50 Tab presses, every read of `document.activeElement` returned a non-null element descriptor. `any_null_active` was `False` for all passes.

### Claim 3 — **KNOWN** — Full-cycle termination is detectable

All three passes terminated via **body-return** on Tab 21 (one press past the last focusable element). In this fixture, body-return fires before element-already-seen would — meaning:

- **Primary termination signal:** body-return (`document.activeElement.tagName === 'body'`)
- **Fallback signal:** element-already-seen (kept in `spike.py` logic for defensive coverage against hypothetical sites where Tab does not wrap to body)

In all three passes `cycle_detected_at_press` was `None` because the primary signal fired first. This is expected in Chromium with well-formed fixtures; the fallback remains armed for real-world sites.

## Scope boundaries — what this spike does NOT verify

Labeled MODELED or UNKNOWN per BUILD.md §1.2. These are not failures of the spike; they are explicit out-of-scope items.

- **Shift+Tab (reverse traversal):** MODELED. LANTERN.md Part 3 Methodology B mentions Shift+Tab as a consistency check. Not verified here; will be exercised when `endpoints.py` tests run or in a follow-on spike if needed.
- **Non-Chromium browsers:** UNKNOWN. Lantern is pinned to Chromium per LANTERN.md Part 4 Step 0; no cross-browser verification planned.
- **Real-world site behavior:** MODELED. Fixture is hermetic and well-formed. Sites with infinite-loop Tab handlers, focus-trapping modals, or dynamic focusable-element insertion mid-traversal are covered by the MAX_TABS safety cap + the element-already-seen fallback, but not verified against live examples.
- **Tab behavior under `tabindex` > 0:** MODELED. Fixture uses only `tabindex="0"` and `tabindex="-1"`; positive `tabindex` values (which re-order the sequence) are not in the fixture. LANTERN.md does not treat positive tabindex as a measurement surface — the a11y tree orders what the browser orders.

## How to re-run

From repo root:

```bash
uv run playwright install chromium    # one-time
uv run python spikes/L-SPIKE-01-tab-order/spike.py
```

Exit code 0 = GREEN, 1 = RED. Console summary printed; detailed results in `spike_results.json`.

## Re-verification triggers (per BUILD.md §R1.2)

Re-run this spike and re-commit its artifacts when **any** of:

- `playwright` version in `pyproject.toml` changes (bump requires ADR)
- Chromium binary bundled by Playwright changes in a way that affects keyboard event handling
- `fixture.html` is modified (the fixture is part of the spike's measurement surface)

## Downstream consumers

- **`lantern/endpoints.py`** (Methodology B) — gated by this spike.
- **`lantern/probe.py`** (L-05) — depends on the tab-order primitive verified here.
- **`tests/test_endpoints.py`** — will reuse this fixture (or variants of it) for module-level tests.

## Artifacts

- `fixture.html` — 20-focusable + 4-decoy test page
- `spike.py` — verification script
- `spike_results.json` — machine-readable results from the GREEN run
- `README.md` — this document
