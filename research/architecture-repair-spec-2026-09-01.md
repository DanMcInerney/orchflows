# Architecture repair spec — 2026-09-01

Work order for a fresh agent. Evidence base:
[research/architecture-review-2026-09-01.md](architecture-review-2026-09-01.md)
(the judged, repaired pass-2 synthesis of run `20260901T155911Z`, ~1,700
raw findings across five surface lanes). That report is evidence, not
instruction: every unit below cites it, but this spec is the sole work
order, and where the two differ this spec's rulings win. Tree at spec
time: branch `claude/orchflows-architecture-review-0f5268`, even with
`main` plus the report and this file.

## Rulings already made — not up for re-litigation

1. **Rename scope is brick + door only.** "brick" leaves the vocabulary
   (user ruling) and "door" with it (load-bearing, never defined).
   **frame and seal STAY** — `frame` is the standard call-stack term
   naming exactly its mechanism (`docs/vocabulary.md:34`), `seal` is
   standard integrity vocabulary used in its standard sense; renaming
   either would trade self-explanatory standard usage for churn across
   ~200 sites. "gate" is disambiguated by documentation (U9), not
   renamed. The report's Q3 table marks frame/seal "fails"; this ruling
   overrides it.
2. **No new config file format.** `tools/validate_support/common.py` is
   already the enforced, diff-reviewed budget table; it becomes the
   declared owner of every terseness number. `rules/token-economy.md`
   §11 keeps the law (ceilings only fall, load-frequency ordering, the
   eight-demand cap) and loses the numbers. No limits.toml.
3. **One owner, one witness.** For each mechanically-owned constant,
   exactly one test may pin the literal value independently (the
   oracle that catches a fat-fingered owner); every other reader
   imports the owner. Zero witnesses is unfalsifiable; two is
   duplication. The codebase already demonstrates both halves:
   `tests/test_architecture_owners.py:27-29` (witness) and
   `tests/test_state_root_cases/support.py:22` (importer).
4. **Deterministic refusals are untouchable.** The dispatch protocol's
   causal-order, stale-attempt, and idempotency refusals behaved
   correctly under load in run `20260901T155911Z` and stay exactly as
   they are. Process gaps are fixed with wording (U2), never by
   weakening a refusal.

## Standing constraints (every unit)

- The five `craft.md` sentences matching `CRAFT_SCOPE_ANCHOR`
  (`scripts/tickets_assignment.py:50-54`) are live dispatch machinery:
  no unit edits, moves, or link-replaces them. Report §T2 has the full
  mechanism.
- `tests/test_architecture_owners.py`'s `CEILING_RE` reads
  `ARCHITECTURE.md:3`'s number from the prose at test time. The number
  stays in the prose.
- Word ceilings only fall. A kernel body edit stays under 300 words
  (`common.py:24`); check with `tools/validate.py` before committing.
- No T0 shape changes are needed anywhere in this spec (the narrowed
  rename avoids every contract field). If a unit ever appears to need
  one, stop and hand back — that is a scope error.
- Required checks per AGENTS.md gate every unit; the tip runs
  `python tools/run_required.py --no-cache`. Adding or removing tests
  regenerates the serial manifest. Reinstall after merge.
- Log friction per the host block's law as you hit it. Six entries from
  the review run are already in the sink; U2 answers two of them.

## Phase 1 — live wrong instructions (smallest, most urgent)

