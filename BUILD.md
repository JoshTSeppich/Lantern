# Lantern — Build Contract (v1, cairn-explicit)

Claude Opus 4.7 in Claude Code, 1M context. You are building **Lantern** — a probe-based schema inference system for undocumented web surfaces that plugs into Foxworks Sherpa as an upstream classifier.

Lantern is a separate repo from Sherpa. It is developed asynchronous to Sherpa's harden sequence. The two integrate at a single contract boundary, specified in §R2.

This document inherits the verification methodology from `cairn` (verification-driven agentic coding). All cairn primitives that apply to this build are listed in §C0 and made enforceable in the body of this document. Re-read §C0 and §1 before every new ticket.

The canonical spec for Lantern's methodology is `LANTERN.md` (attached). This build contract governs *how* Lantern gets built. The methodology spec governs *what* Lantern does. If the two conflict, the build contract wins on process questions; the methodology spec wins on thesis questions. Flag any conflict before resolving.

---

## §R0 — Pre-build revision gate

Before Step 1 of any ticket, incorporate the six revision edits from the pre-registration review into `LANTERN.md`. These are not optional; they are the outcome of the investigation design review and must land in the frozen methodology before any data touches it.

**R0.1** — Part 4 Step 6: add explicit paragraph stating "the library does not exist prior to the discrimination test. It is the output of the discrimination test. First 30 probes emit shape_id='unknown' until clustering completes. No hand-authored seed shapes."

**R0.2** — Part 5 Measurement Surface Freeze: promote poke-selection policy from Part 4 Step 3 implementation detail to pinned measurement surface. State it cannot change mid-investigation without being logged as a rubric-drift event.

**R0.3** — Part 5 Discrimination criterion: state explicitly that clustering uses A+B+C static fingerprint only, excluding Methodology D output. This prevents circularity between shape classification and D's completeness evaluation.

**R0.4** — Part 5 Completeness criterion: refactor to per-shape-class, two-condition pass criterion. (i) On dynamic-interaction-heavy shape classes, D discovers ≥25% more focusable elements than single-pass on ≥70% of sites in that class. (ii) On static-content shape classes, D produces ~0% delta (correct-null behavior). Pass requires both. Per-category result table is a reporting requirement alongside per-class.

**R0.5** — Part 5 Utility criterion: pre-register two frozen prompt variants for hint generation, differing on a pre-declared axis (terseness vs explicitness by default; change only with justification). Both variants authored before utility runs, both committed to `lantern/prompts/`. Utility test runs against both. Decision table for disambiguating prompt-failure from classification-failure is committed alongside prompt variants.

**R0.6** — Part 1 or Part 5 (your call which fits better): add explicit expectation that compliance pressure varies by site category. Consumer-facing commercial sites are mostly honest; legacy SaaS, internal tools, and indie-web sites have substantial gaps. Per-category Completeness reporting is how we observe this.

Commit: `revision(R0): incorporate pre-registration review, freeze LANTERN.md`

After R0.1–R0.6 land and `LANTERN.md` is frozen, proceed to §C0 and §1. Do not start any probe work before R0 is committed.

---

## §C0 — Cairn primitives invoked

**Tier 3 build.** Full scaffold. The justification follows.

### Tier 3 justification

Lantern meets three Tier 3 triggers from the cairn rubric:

1. **Multiple novel primitives.** Tab-order traversal via Playwright, full AX-tree extraction via CDP, three-pass state-change protocol, role-sequence Levenshtein fingerprinting, LLM-backed hint generation. None of these exist in the Foxworks codebase. Multiple unverified surfaces compose in a single pipeline.
2. **Bleeding-edge APIs.** Playwright's accessibility snapshot API and CDP's `Accessibility.getFullAXTree` are both evolving surfaces. Training data is stale. Spikes are mandatory before any pipeline integration.
3. **Reputation-risk via Sherpa integration.** If Lantern ships bad hints to Sherpa, Sherpa's executor pass rate degrades — visible to users, visible to your own harden-sequence metrics. The utility test is where this risk surfaces; failure mode protection (soft-fallthrough, confidence threshold, revert diff) is mandatory.

If you find yourself relaxing any Tier 3 primitive ("we don't really need a spike for `Accessibility.getFullAXTree`, the docs are clear"), stop. The tier was set deliberately. Under-scaffolding a Tier 3 build is the most expensive mistake you can make in this codebase.

