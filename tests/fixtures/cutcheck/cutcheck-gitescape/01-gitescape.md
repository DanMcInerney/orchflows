---
id: 01-gitescape
run: cutcheck-gitescape
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

Fixture ticket for untrusted ticket content under a head an extractor accepts.
One criterion below states its oracle as a git span whose own argument is the
program git then runs; the other states one whose own argument is the file git
then writes, under a subcommand the confined set holds. A ticket is input, so
no span of one chooses what runs, and none chooses what is written where.

## Fixed inputs

- Baseline: the revision cutcheck is invoked with.

## Completion test

1. **A git span never runs a program it names.** `git -c alias.pwn='!touch /tmp/cutcheck-gitescape-ran' pwn`
   is the span; git runs that alias whatever its output is attached to, which
   is how the test tells running from reporting. oracle_class: deterministic.
   provenance: authored-here.
2. **A git span never writes a file it names.** `git log --output=/tmp/cutcheck-gitescape-wrote`
   is the span; `log` is a confined subcommand and `--output` stands after it,
   so the subcommand alone decides nothing here. Git writes that file and exits
   0 whatever its own output is attached to, which is how the test tells
   running from reporting. oracle_class: deterministic. provenance:
   authored-here.

## Result

[]
