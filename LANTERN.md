# Lantern

**Probe-Based Schema Inference for Undocumented Web Surfaces — as Sherpa's Upstream Module**

---

## 0. What this is

A single-file spec covering:
1. **Epistemic foundation** — why this works at all
2. **The REST-API reframing** — what Lantern is actually doing
3. **The four synthesized methodologies** — named, scoped, and how they compose
4. **Shape construction** — descriptive, step-by-step, how a fingerprint becomes a shape
5. **The Cairn investigation** — pre-registered rubric, measurement surface freeze
6. **Sherpa integration contract** — async development, single call site
7. **Build scaffold** — directory, modules, commit order, anti-drift rules

Frozen before evidence. Changes after step 1 of the build are rubric-drift events and must be documented.

---

# Part 1 — Epistemic Foundation

Lantern works because of one structural fact about the modern web:

**Sites cannot hide their real interaction surface from screen readers without breaking accessibility compliance.**

Every interactive element a sighted user can reach must also be reachable via keyboard navigation and semantically described via ARIA roles and states. This is enforced by:

- WCAG 2.1 AA as a legal requirement in many jurisdictions (US ADA, EU EAA, Section 508)
- Commercial lawsuit risk driving compliance on large surfaces
- Framework defaults (React, Vue, Angular) emitting semantic HTML by default
- Screen-reader testing as part of standard QA on enterprise sites

Consequence: **the accessibility tree is the least-hidden, most-honest representation of a site's interaction surface.** CSS lies about layout. JavaScript hides implementation. The DOM has ten flavors of div-based widget. But the a11y tree must expose the real thing, because blind users depend on it.

Lantern reads the a11y tree because that's where sites are structurally obligated to tell the truth about themselves.

**But compliance pressure is not uniform across the web (R0.6).** Consumer-facing commercial sites — Shopify shops, airline checkouts, major publishers — face real WCAG litigation risk and are typically honest. Legacy SaaS, internal enterprise tools, and indie-web sites face less legal pressure and tend to have substantial accessibility gaps: divs-with-onclick widgets, missing ARIA relationships, inconsistent landmarks. Lantern reads the same a11y tree on both, but the signal is cleaner on the former. The per-category Completeness reporting requirement (Part 5) is how we observe this variance empirically — rather than assuming it or dismissing it.

This is also why the methodology is low-overhead: we're not parsing, rendering, or reverse-engineering. We're reading a representation the browser has already computed and that the site is legally compelled to keep accurate.

---

# Part 2 — The Web as Undocumented REST API

The unifying thesis that ties every methodology below together:

**A website is a poorly documented, large, stateful REST API where the "endpoints" are interactive elements, the "parameters" are form fields and selectors, and the "response schemas" are the state transitions that happen after interaction. Lantern is a probe-based schema inference system for these undocumented surfaces.**

Traditional API discovery has OpenAPI specs, Swagger docs, Postman collections. Websites have none of that — but they do have structural obligations (Part 1) that expose enough signal to *infer* the spec. Lantern infers it.

Map of API concepts to web concepts:

| REST API concept | Web equivalent | What Lantern uses to infer it |
|------------------|----------------|-------------------------------|
| Service identification | Site class (e-commerce, SaaS, news) | Shape fingerprint (Methodology A) |
| Endpoint discovery | What's clickable/interactive | Tab traversal (Methodology B) |
| Parameter discovery | What inputs belong to what action | Focus-event instrumentation + ARIA relationships (Methodology C) |
| Response schema | What changes after interaction | State-change rescanning (Methodology D) |

Every methodology below is one of these four inference moves. Named explicitly so we know what we're composing.

---

# Part 3 — The Four Synthesized Methodologies

## Methodology A — Shape Fingerprinting *(service identification)*

**What it answers:** What kind of site is this? Which known shape class does it belong to?

**What it consumes:** A single tab traversal of the entry page, yielding an ordered list of focused elements with role + state + landmark.

**What it produces:** A canonical fingerprint (ordered role-state-landmark tuple sequence) that can be compared against a library of known shapes via Levenshtein distance on role sequence.

**Why it's cheap:** One browser session, one pass, no interaction. Terminates in seconds.

