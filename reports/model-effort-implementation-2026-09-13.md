# Model and effort implementation

## Plan and decisions

Keep model and effort optional and assignment-specific. Work and Review defaults reduce repetition; any named worker, reviewer or fixer can differ. Resolve model and effort separately: current run instructions beat saved preferences, and a named assignment beats its operation default within either source. Leave absent native controls unset.

The architecture owns this contract. The two primitives apply it through native host controls; dynamic work also applies it to direct work and repairs. Workflow building saves explicitly requested preferences beside assignments in `SKILL.md`, without copying the authoring session's settings. No model document, role registry, translation layer or runtime is added. Behavioral corrections still belong in removable guidance.

This adopts Fable's review's preference for plain caller instructions and native execution, while allowing users to save deliberate execution preferences in their own workflows. Native defaults need not equal parent settings. A final fixer gets a fresh worker when an existing worker cannot honor its settings.

## Candidate

Release 0.6.3 updates the architecture, host reference, both primitives, dynamic workflow, workflow builder and README. The root and native manifest versions agree. Host references distinguish current Codex spawn controls from Claude agent definitions; unsupported choices are reported before dependent work. Claude execution was not exercised in these trials.

## Migration audit

The task's `origin` now points to `DanMcInerney/orchflows`; the private source remains an archive remote.

An independent read-only comparison at public main `660b69cf57ff7fa8c52dbd9bf19a49614a601611` found all 1,061 tracked source paths present. Their blobs and modes match the source except the intentionally rewritten README. The only added paths were the original MIT license and banner, both identical to their original blobs. Both histories are ancestors of public main; 2,672 original paths were removed. No old runtime, installers, contracts, rules, standards, reader or host-adapter trees remain.

The audit found one stale report link to the now-private source repository; it now points to the same preserved commit in the public repository. No additional tracked-file deletion was warranted. GitHub reports `orchflows` public and `orchflows-light` private. The public repository has no releases or Actions workflows to retire. Historical commits and unrelated branches were not rewritten.

## Verification

The core suite passed: 65 tests, one platform-dependent skip. Plugin validation, all four changed skills' frontmatter validation and `git diff --check` passed. Validation tools used an isolated PyYAML dependency; the library itself gains no runtime dependencies.

### Dynamic execution

A fresh coordinator loaded the candidate by absolute path and used an unrelated disposable Python workspace. Two makers owned independent `double` and `triple` modules. A prepared `quote` module deliberately subtracted their outputs, and the trial request held that known defect until review. This intervention made the repair branch observable; it does not test whether an unsteered workflow would postpone a known repair.

| Assignment | Requested and observed native model | Effort |
| --- | --- | --- |
| Double, using Work defaults | `gpt-5.6-sol` | low |
| Triple, named override | `gpt-5.6-terra` | medium |
| Independent reviewer | `gpt-5.6-luna` | high |
| Final fixer, named override | `gpt-5.6-sol` | medium |

The makers ran concurrently and passed their checks. Joined verification failed as seeded; the fresh reviewer reported the subtraction defect without editing. A fresh fixer changed only the join operator and passed the acceptance checks. It did not reuse the low-effort Double worker. Root independently checked all four model/effort pairs in native `turn_context` records and reran acceptance: `quote(3) == 15`, `quote(0) == 0`.

Native coordinator: `01a09b3c-b913-7781-8dca-5967fa68028a`. Children: Double `01a09b3d-e4dd-7163-90ef-4a94a22b6965`, Triple `01a09b3e-297a-74b2-92ff-3888d810d19e`, reviewer `01a09b3f-3fb1-7633-95c0-41a676026e4b`, fixer `01a09b40-6a0f-7ab3-b53f-1bcfd360d9e9`. Raw transcripts and disposable artifacts remain local.

### Authoring and saved preferences

A fresh maker generated two sentence-case workflows from separate briefs. The first requested saved Work, Formatter and Review settings and retained them beside assignments. The second requested no settings and contained no model or effort preferences. Neither embedded machine paths or introduced a model document. Both declared one maker and one independent reviewer. Author thread: `01a09b3d-552c-7ba3-8865-b949d1673afc`.

A fresh runner invoked the first fixture with current Work model `gpt-5.6-sol`, named Formatter effort `high`, and Review effort `medium`. It correctly replaced the saved named Formatter model with the current Work model, while retaining the saved Review model because that field was unspecified in the run. Root verified the resulting native launches: Formatter `gpt-5.6-sol/high`, reviewer `gpt-5.6-luna/medium`. The title became “Writing better workflows with Python” and independent review passed. Exactly one maker and one reviewer ran. Trial feedback returned to the authoring maker without requiring revisions.

Native runner: `01a09b3e-f157-7a61-b9ef-56f0a5312bd3`; Formatter: `01a09b40-5e09-74c1-93be-39f06457d5e6`; reviewer: `01a09b41-2bf0-7253-aa80-9c2594bd382f`.

### Limits

These are explicit-path candidate trials, not proof of host registration. The no-preferences authoring fixture was inspected but not executed. Claude execution, workflow launches with omitted controls, native configuration overriding launch parameters, unsupported settings, and changing settings on an existing agent remain unexercised. Trials establish the observed small assignments; they do not measure quality, cost or large-task performance of the example models.

### Final independent review

One fresh reviewer assessed the joined candidate and trial records. It found no behavioral blocker and one README ambiguity: omitted current-run settings retain saved preferences, rather than immediately using native defaults. The repair clarifies that only settings absent from both sources use native defaults. This wording-only repair was checked against the shared contract and the observed saved-workflow trial; no additional review was added.
