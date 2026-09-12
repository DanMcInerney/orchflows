# Independent review of Orchflows authoring design

Review this proposal independently for elegance, simplicity, clarity, and fast, high-quality delivery by agents that begin without our conversation history. Review only; do not edit files. Challenge the proposed structure and wording where a simpler or clearer alternative exists.

## Workspace and evidence

The proposing agent is working in:

```text
C:\Users\danhm\.codex\worktrees\2ef1\orchflows-light
```

That worktree is detached at `6f1249473c2f2c9e0f8cf1c8d84a8c315859a7b4`. Its checked-out files still use `standards/`. The newer guidance implementation was inspected through Git at `915f02c4614af40c61abedf6c69e43c836c4f8cd` on `codex/simplify-ownership`. Use that pinned revision for the existing `guidance/`, selection rules and builder when assessing the proposal; for example:

```text
git show 915f02c4614af40c61abedf6c69e43c836c4f8cd:docs/architecture.md
git show 915f02c4614af40c61abedf6c69e43c836c4f8cd:skills/orch-build-workflow/SKILL.md
```

Local uncommitted work includes `docs/principles.md`, its routing changes in `AGENTS.md` and `README.md`, and `reports/guidance-review-2026-09-12.md`. Read the report for the previous research into gstack, Matt Pocock's skills, Superpowers, expert instruction files, and exact Astra/Fable 5.1 prompting guidance. Its recommendations are hypotheses, not measured Orchflows improvements. Our subsequent clarification below changes its emphasis. None of the proposed files or replacement wording below has been implemented.

## Intent

Orchflows uses native agents and two primitives: orch-work makes; orch-review independently judges without fixing. Small workflows compose into larger workflows. The host supplies execution; we want little extra machinery or prescription.

Guidance should express durable taste and necessary local distinctions. A capable model can know accepted practice without knowing our preferences. Examples: prefer code files below roughly 500 lines, split at coherent responsibilities, and design tests to run independently and in parallel. Omit generic reminders such as avoiding security bugs. A preference need not beat every alternative in a benchmark; checks establish whether its wording communicates the intended choice.

Most corrections for current model weaknesses should be removable extensions or selected library guidance. Base guidance may shrink as models improve, but lasting preferences need not disappear. Do not assume every model upgrade improves every behavior.

## Proposed ownership

```text
AGENTS.md
  Short conditional reference map inherited by agents and subagents.

docs/architecture.md
  Canonical vocabulary, contracts, file placement, guidance selection,
  and short reasons for the architectural boundaries.

guidance/orchflows.md
  One independent domain for authoring workflows and guidance.
  Make and Review criteria; no delegation or trial-running procedure.

guidance/code.md and other base domains
  Durable preferences for work in each domain.

guidance/code.api.md and other extensions
  Only additional or different criteria for narrower contexts.

skills/orch-build-workflow/SKILL.md
  Thin, discoverable entrypoint for authoring reusable artifacts.
```

Fold genuinely Orchflows-specific principles into the relevant architectural passages and retire the separate principles page. Do not also add DESIGN.md. Treat this consolidation as a proposal to assess, not an established requirement.

The authoring domain is independent of Code because it also applies to research guidance, writing guidance and workflows without code. An agent editing CLI implementation primarily needs Code and the relevant architecture. An agent authoring guidance uses Orchflows and, where useful, Writing. The parent domain being extended is source material for that authoring task; its coding or research procedures should not accidentally become the author's assignment.

```text
AUTHORING
Request -> authoring entrypoint -> architecture + authoring criteria
        -> candidate + relevant trial evidence -> final review

EXECUTION
Request -> workflow -> relevant working domains -> finished result
```

Normal execution does not load the authoring guide merely because a workflow is involved.

## Is the builder necessary?

The current recommendation is to retain a much thinner builder. The existing builder adds three things beyond the general dynamic workflow: library placement and manifests/dependencies; a portable trial from an unrelated workspace using an ordinary brief; and checking registration before claiming native availability. Its skill description also makes authoring discoverable to external users' agents, which cannot rely on this repository's AGENTS.md.

Its generic maker/reviewer/repair sequence overlaps with orch-dynamic-workflow. Reuse existing orchestration instead of owning another copy. Trial-driven revisions should be included in the candidate covered by final review. Keep delegation, trial execution and registration operations out of shared authoring guidance.

Broaden the builder's description to cover workflows, guidance and extensions. Guidance authoring needs an example of applying its intended preference; it should not automatically incur workflow packaging, registration or a whole portable workflow trial. Do not create three separate builders or rename the existing skill merely to make this proposal possible.

Please independently decide whether this remaining entrypoint earns its place. If removing it is simpler, explain exactly how external agents discover authoring guidance and where its unique operations go. Do not justify retention solely by asserting that process and criteria are different.

## What belongs in AGENTS.md?

Every agent and subagent receives this file. It should contain concise references triggered by the assigned work, not instructions that make every reader a coordinator. In particular, avoid telling every agent editing a workflow to invoke the builder: a child author would inherit that instruction too.

Candidate wording, with paths relative to AGENTS.md:

```text
Architecture and file placement: docs/architecture.md. When writing
or reviewing workflows or guidance, apply your assigned role's section
of guidance/orchflows.md. Home operations: docs/home.md. Host isolation
and registration: docs/hosts.md. Transcript inspection: docs/history.md.
```

The calling workflow supplies relevant resolved guidance to its children, as the primitives already require. Do not repeat that selection algorithm, every domain's preferences, model workarounds, or a mandatory authoring workflow in AGENTS.md. The root remains able to select relevant guidance before delegation. Existing roles and explicit assignments should stay intact.

