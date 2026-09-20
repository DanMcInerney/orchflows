# Study: work units, review gates, and workflow authoring

Status: development test design with six new executable cases. [Pilot predictions](gate-predictions.md) freeze the selected cases and expected behavior before native execution of the revised policy. The scenarios are synthetic diagnostic examples, not a measured sample of user demand. Historical native results do not validate these cases or proposed policies.

## Decision to make

Should Dynamic and Build share a rule for composing reviewed units? Which boundaries produce useful results without unnecessary review, and should saving a process invoke a distinct authoring procedure?

Working hypothesis: a unit produces a coherent candidate that can be judged against a shared acceptance contract and handed to dependent work. Its shape is:

`one or more makers -> join candidate and evidence -> one independent review -> at most one repair pass -> affected checks`

Accepted staffing choice: each gate has one independent reviewer and one worker for the single permitted repair pass when repairs are needed. A clean review needs no fixer. Checks after repair establish the repaired behavior; they do not renew the original independent verdict. Unresolved blockers stop dependent work. Relabeling another fix/review round as a new unit must not replenish a bound. Fixer count is a settled policy for this study, not an optimization variable.

A unit is not automatically a worker, file, guidance document, tool, or workflow call. Guidance supplies criteria and methods. An output contract, consequential dependency, or separately consumed result can justify a boundary. Several guidance domains can apply to one result; successive units can share guidance. Investigate whether that definition is specific enough for reliable model use.

Choose boundaries before dependent work starts, using the result and acceptance criteria. Later evidence can change the plan, but cannot erase consumed reviews or repairs. Avoid defining units retrospectively as whatever happened to get reviewed: that would make this hypothesis impossible to test.

QA can be maker evidence, the independent review itself, or a separately requested deliverable. Its role and consumed result determine its place. A review report does not automatically need another review. Changes between graybox and production create a new candidate; repeating review of an unchanged candidate under another label does not.

## Library behavior before this revision

| Consumer | Current behavior | Fit with the hypothesis |
| --- | --- | --- |
| [Dynamic](../../skills/orch-dynamic-workflow/SKILL.md) | One final joined review by default; intermediate gates for costly decisions; direct checks for trivial work; coordinated repair staffing | Close, but boundaries are inferred and one fixer is not required |
| [Build](../../skills/orch-build-workflow/SKILL.md) | Author reusable procedure; finish trials; one authoring review and at most one repair pass | Reviews the procedure, not every unit that the procedure will execute; does not prescribe a universal unit shape |
| [3D game](../../example-workflows/3d-browser-game/skills/3d-browser-game/SKILL.md) | Core playtest gate, then final integrated playtest gate, each with at most one repair pass | Two gates contain several types of production work |
| [Blender assets](../../example-workflows/3d-browser-game/skills/make-blender-game-assets/SKILL.md) | Explicitly no independent review; inspect exports and hand them to integration | A separate guidance specialization currently does not create a gate |
| [Short video](../../example-workflows/short-video/skills/short-video/SKILL.md) | One review per film's exports; explicitly no repair loop | Conflicts with an unconditional review-plus-fix rule |
| [Design loop](../../example-workflows/design-loop/skills/design-loop/SKILL.md) | One comparison round per attempted cycle; corrections go into later bounded cycles | Multiple stages share a gate; no immediate repair pass |
| [Software factory](../../example-workflows/software-factory/skills/software-factory/SKILL.md) | Review per applicable specialist lens; revised candidates repeat reviews within a pass budget | Deliberate exception to one reviewer/one pass |
| [Compare candidates](../../example-workflows/shared/skills/compare-candidates/SKILL.md) | Review-only judgment; no candidate repair or adoption | Assessment itself must remain a valid operation |

Treat these as actual differences, not evidence that one policy is superior. An experiment must explicitly amend a named workflow before applying a new policy to it. Do not silently wrap existing workflows or count their reviews twice.

## Conditions and staged comparison

Freeze task fixtures, evaluator criteria, budgets, host/model settings and package snapshots before measurement. Execute each condition from a separate checkout with the identical study cases. The runner snapshots runtime packages. Change only the intended instructions; record the exact diff. Its package override option does not replace core with another package of the same name.