**Why it's sufficient for classification:** Most sites follow template patterns (Part 1 convergent-shapes thesis). A header-nav-main-footer layout with a product grid is an e-commerce product listing whether it's Shopify, BigCommerce, or custom. The role-sequence fingerprint captures the bone structure and ignores the cosmetic variation.

## Methodology B — Tab-Order Endpoint Discovery *(endpoint discovery)*

**What it answers:** What are all the interactable elements on this page, in what semantic order?

**What it consumes:** Repeated `Tab` keypresses via Playwright, each followed by an accessibility snapshot of the currently focused element.

**What it produces:** An ordered graph of focusable elements. Tab advances forward, Shift+Tab reverses — the two together validate that the ordering is consistent and catch dynamic insertions.

**Why it beats DOM crawling:** Most modern sites have five to ten times more DOM nodes than interactive elements. The DOM is full of layout divs, decorative spans, and framework-emitted containers. Tab order is a filter: it returns only what's *actually* a button, link, control, or focusable custom widget. This is the single biggest overhead reduction in the whole methodology.

**Why it beats CSS-selector enumeration:** Tab order already respects `tabindex`, visibility, disabled state, and display rules. We don't have to re-implement focusability heuristics. The browser has already done it.

**The caveat from Part 1:** elements implemented as divs with JS click handlers and no `tabindex` are invisible to this method. That's a real gap. It also means these elements are invisible to keyboard users and screen readers, i.e. they're accessibility bugs. For well-built sites the gap is small; for badly-built sites we flag the site as low-confidence and fall through.

## Methodology C — Focus-Event + ARIA Relationship Probing *(parameter discovery)*

**What it answers:** Given an endpoint (interactive element), what parameters belong to it? What inputs, selectors, and sub-controls are grouped with it?

**What it consumes:**
1. Focus-event listeners attached during traversal to catch lazy-loaded or hover-revealed elements that only become focusable after interaction
2. ARIA relationship attributes on focused elements: `aria-labelledby`, `aria-describedby`, `aria-controls`, `aria-owns`, `aria-activedescendant`
3. `data-*` attributes as fallback grouping signal
4. `getComputedStyle` snapshots for layout-grid grouping (controls that share a parent layout region likely belong together)

**What it produces:** A grouping map — for each primary endpoint, the set of parameter controls associated with it. For a product page's "Add to Cart" button, this includes color selector, size selector, quantity input, and (if present) the round-up-donation checkbox that only appears after size is chosen.

**Why it's necessary:** Tab order alone gives you a flat sequence. Parameter discovery requires *grouping*: knowing that the "Large" radio button is a parameter of the product form, not a standalone choice. ARIA relational attributes are how well-built sites encode this grouping, and they're designed to be read programmatically.

**The layout-grid assist:** When ARIA relationships are missing or ambiguous, `getComputedStyle` gives you spatial grouping for free. Controls inside the same `<form>` with the same computed parent grid area are almost certainly parameters of the same endpoint. This catches grouping cases where the markup isn't ARIA-perfect but the layout is coherent.

## Methodology D — State-Change Rescanning *(response schema inference)*

**What it answers:** When an interaction happens, what changes? What new endpoints and parameters become available?

**What it consumes:** A three-pass protocol:
1. **Scan** — full Methodology B tab traversal of the initial page state, Methodology C grouping
2. **Poke** — programmatic interaction with one endpoint (click, select, focus) chosen by policy
3. **Rescan** — re-run Methodology B + C, diff against the pre-poke snapshot

**What it produces:** A state transition record: "clicking the product card revealed these five new focusable elements in this grouping." This is the response schema for that endpoint.

**Why this is the missing piece:** Methodologies A–C give you the *static* surface. Real web interactions are stateful. The donation-round-up button only appears after you add to cart. The size selector is disabled until you pick a color. The shipping-option radio group doesn't render until an address is entered. Without rescanning after interaction, Lantern would miss every element that lives behind a state transition — which is most of the interesting ones.

**Three-pass protocol, made explicit:**

- Pass 1 (Scan): tab-traverse the page in its initial state. Emit fingerprint F₀.
- Pass 2 (Poke): select the first primary endpoint by policy (first button in `<main>`, first link in primary nav, etc.). Interact. Wait for page to settle (`networkidle + 2000ms`). Capture URL and DOM mutation summary.
- Pass 3 (Rescan): tab-traverse again. Emit fingerprint F₁. Compute delta = F₁ \ F₀ = the elements that appeared as a result of the poke. These are the response schema for that endpoint.

