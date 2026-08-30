# Mechanical-trunk hardening spec — 2026-08-30

Status: approved for implementation. Source: the 2026-08-30 deep review
(5 agents + 13 lanes over PRs #117–#136, ~30 session transcripts, 7,200+
friction records, line review of `scripts/`). Executed by plain worker
agents, NOT through orchflows.

## Goal

Eliminate six recurring bug classes by giving every deterministic fact and
every multi-step transaction exactly one mechanical owner:

- T1: the LLM sequences dispatch/launch/join by hand → ordering bugs.
- T2: worktree/isolation has no mechanical owner → the largest friction
  cluster (341 entries Aug 21–30 alone).
- T3: one fact defined in N places → drift bugs at every layer.
- T4: derived artifacts with no regeneration owner → stale installs,
  manifests, fixtures, pins.
- T5: refusals with no mechanical remedy → LLM improvisation, wedged runs.
- T6: tickets/packets carry stale values instead of derivation commands.

## Global conventions (bind every unit)

- Repo: `C:\Users\danhm\tools\orchflows-public\.claude\worktrees\subagent-arch-review-f5130b`.
  Work in place. Never `cd` outside it. Never touch `~/.orchflows` or any
  host config.
- Interpreter: `uv run --no-project python` (bare `python` is a Windows
  Store stub). Python 3.9+ compatible, Windows + POSIX, no network.
- Workers NEVER run `git commit`, `git push`, `git stash`, or create
  branches. The coordinator commits per wave.
- Read before editing: every file named in your unit's write scope, plus
  `ARCHITECTURE.md` and the contract(s) your unit cites. Stay inside your
  write scope; if a needed change falls outside it, report it in your
  return instead of making it.
- Tests: during work, `uv run --no-project python tools/run_tests.py
  --scope <changed-paths>`. Before returning, the full five:
  `uv run --no-project python tools/run_required.py`. If you add/remove
  tests, regenerate the serial manifest:
  `uv run --no-project python tools/run_serial_compat.py --write-manifest`.
- Source-size ceilings are enforced by `tools/check_source_sizes.py` (via
  validate). If your change pushes a module over, split per the family
  convention (unprefixed facade + `<family>_<concern>.py` helpers) and say
  so in your return.
- T0 discipline: adding/removing/renaming a named field or enum in
  `contracts/*.md` shapes is a T0 shape change — every unit EXCEPT U9 is
  designed to avoid them. U9 is the one sanctioned supersession (verb
  rename + new pack cell) and carries its own supersession records.
  Prose edits to contracts re-pin without supersession
  (`uv run --no-project python tools/validate.py --pin` in an LF-clean
  tree). If any other unit cannot be done without a shape change,
  stop and report; do not improvise one.
- Error strings: any refusal that tells the caller to do something must
  name a command that exists (see U4.3's guard — write your messages to
  pass it).
- Encoding: all file writes UTF-8 with `\n` newlines; never rely on
  console encoding; never instruct callers to shell-redirect tool output
  to a file.
- Return format: a terse report — what changed (file list), what each
  invariant now guarantees, test evidence (names + counts), anything
  out-of-scope you found, any spec assumption that proved wrong.

## Decided design choices (do not relitigate)

1. `depends_on` hashing stays as-is. Instead, canonical order is enforced
   at authoring: draft validation refuses an unsorted `depends_on`, and
   the decomposer's mechanical-correction pass sorts it. Rationale:
   changing `assignment_payload` would invalidate historical seals.
2. Isolation reaches the packet as a normalized VALUE of the existing
   `isolation` field (via `normalized_isolation`), not a new field — no
   T0 shape change.
3. The launch spec (U3) is CLI JSON output, never a persisted/wire shape.
4. The terminal two-file write keeps its order (ticket first, identity
   second) but a rollback failure is surfaced with both errors and the
   exact retry command; nothing is swallowed.
5. Both `sequence` forms (skill-name chain, pack-stage chain) stay. The
   one role law: the ticket's `executor` (the chain head) establishes the
   single role; continuation `role:` is inert. Text alignment is U7.
6. Worktree candidates live under `<orchflows-home>/worktrees/<run>/<ticket>`
   (short paths for MAX_PATH); branch `wt/<run>/<ticket>`. Path
   derivation is a pure function with one owner.
7. Workers are refusal-biased: when a unit's instruction conflicts with
   what the code actually shows, report the conflict; don't guess.

## Units

Waves (sequential; ∥ = parallel within a wave, write scopes disjoint):
W1: U1. W2: U2 ∥ U6. W3: U3. W4: U9 (rename + outline cells). W5: U7
(law text, post-rename). W6: U5. W7: U4. W8: U8 + dead-code sweep.
Docs are a separate spec (`research/docs-spec-2026-08-30.md`).

---

### U1 — Lock and write discipline

