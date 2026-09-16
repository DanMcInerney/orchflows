# Software factory versus a single agent

Four completed builds of two applications, with their code and evidence. The workflow caught and fixed a real nested-JSON bug at higher time and token cost. Both approaches passed the fixed acceptance suites. One run per approach per task does not establish a general winner.

The workflow runs used [software-factory 0.1.0 at commit 1a04d852](https://github.com/DanMcInerney/orchflows/tree/1a04d85254455012b9f73e2bced43218f9f755f5/example-workflows/software-factory). These are the original frozen outputs, including the flawed workflow log patch and the single-agent nested-JSON defect. The later 0.1.1 handoff fix has not been substituted into this comparison.

## Results side by side

| Measure | Webhook: factory | Webhook: single agent | Logs: factory | Logs: single agent |
| --- | ---: | ---: | ---: | ---: |
| Independent acceptance checks | 28/28 | 28/28 | 31/31 | 31/31 |
| Build + handoff time | 25.6 min | 17.2 min | 42.4 min | 16.4 min |
| Agent contexts | 6 | 1 | 10 | 1 |
| Uncached input tokens | 362,300 | 102,156 | 762,299 | 117,821 |
| Cached input tokens | 5,376,640 | 772,992 | 13,387,264 | 1,337,856 |
| Output tokens | 76,085 | 31,283 | 118,011 | 27,110 |
| Warm-search speedup | — | — | 374.7× | 620.8× |
| Supplemental deep-JSON probe | — | — | Pass | API/CLI crash |
| Release outcome | Human review required | Human review required | Simulated rollback verified | Simulated rollback verified |

Times include coordination, host scheduling and handoff. Agent counts include the coordinator. Output includes reasoning; cached input is reused context, not unique text. The short warmed query loops do not establish a precise production performance ranking. The deep-JSON probe is exploratory and remains outside the fixed acceptance score.

## Code and artifacts

| Task | Software factory | Single agent |
| --- | --- | --- |
| [Webhook inbox prompt](cases/webhook-inbox/prompt.md) | [Code, tests and usage](runs/webhook-inbox/workflow/project/) · [Handoff](runs/webhook-inbox/workflow/artifacts/HANDOFF.md) · [All artifacts](runs/webhook-inbox/workflow/artifacts/) · [28-check result](results/webhook-inbox/workflow/external.json) | [Code, tests and usage](runs/webhook-inbox/single/project/) · [Handoff](runs/webhook-inbox/single/artifacts/HANDOFF.md) · [All artifacts](runs/webhook-inbox/single/artifacts/) · [28-check result](results/webhook-inbox/single/external.json) |
| [Log archive prompt](cases/log-archive/prompt.md) | [Code, tests and usage](runs/log-archive/workflow/project/) · [Handoff](runs/log-archive/workflow/artifacts/HANDOFF.md) · [All artifacts](runs/log-archive/workflow/artifacts/) · [31-check result and timing](results/log-archive/workflow/external.json) | [Code, tests and usage](runs/log-archive/single/project/) · [Handoff](runs/log-archive/single/artifacts/HANDOFF.md) · [All artifacts](runs/log-archive/single/artifacts/) · [31-check result and timing](results/log-archive/single/external.json) |

Read the [full report](REPORT.md), [original experiment plan](PLAN.md), [machine-readable comparison](results/comparison.json) and [usage breakdown](records/usage-summary.json). The original plan's instruction to retain applications locally describes the initial run; the user subsequently requested this publication.

Review and release evidence includes:

- [Webhook specialist reviews](runs/webhook-inbox/workflow/artifacts/reviews/pass-1/) and [joined findings](runs/webhook-inbox/workflow/artifacts/joined-review.md).
- [Initial log correctness review](runs/log-archive/workflow/artifacts/review-correctness/REPORT.md), [repair handoff](runs/log-archive/workflow/artifacts/builder-pass2.md) and [joined reviews of the repaired candidate](runs/log-archive/workflow/artifacts/joined-pass2.md).
- [Identical supplemental probe results](results/supplemental-deep-json/result.json) for the reference and both log implementations.
- [Original patch audits](records/artifact-inspection.md), including the LF export defect and the explicitly tracked-only control patch.
- [Workflow rollout report](runs/log-archive/workflow/artifacts/release/REPORT.md), [single-agent rollout state](runs/log-archive/single/artifacts/release-state.json) and the [shared simulation policy](tools/RELEASE_POLICY.md).
- [Webhook evaluator correction](records/evaluator-correction-1/record.json) and its retained original failed evaluation under [attempt-1-harness-error](results/webhook-inbox/workflow/attempt-1-harness-error/).

## Rerun the independent checks

Use Python's standard library. The original environment was Windows with Python 3.14.6; the tasks declare Python 3.11+, but other versions and platforms were not tested in the original comparison. From this directory, run each command sequentially, writing fresh results separately from the archived evidence:

```sh
python -B evaluation/webhook-inbox/evaluate.py --project runs/webhook-inbox/workflow/project --output .recheck/webhook-workflow.json
python -B evaluation/webhook-inbox/evaluate.py --project runs/webhook-inbox/single/project --output .recheck/webhook-single.json
python -B evaluation/log-archive/evaluate.py --project runs/log-archive/workflow/project --output .recheck/log-workflow.json
python -B evaluation/log-archive/evaluate.py --project runs/log-archive/single/project --output .recheck/log-single.json
```

The webhook evaluator uses real HTTP over loopback with temporary databases. It exits unsuccessfully on a failed or errored check. The log evaluator exits successfully when it writes its report: inspect **`correctness_passed` and `acceptance_passed`**, not just its exit status. It generates its own deterministic 30,000-record workload; bulk benchmark datasets are not needed. New timing values will vary and must not replace the historical results above. Evaluator details: [webhooks](evaluation/webhook-inbox/README.md) and [logs](evaluation/log-archive/README.md).

Each application's README documents its API/CLI and tests. Supporting scripts inside historical artifacts record the original run and may depend on omitted scratch worktrees, local Git objects or the original paths. The commands above are the supported entrypoints for rechecking the published source; historical release-state files remain evidence of the original simulation.

### Publication verification

All 434 archived files match their published hashes, and the 77 Python files and 10 patches/diffs also match their original bytes. Fresh checks of these published copies passed 28/28 for the single-agent webhook and 31/31 plus the speed target for each log implementation.

The workflow webhook returned 27 passes and one **evaluator startup error** in each of two fresh attempts. Both errors were Windows `PermissionError` while `harness.py` read its own readiness file, before the affected check's assertions ran; the affected checks differed between attempts. The evaluator and applications remain unchanged. This does not replace the historical 28/28 result or count as a successful fresh full run. [Fresh outputs and verification summary](publication-verification/README.md) retain both failed attempts. The archived evaluator has this known Windows startup limitation.

## Provenance and limits

Both arms received identical starter bytes and product prompts, the same tools, a 45-minute cap, and the same observed model/effort (`gpt-6-astra`, `xhigh`). Workflow builds ran first; fresh single-agent controls received no workflow solutions or findings and could not delegate. Final candidates were frozen before external grading. Neither approach was repaired after the score was known.

The archive preserves application/evaluator Python files and delivered patches byte-for-byte. Machine-specific paths in supporting documents and structured evidence are rewritten for publication; original and published hashes and transformations are recorded in [PUBLICATION.json](PUBLICATION.json). Historical hashes inside reports refer to their original files. The archive's `.gitattributes` preserves file bytes across checkout newline settings and excludes existing archival whitespace from formatting checks. Original Python/patch bytes can retain machine-specific paths; their fidelity takes precedence over path normalization.

This is a curated evidence archive, not a native chat transcript dump. It omits private host history, Git metadata, caches, duplicate worktrees, temporary databases and generated bulk inputs. The webhook credentials in example configurations and tests are synthetic fixture values. The original private experiment workspace remains unchanged.

There was one run per approach per case and no equal-compute claim. Concurrent builds may have competed for host resources; external performance grading was sequential. Rollout signals were synthetic local observations. There was no live cloud deployment, production incident mitigation, recurring observation, game-quality assessment or virality test. See the [full report](REPORT.md) for evaluator calibration, corrections and the distinction between fixed scores and exploratory probes.