Repeat for each primary endpoint in the initial fingerprint. The union of deltas is the site's state-transition graph.

**Why this is capped:** Full state-space exploration is exponential. Lantern caps pokes at the primary endpoints from the initial fingerprint (not the rescanned ones), which keeps cost linear in initial endpoints. Deeper exploration is a follow-on investigation.

## How the four compose

```
       Methodology A (Shape Fingerprinting)
                   │
                   ▼
    Methodology B (Tab-Order Endpoint Discovery)
                   │
                   ▼
Methodology C (Focus-Event + ARIA Relationship Probing)
                   │
                   ▼
    Methodology D (State-Change Rescanning)
                   │
                   ▼
        LanternResult → Sherpa executor
```

A is upstream of B because knowing the shape class tells B which endpoints matter most (for an e-commerce shape, product-variant controls are high-priority pokes; for SaaS dashboard, primary-nav controls are).

B is upstream of C because grouping requires a set of focusable elements to group.

C is upstream of D because knowing parameter groups tells D which interactions are worth poking (poke primary endpoints, not every focusable element).

D feeds back into A: state-transition deltas become part of the richer fingerprint for shape classification. A site whose product endpoint reveals a color/size/donation pattern *is* an e-commerce product page with higher confidence than one whose fingerprint only matches statically.

---

# Part 4 — Shape Construction

This section is descriptive and step-by-step: given a URL, how does Lantern construct a shape?

## Step 0 — Probe environment setup

- Launch Playwright with Chromium, headless, pinned version
- Set user-agent from pinned list (Desktop Chrome on macOS for primary probe)
- Set viewport to 1440×900
- Clear cookies and localStorage if `session_state="fresh"`; load pre-warmed state from prior anonymous visit if `session_state="warm"`
- Navigate to URL
- Wait for `networkidle` + 2000ms settle
- Inject a focus-event listener that records every `focus` event globally, including elements that weren't focusable at page-ready time

## Step 1 — Initial scan (Methodology B)

Starting with focus on `document.body`, send `Tab` keypresses in a loop. After each press:

1. Query the currently focused element via `document.activeElement` + accessibility tree lookup (Chromium DevTools Protocol `Accessibility.getFullAXTree` or equivalent)
2. Extract the following fields:
   - **role** — ARIA role, or computed role from tag name. Unknown roles → `generic`.
   - **accessible_name** — computed accessible name, truncated to 64 chars, lowercased. Stripped from fingerprint but retained in sidecar.
   - **state_bitmap** — 8-bit field encoding: `expanded` | `haspopup` | `selected` | `checked` | `disabled` | `required` | `invalid` | `readonly`. 0 for unset. **Field names are the canonical lowercase form (R0.7);** `lantern/vocab.py` is the single normalization boundary that maps CDP's actual property names — which may be camelCase (e.g., CDP surfaces `hasPopup` for `aria-haspopup` per L-SPIKE-02 finding) — to this canonical form on ingest. See ADR 0004.
   - **landmark** — nearest ancestor landmark element: `main`, `nav`, `header`, `footer`, `aside`, or `none`.
   - **tag_name** — HTML tag, for sidecar only.
3. Append the `(role, state_bitmap, landmark)` tuple to the fingerprint.
4. Append the full record (including name and tag) to the sidecar.

Continue until either:
- Focus returns to `document.body` (full cycle complete), or
- 200 focusable elements have been captured (cap), or
- 30 seconds have elapsed since scan start (timeout)

## Step 2 — Grouping analysis (Methodology C)

For each focused element in the scan, extract:

- `aria-labelledby` → ID references → resolve to other focused elements → mark as label relationship
- `aria-describedby` → same treatment → description relationship
- `aria-controls` → same → control relationship (this element controls that one)
- `aria-owns` → same → ownership relationship (this element owns that one as a virtual child)
- `aria-activedescendant` → same → active-descendant relationship (for composite widgets)
- Nearest `<form>` ancestor → form-membership relationship
- `getComputedStyle` grid/flex parent — elements sharing the same computed layout container → spatial-grouping relationship

Build a relationship graph: nodes are focused elements, edges are typed relationships. This graph is the grouping map.

## Step 3 — Poke selection (Methodology D setup)