1. **A: current boundary policy.** Retain current Dynamic/Build boundary selection, with the accepted one-reviewer/one-fixer policy applied to their gates. Freeze any unmodified current snapshot separately as a historical reference; a comparison to it changes staffing as well as boundaries and is not a single-factor result. Named workflows retain their contracts unless explicitly amended.
2. **B: top-level domain boundaries.** Change Dynamic so substantive work in each top-level domain forms a reviewed unit before dependent work in another domain. Ignore changes to dotted specializations, library extensions and Make/Review sections when identifying the domain. Repeated domain occurrences are possible after an intervening dependency; do not collapse every occurrence into one global bucket. Initially test domain changes alone, without C's additional same-domain milestone rule. Keep A's trivial-task exception and fixed staffing. This tests the clarified hypothesis, not a review per guidance file or resolved bundle. Record how mixed-domain deliverables and supporting activities are classified; ambiguous assignment is a finding about the rule's completeness.
3. **C: deliverable boundaries.** Change only the boundary rule: group work by coherent candidate/acceptance contract, and gate consequential handoffs before dependent work. Guidance is a signal, not the boundary. Keep the same trivial-task exception and fixed staffing as A/B. Include repairs crossing multiple files or tools to test whether the single fixer fulfills its assigned scope.
4. **C2: every task reviewed.** Separately remove the trivial-task exception from the preferred boundary condition. Use tiny requests to measure the added cost and any improvement.

After choosing a promising unit rule, compare authoring structures with the SAME unit, trial and review requirements:

- **Separate authoring:** Dynamic runs work; an explicit save/reuse request composes Build's authoring process. Build can also author directly without running the user's real task.
- **Unified entrypoint:** one entrypoint selects execute or author mode; author mode preserves Build's synthetic trials, completed-evidence dependency, authoring review, packaging and honest registration checks.
- **Shared wording:** keep both entrypoints and factor genuinely shared contracts into referenced core guidance. Treat this as a separate instruction-layout experiment; measure total loaded context, not just shorter skill files.

Current Build versus a weakened unified mode would compare different guarantees, not merely structure. Preserve Build's separate scope: its trial exercises generated units; its authoring review judges the recipe and completed trial evidence. Do not add a Dynamic final review around an already sufficient authoring review.

Run A/B/C on diagnostic cases first, then the trivial-task ablation, then authoring comparisons. Start with one attempt to find broken fixtures; freeze corrections before three repeated measurement attempts per condition. Interleave condition order; keep repetitions with their case when summarizing. Select additional unseen task families before final tuning. Everything exposed in this repository is development material, not a protected holdout.

## Stress cases for the top-level domain rule

Optional Make/Review sections can describe two roles judging the same domain result. Their presence or absence must not itself add or remove a unit. Common guidance and the actual task's acceptance criteria still apply. A reviewer writing a report is not automatically a new writing unit; a data analyst's disposable script is not automatically a separately delivered code unit.

| Complex request | Plausible units | What domain labels alone leave unresolved |
| --- | --- | --- |
| Research a feature, then implement it | Research -> code | Clean case: different deliverables and a genuine cross-domain dependency |
| Benchmark an implementation, optimize it, and compare again | Code -> data analysis -> code -> data analysis | The same top-level domain can recur; this must not become a loophole for repeated repairs |
| Migrate an API while keeping existing clients working | Compatible server contract -> migrated clients -> removal of legacy behavior, all code | Consequential same-domain milestones may merit separate gates |
| Analyze survey data and deliver a report with charts | Data analysis -> writing/visual design, possibly one joined final artifact | A supporting script and ordinary explanatory prose should not necessarily create extra units; standalone tools/copy/design outputs might |
| Launch a product with a site, brand assets and announcement | Research -> parallel code, visual design and writing -> integrated launch package | Domain-specific correctness does not establish cross-artifact consistency; the joined candidate needs an owner and applicable criteria |
| Build a game with a playable prototype, original art and a finished level | Code prototype -> parallel visual design and code content -> code integration/review | Two code units can differ in scope; playtesting can be the final unit's review rather than separately reviewed work |
| Author a reusable research-to-code workflow | Orchflows authoring, including trials and authoring review; generated recipe contains research -> code | Domains in the generated recipe differ from the builder's authoring domain; incidental writing must not create recursive review stages |

