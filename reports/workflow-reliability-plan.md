# Plan: simpler, more reliable workflow composition

Status: proposed; this document does not implement the recommendations. Evidence baseline: the 17 September 2026 dogfood series, including events after midnight UTC on 18 September.

## Goal and recommendation

Make saved workflows survive improvements in models. The prompt supplies the current task and constraints. Guidance and extensions supply methods, taste and removable model corrections. Workflows preserve the user's chosen order, dependencies, independent judgments, gates, repetition and stopping conditions. The top-level orchestrator chooses the assignments and owns every child launch and continuation.

Keep that architecture and the small shared library. Improve four places where execution still depends too heavily on interpretation:

1. Separate ordinary production stages from mandatory fresh-worker launches.
2. Reduce workflows to visible dependencies and gates, moving production methods into guidance where appropriate.
3. Strengthen the boundary between the orchestrator and its children, using supported host restrictions where available.
4. Tie completion to evidence about the delivered result, and enforce deterministic limits where the operations occur.

These changes should reduce recurring failure classes. Only an actual execution restriction can prevent a prohibited action; shorter prose cannot guarantee compliance. No new workflow language, universal execution engine, tier hierarchy or mandatory record format is proposed.

## Evidence baseline: preserve what already works

The [dogfood report](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/REPORT.md) covers 19 isolated primary trials and one checkpoint continuation. It records successes and unresolved failures. Its timings are descriptive: trials ran concurrently, so they do not establish comparative speedups.

The [wider-task audit](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/examples-audit.md:13) reports:

> This demonstrates flexible staffing and integration, not an optimal worker count or a measured speedup over sequential execution. The prior smaller tasks used zero or one maker; this wider task used two concurrent makers without a workflow rewrite.

The [custom-library audit](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/authoring-media-audit.md:50) reports:

> Native records prove four fresh children under the trial root: `options_work`, `options_compare`, `brief_draft`, `brief_review`. Each dependent stage started after its prerequisite completed.

This supports keeping flat composition, useful parallel work and reusable comparison/revision components. It does not support replacing the architecture because individual runs failed.

The root-only fallback clarification and export ordering clarifications are already present. Their exact changes are preserved in [source-changes.diff](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/source-changes.diff). This plan builds on them rather than presenting them as unfinished implementation work.

## 1. Let the orchestrator choose staffing beneath the saved process

### Evidence and diagnosis

The current [design-increment component](/C:/Users/danhm/.codex/worktrees/108e/orchflows/example-workflows/design-loop/skills/design-increment/SKILL.md:9) says:

> Invoke core `orch-work` for the named assignment `design-increment` with these inputs and resolved Make guidance.

The [analysis component](/C:/Users/danhm/.codex/worktrees/108e/orchflows/example-workflows/design-loop/skills/analyze-iteration/SKILL.md:9) says:

> Invoke core `orch-work` for the named assignment `analyze-iteration` with the inputs and resolved Make guidance.

Brainstorming, research and implementation also explicitly invoke the fresh-worker primitive. This makes five ordinary production stages require fresh workers in each full cycle, in addition to the independent comparison. The top-level instruction to choose staffing cannot fully remove that prescription.

The [Design Loop trial result](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/REPORT.md:60) states:

> It exceeded the initial limit during second-cycle review and was stopped.

The run later completed under an explicit extension. This proves the original deadline was missed. It does not prove worker launches were the sole cause. Unnecessary launch requirements are a plausible contributor and an independently visible restriction on flexibility.

### Planned change

Revise ordinary production components to state their inputs, required result, allowed effects and stopping conditions. Let the root choose direct work, continuation of an appropriate maker, or fresh workers. Keep `orch-work` itself a fresh-child primitive; change when components require it, not its meaning.

Preserve every deliberate dependency. In Design Loop, options still precede research; research informs design; the evaluation plan is fixed before implementation; independent comparison precedes adoption. Reusing a maker does not permit changing a frozen plan or skipping a handoff. The root continues to apply the components and control each assignment.

Freshness or separation remains mandatory when independence, required isolation or caller-specified settings demand it. A maker cannot become its own independent reviewer. Direct work and continued workers must honor the existing model/effort rules.

Start with the [Design Loop components](/C:/Users/danhm/.codex/worktrees/108e/orchflows/example-workflows/design-loop/skills). Review other production wrappers for the same accidental staffing constraint, changing only cases where a separate worker has no deliberate contractual purpose.

**Expected benefit:** fewer compulsory launches and handoffs, with no change to the saved process. Better models can perform more ordinary work directly while preserving required independent judgments. Latency improvement remains a claim to test.

## 2. Make required gates the visible structure of each workflow

### Evidence and diagnosis

