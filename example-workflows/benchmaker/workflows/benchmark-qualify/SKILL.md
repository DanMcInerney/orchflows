---
name: benchmark-qualify
description: Independently qualify a fixed benchmark draft, its references and candidate-access boundary.
disable-model-invocation: true
---

Require: `draft` (full git artifact identity and component locators), `coverage`
and `rigor`, construction `standard`, `qualification_budget`, `access_policy`
(candidate permissions, protected scope and permitted attack operations), builder
context identities, and a predeclared reference-audit sample including flagged
cases. Missing inputs return UNVERIFIED with available evidence and gaps.

    tickets.py frame-open <run> --goal-file <qualification-goal> --workflow benchmark-qualify

Use three fresh contexts within the declared budget. Every goal carries the
fixed draft, relevant input semantics and [record layout](../../references/qualification.md).
All three calls stamp the construction standard beside package-private
benchmark-quality; its narrowing supplies orch-code. No public workflow
boundary intervenes.

**Controls**: a builder-disjoint qualifier checks instrument quality under the
pinned standards, independently of reference correctness. Record each criterion,
case coverage, observed controls and command exits.

    tickets.py judge <run> --parent <frame> --standard <standard>
      --standard benchmark-quality --artifacts git:<draft-sha>
      --goal-file <controls-goal> --isolation required --bound <controls-bound>

**Reference**: a context disjoint from builders and controls qualifier solves
from visible prompts and licensed inputs before comparing keys and graders.
Carry the predeclared sample and flagged cases; tiny admissions cover all cases.
Return the prompt-first work, comparisons and fatal-flaw classifications.

    tickets.py judge <run> --parent <frame> --standard <standard>
      --standard benchmark-quality --artifacts git:<draft-sha>
      --goal-file <reference-goal> --isolation required --bound <reference-bound>

**Attack**: a context distinct from builders, qualifier and reference auditor
probes only the permitted candidate access scope. Inspect access mechanisms and
record dated SUCCEEDED/FAILED/BLOCKED observations, protected-read evidence and
unrepaired holes. Isolation of a review worktree alone proves no read exclusion.

    tickets.py judge <run> --parent <frame> --standard <standard>
      --standard benchmark-quality --artifacts git:<draft-sha>
      --goal-file <attack-goal> --isolation required --bound <attack-bound>

Collect the three findings lines and review-ticket identities as the fixed
evidence set. Derive `validity`: INVALID for established instrument invalidity;
otherwise UNVERIFIED for any missing required evidence, required UNVERIFIED
criterion or unavailable independence; otherwise VALID. Preserve optional gaps
and separate protection findings. All verdicts bind `benchmark_revision` to
`draft`; repairs return to the caller's making work and need new qualification.

Never: mutate cases, keys, graders or target in judge contexts; count controls
as target attempts; infer reference correctness from controls; accept required
UNVERIFIED; or claim inaccessible evidence from prompt omission.

Return: `tickets.py frame-close <run> <frame> --done <qualification-check>`
over `benchmark_revision`, `validity`, criterion verdicts, controls/reference/attack
review identities and findings locators, independence evidence, spend and gaps
(`[]` when empty). Partial evidence survives blocked or exhausted reviews;
validity alone confers no calibration or campaign eligibility.
