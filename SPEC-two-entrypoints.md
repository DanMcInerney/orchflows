# Simplification spec: two entry points, one grammar

Status: proposal — a T0 supersession; lands as one PR per
`AGENTS.md` required checks. Date: 2026-08-06.

## 1. Objective

One observable end state: a plain request routes through exactly two
entry shapes — **ad-hoc** or **deliver** — with every other workflow
reachable only by name; a request spanning multiple deliverable kinds
produces a chain of single-pack delivers without a hard-coded pairing;
any skill or composition can be glued by `seq`, `par`, or `loop`
because every dispatchable unit returns one result envelope.

Acceptance:

1. `templates/host-block.md` routing presents four branches and no
   pattern enumeration. Oracle: read the file.
2. "Research X and Y, then integrate Y into X" yields two chained
   specs (research pack, then code pack) joined by result identity →
   evidence. Oracle: frozen routing fixture replayed through
   `orch-task`.
3. BenchMaker expressed as a composition file passes `orch-build`
   admission and its fixture replays green. Oracle: admission evidence
   plus replay. This is the algebra's acceptance test: if the
   composition contract cannot express BenchMaker, the contract is
   wrong, not BenchMaker.
4. Every dispatchable unit's `Return:` leads with the result envelope.
   Oracle: new `tools/validate.py` check.
5. The four required checks in `AGENTS.md` pass.

## 2. The model

| Language part | orchflows owner |
| --- | --- |
| Values | result envelope: status, result identity, verification |
| Statements | a run: ad-hoc ticket(s), or `orch-deliver(spec, pack)` |
| Grammar | `seq` (law + composition edges), `par` (`orch-delegate`/`orch-integrate`, `orch-frontier`), `loop` (`orch-loop`) |
| Stdlib | `compositions/` — normative, admitted, invocable by name |
| Dispatch | the host-block: four branches |

Three user tiers, each one concept apart: type plainly (routing does
the rest); call a workflow by name; author a composition file.

## 3. Contract changes (the supersession)

### 3.1 `contracts/result.md` — new

The envelope every dispatchable unit's `Return:` leads with:

- `status` — `complete | blocked | stalled | limited | failed`
  (the worklog terminal vocabulary; one owner).
- `result` — the deliverable's identity; what a successor spec's
  `evidence` cites.
- `verification` — verdict entries per `contracts/verdict.md` covering
  the result identity.

Units bound: `orch-deliver`, `orch-task`, `orch-investigate`,
`orch-loop`, `orch-frontier`, and every composition. Evaluators
(`orch-verify`, `orch-judge`, `orch-critique`, `orch-check`) and
utilities are exempt — they are joins and lenses, not chain nodes.
This closes the `rules/composition.md` rule 10 asymmetry: amend rule
10 so `Return:` items ride T0 carriers exactly as `Require:` items do,
the envelope first.

### 3.2 `contracts/composition.md` — new

A composition is a named workflow over skills and other compositions:

- `name`, `description` — the routing/name surface.
- `entry` — `routed | named | scheduled`.
- `steps` — each: id; unit (skill or composition); pack, when the unit
  takes a stamped spec; frozen bindings (done-check, context packet,
  lens, profile).
