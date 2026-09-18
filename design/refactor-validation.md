# Refactor validation

Worktree: `codex/flat-workflow-composition`, based on `b9675e5b`. This records development trials, not a claim that every workflow or host conforms. The [design](composable-workflows.md) defines the refactor and acceptance questions.

## Evidence and preparation

Local evidence is under `C:/Users/danhm/orchflows-refactor-trials-20260918/`. Each native case has its request, frozen package copies, outputs, JSONL events and exit record. Snapshot hashes identify the tested bytes; early snapshots are not silently relabeled as tests of later source. Trial inputs exclude evaluator expectations and authoring history. Model and effort were left unspecified. Native defaults and user configuration still apply.

The standalone Codex CLI 0.144.0 rejected the configured model before workflow execution. The already-installed desktop CLI 0.154.0-alpha.6.2 ran the subsequent Codex trials. Claude Code 2.1.270 ran its trials. No global registration, configuration change, dependency installation or publication was part of these cases. Direct file loading and native child execution do not establish plugin-name discovery.

## Observed cases

| Case | Observation | Limit |
| --- | --- | --- |
| Bootstrap Codex | Four procedure levels in one coordinator, direct drafting, one fresh native reviewer, then one wording repair and checks. Correct costs, uncertainty and separate campaign guidance. | The repair rejected “fictional,” although the caller supplied that metadata. It shows review/repair execution, not discovery of a false project fact. Package manifests were absent from this early fixture. |
| Bootstrap Claude | Same composition; two native makers and one reviewer, all root-owned leaves. Completed review preceded one repair. Brief facts and costs correct; campaign preferences were not applied to the brief. | The reviewer read campaign guidance as reference material; the coordinator incorrectly claimed it never reached review. Campaign language overstated how complete the source was. About 392 seconds exceeded the soft six-minute target. |
| Documentation authoring pilot | Revised work primitive produced two shared-library README updates. Fresh independent review found no actionable issue; link/whitespace checks passed without repair. | Static documentation review, not a runtime trial. |
| Missing independent review | Claude ran with only Read/Write/Edit tools. Preserved the flawed candidate, checked the source discrepancy, and reported the missing independent review. No repair or false independent verdict. | Explicitly constrained host case; does not test every unsupported control. |
| Initial authoring | Built a reusable two-workflow library with separate guidance, ran one fresh-session trial with independent output review, and independently reviewed the library. Output was a source-grounded 118-word update; both reviews reported no repair. | Authoring review began before the trial finished and received completion evidence as a supplement. This fails the intended ordering. Final reporting exceeded the nine-minute limit; total about 574 seconds. |
| Corrected authoring | Built a one-workflow library with separate guidance and core review/revision reuse. Its completed trial delivered a source-grounded update after one reported review and one wording repair. The library reviewer launched after the trial finished; no library repair was required. | The nested trial used ephemeral execution, so its retained stream cannot verify reviewer parentage, full assignment context or settings. Overall runtime was 757 seconds, exceeding twelve minutes by about 37 seconds; nested trial timing was also overstated. Allowance increased from the first run, so this is not a controlled attribution to wording alone. |
| Design Loop | Direct production plus one fresh comparison produced a converter passing 28 planned subprocess cases. A timeout left a stale checkpoint, one started attempt and the unchanged baseline. A fresh coordinator reconciled completed evidence, adopted the same candidate and delivered it with one attempt completed and zero remaining. | Initial nine-minute request did not finish: the external launcher stopped it after about 601 seconds. Recovery received an explicit four-minute extension, completed in 230 seconds, and added no cycle or comparison. This tests one interruption point, not arbitrary recovery. |
| Evolve | One artifact round established and calibrated an evaluator, used a fresh maker and separate reviewer, confirmed the candidate, then promoted it. Thirteen delivered unit tests passed again when run by the refactor coordinator. One attempted round and zero remaining are durable. | Local speed measurements apply only to the trial's workloads; they are not evidence of workflow-refactor performance. The final response's “8m54s” describes its internal decision timer; total launcher time was 563 seconds and exceeded the nine-minute request. Subjective judging and harness evolution remain untested. |

The independent bootstrap audit is `bootstrap-audit.md` in the evidence directory. It checks actual native parentage, child tools, reviewer completion, candidate changes, calculations, links and snapshots. Codex's review completed at 02:23:07.292Z before repair at 02:23:30.875Z. Claude's review completed at 02:24:24.062Z before repair at 02:24:41.931Z. No child delegation was found. Both runs used shared files and broad host tools; observed compliance is not host enforcement or a secrecy boundary.