The candidate refinement is **primary top-level domain plus a bounded deliverable phase**. Other guidance can support the same candidate and reviewer. Repeated same-domain phases need distinct intended results/dependencies identified before work, not relabeling after a failed review. Keep Dynamic's built-in guidance restriction fixed; broadening extension access is outside this study.

## Task matrix

These are plausible task families to sample, not frequency-ranked claims. Each row names ordinary user intent, a boundary question, and observable success. Except for the executable cases linked below and existing fixtures, rows are specifications awaiting concrete inputs, scorer controls and capability validation.

| ID | Family and ordinary request | Boundary question | Outcome and trap |
| --- | --- | --- | --- |
| W1 | Compare suppliers and write a purchasing recommendation | Parallel source research joins into one decision | Correct total cost, eligibility, linked evidence; duplicated vendor claims are not independent sources |
| W2 | Turn team requests into a weekly capacity plan and brief | Data analysis and writing can serve one result | Capacity respected, unknown effort preserved, brief agrees with plan |
| W3 | Convert meeting notes into actions and draft follow-ups | Extraction precedes drafts; sending has separate authority | Correct owners/dates; capture drafts without live messages |
| W4 | Update a budget workbook and board summary | Reconcile numbers before narrative depends on them | Formulas and denominators correct; rendered workbook inspected |
| W5 | Prepare an RFP response from policy and product documents | Coverage/research handoff before final response | No invented commitments; unanswered requirements remain visible |
| W6 | Compare contract revisions and draft negotiation notes | Evidence extraction versus advice/drafting | Accurate clause references and material omissions; synthetic documents |
| W7 | Analyze an incident and prepare a customer update | Technical conclusions before external claims | Timeline supported; uncertainty not turned into root-cause certainty |
| W8 | Draft a launch plan, positioning and support FAQ | Shared facts across several writing deliverables | Product claims consistent; parallel drafting does not duplicate review per file |
| D1 | Research two changed export formats and build adapters | Research gate before parallel dependent code | Correct current formats, joined contract, tested adapters |
| D2 | Define a wire contract and implement producer/consumer | Similar code guidance across separate handoffs | Compatible implementations and evidence contract settled first |
| D3 | Build a small accessible event landing page | Code, design and writing for one candidate | Correct content and navigation; no invented gate per CSS/HTML/copy file |
| D4 | Fix two related modules after reviewing the whole patch | One fixer's coverage across related artifacts | Both bugs fixed after review, no premature edits, affected checks |
| D5 | Investigate a regression, patch it and run QA | QA as evidence/review versus a recursively reviewed unit | Reproduced failure, fix, regression evidence; no second review of the report by default |
| D6 | Plan a schema migration and implement rollback | Irreversible contract/data boundary despite same guidance | Data preservation and rollback verified with synthetic snapshots |
| D7 | Change an API, client and documentation together | Three artifacts may form one integration candidate | Behavioral compatibility; no partial interface handed downstream |
| D8 | Deliver a security-sensitive change using Software Factory | Required specialist reviews versus universal one reviewer | Preserve selected workflow's lenses or record explicit policy amendment |
| R1 | Synthesize several studies into a decision memo | Parallel topics merge under one research gate | Qualifications, contradictory studies, source independence |
| R2 | Choose an approach, then implement a simulation | Consequential research choice gates code | Reproducible parameters and limitations; code cannot legitimize weak premise |
| R3 | Analyze survey data and make recommendations | Cleaning/denominators before downstream inference | Missingness and sample limits correct; no population overclaim |
| R4 | Recommend a vendor with missing eligibility evidence | Blocked unit must not feed a fabricated decision | Explicit insufficient evidence, no invented current audit |
| V1 | Create a pitch deck from company facts | Facts, story, visual layout: which handoffs merit gates? | Accurate claims and actually rendered readable slides |
| V2 | Produce three ads in one campaign | Independent deliverables versus one joined campaign review | Consistent claims and distinct useful concepts; latency versus coverage |
| V3 | Research FPS mechanics, build a graybox, add art and playtest | Mechanics, assets, integration and adaptive play | Actual playable loop, runtime assets and observed QA; tooling cannot be mocked into a pass |
| V4 | Create a Blender asset pack for an existing game | Standalone asset consumer may justify a gate absent in embedded production | Editable sources, loaded GLBs, correct scale/pivots/budgets |
| V5 | Produce a short video and inspect its exports | Existing review-only workflow versus new repair policy | Real playback, readable text/audio, honest bounded repair scope |
| X1 | Correct a typo or reformat a tiny table | Is a direct check sufficient? | Exact requested change; measure avoidable agents/time |
| X2 | Choose among stable proposals without changing them | Pure review is useful work | Supported preference/tie; no automatic fixer or review of the reviewer |
| X3 | Run a nested saved workflow with a scoped extension | Composition must not multiply gates | No duplicate review of identical candidate/scope; local guidance stays local |
| X4 | Review unavailable, repair insufficient, or budget exhausted | Stop rules and honest partial outcomes | No self-review substitution, extra pass, hidden reset or false readiness |
| X5 | Resume after review but before repair | Preserve consumed bounds and candidate identity | No replayed review or duplicate external operation |
| X6 | Do a task, then save its process; reuse on changed inputs | Dynamic-to-Build handoff and generalization | Actual task delivered, safe authoring if selected, fresh reuse without hardcoded answers |