*(This policy is pinned as a measurement surface per R0.2 — see Part 5 § Measurement Surface Freeze § Probe configuration. Mid-investigation changes are rubric-drift events.)*

From the initial fingerprint, select primary endpoints to poke. Policy:

- All elements with role `button` inside `main`
- All elements with role `link` inside `nav` landmark (up to 10, in tab order)
- The first element with role `textbox` inside a form (to probe form revelation behavior)
- Any element with `aria-haspopup` set (these are known state-revealers)

Deduplicate: if two elements have identical role + accessible-name-hash + landmark, poke only one.

## Step 4 — Poke and rescan (Methodology D execution)

For each selected endpoint:

1. Snapshot current URL and compute a DOM size summary (node count)
2. Focus the endpoint
3. Dispatch a click (or `Enter` keypress for links, or `Space` for checkboxes/buttons)
4. Wait for `networkidle` + 2000ms settle, capped at 8 seconds total
5. Check for URL change:
   - If URL changed → this endpoint is a navigation endpoint. Record destination URL. Do not rescan (that's a new page; out of scope for this site's shape). Navigate back.
   - If URL unchanged → this endpoint is a state-transition endpoint. Proceed to rescan.
6. Re-run Step 1 (tab traversal) to produce fingerprint F₁
7. Compute `delta = F₁ \ F₀` — tuples present in F₁ but absent in F₀ at matching positions
8. Record the delta as the response schema for this endpoint
9. Re-run Step 2 grouping analysis on F₁ to catch newly-revealed parameter groups
10. Reset page state: reload URL, restore session_state, return to step 1 of poke loop for the next endpoint

## Step 5 — Shape assembly

The complete shape is now:

```
Shape := {
    static_fingerprint: F₀,
    static_groupings: [group₁, group₂, ...],
    state_transitions: {
        endpoint₁: {kind: "navigation", destination_url: "..."},
        endpoint₂: {kind: "state_change", delta: [...], new_groupings: [...]},
        endpoint₃: {kind: "no_change"},
        ...
    },
    sidecar: {
        names: [...],  // accessible names, for hint generation
        tags: [...],   // tag names, for debugging
        probe_metadata: {url, session_state, user_agent, elapsed_ms}
    }
}
```

## Step 6 — Shape library lookup (Methodology A application)

**The library does not exist prior to the discrimination test (R0.1).** It is the *output* of the discrimination test — see Part 5 § Discrimination criterion. During the stability and discrimination phases, the first ~30 probes run without a library to compare against and emit `shape_id="unknown"` by construction. Clustering at L-07 bootstraps the library from those 30 probes. No hand-authored seed shapes; no pre-seeded library carried across investigations.

Once the library exists, compute distance from this shape to each shape in the library:

- Primary distance: Levenshtein on the `static_fingerprint` role-sequence
- Secondary distance (tiebreak): Jaccard on the set of state-transition endpoint kinds
- Tertiary (further tiebreak): size-of-delta signatures on state-transition shapes

Find nearest library shape. `confidence = 1 - (nearest_distance / max_observed_distance_in_library)`.

If `confidence >= 0.6` (tunable, frozen at investigation start): assign `shape_id` = nearest library shape's ID.
If `confidence < 0.6`: assign `shape_id = "unknown"`. Record as candidate for library expansion (out-of-band).

## Step 7 — Hint generation

If `shape_id != "unknown"` and `confidence >= 0.6`:

Call the hint-generation LLM with one of the two pre-registered prompt variants (R0.5) — see Part 5 § Utility criterion for variant definitions. During the utility investigation, both variants are run per task for comparison; production runtime uses a single selected variant (selection policy pinned at L-11). Inputs to the prompt:
- `shape_id` and its canonical description from the library
- The new shape's sidecar (names, tags)
- The new shape's state_transitions summary
- The task Sherpa is about to execute (optional — passed through if available)

The LLM returns up to 5 natural-language hints, each ≤40 tokens. Examples:
- "Primary product variant controls appear in the `<form>` inside `<main>`; expect size and color selectors."
- "Add-to-cart triggers a state change revealing shipping and donation controls; watch for modal overlay."
- "Primary nav contains 6 category links; product-specific content is under the third link in tab order."

## Step 8 — Return LanternResult

