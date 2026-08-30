# Minimal machinery spec — 2026-08-30

## Identity

The successor to the cohesion/refactor spec pair
(the state sink's `research/20260828T195033Z-cohesive-library/`; root per rules/visibility.md §6), written
after their units U0–U12 merged and after PR #138's three waves (taste pass,
lens-cell deletion + cell minimization, red-green retirement + cause
threading; branch `claude/pack-structure-taste-2ed140`, tip `5e31063a`).
Where this spec and the cohesion spec disagree, this spec wins; it was
written against the later tree. A fresh agent should execute from this file
without the transcript.

Evidence base, by identity:

- Sink mine 2026-08-30: 7,508 friction entries 2026-07/08; findings in
  the state sink's `research/20260830T-pack-taste-recommendations/recommendations.md`.
- Web evidence 2026-08-30 (same file): oracle-immutability supported,
  test-first ordering unsupported; file-size band unmeasured; single
  ownership is the agent-form of DRY.
- Lens-semantics research
  (the state sink's `research/lens-semantics-20260828/`): gate machinery
  never read the lens cell — the precedent this spec generalizes.
- The evidence-lane defect found 2026-08-30: `EXECUTE_CELLS` in
  `scripts/packs_support.py` omits `evidence`, while
  `skills/kernel/orch-execute/SKILL.md` Never-clause holds the executor to
  "the pack's evidence" — a cell it never receives. U1 removes the class.

## Design laws

Restated from the user's lens; every unit answers to these.

1. **Durability gradient.** Contracts are the frozen ABI (hash-pinned).
   Scripts change slowly, with mechanisms. Skill bodies are thin prompts,
   cheap to edit. Packs and the user prompt churn freely. A stronger model
   changes only the last layer.
2. **Four thinking jobs.** A fresh LLM context is dispatched only where a
   perfect model still cannot act alone: freeze (`orch-outline`), cut
   (`orch-decompose`), work (`orch-execute`), judge (`orch-check`). Repair
   is work with blockers in Context. Everything else is a script or the
   orchestrator's hands.
3. **One driver.** Compute-ready → dispatch → land → repeat is one loop.
   Scripts make its every decision; the thing invoking them (orchestrator
   today, a host daemon later) holds only spawning authority. A loop is a
   stub type the driver re-arms, not a second engine.
4. **Typed exactly when branched.** A field exists only where machinery
   branches on it. Prose for model consumption lives in one document per
   owner, never in parallel cells, copies, or lanes.
5. **Envelopes are rendered, never authored.** What a child receives is
   composed by script from ticket + pack + role + reply path. (The
   contract's name for the envelope is the dispatch packet,
   `contracts/dispatch.md`; no rename — grep continuity is law.)
6. **Every artifact is for agents.** `README.md`, and `DESIGN.md` where it
   narrates history, are the only human surfaces. Everything else is
   optimized for an amnesiac agent: one owner per fact, stable greppable
   anchors (headings, backticked names, fields), no narrative, no
   restatement beside a link. Human legibility is a side effect, never a
   design input.
7. **Judgment is never scripted.** Meaning, construction, adequacy — the
   cut's seam choices, a verdict, a synthesis — stay with dispatched
   agents. Scripting a judgment hides it rather than determinizing it.

## U1 — Fold the pack: one document plus typed cells

The lens-deletion logic run to completion. A pack becomes:

- `SKILL.md`: frontmatter + a typed table of exactly four rows —
  `adapter` (registry key), `stages` (ordered names), `assembly` (stage or
  `none`), `craft` (the document pointer). `pack_cells` T0 shape shrinks
  to those four required fields (supersession record citing the current
  `pack-signature.md` pin; `contracts/shapes.json` + `tools/render_shapes.py
  --write`; `tools/validate.py --pin`).
- `references/craft.md`: THE document. Mandatory sections, each a stable
  `##` anchor: `Vocabulary`, `Workspace`, `Spec fields`, `Outline`,
  `Slicing`, `Evidence`, `Lens`. Optional: `Shape`, `Stages`. Content
  migrates verbatim from today's cells and reference files; the
  `required_spec_fields` cell becomes `## Spec fields`; the `workspace`
  cell prose becomes `## Workspace`; `outline.md`, `slicing.md`,
  `evidence.md` fold in and are deleted.
- Every verb reads the whole document; the section heading does what the
  lane projection did. `packs.py cells` returns the four cells; the
  `--for <lane>` flag becomes an accepted no-op alias for one release,
  then retires. `EXECUTE_CELLS`/`CHECK_CELLS`/`OUTLINE_CELLS` in
  `scripts/packs_support.py` delete; consumers (`orch-outline`,
  `orch-execute`, `orch-check` bodies) say "the stamped pack's craft"
  and name the sections they act under.
- Validators: `validate_craft_budget` bound rises 60 → 130 non-empty lines
  (sum of today's parts; only-falls ratchet keeps its law).
  `validate_lens_anchor` generalizes to `validate_craft_sections`: every
  mandatory section heading present per pack. The cell-duplication linter
  compares same-named sections across packs instead of cells — same
  thresholds, same allowlist mechanism.
- Tests: `tests/test_packs.py` cell sets → four; workspace-binding test
  reads `## Workspace`; craft markers unchanged; fixture packs in
  `tests/test_cell_linter_cases/pack_cells.py` and
  `tests/test_validator*.py` gain the mandatory sections.
- Docs: `contracts/pack-signature.md` rewrites its three cell tables into
  the section table; `docs/pack-authoring.md` reorders to section order.

Acceptance: five packs in the folded form; `packs.py resolve` digests
stable-shaped; the evidence-lane defect class is unrepresentable (there is
no lane to omit a section from). Oracles: `tools/run_required.py
--no-cache` exit 0; grep proves no `references/outline.md`,
`references/slicing.md`, `references/evidence.md` remain under `packs/`;
`tests/test_packs.py::test_every_pack_resolves_a_distinct_outline_leaf`
retargets to distinct `## Outline` sections.

## U2 — Absorb loop into the driver

- T0 (`contracts/work-item.md` supersession + `contracts/shapes.json`):
  a loop stub is a ticket whose new optional `loop` object carries
  `body` (a verb binding, or a template directory to instantiate per
  iteration), `done` (a deterministic command, or the id of a check stub
  dispatched per iteration), and reuses the existing `bound`. No other
  new fields.
- Script `scripts/tickets_loop.py`: `arm` (instantiate body iteration N,
  render its envelope from frozen goal + worklog tail + last handoff),
  `evaluate` (run deterministic `done`, or mint the check ticket),
  `advance` (re-arm | close `complete` | close `limited` on bound |
  close `stalled` on two consecutive iterations with no artifact delta
  and no measured delta). All replayable, fail-closed.
- The driver treats a ready loop stub as: arm → run body to terminal →
  evaluate → advance. No LLM holds loop state; the worklog is the state.
- `rules/loops.md` shrinks to invariants: external done-check, fresh
  context per iteration, stall exits, and no-terminal work remains
  scheduled bounded runs (a host scheduler chains campaigns; nothing in
  the library pretends to run forever).
- `skills/engines/orch-loop/` retires: entry in
  `scripts/tickets_registry.py` `SUPERSEDED_EXECUTORS` mapping to the
  loop stub form; templates binding `executor: orch-loop` (grep
  `templates/`, `compositions/`) migrate to loop stubs.

Acceptance: the evolve composition's generation loop runs as a loop stub
whose body is the generation template, with selection and promotion in
scripts and only candidate-makers and judges as LLMs. Oracles: required
gate green; a fixture loop run (`tests/`) shows arm/evaluate/advance
replay after kill; `orch-loop` dispatch refused with the superseded
message.

## U3 — Demote frontier and integrate (gated)

Gated on one full run's friction under U1+U2 showing dispatch scripts
refuse improvisation (the sink's packet-less fork firings are the
counter-evidence; `tickets.py dispatch` already refuses without a
committed packet — the gate is confirming nothing else leaks).

- `orch-frontier` retires to: `tickets.py frontier` (exists) + the driver
  procedure, ≤40 words, in `templates/host-block.md` (400-word ceiling
  holds). `orch-integrate` retires to: `tickets.py land` (exists) + the
  disposition/blame table staying in `rules/delegation.md` §9, applied by
  the orchestrator as its one judgment at the join.
- `CALLABLE_EXECUTORS` shrinks to: `orch-outline`, `orch-decompose`,
  `orch-execute`, `orch-check` (+ `script:` rung). Both retirees enter
  `SUPERSEDED_EXECUTORS`. Gate stubs, worklog rendering, and
  `tickets_dispatch_gate.py` references sweep to the script names.
- The four thinking jobs keep their names. No renames: grep continuity
  outprices naming taste (documentation law).

Acceptance: a graph run end-to-end with no engine dispatch — every
launch traces to a driver invocation of script output. Oracle: run
record shows zero `orch-frontier`/`orch-integrate` dispatches; required
gate green; `tests/test_seven_skills.py` becomes the registry census at
four (rename the module honestly).

## U4 — Ticket diet

One `contracts/work-item.md` supersession, batched:

- `claimed_by`/`claimed_at` move off ticket frontmatter into the dispatch
  record beside it (`orchflows.dispatch.v1` already owns the lease);
  tickets keep `status` only.
- `isolation` is derived from the stamped pack's adapter
  (`establishes_isolation`); the field survives only as the rare explicit
  override, default absent.
- `sequence` retires in favor of the pack's `stages` list (the cohesion
  spec's cell-sequence form): a ticket naming stage N of its pack runs
  the chain at the head's role. `SEQUENCE_NAME_RE` and its `orch-` prefix
  wedge delete with it.

Acceptance: a ticket's frontmatter is `run, id, status, executor, pack,
depends_on, seal refs` + optional overrides, nothing else; every removed
field has one script-owned home. Oracle: required gate green;
`tickets.py lint` rejects the removed fields as unknown.

## U5 — Agent-consumption sweep of docs

`README.md` stays human. Everything else answers to law 6:

- Heal the dead tiers: `rules/token-economy.md` §11 and
  `rules/composition.md` §5 still budget "instance and utility bodies";
  rewrite to the live tiers (kernel/engine/workflow until U3, then
  kernel/workflow). `docs/vocabulary.md` retires **instance** and
  **utility** (moving **composition instance** into the composition
  entry) once no law names them.
- `docs/pack-authoring.md`, `contracts/pack-signature.md` — rewritten in
  U1; verify no doc still narrates the cell/lane model (grep
  `--for execute`, `lens cell`, `evidence cell`).
- `DESIGN.md` keeps supersession history (agents read it for why-nots);
  anything in it addressed to a human reader moves to README or deletes.

Oracle: `tools/validate.py` exit 0 with cross-tier warning count at or
below the U-wave floor (29 at `5e31063a`; only falls).

## U6 — The outside proof (cheap, do first)

Before U1: author a toy pack in a scratch project outside this checkout
(`<scratch>/.orchflows/packs/<name>-pack/`, current 9-cell form),
declare adapter `git`, stamp it on one real ad-hoc ticket, run
work + check end to end. The cohesion handoff marks custom packs
"likely true, not observed"; U1 changes the format custom packs must
follow, so observe the current one first, then re-run the same proof
after U1 in the folded form. Acceptance: both runs complete with the
project-scope pack resolving by digest; friction logged for every
refusal met.

## Non-goals, priced

- **outline+decompose merge**: killed. The freeze is dialogic and early;
  the cut is solitary optimization at cut time. One saved name does not
  buy blurring that boundary.
- **Verb renames** (plan/work/judge): grep continuity outprices taste.
- **Fifth adapter** (non-isolating, serialized, receipt-identified
  external state — infra, publication, live ops): the one build that
  unlocks the irreversible-world domains. Separate spec; the pack
  template needs no change to receive it.
- **Perpetual loops**: a host scheduler chaining bounded campaigns; a
  library that promised more would be hiding a missing terminal.
- **Nondeterministic production** (training runs) and **peer
  negotiation**: recorded architecture limits, unchanged.

## Order and shape

U6 → U1 → U2 → U4 → U5, then the U3 gate decision on run evidence.
U1 and U2 are independent after U6; U4 depends on U2 (sequence → stages).
Every unit is one supersession PR with the required gate green and, for
T0 changes, a supersession record citing the superseded pin. End state:
four thinking verbs, one driver, one document per domain, tickets carrying
only branch-worthy fields, envelopes rendered — and every layer above the
contracts either deterministic or cheap to discard when a smarter model
arrives.
