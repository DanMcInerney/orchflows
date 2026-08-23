# Orchflows speed specification

Identity: 2026-08-23 implementation specification. Supersedes the
measurement and sequencing sections of
`research/orchflows-phased-simplification-spec-2026-08-22.md`; keeps its
invariants and its Proposals 1, 2 and 4 in modified form. Evidence is the
state sink for 2026-08-15 → 2026-08-23, summarised in the review "Where the
Hours Went" (session artifact, 2026-08-23) and reproducible from the sink
with `tools/run_report.py` once item 0 lands.

Status: proposed. Changes no authority semantics: the caller still owns the
semantic root, executors still write only their own sections, verification
§10 still names the independence paths, terminal status is still set only by
the join. Every item below removes machine-checkable waste from around those
rules or makes an existing rule mechanical.

## 1. Goal and metric

Goal: small tasks finish in minutes, not hours; long runs do not derail; a
script stands in for model judgment wherever the judgment is mechanical.

Primary metric: **wall-clock per objective** — first run opened for an
objective → accepted result (merged PR or accepted root result). Secondary:
**physical runs per objective** (a run family is the name stem after
stripping the timestamp and any `-v2|-v3|-retry|-restart|-corrected|-direct|
-final|-cut-ready|-edge-ready|-runnable|-replacement` suffix) and **oracle
minutes per objective** (summed wall of `run_tests.py`, `run_serial_compat.py`,
`pnpm test|build|lint|typecheck`, `playwright` invocations recorded in ticket
or run text). Baseline is the fixed window 2026-08-15T00:00Z → 2026-08-23T00:00Z
as recorded in the sink today; no prospective instrument-only days.

What the baseline shows (from the review): 159 timestamp-named runs; 36 never
claimed a non-decompose ticket; 24 terminal blocked/failed runs = 12.5 h; 646
full-suite mentions; a one-line `package.json` pin took 5 h 01 m under a
"≤ 30 tool calls" bound; `remove-project-install` took 7 runs / 1 h 33 m for
34 m of work; `now-page-improvements` took 11 repair runs / 6 h 32 m before the
first product unit; the 8 h `final-spec-implementation` ignored every bound
(100 m → 2 h 47 m) and spent 69 m on 34 gate repairs after acceptance.

## 2. What is already law (do not restate; make mechanical)

- "Regression — the full suite the spec names — the gate's row, never a
  unit's" (`packs/orch-code-pack/references/oracles.md:6`). The frontier:
  "A lane runs its ticket's own oracles, nothing wider"
  (`skills/engines/orch-frontier/SKILL.md:38`). cutcheck convicts
  `whole-suite-oracle` (`scripts/cutcheck_contract.py:57`,
  `scripts/cutcheck_search.py:301-325`) — but only on issued cuts, never on an
  ad-hoc single ticket, and only when the oracle is a bare test command, not
  when it says "run the `acceptance-as-runnable-checks` fixed input".
- "For gate-deferred, already checked, or pre-existing-only tickets, never
  emit [the checker packet]" (`orch-frontier/SKILL.md:17-18`) — no code
  refuses it (`scripts/tickets_packet.py` refuses only gate-deferred and
  already-checked).
- `bound` is "the item's effort budget" (`contracts/work-item.md:107`); the
  only reader is staleness, via `_parse_bound_minutes`
  (`scripts/tickets_format.py:39,42,397-404`) which accepts only `^\d+(m|h)$`
  and otherwise returns 60 — so `<= 30 tool calls` is silently 60 minutes and
  nothing ever suspends on a bound.
- Verdict reuse on unchanged `covers` is permitted
  (`contracts/verdict.md:16-17`, `skills/kernel/orch-verify/SKILL.md:12-14`);
  the only executable precedent is cutcheck's `(command, tree)` memo
  (`scripts/cutcheck_execute.py:39-61`). No tree-hash-keyed cache exists.
- `tickets.py --file <path>` exists for `amend`, `result`, `run-state
  --artifact|--terminal`, `improvement --proposal`, and `new --file` for a
  whole ticket. It does not exist for `run-state --note` or
  `amendment-request --record` (`scripts/tickets_result.py:381-384`,
  `scripts/tickets_generations.py:468-470`).
- Sibling write-scope overlap is computed (`scripts/cutcheck_graph.py:85-96,
  301-341` → `scope-collision`; `_oracle_reads` → `staged-invalidation`);
  test-module identity is not.
