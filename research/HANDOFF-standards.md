# Handoff: run the standards spec

Written 2026-09-04. One piece of work is queued: a four-unit run, specified
and sliced, waiting on a session to drive it. Everything it needs is
committed and pushed.

## Where everything is

| thing | where | state |
|---|---|---|
| spec of record | `research/standards-spec-2026-09-04.md` | committed |
| driver | `research/standards-tickets/RUN.md` | committed |
| unit tickets | `research/standards-tickets/U{0,1,2,3}.{goal,details}.md` | committed |
| judge + repair | `research/standards-tickets/judge.*`, `repair.goal.template.md` | committed |
| branch | `claude/standards-spec`, pushed, tip `c7d9cb57` or later | PR #176, **draft** |
| installed library | `~/.orchflows`, receipt `6d47143e` | current with `main` |
| `main` | `6d47143e` | gate green |

PR #176 is a **draft on purpose**: the spec is a proposal, not a change.
Nothing in it executes until someone drives `RUN.md`.

## What the run does, in one paragraph

Retires three nouns — `pack`, `sheet`, `craft` — for one: a **standard**. A
standard states what a good artifact carries in a domain, and may `narrows:`
exactly one other standard, so specificity cascades: `three-js` narrows
`javascript` narrows `code`. The worker reads the resolved chain broad to
narrow; the judge reads the identical chain at the identical digests. Adds
one optional `## Scaffolding` section — content a perfect executor would not
need, deletable without changing what the standard means — which turns
`docs/library-review.md` criterion 11 from a judgment made afresh at each
review into an operation.

## Before you start

1. **Merge PR #176 first, or don't** — either works. The run branch can be
   cut from `claude/standards-spec` directly, which is simplest, since the
   spec and tickets have to be in the tree the run reads. Suggested run
   branch: `claude/standards`.
2. **Do not reinstall while the frame is open.** U1 changes which frontmatter
   fields the assignment seal covers and U3 renames them. Installing either
   mid-run recomputes every open ticket's digest and refuses every further
   write. Reinstall after `frame-close`.
3. Dispatch every unit with `--pack orch-code-pack`. This run renames that
   flag, but the *installed* trunk still takes the old one until the
   post-close reinstall.

Then hand the new session `research/standards-tickets/RUN.md`.

## The shape

    U0  the contract         wave 1, alone
    U1  resolution      ┐    wave 2, launched together
    U2  the items       ┘
    U3  the rename           wave 3, alone
    judge over the joined tip, then bounded repair, then the gate

Three things in the driver that are easy to skip and expensive to miss:

**U1 and U2 work under the old directory names on purpose.** Items stay in
`packs/` and `sheets/` while those two units change behaviour and content;
U3 moves and renames everything afterwards. A `git mv` racing an edit reads
as a rewrite and the judge cannot see what changed. The judge is told to
read the U2/U3 seam first for exactly this.

**U3 is alone in its wave** because the rename reaches every file the other
three touched. It is the largest unit — roughly forty files, nearly all
spelling — and its bound is set for a sweep. If it comes back having
designed something, that is a finding.

**One judge, after the last wave, over the joined tip.** Not one per unit.

## Numbers the run must hit

Each was measured against the tree, not estimated. A child that reports one
without a command behind it is a finding.

| | |
|---|---|
| `install.py --dry-run` at base | 359 entries |
| after | 25 fewer — 20 deleted host adapters + 5 collapsed second files |
| `STANDARD_BUDGET` | 1200 words, whole manifest, equal for root and narrowing |
| largest manifest today | `orch-design` at 920 words |
| host block ceiling | 400 words, must still hold |
| `AGENTS.md` ceiling | 230 words, must still hold |

## Three things I got wrong while writing the spec

All three are fixed in it, and all three are the same failure — writing from
a plausible reading instead of from the tree. They are recorded here because
the spec now tells its children to verify exactly these, and a driver who
knows why will read those instructions properly.

1. **Adapter values.** I wrote `doc` and `evidence`. The tree says
   `document-tree` and `evidence-store`. Those are workspace-mechanism keys;
   `git`/`doc`/`evidence` are the `## Lens` adapter *kinds* — a different
   vocabulary. A child copying my values while moving the cell into
   frontmatter would have silently rekeyed every Lens entry in the library.
2. **Twenty adapters, not fifteen.** Codex renders two files per item, a
   prompt and a redirect skill. The `by-name` pointers stay.
3. **The budget.** I flattened two ceilings into one number without noticing
   there were two, and the flat number would have broken `orch-design` on
   contact. It is now one ceiling again, but by your decision and in words —
   line ceilings are gamed by writing longer lines.

## Successors the spec defers

- **Routing to narrowings.** Decision 6 keeps them authored-only. Turning
  routing loose is purely additive and needs its own evidence about how a
  router picks depth.
- **A ring-level house standard.** A `house:` field in `BUNDLE.md` that
  prepends one standard to every chain resolved from that ring would let a
  house style sit above shipped roots without forking one. Decision 3's
  optional adapter is what makes it possible later.
- **Ratcheting `STANDARD_BUDGET` down.** 1200 was chosen for migration
  safety, not as a target. A ceiling in this library only falls, and
  lowering it once the shipped standards have had their `## Scaffolding`
  deleted is the cheapest version of the pressure decision 4 declined to
  build.
- **Splitting the shipped roots.** Nothing is near the ceiling. The pressure
  appears only when promoting a narrowing's content up into a root.

## Unrelated, still open

Two pull requests from earlier sessions are open and are not this run's:
#166 (tiktok-video gallery workflow) and #167 (browser-game workflow body).
#167 wants its CI watched to completion before merging.
