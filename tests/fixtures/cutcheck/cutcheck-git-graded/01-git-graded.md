---
id: 01-git-graded
run: cutcheck-git-graded
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
root_generation: root:01-git-graded:1:sha256:37043da8f77e65e81f89c65215b0649edfe8c4bd4e4b53014e4a3dda45a54b2a
cut_generation: cut:01-git-graded:1:sha256:8b63a07b7daf0d12934b3c6e62d9014be0cd5b451229751c289b268d9ba7dc1c
assignment_seal: sha256:05ab6c7726a8873552df8015c61131d52dfe82e3c938b83fcec8fa46ec0861d9
---
## Objective

Fixture ticket for oracles the graded revision's own history answers: a log
read, a two-argument diff, and an ancestry question. Each is graded on its
exit status in the scratch clone, none excused for its head.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"462ef52aab37655260bdc9f9f98be4ed2601af2d"},"name":"baseline","type":"identity"}

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