### Primitives enforced

| Primitive | Enforcement |
|---|---|
| Anti-fabrication | §1.1, every external API gets a spike before pipeline integration |
| Confidence labels | §1.2, every commit, every ADR, KNOWN/MODELED/UNKNOWN |
| TDD literal with commit grammar | §1.3 |
| Frozen contracts | §1.4, `LanternResult` and all inter-module boundaries frozen before spike |
| Verification dashboard | §1.5, live during investigation phases |
| Flag-don't-improvise | §1.6 |
| Self-checks before commit | §1.7, seven questions required |
| Stop when done | §1.8 |

### Self-check block (mandatory in every commit)

```
Self-check:
1. Is the API I called verified by a spike in this repo? [yes/no/n/a]
2. Does my test exercise behavior, or my mocks? [behavior/mocks/mixed]
3. If implementation deleted, would test still pass? [yes/no]
4. Did I add anything outside the ticket's acceptance criteria? [yes/no]
5. Did a contract drift without a freeze commit? [yes/no]
6. Is any claim in my commit body unlabeled? [yes/no]
7. Did I tune any frozen measurement-surface element post-evidence? [yes/no]
```

Commit without Self-check block → rejected.
Any "yes" on questions 4, 5, or 7 → rejected, revert and flag.

---

## §1 — Invariants

### 1.1 — Anti-fabrication

No pipeline integration before the underlying primitive is verified by a spike in *this* repo against the *pinned* Playwright version. Specifically:

- **L-SPIKE-01** — Playwright `page.keyboard.press('Tab')` + `document.activeElement` readback on a local fixture page. Verify: tab order is deterministic, `activeElement` is always reachable, full-cycle termination is detectable.
- **L-SPIKE-02** — CDP `Accessibility.getFullAXTree` against a fixture page with known ARIA roles, states, and landmarks. Verify: role vocabulary coverage, state-attribute extraction, landmark ancestry traversal.
- **L-SPIKE-03** — `getComputedStyle` snapshot cost per focused element. Verify: computing styles for 200 elements stays under 2 seconds total.
- **L-SPIKE-04** — Mutation-observer-based state-change detection after a synthetic click. Verify: we can reliably distinguish "page settled after state change" from "page in transition."

No methodology module (fingerprint.py, endpoints.py, grouping.py, rescan.py) integrates until its spike is green.

### 1.2 — Confidence labels

KNOWN (verified by spike or property test in this repo), MODELED (inferred from docs, not yet verified in this repo), UNKNOWN (not inferable without further investigation).

UNKNOWN code does not reach green. If you catch yourself at UNKNOWN during implementation, revert and spike.

### 1.3 — TDD literal, with commit grammar

```
spike(L-SPIKE-NN): <what was verified, against which API>
contracts(group-X): freeze
red(L-NN): <failing behavior>
green(L-NN): <minimum implementation to pass>
refactor(L-NN): <only after green, no scope creep>
adr(L-NN): <decision record if pipeline shape changed>
revision(R0.N): <revision from pre-registration review>
```

Tests written before implementation. No "I'll write the test after I see what the code does." No exceptions.

### 1.4 — Frozen contracts

The following are frozen before any spike touches them:

- `LanternResult` (Part 6 of `LANTERN.md`). Frozen dataclass, `@dataclass(frozen=True)`.
- `ProbeRecord` — raw probe output format, zod-equivalent schema (Python: pydantic).
- `Shape` — Part 4 Step 5 structure.
- Role vocabulary — WAI-ARIA 1.2 list, pinned in `lantern/vocab.py`.
- State bitmap — 8 fields as enumerated in Part 4 Step 1, bit positions pinned.
- Distance metric contract — Levenshtein primary with size-of-delta tertiary.

Contract changes require `contracts(group-X): freeze` commit. No silent drift.

### 1.5 — Verification dashboard

A `harness/dashboard.py` CLI renders live investigation state. Fields from `state.json`:

- Current ticket and phase
- Spike status per L-SPIKE-NN (pending/green/red/failed)
- Probe count per site per category
- Cluster count and category-majority per cluster (post-discrimination)
- Completeness delta per shape-class (post-completeness)
- Utility pass-rate delta per prompt variant (post-utility)