Motivation: unlocked mutating paths and ordering holes found at the tip
(review findings 5–13): malformed-run-id handlers skip the lock but then
proceed; `workspace_git._record` races outside `_run_lock`;
standalone `dispatch-packet` pre-checks run unlocked; any ticket can claim
the run's terminal-identity slot; `dispatch-open` checks seal before
replay; the store's atomic-write helper imports the CLI facade on every
write.

Write scope: `scripts/tickets_store.py`, `scripts/tickets_lifecycle.py`,
`scripts/tickets_attempts.py`, `scripts/tickets_dispatch_packet.py`,
`scripts/tickets_dispatch.py`, `scripts/tickets_project.py`,
`scripts/workspace_git.py`, `scripts/workspace.py`, `scripts/tickets.py`,
`scripts/tickets_join.py`, tests under `tests/`.

Deliverables:

1. **Structural locking.** Add one store-owned primitive (e.g.
   `locked_ticket_write(run, ticket_id)` context manager) that (a)
   validates BOTH segments with `_segment_error` and refuses malformed
   ids with a structured error, (b) acquires `_run_lock`, (c) yields the
   canonical ticket path. Convert `_cmd_check`, `_cmd_set_status`,
   `_cmd_join_noop_repair` (tickets_lifecycle.py:183,264,273) and the
   `tickets_project.py` twin to it. A malformed run id must now refuse —
   never fall through to an unlocked handler. Delete the
   "skip-lock-on-bad-id" pattern everywhere.
2. **`workspace_git._record` under the lock.** The read-compare-write in
   workspace_git.py:233-271 runs inside `_run_lock`, and the update is
   computed from the text read under the lock (not a pre-lock snapshot).
   `workspace.py start` invoked standalone must take the lock itself;
   invoked from the dispatch facade it must not deadlock (accept a
   `_lock_held` flag or restructure so the facade passes the lock down —
   match the existing `_lock_held` convention in
   tickets_dispatch_packet.py).
3. **Standalone `dispatch-packet` fully locked.** `_cmd_dispatch_packet`
   (tickets_dispatch_packet.py:236) wraps its whole body (reads +
   commit) in `_run_lock` when `_lock_held=False`.
4. **Root-only terminal identity.** `_cmd_dispatch_join`
   (tickets_join.py:467-481) calls `_terminal_identity_update` only when
   the joined ticket is the run's root (the ticket named by
   `root_generation`, or the run's single ticket for ad-hoc/direct runs
   — derive the predicate from existing data, single owner, with tests
   for: root joins last, root joins first, ad-hoc single ticket, loop
   ticket).
5. **Replay-first `dispatch-open`.** In tickets_attempts.py:127-147,
   check exact-replay of an already-opened `(dispatch_id)` BEFORE
   `seal_findings`, mirroring `_commit_record`'s precedence, and return
   the stored success on replay.
6. **Kill the facade back-import.** `_waiting_out_windows`
   (tickets_store.py:282-294) must not import `tickets`. Investigate why
   `_sync_seams` exists (test monkeypatching through the facade is the
   likely reason); repoint those tests to patch the owning module, sync
   seams once at facade import if still needed, and delete the per-write
   call. Helpers never import the facade — add a test asserting no
   `scripts/tickets_*.py` or `scripts/workspace*.py` module imports
   `tickets` at module or function level (allow the facade itself).
7. **Surfaced terminal-write failure.** tickets_lifecycle.py:405-415: on
   a failed identity write followed by a failed rollback, return an
   error naming both underlying errors and the exact retry command
   (`tickets.py set-status <run> <id> <status>` replays idempotently —
   verify and test that replay path).
8. Remove the unreachable retire-state check (tickets_attempts.py:371-375)
   and fix the `_sync_seams` coverage asymmetry by deleting the mechanism
   (item 6) rather than extending it.

Acceptance: new tests for each of 1–7 (including a regression test that
`tickets.py check ".." X --stage X.check` and the set-status/join-noop
twins refuse without writing); five required checks green.

---

### U2 — Workspace owner: mechanical worktree creation

Motivation: no script anywhere creates the per-subagent worktree
(work-item.md calls it "host-owned", i.e. LLM-improvised); isolation is
recorded rather than enforced; stamps are non-idempotent; `start`
sometimes emits nothing; packets have carried another ticket's workspace.
Review findings 14–22; friction theme 1 (341 entries).

Write scope: `scripts/workspace.py`, `scripts/workspace_git.py`,
`scripts/state_root.py`, `scripts/tickets_dispatch_facade.py`,
`scripts/tickets_dispatch_packet.py`, `scripts/tickets_adapters.py`
(read; edit only if adapter properties need a new property surfaced),
tests under `tests/`.

Deliverables:

1. **Path derivation, one owner.** `state_root.py` gains
   `worktrees_root()` → `$ORCHFLOWS_WORKTREES_HOME`, else
   `<orchflows-home>/worktrees` (sibling of `state/`; orchflows home
   resolved the same way state root is today). Pure function
   `candidate_paths(run, ticket_id)` → `{path, branch}` with
   `path = worktrees_root()/<run>/<ticket>` and `branch =
   wt/<run>/<ticket>`. Nothing else may compute these.
2. **`workspace.py establish <run> <id> --repo <source-tree>`**: for a
   ticket whose normalized isolation is `required`, creates the worktree
   (`git worktree add -b <branch> <path> <baseline>`), where baseline =
   the source tree's current HEAD unless the ticket already carries
   `workspace_baseline`. Idempotent: if the stamp already exists and the
   worktree matches it, return the same JSON with `"replayed": true`;
   never restamp `workspace_baseline` on re-establish (fixes the
   baseline-rewrite defect). If creation fails (branch exists with
   different tip, path occupied by a foreign tree, git error), REFUSE
   with a structured error — never record success, never fall back to
   the shared tree. For isolation `none`, behave as today's `start`
   (observe + stamp). Always emit exactly one JSON document on stdout
   (fixes silent-success; add a test asserting non-empty stdout on every
   exit path).
3. **`workspace.py retire <run> <id>`**: removes the derived worktree
   (`git worktree remove` + prune; `--force` only with an explicit flag)
   and records nothing on failure beyond a structured error naming the
   manual command. Safe when the worktree never existed (no-op JSON).
4. **Facade integration.** `tickets_dispatch_facade._cmd_dispatch` calls
   establish (not observe-only start) after `dispatch-open`, preserving
   the d0b6bc4c ordering (open → establish → packet). The workspace
   value baked into the packet comes ONLY from establish's return, and
   the `isolation` value in the packet passes through
   `normalized_isolation` (fixes the raw-passthrough at
   tickets_dispatch_packet.py:139). An isolation-required ticket whose
   establishment fails refuses the dispatch as one transaction (attempt
   retired or never opened — reuse the existing failure path).
5. **Truthful sharing check preserved.** Keep exit-code-7 semantics for
   genuinely shared trees in the observe path; establish makes that path
   unreachable for `required` tickets in the facade flow.
6. Git subprocess work runs OUTSIDE `_run_lock` where possible: prepare
   (worktree add) unlocked against the derived path (collision-safe by
   derivation), then validate + stamp under the lock (coordinates with
   U1.2; reduces the lock-span problem, review finding 12).

Acceptance: tests covering create/replay/refuse/retire, Windows path
length (derived path stays under ~150 chars for realistic ids),
facade-integration test proving two dispatched isolation-required
siblings get distinct worktrees and distinct packet workspace values;
five checks green.

---

### U3 — `dispatch` completes the launch; `land` completes the return

