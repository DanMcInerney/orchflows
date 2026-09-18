# Dynamic orchestration, core 0.13

The user's decision on 2026-09-18 restores `orch-dynamic-workflow` as the default candidate for ordinary top-level tasks, while explicitly selected workflows and primitives take precedence. It plans and performs the current task. `orch-build-workflow` still authors reusable workflows.

## Change from 0.12

Core gains one skill and its native invocation metadata. No CLI execution engine, routing script, compatibility alias or automatic migration is added. Other skills retain manual invocation settings. The dynamic workflow can compose saved workflows or primitive assignments in the same coordinator; an unavailable named selection remains an error.

The coordinator establishes the result, checks, stages, dependencies, applicable guidance, review gates and bounds before dependent execution. Independent research or implementation assignments can run concurrently. The coordinator joins their results and settles shared decisions before starting dependent work. A plan is execution context, not a generated skill file.

The default is one independent review of the joined final result. Intermediate review gates belong where research or design decisions would be costly to correct after dependent work starts. Each gate introduced by dynamic orchestration uses the existing review-and-one-repair workflow. Existing component gates count only when candidate, criteria and scope match; their contracts are preserved. Missing required review/evidence and unresolved blocking findings prevent dependent work. Replanning cannot replenish caller limits.

For a research-to-code task, the coordinator can select parallel research → joined research review and permitted repair → parallel implementation → joined code review and permitted repair/checks. A clear small task can use direct production and one independent reviewer. These are choices made for the task, not mandatory stage counts for every request.

## Preserved decisions

`orch-work` and `orch-review` remain coordinator-facing delegation skills. The coordinator applies them and gives each child a concrete assignment, inputs, applicable guidance paths, bounds and permitted effects. Children read their domain guidance and perform the assignment without launching agents or restarting dynamic orchestration. They do not need to load the delegation skill.

Composition still has arbitrary procedure depth in one coordinator. Local guidance and settings stay scoped; explicit work calls still require fresh makers, and review still requires a fresh non-maker. Original verdicts remain distinct from delivered revisions. Task details stay in prompts, process in workflows, and methods/taste in guidance.

## Native selection limit

Invocation metadata makes the skill available for automatic selection; it cannot force a model to choose it. In the native trial, Claude selected it for research-to-code but skipped it twice for a trivial arithmetic file request. Explicit invocation requests its process directly. Enforcing every ordinary request would require a separate host hook or routing mechanism, beyond this small skill-library design. We retain the failed routing diagnostic and report this limit rather than claiming guaranteed activation.

The [test record](../tests/e2e/README.md) separates registration, actual selection, execution and independent review evidence. Native selection is tested on Claude; Codex metadata is checked in the package tests, without a claim of a new native Codex trial.
