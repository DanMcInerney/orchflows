# Composable library implementation series

Status: proposed implementation contracts. Baseline: a7f19004d595fa09ab1aeda685f70002af2388fd (main), observed 2026-09-05. The series is written for an agent starting cold: the agent reads this index and the current stage, then uses the accepted predecessor as its only substrate. It is not a claim that any proposed behavior is already shipped.

The fixed design target is the request, “build me a workflow that builds games.” The library should let an agent recover the theory from compact documents, compose reusable workflow skills, select a host profile independently of whether a call makes or judges, and leave durable, truthful results. Human summaries and diagrams are generated views. The source of truth remains the agent-facing contracts, standards, workflow bodies, tickets, and evidence.

## Sequence

| stage | result | depends on | primary owners |
| --- | --- | --- | --- |
| 1. [Bootstrap and self-hosting](01-bootstrap-and-self-hosting.md) | A reusable implement-spec workflow and a verified accepted-source handoff using the existing do/judge path | current main only | example-workflows/implement-spec, installer handoff and host adapter seams only where a probe proves a defect |
| 2. [Composition and resources](02-workflow-composition-and-resources.md) | Workflows can compose smaller workflows to real bounded depth and may own scripts, private resources, and local narrowing standards | accepted stage 1 | ring resolver, custom authoring, workflow validator, environment checks |
| 3. [Roles and execution](03-roles-execution-and-workspaces.md) | Roles are model profiles independent of do/judge; grouped work preserves context, workspace ownership, and durable results | accepted stage 2 | tickets_mint, dispatch adapters, host records, workspace/result contracts |
| 4. [Standards and review](04-standards-composition-and-review.md) | Outline, slice, make, and review guidance composes through compact standards; mixed-artifact review can judge relationships | accepted stage 3 | contracts/standard.md, standards_support, judge artifact binding, evidence lenses |
| 5. [Authoring, routing, and improvement](05-authoring-routing-and-improvement.md) | Economical autorouting, self-improve, evolve, and a cross-host proof close the loop for executable and non-runnable artifacts | accepted stage 4 | host block, authoring docs, improvement/evolve workflows and their existing scripts |

Stage 1 is the only bootstrap. It uses the installed library's current legal commands and contains no later schema migration. Every later stage must be implemented from the accepted source identity installed by the previous stage. A stage may discover successor scope, but it records that scope and does not widen its own commit.

## Shared implementation contract

Every stage document carries the same reviewable fields: dependencies; one observable Goal; current-code evidence; bounded changes with causal owners; exclusions; a practical dogfood exercise; acceptance evidence; and migration and rollback or recovery. A stage's Goal is the result a fresh implementer must make observable. Its Details are guidance, never a second completion criterion. Proposed flags, paths, and frontmatter are marked **proposed** until a code change and a failing-then-passing check establish them.

The canonical authoring owner is [docs/custom-workflow-authoring.md](../../docs/custom-workflow-authoring.md). It is carried in each implementation ticket's ## Context or, where the current minting API cannot carry that pointer, in ## Details with a friction record naming the limitation. The implementation ticket uses the orch-code standard and its git Lens. The implementation must preserve the repository's required checks from [AGENTS.md](../../AGENTS.md); the root runs the full row once at phase close, while children run only affected checks.

The common handoff is deliberately explicit:

1. On the stage branch, run uv run --no-project python tools/run_required.py --no-cache, the stage's focused checks, uv run --no-project python tools/regen.py --check when derived files are touched, and git diff --check.
2. Record the observed exit code and the output identity. Confirm git status --short is empty and record git rev-parse HEAD. The installer's --accepted-source checks only identity equality; it does not prove a completed gate, a clean tree, or absence of live frames or live attempts, so the operator records those facts separately.
3. Close all stage frames and check the shared user state sink for both open frames and live dispatch attempts across every project, not only the project named by orchflows resume. Do not update the installed substrate underneath a live child. Preserve the previous receipt and source commit as the recovery substrate.
4. Install only the recorded commit with uv run --no-project python install.py --accepted-source <commit>, then run uv run --no-project python scripts/orchflows.py sync and uv run --no-project python install.py doctor --quick. The installed receipt and doctor output are the handoff evidence.
5. Start the next stage in a fresh run. If any check or handoff fails, leave the accepted predecessor installed and resume or recover from its tickets; never silently mix source and installed generations.

No stage requires an external service, a daemon, a new package manager, a compulsory DSL, or one agent per question. Existing rings, bundles, pins, tickets, frames, workspaces, traces, friction logging, evolve, and self-improve are reused. Package updates are source-identity cutovers, not live-run mutations.

Each stage also runs a comparable small fixture and records end-to-end time, dispatch/spawn count, workspace/setup count, token or cost readings when the host exposes them, repair count, and user-intervention count beside the quality verdict and evidence identities. An unavailable metric is reported as unavailable. A regression is explained against the predecessor; no arbitrary threshold is invented and no duplicate full suite is added to a child.

## Coverage and non-goals

The stages preserve these decisions:

- Agent-first documents are normative. Briefs stay concise free-form prose with machine metadata only at a real consumer. There is no new product/mode/result-schema/acceptance-document taxonomy, and no duplicate Goal prose.
- A workflow is a reusable skill whose body may call smaller workflows, orch-do, orch-judge, or deterministic scripts. Call depth is bounded by existing real limits. Local helpers, private references, and standards remain private unless explicitly exported. role is a profile binding, not a new persona or operation type.
- A single child may execute a coherent group of steps when its Goal and workspace remain one owned artifact; separate children remain available for parallelism or independent eyes. A local self-review never counts as independent acceptance. The final review is a fresh ordinary judge where the stage requires it.
- Standards answer outline, slice, make, review, and vocabulary questions. Compact cores and applicable narrowings are read whole; detailed material is loaded on demand. Standards do not choose workspace mechanics. Compatible standards can compose; conflicting workspace or authority requirements refuse loudly.
- Autorouting chooses the smallest useful shape and de-escalates after uncertainty is resolved. Named or recurring sequences earn a workflow. Trivial tasks do not acquire mandatory outline/decompose/review, and an expensive evolve campaign never starts silently.
- Self-improve routes friction, worklogs, feedback, and events to the one causal owner, including the environment, a custom workflow, or library architecture. Evolve compares frozen candidates for any artifact, including prose and standards, with blind or held-out evidence where useful; winner selection remains separate from activation and no score is invented merely to fill a field.

The image/world example is a dogfood reference only: intent → scene plan → global assets/terrain → render/judge/refine → region planning → independent region generation/placement/refinement → integrate → global/local QA. A browser-game QA component may own browser checks and narrowings; engine research may feed build-game. The series makes no claim about an external Worldclaw implementation.
