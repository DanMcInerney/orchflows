# Trunk defects — execution spec

2026-09-03. Executes the four trunk defects the library-cleanup run
(`20260903T155153Z-library-cleanup`, frame `B1`, branch tip `c6bc9d39`)
walked into. Each is a wedge or a collision the run paid for in hours, and
each is fixed by a deletion or a clause, never by a migration. Run as a
`team` frame from `research/trunk-defects-tickets/RUN.md`; every unit is a
code-pack `do` in its own worktree, landed on the run's branch, judged once
after the last wave, gate-green at the joined tip. Stop point: PR merged,
library reinstalled.

## 0. Decisions (closed)

1. **The seal reads the ticket, not a code roster.** D1's fix inverts
   `tickets_generations.ASSIGNMENT_SYSTEM_FIELDS`: `assignment_payload`'s
   `system` becomes every frontmatter field the ticket *carries* except the
   ones the trunk writes after sealing, and the inclusion tuple is deleted.
   A field that leaves the code while an open ticket still carries it then
   moves no digest, which is exactly the wedge. Rejected: refusing the
   reinstall while a frame is open — it narrows the window and fixes
   nothing, since a second host, a checkout's own `scripts/`, and the `git
   archive <base> scripts` recovery trunk all still recompute. Rejected:
   recording the sealed field set on each ticket — it adds a frontmatter
   field, a `contracts/shapes.json` row, and a fallback for every ticket
   minted before it, which is a migration.
2. **A retirement returns the status.** D2's fix widens
   `status_ownership_returned` from "a lone attempt that never launched" to
   "a lone attempt that never launched **or was retired**". Retiring ends
   the attempt, so no join can follow and nothing else can write the
   status. Rejected: teaching `land --status` to consume a retired attempt
   (the join consumes a *live* attempt and a committed outcome; the
   retirement already closed it). Rejected: `dispatch-retire --status`,
   a second status writer beside `set-status`.
3. **The remedy is named where the wall is hit, and nowhere else.** D2's
   discoverability half is two strings: `land`'s `outcome-record-mismatch`
   detail, and the generated lifecycle condition. No new paragraph in the
   host block, the frame law, `rules/delegation.md`, or a contract.
   `tests/test_staleness_and_remedies.py:315`
   (`test_every_named_command_is_routed`) already grades that a command a
   refusal names is routed, so the new wording arrives checked.
4. **Derived facts are deleted, not merged.** D3 deletes `count` and
   `sha256` from the manifest's `discovery` block rather than teaching git
   to merge them: `identities` is the fact, the other two are functions of
   it, and both are the single scalar lines two concurrent units always
   collide on. Regeneration also prunes a sentinel whose id is no longer a
   discovered identity — a test that no longer exists is not a judgment a
   reviewer has to make.
5. **The frame law owns the judgment cadence.** D4 states it in
   `tickets_frame.FRAME_LAW`, which `frame-open` prints to every driver,
   and in the close refusal that already carries the same remedy. No other
   file gains a sentence: `docs/custom-workflow-authoring.md:176` says a
   body that restates the frame law is a second owner of it.
6. **Subtraction over addition.** The only new production code in the run
   is decision 4's sentinel prune, which replaces a red a human had to
   diagnose by hand with bytes regeneration writes. Everything else is a
   deletion, an inverted predicate, or a string. New tests are unbounded: a
   walked defect with no check is why these four survived.
7. **Observations are reported, not fixed.** A unit that finds a defect
   outside its Details writes it into `## Report` and leaves it. Two are
   known already and are out of scope: `docs/vocabulary.md`'s **gate**
   entry cites `rules/verification.md` §7 for a sentence that reads like
   §6's, and `tools/run_serial_compat.py` is 519 physical lines against the
   500-line presumption (D3's deletions reduce it; nothing here splits it).

## 1. Frozen goal

At one joined tip on this branch, `uv run --no-project python
tools/run_required.py --no-cache` passes and:

- a ticket carrying a frontmatter field the trunk's own code does not name
  seals, and a dispatch write against that seal is admitted — proven by a
  check whose failing reading is recorded;
- a claimed ticket whose single attempt carries a `launch` record and has
  been retired takes `tickets.py set-status <terminal>` — proven by a check
  in `tests/test_staleness_and_remedies.py` — and the refusal a driver hits
  before retiring names `dispatch-retire`;
- `tests/serial_compat_manifest.json`'s `discovery` object holds exactly
  one key, `identities`, and `tools/run_serial_compat.py --write-manifest`
  drops a sentinel whose id no longer discovers;
- `scripts/tickets_frame.py`'s `FRAME_LAW` states the judgment cadence,
  `grep -rn "joined tip" templates/ rules/ contracts/ docs/ skills/ packs/
  sheets/` names no second owner of it, and `frame-open`'s payload carries
  the law it prints;
- `uv run --no-project python install.py --dry-run` plans the same entry
  count as at `c6bc9d39`, recorded in the frame journal.

## 2. Fixed names and shapes

- `scripts/tickets_generations.py`: `ASSIGNMENT_SYSTEM_FIELDS` is deleted
  and replaced by

      UNSEALED_FIELDS = (
          "admission", "assignment_seal", "cut_generation", "dispatch_v1",
          "root_generation", "status", "workspace_baseline",
          "workspace_branch",
      )

  `assignment_payload`'s `system` is every frontmatter key the ticket
  carries that is in neither `UNSEALED_FIELDS` nor `("depends_on",
  "executor", "id")` — those three ride the payload already as
  `dependencies`, `executor` and `ticket`. The eight are the fields the
  trunk writes after `assignment_seal` is set; re-derive with `grep -rn -A2
  "_set_frontmatter_field(" scripts/*.py` and `grep -n
  "BRANCH_KEY\|BASELINE_KEY" scripts/workspace_git.py` before trusting the
  list.
- `scripts/tickets_dispatch_schema.py` `status_ownership_returned`: one
  attempt, not `live`, and either `state == "retired"` or every record
  `kind: lifecycle`.
- `scripts/tickets_transitions.py:99` condition string: `no dispatch-v1
  record, or a lone attempt that never launched or was retired`.
- `tools/serial_manifest.py` `discovery()` returns `{"identities": [...]}`.
  `tools/run_serial_compat.py` `load_manifest` validates that `identities`
  is a non-empty list of non-empty strings equal to
  `sorted(set(identities))`, and asserts nothing about `count` or `sha256`.
  `write_manifest`'s report prints `len(identities)`, computed at print
  time.
- `scripts/tickets_frame.py` `FRAME_LAW` gains a fourth sentence, and its
  comment says four:

      "Judge once, at the end: a unit lands on its own `done`, and after "
      "the last wave one judging child reads the joined tip with every "
      "unit's artifact together; its blocking findings get one bounded "
      "repair, then the close gate."

- Interpreter, in every `done` and every command here: `uv run
  --no-project python`.

## 3. Units

### U1 — The seal reads the ticket (D1)

`scripts/tickets_generations.py` and the checks that read it. Delete
`ASSIGNMENT_SYSTEM_FIELDS` and its comment; add `UNSEALED_FIELDS` per
section 2, with a comment saying why the partition is stated as the
complement — a field deleted from the trunk while an open ticket still
carries it must not move that ticket's digest.
`tests/test_ticket_done_predicate.py:79` asserts `"done" in
ASSIGNMENT_SYSTEM_FIELDS`; rewrite it to assert the behaviour (changing
`done` moves the digest) rather than the roster. `tests/test_tickets.py:424`
reads `assignment_payload("T1", text)["system"]` and `:428` compares two
digests; reconcile both. `tests/test_ticket_protocol.py:19-32` is the
digest's behavioural contract and should stay green unchanged — if it does
not, that is the finding. New check, in
`tests/test_staleness_and_remedies.py` beside the other wedges: a ticket
carrying a frontmatter field no trunk constant names seals and admits its
dispatch writes, and dropping that field moves the digest; the can-fail
reading is that under the deleted roster the two digests were equal. One
literal seal exists under `tests/` — find it with `grep -rn
"assignment_seal: sha256" tests/` and recompute it rather than deleting the
case. This change invalidates every seal open when it lands: it must not be
installed while a frame is open, and the run that lands it reinstalls only
after `frame-close`. Say so in `## Report`.

### U2 — A retirement can be graded (D2)

`scripts/tickets_dispatch_schema.py:297` `status_ownership_returned` widens
per section 2. `scripts/tickets_lifecycle.py:218-221`'s comment names the
"lone attempt opened and retired before any launch" exception; rewrite it
to the wider one — a retired attempt has no join coming, whatever it
launched. `scripts/tickets_transitions.py:99`'s condition string changes
and `docs/lifecycle.md` is regenerated (`uv run --no-project python
tools/regen.py`); the row count must not change.
`scripts/tickets_join.py:115-118`'s `outcome-record-mismatch` detail names
the remedy: a child that will never commit an outcome is retired with
`dispatch-retire` and then graded with `set-status`. Leave `:122`'s sibling
detail alone — that is a different mismatch. New check in
`tests/test_staleness_and_remedies.py`: open a dispatch, commit a `launch`
record, retire the attempt, then `set-status stalled` succeeds; its
can-fail reading is the `dispatch-join-required` refusal before the
widening. Confirm `test_every_named_command_is_routed` (`:315`) grades the
new refusal wording; if its scan does not reach `tickets_join.py`, say so
rather than widening the scan.

### U3 — The manifest stops colliding (D3)

`tools/serial_manifest.py:52` `discovery()` loses `count` and `sha256`;
`_identity` and `write_manifest`'s printed report derive the count from
`len(identities)`. `tools/run_serial_compat.py` `load_manifest` (`:53`)
loses the two derived comparisons and keeps the sorted-unique check. The
module docstring's "The discovery block (count, identities, sha256)"
sentence changes with it. Regenerate `tests/serial_compat_manifest.json`
with `uv run --no-project python tools/run_serial_compat.py
--write-manifest`. At `c6bc9d39` that file holds 2125 identities, 12
sentinels and 373 mutation owners, with no stale sentinel and no
`unclassified` owner, so both remaining defects are reproduced, not found:
(a) add a sentinel row naming an id that does not discover and show
regeneration prunes it — today `plan_regeneration` raises `regeneration
would rewrite the sentinel roster`, so narrow that guard to refuse anything
but the removal of a vanished id, and keep `load_manifest`'s
`REQUIRED_CATEGORIES` red if a prune empties a category; (b) the reported
reset of a ruled owner's `restoration` to `unclassified` does not reproduce
from the tree at this commit, since `merge_owners` carries `restoration` by
`(module, owner)` — check it against `git log -p
tests/serial_compat_manifest.json` across the run's window, fix it if that
key is unstable, and report the reading either way. Tests:
`tests/test_serial_manifest.py`, `tests/test_serial_compat.py`,
`tests/test_serial_compat_hardening.py`,
`tests/test_serial_compat_manifest_regression.py` — a case asserting the
`count`/`sha256` contract is deleted, not weakened. `tools/regen.py:188-214`
declares the manifest's generator; `--check` reports no drift after.

### U4 — The judgment cadence is law (D4)

`scripts/tickets_frame.py:94` `FRAME_LAW` gains section 2's fourth
sentence and its comment says four; `_judgement_refusal` (`:308`) names the
joined tip in the same words it already uses for the remedy. Nothing else
gains a sentence. Before writing, run `grep -rn "judge\|judgment" rules/
templates/host-block.md docs/custom-workflow-authoring.md` and report which
existing sentences the new law contradicts: the host block's team lane
already says "end at `frame-close`, judging the seams", and
`rules/verification.md` §7 already sends an adversarial review through an
ordinary `judge` ticket — neither contradicts, so neither changes; where
one does, delete the loser and name it. `tests/test_ticket_frames.py:654`
asserts the printed law equals `FRAME_LAW`; add a case pinning the count
(four) rather than the prose, and check `:703`'s `FRAME_LAW[1]` still
indexes the sentence it means. The cadence is stated law, not an enforced
one — the trunk cannot see waves — so `## Report` carries the `grep -rn
"joined tip"` output over `templates/ rules/ contracts/ docs/ skills/
packs/ sheets/` as the one-owner evidence.

## 4. Waves

| wave | units | waits on |
|---|---|---|
| 1 | U3 | base |
| 2 | U1, U2, U4 | U3 |
| 3 | judge, then bounded repair | wave 2 |
| 4 | gate | wave 3 |

Every unit adds a check, and every added check regenerates
`tests/serial_compat_manifest.json` — D3's own lesson. So U3 lands first
and alone, deleting the two scalar lines that always collide; wave 2's
three children then collide only where their new identities sort adjacent
inside `identities`. Wave 2 lands in the fixed order U1, U2, U4, and the
manifest is the wave's one shared derived artifact: where a land conflicts
on it, the driver — not a child — resolves it by regenerating at the merged
tip (`packs/orch-code-pack/references/craft.md`, `## Workspace`). No two
units share another file: U1 owns `tickets_generations.py`; U2 owns
`tickets_dispatch_schema.py`, `tickets_lifecycle.py`,
`tickets_transitions.py`, `tickets_join.py` and `docs/lifecycle.md`; U4
owns `tickets_frame.py`. U1 and U2 both append to
`tests/test_staleness_and_remedies.py`, in different classes; U1 lands
first and U2 rebases onto it.

## 5. Gate

At the joined tip, once, outside every child:

    uv run --no-project python tools/run_required.py --no-cache
    uv run --no-project python tools/regen.py --check
    git diff --check

Then, into the frame journal: the `install.py --dry-run` entry count beside
`c6bc9d39`'s, and U4's `grep -rn "joined tip"` roster. One code-pack
`judge`, after wave 2 and over the joined tip, carrying all four
`artifact:` lines in `--artifacts` and
`research/trunk-defects-tickets/judge.goal.md` as its Goal — the cadence U4
makes law, run by the spec that writes it. Its Details is
`judge.details.md`, a pointer file: this spec's own `##` headings are off
the ticket section contract, so passing it as `--details-file` refuses with
`unknown ticket section`. Where the judge blocks, one repair `do` handed
the `findings:` line verbatim, then one re-judge; two rounds is the bound.
Then reinstall (`install.py`, `orchflows sync`) — never before
`frame-close`, because U1 changes the seal algebra and a reinstall
mid-frame is the defect it fixes.

## 6. Deferred

- A resealing subcommand. U1 removes the field-roster cause; a change to
  the payload's *structure* would still wedge an open frame, and the
  recovery stays what the run used — `git archive <base> scripts` into a
  temporary directory, running that `tickets.py`. Nothing in the library
  says so, deliberately: a recovery paragraph for a case one commit a month
  reaches is prose every reader pays for.
- Enforcing the cadence. The trunk cannot see waves, so U4 states the law
  and nothing refuses a mid-run judge.
- `tools/run_serial_compat.py`'s 519 lines, and the vocabulary **gate**
  entry's §7 citation (decision 7).
