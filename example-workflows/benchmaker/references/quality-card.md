# Quality card and admission

The card is the benchmark's measured account of itself: the claim, how each task earned admission, and how well the suite separates systems. Plans are not observations. Each entry cites evidence or names a gap. Apply [benchmarking guidance](../guidance/benchmarking.md) for validity and the [benchmark contract](benchmark-contract.md) for records and aggregation.

## Claim

Record the decision the score informs, the claim, the population of work it covers, the complete system boundary, requested stage, budget and assumptions. Record the comparison set with each system's conditions and role.

Record the calibration system that judges difficulty during admission, and the difficulty target it is held to. Unless the caller sets a target, leave headroom: the calibration system should succeed on well under all admitted tasks, typically a minority, so stronger systems and real improvements can show. Prefer a calibration system at least as capable as the target and outside the comparison set. When it is also compared, report the selection bias, and never count its calibration attempts as measurement.

## Task admission

A candidate joins the suite only with evidence that it is:

1. **Solvable.** The reference solution passes the verifier in the actual environment within the task's resources, computing rather than echoing its answer. Answer keys and expected states are verified in full.
2. **Unearned by inaction.** Empty, do-nothing and indiscriminate attempts, such as dumping everything or enumerating answers, earn neither full success nor credit for work they skip.
3. **Specified.** A fresh auditor's outcome, saved before it saw evaluator material, and its later review find every requirement the verifier checks stated in the instruction or interface. Reported ambiguities are resolved or the task is rejected.
4. **Fairly graded.** The verifier accepts a materially different valid outcome and rejects plausible wrong ones, including deliberately broken copies of the reference.
5. **Shortcut-resistant.** A fresh adversary told to earn credit without doing the work fails. It tries the exploit classes in [research](research.md) that the environment permits.
6. **Calibrated.** Repeated attempts by the calibration system meet the difficulty target. A task it always solves is hardened, rejected or kept as an anchor. A task it never solves is admitted only when criteria 1 and 7 hold.
7. **Hard for the right reason.** Its difficulty rationale names the claimed ability, and failure transcripts show that ability failing, not confusion about the instruction, environment faults or grader rejection.

A task that fails a criterion is revised, and its revision reruns the checks the change affects, or it is rejected. Log every candidate's disposition and reason. A task with an unavailable check stays draft.

Anchors are admitted tasks deliberately kept easy or unsolved to check floor and ceiling behavior. They are scored and reported as a small labeled share, and excluded from headroom and discrimination statistics.

## The card

| Property | Evidence |
| --- | --- |
| Validity | Reference pass rate; credit earned by trivial attempts; adversary successes; auditor disputes; verifier false accepts and rejects on labeled outcomes |
| Headroom | Calibration and strongest-comparison full-success rates; distribution of per-task success rates |
| Discrimination | Paired differences between comparison systems with uncertainty; share of pairs separated; agreement with the expected ordering of weaker and stronger systems |
| Reliability | Variation across repeats, `pass^k` where reliability is claimed, signal relative to noise, judge agreement |
| Coverage | Families, independent source groups and tasks against the claimed population; expert time estimates |
| Integrity | Enforced access boundaries, public exposure and source dates relative to the compared systems, systems that filtered admission |
| Cost | Setup, execution and grading time and spend per run |
| Yield | Candidates, admitted, anchors, revised and rejected by reason |

The card states whether measured headroom and separation support the claim. That verdict is separate from the stage. Qualified practitioners give the strongest time estimates, answer-key verification and final audit. When none are available, record the gap and the substitute used.

## Stages

| Stage | Required evidence |
| --- | --- |
| Draft | Claim, candidates and built tasks; admission, measurement or review incomplete |
| Development suite | Every task admitted; the comparison set measured with predeclared repeats; card computed; failures classified; independent review completed with no unresolved blocking finding. Tasks exposed during admission support development claims only |
| Evaluation suite | A development suite; a justified sampling plan; held-out tasks from source groups unused in development, calibrated only by systems outside the comparison set; one predeclared measurement with uncertainty; no unresolved validity defect |

Report requested and achieved stages separately; partial completion does not reach the requested stage. `smoke`, `quick` and `full` select runs, not maturity. Task counts are planning defaults, not scientific minimums. Broad claims commonly need tens of independent source groups in development and hundreds of tasks for evaluation. Narrow claims need fewer, and say so.