Dashboard flags red if:
- Any spike is green but its downstream module lacks a frozen contract commit
- Discrimination clusters violate pre-registered rubric
- Completeness falls below soft-pass threshold on dynamic-class sites
- Utility test shows prompt-variant disagreement >5 points (prompt-failure signal)

### 1.6 — Flag, don't improvise

Categories in §R4. When flagged, stop. Do not guess.

### 1.7 — Self-check every commit

See §C0.

### 1.8 — Stop when done

Each investigation phase (stability, discrimination, completeness, utility) returns a number. You score against the pre-registered rubric. You commit the ADR. You stop. No "let me tune the distance metric and re-run." Drift is a rubric-drift event, logged as such.

---

## §R1 — Architecture

Frozen at this document's writing. Changes require ADR.

### R1.1 — Repo layout

```
lantern/
├── pyproject.toml                 # pinned Playwright version, Python 3.12
├── README.md                      # project identity (see R1.4)
├── LANTERN.md                     # methodology spec (frozen after R0)
├── BUILD.md                       # this document (frozen)
├── state.json                     # dashboard state
│
├── lantern/                       # package
│   ├── __init__.py
│   ├── api.py                     # classify() + LanternResult (§R2)
│   ├── probe.py                   # Playwright orchestration
│   ├── fingerprint.py             # Methodology A
│   ├── endpoints.py               # Methodology B
│   ├── grouping.py                # Methodology C
│   ├── rescan.py                  # Methodology D (built after completeness green)
│   ├── distance.py                # Levenshtein, Jaccard, size-of-delta
│   ├── library.py                 # pattern library + NN lookup
│   ├── hints.py                   # LLM hint generation
│   ├── prompts/
│   │   ├── hint_generation_terse.md      # variant A (pre-registered per R0.5)
│   │   └── hint_generation_explicit.md   # variant B (pre-registered per R0.5)
│   └── vocab.py                   # WAI-ARIA roles, landmarks, state bitmap
│
├── spikes/                        # spike artifacts, kept for audit
│   ├── L-SPIKE-01-tab-order/
│   ├── L-SPIKE-02-ax-tree/
│   ├── L-SPIKE-03-computed-style/
│   └── L-SPIKE-04-mutation-observer/
│
├── harness/                       # investigation harness, NOT shipped
│   ├── dashboard.py
│   ├── sites_stability.yaml       # 10 sites
│   ├── sites_discrimination.yaml  # 30 sites across 6 categories
│   ├── tasks_utility.yaml         # 20 tasks across 10 held-out sites
│   ├── run_stability.py
│   ├── run_discrimination.py
│   ├── run_completeness.py
│   ├── run_utility.py
│   └── report.py                  # scorecard against pre-registered rubric
│
├── data/                          # gitignored
│   ├── fingerprints/
│   ├── clusters/
│   ├── completeness_pairs/
│   └── utility_runs/
│
├── adrs/                          # architectural decision records
│   └── 0001-pre-registration.md   # the R0 revision bundle
│
└── tests/
    ├── test_probe.py
    ├── test_fingerprint.py
    ├── test_endpoints.py
    ├── test_grouping.py
    ├── test_rescan.py              # built after rescan.py
    ├── test_distance.py
    ├── test_library.py
    ├── test_api.py
    └── fixtures/                  # static HTML pages for deterministic tests
```

### R1.2 — Python and dependency pinning

Python 3.12 (pinned in `pyproject.toml`). Playwright pinned to a single version, recorded in `pyproject.toml` and `spikes/L-SPIKE-01-tab-order/README.md`. Any Playwright version bump requires a re-run of L-SPIKE-01 and L-SPIKE-02 and a documented ADR.

### R1.3 — Dashboard extension

`harness/dashboard.py` is a CLI that reads `state.json` and renders the current investigation state. Runs in a separate terminal during development. See §1.5 for fields and red-flag conditions.

Location rationale: `harness/` sits at repo root (not inside the `lantern/` package) because the harness is investigation tooling, explicitly "NOT shipped" per §R1.1. Keeping it outside the installed package prevents harness code from ending up in the pip-distributed artifact.

### R1.4 — Project identity

Lantern is a separate Foxworks project from Sherpa. README has its own project identity. License posture: not yet decided; keep private-repo-compatible until commercial identity is pinned. Publishability as research artifact is a Foxworks-level decision, not a build-time decision. Do not add public-repo tooling (badges, contributing guides, CI against public forks) unless explicitly scoped.

