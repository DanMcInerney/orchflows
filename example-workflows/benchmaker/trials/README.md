# Acceptance trials

Run each request in a fresh workspace using the packaged skill, resolved core/guidance and only the request's raw inputs. Withhold the authoring conversation and expected-behavior file from the executing author. The evaluator uses expected behavior afterward. Save generated packages, native child identities, commands, outputs, timings and findings in the caller workspace, outside this library.

| Scenario | Focus | Status |
| --- | --- | --- |
| [Research](research/request.md) | Distinct source-grounded tasks, native execution, supported alternatives | Specified; not run |
| [Stateful planning](stateful-planning/request.md) | Reset, valid actions, preservation and explanations | Specified; not run |
| [Artifacts](artifacts/request.md) | Actual modality inspection and unavailable judgments | Specified; not run |
| [Coding](coding/request.md) | Real workflow invocation and delivered behavior | Specified; not run |
| [Unreliable adapter](unreliable-adapter/request.md) | Overlap, cleanup, durable partial results, retries/resume | Specified; not run |
| [Description only](description-only/request.md) | Useful provisional package without invented execution | Observed locally, 2026-09-16; bounded development validation |

These specifications are not evidence that a run occurred. A bounded trial can expose defects and validate the observed behavior; completing one does not establish cross-domain acceptance. See each scenario's sibling `expected-behavior.md` for its observable checks.

The description-only trial produced a four-case Python-standard-library scheduling package. All 16 declared control outcomes matched; two public-input answers were saved before reference disclosure and independently confirmed valid. One pilot and one reviewer were used. Three runner/test defects were repaired in one pass; seven final harness checks passed both in place and from a standalone copy. Cases and scorer were unchanged by repair; the original control evidence was preserved. Target/representative executions and target scores were zero. Explanation judgments are not calibrated, and actual target integration remains untested.

The separate library review found that public-input audit instructions needed to explicitly exclude inherited authoring history. That instruction was repaired to require the no-history context and staged disclosure already used successfully in the trial. No post-repair native library replay is claimed. Local evidence is in the authoring workspace at `artifacts/benchmaker/2026-09-16/`, including `VALIDATION.md` and `description-only/TRIAL-REPORT.md`; it is not bundled with the installable library.