Motivation: the role→launch hop is the one LLM-transcribed link (wrong
model killed a dispatch; hosts/*.json is hand-read); the return side is
three hand-sequenced commands; oversized inline packets caused the
dead-worker misdiagnosis. Review findings 23–24; roles trace step 4.

Write scope: `scripts/tickets_dispatch_facade.py`,
`scripts/tickets_dispatch.py`, `scripts/tickets_join.py`,
`scripts/tickets_outcome.py`, `scripts/tickets_sequence.py` (read),
`hosts/*.json` (read; extend only if a needed field is missing — that is
data, not a T0 shape), `contracts/dispatch.md` (prose only),
`skills/engines/orch-frontier/references/profiles.md` (read), tests.

Deliverables:

1. **Launch spec in dispatch output.** `tickets.py dispatch` gains
   `--host <claude|codex|grok>` (default from `$ORCHFLOWS_HOST`, else
   `claude`). After packet commit it resolves role → profile → concrete
   launch binding from `hosts/<host>.json` and emits a `launch` object in
   its JSON result: `{verb, agent, model, effort, prompt}` where
   `prompt` is the packet-pointer text the child needs (packet path +
   receipt command + the fixed identities per work-item.md's executor-
   records section). The orchestrator's job becomes: invoke that verb
   with those fields verbatim. A packet `profile` override wins, per
   roles.md §4. Resolution failures (unknown role, host file missing the
   profile) refuse the dispatch before any side effect.
2. **`tickets.py land <run> <id>`**: one locked transaction =
   (optional) `dispatch-outcome` import when `--outcome-file <path|->`
   is given → `dispatch-join` → workspace retire (U2.3) for a derived
   worktree. Replay-safe end-to-end (each inner op already replays;
   `land` composes them and reports which steps replayed). On join
   success it also emits the run's newly-ready frontier (reuse the
   existing `ready` computation read-only) so the caller sees what to
   dispatch next without a second command.
3. **Inline→reference auto-switch.** In packet projection, an inline
   snapshot whose canonical JSON exceeds a threshold (default 16 KiB,
   `--inline-limit` to override) is refused with a message directing to
   reference form — or, when the facade chose inline itself, it silently
   selects reference. Never emit an unbounded inline packet.
4. **Transaction invariant in prose.** Add to `contracts/dispatch.md`
   (prose section, no shape change): "Facade transactions order side
   effects after the last refusable check; a failed step surfaces its
   own error plus any failed cleanup; every step replays idempotently."
   Re-pin.

Acceptance: tests for launch resolution per host file (including
profile-override and unknown-role refusal), `land` happy path + replay +
outcome-carrying variant, inline threshold; five checks green.

---

### U4 — Staleness heals itself; refusals name real remedies

Motivation: receipt staleness after lawful mutation wedged runs ≥5 times;
whole-snapshot CAS refuses tickets for unrelated sibling changes; known
dead ends (corrupted run.json, `limited` dependency, claim-on-pending);
`tickets.py result` rejects valid level-2 headings (~18 recurrences).
Review findings 29–34.

Write scope: `scripts/tickets_lifecycle.py`, `scripts/tickets_admission.py`,
`scripts/tickets_generations.py`, `scripts/tickets_store.py`,
`scripts/tickets_result.py`, `scripts/tickets_markdown.py`,
`scripts/tickets.py`, `scripts/tickets_issue.py` (only if the sorted-
depends_on correction lands there), tests.

Deliverables:

1. **Scoped CAS.** `_snapshot_matches` (tickets_lifecycle.py:67-69)
   honors its `_ids` parameter: compare only the graded ticket + its
   dependency closure (`snapshot_ids` from grade_admission). Unrelated
   sibling changes no longer refuse a ready/claim.
2. **Lawful mutation recomputes dependents.** The recut/seal path in
   tickets_generations recomputes admission receipts for every already-
   claimed/ready member whose receipt its own mutation invalidated, in
   the same transaction — a lawful recut leaves no member holding a
   stale receipt. Test: seal cut generation 2 with a claimed root; the
   root's next packet emission succeeds without manual repair.
3. **Refusal-remedy guard.** New test that extracts every error-string
   command reference (`tickets.py <sub>`, `workspace.py <sub>`) from
   `scripts/*.py` and asserts the subcommand exists in the CLI surface.
   Fix the two known liars (the stale-claim recovery text naming a path
   the seal forbids; any message naming removed commands).
4. **`limited` satisfies a Result-reference dependency.** Admission
   accepts a dependency in any terminal state that carries a Result
   (complete, limited) for ticket-section fixed inputs; blocked/failed
   still refuse. Test both sides.
5. **`tickets.py repair-run-identity <run>`**: quarantines an unreadable
   `run.json` (rename to `run.json.corrupt-<ts>`) and rebuilds the
   minimal identity from ticket-directory evidence, refusing only when
   evidence is genuinely absent. The tickets_store.py:324 refusal
   message now names this command.
6. **Result bodies may contain `##` headings.** Fix the parser/writer
   pair (tickets_result/tickets_markdown) so a level-2 heading inside a
   filed evidence body cannot be confused with a sibling ticket section
   — indent-quote or fence on write, reverse on read, byte-stable across
   round-trips. Regression test with the exact recurring payload shape.
7. **Sorted `depends_on` at authoring.** Draft validation refuses an
   unsorted list with a message naming the fix; the mechanical-correction
   path sorts it. Hash untouched (decided choice 1).
8. **Claim-on-pending names its remedy.** The "ticket is not claimable
   in status 'pending'" error names `tickets.py ready --run <run>`.

Acceptance: five checks green; new tests for 1–8. If
`tickets_admission.py` breaches its size ceiling, split it (the
companion/scope grading is the natural extraction) and note it.

---

### U5 — Fact registry: one owner per enum, predicate, idiom

Motivation: duplicated-facts table from the review (findings 42–52).
This is a deletion/consolidation pass; behavior must not change.

Write scope: `scripts/tickets_format.py`, `scripts/tickets_registry.py`,
`scripts/tickets_dispatch_schema.py`, `scripts/tickets_dispatch_validate.py`,
`scripts/tickets_dispatch_packet_shape.py`, `scripts/tickets_attempts.py`,
`scripts/tickets_join.py`, `scripts/tickets_admission.py`,
`scripts/tickets_packet.py`, `scripts/tickets_transitions.py`,
`scripts/tickets_grade.py`, `scripts/tickets_adapters.py`,
`scripts/tickets_sequence.py`, `scripts/tickets_lifecycle.py`,
`scripts/packs_support.py`, `scripts/workspace.py`,
`scripts/workspace_git.py`, `scripts/isolate.py`,
`scripts/tickets_project.py`, `scripts/tickets.py`,
`tools/validate.py` + `tools/validate_support/` (ratchet), tests.

Deliverables:

1. `tickets_format.dequote()` — the single de-quoting primitive;
   replace all 21+ inline `.strip().strip("`").strip()` sites.
2. Review-stage id predicates (`is_gate_stage_id`, `is_critique_stage_id`
   or equivalent) defined once beside `GATE_*_ID` (tickets_packet.py or
   tickets_registry — pick the import-cycle-free home); replace all 9
   substring sites (schema ×4, join ×4, admission ×1); join line 404
   reuses the local from 346.
3. Reserved record-id namespace: `tickets_dispatch_schema` stays owner;
   `tickets_dispatch_validate.namespace_ok` and
   `tickets_attempts.owned` import it.
4. Enums from generated shapes: `durability`, `review_kind` in
   packet_shape use `DISPATCH_PACKET_VALUES`; result `operation`/`mode`
   literals in dispatch_schema use `tickets_shapes.SHAPES`.
5. `CHECKABLE_STATUSES` imported from tickets_transitions everywhere.
6. One dirty-path parser: `workspace_git._dirty_paths` becomes the owner
   (public name); `isolate.py` imports it.
7. `isolate.py` adopts `verify_at.py`'s temp-root refusal (shared rule;
   put the predicate in one place both import — a small helper in
   `scripts/` is acceptable; tools may import scripts, not vice versa).
8. Delete dead weight: the entire unreachable `claim` plumbing
   (tickets_project claim path, its lifecycle/facade re-exports, its
   seam entry), `_cut_lens_path`/`_cut_subtree`, `workspace_git._checkouts`,
   `_last_motion`'s dead params (and the caller's wasted extraction).
   Grep-verify zero callers before each deletion; keep anything a test
   exercises intentionally (then delete the test too if it only tests
   dead code).
9. **Ratchet.** A validate check (pattern of the existing duplication
   ceiling) that refuses any `scripts/*.py` module-level literal set
   equal to a generated enum's value set or the reserved-namespace
   mapping. Start with exactly the enums consolidated here; keep the
   check byte-cheap.

Acceptance: five checks green; `git diff --stat` dominated by deletions;
a behavior-freeze note in the return listing any site where consolidation
changed an observable string/exit (should be none).

---

### U6 — Regeneration owner + freshness gates

Motivation: derived artifacts drift (installed copies, serial manifest
6+ trailing commits, stale fixtures, mislabeled generated docs, CRLF
pins); each consumer was repaired one at a time. Findings 55–58, 1–4.

Write scope: `tools/regen.py` (new), `tools/validate.py` +
`tools/validate_support/`, `tools/run_serial_compat.py` (read),
`tools/render_shapes.py`/`render_lifecycle.py`/`render_hosts.py` (read),
`install.py` + `installer/` (doctor only), `tests/`.

Deliverables:

1. **`tools/regen.py`**: a declared manifest (in the file) of derived
   artifact → generator invocation, covering at minimum: generated T0
   shape sections (`render_shapes`), `docs/lifecycle.md`
   (`render_lifecycle`), host-block/host renders (`render_hosts`),
   `tests/serial_compat_manifest.json` (`run_serial_compat
   --write-manifest`). `regen` runs all generators;
   `regen --check` runs them against a temp copy and fails listing every
   artifact whose bytes would change. Deterministic, UTF-8, LF.
2. **Gate wiring.** `tools/validate.py` runs the equivalent of
   `regen --check` (direct import, not subprocess spawn per artifact if
   cost matters) so a stale derived artifact fails the existing five
   checks — no sixth check added to AGENTS.md.
3. **`install.py doctor --quick`**: fast freshness verdict — installed
   receipt's source commit + host-block hash vs. the invoking checkout —
   exits nonzero with a one-line "reinstall to update" on drift, no full
   doctor sweep. (Do not auto-install anything.)

Acceptance: five checks green; a test that dirties one derived artifact
and proves validate now fails; doctor --quick tested against a fake
receipt fixture.

---

### U9 — `orch-spec` → `orch-outline`; packs gain the outline lane

Motivation: user directive 2026-08-30. The intake skill is renamed
`orch-outline`, and packs become three tastes — executor taste (execute
cells), review taste (check cells), outline taste (new). This is the
spec's ONE sanctioned T0 supersession. Runs after U3 (wave 4) so later
law/doc waves use final names.

Write scope: `skills/workflows/orch-spec/` → `skills/workflows/orch-outline/`
(git mv), `contracts/work-item.md`, `contracts/pack-signature.md`,
`contracts/shapes.json`, `contracts/dispatch.md` (only if the verb
appears), `rules/delegation.md` (§8 verb sentence only),
`docs/vocabulary.md`, `templates/host-block.md`, `hosts/*.json` (if the
verb appears), `packs/*/SKILL.md` + `packs/*/references/`,
`scripts/tickets_registry.py`, `scripts/packs.py`,
`scripts/packs_support.py`, `scripts/tickets_dispatch*.py` (verb-name
touchpoints only), `installer/` (every name list/tuple), `install.py`,
`compositions/` (grep for the verb in stubs), `reader/docs/workflows.md`
+ reader projection name lists if they enumerate verbs, `tests/`,
`tools/render_shapes.py` output regeneration.

Deliverables:

1. **Verb rename.** `orch-spec` → `orch-outline` everywhere the verb is
   registered or routed: `CALLABLE_EXECUTORS`/registry, the seven-verb
   list in `contracts/work-item.md` (T0 supersession record), delegation
   §8's verb sentence, the skill directory (git mv, preserving
   references/), host-block template, vocabulary entries. The routing
   shape keyword `spec` becomes `outline` in host-block and
   vocabulary's routing-shape entry ("**outline** — a planner must first
   freeze that root..."). The NOUN "spec" (a run's frozen statement,
   per vocabulary) is NOT renamed — the outline skill still freezes a
   spec; keep `required_spec_fields` as-is for the same reason.
2. **Superseded-name refusal with remedy.** A dispatch naming
   `orch-spec` refuses with an error naming `orch-outline` (delegation
   §8's "no dispatch may revive a superseded skill binding" — make the
   refusal say the successor; U4.3's guard applies).
3. **Installer name lists.** Update EVERY installer catalog/tuple that
   enumerates skills by name (`installer/foundation.py`'s
   `CODEX_SKILL_REDIRECT_NAMES` class of lists, by-name index, Claude
   skill adapters, Codex prompts/redirects, Grok skills, role agents if
   they cite it). This exact class of omission previously cost 2h50m —
   add a test asserting every registered verb + pack + composition name
   appears in each host's generated catalog list, so the NEXT rename
   cannot miss one.
4. **Outline lane in the pack signature.** `contracts/pack-signature.md`
   gains an "## Outline cells" section and the flat shape gains one new
   required cell `outline` (a prose/reference leaf: the domain's taste
   for freezing a root — what a well-formed frozen root looks like in
   this domain, intake questions worth asking, exemplar policy).
   `required_spec_fields` and `craft` are listed in that section as the
   lane's other members (they stay single flat leaves; no nesting —
   match the existing execute/check pattern where `craft` appears in
   both lanes). Declare the new cell in `contracts/shapes.json`,
   regenerate the T0 table, append the supersession record.
5. **All four packs** gain real `outline` cell content (terse, domain-
   true, per the cell-earns-its-slot rule: content must differ between
   packs). Pack digests change; regenerate whatever pins/fixtures bind
   them.
6. **Resolver lane.** `packs.py cells <digest> --for outline` returns
   the outline lane (`outline`, `required_spec_fields`, `craft`)
   exactly as `--for execute`/`--for check` return theirs.
   `orch-outline`'s SKILL.md Require block resolves it at intake.
7. Tests: rename-aware (`test_seven_skills` and friends), the catalog-
   completeness test from item 3, resolver-lane tests, superseded-name
   refusal test. Regenerate the serial manifest if test topology moved.

Acceptance: five checks green; `git grep -n "orch-spec"` returns only
supersession records, historical notes, and the refusal mapping; the
review's finding-39 class (name missing from one host catalog) is now
mechanically impossible per the item-3 test.

---

### U7 — Law and routing text alignment (no new features)

Motivation: sequence semantics stated contradictorily in three files;
`topology.md 5a` cited but nonexistent; reader catalog lists the deleted
`fix` composition; vocabulary doesn't disambiguate `fix`; a role-grading
gap in sequence validation. Findings 2, 35–38, 50.

Write scope: `rules/roles.md`, `rules/delegation.md`,
`contracts/work-item.md` (prose only), `docs/vocabulary.md`,
`rules/topology.md` (or the citing files), `reader/docs/workflows.md`,
`skills/workflows/orch-outline/SKILL.md` (the 5a citation; U9 renamed
it — use post-rename paths throughout), `scripts/tickets_sequence.py`,
tests.

Deliverables:

1. `rules/roles.md` §4 becomes the sole owner of the sequence-role
   sentence: "a `sequence` — skill names or pack stages — runs in one
   child at the role resolved from the ticket's `executor`; a
   continuation's own `role:` has no dispatch effect." `delegation.md`
   §4 and `work-item.md`'s template section defer by link, keeping only
   their own concerns (execution order / field shape). Both forms stay
   legal (decided choice 5).
2. `tickets_sequence.py`: for a skill-name chain, refuse any entry that
   is not a registered callable or whose own declared role would require
   a fresh independent verdict per the law (concretely: keep the head==
   executor rule; add a structured finding when a continuation names a
   skill with `role:` differing from the head's resolved role — a
   warning-level finding is acceptable if refusal would break the
   shipped compositions; state which you chose and why).
3. Fix the `topology.md 5a` ghost: either restore the sub-item label or
   re-cite (vocabulary.md "domain" entry and orch-spec SKILL.md both
   cite it — make citation and target agree).
4. `docs/vocabulary.md`: one sentence under "routing shape" stating fix
   is a disambiguation between single and spec, not a fifth shape.
5. `reader/docs/workflows.md`: remove the `fix` catalog row.
6. Word budgets hold (token-economy ceilings); doclint green.

Acceptance: five checks green; validate near-duplicate count does not
rise (report the before/after number).

---

### U8 — Windows/IO hardening + final sweep

Motivation: cp1252 reporter crash, mojibake packets, BOM, redirect
corruption. Findings 25; session evidence across three runs.

Write scope: `scripts/` CLI entrypoints (`tickets.py`, `workspace.py`,
`packs.py`, `cutcheck.py`, `friction.py`, `isolate.py`, `state_root.py`,
`trace.py`), `tools/run_required.py` (verify the earlier fix landed;
repair if not), a new tiny shared helper if needed, tests.

Deliverables:

1. One helper (home: `tickets_format.py` or a new `scripts/_io.py` —
   pick the cycle-free option) that reconfigures stdout/stderr to UTF-8
   with `errors="replace"` on Windows; every CLI entrypoint calls it
   first. `BrokenPipeError` on stdout exits 0 silently (the head-pipe
   crash from the Aug 16 session).
2. Every command that produces a file for a consumer (packet projection
   especially) offers/uses direct file output (UTF-8, LF) — audit for
   any remaining "redirect me" instruction and replace with `--file`/
   `--out` guidance.
3. JSON reads of tool-produced files use `utf-8-sig`.
4. Sweep: `git grep` for leftover references to anything U1–U7 deleted
   or renamed (docs excluded — the docs wave owns those); fix stragglers
   in scripts/tools/tests only.

Acceptance: five checks green on Windows (this machine); a test that
pipes a tool's stdout into a closed pipe and asserts clean exit.

---

## Coordinator gate (per wave)

After each wave: `git diff` review → `uv run --no-project python
tools/run_required.py` → commit with a unit-scoped message. After W6:
full `uv run --no-project python -m unittest discover -s tests -v` once,
then `uv run --no-project python tools/preflight.py` if time allows.
Docs wave follows `research/docs-spec-2026-08-30.md`.

## Addenda from wave reports (binding on later units)

- **A1 (→ U5 scope):** `tests/test_tickets_cases/` has a severed intra-
  package import chain (three modules deleted in `2182d018`:
  `lifecycle_validation`, `lifecycle_claim`, `grant`) leaving ~19 case
  modules uncollected while the suite stays green — `TestCaseTreeReach`
  only proves the package is reached, not the chain. U5 repairs the
  chain or deletes genuinely-dead case modules (read before deciding),
  and strengthens the reachability test to assert every module inside a
  reached `*_cases/` package is imported by the chain.
- **A2 (→ U5 scope):** four more skip-lock-on-bad-id sites:
  `tickets_packet.py:166` (`_cmd_packet`), `tickets_dispatch_gate.py:93`
  and `:103`, `tickets_result.py:257` (`_cmd_run_state`, run-only — add
  a `locked_run_write(run)` sibling primitive). Convert all four to the
  U1 primitives; extend the U1 regression tests. `tickets_dispatch_gate.py`
  and `tickets_result.py` join U5's write scope for this item only.
- **A3 (all units):** `tickets_store.py` and `tickets_dispatch_packet.py`
  sit at exactly the 510-line ceiling; the next unit touching either
  must split per the family convention rather than trimming.
- **A4 (→ U4 note):** `_cmd_dispatch_join`'s terminal-identity write
  runs after `_commit_record` releases the lock (pre-existing). U4 puts
  it under the same lock while editing `tickets_lifecycle`/`tickets_join`
  adjacency, or reports why not.
- **A5 (→ U4 scope):** pre-existing inline-lane bug:
  `_inline_assignment_failure` compares the packet's NORMALIZED
  `isolation` against the sealed assignment's RAW `system.isolation`
  (`assignment_payload` stores it verbatim) — a ticket with no
  `isolation` field yields `None` vs `"none"` and `dispatch-receive`
  refuses a valid inline packet. Fix by normalizing BOTH sides at the
  comparison; never change what the seal hashes.
- **A6 (→ U5 scope):** two more duplicate-fact repoints:
  `state_root.candidate_paths` restates the one-segment rule
  `tickets_store._segment_error` owns (invert: predicate lives in
  `state_root`, `_segment_error` delegates — state_root is the
  dependency-free home); `tickets_grade.py:291` re-derives the revision
  `workspace_git.revision_of` now owns. Also A1 has a SECOND instance:
  `tests/test_workspace_cases/` — only `start_cases` +
  `candidate_cases` are wired; `cli_cases`, `contract_cases`,
  `emission_cases`, `grade_cases`, `operation_cases`, `prepare`,
  `sharing_cases` (~1900 lines) are uncollected and some no longer
  import (`workspace.WRITE_SCOPE_KEY` is gone). Same repair-or-delete
  ruling as A1, same reachability-test strengthening.
- **A7 (→ U3 scope, DONE except second half):** usage text fixed by U3.
  `install.py` is at the 510 ceiling (A3 applies). `tickets_dispatch.py`
  is at 509 — the next unit adding a subcommand line splits it
  (`_cmd_instantiate`/`_cmd_improvement` are the natural extractions).
- **A8 (→ U8 scope):** move `workspace_prepare.prepare()` out of the
  facade's locked span, per U3's analysis: `workspace_candidate` stops
  calling `prepare` (returns without the `**prepared` keys),
  `workspace.py` gains a lock-free `prepare <run> <id>` subcommand
  running against the recorded `workspace_path`, and
  `tickets_dispatch_facade._cmd_dispatch` calls it AFTER the
  `with _run_lock(run)` block. Files: `workspace_candidate.py`,
  `workspace.py`, `tickets_dispatch_facade.py` join U8's write scope
  for this item only.

- **A9 (→ U5 scope):** `tools/validate.py`'s `DOC_PATH_EXEMPT_SITES` is
  keyed by LINE NUMBER — any insertion above an exempt site in a
  contract silently breaks the exemption (bit U9). Re-key by
  path + content substring.
- **A10 (successor, NOT this branch):** the reader frontend still names
  `orch-spec` (`reader/web/src` fixture id + two capture routes in
  `reader/docs/view-manifest.json`); fixing it requires a `pnpm`
  rebuild of the committed dist, impossible offline here. Also
  `tools/live_routing_bench_support/grading.py` keeps route-class label
  `spec` because `benchmarks/routing/cases.json` (frozen, with recorded
  results) owns that vocabulary — rename with the benchmark or accept.
- **A11 (→ U7 scope):** `reader/tests/test_ui_cases/workflows_catalog.py`
  is red at HEAD — it still asserts the deleted `fix` composition.
  U7's fix-row removal extends to this test file.

- **A12 (→ U8 scope):** two reader test modules red at HEAD with stale
  expectations from the cutover:
  `reader/tests/test_ui_cases/workflows_compositions.py` and
  `…/workflows_sources.py` both expect `skill:orch-eval-design` for the
  `evolve` composition; the stub now binds `orch-outline`. Align them.
- **A13 (→ U5 scope, + `scripts/tickets_lint.py`):** wire
  `tickets_sequence.sequence_role_findings` into
  `tickets_lint.lint_findings` as a warning-severity finding (U7 left
  the public function ready; `_cmd_lint` already exits 0 on non-error
  findings).
- **A15 (→ U8 scope, replaces U5.7 which was rightly not shipped):**
  the temp-root predicate moves to `scripts/state_root.py`
  (`inside_temp_root`); `tools/verify_at.py` (joins U8's scope)
  repoints at it; `scripts/isolate.py` does NOT refuse — it WARNS in
  its JSON payload when the destination is temp-rooted and its
  docstring example stops recommending `/tmp/mine`. `tests/test_isolate.py`
  stays on temp roots by design.
- **A16 (→ U8 sweep):** `tickets_packet._cmd_packet` is unrouted dead
  plumbing (`test_command_surface` asserts it; imports exist, calls do
  not) — same class as the deleted claim route. Grep callers; delete
  the function + usage if truly dead, with its tests.
  `tools/validate_support/packages.py:273-304` still strips backticks
  inline (tools layer) — repoint at the public `dequote` if the import
  direction allows, else leave with a comment.
- **A14 (coordination note, all waves):** `validate.py --pin` is lawful
  once per committed baseline — a second `--pin` over an uncommitted
  re-pin finds no git ancestor and demands a supersession record for a
  prose edit. Recover with `git checkout HEAD -- tests/pins.json` then
  one re-pin. Also: `_t0_shape`'s enum sniffing treats any contract line
  matching `one of|enum|value(s)` as enum-bearing — phrase contract
  prose to avoid it.

## Out of scope (explicit)

- The errand lane (dead by design; user decision pending).
- Reinstalling into `~/.orchflows` (post-merge action).
- T0 shape changes outside U9's sanctioned supersession.
- The reader/web frontend.
- orch-decompose prose changes for measurement-commands (docs wave notes
  it; the mechanical half — refusing measured values in stubs — is a
  successor, not this spec).