The [game audit](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/authoring-media-audit.md:115) records:

> Asset production actually finishes at 00:23:34.519; no core reviewer was ever launched.

The [current game workflow](/C:/Users/danhm/.codex/worktrees/108e/orchflows/example-workflows/3d-browser-game/skills/3d-browser-game/SKILL.md) already requires that review before final asset production. The audit ties the violation to the installed instructions and native trace. This was a skipped dependency, not an omitted rule.

Likewise, the [original export audit](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/independent-audit.md:88) concludes:

> Thus the mandatory export review lacked trial evidence. Later running a trial cannot retroactively make that review assess its results.

These findings motivate making dependencies prominent. They do not establish that document length caused either failure or that shortening alone will cure them.

### Planned change

Rewrite the game entrypoint around its essential process:

```text
Establish brief, feasible scope and capabilities
                      ↓
Produce and exercise the playable core
                      ↓
Independent core review → at most one repair → required verification
                      ↓ ready core only
Produce assets ────────────┐
                          ├─→ Integrate and verify the production candidate
Build remaining content ──┘
                      ↓
Independent final review → at most one repair → required verification
                      ↓
Deliver the result with its actual acceptance status
```

The root owns every assignment. Production blocks can use one or several makers. Failed or missing prerequisites stop dependent work; independent work can continue when useful and within the remaining bounds. A partial-phase request returns only the requested phase and evidence.

Move camera techniques, modeling procedures, tuning methods and similar production advice into the existing relevant guidance or references. Read that guidance for the applicable assignment rather than loading the entire production manual into every child.

Preserve deliberate requirements. For example, the current two mechanics experiments remain a requirement unless intentionally changed; moving that count into optional advice would change the process. The two distinct review checkpoints and their repair limits remain intact.

Use the same editing test elsewhere: does a sentence define a dependency, independent judgment, bound or allowed effect, or does it teach how to do the work? Retain the former in the workflow. Put the latter with its domain owner. Delete duplicated generic advice instead of merely relocating it.

The [authoring guidance](/C:/Users/danhm/.codex/worktrees/108e/orchflows/guidance/orchflows.md) already calls for this separation. Prefer applying it to the examples over adding another architecture document. Measure the entrypoint plus its required context, not just the entrypoint's word count.

**Expected benefit:** easier inspection of what may run concurrently and what must wait; less competition between process constraints and production advice. This remains a behavioral improvement to validate, not hard gate enforcement.

## 3. Give children complete assignments without coordination authority

### Evidence and diagnosis

The [original Benchmaker audit](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/examples-audit.md:51) states:

> Native metadata independently identifies the new agent's depth as **2**, with the pilot as parent.

It also records that the child read the root-only rule and later acknowledged that its original assignment prohibited delegation. The restriction already existed; the child nevertheless interpreted its audit as an occasion to invoke the dynamic fallback.

The same audit identifies a separate context failure:

> The actual phase-1 scope withheld README, which defines the required `schedule` schema; neither authorized public JSON file carries that contract.

Source: [public-contract finding](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/examples-audit.md:59). The reasonable schedules scored zero because the assignment lacked their public response contract. Removing context indiscriminately would worsen this failure class.

### Planned change

Keep workflow interpretation and assignment decisions at the root. A leaf assignment receives the intended result, complete public inputs and response contract, relevant guidance, working/output locations, applicable bounds and allowed effects. It returns results and requests for further work to the root.

Avoid giving a child an open-ended workflow invocation as its assignment. Do not require a new machine-readable task schema or ban all inherited context. Use no-history execution where the process requires independence from authoring material; exclude evaluator secrets while retaining the complete public task.

Retain the existing fallback eligibility guard. The [corrected-run audit](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/authoring-media-audit.md:99) observed the auditor reading that exclusion and proceeding directly, with only two depth-one children. That supports the specific correction on this host; it is not proof of universal enforcement.

Perform a bounded feasibility check of the active host's native child controls. Where supported, restrict child launch, assignment and continuation capabilities while preserving tools needed to do the task. Verify alternate delegation paths, including agent CLIs, before describing the restriction as enforced. Hiding skills alone is insufficient.

Record verified host capabilities in the existing [host documentation](/C:/Users/danhm/.codex/worktrees/108e/orchflows/docs/hosts.md). If enforcement is unavailable, preserve the instructed boundary and disclose that limit. Do not build a new cross-host execution platform to disguise the missing capability; do not claim an explicitly required hard restriction was satisfied.

**Expected benefit:** fewer accidental nested workflows and incomplete leaf assignments. A verified host restriction can prevent delegation through the paths it controls; assignment prose can only reduce violations.

## 4. Base completion and limits on actual operations and current evidence

