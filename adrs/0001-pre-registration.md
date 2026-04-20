# ADR 0001 — Pre-registration revision bundle (R0.1–R0.6)

**Status:** Accepted
**Date:** 2026-04-20
**Pre-R0 LANTERN.md blob SHA:** `f03b78bd3bc295079bd01ce8a39bfbc891069b9b`
**Pre-R0 commit SHA:** `26b01f6` (`docs: initial LANTERN.md methodology spec`)
**Post-R0 commit SHA:** the commit this ADR lands in (`git log adrs/0001-pre-registration.md` resolves it)

## Context

LANTERN.md as committed at `26b01f6` passed an external pre-registration review. Six edits (R0.1–R0.6) were identified before any evidence touches the rubric. Applying them as a bundle, pre-evidence, preserves the frozen-measurement-surface invariant (BUILD.md §1.8) and produces a single reference point for post-evidence comparison: "was the rubric tuned post-hoc?" — answer: no, the rubric at L-05 onward is the rubric at this commit's blob SHA.

Two pre-build revisions (R0.0 and R0.0b) already landed against BUILD.md before this ADR — they resolved BUILD.md's internal `harness/` path ambiguity and added §R6.0's LANTERN.md presence gate. Those are BUILD-side process fixes; this ADR covers the spec-side revisions.

## Decision

Apply six revisions to LANTERN.md as a single bundled commit, plus this ADR. Commit message: `revision(R0): incorporate pre-registration review, freeze LANTERN.md`.

### R0.1 — Library is output of discrimination, not input

**Landing:** Part 4 § Step 6 (Shape library lookup).

**Change:** Leading paragraph stating the library does not exist prior to the discrimination test. First ~30 probes emit `shape_id="unknown"` by construction until clustering at L-07 bootstraps the library. No hand-authored seed shapes; no pre-seeded library carried across investigations.

**Rationale:** Prevents seed-shape overfitting. If seeds existed pre-discrimination, the classifier could "succeed" by classifying novel sites into a biased seed space — the utility test would be measuring seed quality, not Lantern's methodology. Making the bootstrapping explicit forces honesty about what's empirically justified vs authored-in.

### R0.2 — Poke-selection policy promoted to pinned measurement surface

**Landing:** Part 5 § Measurement Surface Freeze § Probe configuration (new bullet); Part 4 § Step 3 (cross-ref note added).

**Change:** The poke-selection policy (buttons in `<main>`, links in `<nav>` up to 10, first textbox in form, any `aria-haspopup`; dedup by `(role, accessible-name-hash, landmark)`) is added to the pinned measurement-surface list. Mid-investigation changes are rubric-drift events.

**Rationale:** Methodology D's output depends on which endpoints are poked. If poke-selection is an implementation detail subject to silent change, completeness-test results are not comparable across runs and cannot be audited. Pinning makes drift observable. Part 4 Step 3 keeps the operational description; Part 5 is the normative freeze.

### R0.3 — Discrimination clustering uses A+B+C only, excluding D

**Landing:** Part 5 § Pre-Registered Rubric § Discrimination criterion.

**Change:** Explicit statement that clustering operates on the A+B+C static fingerprint only; Methodology D's state-transition deltas are excluded from the distance metric used for clustering.

**Rationale:** Methodology D's output is what the Completeness criterion evaluates. If the Discrimination clustering used D's output, a cluster would be partly defined by the very thing Completeness is trying to measure — a circular pass. Excluding D from clustering keeps the two tests independent: Discrimination asks "are static shapes separable?" and Completeness asks "does D add value on top of that separation?" — two different questions, cleanly decoupled.

### R0.4 — Completeness refactored to per-shape-class, two-condition pass

**Landing:** Part 5 § Pre-Registered Rubric § Completeness criterion (full rewrite).

**Change:** The single uniform pass criterion is replaced with a per-shape-class, two-condition criterion. (i) On dynamic-interaction-heavy shape classes, the three-pass probe must discover ≥25% more focusable elements than single-pass on ≥70% of sites in that class. (ii) On static-content shape classes, the three-pass probe must produce ~0% delta (correct-null behavior). Pass requires both. Per-category reporting table is required alongside per-class.

The "~0%" threshold for condition (ii) is deferred to a pre-L-09 ADR, to be pinned before the completeness harness runs and frozen thereafter. Dynamic/static class labeling also happens post-discrimination, pre-completeness, as its own ADR.

**Rationale:** The original criterion treated all sites uniformly, but Methodology D's value proposition is asymmetric. On dynamic sites D should reveal state transitions; on static sites D should produce empty deltas. Conflating the two hides failures: a noisy D that produces spurious deltas on static content gets credit because it also finds real deltas on dynamic content. Per-class evaluation separates the two failure modes. Per-category reporting (redundant dimension) is how we observe compliance-pressure variance (R0.6) empirically.

