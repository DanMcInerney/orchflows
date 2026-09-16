# Review dispatch plan

Every reviewer is a fresh orch-review child who did not build the candidate. Apply Review sections of core/guidance/code.md followed by software-factory/guidance/software-delivery.md. Absolute dependency roots and deadline are in brief.md. Model/effort omitted. No repairs or delegation.

After build freeze: coordinator verifies all required checks, source commit plus note manifest, and preserved files. Create isolated detached worktree per reviewer at exact candidate commit, with caller-note.txt copied byte-for-byte. Raw outputs, scratch tests, reports live outside source under artifacts/review-{lens}; review snapshot not edited. Compare commit/source hashes to frozen candidate. Pass actual builder report, check outputs and benchmark data to each review.

## Correctness
Read TASK.md, entire public README contract, actual API/CLI code/tests and benchmark. Assess behavioral acceptance, implementation logic, validation and error handling, concurrency/file freshness under complete append/truncate/atomic replace, stable ordering, all-match AND ASCII tokens, pagination/total and independent objects. Verify high-impact gaps with targeted standalone scripts in scratch. Benchmark must be paired, sequential, identical workloads, warmed, alternating two rounds, every timed answer checked against baseline, >=5x. Assess Python 3.11+ and current actual runtime. Report candidate identity, commands/evidence, actionable findings with location/consequence/repro, missing context and lens risk.

## Data
Read full input/output contract and implementation. Focus malformed records, valid timestamp boundaries, complete nested extra fields and duplicate records, physical source-order ties, caller ownership, cache path separation and replacement freshness, concurrent coherent versions. No durable writes to archive or irreversible migration is expected. Use isolated scratch fixtures. Findings need demonstrable contract impact. No changes.

## Infrastructure
Read local release policy, run context, candidate operation docs/check commands and simulator source/status. Assess required checks and reproducible benchmark, runtime/CLI operability, frozen artifact/evidence linkage, staged exposure and observability thresholds, exact stop/rollback/recovery commands and supported authorization. Read simulator status only; do not execute deploy/observe/rollback or mutate release state. Assess risk for bounded local simulation; do not infer live deployment capability or remote CI requirement.

Reviewer reports must say complete/blocked, list missing context and unresolved actionable findings, and classify lens risk with rationale. Correctness is not approved by a mere successful public smoke check. Coordinator joins all reports and revisits applicable lens coverage before risk routing.