### Evidence and diagnosis

The game's own [repair record](/C:/Users/danhm/orchflows-dogfood-20260917/browser-game/workspace/evidence/repair-record.md:12) says:

> Safe-route completion remains unverified.

The repair demonstrated that holding forward no longer wins. The [independent audit](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/authoring-media-audit.md:119) found no demonstrated successful delivery on either route after the layout change. Fixing the exploit did not establish acceptance of the delivered game.

The [Benchmaker request](/C:/Users/danhm/orchflows-dogfood-20260917/benchmaker-recheck/request.md:1) says:

> Cap authoring validation at four control outcomes per case and a two-case independent public-input audit.

The [budget audit](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/authoring-media-audit.md:101) records:

> However, `run.py:selftest` additionally grades `None` for case `crb-dev-001`, beyond those four distinct fixture outputs.

Four stored fixtures therefore do not establish compliance with the validation allowance. Whether repeated grading and harness assertions count separately was not fully resolved; the evidence supports an accounting gap, not an unqualified claim about every budget interpretation.

The [builder audit](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/authoring-media-audit.md:56) also found an actual review report inside the installable library. The [misplaced record](/C:/Users/danhm/orchflows-dogfood-20260917/builder/workspace/personal/trials/ordinary/builder-review.md:1) begins:

> # Builder review record
>
> An independent reviewer assessed the candidate library and the completed ordinary trial without editing either.

These are different symptoms of relying on labels or intended behavior where concrete evidence and destinations are available.

### Planned change

**Acceptance:** use the existing review/repair contract. Gather the completed required judgment before repair. Track which artifact was reviewed and which artifact is delivered. After changes, run affected checks plus caller-required acceptance checks; preserve missing checks as gaps. Do not add a universal second review. A failed reviewer launch blocks review-dependent repair; disclosing the failure does not satisfy the prerequisite.

For resumable or bounded workflows, reuse their existing checkpoint and native handles to retain the current candidate, completed prerequisites, outstanding checks and remaining limits. The [Design Loop contract](/C:/Users/danhm/.codex/worktrees/108e/orchflows/example-workflows/design-loop/references/design-loop-contract.md:15) already owns such a record. Do not add a parallel ledger or require checkpoint files for a short notice.

**Budgets:** define the counted unit before execution and count it at the operation boundary. Distinguish target launches, control outcomes, audit cases, repeated validation and time. Count retries where the applicable limit includes attempts. Include malformed-output variants in the stated accounting rather than silently exempting them because they live in a self-test. When the allowance cannot cover all desired checks, preserve the bound and report the uncovered checks.

Apply this in the runner produced by Benchmaker under its existing [benchmark contract](/C:/Users/danhm/.codex/worktrees/108e/orchflows/example-workflows/benchmaker/references/benchmark-contract.md). Update authoring guidance from the observed omission and trial the generated runner. Do not turn the core installation CLI into a scheduler. Use supported deadlines and owned-process cleanup where actual execution controls exist; a written deadline alone is not enforcement. Resumption consumes the remaining allowance unless the caller explicitly extends it.

**Output placement:** in builder and export work, establish separate package and trial-output destinations before running validation. Keep reusable requests and expectations in the package; keep actual reports, logs and run outputs outside it. Inspect the package diff before delivery. This check detects misplaced output; it is not a filesystem security boundary. Leave frozen failed trials unchanged as evidence.

**Expected benefit:** fewer premature repairs, stale acceptance claims, hidden budget overruns and contaminated reusable libraries. Keep the correction at its existing owner rather than creating a shared workflow for every check.

## Shared library and future custom workflows

Retain [compare-candidates](/C:/Users/danhm/.codex/worktrees/108e/orchflows/example-workflows/shared/skills/compare-candidates/SKILL.md) and [review-revise-once](/C:/Users/danhm/.codex/worktrees/108e/orchflows/example-workflows/shared/skills/review-revise-once/SKILL.md). They preserve meaningful independence and repair contracts across domains. Keep domain-specific components with their domain libraries and user-authored compositions in the user's own libraries.

For example, a purchasing workflow can compose collection, independent comparison, recommendation drafting and bounded review/revision. Its prompt names the purchase and budget; guidance supplies purchasing preferences; the root chooses how many quote collectors to use. The saved comparison and review dependencies survive a change in model capability.

Do not extract standalone components for waiting, gathering, choosing a worker count or writing a status line. Extract another common workflow only when real consumers share a meaningful process contract and reuse removes more complexity than it adds.

## Implementation order and scope

