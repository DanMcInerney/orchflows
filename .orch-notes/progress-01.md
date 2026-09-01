Progress checkpoint (not final). Items completed so far, each verified dead
by grep before deletion, scoped tests run and green:

1. tests/test_tickets_cases/common.py: deleted unused SequencedPath,
   refusing_to_read, refusing_to_write (zero repo-wide consumers), and 5
   dead constants (TICKETS_FORMAT_PY, TICKETS_STORE_PY, TICKETS_WORKLOG_PY,
   STATE_ROOT_PY, WORKSPACE_PY) -- verified against the full wildcard-import
   fan-out in tests/test_tickets_cases/*.py plus external importers
   (test_lock_discipline.py, test_tickets.py, test_tickets_bound.py).
   Spec cited "common.py:50-52" for the dead constants; line numbers had
   drifted (this branch already carries B1.1-B1.9 merges) so I trusted the
   grep, not the anchor -- 5 dead constants found, not the 2-3 the old
   line range implied.
2. tests/test_lock_discipline.py:30-31: removed the literal duplicate
   `from scripts import tickets_dispatch_facade` line (module is used
   elsewhere in the file, so the import itself stays).
3. tests/test_validate_cases/sink_contracts.py: removed 10 dead imports
   (ast, os, shutil, subprocess, datetime, timezone, scripts.friction,
   scripts.state_root, tools.validate, tests.tree_removal.remove_repo_tree)
   -- confirmed via grep that none appear anywhere else in the file body,
   and confirmed tests/test_validate.py only imports the three test
   classes from this module, not any module-level name. The module
   docstring's "third half" description (PACK_WORKSPACE_MECHANISMS,
   friction-log checks) no longer matches this file's content -- those
   checks live in validator_ownership.py/sink_law.py now. Left the
   docstring as-is: out of this item's scope (dead imports only), and
   editing prose beyond that risks scope creep this ticket doesn't cover.
4. tests/test_validate_cases/validator_ownership.py:2: removed dead
   `import ast` (every other import in the file has real, verified
   in-file uses; ast had none).
5. tests/test_validator_cases/support.py: removed dead `import json` and
   `import subprocess` (grep showed only their own import lines and
   comment-text hits, e.g. "pins.json" prose, not real usage). `io` at
   the same cited line range (spec said ":3,6") is NOT dead -- it's used
   at `io.StringIO()` in `_run` -- so I left it. Deviation note: a
   consumer (io.StringIO usage) redeemed one of the two originally-cited
   lines; verified other test_validator_cases files import subprocess/json
   directly where they actually need them, confirming support.py's copies
   were genuinely orphaned.
6. tests/test_installer_cases/support.py:224-229: deleted dead
   `seed_user_frontend` (zero callers repo-wide).
7. tests/test_tickets_cases/identity_terminal.py:310: the vacuous test.
   Retargeted (not deleted) the `("check", ...)` row inside
   `test_every_ticket_writing_subcommand_reports_and_lands_nowhere` to
   `("dispatch-outcome", "testrun", "T1", "--note", "a line")`. Chose
   retarget over delete because the row's law (rules/visibility.md §6
   no-fallback) needs a witness for a genuine ticket-writing subcommand,
   and `dispatch-outcome` is live, untested elsewhere in this file for
   this law, and structurally fits the existing loop. Verified empirically
   with a standalone probe (not just reasoning): under a blocked sink,
   `dispatch-outcome` fails with `"unreadable ticket: [Errno 2] No such
   file or directory: '.../not-a-directory/state/tickets/testrun/T1.md'"`
   -- a genuine sink-unreachable failure, not a usage error and not
   "unknown subcommand". `check` itself is confirmed retired: no
   subcommand table entry anywhere in scripts/tickets_commands.py.
   Class test suite (2 tests) reruns green.
8. reader/scripts/ui_layout.py: this is the biggest item and needed more
   than a one-line fix. Per report P11 (explicitly cites this as "dead
   server-side work maintaining a duplicate that is never used", B1.3
   note-02) and confirmed independently: the browser now lays the
   dependency graph out itself (reader/web/dist/assets/elk-worker...js,
   RunMapView.tsx/elk.worker.ts/layout.worker.ts per the review). Neither
   JSON-API consumer of `graph_layout()` (ui_now_projection.py,
   ui_runs_projection.py) nor ui_experience.py ever reads anything but
   `layout["edges"]` / `layout["diagnostics"]` -- `nodes` (with x/y),
   `width`, `height` are computed and thrown away by every caller.
   Deleted: LAYER_WIDTH/NODE_WIDTH/NODE_HEIGHT/GAP_X/GAP_Y/MARGIN
   constants, the LayoutNode namedtuple, `_predecessors`,
   `_coffman_graham_order`, `_layer_assignment`, `_barycenter`,
   `_within_layer_order`, and the entirely-unused (zero callers anywhere,
   not even a test) `LAYOUT_CACHE`/`LAYOUT_CACHE_LIMIT`/`cached_layout`.
   `graph_layout()` now returns only `{"edges": ..., "diagnostics": ...}`;
   the cycle/dangling detection it depends on (`_break_cycles`,
   `layout_key`) is untouched since it IS consumed. Also removed the now-
   dead `_make_room` import (only user was `cached_layout`).
   reader/tests/test_ui_cases/graph.py rewritten to match the slimmed
   contract (dropped x/y/layer/order/width/height assertions and the
   LAYER_WIDTH bound-check; kept edge/diagnostic assertions, renamed two
   tests to describe what they now check). Verified: both the isolated
   graph.py test module (8/8 green) and workflows_sources.py (9/9 green)
   pass. Searched reader/web/src for any frontend read of width/height
   from the API response -- none found, confirming the browser truly
   never consumed the server geometry.
9. NAME_RE dedup: reader/scripts/ui_artifacts_projection.py's byte-
   identical copy deleted; it already imports
   `ui_workflows_identity as contained`, so its one use site now reads
   `contained.NAME_RE`.
10. REDACTED_HOST_PATH dedup (3 copies -> 1): no existing import
    relationship made an owner obvious among ui_artifacts_projection.py,
    ui_experience.py, ui_workflows_sources.py, so I put the single
    definition in reader/scripts/ui_model.py, which is already the
    module all three of these reach (directly or is idiomatic to reach)
    for shared sentinel-string constants (EMPTY_*, DIAGNOSTIC_UNREADABLE
    live there in the same style) -- no new module created. All three
    consumers now import it; the WINDOWS_HOST_PATH_RE/POSIX_HOST_PATH_RE
    regexes next to each copy were NOT touched (P11 named only
    REDACTED_HOST_PATH as duplicated, not the regexes -- out of scope).
    `reader/tests/test_ui_cases/workflows_sources.py`'s
    `sources.REDACTED_HOST_PATH` access still resolves (module-level
    import binding). Reran workflows_sources tests green (see item 8).
11. Two fixture READMEs (tests/fixtures/transcripts/README.md,
    tests/fixtures/ui/README.md): both cited nonexistent
    `tests/test_ui.py`. Confirmed via `find` that no such file exists
    anywhere in the tree, and via grep that the actual consumer copying
    both fixture trees is `reader/tests/test_ui_cases/_base.py`
    (FIXTURES / FIXTURE_TRANSCRIPTS constants). Fixed both citations to
    name the real consumer. Left
    tests/fixtures/final_specs/01/authorities.json's own "tests/test_ui.py"
    string alone -- it's synthetic fixture *data* for a different test
    (not one of the "two fixture READMEs" the ticket named), and
    research/architecture-repair-spec-2026-09-01.md's own mention is the
    ticket's own source text, not something to edit.
12. ITERATION_ID_RE (scripts/tickets_worklog.py:28): confirmed zero real
    consumers anywhere (only the facade re-export in tickets.py touches
    it, no `.match`/`.fullmatch`/`.search` call site exists at all) --
    genuinely dead as a matcher today, but per Details this is a behavior
    fix regardless. Changed `r"^.+\.iter\.\d+$"` to
    `r"^.+\.repair\.\d+$"` to align with tickets_format.py:100-104's live
    `ROUND_ID_RE` grammar (REPAIR_MARKER = 'repair'). Also fixed the
    stale `X.iter.2` docstring example at tickets_format.py:324's
    `mint_ordinal` to `X.repair.2` (verified the docstring's behavioral
    claim still holds for the new example by tracing MINT_CHILD_ID_RE
    against it by hand). No live consumer was found still emitting
    `.iter.` ids, so this is the mechanical fix per the Details, not a
    deviation.
13. Dead worklog/format constants: deleted `_packs_root`, `_upstream`,
    `PACKS_DIR` from scripts/tickets_worklog.py (zero consumers beyond
    the facade), and `PACK_NAME_PREFIX`/`PACK_NAME_SUFFIX` from
    scripts/tickets_format.py:90-91 (same). Since scripts/tickets.py is a
    hand-maintained re-export facade (not test-enforced for parity --
    checked: no test iterates every submodule's public names against the
    facade), I had to manually delete the 5 corresponding facade lines in
    scripts/tickets.py too, or `import scripts.tickets` would crash with
    AttributeError at module load (these are eager attribute reads, not
    lazy properties). Verified fix by importing scripts.tickets directly
    after the edit.
14. DEFAULT_BOUND_MINUTES split (scripts/tickets_bound.py:63-64): added a
    new `ITERATION_MINUTES = 60` constant (same value, no behavior
    change) for the iterations-kind minutes-per-iteration factor, leaving
    `DEFAULT_BOUND_MINUTES` meaning only the unparsed-bound fallback
    substitute. Updated the one witness test
    (tests/test_tickets_bound.py::test_the_stated_conversions_are_the_stated_constants,
    the Ruling-3-style "one owner one witness" pin for these constants)
    to also assert `ITERATION_MINUTES == 60`, and fixed its neighbor
    test's docstring that named the old shared constant. Added the
    facade re-export in scripts/tickets.py for symmetry with
    TOOL_CALL_MINUTES. tests/test_tickets_bound.py full module reran
    green (15/15).

Verification note on process: an early scoped run
(`tools/run_tests.py --scope tests/test_tickets_cases/common.py,tests/test_lock_discipline.py,tests/test_validate_cases/sink_contracts.py,tests/test_validate_cases/validator_ownership.py,tests/test_validator_cases/support.py,tests/test_installer_cases/support.py`)
surfaced FAILs in tests.test_validate and tests.test_validator. Bisected
by stashing my changes and rerunning: baseline (unedited tree) was green
(0 failures). With my changes, the only new failure signature is
`ERROR tests/serial_compat_manifest.json: committed serial-compatibility
manifest drifted from the live test tree` (raised by validate.py's own
check when it runs against the live repo tree, which several tests in
test_validate/test_validator/test_cell_linter exercise). This is expected
mid-work per the Details ("regenerate the serial manifest ... at the
end"); confirmed the WARN lines in the same output are pre-existing
cross-tier near-duplicates unrelated to my edits (identical content in
both the baseline and edited runs). Manifest regen + final validate.py /
install.py --dry-run / git diff --check pass are still pending, to be run
once after every remaining item is done.

Still remaining: rings.py resolve()/inventory() factoring,
tests/test_script_executors.py:32-77 fixture headings, dead installer
surface (packages.py/application.py/presentation.py/planning.py),
GROK_MODEL_CENSUS, dead tools items (run_report_support/model.py,
live_routing_bench.py, validate_support/common.py), then the end-of-work
gate: tools/validate.py, install.py --dry-run, git diff --check,
tools/run_serial_compat.py --write-manifest, and a final broad scoped
test run.
