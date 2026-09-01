Progress checkpoint 2 (not final) -- remaining items completed after
progress-01.md, plus one important reasoning correction.

15. scripts/rings.py: factored the duplicated shadows/notice-building code
    (identical between resolve() and inventory()) into one new private
    function `_shadowed_record(hits)`, called by both. This is the one
    prescribed exception to "no new helper added anywhere" -- Details
    explicitly authorizes exactly this: "one private function both
    resolve() and inventory() call -- inside rings.py, not a new module."
    Left resolve()'s reserved-name *refusal* (raises RingError) and
    inventory()'s reserved/refusal *recording* (never raises) as their own
    separate logic -- they are genuinely different behaviors over the
    reserved-name concept, only the shadows/notice construction was
    byte-identical. `_shadowed_record` is not added to `__all__`,
    consistent with the file's other private helpers (`_require_trust`,
    `_trust_state`). tests.test_rings reran green (20/20).
16. tests/test_script_executors.py:32-77: migrated the fixture ticket's
    body from the pre-migration Objective/Fixed inputs/Completion
    test/Return fields/Result/Verification/Feedback/Risks section set to
    the live sealed Goal/Context/Report schema (contracts/work-item.md,
    scripts/tickets_markdown.py's CUT_SECTIONS + EXECUTOR_SECTIONS).
    Confirmed first that `tickets_admission.grade_admission` (what this
    whole test file exercises) never reads body sections at all -- the
    old headings were cosmetic, so this is a pure prose-accuracy fix with
    no behavior at stake. Verified against a real live-schema fixture
    already in use elsewhere (tests/test_registry_census.py) for the
    exact idiom. tests.test_script_executors reran green (9/9).
17. Dead installer surface, installer/packages.py:289,296
    (`template_markers`, `resolved_python_interpreter`): both are true
    dead code in *production* -- zero call sites anywhere in installer/
    or install.py's actual logic, confirmed by grep; both survive only as
    the facade re-export line in install.py and as direct calls from
    three tests. Traced the real, live mechanism each one duplicates:
    `template_markers(template_text)` derives the managed-block start/end
    marker strings by taking the first and last stripped line of the raw
    template file; `installer/hosts.py`'s `marker(host, "host_instructions",
    adapters)` derives the same two strings from the per-host adapter's
    `managed_markers` registry (the mechanism `_host_block_content()`
    actually uses today). Verified byte-for-byte that both give identical
    strings today (checked installer/host_adapters/claude.json and
    grok.json directly) before touching any test, so retargeting the two
    test call sites to `install.marker(...)["start"/"end"]` is exactly
    behavior-preserving, not a guess. `resolved_python_interpreter()`
    (sys.executable-based) is superseded by the private-runtime mechanism
    (`private_runtime_python()`, used by `_host_block_content()`); its one
    dedicated unit test
    (`test_resolved_python_interpreter_refuses_a_bare_name`) tested
    nothing but this dead function's own behavior, so it is deleted
    outright rather than adapted. Deleted the now-dead `import sys` in
    installer/packages.py (zero remaining `sys.` uses) and the orphaned
    "managed marker blocks" section-heading comment above the deleted
    functions. Added `marker` to install.py's `installer.hosts` import
    (parallel to `template_markers`'s removal from the `installer.packages`
    import). Verified: `install.py --dry-run` renders; the two retargeted
    tests
    (tests.test_installer_shared::test_apply_migrates_legacy_inline_block_in_claude_md,
    tests.test_installer_hosts::test_the_planned_grok_surface_hangs_off_grok_home)
    pass individually; the full test_installer_managed/test_installer_hosts/
    test_installer_shared/test_installer_planning modules all green.
18. installer/hosts.py:16 GROK_MODEL_CENSUS: `("grok-4.6", "grok-4.5")`
    allowed "grok-4.5", which appears nowhere else in the entire
    repository except this tuple and the two tests that iterate it
    generically (neither test asserts on the specific string "grok-4.5",
    both are parametrized over whatever the tuple holds). Cross-checked
    installer/host_adapters/grok.json and hosts/grok.json (the two real,
    shipped bindings) -- only "grok-4.6" is ever bound to a role.
    Contrasted deliberately against GROK_EFFORTS (5 declared values,
    "low"/"medium"/"max" also currently unbound by any profile, yet NOT
    flagged by the spec) to confirm the standard here isn't "unused by a
    current profile" but "not a real value anywhere" -- "grok-4.5" fails
    that stricter bar, "low"/"medium"/"max" don't (they're real Grok
    effort levels available for a future profile). Changed to
    `("grok-4.6",)`. Zero test changes needed (both consumers are
    parametrized over the tuple's contents). tests.test_live_harnesses -k
    grok (6/6) and the full tests.test_installer_hosts (44/44) rerun
    green.
19. tools/run_report_support/model.py:32-33 (`LONGEST_TICKETS`,
    `SLICE_EXECUTOR`) and render.py:114's "decompose" wording -- IMPORTANT
    CORRECTION, reported as a deviation from the Goal's literal item list,
    not silently skipped. I initially deleted `SLICE_EXECUTOR` and the
    `work = [... executor != SLICE_EXECUTOR]` filter feeding
    `claimed_no_work`, trusting the spec's "vestigial" framing (orch-slice
    is a fully-retired executor per docs/vocabulary.md and
    contracts/work-item.md's W4a decomposition retirement, tombstoned in
    scripts/tickets_registry.py's SUPERSEDED_EXECUTORS-style remedy table
    -- no *new* ticket can ever carry executor: orch-slice again). Running
    the scoped tests caught the actual defect before I moved on:
    tests/test_run_report_cases/common.py's BLOCKED_RUN fixture
    deliberately writes a *historical* ticket with
    `executor="orch-slice", claimed_at=...` (claimed) alongside a real
    "orch-tdd" ticket that is never claimed -- exactly the shape the
    fixture's own docstring says "36 of the baseline's 159 [historical]
    runs had". The run-report tool's job is to summarize the *whole sink
    history*, including pre-W4a runs where orch-slice tickets are real,
    legitimately-claimed data -- removing the filter flips
    `claimed_no_work` from True to False for that fixture (its slice
    ticket has a claimed_at) and breaks
    tests.test_run_report_cases.runs::test at line 61 plus the totals
    assertion at line 64. This is the textbook case the Details warned
    about: "verify each item is dead by grep before deleting" was not
    enough here -- the code path is reachable and *correct* over
    historical data even though it can never fire on a *new* ticket.
    Reverted `SLICE_EXECUTOR` and the `work` filter to their original
    text (confirmed via `git diff` showing zero net change to those
    lines) and reverted the render.py:114 wording change too (the
    "non-decompose ticket" phrase is accurate as long as the mechanism it
    describes still exists). Kept only `LONGEST_TICKETS` deleted --
    confirmed separately dead (a value-40 near-duplicate of the live
    `DEFAULT_TOP = 40`, zero references anywhere, no test dependency).
    tests.test_run_report full module (49/49) reran green after the
    revert, confirming the correction.
20. tools/validate_support/common.py:172 (line drift: now ~190)
    `TEMPLATE_ENTRY_VALUES = {"routed", "named"}`: zero real usage beyond
    its own `__all__` entry (confirmed by grep). The ~25-line comment
    block directly above it exists solely to justify this one constant,
    describing the fully-retired `template.md`-plus-stubs mechanism
    (contracts/work-item.md's own text: "retired with the decomposed-root
    concept they served (W4a)"). Confirmed the *current*
    `validate_templates` function (tools/validate_support/structure.py,
    still called from tools/validate.py) does something entirely
    different today (validates `example-workflows/<name>/SKILL.md`
    workflow-skill frontmatter) and touches `TEMPLATE_ENTRY_VALUES`
    nowhere -- the name survived a repurposing, the constant did not.
    Deleted the constant, its `__all__` entry, and the now-orphaned
    comment block describing dead architecture (craft.md: "Comments state
    only what code cannot" -- a comment with nothing left to explain is
    not kept for atmosphere). tests.test_validate reran green as part of
    the final comprehensive scoped run (item 22 below).
21. tools/live_routing_bench.py:77 `ROLE_SKILL_ROUTES = {}`: permanently
    empty, so `.get(route_class(expected))` always returns `None` and the
    `if required_pair and ...` refusal at line 120-124 can never fire --
    confirmed zero test exercises this branch (no test even imports the
    name). This is a *separate*, always-inert cross-case consistency
    check layered on top of the real, live per-case
    `required_role`/`required_skill` enforcement, which is a completely
    different, still-live path
    (tools/live_routing_bench_support/execution.py:172-173,
    `expected_role=`/`expected_skill=`, unaffected by this deletion).
    Deleted the dict and the branch that reads it.
    tests.test_live_harnesses full module (119/119, including
    routing_grading_cases.py) reran green.
22. End-of-work gate, run once after every item above:
    - `tools/validate.py`: exit 0. Every remaining line is a pre-existing
      WARN (cross-tier near-duplicate prose, unrelated to this ticket's
      files) -- confirmed identical WARN set present on the untouched
      baseline tree early in this run (see progress-01.md's bisection
      note).
    - `tools/run_serial_compat.py --write-manifest`: regenerated
      tests/serial_compat_manifest.json (discovery 2115->2114 tests,
      mutation owners 383->380 -- both explained by this ticket's
      deletions: one fewer test after the resolved_python_interpreter
      test removal net of the graph.py test rename/consolidation, and
      fewer owned mutants after rings.py/tickets_bound.py/model.py lost
      surface).
    - `tools/run_serial_compat.py` (read-only recheck): `"ok": true`,
      0 failures/errors/skipped over 14 sentinels -- the regenerated
      manifest is self-consistent.
    - `install.py --dry-run`: exit 0, planned entries: 319, renders the
      full user-scope plan (skills, role agents, host configs,
      instruction blocks/imports, receipt) with no error.
    - `git diff --check`: exit 0, no whitespace errors.
    - Comprehensive scoped run over every changed source file
      (`tools/run_tests.py --scope <all 34 changed .py/.md/.json paths,
      comma-separated>`): 70 modules, 1884 tests, 0 failures, 0 errors,
      4 skipped (the 4 skips are pre-existing platform skips, e.g.
      Windows venv symlink privilege -- unrelated to this ticket).
      This is the broadest scoped selection `run_tests.py --scope`
      produced (tickets.py's facade touches nearly every ticket-family
      test); it is not the full `unittest discover` suite, which craft.md
      reserves for the gate.

Deviations from the spec's literal text, both evidence-backed (see above
for full detail):
  a. installer/application.py:333-338 / presentation.py:124 "unreachable
     `manage_host_surfaces=False` branch": NOT deleted. It is unreachable
     from *production* `build_plan()` (confirmed: `if scope != "user":
     raise` refuses project-scope before any Plan is built), but it is a
     live, deliberate, currently-used test-isolation lever in
     tests/test_installer.py -- three hand-built `Plan(...,
     manage_host_surfaces=False)` fixtures that isolate frontend-plan
     -application testing from the ~80-line host-surface write block,
     without needing to populate every claude_adapters/codex/grok/config
     field those tests aren't about. Deleting the field would force
     rework of all three tests for no behavioral gain, and the mechanism
     is a genuine consumer, not residue -- the ambiguous case Details
     names explicitly ("a consumer added since the review is a deviation
     to report, not delete"). What I did fix: the stale comment at
     application.py:333-337, which claimed "Thin project plans set
     manage_host_surfaces False" -- false today, since project-scope
     plans no longer exist at all. Corrected to state the mechanism's
     actual current shape and user (a hand-built test Plan, not a project
     plan).
  b. tools/run_report_support/model.py's SLICE_EXECUTOR filter and
     render.py's "decompose" wording: NOT deleted, per item 19 above --
     reverted after a scoped test caught the historical-data regression
     this deletion would have caused.
  c. tests/test_validate_cases/sink_contracts.py's module docstring
     ("Its third half is tools/validate.py's two remaining owned-literal
     checks...") describes content (PACK_WORKSPACE_MECHANISMS,
     friction-log-location checks) that has moved to
     validator_ownership.py/sink_law.py and is no longer in this file.
     Left as-is: the Goal's item here is specifically "dead imports", and
     the docstring inaccuracy, while real, is a scope boundary I did not
     cross without a more specific instruction to rewrite doc prose in
     this file.

Commit: all 36 changed files (35 source/test files + this progress note)
are staged for one commit; the exact hash is named in the closing
dispatch-outcome note per this ticket's instructions.