```python
LanternResult(
    shape_id=shape_id,
    confidence=confidence,
    hints=hints,
    fingerprint_hash=sha256(canonical(F₀)),
    elapsed_ms=total_probe_time,
)
```

---

# Part 5 — Cairn Investigation

## Investigation Question

**Does the composed four-methodology probe produce stable, discriminative site-shape classifications that correlate with Sherpa executor success rate?**

Four sub-questions — one added from the prior revision because the REST-API framing requires it:

1. **STABILITY** — does the same site produce the same shape across repeated visits, user-agents, and session states?
2. **DISCRIMINATION** — do different sites produce different shapes, and do similar sites produce similar shapes?
3. **COMPLETENESS** *(new)* — does the three-pass probe (Methodology D) catch state-revealed elements that a single-pass probe misses? This is the falsifiable claim about Methodology D being necessary, not just nice-to-have.
4. **UTILITY** — does Sherpa perform better with Lantern hints than blind?

## Pre-Registered Rubric (commit before evidence)

### Stability criterion

10 sites × 5 visits × 2 user-agents × 2 session states = 200 probes. Primary metric: Levenshtein on static_fingerprint role-sequence.

- **Pass:** within-site distance <20% of mean cross-site at 95th percentile
- **Soft pass:** 20–40%, document session-state as required input
- **Fail:** >40%, investigation stops

### Discrimination criterion

30 sites × 1 full probe across 6 categories (5 each): e-commerce, news, SaaS dashboard, marketing landing, forum/social, misc. Hierarchical agglomerative clustering on primary distance with secondary tiebreak.

**Clustering uses the A+B+C static fingerprint only (R0.3).** Methodology D's output (state-transition deltas) is excluded from the distance computation used for clustering. This prevents circularity between shape classification and Methodology D's completeness evaluation — if D's output fed clustering, a cluster would be partly defined by the very thing Completeness is trying to measure.

- **Pass:** 4–8 clusters emerge, category-majority >70%
- **Soft pass:** 3 or 9–12 clusters, category-majority 50–70%
- **Fail:** 1–2 or >12 clusters, category-majority <50%

### Completeness criterion *(new, refactored per R0.4)*

Same 30 discrimination sites. Run each twice: once with Methodology A+B only (single-pass static), once with full A+B+C+D (three-pass). Compare the set of focusable elements discovered per run.

**Pass is per-shape-class, two-condition — both conditions must hold.**

Shape classes are derived from discrimination clusters (§ Discrimination criterion). Each cluster is labeled as either **dynamic-interaction-heavy** (e.g., e-commerce product page, SaaS dashboard with modals, interactive forum thread) or **static-content** (e.g., news article, marketing landing without interactive widgets). Dynamic/static labeling happens once, post-discrimination and pre-completeness-harness, committed as an ADR. Changes thereafter are rubric-drift events.

- **Condition (i) — dynamic classes:** the three-pass probe discovers ≥25% more distinct focusable elements than single-pass on ≥70% of sites within that class. Evaluated independently per dynamic class.
- **Condition (ii) — static classes:** the three-pass probe produces ~0% delta — this is the correct-null behavior. Spurious state-transition elements on static content indicate Methodology D is noisy. The operational threshold for "~0%" is pinned in a pre-L-09 ADR (before the completeness harness runs) and frozen thereafter.

**Pass:** both (i) and (ii) hold across all evaluated shape classes.
**Soft pass:** (i) is met on some but not all dynamic classes, OR (ii) is marginally violated (documented exceptions, small-magnitude). Keep Methodology D, flag findings.
**Fail:** (i) fails on all dynamic classes (Methodology D not earning its cost) OR (ii) fails broadly (Methodology D generates false deltas on static content). Scope down to A+B+C if (i) fails; investigate separately if only (ii) fails.

**Reporting requirement (R0.4):** results are published as two tables — per-shape-class AND per-category. Per-category reporting is how we observe compliance-pressure variance by site type (Part 1 / R0.6). Neither table is optional.

This criterion is what justifies the extra cost of the three-pass protocol. If the class-aware pass fails, Lantern scopes down to A+B+C only (Methodology D dropped).

### Utility criterion *(dual-variant per R0.5)*

20 Sherpa tasks × 10 held-out sites × 2 conditions (blind vs Lantern-primed) × **2 prompt variants** = 80 runs. McNemar paired test run independently per variant (blind vs primed).