---

## §R2 — Sherpa integration contract (frozen)

This is the only coupling point between Lantern and Sherpa. It is frozen here and duplicated in Sherpa's codebase when integration happens.

### R2.1 — Public surface

```python
# lantern/api.py
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class LanternResult:
    shape_id: str           # stable ID from pattern library; "unknown" for novel
    confidence: float       # 0.0 to 1.0
    hints: list[str]        # 0 to 5, each ≤40 tokens
    fingerprint_hash: str   # telemetry only
    elapsed_ms: int         # telemetry only

def classify(
    url: str,
    session_state: Literal["fresh", "warm"] = "fresh",
    timeout_ms: int = 8000,
) -> LanternResult: ...
```

### R2.2 — Sherpa-side integration

A single call site in Sherpa's executor, gated by exception handler so any Lantern failure soft-falls-through to blind execution. Hints prepended under `## Site shape context` header. Temperature, model, and max_tokens pinned to Sherpa's production values.

### R2.3 — Reverse contract: what Sherpa gives Lantern

Lantern does not call into Sherpa. Lantern is stateless from Sherpa's perspective. Every `classify()` call is independent. If future integration (episodic memory, shape-aware re-observation, state-transition-graph planning) changes this, that is a new contract and a new ADR.

### R2.4 — Integration gate

Sherpa integration does not happen until Lantern has passed stability, discrimination, and completeness tests. Utility test is the integration. If Lantern fails any prior phase, Sherpa integration never happens. No "let's just see if it helps" before the gates are cleared.

---

## §R3 — Tickets

Tickets are executed in order. Each gate requires prior gates to be green. No skipping ahead.

### R0 — Pre-registration revision bundle

**R0.1–R0.6** as specified above.

Commit: `revision(R0): incorporate pre-registration review, freeze LANTERN.md`

Acceptance: `LANTERN.md` reflects all six edits. Diff reviewed against pre-registration review document.

### L-SPIKE-01 — Tab order + activeElement

Verify Playwright's `page.keyboard.press('Tab')` produces a deterministic focus traversal on a fixture page with 20 focusable elements of varying types (button, link, input, custom widget with `tabindex`). `document.activeElement` always resolves. Full-cycle termination is detectable by returning to `document.body` or by element-already-seen detection.

Artifact: `spikes/L-SPIKE-01-tab-order/spike.py`, `spikes/L-SPIKE-01-tab-order/README.md` with verified claims labeled KNOWN.

Gate: green before `endpoints.py` implementation begins.

### L-SPIKE-02 — AX tree extraction

Verify `Accessibility.getFullAXTree` via CDP returns the roles, states, and landmarks we enumerated in Part 4 Step 1 of `LANTERN.md`. Fixture has elements with `aria-expanded`, `aria-haspopup`, `aria-selected`, and landmark ancestors.

Artifact: `spikes/L-SPIKE-02-ax-tree/` with extracted-field coverage report labeled KNOWN.

Gate: green before `fingerprint.py` and `grouping.py` implementation.

### L-SPIKE-03 — Computed-style cost

Verify `getComputedStyle` snapshot per-element cost on a page with 200 focusable elements stays under a 2-second wall-clock total. If it exceeds, flag and investigate alternatives (layout-parent-only snapshot, deferred snapshot, skip).

Artifact: `spikes/L-SPIKE-03-computed-style/` with benchmark results labeled KNOWN.

Gate: green before `grouping.py` uses computed styles.

### L-SPIKE-04 — Mutation observer + settlement

Verify mutation-observer-based state-change detection on a fixture page that triggers a known DOM change after a click. Settlement defined as `networkidle + 2000ms + no mutations in observer for 500ms`.

Artifact: `spikes/L-SPIKE-04-mutation-observer/` with detection-reliability report labeled KNOWN.

Gate: green before `rescan.py` implementation.

### L-01 — Vocab + fingerprint

`lantern/vocab.py` (roles, landmarks, state bitmap, role-vocabulary pinning).
`lantern/fingerprint.py` (pure function, synthetic AX-tree input → canonical tuple sequence).
Property tests: determinism, order-preservation, state-bitmap correctness.

Gate: L-SPIKE-02 green. Contracts frozen: `ProbeRecord`, fingerprint tuple format.