- Successor roots citing a predecessor's Result/Handoff identity are law
  (`rules/topology.md §7`, `contracts/work-item.md:237-238,297-302`); there is
  no command that produces one.

## 3. Items

Each item names its owning files under the 510-line cap
(`tools/check_source_sizes.py:14`): `scripts/tickets_issue.py`,
`scripts/tickets_dispatch.py`, `scripts/tickets_lifecycle.py`,
`scripts/tickets_generations.py`, `scripts/workspace.py`,
`tools/run_tests.py`, `tools/run_serial_compat.py` are at or within two lines
of the cap; new behaviour goes in a new sibling module that the facade wires
(`scripts/tickets.py _sync_seams`, `tickets_dispatch._dispatch`,
`SUBCOMMAND_USAGE/SUMMARY`, `VALUE_FLAGS` at `tickets_dispatch.py:52`).
Installed scripts are plain copies from `scripts/` (`install.py:82-102`
`SCRIPT_NAMES` + `SCRIPT_SUPPORT_PREFIXES`); `tools/` is never installed.
Every item: Python 3.9+, Windows and POSIX, no network at run time, tests
under `tests/test_<subject>.py` (+ `tests/test_<subject>_cases/`) surviving
the one-process-per-module runner, and the serial manifest regenerated
(item 8) when tests are added.

### Item 0 — `tools/run_report.py`: retrospective speed report

Job: read the sink and print, for a UTC window, (a) runs ranked by exact
`elapsed_ms` then by opened-at → last sink write, with terminal status, ticket
count, complete/failed counts; (b) run families (stem grouping above) with
physical-run count, span, and statuses; (c) ticket durations by executor
(`claimed_at` → ticket file mtime; median/p90/max) and the 40 longest; (d)
friction records in the window by `category`, `skill`, `host`, run, and by a
fixed keyword-cluster table (PowerShell quoting, `rg` wildcard, guessed path,
truncated/escaped Result, workspace vantage, missing node_modules, word
ceiling, sealed cohort, isolation, missing flag, full-suite flake); (e) the
three metrics of §1 per family. Flags: `--since <iso>`, `--until <iso>`,
`--format text|json`, `--top N`. Read-only; never writes the sink.
Owner: new `tools/run_report.py` (+ `tools/run_report_support/` if over the
cap); add `read_run_identity(root, run)` to `scripts/ui_discovery.py` and
reuse `ui_model.read_ticket`, `ui_model.claim_meter`,
`ui_discovery.read_friction` rather than re-parsing.
Completion test: `uv run --no-project python -m unittest tests.test_run_report
-v` — a fixture sink with three runs (one terminal complete, one terminal
blocked with a non-decompose ticket never claimed, one nonterminal), two
families, and a friction file across the window boundary; the JSON output
names each metric with the expected value; `--since` after all records gives
empty tables and exit 0; a malformed `run.json` is reported under
`unreadable`, never raised.
Dogfood: run it before the first wave lands and after the last; the delta is
the acceptance evidence of §1 (reported, not asserted).

### Item 1 — `tickets.py lint`: every admission finding at once, syntactic ones auto-fixed