Check whether these pointers are sufficient, whether any are unnecessary, and whether the same text works for a maker, a reviewer, a researcher and the orchestrator. Consider the full inherited instruction bundle, not only the file in isolation.

## Candidate domain wording

These are complete proposed drafts to challenge, not approved replacements. They intentionally prioritize taste, useful distinctions and assessable outcomes over general competence lessons. Preserve necessary qualifications without growing exception lists. Each role applies its own section, so necessary repetition across Make and Review is acceptable.

### guidance/orchflows.md

```markdown
# Orchflows

## Make

When authoring workflows or guidance, prefer small compositions of existing capabilities. Add only what the result needs at this level. Follow architecture for structural contracts and placement.

Persist preferences and necessary local meanings. Keep request details in the assignment, quality criteria in guidance, orchestration in workflows and deterministic mechanisms in scripts. Extensions add differences rather than restating parents. Keep temporary behavioral corrections separately removable.

Define a term only when its local meaning affects a decision or shared result. A reusable artifact should work from an ordinary brief and its declared context, without undocumented preparation or knowledge held only by its author.

## Review

Look for duplicated ownership, unnecessary coordination, generic competence reminders and instructions at the wrong scope. Check whether extensions add a useful difference and whether the artifact can be understood without the author's conversation. Assess claims about behavior against the supplied evidence; identify what remains untested.
```

### guidance/code.md

```markdown
# Code

## Make

Prefer code files below roughly 500 lines; split longer files at coherent responsibility boundaries. Prefer one clear owner per behavior and maintained dependencies when they simplify the implementation.

Design tests to run independently and in parallel, with isolated state and fixtures. Test observable behavior rather than implementation structure.

## Review

Look for coherent splits in oversized changed files, duplicated ownership, and tests coupled through shared state or execution order. Tie findings to a concrete consequence. Treat the file-size preference as a design judgment, not an automatic refactoring requirement.
```

### guidance/research.md

```markdown
# Research

## Make

Prefer a few primary sources that directly support the important claims. Link evidence beside the claim. Keep observations, interpretations and recommendations distinguishable. Preserve qualifications and counterevidence that could change the conclusion.

## Review

Trace central claims to their evidence. Flag conclusions stronger than their sources, recycled sources counted as independent, and omitted evidence that materially changes the answer.
```

### guidance/writing.md

```markdown
# Writing

## Make

Lead with the point. Prefer plain, direct prose and concrete nouns and verbs. Use lists and tables when they make relationships easier to understand. Remove repetition and decorative wording while preserving meaningful qualifications. Adapt these defaults to the reader and genre.

## Review

Flag wording that obscures meaning, buries the point or requires needless rereading. Recommend changes that improve understanding; distinguish those from equally valid stylistic choices.
```

### guidance/visual-design.md

```markdown
# Visual design

## Make

Give the composition a clear visual priority. Prefer consistent typography, spacing, color and reusable patterns. Use realistic content and inspect the rendered result at its intended size and in its intended medium.

## Review

Inspect the actual rendered artifact. Look for weak hierarchy, unreadable detail, clipping and inconsistent treatment of equivalent elements. Distinguish problems with comprehension or interaction from aesthetic alternatives.
```

### guidance/data-analysis.md

```markdown
# Data analysis

## Make

Make the unit of observation, population and denominator explicit. Prefer the simplest analysis that answers the question. Keep transformations reproducible. Show magnitudes and baselines alongside percentages, and use precision the data supports.

## Review

Cross-check the central result. Look for changes in units, denominators, join cardinality or population that alter its meaning. Check assumptions that could reverse the conclusion. Distinguish a reproducible calculation from a justified inference.
```

### guidance/code.api.md — existing specialization

```markdown
# API code

## Make

Prefer stable caller contracts and machine-readable errors. Make ordering, pagination limits and retry effects explicit. Distinguish absent, empty and invalid values when their behavior differs.

## Review

Check whether a caller can recover from errors and retry without guessing. Flag accidental contract changes and ambiguous behavior at the interface's limits.
```

## Extensions, vocabulary and model changes

Dots narrow a subject: code.api is API guidance. A model is a different dimension. Avoid duplicating common corrections across code.api.astra, code.cli.astra and similar combinations.

Initially, put useful corrections in an already selected user library. If separate model bundles become useful, existing selected libraries can contribute guidance/code.md or guidance/writing.md. This uses existing precedence; model guidance does not automatically override a more-specific domain. Do not add a required model directory, automatic model detector or new resolver.

Do not require a vocabulary section in every domain. Keep local definitions in their canonical owner, and exact field names, status values or metric meanings in shared artifact contracts. Everyone producing related outputs must receive the relevant shared meanings. Judge whether any terms in these drafts need clarification or can replace longer descriptions without becoming jargon.

## Requested review

Give your recommendation in plain English with a small text diagram. Address:

1. The smallest useful file structure and whether the builder still earns its place.
2. Exact AGENTS.md wording that routes effectively without directing inherited child agents to coordinate or restart the workflow.
3. A critique of every candidate domain: useful taste, redundant competence reminders, consequential omissions, excessive prescription and ambiguous wording. Suggest replacement wording where it materially improves the draft.
4. Whether architecture and the authoring guide duplicate responsibilities, and how to remove that duplication.
5. How this works for a fresh external user's agent as well as agents developing Orchflows itself.
6. Whether the model-correction scheme concentrates churn without creating extra structure.

Prefer removing or combining things before adding machinery. Keep research claims separate from judgment. Do not demand a benchmark to justify a declared preference, and do not claim these proposed drafts improve results without a comparative trial. Review the proposal on its merits rather than agreeing with its author.
