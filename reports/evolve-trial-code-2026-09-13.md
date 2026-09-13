# Evolve runnable-artifact trial — 2026-09-13

Completed two real search rounds in an unrelated disposable Python project. The workflow inferred its own evaluation, promoted a verified faster implementation, rejected the second candidate and applied the retained winner. The trial found and helped repair an incomplete metric-review handoff; it also exposed avoidable verification after failed screening.

## Request and preparation

The coordinator received this complete task request:

> Improve this project’s duplicate finder. Preserve its public behavior. Run two rounds. Use this project directory for outputs.

The trial supervisor created `C:/Users/danhm/tmp/evolve-code-65607f1672/` with an ordinary README, an intentionally quadratic `duplicates.find_duplicates` implementation and seven `unittest` behavior checks. The function accepts a finite iterable, follows Python equality, returns each repeated value once in first-repeat order, accepts unhashable values and leaves the input unchanged. The examples and tests exercise empty/unique input, ordering, strings, generators, lists, numeric equality and mutation. They supply behavior, not a score, benchmark, ranking, evaluator or improvement threshold. All seven original tests passed with Python 3.14.6 before dispatch.

The supervisor then applied `orch-work` and launched a fresh coordinator with no inherited conversation. Additional context supplied only the target/output directory, exact absolute workflow/core/guidance paths, available native child tools and Python, a local/small-experiment limit, and the prohibition on writing outside the target. The coordinator was told to read and follow the workflow and its package references. Evaluation design and child orchestration were left to that workflow. The package was loaded by file path; installation or native skill-name registration is not claimed.

The resolved target guidance was `guidance/code.md`. The supervisor used `guidance/orchflows.md` and `guidance/writing.md` when producing this report. No skill changes are owned by this trial.

## Identities at launch

Repository root: `C:/Users/danhm/.codex/worktrees/a868/orchflows-light/`.

| Input | SHA-256 |
| --- | --- |
| `example-workflows/evolve/skills/evolve/SKILL.md` | `8C4E69E630D303503017E6F1E05BE4F16138D3A241E402126D64EB3A2EADA85F` |
| `example-workflows/evolve/skills/evolve/references/evaluation.md` | `25CFBEB79D84AC9E5AE86D7780D222FE64978956CFDFEE8D558CCE51467C3678` |
| `example-workflows/evolve/skills/evolve/references/state.md` | `866E9C8E5AC37B9FEAEF157D7541FC315E3BEE9E9EE0CD903DF420716C994FC8` |
| `example-workflows/evolve/references/library-context.md` | `933F4074AB3FFD71CD1221152F2C6BFBEEFE5E52BCCFDEBE5C326D0457704C7A` |
| Target `duplicates.py` | `FA07898E8ED70A6585944E6A34C216A86CD00DFAFB17E162B83BBEDF218DE306` |
| Target `tests/test_duplicates.py` | `5A52069DC12F761BC3893037F1633F415C423E7265EA093FDDBE0181A50D9052` |
| Target `README.md` | `A510A35150BDEB6F70D8297EB86A3FFD8A63B020B4E3CD8D41AA8FA4A235C016` |

Coordinator handle: `/root/trial_code/evolve_code_coordinator`. Launch was approximately 2026-09-13 04:23 UTC. The supervisor is `/root/trial_code`; it is trial preparation/reporting overhead, separate from the workflow's agent count.

## Observed execution

The coordinator inferred runtime improvement on common built-in inputs, preserved general Python equality as a requirement, and labeled performance as a workload-specific claim. Before dispatch it created an original snapshot, brief, evaluator, judge prompt, working harness, journal and checkpoint. It imposed one challenger per round and inherited model settings; exact model/effort and token consumption were not exposed.

Evaluation v1 uses the original implementation as a differential oracle. It checks first-repeat order and returned-object identity, generator/equality traces, NaNs, unhashable/mixed/custom values, nonmutation and the unchanged project tests. The seed passed 232 differential cases and all seven original tests. An obvious broken function failed 219 differential cases and the original tests, establishing that calibration could reject a defect.

The coordinator generated six timing workloads, five alternating samples with three invocations per sample, median timings and geometric-mean speedup. Its inferred promotion rule requires at least 1.10× aggregate speedup, no workload below 0.70×, preserved requirements and a second matched measurement run with fresh confirmation cases. This numerical goal and its tradeoff were created by the workflow, not supplied in the task. The coordinator saved a complete independent judge prompt and reserved confirmation generation, while explicitly acknowledging that filesystem access does not enforce secrecy.