### R0.5 — Dual pre-registered prompt variants for utility test

**Landing:** Part 5 § Pre-Registered Rubric § Utility criterion (full rewrite); Part 5 § Measurement Surface Freeze § Hint-generation prompts (retitled); Part 4 § Step 7 (cross-ref); Part 6 § Async timeline step 6; Part 7 § build scaffold tree; Part 7 § First commit order step 14.

**Change:** Two pre-registered prompt variants (terse vs explicit) differing on a single pre-declared axis. Both authored at L-10, committed to `lantern/prompts/hint_generation_terse.md` and `lantern/prompts/hint_generation_explicit.md` before any utility-harness data collection. Decision table for disambiguating prompt-failure from classification-failure committed alongside.

Utility test expands from 40 runs (20 tasks × 10 sites × 2 conditions) to **80 runs** (× 2 variants). McNemar paired test is run per variant. New failure mode: prompt-variant disagreement >5 points = classification/prompt cannot be disambiguated, halts utility verdict.

Note: this ADR does not author the prompt variants. Authoring happens at L-10 per BUILD.md §R3, once discrimination clusters are available. The two `.md` files referenced in Part 7's scaffold tree are placeholders until L-10.

**Rationale:** A single prompt confounds prompt-failure and classification-failure. If Lantern-primed Sherpa underperforms blind Sherpa, is `shape_id` wrong, or are the hints badly phrased? Two variants differing on a known axis (terse vs explicit) let us triangulate: both variants fail → classification suspect; variants disagree → prompt/task-interaction suspect. The decision table makes this triangulation pre-registered rather than post-hoc.

### R0.6 — Compliance pressure varies by category (explicit expectation)

**Landing:** Part 1 § Epistemic Foundation.

**Change:** New paragraph stating compliance pressure varies across site types: consumer-facing commercial sites (Shopify, airlines, publishers) typically honest under WCAG litigation risk; legacy SaaS, internal tools, indie-web sites have substantial accessibility gaps. The per-category Completeness reporting (R0.4 requirement) is the instrument for observing this variance empirically.

**Rationale:** Part 1's original framing presented the a11y tree as uniformly honest across the web. That is true as a legal obligation but not uniform as practice. Writing the expected variance into Part 1 prevents post-hoc rationalization ("well obviously legacy SaaS is different") when a class shows lower completeness. Pre-declaring the expectation means the per-category table becomes a confirmation of a prior rather than a discovery of a convenient narrative.

## Consequences

- LANTERN.md is frozen at the post-R0 blob SHA. Further changes require a new ADR and a new `revision(R0.N+k): ...` or `contracts(group-X): freeze` commit per BUILD.md §1.4.
- Part 4 § Step 3's poke-selection policy is now a measurement surface. Its parameters (buttons-in-main, nav-link-cap=10, textbox-first, any-aria-haspopup, dedup key) cannot change without rubric-drift handling.
- L-09 scope expands: in addition to the delta-comparison harness, L-09 requires a pre-run ADR pinning both (a) the "~0%" operational threshold for condition (ii) and (b) the dynamic/static class labels assigned to each discrimination cluster.
- L-10 scope expands: two prompt files plus a decision table, all committed before any utility-harness data collection.
- L-12 scope expands: 80 runs instead of 40; McNemar per variant; prompt-variant disagreement check against decision table; new flag condition (`prompt-variant-disagreement`) per BUILD.md §R4.
- The "Poke-selection policy" bullet in Part 5 Measurement Surface Freeze is now duplicated between Part 4 Step 3 (operational description) and Part 5 (normative freeze). Any future change must land in both places — ADR-required.

## Confidence labels

- Content of R0.1–R0.6 edits: **KNOWN** — applied verbatim from the pre-registration review directives.
- Cross-section cascade (Part 4 Step 3/6/7, Part 6 async timeline, Part 7 scaffold tree, Part 7 first-commit-order step 14): **KNOWN** — changes follow mechanically from R0.1–R0.6's scope.
- Rationale for each revision: **MODELED** — reconstruction of why each edit matters; the operator's pre-registration review document is the ground truth.
- Operational threshold for "~0%" in R0.4 condition (ii): **UNKNOWN** — explicitly deferred to a pre-L-09 ADR.
- Dynamic-heavy vs static-content class labels: **UNKNOWN** at R0 — derived from L-07 discrimination clusters, labeled in a pre-L-09 ADR.
- Prompt variant contents: **UNKNOWN** at R0 — authored at L-10 per BUILD.md §R3.

## Pre/post snapshots

- Pre-R0 LANTERN.md blob SHA: `f03b78bd3bc295079bd01ce8a39bfbc891069b9b`
- Pre-R0 commit: `26b01f6`
- Post-R0 commit and blob: resolvable via `git log adrs/0001-pre-registration.md` and `git rev-parse HEAD:LANTERN.md` after this commit lands.