**Prompt variants (pre-registered, authored at L-10):**
- **Variant A — terse:** minimal framing, short hints, relies on Sherpa's base prompt for structure
- **Variant B — explicit:** explicit scaffolding, labeled sections, more verbose hints

The two variants differ on one pre-declared axis: **terseness vs explicitness**. The axis can only change with documented justification as a rubric-drift event. Both variants are committed to `lantern/prompts/` before any utility-harness data collection. A **decision table** for disambiguating prompt-failure (a variant is bad) from classification-failure (Lantern's `shape_id` is wrong) is committed alongside the prompts and applied to the utility results.

- **Pass:** ≥10 point pass-rate improvement on **both** variants, p<0.05
- **Soft pass:** 5–10 point improvement on one or both variants, or p<0.10
- **Fail:** no improvement or degradation on both variants
- **Prompt-variant disagreement (>5 points between variants):** flagged; decision table applied; classification-vs-prompt cannot be disambiguated without further investigation (halts the utility verdict pending resolution)

### Investigation verdict mapping

| Stability | Discrimination | Completeness | Utility | Verdict |
|-----------|---------------|--------------|---------|---------|
| Pass | Pass | Pass | Pass | Full Lantern justified |
| Pass | Pass | Fail | Pass | Scope down: ship without Methodology D |
| Pass | Pass | Pass | Fail | Research artifact only; not justified for Sherpa |
| Pass | Fail | — | — | Thesis partially survives; Lantern-as-probe-library but no classifier |
| Fail | — | — | — | Investigation stops |

## Measurement Surface Freeze

### Probe configuration (pinned before data collection)

- Browser: Playwright + Chromium, pinned version in `pyproject.toml`
- User-agents: Desktop Chrome macOS, Mobile Safari iOS, pinned strings
- Session states: `fresh` (incognito) vs `warm` (pre-warmed anonymous cookies)
- Tab depth cap: 200 per traversal
- Page-ready: `networkidle + 2000ms`
- Role vocabulary: WAI-ARIA 1.2, unknown → `generic`
- State bitmap: 8 fields as enumerated in Part 4 Step 1
- Confidence threshold for shape assignment: 0.6
- Poke timeout: 8s total per poke
- Hint count cap: 5, each ≤40 tokens
- Distance: Levenshtein primary, Jaccard secondary, size-of-delta tertiary
- **Poke-selection policy (pinned per R0.2):** from each probe's initial fingerprint, poke (a) all elements with role `button` inside `main`, (b) all elements with role `link` inside `nav` landmark (up to 10, in tab order), (c) the first element with role `textbox` inside a form, (d) any element with `aria-haspopup` set. Dedup by `(role, accessible-name-hash, landmark)`. Mid-investigation changes are rubric-drift events.

### Hint-generation prompts as measurement surface *(R0.5)*

The two pre-registered hint-generation prompt variants (Part 4 Step 7; variant definitions in § Utility criterion above) are drafted **after discrimination clusters emerge** (so the prompts know what shape classes exist) and **before any utility run** (so utility-run results don't retroactively tune the prompts). Both variants committed to `lantern/prompts/hint_generation_terse.md` and `lantern/prompts/hint_generation_explicit.md`. A decision table distinguishing prompt-failure from classification-failure is committed alongside the prompt files. Post-hoc prompt quality concerns are findings, not drift justifications.

### Sherpa integration surface (pinned for utility test)

- Entry point: `lantern.classify(url, session_state) -> LanternResult`
- Hints prepended under `## Site shape context` header
- Blind baseline: Sherpa executor with no Lantern call, no header section
- Primed: same executor, only difference is prepended hints
- Temperature, model, max_tokens: pinned to Sherpa's production values, recorded in harness

## Out of Scope

- Persistent production library (investigation uses ephemeral in-memory)
- Deep-link navigation beyond entry page (Methodology D recurses one level only)
- Authenticated surfaces beyond anonymous signup
- Shape-change detection over time (snapshot only)
- Mobile-native apps
- Full state-space exploration beyond primary endpoints

## Deliverables

1. Harness code — probe, fingerprint, clustering, completeness comparator, utility comparator
2. Data artifacts — 200 stability fingerprints, 30 discrimination shapes, 30 completeness pairs, 40 Sherpa runs
3. Findings document with rubric scorecard
4. ADR: proceed / scope down / halt

Rate this investigation design before starting step 1.

---

# Part 6 — Sherpa Integration Contract

## Async development principle

Lantern and Sherpa build independently. Single contract, single call site.

## Contract

```python
# lantern/api.py
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class LanternResult:
    shape_id: str
    confidence: float
    hints: list[str]
    fingerprint_hash: str
    elapsed_ms: int

def classify(
    url: str,
    session_state: Literal["fresh", "warm"] = "fresh",
    timeout_ms: int = 8000,
) -> LanternResult: ...
```

## Sherpa-side change

```python
# sherpa/executor.py
def execute_task(url: str, task: str, ...):
    lantern_result = None
    try:
        lantern_result = lantern.classify(url, session_state="warm")
    except Exception as e:
        log.warning("lantern classify failed, proceeding blind", exc_info=e)

    system_prompt = build_base_system_prompt(...)
    if lantern_result and lantern_result.hints:
        system_prompt += "\n\n## Site shape context\n"
        system_prompt += f"Shape: {lantern_result.shape_id} "
        system_prompt += f"(confidence {lantern_result.confidence:.2f})\n"
        for hint in lantern_result.hints:
            system_prompt += f"- {hint}\n"
```

Soft-fallthrough on any failure. No regression risk.

## Reserved channels (future, not in investigation scope)

1. **Fingerprint-keyed episodic memory.** Shape_id becomes the key for Sherpa's trajectory memory. A workflow learned on one Shopify store generalizes to all shops matching that shape.
2. **Shape-aware re-observation policy.** Sherpa's observer loop behavior parameterized by shape class. E-commerce shapes expect variant-selector mutations; SaaS shapes expect modal overlays.
3. **State-transition-graph-aware planning.** Methodology D's output is literally a graph of what-leads-to-what. A future Sherpa planner can consume this as an action-space prior.

## Async timeline

**Lantern track** (no Sherpa dependency):
1. Harness + probe (Playwright, a11y tree, tab traversal)
2. Stability test + report
3. Discrimination test + report
4. Completeness test + report
5. Library seeded from discrimination clusters
6. Hint-generation prompt variants (terse + explicit) and decision table authored + committed (per R0.5)
7. `classify()` API surface
8. Pip-packaged with pinned Playwright

**Sherpa track** runs independently throughout.

**Integration touch** (~1 day):
- Add call site + prompt section to Sherpa
- Run utility test
- ADR, merge or revert

## Failure modes protected against

- Lantern slow/broken: timeout + exception → blind execution, no regression
- Bad hints: utility test catches, revert is two-line diff
- Library staleness: confidence threshold drops low-confidence noise
- Novel sites: `shape_id="unknown"`, `hints=[]`, blind execution

## What the contract does NOT do

- Does not alter Sherpa's trigger grammar, retry policy, or observer loop
- Does not allow Sherpa to update Lantern's library mid-run
- Does not share state between runs; each classify() is stateless

---

# Part 7 — Build Scaffold

```
lantern/
├── pyproject.toml                 # pinned Playwright, Python version
├── README.md
├── LANTERN.md                     # this file (frozen)
│
├── lantern/                       # package
│   ├── __init__.py
│   ├── api.py                     # classify() + LanternResult
│   ├── probe.py                   # Playwright harness, tab traversal, a11y dump
│   ├── fingerprint.py             # role-sequence + state-bitmap (Methodology A)
│   ├── endpoints.py               # tab-order endpoint discovery (Methodology B)
│   ├── grouping.py                # ARIA + layout grouping (Methodology C)
│   ├── rescan.py                  # three-pass state-change protocol (Methodology D)
│   ├── distance.py                # Levenshtein, Jaccard, size-of-delta
│   ├── library.py                 # pattern library + nearest-neighbor lookup
│   ├── hints.py                   # LLM-backed hint generation
│   ├── prompts/
│   │   ├── hint_generation_terse.md      # variant A (pre-registered per R0.5)
│   │   ├── hint_generation_explicit.md   # variant B (pre-registered per R0.5)
│   │   └── DECISION_TABLE.md             # prompt-failure vs classification-failure (R0.5)
│   └── vocab.py                   # WAI-ARIA roles, state-bitmap encoding, landmarks
│
├── harness/                       # investigation harness, NOT shipped
│   ├── sites_stability.yaml       # 10 stability sites
│   ├── sites_discrimination.yaml  # 30 discrimination sites, 6 categories × 5
│   ├── tasks_utility.yaml         # 20 Sherpa tasks across 10 held-out sites
│   ├── run_stability.py
│   ├── run_discrimination.py
│   ├── run_completeness.py        # new: single-pass vs three-pass comparison
│   ├── run_utility.py
│   └── report.py                  # scorecard against pre-registered rubric
│
├── data/                          # gitignored
│   ├── fingerprints/
│   ├── clusters/
│   ├── completeness_pairs/
│   └── utility_runs/
│
└── tests/
    ├── test_probe.py
    ├── test_fingerprint.py
    ├── test_endpoints.py
    ├── test_grouping.py
    ├── test_rescan.py
    ├── test_distance.py
    ├── test_library.py
    └── fixtures/                  # static HTML pages for deterministic tests
```

## Module responsibilities

**`lantern.probe`** — Playwright orchestration. Loads URL, manages browser state, injects focus-event listeners, coordinates the three-pass protocol.

**`lantern.fingerprint`** *(Methodology A)* — Pure function. Probe records → canonical fingerprint tuple sequence.

**`lantern.endpoints`** *(Methodology B)* — Tab-order traversal executor. Returns ordered list of focusable elements with captured fields.

**`lantern.grouping`** *(Methodology C)* — ARIA + layout grouping analyzer. Takes endpoints list + DOM snapshot, returns relationship graph.

**`lantern.rescan`** *(Methodology D)* — Three-pass state-change protocol. Poke policy, diff computation, state-transition recording.

**`lantern.distance`** — Pure metric functions, property-tested.

**`lantern.library`** — Pattern library, nearest-neighbor lookup. Seeded from discrimination clusters. Out-of-band updates only.

**`lantern.hints`** — LLM call with frozen prompt. Returns up to 5 hints.

**`lantern.api`** — Public surface orchestrator. Runs all four methodologies in sequence, handles timeouts and exceptions.

## Test strategy

- **Unit tests:** fingerprint determinism on fixture HTML; distance metric properties; grouping correctness on ARIA-annotated fixtures; rescan diff correctness on fixtures with known state transitions.
- **Integration tests:** full `classify()` pipeline on fixture pages served via local HTTP fixture server. No public-web dependency in CI.
- **Investigation tests:** `harness/run_*.py` — manual, produce reports.

## What NOT to do during investigation

- **Do not optimize.** Correctness before performance.
- **Do not generalize the library schema** until discrimination test tells us what shapes exist.
- **Do not build UI, dashboard, CLI ergonomics.** `classify()` is the entire public surface.
- **Do not tune hint-generation prompt based on utility results.** Rubric drift.
- **Do not expand scope mid-investigation.** Interesting follow-ons get documented as future investigations.
- **Do not skip the Completeness test.** It is the single strongest falsifiable claim in this investigation — that Methodology D is necessary, not ornamental. Skipping it would let the three-pass protocol survive on aesthetic grounds.

## First commit order

1. `pyproject.toml`, `README.md`, freeze `LANTERN.md`
2. `lantern/vocab.py` + `lantern/fingerprint.py` + fingerprint tests on synthetic a11y input
3. `lantern/distance.py` + distance property tests
4. `lantern/endpoints.py` + tests against fixture HTML (no Playwright yet)
5. `lantern/grouping.py` + tests against ARIA-annotated fixtures
6. `lantern/probe.py` — first Playwright integration, tested against local fixture server
7. `harness/run_stability.py` — first real data touches the rubric
8. Stability report. Proceed or halt.
9. If stability passes: `harness/run_discrimination.py`, library bootstrap
10. Discrimination report. Proceed or halt.
11. `lantern/rescan.py` + tests
12. `harness/run_completeness.py` — justify or drop Methodology D
13. Completeness report. Proceed with full Lantern or scope-down to A+B+C.
14. `lantern/prompts/hint_generation_terse.md` + `lantern/prompts/hint_generation_explicit.md` + decision table authored and committed (per R0.5)
15. `lantern/hints.py` + `lantern/api.py`
16. `harness/run_utility.py` on Sherpa integration
17. Utility report, ADR, integration touch, merge or revert

Each numbered step is a commit boundary with a pass/fail against the frozen rubric. No step skips ahead.