Corrected authoring's trial completion was recorded at 02:48:20.925Z and its native library-review launch at 02:48:56.872Z. The final independent library judgment preserved its evidence qualifications; final reporting exceeded the overall allowance despite an earlier disposition claiming otherwise. The completed trial and launch ordering is established, while the ephemeral child's internal controls remain unverified.

`snapshot-comparison.json` identifies tested-source differences. Corrected authoring copied 42 dependency files; only the later library-documentation anchor/scope clarification differs. Evolve copied 54 and Design Loop 65; their final difference additionally includes the authoring-only wait clarification, outside the loop execution path. Early 27-file bootstrap snapshots differ in ten core files, listed in that record. Design Loop's independent coordinator audit also verifies delivered hashes, direct CLI checks and a single root with no child on resume.

## Changes prompted by use

- Guidance scope now explicitly means which preferences apply, not which shared files are accessible. Another scope's guidance may be inspected as evidence without adopting it. Reporting must distinguish those facts.
- `orch-build-workflow` now requires trial session completion and its required judgments before launching authoring review. A later evidence supplement cannot retroactively satisfy that dependency.
- The obsolete four-core-skill assertion was updated to include the reusable review/revision workflow. The two primitive meanings are unchanged.

The generated campaign's overstatement remains failure evidence. Adding an automatic review to every transformation would change the saved process; no such wrapper was introduced. Missing caller metadata in a review is a context-quality limit, not evidence that fresh reviewer identity alone guarantees good judgment.

Written time bounds did not reliably bound total runtime. Several runs also described their own timing inaccurately. External launcher timestamps take precedence in this report. Hard wall-clock enforcement needs a host deadline or external supervisor; this refactor adds neither. Design Loop's successful recovery demonstrates that a saved procedure can reconcile one interrupted run without a new runtime, given an explicit time extension and valid durable evidence.

## Static and integration checks

- Baseline and final post-change core suites: 126 tests, 125 passed and one platform skip.
- Changed skill frontmatter and invocation metadata: 21 files parsed with YAML; names, descriptions, folder identities and both manual-invocation settings checked.
- Changed Markdown: 198 local links and 44 heading targets checked, no missing target after correcting an anchor moved with library-authoring documentation.
- Package-local checks: game 24 links/3 entrypoints; loops 61 links/9 entrypoints; consumer migration 39 links. These establish structure only.
- The bundled generic skill validator rejects `disable-model-invocation` on both existing and new skills. It was not treated as a successful validation; native metadata checks were performed separately. This host field already existed throughout Orchflows.
- All 12 package version sets agree across their four host manifests. Whitespace checks passed. Final independent implementation review completed; its disposition is below.

## Independent implementation review and disposition

A fresh reviewer inspected the stable 126-file candidate against this design and the completed trial evidence. The original judgment is retained as `implementation-review.md`, with reviewed hashes in `implementation-candidate.json`. It found no demonstrated fundamental blocker or static loss of the migrated review, confirmation and attempt gates. It did not claim every host or workflow conforms.

Two documentation findings prompted one repair pass: three library READMEs now match their contexts' core 0.11.0 minimum, and Benchmaker's current-version label now matches its 0.4.2 manifests. Historical version attributions remain intact. The corrected declarations, local links, heading anchors, invocation metadata, manifests and whitespace were checked afterward. No procedure or runtime behavior changed in this repair, so no behavioral trial was repeated.

`implementation-disposition.md` and `implementation-delivered.json` identify the delivered changes and their checks separately from the original review. The repaired documentation has verification, not a second independent verdict. The design status and this validation record were finalized after review; their updated summaries likewise do not inherit the earlier judgment unchanged.

## Size and claim boundaries

Whitespace word counts are descriptive: architecture 1,393 to 971 before the final scope clarification; Evolve entry 928 to 553; game entry 2,394 to 1,020. Author packaging moved to `docs/libraries.md` and methods moved into guidance/references. That reduces entrypoint reading without pretending the moved material disappeared.

The game package's agent-facing skills/guidance/references decreased from about 8,250 to 7,626 words. Evolve's ordinary artifact-round entry plus required context is approximately unchanged (2,243 to 2,275); including its conditional harness contract increases it. That change clarifies attempts and validation independence and makes methods reusable; it is not a demonstrated reduction in total instruction cost.

There is no matched old/new performance comparison here, so no improvement in quality, cost or latency is claimed. Full game production, all acquisition backends, subjective Evolve judging, harness evolution, native plugin registration, distinct model/effort overrides and the other supported hosts remain untested unless later records explicitly add them. No fundamental premise failure has been established by these cases. The corrected authoring ordering and interrupted-loop recovery support proceeding with the small design, while instruction following and output quality still require honest evidence and selective review.