Round 1 dispatched the fresh maker `/root/trial_code/evolve_code_coordinator/make_01` after saving its plan, parent hash and exclusive candidate write scope. It produced a dictionary index for exact built-in scalar types and permanently returned to the original list scans when arbitrary equality/hash behavior could matter. The coordinator froze the candidate before scoring. Screening passed 232 differential cases and seven original tests; confirmation passed 394 cases and those same tests. Measured geometric-mean speedup was 10.0304× in screening and 9.5980× in confirmation. The smallest workload ratios were 0.8465× and 1.0290×, respectively, passing the inferred 0.70× floor.

Fresh reviewer `/root/trial_code/evolve_code_coordinator/review_alpha` received task-only context and neutral A/B copies. It verified the exact hashes and arithmetic, ran 1,800 additional differential cases plus five custom equality-trace checks, and preferred the challenger without requirement failures. The coordinator journaled promotion, then updated the checkpoint to `snapshots/round-01/`, hash `f96957818fafdd38bd606b289bf231c466d7477bbf1c561e92a75e42f4f1a8fe`. It retained the original and saved the plan and native handle for round 2.

The first reviewer initially stated that the timing-harness implementation and reserved-case freshness were unavailable for its independent inspection. Its neutral bundle included criteria, environment, artifacts and raw reports, but not the implementation of `evaluate.py`. After the author repair described below, the same reviewer received the omitted evidence and completed a separate limited measurement audit. It verified exact scoring bytes, actual fixtures, the original oracle, timing sequencing, aggregation and case-selection mechanics; its preference remained unchanged. The original review and its limitations were preserved. No broad behavioral retesting or timing replay was performed during that follow-up.

Round 2 ran from the promoted snapshot with a concrete hypothesis about redundant list/index bookkeeping and fallback dispatch. Maker `/root/trial_code/evolve_code_coordinator/make_02` produced lazy fallback materialization, frozen at hash `38f416dc32ddaa969002533b02a3c3b3d7ee475d0df797d5f92c792c37ac1d85`. It passed behavior checks but failed the fixed performance rule: coordinator screening measured 0.9709× geometric-mean speedup against round 1, with a 0.6882× worst workload. The coordinator also ran confirmation, measuring 1.0148×, still below 1.10×. These are unconfirmed/no-improvement results, regardless of the maker's advisory 1.0643× measurement.

| Round | Parent | Screening speedup | Confirmation speedup | Status |
| --- | --- | --- | --- | --- |
| 1 | Original | 10.0304× | 9.5980× | Promoted; independent review and added measurement audit passed |
| 2 | Round 1 | 0.9709× | 1.0148× | Rejected under the fixed rule; round 1 retained |

The coordinator performed confirmation after a failed round-2 screen and initially planned a review of that nonwinning candidate. The parent clarified that its earlier round-2 handoff instruction applied only if screening warranted review, then directed the coordinator to skip the extra reviewer and finish after the first reviewer's measurement audit. No second reviewer was dispatched. The spent confirmation and prepared unused review bundle are avoidable overhead; the failed screen already required retaining round 1. The confirmation took approximately 0.554 seconds of reported shell wall time.

The coordinator applied round 1's source and focused tests to the project. All 12 final project tests passed; the original README and seven-test source remained byte-identical to preparation. The supervisor independently checked those file hashes and that the applied source matches the checkpoint's retained snapshot. The final checkpoint is `complete`, with no in-flight work, two completed rounds, zero remaining rounds and the explicit stop reason `Caller-selected two-round bound reached.` Original, previous best, current best and the rejected alternative remain available. Harness v1 and evaluation v1 stayed fixed; no harness improvement is claimed.

## Evidence and observed cost

All run evidence is inside `C:/Users/danhm/tmp/evolve-code-65607f1672/`:

| Evidence | Exact path |
| --- | --- |
| User-facing run result | [EVOLVE_RESULT.md](C:/Users/danhm/tmp/evolve-code-65607f1672/EVOLVE_RESULT.md) |
| Inferred evaluation and margins | [public.md](C:/Users/danhm/tmp/evolve-code-65607f1672/evaluation/v1/public.md) |
| Generated scoring implementation | [evaluate.py](C:/Users/danhm/tmp/evolve-code-65607f1672/evaluation/v1/evaluate.py) |
| Seed and obvious-defect calibration | [seed.json](C:/Users/danhm/tmp/evolve-code-65607f1672/evaluation/v1/seed.json), [calibration-defect.json](C:/Users/danhm/tmp/evolve-code-65607f1672/evaluation/v1/calibration-defect.json) |
| Complete generated judge prompt | [judge-prompt.md](C:/Users/danhm/tmp/evolve-code-65607f1672/evaluation/v1/judge-prompt.md) |
| Round 1 raw measurements | [screen.json](C:/Users/danhm/tmp/evolve-code-65607f1672/experiments/01/screen.json), [confirm.json](C:/Users/danhm/tmp/evolve-code-65607f1672/experiments/01/confirm.json) |
| Round 1 review and completed audit | [review.json](C:/Users/danhm/tmp/evolve-code-65607f1672/experiments/01/review/review.json), [measurement-audit.json](C:/Users/danhm/tmp/evolve-code-65607f1672/experiments/01/review/measurement-audit.json) |
| Frozen audit source, inputs and commands | [manifest.json](C:/Users/danhm/tmp/evolve-code-65607f1672/reviews/0f1842a94a/audit/manifest.json) |
| Round 2 screening and retention decision | [screen.json](C:/Users/danhm/tmp/evolve-code-65607f1672/experiments/02/screen.json), [decision.json](C:/Users/danhm/tmp/evolve-code-65607f1672/experiments/02/decision.json) |
| Final test output | [final-project-tests.txt](C:/Users/danhm/tmp/evolve-code-65607f1672/evidence/final-project-tests.txt) |
| Working harness | [instructions.md](C:/Users/danhm/tmp/evolve-code-65607f1672/harness/v1/instructions.md) |
| Journal and resumable state | [journal.jsonl](C:/Users/danhm/tmp/evolve-code-65607f1672/journal.jsonl), [checkpoint.json](C:/Users/danhm/tmp/evolve-code-65607f1672/checkpoint.json) |