### L-02 — Distance metrics

`lantern/distance.py` — Levenshtein on role sequence, Jaccard on state-transition-endpoint-kinds set, size-of-delta tertiary.
Property tests: symmetry, identity, triangle inequality (Levenshtein only), bounds [0, 1] after normalization.

Gate: L-01 green.

### L-03 — Endpoint discovery (Methodology B, no Playwright)

`lantern/endpoints.py` with synthetic AX-tree input. Tests against fixture AX-tree JSON files.

Gate: L-SPIKE-01, L-02 green.

### L-04 — Grouping (Methodology C, no Playwright)

`lantern/grouping.py` with synthetic input. Tests against fixture AX-tree + ARIA-annotated HTML.

Gate: L-SPIKE-02, L-SPIKE-03, L-03 green.

### L-05 — Probe (Playwright integration)

`lantern/probe.py` — Playwright orchestration, loads local fixture HTTP server, coordinates tab traversal and AX-tree extraction. Integration tests against fixture server.

Gate: L-01 through L-04 green, L-SPIKE-01 and L-SPIKE-02 green.

### L-06 — Stability harness and first evidence

`harness/run_stability.py` — 10 sites × 5 visits × 2 UA × 2 session-state. Dashboard renders live progress. Stability report committed.

This is the first moment real evidence touches the pre-registered rubric. If stability fails, investigation halts.

Gate: L-05 green. Pre-registered rubric frozen.

**Halt point.** If stability scores Fail, halt. Commit ADR. Do not proceed to discrimination.

### L-07 — Discrimination harness and library bootstrap

`harness/run_discrimination.py` — 30 sites × 1 probe across 6 categories. Hierarchical agglomerative clustering on A+B+C static fingerprint (per R0.3). Library bootstrapped from clusters.

**Halt point.** If discrimination scores Fail, halt. Commit ADR. Investigation returns "thesis partially survives; Lantern-as-probe-library but no classifier" verdict.

Gate: L-06 Pass or Soft Pass.

### L-08 — Rescan (Methodology D)

`lantern/rescan.py` — three-pass protocol. Tests against fixtures with known state transitions. Poke-selection policy pinned per R0.2.

Gate: L-07 Pass or Soft Pass. L-SPIKE-04 green.

### L-09 — Completeness harness

`harness/run_completeness.py` — re-run the 30 discrimination sites with A+B only vs A+B+C+D. Per-shape-class pass evaluation per R0.4. Per-category reporting.

**Halt point with scope-down option.** If completeness Fails on dynamic-class sites, scope down to A+B+C only (Methodology D dropped). If completeness Passes but dynamic-class correct-null behavior fails on static-class sites, that is a different finding — investigate before proceeding.

Gate: L-08 green.

### L-10 — Hint generation prompts (dual variants)

Author `lantern/prompts/hint_generation_terse.md` and `lantern/prompts/hint_generation_explicit.md`. Both committed before any utility run. Decision table for prompt-variant disambiguation committed alongside.

Gate: L-09 complete (Pass, Soft Pass, or scope-down). Clusters from L-07 available.

### L-11 — Hints module and classify()

`lantern/hints.py` (LLM call with prompt variant selection).
`lantern/api.py` (`classify()` orchestration).
Integration test: full pipeline on a fixture page end-to-end.

Gate: L-10 committed.

### L-12 — Utility harness

`harness/run_utility.py` — 20 Sherpa tasks × 10 held-out sites × 2 conditions × 2 prompt variants = 80 runs. McNemar paired test. Decision table applied.

Gate: L-11 green. Sherpa integration point identified (current Sherpa commit SHA recorded).

### L-13 — Sherpa integration touch

Add `lantern.classify()` call site to Sherpa executor. Add `## Site shape context` header. Run utility test from L-12 against integrated Sherpa.

Gate: L-12 Pass.

### L-14 — ADR + cairn primitives compliance audit

Two artifacts:

(a) Final ADR — verdict per the pre-registered mapping table. Proceed / scope-down / halt. Evidence citations to every prior ticket and harness report.

(b) Cairn primitives compliance audit — ADR confirming each cairn primitive from §C0 was enforced, with specific evidence (commit SHAs, ticket references, spike artifacts, dashboard flags raised). If any primitive was relaxed, document why.

Gate: L-13 complete or scope-down decision committed.

