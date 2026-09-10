B1.5.1 — dispatch B1.5.1:d1 — assignment seal sha256:d4ea5869b23413190e7bb3bdc88af542c6e4d7c9a066c23bfdd7feae16430cff

Baseline: git:08d3e612a2569b085a65d540cc8216d5e6c09233. Scope: the dependency mutation seam behind PR #192 / CI run 34519268701. Standards: orch-code@sha256:8049030d7cef517e5d6dbc09a1ece092c43841521cd76665022132bded12ddf6 and orch-workflow-authoring@sha256:6ab4a4dee535a7f0ddcde8682049dac84499245f13aeaba1bb82b7b80a1258a0. Authoring owner: docs/custom-workflow-authoring.md.

### Cause and counterevidence

The initially suspected admission test was innocent: interception of its first sync showed only the temporary project 3D package, trust=untrusted, hence skipped. The project package shadows the source library package. In Ubuntu Python 3.9 CI, admission ended at 19:20:30; outside ran at 19:21:01–05.

The actual source install comes from three existing fixture callers:

- tests.test_orchflows_cli.SyncTests.test_sync_makes_a_fresh_home_ring_whole
- tests.test_orchflows_envs.EnvCommandTests.test_env_prints_the_items_own_interpreter_once_sync_built_it
- tests.test_orchflows_tooling.SyncReportTests.test_sync_reports_each_missing_tool_with_its_line_and_prunes_the_orphan

Each reaches the real source example-workflows/3d-browser-game with ('npm', 'ci'). CLI overlaps the failing outside reader in Linux CI (19:21:03–05). Raw CI npm ci does not create orchflows-node.json, so ensure requests another npm ci, which replaces the shared modules while Node readers run. The package lock serializes installers only; these Node readers do not take it.

Before editing, each caller was instrumented with this control, from the baseline candidate root. The first two calls traverse orchflows.main -> cmd_sync -> _report_dependencies; the third calls _report_dependencies. All then traverse orchflows_node.sync -> ensure -> install. The cold modules directory and attempted stamp writes were redirected to a disposable directory, and the installer was intercepted before execution. Each probe exited 0, printing the source directory and ('npm', 'ci'); no source stamp or dependency was changed.

```python
import sys, tempfile, traceback
from pathlib import Path
from unittest import mock
from scripts import orchflows_node
from tests.test_orchflows_cli import SyncTests

class Observed(BaseException):
    pass

def stop_install(directory, command):
    print('INSTALL TARGET:', directory, tuple(command), file=sys.__stdout__)
    traceback.print_stack(limit=12, file=sys.__stdout__)
    raise Observed()

with tempfile.TemporaryDirectory(prefix='cold-cli-probe-') as raw:
    with mock.patch.object(orchflows_node, 'modules_dir', return_value=Path(raw) / 'node_modules'), \
            mock.patch.object(orchflows_node, 'install', side_effect=stop_install):
        try:
            SyncTests('test_sync_makes_a_fresh_home_ring_whole').test_sync_makes_a_fresh_home_ring_whole()
        except Observed:
            pass
        else:
            raise AssertionError('No attempted install observed')
```

The other two probes substituted the named case/method above. This baseline-only probe calls the method directly; the durable regression runs each case through unittest, including the repair's new setup and cleanup.

### Repair and readings

Only test fixture inventory is isolated: pass an empty temporary library through rings.inventory's existing lib parameter. Host adapter lookup retains the real library root. No new product contract or public/private package boundary was introduced. The existing inventory, resolver, sync and preparation implementations remain the owners; no workflow method, adapter, standard, or dependency declaration changed. The offline installer helper was not reused because its fake installer could leave a false stamp in the source tree.

The new regression calls all three real cases and intercepts ensure before the stamp check. Any source-root target fails, regardless of whether a developer has a warm stamp. It also verifies each case restores rings.inventory. Its initial reading failed all three subcases on the source 3D package, command exit 1. After repair, the same test passed, command exit 0. An intermediate lib_root override was too broad and failed two cases on missing host records, exit 1; narrowing to the inventory argument resolved that without weakening the assertions.

Commands below ran through C:\Users\danhm\.orchflows\runtime\Scripts\python.exe. Long commands were supervised with subprocess.run(timeout=...) and tool-managed handles through observed completion.

| Command/control | Observed exit/result |
| --- | --- |
| Cold source-install probe, each of the three callers, timeout 120s | 0; source package + npm ci reached, installer intercepted |
| Admission inventory probe, timeout 120s | 0; untrusted project item only (first output captured; rerun printed it) |
| `-m unittest tests.test_sync_dependency_isolation -v`, timeout 120s | 1 before repair (3 subcase failures); 1 for broad-root intermediate (2 host-record failures); 0 after narrow repair |
| `npm ci --prefix example-workflows/3d-browser-game --ignore-scripts --no-audit --no-fund`, timeout 600s | 0; 8 packages installed into this isolated candidate |
| `tools/run_serial_compat.py --write-manifest`, timeout 180s | 1 for two unclassified new mutation owners; 0 after restoration rulings; 2442 identities, 458 mutation owners, same 12 sentinels |
| `tools/run_tests.py --no-cache -j 6 tests.test_sync_dependency_isolation tests.test_orchflows_cli tests.test_orchflows_envs tests.test_orchflows_tooling tests.test_orchflows_check tests.test_3d_browser_game_outside tests.test_serial_manifest tests.test_serial_compat_manifest_regression tests.test_serial_compat_hardening`, timeout 600s | 0; 9 modules, 123 tests, 0 failures/errors/skips, 10.89s wall; source stamp absent before and after |
| `tools/validate.py`, timeout 180s | 0; advisory warnings only |
| `tools/check_source_sizes.py tests/test_orchflows_cli.py tests/test_orchflows_envs.py tests/test_orchflows_tooling.py tests/test_sync_dependency_isolation.py`, timeout 60s | 0; tooling remains above the advisory band at 737 lines; its four added lines stay in the existing fixture concern, while regression grows sideways |
| `git diff --check` | 0 |

Both new mutation owners were locally ruled selected-module-boundary: the CLI patch stops via addCleanup before its temporary library is removed, and the regression's ensure patch exits its context. The regression observes restoration of the inventory identity. This is maker inspection, not independent acceptance.

The affected-tests queries exited 0 and selected CLI/check/envs/tooling. Its git-tree discovery omitted the newly staged identity, so it was named explicitly in the watched run. Including the generated manifest selected broad infrastructure; this unit ran the exact relevant manifest controls, leaving the repository gate to root. No full-suite, cross-platform, CI, live workflow-body, or gameplay acceptance is claimed here. Root owns the uncached five-check gate, independent review, installation, and publication. No agent was delegated, no library was installed, and no PR was merged or published by this ticket.

### Command accounting and gaps

Every Get-Content, git status/diff, successful rg search, tickets result/show, git add, and friction command completed with exit 0. Three exploratory rg commands exited 1 for a Windows path glob or nonexistent filename; they were corrected. Get-Item exited 1 because this fresh candidate initially lacked the inspected dependency files. The initial combined reads exceeded the output budget and were completed with bounded reads. All four friction records exited 0, including the unexpected manifest exit convention and affected-test discovery limitation. Every apply_patch call completed successfully. There are no running probes, agents, or tests.

Residual gap: reproduce the repaired revision on the full CI matrix; this candidate proves the identified mutation seam locally on Windows Python 3.13 and Node-reader concurrency only. Existing product behavior, recent-search fixes, admission assertions, installer locking, suite concurrency, and user changes remain intact.
