# Software factory

An Orchflows example library that turns a software request into checked code, independent reviews and, when requested and authorized, an observed release.

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
2. **Build.** One fresh `orch-work` child implements the change, updates relevant documentation and prepares the handoff and rollout plan.
3. **Check the exact result.** The builder runs required tests, builds, CI and applicable performance checks. A delivered patch must also apply to its recorded clean baseline and reconstruct the candidate, including new files and deletions. The returned candidate is frozen for review.
4. **Review independently.** Fresh `orch-review` children inspect that candidate in parallel. Correctness is mandatory; data, infrastructure, cloud and security are included when the affected surfaces call for them. They receive real project context and the same candidate identity.
5. **Repair within the bound.** Failed checks or blocking findings go to a fresh builder on the next pass. Every revised candidate gets new required checks and applicable reviews. Running out of passes returns unresolved work; it never promotes a failed candidate.
6. **Decide readiness.** Low risk can satisfy the review gate automatically only with explicit project opt-in. Other cases need human review of the concrete diff, check evidence, findings, risk and rollback plan. Missing required evidence still blocks readiness.
7. **Release when requested and authorized.** A separate `orch-work` child receives the validated artifact. It verifies the actual published/merged inputs, baseline health, rollback path and stopping criteria, then advances through the project's rollout stages. A breach stops rollout; an already-authorized rollback is applied and recovery checked. Missing telemetry or an unfinished window cannot count as healthy.

Build, validation and deployment are separate checkpoints with recorded evidence. The same builder can run implementation checks, but it cannot approve its own independent review or silently deploy. Approval for one candidate does not cover changed release inputs. The default endpoint is a validated change and release handoff; shipping requires the release stage's authority and capabilities.

The central handoff rule in the guidance is:

> A complete patch must apply to a clean copy of its recorded baseline and reconstruct the candidate, including new files and deletions.

This includes checking the actual saved patch bytes. A passing test suite in the builder's directory, or `git diff --check`, does not prove that someone else can apply the patch.

## Production feedback and bounds

| Workflow | What it returns | Fresh children |
| --- | --- | --- |
| [software-factory](skills/software-factory/SKILL.md) | Checked change, reviews, risk decision and optional observed rollout | Per pass: 1 builder and 1–5 reviewers; optional 1 release worker per run |
| [observe-production](skills/observe-production/SKILL.md) | Bounded telemetry comparison, deduplicated signals and proposed performance-fix briefs | 1 `orch-work` worker |
| [investigate-incident](skills/investigate-incident/SKILL.md) | Incident timeline, evidence, answers and proposed or specifically authorized mitigation | 1 `orch-work` worker |

Delivery defaults to `P=3` candidate passes, including the first attempt: at most `6P + 1` child calls, or 19 by default. It stops early when the requested endpoint is reached. An unavailable required capability or missing decision returns the checkpoint and gap.

Observation and incident investigation are explicit invocations. Observation is read-only and proposes follow-up work; it does not automatically start a fix. Recurring observation requires a caller-requested host schedule. Incident investigation can perform a specifically authorized operation, but a request to investigate alone authorizes no mitigation. The package adds no daemon, scheduler, service adapters or production access.

## What the output-quality comparison found

We tested version 0.1.0 at commit `1a04d85254455012b9f73e2bced43218f9f755f5` against a fresh single agent on two tasks. Each pair received identical source and product prompts, the same model/effort (`gpt-6-astra`, `xhigh`), tools and a 45-minute limit. Workflow agents could delegate; controls could not use Orchflows or delegate. Independent acceptance suites were prepared before the builds. Candidates were frozen before external grading.

| Task | Workflow | Single agent | Observed quality difference |
| --- | --- | --- | --- |
| Authenticated webhook inbox: tenant isolation, SQLite persistence, idempotency, concurrency and pagination | 28/28 external checks; 25.6 minutes | 28/28; 17.2 minutes | Both returned usable complete patches and stopped for human security review |
| Fast log search: preserve API/CLI behavior, freshness and concurrency; simulated staged release | 31/31; 42.4 minutes | 31/31; 16.4 minutes | Workflow review found and repaired a valid nested-JSON crash that remained in the single-agent result |

The nested-JSON probe is **separate from the fixed acceptance score**. It was chosen after workflow review found the problem, before inspecting the control's final result, then applied identically to the frozen reference and both candidates. The reference and workflow passed; the control raised `RecursionError` in its API and CLI. This is evidence for that specific review benefit, not a general quality ranking.

Both log implementations exceeded the 5× warm-search target (374.7× workflow, 620.8× single agent in short paired query loops). Both stopped the local release simulation at a failing 50% rollout, rolled back and verified recovery. These were synthetic signals, not a live production deployment.

Handoff quality had a separate defect: the workflow log patch failed to apply to the clean LF baseline because its export changed line endings, although its Git candidate was valid. The single-agent log patch was explicitly tracked-only, so its new benchmark and test files required the full candidate and manifest. Version **0.1.1** adds reconstruction evidence to the guidance, correctness review and checkpoint contract. The original benchmark artifacts and scores remain unchanged.

A targeted trial of the revised guidance packaged the same log candidate without changing its source. The new saved patch reconstructed the exact candidate tree with both LF and CRLF checkouts, reversed to the baseline, and passed all 17 application tests in the candidate and reconstructed checkouts. The old patch's failure was reproduced on the LF baseline; it does apply to a CRLF checkout. This validates the exercised handoff, not a rerun of the full delivery comparison.

The workflow used 2.4× and 4.4× the output tokens, respectively. There was one run per approach per task, not equal compute or a statistical experiment. A Windows SQLite cleanup bug in the webhook evaluator was corrected without changing assertions and the same corrected evaluator graded both arms. These results do not establish visual polish, game appeal, virality, live deployment reliability or overall maintainability. Raw run evidence is retained in the experiment workspace, outside this reusable library.

## Install and use

From an Orchflows checkout:

```sh
python scripts/orchflows.py setup --example software-factory
```

Then register or refresh the `software-factory` library using core's host installation instructions. Setup preserves an existing user-owned library copy; it does not overwrite it with this example's updates. Copy the intended changes into that library before refreshing an existing install. All three entrypoints remain manual-only on Codex and Claude Code. A checked-out `SKILL.md` can be followed by path, but that does not register a slash command.

Example requests:

> Use software-factory:software-factory to add a CSV export to this application. Preserve its filtering behavior. Use P=2 passes and return a reviewed change with test evidence and a release plan.

> Use software-factory:software-factory to ship this approved fix to staging using the repository's rollout policy. You may use its documented rollback if the error-rate threshold is breached. Observe the full policy window and record the release identifier.

> Use software-factory:observe-production to compare the last hour after release v42 with its baseline. Deduplicate latency alerts and prepare fix briefs for supported regressions.

> Use software-factory:investigate-incident to investigate checkout errors between 14:00 and 14:20 UTC. Explain likely causes and rank possible mitigations.

Supply an outcome and workspace, plus any chosen bounds, output directory, release target, project policy, domain guidance or model/effort preferences. Unspecified model settings stay with the host. Require Orchflows core 0.7.0+, native child delegation and the target project's build/check tools; CI hosting, deployment, flags and telemetry are needed only for stages that depend on them. See [library context](references/library-context.md), the [run contract](references/run-contract.md), [trial request](trials/request.md) and [expected behavior](trials/expected-behavior.md).
