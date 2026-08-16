# SPEC — the ticket set

Source of truth for the 2026-08 redesign; the end state, its phases,
and the invariants every phase keeps. Grounded in
[REVIEW-2026-08-15.md](REVIEW-2026-08-15.md) (threads T1–T10), the
state-sink evidence (10 of 36 skills ever execute a ticket; 81% of
criteria name no oracle; worklogs freehand; improvement 1,864 → 39 → 2)
and the PR history (the deliver loop got fast when checks moved to
scripts, #48; churn = "state or a dispatch invented for a signal that
had not yet occurred"). Delete this file when the last phase lands;
`DESIGN.md` then owns the rationale.

## 1. End state

**One artifact.** The ticket ([contracts/work-item.md](contracts/work-item.md))
is the only unit of work, plan, and record:

- a **spec** is a *root ticket* — `executor: orch-decompose`, a `pack`
  stamp, acceptance as its `## Completion test`;
- a **composition** is a *template* — a directory of ticket stubs with
  `{{placeholders}}`, instantiated into `tickets/<run>/`;
- a **worklog** is a view `tickets.py` renders from the ticket
  directory, never a second hand-written file;
- a **handoff** is a ticket's `## Handoff` section.

**Two engines.** `orch-frontier` drains a ticket directory (every ready
ticket in flight; new tickets are an event; a root ticket completes when
its terminal ticket completes). `orch-loop` issues fresh-context
iterations against a done-check within a bound.

**Two evaluators.** `orch-critique` (open search for defects; write
authority in the packet makes it the corrector — today's `orch-check`)
and `orch-verify` (closed criteria → verdicts; a score scale in the
packet makes it the judge — today's `orch-judge`; blindness is an
`inputs` property).

**Primitives** critique, verify, investigate, decompose, integrate.
**Instances** tdd, draft, edit, render, resolve-conflicts, synthesize.
**Judgment workflows** spec (writes the root ticket), build, repair,
fixture, triage, eval-design. **Utility** visualize.

**Contracts (T0)** work-item (absorbing spec, delegation, composition),
verdict, result, pack-signature. Tests pin shapes and bytes, never
sentences; the validator forbids cross-tier copies instead of syncing
them.

**Routing** `answer | ticket | fix`; everything else runs only when
named. The host block owns the table. Both hosts expose the same four
adapters (`orch-spec`, `orch-frontier`, `fix`, `orch-build`); every
other name resolves at `by-name/`.

**Compositions** are named templates: canonical at
`compositions/<name>/`, custom at `<repo>/.orchflows/compositions/<name>/`
(unprefixed), admitted by the same validator that checks tickets,
manual-call only.

**Enforcement is mechanical.** `tickets.py` refuses a ticket with an
off-enum status, no frontmatter, or a criterion without `oracle:` and
`oracle_class:`; the validator rejects a template that is cyclic, has a
stub without an executor or completion test, or has no terminal stub.

## 2. Vocabulary added (owned by docs/vocabulary.md at P3)

- **root ticket** — a ticket whose executor is `orch-decompose`; its
  subtree is `<id>.NN` unit tickets plus `<id>.gate.*`; it completes
  when `<id>.gate.verify` completes; a successor depends on the root
  id alone.
- **template** — a directory of ticket stubs; a stub is a ticket
  missing only `run`, `status`, `claimed_*` and any `{{placeholder}}`.
- **terminal ticket** — the stub no other stub depends on; its
  completion test is the template's done check.
- **gate stubs** — `<root>.gate.critique.<lens>` (read-only, one per
  stamped lens, parallel), `<root>.gate.repair` (write authority over
  the run scope, depends on every critique), `<root>.gate.verify`
  (depends on repair; carries the root's acceptance).

## 3. Mechanics — how the combinators map

| composition.md today | ticket set |
|---|---|
| `seq A → B` (A's result identity is B's evidence) | `B.depends_on: [A]`; `B.## Fixed inputs` cites `A.## Result` by identity |
| `par A ‖ B`, named join | no edge, disjoint `write_scope`; the join is `C.depends_on: [A, B]` |
| `loop body / done-check / bound` | a ticket with `executor: orch-loop`; body, done-check, bound in its sections |
| `invariants` | `excluded_actions` on every stub |
| `done_check` | the terminal ticket's `## Completion test` |
| step with `pack` | a root ticket |
| `entry` | whether the host block names the template |
| `when` | dropped (no consumer) |

Frontier additions: (a) event "a new ticket file appeared" (`tickets.py
ready` already rescans); (b) root completion rule; (c) `tickets.py
instantiate <template> --run <run> --set k=v`; (d) P2: `executor:
script:<path>` names a tested script (the ladder's floor as a node).

## 4. Phases

**P0 — this spec.** Committed on `claude/ticket-set-redesign`.

**P1 — the dogfood kernel** (built first, then used to build the rest):
`tickets.py new` (issue a ticket, refusing off-contract shapes) and
`tickets.py instantiate`; the template directory format and its
validator check; `compositions/fix/` as the first template (four stubs)
beside `compositions/fix.md` until P4; `orch-frontier` gains the
new-ticket event, the root completion rule, and template instantiation;
vocabulary entries. Oracle: `fix` instantiated from the template runs
under `orch-frontier` on a fixture and terminates with the same
verification the composition promised; validator + suite green.

**P2 — tests first, then the T0 supersession.** Delete the ~25
sentence assertions and `validate_sync`; add the cross-tier
near-duplicate ERROR (T2). Then one supersession PR: `work-item.md`
absorbs `spec.md`, `delegation.md`, `composition.md` (root ticket,
stub, template; the packet parts already map); `result.md` = three
fields; `run.json` → `tickets.py` docstring; the lease → artifact
motion; `executor: script:`; re-pin. `orch-decompose` emits the gate
stubs and repairs via `cutcheck.py` before returning; `orch-spec`
writes the root ticket; `orch-frontier` absorbs `orch-task`.

**P3 — law, skills, packs, docs, host block** (independent PRs): rules
to ~220 lines (T4); evaluators to two and kernel to five (T6); packs
state deviations only, lens → craft (T7); docs (T8); the loop text
(T9); §10 reword (T10); one routing rule, four adapters on both hosts,
prompts as redirects (T5).

**P4 — compositions → templates.** evolve, benchmaker, renovate,
drift-canary, self-improve (new, named), skill-tournament = evolve with
`writer: orch-build`; delete `orch-compose`, `orch-panel`,
`orch-diagnose`, `orch-task`, `improvement-delivery`,
`orch-search-plan` (→ `scripts/`); installer stubs for templates.

**P5 — proof.** Fixtures: `fix` replay; one code delivery through the
root-ticket path; evolve open on a fixture. The routing benchmark (47
vs 4 adapters). Ablations from REVIEW §5. Sink checks: worklog view
renders for every run; ticket refusals fire on the 27 off-enum / 32
frontmatter-less legacy tickets.

## 5. Invariants kept in every phase

The executor's claim is never green; independence enters every unit
before acceptance; one join per return, authority attenuates; blind
judges; the two-channel state law and the sink; the friction law;
hash-pinned T0 with a supersession PR for any shape change; every
canonical change through the required checks in `AGENTS.md`.

## 6. Deletions with recorded loss

| deleted | the capability that leaves with it | why it is safe |
|---|---|---|
| `orch-compose`, `contracts/composition.md` grammar | a step-level `when`; `scheduled` as a field | no consumer; no scheduler exists |
| `orch-task` | a named single-ticket entry | frontier over a one-ticket directory |
| `orch-panel` | packet enumeration prose | judge stubs + reduce stub |
| `orch-check` | a separate checker name | critique with write authority (already how deliver uses it) |
| `orch-judge` | a separate scorer name | verify with a score scale; blindness via `inputs` |
| `orch-diagnose`, `improvement-delivery` | — | the `fix` template; the deliver path |
| `orch-delegate`, `orch-worklog`, `orch-workspace`, `orch-mechanize`, `orch-elicit` as skills | a by-name stub each | one clause where each already points; scripts |
| `spec.md`, `worklog.md`, `delegation.md` | three file names | root ticket; rendered view; merged shape |
| hand-written worklogs | narrative | rendered from tickets — reconstructable by observation |

## 7. Open decisions (defaults; proceed on them)

1. Ticket sets vs `orch-compose` with fixed `seq` — **ticket sets**, gated on the P1 fix fixture.
2. Four adapters on Claude — **yes**, gated on the P5 routing benchmark.
3. Merge `delegation.md` into `work-item.md` — **yes**, in the P2 supersession.
4. Delete `orch-delegate` as a skill — **yes**, unless the validator needs a named spawn node.
5. §10 reword vs mandatory `independence` on ad-hoc tickets — **reword**.
6. Keep the five domain instances — **yes**; design/content packs get ablation tickets, not deletion.
7. Keep `orch-loop` as an engine — **yes**; iterations-as-tickets need an issuer.