- `edges` — `seq`: predecessor's result identity becomes successor
  evidence (today's topology §7, promoted from prose to field);
  `par`: disjoint write scopes plus a named join (check, reduction, or
  adjudication); `loop`: body plus done-check plus bound, dispatched
  through `orch-loop`.
- `invariants` — the `Never:` block binding every step. This is where
  a demoted pattern's law survives: evolve's frozen
  benchmark/blindness/margin, fix's proven-cause-before-repair.
- `done_check` — the end-to-end oracle over the final envelope. A
  chain of individually gated runs has no gate over the whole; this
  field is that gate.
- `Require:` / `Return:` — envelope law as any skill.

Instances at runtime: a multi-kind request materializes an unnamed
composition instance at `.orch/runs/<run>/composition.md` — chains and
saved workflows share one representation, and cross-session resumption
reads it. Nesting: one level, matching the workflow analogy in every
host.

### 3.3 `contracts/spec.md` — amended

`routing` stamps **pack only**. The pattern field is deleted; the six
shapes of done become grammar and stdlib. Spec filename becomes
`spec.md` (no `<pattern>` suffix).

### 3.4 `compositions/` — reclassified

T3 stops being non-normative free churn. Compositions are admitted
through `orch-build` (admission now checks the composition contract:
envelope, invariants present, done_check named), invocable, and listed
as the named tier. `ARCHITECTURE.md` T3 line and `docs/vocabulary.md`
`composition` entry rewritten accordingly.

## 4. Routing rewrite

Replacement for the host-block routing (and topology §2, same
content, one owner — host-block links, topology owns):

> Route smallest-first:
> 1. **Answer** — evidence already in context decides it.
> 2. **Ad-hoc** — bounded work needing no frozen spec. Write ad-hoc
>    ticket(s) with named acceptance and oracles; one item →
>    `orch-task`; a read-only question → `orch-investigate`;
>    independent items → parallel `orch-delegate`, every return
>    crossing `orch-integrate`; dependent items → `orch-frontier`.
>    Ticket files are the durable state.
> 3. **Deliver** — work needing a frozen spec: lanes at scale, an
>    assembly, or cross-session resumption. `orch-spec` counts the
>    deliverable kinds the end state spans and emits one spec per
>    kind — one run, or a composition instance chaining single-pack
>    delivers, cut where the deliverable's kind changes, joined by
>    result identity → evidence. `orch-deliver` runs each.
> 4. **Fix** — a failure with unknown cause → the `fix` composition:
>    prove the cause before repairing.
>
> Everything else — `evolve`, `benchmaker`, scheduled snapshots, and
> saved compositions — runs only when named. The named tier grows;
> this table never does.

The litmus law, added to `rules/topology.md`: a request earns a
*name* only when it carries an invariant routing cannot be trusted to
preserve or a recurring multi-run shape; a named workflow earns a
*routed slot* only when its natural-language trigger is unmistakable.
Everything else is a spec.

`orch-spec` amendments: add the count question; on ≥2 kinds, return
spec 1 plus the composition instance (successor pack, evidence =
run 1's result identity — spec 2 is written when that identity
exists); delete the "Never: stamp two packs" parenthetical in favor of
the slot; absorb the decision pattern as its existing stop-early
behavior (`orch-elicit` + `orch-panel`, ship the approved spec).

## 5. Skill dispositions — all 37

The review found the kernel, engines, instances, and packs already at
lego grain (19–46 lines, single ownership, clean call edges). The
simplification lands almost entirely in `skills/workflows/` and the
contracts above.

**Keep unchanged (24).** Kernel: `orch-check`, `orch-critique`,
`orch-decompose`, `orch-delegate`, `orch-elicit`, `orch-integrate`,
`orch-judge`, `orch-mechanize`, `orch-synthesize`, `orch-verify`,
`orch-worklog`, `orch-workspace`. Engines: `orch-frontier`,
`orch-panel`, `orch-task` (envelope already carried via the ticket).
Utilities: `orch-off`, `orch-visualize`. Instances: `orch-draft`,
`orch-edit`, `orch-render`, `orch-resolve-conflicts`, `orch-tdd`.
Plus `orch-diagnose` and `orch-eval-design` — leaves with real
procedure, referenced by compositions.

**Amend (7).**
- `orch-spec` — §4 changes; stamp = pack.
- `orch-deliver` — unchanged shape (it is the workhorse statement and
  stays a skill even though its body is a chain — center of gravity
  earns the exception); Return already leads the envelope; drop
  pattern language.
- `orch-investigate` — add the envelope to `Return:` (today it
  returns no status, identity, or verification — the one unit that
  cannot currently be chained).
- `orch-loop` — add the envelope; body contract already admits "a
  caller-owned composite," now explicitly including compositions.
- `orch-frontier` — add the envelope.
- `orch-build` — admission extends to composition files.
- `orch-review-fix`, `orch-repair` — pattern references only; no
  contract change. (Counted with amends for the sweep.)

**Demote to compositions (3).**
- `orch-fix` → `compositions/fix.md`, `entry: routed`. Confirmed a
  pure chain — `seq(diagnose → repair → verify)` — whose single
  invariant (the regression guard) moves to the composition's
  `invariants`. The routed table pointing at a composition is
  deliberate: it proves compositions are first-class.
- `orch-evolve` → `compositions/evolve.md`, `entry: named`. Its 38
  lines are invariants around `loop` + `panel` + `judge`; they move
  intact into `invariants` and step bindings. Manual-only is `entry:
  named`.
- `orch-benchmaker` → `compositions/benchmaker.md`, `entry: named`.
  The spec→deliver→eval-design→deliver chain becomes steps; sealing
  and manifest invariants ride `invariants`. This file is acceptance
  criterion 3.

**Dissolve without deleting a file (2 patterns).** `decision` →
`orch-spec` stop-early. `snapshot` → `scheduled` entry on a
composition wrapping `orch-triage` or a bounded deliver; `orch-triage`
itself stays a leaf skill.

Net: 37 skills → 34; six patterns → zero; routing branches 7 → 4;
spec stamp 2 fields → 1; two new T0 contracts.

**Deferred, noted for later.** The `orch-check`/`orch-critique` pair
and `orch-verify`/`orch-judge` pair are a 2×2 (verdicts vs findings ×
open vs blind) — document the grid in `docs/vocabulary.md` rather
than merging; the blindness and reuse asymmetries are load-bearing.
`orch-tdd`/`orch-render` share ~6 lines of slice→verify→commit
structure a slicing rule could own — consolidation, not now.
`orch-worklog`'s mechanical half is a `scripts/worklog.py` candidate
under `orch-mechanize`'s own law.

## 6. Deletions

- `pattern` entry in `docs/vocabulary.md`; six-way enumeration in
  topology §2 and the host-block.
- `spec-<pattern>.md` naming.
- "non-normative example" markers across `compositions/`.
- `skills/workflows/orch-fix/`, `orch-evolve/`, `orch-benchmaker/`
  directories (content moves, invariants verbatim).
- Topology §7's prose-only status — its rule becomes the `seq` edge
  definition in `contracts/composition.md`; §7 links it.

## 7. Migration — one supersession PR

1. Freeze routing fixtures first: today's behavior on ~10 request
   cases (single-domain, multi-domain, ambiguous-cut, "sounds
   multi-domain but isn't") via `orch-fixture`, so criterion 2 has a
   before/after.
2. Land `contracts/result.md` and `contracts/composition.md`; update
   hash pins in `tests/`.
3. Amend `contracts/spec.md`, `rules/composition.md` rule 10,
   `rules/topology.md` §2/§7 + litmus law.
4. Rewrite `templates/host-block.md`; re-render via `install.py`.
5. Amend the seven skills in §5; add envelopes.
6. Author the three demoted compositions; admit through `orch-build`;
   delete the three skill directories.
7. Update `ARCHITECTURE.md`, `docs/vocabulary.md`
   (composition, stamp/routing, delete pattern; add envelope, litmus
   law pointer).
8. Extend `tools/validate.py`: envelope check, composition-contract
   check.
9. Replay fixtures; run the four required checks.

## 8. Risks

- **Invariant dilution** — the demotions move law from skill bodies
  into composition files. Mitigation: the composition contract makes
  `invariants` required; admission rejects a composition whose steps
  a `Never:` does not bind; evolve/fix invariants move verbatim.
- **Routing regression** — the four-branch table must still catch
  what seven branches caught. Mitigation: step 1 fixtures; the
  ambiguous cases are the frozen adversarial set.
- **Chain without a whole-gate** — mitigated by `done_check` in the
  composition contract; a composition missing it fails admission.
- **Library drift** — resolved: `orch-goal` is absent from both this
  repository and the installed `~/.orchflows/lib` (a stale host
  listing); no action.
- **Host adapters** — demoted skills lose their `~/.claude/skills/`
  stubs; `install.py` must mint stubs for named compositions or the
  named tier is unreachable from the host. Add to step 4.