| Order | Work | Main existing owners | Completion criterion |
| --- | --- | --- | --- |
| 1 | Remove accidental fresh-worker requirements from ordinary Design Loop stages; simplify the game entrypoint. | The Design Loop components and game workflow linked above; their existing guidance/references. | Required dependencies, counts, isolation and independent judgments remain explicit; production staffing is flexible. |
| 2 | Improve complete leaf handoffs, evidence-based closure, output destinations and budget accounting. | [Core architecture](/C:/Users/danhm/.codex/worktrees/108e/orchflows/docs/architecture.md), [work primitive](/C:/Users/danhm/.codex/worktrees/108e/orchflows/skills/orch-work/SKILL.md), [review primitive](/C:/Users/danhm/.codex/worktrees/108e/orchflows/skills/orch-review/SKILL.md), [builder](/C:/Users/danhm/.codex/worktrees/108e/orchflows/skills/orch-build-workflow/SKILL.md), [export workflow](/C:/Users/danhm/.codex/worktrees/108e/orchflows/example-workflows/export-workflow/skills/export-workflow/SKILL.md), and Benchmaker's existing contract/guidance. | Modify only genuine gaps; delete duplicated instructions. Generated artifacts demonstrate the intended behavior. |
| 3 | Check and use native child restrictions where feasible. | Existing host integration and host documentation. | State exactly what is enforced, instructed or unsupported, with an actual boundary test for enforcement claims. |
| 4 | Replay affected behaviors and consolidate documentation. | Existing trial fixtures, temporary runners and current documentation owners. | Evidence supports each claimed improvement; unresolved cases stay visible; total required prose is assessed for reduction. |

Keep old reports and failed artifacts intact. Update reusable trial expectations when the intended contract changes. Do not copy this planning document wholesale into live agent instructions or edit every listed file merely to restate an existing rule.

## Validation plan

Use ordinary requests without expected answers or authoring history. Freeze source identities. Keep request, model, host mode, preparation and bounds matched when comparing old and new behavior. Report changed variables and retain unsuccessful attempts. Use repeated bounded runs before claiming a reliable speed or compliance improvement; a single success demonstrates only that path.

| Trial | Evidence required |
| --- | --- |
| Small and wide dynamic tasks | Correct outputs, root-owned fan-out/gather and required independent review. Record staffing; do not require a particular worker count. |
| Two-cycle Design Loop | Preserved stage dependencies and pre-implementation evaluation plan; independent comparison; correct cycle count and accepted state. Complete within the original bound or stop honestly with resumable partial work. Report elapsed time and launches separately. |
| Browser Game | Core judgment and readiness before final assets; final review on the production candidate; required gameplay on the delivered revision after relevant repairs, or an explicit incomplete result. |
| Benchmaker | Auditor receives the complete public contract without evaluator secrets; no child delegation; actual accounting includes exercised control variants; zero target launches stays zero. |
| Export, including unavailable reviewer | Trial precedes authoring review; completed review precedes repair. Failed launch must not silently trigger repair. A saved final summary alone does not prove independence. |
| Personal-library builder | Reuses shared components under root dispatch; remains reusable with a different ordinary request; actual trial evidence is outside the installable package. |

Reuse the existing [native audit tooling](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/audit.py) and [output checks](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/verify_outputs.py) where they fit. Inspect child-own events rather than inherited parent history. Distinguish output correctness, process compliance, infrastructure failures and resource compliance.

After implementation, run the required core suite and whitespace checks. The prior [test record](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/core-tests.txt) reports 126 tests run, 125 passed and one platform skip; those results do not validate these proposed changes. Add focused tests for any new deterministic mechanics, not tests that merely search for prescribed prose.

## Limits and evidence access

The timestamp defect requires a task-specific software fix and validation. The [independent reproduction](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/independent-audit.md:24) states:

> Fresh CLI reproduction produced exit **0**, empty stderr, and replaced both sentinel files.

That failure is also retained in [output-checks.json](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/output-checks.json). No architecture change proposed here makes generated code infallible. Preserve the regression case and keep its repair separate from general orchestration instructions.

The linked audits are observer assessments, not raw transcript quotations unless explicitly identified. They name the underlying native session files and locations. [audit.json](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/audit.json) and [inventory.json](/C:/Users/danhm/.codex/worktrees/108e/orchflows/reports/dogfood-20260917/inventory.json) provide the consolidated trace and run indexes. Raw requests, frozen installed identities, artifacts and native sessions remain under [the temporary trial root](/C:/Users/danhm/orchflows-dogfood-20260917).

The quotes make this plan readable on its own; the absolute links point to this machine's retained evidence and must be accompanied by the relevant files for an external reviewer without filesystem access. The evidence supports targeted simplification and stronger execution boundaries. Whether those changes improve reliability across models and hosts remains a matter for the proposed trials.