The workflow used four distinct agents: one coordinator, two fresh makers and one fresh independent reviewer. The reviewer received one additional authorized audit turn. The trial supervisor is one additional preparation/reporting agent, not part of evolve's agent count. Native handles are saved under each experiment and in the journal. Neither a harness proposer nor a second reviewer was launched.

Initialized state was recorded at 04:25:04 UTC and final application at 04:42:16 UTC on 2026-09-13: approximately 17.2 minutes, plus preparation and initial context reading. The coordinator recorded 1.593 seconds inside the paired benchmark calls. This narrow timing total excludes evaluator construction, correctness checks, agents, review and shell overhead; it is not a total compute-cost claim. Maker 1 reported four shell calls. Token use, monetary cost and complete aggregate shell cost were unavailable. Evaluation preparation and orchestration dominate this small trial's wall time.

## Interventions and limits

The original quadratic implementation and behavior examples were deliberately prepared by the supervisor. The task therefore tests portable operation with an ordinary, inspectable target, not discovery of an arbitrary real-world performance problem. The short instruction does not supply a scoring goal, evaluator or target threshold.

The first in-flight author intervention occurred before judging: the parent revised `evaluation.md` to require task-only judge context, neutral artifact labels/paths for subjective comparisons, and explicit acknowledgment that a shared filesystem is not a secrecy boundary for reserved cases. The supervisor relayed the change and asked the coordinator to reread the reference before judgment. The revised file hash was `D8503A7C5C3BC0E8D3E340175E7E50547FA4B85603BAD5B5834BDA08AAF04BC9`.

The second intervention followed the observed metric-review handoff gap. The author revised `evaluation.md` to explicitly supply frozen scoring code, workload inputs and commands/environment to metric reviewers. The supervisor relayed the repair, asked the coordinator to include that evidence for round 2, and, at the parent's direction, requested a follow-up to the same round 1 reviewer for the omitted measurement audit. This adds an inspection turn rather than a new reviewer or search round; there was no request to rerun the broad behavioral fuzz checks. The revised file hash was `2CE3137E5D74E17EFC5B74BFAF324B51DDC035308864BC183A192A8D6178AFF4`.

One further runtime clarification followed: the supervisor relayed the parent's instruction to skip a fresh reviewer for round 2 after its failed screen. The coordinator had interpreted the repaired handoff request as requiring that review. The parent clarified the conditional scope; the already spent confirmation remains recorded as overhead.

The two package revisions and runtime clarification were author interventions during a behavioral trial, not experimentally validated harness improvements. They limit any claim about an untouched start-to-finish package revision. The second package change repaired a gap observed in use, and the same reviewer's completed measurement audit verified the repaired handoff. A fresh initial reviewer receiving the repaired bundle was not exercised because the second candidate failed screening.

Reserved confirmation cases were excluded from maker context by instruction; makers reported no access. Shared filesystem access does not establish secrecy or independently prove non-access. The independent audit checked case-generation mechanics; it did not attest historical host load or execute a new timing replay. Behavior checks are finite, and mutation checks do not prove arbitrary nested-object immutability. Observed speedups apply to six small local Python 3.14 workloads, with extra index memory and quadratic fallback behavior still present.

This two-round trial does not establish indefinite continuation, interrupted-run recovery, long-run regression control, harness self-improvement, tournament behavior, unseen-task generalization or RSI Level 1. It does not exercise image, audio or interactive inspection. It does establish that a portable ordinary request without a supplied score can cause the workflow to construct a runnable evaluator, verify a real improvement, reject a nonwinning challenger and return a bounded, inspectable result.
