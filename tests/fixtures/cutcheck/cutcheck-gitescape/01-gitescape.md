---
id: 01-gitescape
run: cutcheck-gitescape
status: pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
bound: 20 tool calls
write_scope:
  - install.py
excluded_actions:
  - editing scripts/tickets.py
admission: pending
mutations: []
ownership_regions: []
root_generation: root:01-gitescape:1:sha256:e790c1e55903b21da3f79651ec7b0ef288cab278dc44f4953cf8fb3a182a1716
cut_generation: cut:01-gitescape:1:sha256:a827c72ea689e64ce14ed90b4d1c6db419e6bc7771a07440e9179e775784c039
assignment_seal: sha256:44dcea608ec83fba1399143060b5e8d6ee3074a8e1f8d369e370d32f5ef4e7fb
---
## Objective

Fixture ticket for untrusted ticket content under a head an extractor accepts.
One criterion below states its oracle as a git span whose own argument is the
program git then runs; the other states one whose own argument is the file git
then writes, under a subcommand the confined set holds. A ticket is input, so
no span of one chooses what runs, and none chooses what is written where.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

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
