# Software Factory

**Give your next pull request a builder, independent reviewers, and a release plan.**

Describe the change. Software Factory builds it, runs the project's checks, and sends the exact result to fresh reviewers. Findings feed a bounded repair loop. You get the code, the evidence, and a concrete release handoff. Ask it to ship with the required authority and tools, and a separate worker carries the validated artifact through an observed rollout.

**One request can carry the work from implementation through release. Every stage leaves evidence.**

[Try it](#try-it) · [See the flow](#the-same-flow-implemented-with-two-primitives) · [Read the measured results](#what-the-output-quality-comparison-found) · [Install](#install-and-use)

## Try it

After [installation](#install-and-use), paste this into your agent:

```text
Use software-factory:software-factory to add CSV export to this application.
Preserve filtering and tenant isolation. Use P=2 candidate passes. Return
the reviewed change, a complete patch, check evidence, remaining findings,
and a release plan. Save the handoff in delivery/csv-export.
```

| Bring it this | Get back this |
| --- | --- |
| A feature or bug fix | Checked code, applicable specialist reviews, and a release handoff |
| A change requested for release with the required authority | A separate release worker, staged observations, and recorded outcome |
| A production window to inspect | Deduplicated signals and evidence-backed proposals for follow-up work |
| An incident to investigate | A timeline, tested hypotheses, and ranked mitigation options |

Delivery defaults to three candidate passes, stopping earlier when the endpoint is reached. The orchestrator chooses staffing for implementation and independent review. Production observation and incident investigation remain separate, explicit workflows.

## The inspiration

Based on Gergely Orosz's [Inside OpenAI's agentic software factory](https://newsletter.pragmaticengineer.com/p/openai-software-factory), *The Pragmatic Engineer*, September 15, 2026. The original diagram below was supplied by the user and is credited to The Pragmatic Engineer. This library adapts that design to your project's tools; it does not include OpenAI's internal systems.

## The same flow, implemented with two primitives

The diagrams use the same positions, stages and feedback paths. Open either image to read it at full size, or open [the comparison page](assets/comparison.html) locally.

| Original design · The Pragmatic Engineer | Orchflows implementation |
| --- | --- |
| [![Original software factory diagram](assets/openai-factory-original.png)](assets/openai-factory-original.png) | [![Matching Orchflows flowchart](assets/orchflows-factory.svg)](assets/orchflows-factory.svg) |

**`orch-work` and `orch-review` are the only primitives.** `software-factory`, `observe-production` and `investigate-incident` are composing workflows exposed as skills. Loading their `SKILL.md` supplies instructions in the caller; each delegates through the primitives. The operational entrypoints are not independent agent implementations hidden behind a new primitive.

| Part | What it owns |
| --- | --- |
| Workflow `SKILL.md` | Order of work, assignments, branches, retry bounds and when to stop |
| `orch-work` | A fresh child that makes the assigned result using the selected guidance's Make sections |
| `orch-review` | A fresh independent child that applies Review sections, reports findings and does not repair |
| Core `guidance/code.md` | General code quality criteria |
| [software-delivery guidance](guidance/software-delivery.md) | Artifact integrity, specialist review criteria, risk, recovery and production evidence |
| [Run contract](references/run-contract.md) | Candidate identities, evidence, checkpoints, authority and resumption |
| Your project | Source, documentation, acceptance criteria, CI, rollout policy and available telemetry |

## How a delivery runs

1. **Define the outcome.** The coordinator reads the project, preserves the starting state and records acceptance checks, applicable review lenses and existing permissions.
2. **Build.** Use `orch-work` for implementation, relevant documentation and the handoff and rollout plan, assigning ownership across the work.
3. **Check the exact result.** Run required tests, builds, CI and applicable performance checks. A delivered patch must also apply to its recorded clean baseline and reconstruct the candidate, including new files and deletions. The integrated candidate is frozen for review.
4. **Review independently.** Fresh `orch-review` children inspect that candidate in parallel. Correctness is mandatory; data, infrastructure, cloud and security are included when the affected surfaces call for them. They receive real project context and the same candidate identity.
5. **Repair within the bound.** Failed checks or blocking findings inform the next implementation pass. Every revised candidate gets new required checks and applicable reviews. Running out of passes returns unresolved work; it never promotes a failed candidate.
6. **Decide readiness.** Low risk can satisfy the review gate automatically only with explicit project opt-in. Other cases need human review of the concrete diff, check evidence, findings, risk and rollback plan. Missing required evidence still blocks readiness.
7. **Release when requested and authorized.** Assign release through `orch-work`, with one accountable owner for each external operation. Verify the actual published/merged inputs, baseline health, rollback path and stopping criteria, then advance through the project's rollout stages. A breach stops rollout; an already-authorized rollback is applied and recovery checked. Missing telemetry or an unfinished window cannot count as healthy.

Build, validation and deployment are separate checkpoints with recorded evidence. The same builder can run implementation checks, but it cannot approve its own independent review or silently deploy. Approval for one candidate does not cover changed release inputs. The default endpoint is a validated change and release handoff; shipping requires the release stage's authority and capabilities.

The central handoff rule in the guidance is:

> A complete patch must apply to a clean copy of its recorded baseline and reconstruct the candidate, including new files and deletions.

This includes checking the actual saved patch bytes. A passing test suite in the builder's directory, or `git diff --check`, does not prove that someone else can apply the patch.

## Production feedback and bounds

| Workflow | What it returns |
| --- | --- |
| [software-factory](skills/software-factory/SKILL.md) | Checked change, reviews, risk decision and optional observed rollout |
| [observe-production](skills/observe-production/SKILL.md) | Bounded telemetry comparison, deduplicated signals and proposed performance-fix briefs |
| [investigate-incident](skills/investigate-incident/SKILL.md) | Incident timeline, evidence, answers and proposed or specifically authorized mitigation |

Delivery defaults to `P=3` candidate passes, including the first attempt. The orchestrator staffs implementation, applicable review coverage and any authorized release. It stops early when the requested endpoint is reached. A missing required capability or decision returns the checkpoint and gap.

Observation and incident investigation are explicit invocations. Observation is read-only and proposes follow-up work; it does not automatically start a fix. Recurring observation requires a caller-requested host schedule. Incident investigation can perform a specifically authorized operation, but a request to investigate alone authorizes no mitigation. The package adds no daemon, scheduler, service adapters or production access.

## What the output-quality comparison found

We tested version 0.1.0 at commit `1a04d85254455012b9f73e2bced43218f9f755f5` against a fresh single agent on two tasks. Each pair received identical source and product prompts, the same model/effort (`gpt-6-astra`, `xhigh`), tools and a 45-minute limit. Workflow agents could delegate; controls could not use Orchflows or delegate. Independent acceptance suites were prepared before the builds. Candidates were frozen before external grading.

The [published comparison](https://github.com/DanMcInerney/orchflows/tree/main/benchmarks/software-factory/2026-09-16) includes **all four implementations**, their tests and documentation, exact task prompts, independent evaluators, saved scores, reviewer reports, handoffs, original patches and simulated release evidence. The applications and evidence live outside the installable library.

### Authenticated webhook inbox

Tenant isolation, SQLite persistence, idempotency, concurrency and pagination.

| Measure | Software factory | Single agent |
| --- | ---: | ---: |
| Independent acceptance checks | 28/28 | 28/28 |
| Build + handoff time | 25.6 min | 17.2 min |
| Agent contexts, including coordinator | 6 | 1 |
| Output tokens | 76,085 | 31,283 |
| Uncached input tokens | 362,300 | 102,156 |
| Cached input tokens | 5,376,640 | 772,992 |
| Delivered patch | Complete; applies | Complete; applies |
| Release outcome | Human security review required | Human security review required |
| Implementation | [Code and tests](https://github.com/DanMcInerney/orchflows/tree/main/benchmarks/software-factory/2026-09-16/runs/webhook-inbox/workflow/project) | [Code and tests](https://github.com/DanMcInerney/orchflows/tree/main/benchmarks/software-factory/2026-09-16/runs/webhook-inbox/single/project) |
| Run evidence | [Handoff and artifacts](https://github.com/DanMcInerney/orchflows/tree/main/benchmarks/software-factory/2026-09-16/runs/webhook-inbox/workflow/artifacts) | [Handoff and artifacts](https://github.com/DanMcInerney/orchflows/tree/main/benchmarks/software-factory/2026-09-16/runs/webhook-inbox/single/artifacts) |

### Fast log archive

Preserve the search API/CLI, freshness and concurrency; exceed a 5× warm-search target and handle a failing staged-release simulation.

| Measure | Software factory | Single agent |
| --- | ---: | ---: |
| Independent acceptance checks | 31/31 | 31/31 |
| Build + handoff time | 42.4 min | 16.4 min |
| Agent contexts, including coordinator | 10 | 1 |
| Output tokens | 118,011 | 27,110 |
| Uncached input tokens | 762,299 | 117,821 |
| Cached input tokens | 13,387,264 | 1,337,856 |
| Warm-search speedup over reference | 374.7× | 620.8× |
| Exploratory nested-JSON probe | Pass after review-driven repair | API and CLI crash |
| Original delivered patch | Fails on LF baseline | Tracked files only |
| Simulated release checks | 8/8; rollback and recovery verified | 8/8; rollback and recovery verified |
| Implementation | [Code and tests](https://github.com/DanMcInerney/orchflows/tree/main/benchmarks/software-factory/2026-09-16/runs/log-archive/workflow/project) | [Code and tests](https://github.com/DanMcInerney/orchflows/tree/main/benchmarks/software-factory/2026-09-16/runs/log-archive/single/project) |
| Run evidence | [Handoff, reviews and artifacts](https://github.com/DanMcInerney/orchflows/tree/main/benchmarks/software-factory/2026-09-16/runs/log-archive/workflow/artifacts) | [Handoff and artifacts](https://github.com/DanMcInerney/orchflows/tree/main/benchmarks/software-factory/2026-09-16/runs/log-archive/single/artifacts) |

Times include coordination and handoff. Output tokens include reasoning; cached input can be reused across many calls. Counts are recorded usage, not dollar costs. The [full report](https://github.com/DanMcInerney/orchflows/blob/main/benchmarks/software-factory/2026-09-16/REPORT.md) links the underlying scores and measurements.

The nested-JSON probe is **separate from the fixed acceptance score**. It was chosen after workflow review found the problem, before inspecting the control's final result, then applied identically to the frozen reference and both candidates. The reference and workflow passed; the control raised `RecursionError` in its API and CLI. This is evidence for that specific review benefit, not a general quality ranking.

Both log implementations exceeded the 5× warm-search target (374.7× workflow, 620.8× single agent in short paired query loops). Both stopped the local release simulation at a failing 50% rollout, rolled back and verified recovery. These were synthetic signals, not a live production deployment.

Handoff quality had a separate defect: the workflow log patch failed to apply to the clean LF baseline because its export changed line endings, although its Git candidate was valid. The single-agent log patch was explicitly tracked-only, so its new benchmark and test files required the full candidate and manifest. Version **0.1.1** adds reconstruction evidence to the guidance, correctness review and checkpoint contract. The original benchmark artifacts and scores remain unchanged.

A targeted trial of the revised guidance packaged the same log candidate without changing its source. The new saved patch reconstructed the exact candidate tree with both LF and CRLF checkouts, reversed to the baseline, and passed all 17 application tests in the candidate and reconstructed checkouts. The old patch's failure was reproduced on the LF baseline; it does apply to a CRLF checkout. This validates the exercised handoff, not a rerun of the full delivery comparison.

The workflow used 2.4× and 4.4× the output tokens, respectively. There was one run per approach per task, not equal compute or a statistical experiment. A Windows SQLite cleanup bug in the webhook evaluator was corrected without changing assertions and the same corrected evaluator graded both arms. These results do not establish visual polish, game appeal, virality, live deployment reliability or overall maintainability. Published evidence preserves the original scores and source; machine-specific paths in supporting documents are made portable, with changes recorded in the archive manifest. Private host transcripts, duplicate worktrees and generated bulk data are excluded.

## Install and use

From a complete Orchflows checkout with Python 3.11+:

```sh
python scripts/orchflows.py setup --example software-factory
```

Register the home and install core plus `software-factory` using core's `docs/hosts.md`, then start a new session. Setup preserves an existing user-owned library copy; it does not overwrite it with this example's updates. Copy the intended changes into that library before refreshing an existing install. All three entrypoints remain manual-only on Codex and Claude Code. Invoke `$software-factory:software-factory` in Codex or `/software-factory:software-factory` in Claude Code; substitute a leaf name to use it alone. A checked-out `SKILL.md` can be followed by path, but that does not register a slash command.

Example requests:

> Use software-factory:software-factory to add a CSV export to this application. Preserve its filtering behavior. Use P=2 passes and return a reviewed change with test evidence and a release plan.

> Use software-factory:software-factory to ship this approved fix to staging using the repository's rollout policy. You may use its documented rollback if the error-rate threshold is breached. Observe the full policy window and record the release identifier.

> Use software-factory:observe-production to compare the last hour after release v42 with its baseline. Deduplicate latency alerts and prepare fix briefs for supported regressions.

> Use software-factory:investigate-incident to investigate checkout errors between 14:00 and 14:20 UTC. Explain likely causes and rank possible mitigations.

Supply an outcome and workspace, plus any chosen bounds, output directory, release target, project policy, domain guidance or model/effort preferences. Unspecified model settings stay with the host. Require Orchflows core 0.10.0+, native child delegation and the target project's build/check tools; CI hosting, deployment, flags and telemetry are needed only for stages that depend on them. See [library context](references/library-context.md), the [run contract](references/run-contract.md), [trial request](trials/request.md) and [expected behavior](trials/expected-behavior.md).