---

## §R4 — Flag categories

Base cairn flags apply. Lantern-specific additions:

- `HUMAN REVIEW: compliance-variance` — a category's sites show substantially different Completeness results; investigate whether the category needs splitting
- `HUMAN REVIEW: cluster-instability` — discrimination clustering produces different results under different seeds or hyperparameters
- `HUMAN REVIEW: prompt-variant-disagreement` — utility-test prompt variants diverge >5 points, cannot disambiguate classification from prompt quality
- `HUMAN REVIEW: library-staleness-at-integration` — utility test's held-out sites exceed the library's confidence threshold on >30% of tasks; library is too sparse for production
- `HUMAN REVIEW: playwright-breakage` — Playwright version drift breaks a prior spike; requires re-verification before proceeding
- `HUMAN REVIEW: rubric-drift` — any proposed change to frozen measurement surface mid-investigation

A raised flag is a successful outcome. A silent mis-build is a failure even if tests are green. A successful probe run that does not produce its required fingerprint JSON is a defect, not a success.

---

## §R5 — Definition of done

Lantern is done when:

1. All six R0 revisions are frozen in `LANTERN.md`
2. All four spikes (L-SPIKE-01 through L-SPIKE-04) are green
3. All tickets L-01 through L-14 are complete or have committed halt/scope-down ADRs
4. The dashboard renders live state throughout the investigation and reaches "ready for Sherpa integration" or "halted at phase N" state
5. The cairn primitives compliance audit (L-14 part b) shows every enforced primitive has evidence
6. `classify()` produces a `LanternResult` on a fixture page end-to-end, and the result's `hints` are either populated (for library-match sites) or empty (for unknown-shape sites) with `soft-fallthrough` confirmed
7. If utility test Passed: Sherpa integration touch is complete, both codebases compile, utility-test report is committed
8. If utility test Failed: revert diff is committed to Sherpa (if integration was attempted), Lantern stands as research artifact with full evidence trail

"Works on my machine" is not done. Done includes the ADR and the dashboard state.

---

## §R6 — First response protocol

Before writing any code or running any spike, your first response must:

1. **Environment check.** Confirm Python 3.12 available, Playwright installable, CDP accessible. Report any blockers.
2. **§C0 read confirmation.** Confirm you have read §C0 and understand which cairn primitives apply to this Tier 3 build. List them back.
3. **R0 revision plan.** Restate R0.1–R0.6 as a checklist, one line per revision, and identify which section of `LANTERN.md` each edit lands in.
4. **Risk ranking.** Identify the highest-risk spike. My prior: L-SPIKE-04 (mutation observer + settlement detection) because false negatives produce silent state-miss and false positives produce false deltas. Confirm or rank differently with reasoning.
5. **File layout confirmation.** Propose the exact `lantern/` directory structure from §R1.1, flag anything you'd change and why.
6. **Ask for "go"** before starting R0.

If anything in §C0–§R5 is ambiguous or contradicts `LANTERN.md`, flag before starting. Do not improvise.

Do not start R0 before receiving "go."

---

## §R7 — When stuck

If a spike fails in a way that contradicts its hypothesis, flag. Do not rework the methodology to survive the evidence.

If a contract needs to drift after freeze, flag. Do not silently re-freeze. Commit an ADR explaining why the freeze was wrong, and commit a new freeze.

If a rubric criterion seems to be near the edge of pass/fail and you're tempted to collect more data, flag. Drift-by-re-running is the most seductive rubric-drift failure mode. The rubric was frozen for a reason.

If `LANTERN.md` and this build contract disagree on a thesis question, `LANTERN.md` wins. On a process question, this document wins. Flag the conflict either way.

If Sherpa's public surface changes during Lantern development in a way that affects R2.1 or R2.2, flag. Do not silently accommodate. Sherpa's contract is frozen for Lantern's purposes at the commit SHA recorded in L-12.

A successful operation that does not produce its required audit artifact (log, ADR, dashboard flag, screenshot) is a defect, not a success.

---

## §R8 — Rate

Before starting, rate this build contract. Identify the weakest section. State one change you'd make if you could change one thing. Then ask for "go."

Rating scale (per cairn convention):
- 1 — strong, no changes needed
- 2 — strong with minor edits
- 3 — viable but has identified risks
- 4 — major revision needed before starting
- 5 — reject