For each applicable family, exercise: **do now**, **author only**, **do then save**, **invoke saved on changed inputs**, and **compose saved inside a larger task**. Do not expand the full cross-product before a small pilot is valid. Author-only trials must not count as delivery of the real task.

## Executable development subset

| Case | Matrix | Main diagnostic | Scoring limits |
| --- | --- | --- | --- |
| `core/gates/mixed-guidance` | D3 | Several domains, one small integrated output | HTML checks establish semantics only; actual layout/accessibility need rendered inspection |
| `core/gates/contract-code` | D2 | Same broad domain, consequential contract handoff | Python behavior plus transcript audit for ordering; output alone cannot prove a gate |
| `core/gates/repair-once` | D4 | Explicit one reviewer and one fixer over two faulty modules | Seeded defects ensure actionable findings; native trace proves staffing/order |
| `core/gates/missing-evidence` | R4 | Insufficient research evidence blocks recommendation | Public eligibility criteria determine abstention |
| `core/gates/build-reuse` | W2/X6 | Author a recipe, freeze it, reuse twice | Build's completed trials and authoring review remain mandatory |
| `core/gates/save-dynamic` | W2/X6 | Execute then save; same reuse inputs as Build | Revised Dynamic requires Build's trial and authoring review; historical snapshots are judged against their actual contract |
| `core/research-code` | D1 | Parallel research then dependent adapters | Existing supplied-corpus task; no live-research claim |
| `core/composition` | X3 | Scoped nested workflows | Existing source-backed scenario |
| `core/explicit-dynamic` | X1 | Explicitly selected trivial work | Baseline permits direct checks |
| `core/missing-review` | X4 | Reviewer unavailable | Correctly blocked result can succeed |
| `core/safe-authoring` | W3 | Synthetic rehearsal and captured effects | Trial phase only; not complete Build validation |

The four new direct cases are in `gates`; the two authoring paths are in `gates-authoring`. Existing cases remain individually runnable. Smoke membership is unchanged. All six use local files and core only. They cannot establish selection of Blender, playtesting or other library extensions: current Dynamic deliberately excludes those. Test named library workflows separately; changing Dynamic's extension policy is another experimental factor.

Each case with a manifest is discoverable now. Grader controls in `tests/test_gate_study.py` exercise valid outputs, alternate valid outputs where relevant, near misses and malformed/empty outputs. These are offline scorer checks, not agent performance or native process-auditor calibration. A real public-input solvability pilot and independent semantic/process-auditor calibration remain required before ranking instruction variants.

## Evaluation and evidence

Keep two questions separate:

1. **Useful task outcome:** executable correctness, supported claims, coherent artifacts, valid uncertainty, preservation and allowed effects.
2. **Selected process compliance:** ordering, joined evidence, reviewer independence, applicable guidance, stable candidate, repair bounds, scoped settings and no duplicate wrapping.

