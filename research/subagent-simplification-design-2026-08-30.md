# Subagent + packet/ticket simplification — design

2026-08-30. Status: **PROPOSED — awaiting review. Nothing here is implemented.**

Synthesis over seven parallel investigations (A performance audit, B
pre-refactor baseline, C envelope/packet drift, D external-tool survey,
E reviewer context, F final-verify redundancy, G mechanization sweep).
Primary evidence: the three dogfood runs of 2026-08-30 in
`~/.orchflows/state/tickets/` (`20260830T231500Z-u6-proof`,
`20260830T234500Z-workspace-derivation`, `20260831T001500Z-friction-fixes`),
the friction ledger `~/.orchflows/state/friction/2026-08.jsonl` lines
7243–7255, the session transcript
(`~/.claude/projects/...-1a96c3/6073e83d-....jsonl`), git history back to
`7b1ba5d1` (pre-PR-#116), and source reads of twelve external
orchestrators.

---

## Part 1 — The four answers

### 1. Was the pre-refactor path viable? Mostly yes — and it was already fixed.

Of the ten concretely documented problems of the pre-#116 `claim`/`packet`
path, **eight were fixed by small patches to that path before dispatch-v1
existed** (~1,500 lines across PRs #82/#87/#88/#89 and the
project-binding work: packet completeness, transition tables, ceiling
breakdowns, `--append` in the emitted template, documented-path
validation, the installer's `FORK_ARRIVAL_CLAUSE`, `## Carry`,
`tickets_bound.py`). **Exactly two problems genuinely required a
protocol**:

- **Stale-claim displacement of a live child** — `_is_stale` computed
  staleness from `max(claimed_at, mtime)` with a 60-minute default; a
  quiet healthy child could be displaced and then refused its own
  `result --by` on writer mismatch. Silent evidence loss, no atomic
  recovery.
- **Non-idempotent return** — `result --append` had no idempotency key; a
  retried write duplicated content and the join guessed which streamed
  write closed the attempt.

Both are covered by a **strict subset** of dispatch-v1: a durable
per-attempt identity, an absolute non-extending lease, a
`(dispatch_id, record_id)` idempotency key, and one reserved closing
identity. The receipt/authority half (`dispatch-receive`, the
`authority-mismatch`/`identity-mismatch`/`profile-mismatch`/
`assignment-divergent`/`receipt-required` family, inline envelope seals)
polices the packet-less-fork class — which PR #89 closed structurally at
the installer, at the one point in a fork's load path a packet can never
reach ("a packet-less fork never reads a packet").

The cost side: the two protocol waves added **+8,178 lines** to the
`tickets_*`/`workspace_*` family (6,215 → 14,393), refusal codes 0 → ~28,
T0 shapes 0 → 40 — and PR #116's entire recorded rationale is seventeen
one-line commit messages with empty bodies. Of the eight fixes merged on
dogfooding day (#140/#141), six were defects **in the machinery the
waves added**, including a shared-tree establishment regression
(`55d12fc4`) that is exactly the failure `DESIGN.md` says U2 was built
to make impossible, reintroduced 24 hours later by the ticket diet. The
mechanical trunk's two largest measured wins — launch emission and
workspace ownership, 341 friction entries — are orthogonal to the
protocol and port to any path.

### 2. How much envelope drift? Severe, and now counted.

Of the packet's **21 fields** (built in
`scripts/tickets_dispatch_packet.py:101-172`):

- `admission` — **dead everywhere**: zero readers across `scripts/`,
  `tools/`, `tests/`.
- `independence`, `isolation` — dead outside an inline self-comparison
  (`scripts/tickets_dispatch_inline.py:61-70`).
- `reply_to` — **dead as routing**: validated
  (`tickets_dispatch_packet_shape.py:81-88`), carried in six homes,
  resolved by nothing; `hosts/claude.json` declares no return channel.
  10 of 10 returning children burned 15–40 s on the fallback.
- `reference` — a forced copy of `source` (`packet_shape:69` refuses
  unless they are equal).
- `outcome_record_id` — a constant restated on the wire so it can be
  checked against itself (`packet_shape:79`).

The generated `prompt` then re-renders eight of the surviving fields as
English (lines L08/L09/L14 restate run, id, seal, dispatch_id,
assigned_name, outcome identity). The **median fact has 4 homes**;
`reply_to` and `assigned_name` have 6. Every committed record is stored
**twice** inside its own ticket (escaped `content` +
`success.committed_record.content`): `R1.gate.verify.md` is 275,716
bytes, 73% `dispatch_v1`, and embeds its 54,682-byte `review_v1` ledger
a second time inside the prompt.

The structural inversion that explains the hand-written launches: **the
two facts a child cannot obtain any other way — where the packet file is,
and that it must stand in the workspace before accepting — are the two
the machinery does not carry.** `--packet-file` exists in
`scripts/tickets_commands.py:52` and in zero markdown files; the
stand-in-workspace precondition of `tickets_dispatch_receipt.py:77-101`
is stated nowhere. That is why 12 of 12 launches were hand-composed
against `rules/delegation.md:19-21` ("improvises neither"). All nine
dogfood bug traces (C §5) reduce to one shape: **a fact with either more
than one owner or none.**

### 3. Do reviewers see the root ticket? Only by their own initiative.

The gate stub body carries the root **ID only** ("root ticket: R1",
`scripts/tickets_dispatch_gate.py:49-69`); the review prompt branches
name no ticket path (`scripts/tickets_packet.py:205-219`) and
`_dependency_prompt` is unreachable from them. Three of the four
root-aware reviewers dereferenced `R1.md` unprompted, and in three
proven cases the verdict **materially depended** on root clauses that
exist nowhere else: F2's blocker is warranted only by the root's
"extinguished" clause; F4 overrode three wrong authorities via the
root's can-fail-check clause (`R1.md:30-32` only); the verify FAIL is
bound to the root's "gate is green at the tip" clause. The fourth
(gate-repairer) judged the root Goal only through the critique's
paraphrase. Verdict-load-bearing context currently reaches reviewers by
agent initiative, not by design.

### 4. Is the final verify redundant? Split verdict, clean rule.

Where the root Goal reduces to a deterministic gate: **yes**. The verify
child spent 16m18s and 14.1M tokens; the oracle inside it was 5m08s and
one turn, and its stdout carried the defect, its location, and the
**verbatim two-line remedy** that shipped (`9a0a0e15`). Where the Goal
has clauses no oracle speaks to: **no**. The same child's non-redundant
~11 minutes (provenance across six commits, the `affected_tests.py`
structural blindness that made every scoped lane blind, the
unguarded-vs-untrue separation) came from exactly those clauses — and
the zero-oracle `N1.check`, judging a three-line markdown note, had the
**highest yield of all three runs** (its F2/F3 became the whole W1 run
and ticket R1.05).

Two aggravating facts: the run had **no lawful round-two slot**
(friction `23:34:47Z`: "the composite gate has no round-two
materializer"), so the remedy was applied by hand outside the protocol;
and the tree that shipped to main **never had a full local gate run**.

The extracted rule: **deterministic oracles run as host predicates; LLM
review is dispatched only against the Goal-fraction no oracle covers.**

---

## Part 2 — The design

### Principles (each one bought with evidence)

1. **One owner per fact.** All nine bug traces reduce to 0 or >1 owners
   (C §5).
2. **Done is a checked condition, not a recorded claim.** F's verdict;
   the survey's only universal among the serious systems (Fletch,
   NEEDLE, bernstein — the three that don't let an LLM judge
   completion).
3. **The child receives exactly what it cannot derive, and nothing it
   can.** C's inversion: today it receives everything else and not the
   two facts it needs.
4. **Machinery the orchestrator does not use does not exist.**
   `--packet-file`: 0 uses vs 11 hand re-implementations; `bound-check`:
   0 uses vs 9 bespoke parsers; `launch_prompt()`: 0 of 12 (G).
5. **The field's floor is five lines** — worktree, cd, prompt,
   human-read diff, merge. Not one shipped tool passes a structured task
   file to a child (D). We keep only what the two theorems and the done
   predicate require above that floor.

### What gets DELETED

**D1. The receipt handshake.** `dispatch-receive`, the receipt record,
`scripts/tickets_dispatch_receipt.py`,
`scripts/tickets_dispatch_inline.py`, and the authority refusal family
(`receipt-required`, `authority-mismatch`, `identity-mismatch`,
`profile-mismatch`, `assignment-divergent`, `packet-invalid`).
*Grounds:* it polices a class closed at the installer (B); it cost the
accept phase 29 s–6 m 16 s per child (A: N1's 6m16s accept was entirely
refusal-retry; W1 and R1.01 both hit `authority-mismatch` on cwd); it
stores 50–59 KB of duplicated handshake per gate ticket (C). The child's
**first filed record is its acceptance** — identity is proven the same
way every later write proves it: by carrying `(dispatch_id, seal, --by)`
which `tickets_result` already validates. Deleting receive also
dissolves the cwd-sensitivity bug class structurally: there is no accept
step to run from the wrong directory.

**D2. The packet as a wire object.** The 21-field `dispatch_packet`
shape dies. The **ticket is the assignment**; the **launch prompt is the
delivery**. Field disposition:

| field | disposition |
|---|---|
| `admission` | delete (dead) |
| `independence` | delete from wire (ticket owns) |
| `isolation` | delete from wire (derived; `tickets_adapters` owns) |
| `reference` | delete (== `source`) |
| `outcome_record_id` | delete (constant) |
| `executor`, `pack`, `review_kind`, `assignment_seal` | delete from wire (ticket owns; seal still cited on writes) |
| `reply_to` | **delete outright** (D7) |
| `role`, `profile` | live in the launch object only (they select the agent; the child never needs them) |
| `lease_expires_at` | attempt owns; the prompt states the deadline in one sentence |
| `source`, `workspace`, `dispatch_id`, `assigned_name`, `prompt` | survive as inputs to the generated launch prompt — there is no separate wire |

`dispatch` emits **one launch object** `{agent, model, effort, prompt}`
and nothing else.

**D3. Hand-written launch prompts.** The generated prompt
(`scripts/tickets_dispatch_launch.py::launch_prompt`) becomes the only
child-facing instruction surface, and it absorbs the orphan facts that
forced hand-writing (C §3b): the ticket's absolute path inside the
established workspace; "run every command from this workspace"; the
verified interpreter path; the filled filing-command template; the
assigned name and lease deadline; **the resolved craft path** (dispatch
already resolves the pack to establish the workspace — emitting the
craft path kills both the `packs.py resolve`-vs-`cells` third-spelling
drift and the packet-less `Skill`-fork class, 4 firings); **the root
ticket path for review lanes** (E's fix); the craft's own
verification-scope sentence ("narrow affected checks; the full suite is
the gate's row" — the absence of which caused the five-way gate
saturation, 56 killed process-minutes, ≥15 timeout-parks, 10 nudges);
and the host block's standing laws (foreground-only, commit trailer).
The prompt already names the skill in prose (C: L01) — that line
survives; the duplication lines L02–L04 and L08–L14 die with the wire.

**D4. Double storage of records.** Store each committed record once.
This alone removes ~73–75% of gate-ticket bytes
(`R1.gate.verify.md` 275,716 → ~72 KB).

**D5. The review ledger's second embedding.** Review prompts pass the
ledger **by path** (the ticket owns `review_v1`); the 54,682-byte
verbatim embedding dies.

**D6. The standing LLM verify lane — replaced by a done predicate at
land.** Generalize U2's loop grammar to every ticket: an optional

```json
"done": {"form": "command" | "check", "value": ...}
```

- `form: command` — `tickets.py land` runs it in the integrated tree;
  exit 0 is the verdict. This **is** the one outside execution
  (consistent with the existing law: the checker's re-run is THE outside
  execution; close is a recording act).
- `form: check` — land mints an `orch-check` ticket scoped to the
  clauses no oracle covers (the `N1.check` case — where LLM review had
  its highest measured yield).

The composite gate becomes **critique → repair → land-runs-the-predicate**
(plus an optional check ticket for un-oracled Goal clauses). Three bug
classes dissolve at once: the verdict-token collision (no prose
`PASS:`/`FAIL:` parsing — delete `tickets_review.py:476-480` and the
envelope-reading at `tickets_join.py:292-293`; a command verdict is an
exit code, a check verdict is the check ticket's structured findings);
the **no-round-two-materializer** wedge (a failing predicate re-arms a
repair iteration through the existing `loop-advance` machinery — bound
and stall exits included, for free); and the
**shipped-tree-never-gated** hole (land will not set `complete` on a
tree whose predicate did not pass *in land's own process*).

**D7. `reply_to`, entirely.** Field, validation, prompt line, flag. The
return channel is the ticket's records plus the harness notification;
there is no in-band routing fact. (Ten of ten children proved the
current one is theater.)

**D8. The child's claimed status.** The outcome record survives as the
**protocol's closing identity only** — a delta-only closing note whose
existence closes the attempt. Ticket status is computed at land from
the predicate (D6). "Done because the agent says so" dies (D principle
2). The `outcome-invalid` collision guards shrink accordingly.

**D9. The inline packet form.** Delete (no-fallback law). Its only
consumers were the self-comparisons that made `independence`/`isolation`
look alive; the one host in `hosts/` supports files.

**D10. Refusal-code diet.** ~28 → ~10. Survivors are the protocol
core's (`stale-attempt`, `live-attempt`, the three remedied
`idempotency-conflict` variants, `claim-without-dispatch`,
`dispatch-mismatch`, lease/staleness) — each already naming its remedy
per the staleness-remedies idiom. The authority family, `packet-invalid`,
`receipt-required`, and `review-invalid`'s token rule ride out with
their machinery.

### What remains — the single owner of each fact

| fact | sole owner |
|---|---|
| assignment (Goal, Context, deps, bound) | the sealed ticket file |
| attempt identity, owner, lease | `dispatch_v1` attempt (shrunk to `dispatch_id`, `owner`, `opened_at`, `lease_expires_at`, `state`) |
| workspace path | the attempt record (the `workspace_path` frontmatter field dies — today it is a second home) |
| idempotent return | `tickets.py result`, keyed `(dispatch_id, record_id)`; reserved closing id `outcome` |
| done | the ticket's `done` predicate; **evaluated only by land** |
| isolation | derived — `tickets_adapters.derived_isolation` (explicit override stays rare) |
| launch (agent/model/effort/prompt) | `tickets_dispatch_launch.py` reading `hosts/*.json` |
| child-facing instructions | the generated launch prompt — the only prompt |
| root Goal for reviewers | the root ticket path, named in the review launch prompt |
| verification scope | the pack craft; the prompt quotes its one sentence |
| lease law (absolute, non-extending) | `contracts/dispatch.md` — unchanged |

**The flow** (three public verbs, two locks):

1. `tickets.py dispatch <run> <id> --by ... --host <h>` — one lock:
   readiness → mint attempt → `workspace.py establish` → emit the launch
   object. The orchestrator invokes it verbatim. Nothing is
   hand-transcribed.
2. The child works in the workspace, files idempotent records through
   `result`, and closes with the delta-only `outcome` note.
3. `tickets.py land <run> <id>` — one lock: import outcome (closes the
   attempt) → run the `done` predicate / mint the check ticket →
   **integrate the candidate branch** (G inverse case I — today land
   leaves the branch for hand git, which produced the silent empty-seal
   no-op) → join → retire worktree → frontier report.

This lands within sight of the field's floor (worktree + generated
prompt + host-checked done + a merge) while keeping exactly what the
floor lacks and the record shows we need: idempotent return, an absolute
lease, and a machine-evaluated done.

### Migration sketch (three stages, each independently gate-green)

**Stage A — deletion.** Delete
`tickets_dispatch_receipt.py`, `tickets_dispatch_inline.py`, the
receipt/inline verbs and refusal family; delete `admission`,
`independence`/`isolation`/`reference`/`outcome_record_id`/`reply_to`
from the wire and `workspace_path` from frontmatter; single-store
committed records; pass the review ledger by path. Regenerate
`contracts/shapes.json` (40 shapes shrink hard — the 23 `dispatch_*`
entries collapse to attempt + record + launch), T0 supersession records,
`--pin`. Dead-code sweep C found in passing: `PACKET_USAGE`
(`tickets_packet.py:47`), the four unread keys `_packet_under_run_lock`
returns (`tickets_packet.py:265-273`).

**Stage B — the launch prompt.** Move the orphan facts (D3) into
`launch_prompt`; delete the packet prompt's duplication lines; delete
`--packet-file` (there is no packet file — the ticket path is the
pointer). `templates/host-block.md`'s graph route shrinks to:
dispatch → invoke launch verbatim → land.

**Stage C — done at land.** Promote the loop `done` grammar to all
tickets (`tickets_format.parse_loop` generalizes); land evaluates;
delete the verdict-token law and the standing verify lane; wire the
failing-predicate path through `loop-advance` re-arm. The gate family
shape in `tickets_dispatch_gate.py` drops verify; review stubs gain the
root path. Note the U3 interplay: land computing status this way absorbs
most of `orch-integrate`'s grading role — Stage C is the natural moment
to take U3's evidence to the user.

**Size estimate** (measured bases: family 53 modules / 14,393 lines;
2,529 lines of dispatch-protocol tests; receipt+inline+packet-shape
+prompt-assembly ≈ 1,300 lines of scripts): roughly **−4,500 to −6,000
lines** including tests, refusals 28 → ~10, packet fields 21 → 0 (one
4-field launch object), gate-ticket bytes −70%+. Target: the family back
under ~9,000 lines while keeping both theorems.

### External steals — adopted, deferred, rejected

- **Adopted:** done-as-checked-condition (Fletch/NEEDLE) — is D6.
  Root-path in review prompts (analog of bernstein's context-bearing
  decomposition) — is D3.
- **Deferred, worth a line:** firstmate's one-line append-only status
  file + zero-token watcher ("unknown never decays into idle") — the
  cheap liveness answer to the parking class if it survives D3;
  treehouse's pooled detached-HEAD worktrees — only if establish cost
  ever shows up in the friction ledger (it has not); bernstein's
  owned-paths field — the only real answer to hotspot collisions (our 3
  manifest merge conflicts were exactly this class), but `Suggested
  files` already exists non-binding; revisit with evidence.
- **Rejected:** git-notes state (container-use) — the sink works and is
  queryable; OSC 133;A PTY watching — our children are harness
  subagents, not PTYs; SQLite boards — vibe-kanban's 81 migrations
  against a 2 KB task model is the cautionary ratio.

---

## Part 3 — Ranked mechanical captures

Ranked by (bugs eliminated × frequency) / effort. "Absorbed" = becomes
unnecessary because the design deletes the machinery it patches.

| # | capture | bugs × frequency | effort | fate under the design |
|---|---|---|---|---|
| 1 | **Generated launch prompt invoked verbatim** (dispatch prints it; orchestrator pastes nothing) | the dominant defect source: clause drift across 12/12 hand prompts → 3 frictions + all 10 nudges + 4 Skill-forks + 10 reply-fallbacks + the silent empty-seal land | small — the seam exists (`launch_prompt`), it lacks eight facts | **Absorbed (is D3)** |
| 2 | **Done predicate at land** | verdict-token wedge, no-round-two wedge, unverified-shipped-tree, the 14.1M-token verify wrapper — every gated run | medium — the loop grammar and `loop-advance` exist | **Absorbed (is D6)** |
| 3 | **`friction.py` auto-stamps `--run`** (from cwd/state or env) | 13 of 13 entries unqueryable by run — blocks every future mining pass | trivial | **Survives** — do regardless |
| 4 | **land integrates the candidate branch** | hand git after every member join; the class that produced the silent no-op land | small | **Absorbed (in D6's land)** |
| 5 | **Craft's verification-scope sentence in the prompt** | 5-way gate saturation: 56 killed process-minutes, ≥15 timeout-parks, 3 parked workers, contention that doubled scoped-run cost | trivial once #1 lands | **Absorbed (is D3)** |
| 6 | **Single-store committed records** | −70% ticket bytes; every read of a gate ticket | small | **Absorbed (is D4)** |
| 7 | **Canonical-JSON producer named in the refusal** (or an `outcome --template`) | friction `22:44:33Z`, still open | trivial | **Mostly obsoleted** — D8 shrinks the outcome to a note filed like any record |
| 8 | **Zero-token parking watcher** (firstmate steal: status line + non-model watcher) | residual parking after #1/#5 remove the cause | medium | **Survives as optional** — only if parking recurs post-design |
| 9 | **`bound-check` in the driver loop** (replace the 9 bespoke regex parsers) | orchestrator-side only; no child bugs | trivial | **Obsoleted** if #8 lands; else a one-line habit |

Items 3 is worth doing today regardless of the design's fate; items 1–2
ARE the design; everything else rides along or waits for evidence.

## Open questions for review

1. **U3 coupling** — Stage C absorbs most of `orch-integrate`'s grading
   into land. Fold U3 (retire `orch-frontier` + `orch-integrate`) into
   Stage C, or keep them separate PR trains?
2. **Bearer-token trust** — with receive gone, possession of
   `(dispatch_id, seal)` is authority, same strength as today minus the
   ceremony (the receipt only ever echoed packet values back). Accept,
   or keep one lightweight first-write assertion?
3. **Owned-paths field** — adopt bernstein's binding hotspot ownership
   now (evidence: 3 manifest conflicts), or wait for a second
   occurrence?
