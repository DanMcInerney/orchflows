# Personal decision brief

A small personal library showing how to combine shared processes with your own guidance. The [workflow](skills/decision-brief/SKILL.md) compares proposals, drafts or accepts a supplied recommendation, then independently reviews and revises it at most once. The [guidance](guidance/decision-brief.md) owns reporting style and evidence quality.

Requires Orchflows core 0.8.0+, shared 0.1.0+ and native child delegation. Resolve both dependencies before starting; copying this fixture does not install or register them. For an isolated trial, copy this complete folder to the supplied home's `libraries/personal/`. Do not replace an existing personal library with it. All skills are manual-only by default.

Supply the question, proposals, decision criteria, optional draft and output location. Default to three total child starts: one comparison reviewer, one draft reviewer and a possible fresh fixer. Direct drafting uses the caller when its settings permit. Inherited bounds do not reset; any delegated drafting must also fit the same ceiling. The output includes the comparison, original review, delivered memo, verification and remaining gaps. No purchase, message, approval or extra review is part of this process.