Do not fail baseline A because it lacks an experimental gate that neither the request nor its selected contracts requires. Record proposed boundaries as observations with consequences. For B/C, enforce their frozen contract, but compliance alone cannot make them better. A failed dependency with downstream damage, or a costly redundant gate with no benefit, is the important comparison.

Annotate observed units from native assignments and artifact identities: candidate scope, evidence consumed, guidance, review start/end, fix owner, changed state, checks, downstream start and gaps. This is evaluator analysis, not a new production schema or required agent ceremony. Inspect actual events; self-reported plans and agent counts do not establish causality. Maker checks must not be mislabeled as independent reviews.

Report by task family: useful-outcome success/unknown, critical failures, process violations, justified blocked outcomes, required gates missed, duplicate reviews of the same state/scope, and applicable domain coverage. Report quality of subjective work with anchored judgments and cited artifacts. Do not reward gate counts, parallel worker counts, verbosity or checklist completion.

Also report elapsed execution/audit time, observed usage/cost, child launches, avoidable waiting, and authoring versus reuse costs separately. Unknown cost remains unknown. Compare one, five and twenty reuses when estimating whether authoring overhead pays off. Report exact finite-suite results and paired case deltas, not population-wide reliability.

Retain every planned repetition. Task failure, infrastructure failure, incomplete run and missing evaluation evidence are distinct. Existing harness verdicts conservatively treat timeout/missing evidence as inconclusive; record task deadline misses separately if measuring time-to-completion. Never silently retry a bad result or rank systems on a smaller successful subset.

Calibration should include a valid trace, equivalent staffing/artifact variation, an omitted required gate, review before all results arrive, mutation during review, an unchanged candidate reviewed twice, a fixer acting before review, a second repair disguised as a new unit, and a missing native record. Validate false accepts and false rejects with independently adjudicated examples before trusting a process score.

## Run and compare

From each frozen checkout, preflight without launching agents:

```powershell
python tests/e2e/run.py --suite gates --plan --deadline 2400 --audit-seconds 120
python tests/e2e/run.py --suite gates-authoring --plan --deadline 3600 --audit-seconds 180
python -m unittest discover -s tests -p test_gate_study.py -v
```

Pilot one diagnostic first, with a new evidence directory outside the checkout:

```powershell
python tests/e2e/run.py --case core/gates/contract-code --output ../gate-pilot-A --jobs 1 --deadline 900 --audit-seconds 120
```

After fixture and evaluator validation, execute a frozen condition:

```powershell
python tests/e2e/run.py --suite gates --output ../gate-study-A --jobs 2 --deadline 3600 --audit-seconds 120 --repeat 3
python tests/e2e/run.py --suite gates-authoring --output ../gate-authoring-A --jobs 2 --deadline 7200 --audit-seconds 180 --repeat 3
```

These are bounded example budgets, not predictions or guaranteed completion. Authoring permits 840 seconds plus two concurrent reuse sessions of up to 240 seconds per case; cases cap at 1260 seconds. Suite deadlines include audits and can leave work unstarted. Native trials consume normal model usage; host subagents and Build's inner trials are additional to harness concurrency. Keep host, model, effort, hardware and budgets matched and record interventions.

The automated adapters support Claude and Codex but do not provision browser/MCP tools or multimedia runtimes for these cases. The game, Blender, deck rendering, spreadsheet rendering and video rows need a declared capable host-driven trial or a separately validated tool environment. Shell access alone does not establish those capabilities. Leave unvisited modalities unverified. Synthetic filesystem separation is not a security boundary.

Choose a structure only after seeing whether it improves useful outcomes or reduces cost without losing required behavior. The initial recommendation to test is shared unit semantics with distinct authoring obligations and an explicit save handoff, rather than deriving gates solely from guidance filenames. The implementation uses one shared `orchflows` guidance document; it does not introduce a guidance specialization per consuming skill.

## Local verification, 2026-09-20

The initial fixtures passed discovery and offline scorer controls before native execution. Subsequent implementation, predictions, native trials, fixture corrections and limitations are recorded in [gate-results.md](gate-results.md). The latest full offline suite ran 181 tests with one platform skip and no failures. These are harness/regression checks, distinct from native behavioral outcomes. The proposed matched A/B/C comparisons and repeated measurements have not been run.