Job: `tickets.py lint <run> <id>` or `tickets.py lint --file <draft.md>
[--executor E --pack P]` runs every grader a later `new`, `ready`, `claim`,
`packet` would run — `ticket_defects`, `_issue_defects`, the 300-word
ceiling (`instruction_words`, reporting count and overage), `grade_admission`
(authority, adapter, input-record shape/canonical JSON, dependency state),
`grade_result` where a Result exists, and the whole-suite-oracle detector —
and emits **all** findings as one JSON list `{code, severity, kind:
syntactic|semantic, message, fix}`; exit 0 when none, 1 when any semantic
finding, 2 on an unreadable input. `--fix` rewrites the draft (or the pending
unclaimed ticket through the existing amend/recut paths, never a claimed one)
for syntactic findings only: canonical JSON re-emission of fixed inputs
(`tickets_input_producers.render_inputs` is the normaliser), `return-size` key
order, mutation path form, `isolation: required` for `orch-tdd`, prose VCS
exclusions that map to one reserved token (`VCS_ACTION_TOKENS`), missing
default-able frontmatter. Semantic findings (ceiling overage, executor/pack
mismatch, dependency-incomplete, cohort sealed, missing oracle) are reported
with the exact rule and never rewritten.
Owner: new `scripts/tickets_lint.py` wired through the facade; move the pure
whole-suite detector regex from `scripts/cutcheck_search.py:301-325` into
`scripts/tickets_format.py` (syntax owner) and have cutcheck import it from
there (cutcheck may import lower owners; admission and cutcheck still never
import each other). Also: `run-state --note --file <path>` and
`amendment-request --record-file <path>` (plus `-` for stdin on both), added
to `VALUE_FLAGS`.
Completion test: `uv run --no-project python -m unittest tests.test_tickets_lint
-v` — a draft with five simultaneous defects (noncanonical input JSON,
`isolation: none` on orch-tdd, a 320-word instruction, a prose VCS exclusion,
a missing oracle_class) reports all five in one call; `--fix` clears exactly
the three syntactic ones and leaves the two semantic ones with exit 1; a clean
`tests/test_tickets_cases/admission_v1.py`-style ticket exits 0; a `.gate.`
id and an `orch-decompose` root are exempt from the ceiling as today; `lint`
on a claimed ticket with `--fix` refuses with exit 2 and writes nothing;
`run-state --note --file` and `amendment-request --record-file` round-trip a
payload containing `"`, `'`, `` ` ``, `$`, newlines and a non-cp1252 glyph
byte-exactly; existing `tests.test_tickets` and `tests.test_tickets_issue`
stay green.
Dogfood: every ticket after this item lands is linted before `new`; the
decomposer runs `lint --file` on each draft unit before issuing it.

### Item 2 — `tools/affected_tests.py`: write_scope → test modules, mechanically

Job: `affected_tests.py <path> [<path> ...] [--format lines|json|argv]`
prints the top-level `tests/test_<x>.py` shard modules whose module or
`tests/test_<x>_cases/**/*.py` (a) imports a scope path's module
(`import scripts.foo`, `from scripts import foo`, `from tools import foo`,
`importlib.util.spec_from_file_location(..., "scripts/foo.py")`), or (b)
names the scope path as a string literal (`"scripts/foo.py"`,
`ROOT / "tools" / "foo.py"`); plus, for a scope path that is itself under
`tests/`, that module; plus every module whose case package or module reads
a literal under the scope path's directory when the scope path is a
directory. Static AST + literal scan, no imports executed. `--argv` prints
the list in `tools/run_tests.py MODULE ...` form. A scope path matching no
module prints a `no-tests:` line and exit 0; an unreadable test file is
reported and skipped.
Owner: new `tools/affected_tests.py`; `tools/run_tests.py` gains `--scope
<path>[,<path>]` that resolves through it (one new branch; if the file is at
cap, the branch lives in a new `tools/run_tests_scope.py`). `tools/preflight.py`
forwards positionals already.
Completion test: `uv run --no-project python -m unittest
tests.test_affected_tests -v` — over a fixture `tests/` tree: an import edge,
a `from … import` edge, a spec_from_file_location edge, a string-literal path
edge, a case-package edge attributed to its shard module, a directory scope,
and a no-match scope each resolve as stated; and, against the live repo,
`scripts/tickets_format.py` resolves to a set containing
`tests.test_tickets`, `tests.test_tickets_issue` and `tests.test_cutcheck`,
while `scripts/friction.py` resolves to a set containing `tests.test_friction`
(the spec_from_file_location case) — asserted as subsets so the test does
not pin the whole map.
Dogfood: every unit ticket after this lands names, in its completion test,
`uv run --no-project python tools/run_tests.py --scope <its write_scope>`
as its regression oracle rather than the full suite; the gate's row keeps
the full suite.

### Item 3 — `tools/run_required.py`: the five required checks, cached by tree identity

Job: `run_required.py [--repo <path>] [--python <exe>] [--no-cache]
[--format text|json]` runs, in order, the five checks `AGENTS.md` names —
`[python, tools/validate.py]`, `[python, tools/run_tests.py]`, `[python,
tools/run_serial_compat.py]`, `[python, install.py, --dry-run]`, `[git, diff,
--check]` — the three cheap ones concurrently, then `run_tests.py`, then
`run_serial_compat.py`; records each `{argv, started_at, ended_at,
exit_status, stdout_sha256, stderr_sha256, cached: bool}` and one overall
record `{repository_identity, tree_identity, dirty, commands[], exit}` as JSON
(`required-check-run/v1`); exit 0 when all five exit 0, 1 otherwise, 2 on
refusal (interpreter missing, not a git checkout). **Cache:** key = sha256
over (`git rev-parse HEAD^{tree}`, a sha256 of `git diff HEAD` including
untracked-but-not-ignored files, argv, resolved interpreter path,
`sys.platform`, `python --version`); store under
`<repo>/.orch/required_cache/<key>.json` (gitignored already via `.orch/*`).
A hit on exit 0 returns the stored record with `cached: true` and does not
re-run. A stored non-zero exit is never served (always re-run). A run is
cached only when the tree was clean at start and unchanged at end. `--no-cache`
bypasses. The cache is a deterministic-oracle memo exactly as
`cutcheck_execute._exit_code` is; it never stands in for a judged verdict.
Owner: new `tools/run_required.py` (+ `tools/run_required_support/` as
needed). `AGENTS.md` gains one line naming it as the way to run the five
checks locally (the five commands stay listed; CI unchanged —
`tests/test_run_tests.py:223-296` pins the workflow shape).
Completion test: `uv run --no-project python -m unittest
tests.test_run_required -v` — with a stub `python` that records its argv to a
file: five commands in the stated order with the cheap three overlapping in
`[started_at, ended_at)`; exit mapping 0/1/2; a second invocation on an
unchanged clean tree serves all five from cache with `cached: true` and
invokes nothing; touching one tracked file invalidates; a dirty tree is run
but not stored; a stored exit 1 is re-run; `--no-cache` re-runs; the JSON
record validates against the stated keys. `git diff --check` on the result
is green.
Dogfood: after it lands, the join runs `run_required.py` at each integrated
tip; the gate's verify reads the record; the checker for any later ticket
reuses its record on an identical tree instead of re-running.

### Item 4 — bounds are enforced

Job: (a) `tickets.py bound-check <run> [--now <iso>]` lists every claimed
ticket with `{id, bound, bound_kind: duration|tool-calls|iterations|other,
bound_minutes, claimed_at, last_motion_at, elapsed_minutes, overdue: bool}`;
exit 1 when any is overdue. Bound parsing widens `_parse_bound_minutes`
to accept `Nm`, `Nh`, `N min`, `N minutes`, `N hours`, `<= N tool calls` /
`N tool calls` (converted at a stated default of 2 minutes per tool call,
constant `TOOL_CALL_MINUTES`), `<= N iterations` (reported as `iterations`,
minutes from `N * DEFAULT_BOUND_MINUTES`), and any leading `<=`/`at most`;
anything else reports `other` with `bound_minutes: 60` as today. `last_motion`
is `tickets_packet._last_motion` (own sections or a named Result artifact).
(b) `skills/engines/orch-frontier/SKILL.md` gains one sentence: at each
re-check the engine runs `bound-check`; a ticket overdue with no motion since
its bound elapsed is parked by the engine as `suspended` with a Handoff stub
naming the bound, `last_motion_at`, and "bound elapsed without motion; caller
decides", through the existing join-side status path; a ticket overdue with
motion is reported `over-bound` in the run notes and continues.
`references/profiles.md` names `bound-check` as the re-check command.
Owner: new `scripts/tickets_bound.py` wired through the facade; parser change
in `scripts/tickets_format.py`; `scripts/ui_model.claim_meter` reads the same
parser. Skill prose per above.
Completion test: `uv run --no-project python -m unittest
tests.test_tickets_bound -v` — each bound grammar above parses to the stated
minutes/kind; a claimed ticket with `claimed_at` 90 minutes ago, bound `30m`,
and last motion 80 minutes ago is `overdue: true`; the same with motion 5
minutes ago is `overdue: true` (still over) but the engine rule's
"park" predicate (exposed as a pure function) is false; exit codes; `--now`
pins the clock; `tests.test_ui` stays green. `tools/validate.py` accepts the
skill edit (one sentence, inside existing budgets).
Dogfood: the root for this run carries a real bound; the engine (this
session) runs `bound-check` at each re-check once the item is installed.

### Item 5 — the checker is not dispatched when §10 already exempts the ticket

Job: `tickets.py packet <run> <id> --executor orch-critique` refuses with
`checker not required: every criterion carries provenance: pre-existing
(verification §10)` when the ticket's `independence` is `checker` (or
absent) and every `## Completion test` criterion carries `provenance:
pre-existing`; the refusal names the rule. The frontier's existing sentence is
unchanged.
Owner: `scripts/tickets_packet.py` (370 lines).
Completion test: `uv run --no-project python -m unittest
tests.test_tickets_packet_checker -v` (new case module under
`tests/test_tickets_cases/`) — refusal on the all-pre-existing ticket; the
ordinary executor packet for the same ticket still issues; a ticket with one
`authored-here` criterion still issues the checker packet; gate-deferred
behaviour unchanged.
Dogfood: later tickets in this run whose oracles are all pre-existing skip
the checker.

### Item 6 — cutcheck: close the fixed-input indirection; advisory shared-test-module

Job: (a) `whole-suite-oracle` also fires when a unit's oracle names a fixed
input (by `name`) whose literal value is, or contains, any of the five
required-check commands or a bare `tools/run_tests.py` / `unittest discover`
invocation. (b) New advisory finding `shared-test-module` (family 4, pairwise):
for each unordered sibling pair, the `affected_tests` sets of their
`write_scope`s intersect; reported with the shared module names. Advisory
(does not move the exit status) in this generation; the graph reading is
unchanged.
Owner: `scripts/cutcheck_search.py` / `cutcheck_ticket.py` for (a) (importing
the detector from `tickets_format` per item 1); `scripts/cutcheck_graph.py`
for (b), calling `tools/affected_tests.py` as a subprocess or importing it by
path (cutcheck may import lower owners; `tools/` is repo-only, so the import
is guarded and the finding is skipped with an `advisory` note when the tool
is absent in an installed copy).
Completion test: `uv run --no-project python -m unittest tests.test_cutcheck
-v` restricted to the new case modules: a unit whose oracle is "run the
`acceptance-as-runnable-checks` fixed input" with the five commands as the
value is convicted; the same with a focused command is not; two siblings both
scoped to `scripts/tickets_format.py` report `shared-test-module` naming
`tests.test_tickets`; exit status unchanged by the advisory.
Dogfood: the cut for this run is checked with the extended detector once
installed.

### Item 7 — `tickets.py reissue`: supersede a blocked ticket without re-spec

Job: `tickets.py reissue <run> <id> --run <new-run> [--id <new-id>] [--set
<key>=<value> ...] [--add-scope <path>[,<path>]] [--cite result|handoff]`
reads the source ticket, drops lifecycle state (`claimed_by`, `claimed_at`,
`checked_by`, `workspace_*`, `admission` → `v1:pending`, `status` →
`pending`, v2 generation/seal fields, `cohort` → a fresh cohort of the same
shape for the new run), applies `--set` to frontmatter keys and `--add-scope`
to `write_scope`/`mutations`, appends one fixed input
`{"identity":{"kind":"ticket-section","run":<run>,"ticket":<id>,
"section":"Result"|"Handoff","sha256":<digest>},"name":"predecessor",
"type":"identity"}`, writes the result through the existing `new --file`
path (so every admission rule applies and lint runs), and prints the lint
report plus the new path. Refuses (exit 2) when the source is `pending` or
`ready` (amend exists for that), when `--run` names an existing run holding a
root and the source is a root, or when a `--set` names an executor-owned
section. Never edits the source.
Owner: new `scripts/tickets_reissue.py` wired through the facade; reuses
`tickets_issue._place_ticket` and item 1's lint.
Completion test: `uv run --no-project python -m unittest
tests.test_tickets_reissue -v` — a blocked root reissued into a new run with
`--add-scope web/src/smoke.spec.ts` carries the predecessor identity with a
verified digest, a fresh cohort, no lifecycle fields, the widened scope, and
passes `grade_admission`; `--set isolation=required` lands; refusals as
stated; the source file bytes are unchanged.
Dogfood: any ticket in this run that blocks on a field problem is reissued
with this command rather than re-specified.

### Item 8 — serial manifest regenerates itself; scans skip `node_modules`

Job: `tools/run_serial_compat.py --write-manifest` regenerates
`tests/serial_compat_manifest.json`'s `discovery` (`count`, `identities`,
`sha256`) from live discovery and `mutation_owners` from
`scan_mutation_owners`, preserving `sentinels` byte-for-byte and the key
order; prints the before/after count and sha; exit 0. Owner classification
stays whatever the scan says today (the spec's Proposal 3 concern is about
*semantic* owner classes; the count and identity multiset are derived
facts). `tests/test_benchmaker_cases/retirement.py` `SKIPPED_TREES` gains exactly
`node_modules` and `.venv`; `BINARY_SUFFIXES` gains `.ttf`, `.woff`, `.woff2`.
Owner: new `tools/serial_manifest.py` (the runner is at cap) called from the
runner's flag; `tests/test_benchmaker_cases/retirement.py`.
Completion test: `uv run --no-project python -m unittest
tests.test_serial_compat -v` plus a new case: after adding one test to a
fixture tree, `--write-manifest` makes `_require_discovery` pass and the
sentinels block is byte-identical; `uv run --no-project python -m unittest
tests.test_benchmaker -v` stays green with a `node_modules/x.ttf` of random
bytes placed under the repo during the test (and removed after).
Dogfood: every ticket in this run that adds a test runs `--write-manifest`
as its last slice instead of hand-editing the count.

### Item 9 — `workspace.py start` prepares the tree; detached HEAD and absolute scope are graded

Job: (a) after recording, `start` runs `pnpm install --frozen-lockfile
--prefer-offline` in `top` when `top/pnpm-lock.yaml` exists and `pnpm` is on
PATH, with a 10-minute ceiling, and reports `{frontend: installed|skipped:
<reason>|failed: <exit>}` in its payload plus `playwright_browser:
present|missing|unknown` (present when `ORCHFLOWS_BROWSER_EXECUTABLE` resolves
or `pnpm exec playwright --version` and the chromium directory under the
Playwright cache exist) — it never installs a browser. (b) In a detached
worktree (`rev-parse --abbrev-ref HEAD` → `HEAD`), `start` records
`workspace_branch` as `detached:<full-sha>` and `check` accepts that form as
the tip ref, grading ancestry and scope exactly as for a branch. (c) Absolute
`write_scope` entries under `top` are canonicalised to repo-relative POSIX
form in the recorded payload and in the scope used by `check`; an absolute
entry outside `top` is refused at `start` with the existing message.
Owner: new `scripts/workspace_prepare.py` for (a); `scripts/workspace.py`
(508 lines — move the HEAD/branch capture into `workspace_git.py` to make
room) and `scripts/workspace_scope.py` for (b)/(c). The installer never
invokes pnpm (`tests/test_installer.py:262` stays green).
Completion test: `uv run --no-project python -m unittest tests.test_workspace
-v` plus new cases: a fixture repo with a `pnpm-lock.yaml` and a stub `pnpm`
on PATH records `frontend: installed` and the stub's argv; without pnpm,
`skipped: pnpm-missing`; a detached worktree starts, checks, and grades a
scoped commit; an absolute in-tree scope entry is recorded relative and
graded; an absolute out-of-tree entry refuses.
Dogfood: every worktree this run opens goes through `start`; the frontend
tickets (none in this run) would inherit it.

### Item 10 — host block: two mechanical sentences, inside budget

Job: extend demand #6 of `templates/host-block.md` ("In a worktree-isolated
session, one command per Bash call: no loops, no `&&` chains.") with ";
pass `rg` globs with `--glob`, never as a positional path; pass ticket text
with `--file`, never inline." and pay for it inside the 400-word budget by
tightening existing sentences (`tools/validate.py` and
`tests/test_installer_cases/managed_text/host_block.py` both enforce; the
eight-demand count is unchanged because the clause extends #6).
Owner: `templates/host-block.md`; anchors in
`tests/test_installer_cases/managed_text/host_block.py:143-147`.
Completion test: `uv run --no-project python tools/validate.py` exit 0 with no
new WARN naming host-block; `uv run --no-project python -m unittest
tests.test_installer -v` green; `uv run --no-project python install.py
--dry-run` green; the rendered block contains both new phrases.

### Item 11 — critique marks blocking findings; gate repair consumes only those in-run

Job: `orch-critique`'s ranked findings carry `blocking: true|false` —
`true` when the finding shows a frozen completion criterion false or a
correctness-lens defect at the fixed identity; `false` otherwise (shape,
contract-fidelity without a failing criterion, scope advisories). The gate
repair's objective and completion test (`scripts/tickets_dispatch.py:254`)
read "every accepted **blocking** finding is repaired inside this ticket's own
write scope, or declined with a stated reason; accepted non-blocking findings
are queued as candidate scope per verification §9". `orch-integrate`
records non-blocking accepted findings to the run's
`improvement/` or `successors.md` candidate list rather than the repair
ticket.
Owner: `skills/kernel/orch-critique/SKILL.md` (Return shape),
`packs/orch-code-pack/references/craft.md#lens` (blocking definition per
lens), `scripts/tickets_dispatch.py:254` objective text (no new lines),
`skills/kernel/orch-integrate/SKILL.md` (one sentence).
Completion test: `uv run --no-project python tools/validate.py` exit 0;
`uv run --no-project python -m unittest tests.test_tickets -v` green (the
gate stub text is pinned in `tests/test_tickets_cases/`; update the pin);
`tools/validate.py` near-duplicate warnings do not increase for the edited
files.
Dogfood: this run's gate critique returns blocking flags; only blocking
findings enter `gate.repair`.

## 4. Sequencing and the cut

Wave 0 (no dependencies between them; all are new modules or additive
flags): items 0, 1, 2, 3, 8, 9, 10. Wave 1 (each depends on the named wave-0
item): item 4 (no dependency; wave 1 to keep wave 0 at seven), item 5 (no
dependency), item 6 (depends on items 1 and 2), item 7 (depends on item 1),
item 11 (no dependency). Gate: code-pack critique lenses → repair → verify on
the integrated tip, with the full required checks through item 3's runner.

Write-scope ownership is disjoint by construction except: `scripts/
tickets_format.py` (items 1 and 4 — order item 4 after item 1 or give item 4
its parser in `tickets_bound.py` and let `tickets_format` import it; choose
the latter so they stay parallel), `scripts/tickets.py` facade and
`scripts/tickets_dispatch.py` wiring (items 1, 4, 7 each add a subcommand —
each adds exactly its own lines to `_dispatch`/`SUBCOMMAND_*`; since
`tickets_dispatch.py` is at cap, item 1 first moves the subcommand tables
into a new `scripts/tickets_commands.py` that items 4 and 7 then extend;
therefore items 4 and 7 depend on item 1), `tests/serial_compat_manifest.json`
(every item that adds a test; the integrator regenerates it at each merge
batch with item 8's flag once it lands, and by hand before that).

Decomposer: the unit tickets are this section's items; each unit's
completion test is the item's stated oracle list plus `uv run --no-project
python tools/run_tests.py --scope <write_scope>` once item 2 is installed
(before that, the named test modules); `git diff --check`; and `uv run
--no-project python tools/validate.py` only for items touching
`skills/`, `packs/`, `templates/`, `contracts/`, `rules/`, `AGENTS.md`. The
full `run_tests.py`, `run_serial_compat.py`, and `install.py --dry-run` are
the gate's row. Bound per unit: 90 minutes (items 0, 3, 9), 60 minutes
(others). Instruction budget 300 words per unit — the item text above is the
source; the unit quotes the oracle list, not the rationale.

## 5. Non-goals and refusals

- No change to who owns the semantic root, to append-only executor sections,
  to verification §10's paths, or to join-only terminal status.
- No automatic semantic ticket repair: `lint --fix` touches syntax only;
  `reissue` copies fields the caller names and nothing else.
- No cached judged verdicts; no cached non-zero exits; no cache across
  interpreter or platform.
- No browser installs, no network in any script.
- No new control-plane identities (lifecycle.json, control cards, evidence
  ledger, host preflight) in this generation; revisit only if `run_report.py`
  after this program still shows admission-side loss.
- The prior spec's Proposals 1 (`workspace.py plan`) and 2 (`tickets.py show`,
  `state-check`) remain good and are not in this wave; `lint` and
  `bound-check` cover the urgent half of Proposal 2's "show".

## 6. Measurement

`tools/run_report.py --since 2026-08-15 --until 2026-08-23` is the baseline
(recorded once item 0 lands; the numbers in §1 are its expected shape).
After this program merges and installs, every subsequent run is in the
report; the review repeats after one week of ordinary use. Report, do not
assert: wall-clock per objective, physical runs per objective, oracle
minutes per objective, and the friction clusters named in item 0.
