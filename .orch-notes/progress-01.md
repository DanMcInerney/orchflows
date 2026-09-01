Progress note (mid-run), B1.4, U4 bootstrap-safe resolver leaf.

Done:
- Created scripts/_bootstrap.py (zero-import: pathlib only): ENV_VAR +
  ROOT (Path(__file__).resolve().parent.parent).
- scripts/state_root.py imports ENV_VAR from it (try `scripts._bootstrap`,
  except flat-sibling `_bootstrap`, matching this module family's
  existing package/flat dual-mode idiom).
- Converted every module/test that redeclared the ENV_VAR literal
  ("ORCHFLOWS_STATE_HOME") to import state_root.ENV_VAR (or, where
  importing state_root itself would be wrong -- tools/suite_check.py,
  which must watch the sink a --repo-root tree with no such module
  would resolve -- scripts._bootstrap.ENV_VAR directly). ~45 files
  touched: the P3 report list (12+ declaration sites), embedded
  subprocess-command literals, docstring/comment prose mentions, and
  three .orchflows/self-improve-delivery/*.md historical goal docs.
- Deleted tools/suite_check.py's stale bootstrap-ordering workaround
  (STATE_HOME_ENV_VAR literal + its comment); it now imports
  scripts._bootstrap directly (own-tree sibling, never the tree under
  test).
- scripts/tickets_store.py NO_SINK_ERROR now builds from state_root.ENV_VAR.
- scripts/orchflows_home.py MANAGED_IGNORES's six sink subdirectory
  names now derive from state_root.py owners: the pre-existing
  tickets_root().name plus five NEW owner constants (LOCKS_SUBPATH,
  SCRATCH_SUBPATH, WORKSPACES_SUBPATH, MUTANTS_SUBPATH, DRAFTS_SUBPATH)
  -- the four pre-existing *_root() functions were deliberately left
  spelling their literal subpath directly (not refactored to reference
  a constant), because tools/validate_support/friction.py's
  _friction_owner_tree reads friction_root()'s return expression by
  AST, matching only a literal `<root> / "name"` join; a `Name`
  reference reads as zero matches -- confirmed by first breaking it,
  then reverting and re-verifying the AST shape by hand.
- tests/test_state_root_cases/environment.py: added the one sanctioned
  witness (TestTheEnvVarNameIsThisLiteral, pins the value once,
  independent of the owner) plus a new purity check on the bootstrap
  leaf (test_the_bootstrap_leaf_imports_nothing_beyond_pathlib) since
  the old leaf-purity test's import-set assertion had to change shape
  anyway (state_root.py legitimately imports the leaf now); re-exported
  the new witness class through tests/test_state_root.py's aggregator.
- Regenerated tests/serial_compat_manifest.json (2 new tests: 2111->2113
  discovered; 1 new mutation-owner row ruled sharded-module-guard,
  matching every other <module>/import-path row's precedent) --
  confirmed byte-for-byte stable on a second --write-manifest pass.
- Fixed three residue breaks the first scoped run caught, each in a
  file this candidate didn't originally plan to touch, each a real bug
  the ticket's own grep-your-own-sites instruction anticipated:
  - installer/inventory.py's SCRIPT_NAMES and
    installer/planning_support.py's SHARED_READER_MODULES both curate
    which scripts/*.py ship to the flat bin dir / reader payload
    package; neither listed the new leaf, so an installed tree's
    state_root.py raised ModuleNotFoundError. Added "_bootstrap.py" to
    both (alphabetically first, matches the reader payload's own
    ordering comment).
  - tests/test_state_root_cases/fallback.py's synthetic flat-layout
    test built its own copy list without "_bootstrap.py"; added it.
  - tests/test_suite_check_cases/snapshot.py and
    tests/test_installer_cases/planning/runtime.py both referenced the
    now-deleted suite_check.STATE_HOME_ENV_VAR / a "cannot import"
    docstring that became false once state_root.py's own consumers
    started importing directly; updated both, simplifying the sys.path
    dance in runtime.py's test since the import now just works.
  - tests/test_live_harnesses_cases/_support.py has an explicit
    __all__ gating what `from ._support import *` re-exports; added
    "state_root" (my new import there didn't reach routing_run_cases.py
    without it).

Verification so far (all via C:\Users\danhm\.orchflows\runtime\Scripts\python.exe):
- py_compile on all 47 changed .py files: OK.
- Manual AST re-checks of both new tests (bootstrap purity, state_root
  import-set) against the real source: pass.
- tools/validate.py: exit 0 (only pre-existing, unrelated cross-tier
  WARNs; the friction_root and serial-manifest ERRORs from the first
  scoped run are gone).
- git diff HEAD --check: exit 0.
- tools/run_tests.py --scope <the 5 changed paths>: first run found 14
  failures/3 errors (all four residue classes above); after fixes,
  targeted re-runs of every module that had failed
  (tests.test_state_root, tests.test_suite_check,
  tests.test_live_harnesses, tests.test_installer, tests.test_validator,
  tests.test_validate_cases_schema) are individually green. A full
  final re-run of the whole 5-path scope is in flight now to confirm
  green together, not just individually.
- reader tests: tools/run_tests.py's affected-test mapping does not
  cover reader/ at all (confirmed via tools/affected_tests.py). Ran
  reader/tests/test_ui_cases/root_resolution.py (the file I touched)
  directly: 6/6 pass. Ran every other ACTIVE_MODULES entry from
  reader/tests/test_reader.py individually (the aggregator's own
  load_tests import of "reader.tests.test_ui_cases.workflows_compositions"
  fails: that file does not exist on disk -- pre-existing, confirmed via
  `git log -- reader/tests/test_ui_cases/workflows_compositions.py`,
  last touched by an unrelated prior commit ("W4a: retire instantiate,
  orch-slice, and join-noop-repair"), nothing to do with this ticket).
  Of the rest: 3 pre-existing failures unrelated to state_root/ENV_VAR
  (a workflow-catalog node lookup and two documentation content-hash
  checks in reader/tests/test_ui_cases/{workflows_http,
  experience_projection}.py -- neither file mentions state_root or
  ENV_VAR, and neither is in this candidate's diff, so they are
  baseline, not caused here).

Not yet done: read the final full-scope re-run to completion; write the
closing report and commit.