**U1. Fix both kernel bodies' contract-drifted clauses.**
Report P1/T1, verified in source, widened by the raw-findings residue
read. (a) `skills/kernel/orch-judge/SKILL.md:15-17` instructs a
"seven-field findings array" that "the join reads... and binds in the
ledger." Contracts say five fields (`contracts/shapes.json:179-187`)
and the join binds nothing (`contracts/dispatch.md`'s supersession log,
`contracts/result.md:42-51`). Keep what is still live law: findings
written to one file, its path named in the report (the `findings:`
launch line rides `tickets_registry.py:35`'s `files_findings`). Delete
the field count and the join-binds claim. (b) `orch-do`'s Return clause
("status, result identity, verification, and the pack evidence record",
`skills/kernel/orch-do/SKILL.md:25-26`) names a `verification` envelope
field the same supersession log documents as removed — B1.4's raw
packet caught this and the report's dedup dropped it; verify against
the current envelope shape and align. Acceptance: neither body
contradicts a contract; both ≤ 300 words; `tools/validate.py` green.

**U2. Two conditional fixes to the generated launch prompt.**
Both answer friction logged in run `20260901T155911Z`; find the prompt
composer by grepping scripts/ for "Close exactly once".
(a) *Commit clause conditional on isolation.* Three of five
research-pack children skipped committing because the prompt
unconditionally says "Commit your work inside this candidate" while the
research craft's `## Workspace` is an evidence store with no commit
concept (`packs/orch-research-pack/references/craft.md:30-33`). Emit the
commit clause only when the adapter establishes a git candidate; for
evidence-store/derived-none adapters emit the pack's own workspace
channel line instead. Key off the existing adapter registry
(`scripts/tickets_adapters.py`), not a new contract field.
(b) *Close-after-returns sentence.* Two children (B1.4, B1.5) committed
their outcome while self-dispatched sub-agents were outstanding; the
causal-order refusal then correctly sealed ~190 findings out of the
Report channel. Add one sentence to the close paragraph: close only
after everything you dispatched has returned. One sentence — the prompt
was deliberately trimmed 22→17 lines in PR #158; each addition must
earn its line, and this one has two same-run recurrences as evidence.
Acceptance: a research-pack `do` launch renders no commit clause; a
code-pack launch still renders it; prompt tests
(`tests/test_dispatch_launch.py` family) updated via their owners, not
by retyping literals.

**U3. State the verification-scope law in prose, additively.**
Report P2/T2. `rules/verification.md` — the file `docs/vocabulary.md`'s
"unit" entry names as owning unit scope — nowhere states the law the
five craft sentences carry. Add it there, in prose, touching none of
the five sentences (standing constraint). Acceptance: a reader
following vocabulary.md's pointer now finds the law; all five craft
files byte-identical to before.

## Phase 2 — mechanical roots (highest fan-out)

**U4. Bootstrap-safe resolver leaf.**
Report P3/P4/T3. One new zero-import module (report suggests
`scripts/_bootstrap.py`, ~20 lines) owning exactly two facts: the sink
env-var name (today `scripts/state_root.py:38`) and the
`__file__`-relative repo-root walk. `state_root.py` imports from it;
the 12+ env-var redeclarations and ~20 root-walk re-derivations
(report P3/P4 site lists) switch to importing it. Per ruling 3, keep
exactly one witness: `tests/test_state_root_cases/` pins the literal
value once; every other test imports. `tools/suite_check.py:206-207`'s
bootstrap-ordering workaround dissolves — delete its comment and copy.
Two residue sites the report's count missed:
`scripts/tickets_store.py:31`'s `NO_SINK_ERROR` spells the env-var name
inside a live runtime error string (build it from the constant), and
`scripts/orchflows_home.py:43-57`'s `MANAGED_IGNORES` hand-spells six
sink-subdirectory names, several with no named root in `state_root.py`
— give the subdirectory names owners there and derive the ignore list.
Acceptance: repo-wide grep finds the env-var string literal in exactly
three places — the bootstrap leaf, `rules/visibility.md` §6, and the
one witness test; suite green.

**U5. Budget numbers get one owner.**
Report Q2 table, amended by ruling 2. `common.py` is the owner.
Changes: (a) `token-economy.md` §11 drops its seven restated numbers,
keeps the law, points at the owner; (b) `rules/composition.md:19`'s
140 drops to a pointer (`DESCRIPTION_BUDGET` already enforces it);
(c) `DESIGN.md:190`'s false "60-non-empty-line" claim is corrected —
pointer, not a fresh literal (`CRAFT_BUDGET` is 130, verified);
(d) delete dead `MANIFEST_BUDGET` (`common.py:32`, zero consumers);
(e) the routing-block 400 ceiling is currently enforced nowhere —
add enforcement where the project routing block is rendered/synced
(agent locates the surface; acceptance is a deterministic check that
fails an oversized block); (f) resolve whether the role-agent-file 80
and the rendered-body `BODY_CEILING = 80`
(`tests/test_installer_cases/managed_text/roles.py:52`) are one fact
or two coinciding numbers, and leave one owner either way.
Acceptance: each budget number greps to one code owner plus at most
one witness; prose states no number the owner already states.

## Phase 3 — checks that stop recurrence

**U6. Lifecycle-literal and roster lint.**
Report P6/P7/P8/T5/T6. Two additions to the existing validator family:
(a) an AST-level check refusing bare lifecycle/record-prefix string
literals (`"pending"`, `"claimed"`, `"suspended"`, `join:`/`lifecycle:`
prefixes, `workspace_branch`/`workspace_baseline`/`workspace_path`,
`"receipt.json"`) outside each string's declared owner — site lists in
P7/P8; (b) close `SUPERSEDED_EXECUTORS`' coverage
(`scripts/tickets_registry.py:55-73`) so the five partially-overlapping
retired-name test rosters (P6 list) read the registry instead of
retyping subsets. Per ruling 3 each closed set keeps one witness.
Acceptance: reverting one of P7's thirteen bypass sites makes the new
check fail; the five rosters import.

**U7. Generate the hand-authored topology facts.**
Report P5/P10/T4/T8. (a) A renderer in the existing `tools/render_*`
family reads `.github/workflows/checks.yml`'s matrix/exclude rules and
stamps the leg breakdown into `tools/preflight.py`'s docstring and
`tests/tree_removal.py` as generated blocks — both current hand-typed
breakdowns are wrong and disagree (verified: two Ubuntu, one macOS,
two Windows); (b) `tools/run_serial_compat.py`'s hardcoded sentinel
count reads `len(manifest["sentinels"])` instead; (c) extend doclint so
a `§N` citation fails when section N's heading text mismatches a
declared expectation — catches P5's three wrong-section citations and
all future ones. Acceptance: regen is idempotent and drift-checked by
`tools/regen.py`'s existing mechanism; a deliberately wrong section
citation fails validate.

## Phase 4 — the rename (one commit, narrowed)

**U8. brick + door leave; one mechanical commit.**
Report Q3 occurrence map plus T9's split-rename warning (five friction
entries from the 2026-08-31 two-branch rename fence justify the
one-commit rule). Scope per ruling 1: only "brick"/"bricks" and the
undefined "door". Replacement: name the verb where possible ("a `do`
ticket", "the `tickets.py do` command"), "kernel callable"/"callable"
where a collective noun is needed; "door" becomes "the minting
command" or the verb itself. Touch every map entry: docs/rules/root
docs (~45 sites), `scripts/tickets_brick.py` and its importers plus
`BRICK_*` constants and registry refusal strings
(`tickets_registry.py:62-64`), `contracts/work-item.md` ×10 /
`dispatch.md` ×2 / `result.md` ×2 (prose edits, no shape change),
`example-workflows/self-improve/SKILL.md` ×3, `installer/packages.py`
rendered adapter text (re-render every installed surface),
`tests/test_ticket_bricks.py` + ten sibling files (~100 sites). The
two kernel SKILL.md files use neither word — do not touch them. In the
same commit: add the metaphor-test sentence to `docs/vocabulary.md`'s
preamble (report T10 wording: a term names its mechanism in plain
words; metaphor only where already domain-standard — kernel, cache,
shard, sentinel; never invented for this library), fold the brick
entry into a plainly-named callable entry, and define or eliminate
every remaining "door" occurrence. frame/seal/gate sites: untouched.
Acceptance: repo-wide grep for the metaphor is empty outside
historical/supersession text that names it as retired; suite green;
reinstall renders no stale term on any host surface.

## Phase 5 — cleanup and documentation debt

**U9. Vocabulary entries for the undefined load-bearing terms.**
Report Q3 table rows "fails on documentation". Add `docs/vocabulary.md`
entries (each 1-3 lines, mind its own authoring budget) for: ring,
bundle, trust ledger, shadow notice, pin, surface, vantage, emission,
shared-workspace, adapter, seam, sentinel, shard. Disambiguate "gate"
with one entry naming its live senses and retiring the rest (five
unconnected senses, P6/Q3 — worst term found); disambiguate the
"judge" noun vs `orch-judge` callable collision the file already
self-acknowledges at `docs/vocabulary.md:235-239` (open friction entry
2026-08-31). Benchmark-family "rung"/"tier" senses get their own words
per the report's ladder/rung row. Residue addition: correct the
**baseline** entry (`docs/vocabulary.md:204`) — it says "proven clean
starting state" but the owning code stamps a recorded-dirty state by
design (`scripts/workspace_git.py:308-322`, whose own docstring states
the divergence); redefine as the recorded starting state, clean or
recorded-dirty. Acceptance: every term the review
found load-bearing resolves to exactly one entry; the self-acknowledged
"naming debt" sentence is gone because the debt is paid.

**U10. Dead-code sweep.**
Report P13. Delete: unused test helpers `SequencedPath`,
`refusing_to_read`, `refusing_to_write`
(`tests/test_tickets_cases/common.py:248,288,328`) and dead constants
(`common.py:50-52` of that file); the duplicated
`tickets_dispatch_facade` import (`tests/test_lock_discipline.py:30-31`);
dead imports in `tests/test_validate_cases/sink_contracts.py:20-41`,
`validator_ownership.py:2`, `test_validator_cases/support.py:3,6`;
`seed_user_frontend` (`tests/test_installer_cases/support.py:222-227`).
Fix the vacuous test at
`tests/test_tickets_cases/identity_terminal.py:310` — it exercises a
retired `check` subcommand and green-passes on "unknown subcommand"
instead of the sink-unwritable law it names; retarget it at a live
subcommand or delete it. Reader duplicates (P11): drop the dead
server-side layout constants (`reader/scripts/ui_layout.py`) the
browser recomputes, dedupe `NAME_RE` and the three `REDACTED_HOST_PATH`
copies. Fix the two fixture READMEs citing nonexistent
`tests/test_ui.py`.
Residue additions from the raw packets (each verified by its lane, all
stale/dead classes the report's pattern-dedup dropped):
`scripts/tickets_worklog.py:28`'s `ITERATION_ID_RE` still matches the
retired `.iter.` round-id spelling while `tickets_format.py:100-104`
owns the live `.repair.` grammar — a behavior drift, not just prose
(and `tickets_format.py:324`'s docstring example has the same stale
spelling); `scripts/tickets_emission.py:3,126,166` name doors that no
longer exist (amend/recut/gate/instantiate) and `:172` cites a function
(`tickets_issue._replace_and_invalidate`) that exists nowhere in the
tree; `scripts/tickets_context.py:3-7` treats retired `ready`/`claim`
as live doors; `scripts/tickets_worklog.py:24,32,41` dead
`_packs_root`/`_upstream`/`PACKS_DIR` and `tickets_format.py:90-91`
dead `PACK_NAME_*` constants; `scripts/tickets_bound.py:63` reuses
`DEFAULT_BOUND_MINUTES` as an unrelated minutes-per-iteration factor —
split into two named facts; `scripts/rings.py` duplicates its
shadows/notice/reserved logic between `resolve()` and `inventory()`
(:329-341 vs :394-403) — factor once;
`tests/test_script_executors.py:32-77` builds fixture tickets with
pre-migration section headings (Objective/Fixed inputs/...) that no
longer match the sealed Goal/Context/Details schema; dead installer
surface — `installer/packages.py:289,296` (`template_markers`,
`resolved_python_interpreter`), `installer/application.py:25` unused
import, the unreachable `manage_host_surfaces=False` branch
(`application.py:333`, `presentation.py:124`) and the project-scope
generality `planning.py:466-467` can no longer produce;
`installer/hosts.py:16`'s `GROK_MODEL_CENSUS` allows a model nothing
binds; dead tools items — `run_report_support/model.py:32`
`LONGEST_TICKETS`, the vestigial `SLICE_EXECUTOR` filter (`model.py:33`,
plus `render.py:114`'s retired "decompose" wording),
`live_routing_bench.py:77`'s permanently-empty `ROLE_SKILL_ROUTES`
branch, `validate_support/common.py:172` `TEMPLATE_ENTRY_VALUES`.
Acceptance: each deletion's suite lane green; no
new helper added anywhere.

**U11. Tombstone dating and expiry policy.**
Ruling 4's counterpart for history. Date each `SUPERSEDED_EXECUTORS`
entry (retired-on comment); state the policy once — a tombstone whose
refusal has not fired within its horizon is deleted, registry and
tests together — at the registry itself, the fact's one owner. This
unit writes the policy and the dates; the first deletions are a later
run's call. Acceptance: every entry dated; policy stated once.

**U12. Law-text corrections and the ring's one timestamp owner.**
Two residue items outside the earlier units' shapes. (a)
`rules/visibility.md:45` attributes the events-channel write solely to
`scripts/tickets_frame.py` and `scripts/tickets_land.py`, but the
writing function `_append_event` is defined in
`scripts/tickets_result.py:238` — a false fact in a law file; correct
the attribution (and decide whether the function should move to match
the law instead). (b) The project ring's super-research package
declares its output-timestamp literal at least sixteen independent
times through three different mechanisms (per-adapter
`RECORD_INSTANT_FORMAT` redeclarations, an inline `strftime`, a
hand-built `format()` — B1.4 supplement's site list), while
`references/protocol.md:99` claims `schema.INSTANT_FORMAT` is the one
definition; make it so — one shared constant in the package's
`_support`, every adapter importing it, `open_page.py:108`'s aliasing
pattern as the model. Distinct upstream wire-format grammars (X's, RFC
3339) keep their own constants; only the one output convention
consolidates. Acceptance: the protocol.md claim is true by grep.

**U13. Standing-instruction surfaces: buy back headroom, fix two scoping gaps.**
From the close-out audit of the every-turn surfaces, all three of which
sit exactly at their ceilings (host block ~400/400, `AGENTS.md`
230/230, role agent bodies 80/80 — zero headroom anywhere, and
`rules/token-economy.md` §11 says a ceiling only falls, so growth is
impossible without deletions). (a) `AGENTS.md`, two delete candidates:
the Constitution meta-sentence ("The Constitution in
docs/library-review.md requires every sentence here") fails
token-economy §1's own test — no executor acts differently for it —
and the three-line super-research item note duplicates what the
adapter's manual-only marker already enforces (verify the marker
actually blocks model invocation before deleting; if it does not, that
is the bug to fix instead). Both may be phrase-pinned by
`tests/test_constitution.py`-family tests — adjust the pins through
their owners, never by retyping. ~35 words of headroom bought.
(b) Role agent files: "never redispatch" did not stop three children
from fanning out background read-only agents (the direct cause of the
causal-order strandings) — the word is doing less than it claims.
Reword to plain mechanism ("never hand your ticket or role to another
agent") and rely on U2(b)'s close-sentence for the fan-out discipline;
same word count. (c) Friction-law reach: all six of this run's
friction entries were root-logged; children hit four log-worthy walls
and logged nothing (friction entry 2026-09-01, this run). Investigate
whether forked children actually receive the host block's friction
law; if they do, this is behavioral and the entry stands as evidence;
if they do not, the launch prompt is the only carrier and one pointer
line there is justified despite the prompt budget. Acceptance: AGENTS.md
under its ceiling with headroom; role files unchanged in length;
the reach question answered with evidence, not assumption.

## Deferred — named, not scoped here

- The browser-game trunk/leaf inversion
  (`scripts/browser_game_validate.py`, `tools/validate_support/
  browser_game.py`, the single-entry allowlist in `structure.py:29`) is
  a genuine extension-point design project; the report's map flags it
  as the clearest inversion found. Needs its own spec.
- Custom-skill declared-budget frontmatter (report's terseness
  mechanism, grounded in super-research at 740 words/no applicable
  ceiling) — depends on U5's owner table; spec it after U5 lands.
- Pre-migration example-workflows (browser-game, benchmaker, evolve,
  drift-canary, renovate, skill-tournament) are migration debt by
  standing instruction; nothing in this spec edits them except U8's
  three self-improve sites.
- The `write_scope` frontmatter key: `scripts/workspace_candidate.py:69-84`
  enforces a schema whose refusal text cites `contracts/work-item.md`,
  but the contract's generated frontmatter table declares no such field
  — the code is the schema's only definition. Declaring it in the
  contract is a T0 shape change (supersession PR); dropping the stale
  citation is trivial but leaves the field undocumented. User decision.
- The search-plan schemas (five closed, hash-pinned shapes) live in
  `docs/search-plan-protocol.md` + `scripts/search_plan_protocol.py`
  rather than `contracts/` — they match the vocabulary's own contract
  definition and arguably belong at T0. A placement decision, not a
  mechanical move.
- Host-block root/child split: roughly 250 of the host block's 400
  words are root-only routing law (the lanes, tripwires, `orch-off`,
  resume) that every dispatched child also pays every turn, since the
  block rides the user-scope CLAUDE.md import. Splitting it — routing
  half loaded by interactive roots, law half (state-sink, friction,
  worktree discipline) always-on — would roughly halve every child's
  standing instruction cost, but restructures the installer's
  managed-block scheme and the eight-demand accounting. A design pass
  of its own; user decision. `validate_routing_block`
  (`tools/validate_support/packages.py`) is the enforcement half already
  built -- checked today against synthetic text for lack of a live
  surface -- so whoever executes this split wires it in against
  whichever half becomes the rendered project-scope routing block.

## Suggested execution shape

U1+U2+U3 are one day of small, independent wording units — worker
lane each, or one team wave. U4 and U5 are independent of each other
and of phase 3. U6/U7 land before U8 so the rename commit is checked
by the new lint. U9-U12 are cheap and parallel after U8. Every unit is
sized for one child context; none needs a sub-agent fan-out — the
review already did the enumeration, and U2's own evidence says a child
that fans out and closes early strands its findings.

## Provenance of the residue items

After the report shipped, the coordinator read all ~1,700 raw lane
findings end to end (the report's dedup had read them once; this was
the independent second read). The dedup held: no report claim was
contradicted. It had, however, dropped the specific items now stitched
into U1(b), U4, U9-U10's residue lists, U12, and the two new deferred
entries — mostly stale-fact and dead-code singletons that fit no
twelve-pattern bucket. Raw evidence: the lanes' packets in the run's
research workspace (B1.1/B1.2/B1.4/B1.5 findings files and
supplements) and ticket B1.3's six Report records, all committed in the
state sink.
