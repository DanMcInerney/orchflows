---
id: 01-git-graded
run: cutcheck-git-graded
status: issued
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
---
## Objective

Fixture ticket for oracles the graded revision's own history answers: a log
read, a two-argument diff, and an ancestry question. Each is graded on its
exit status in the scratch clone, none excused for its head.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A log read is graded on its exit status.** `git log -1 --format=%H`
   names the graded revision. oracle_class: deterministic. provenance:
   authored-here.
2. **A two-argument diff exits 0 almost always.** `git diff ac8791a --
   install.py` is empty. oracle_class: deterministic. provenance:
   authored-here.
3. **An ancestry question only history can answer discriminates.**
   `git merge-base --is-ancestor ac8791a HEAD` holds once the work has landed
   and not at the revision the set was cut from. oracle_class: deterministic.
   provenance: authored-here.

## Result

[]
