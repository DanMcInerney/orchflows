"""friction.py logs to the one user-scope sink, from every repository, and
appends to it under a lock that never blocks and never fails."""
from __future__ import annotations

import ast
import contextlib
import errno
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import sysconfig
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from tests._repo_root import ROOT
# friction.py imports its resolver as `scripts.state_root` in-repo, falling
# back to a flat `state_root` beside it once installed. Neither name is
# importable from `tests/` alone, so put the repository root on the path
# before the module body runs.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FRICTION_PY = ROOT / "scripts" / "friction.py"
TICKETS_PY = ROOT / "scripts" / "tickets.py"
STATE_ROOT_PY = ROOT / "scripts" / "state_root.py"
_spec = importlib.util.spec_from_file_location(
    "friction", ROOT / "scripts" / "friction.py"
)
friction = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_spec and friction)

from scripts import state_root, tickets  # noqa: E402  the owner of project identity

STATE_HOME_ENV_VAR = state_root.ENV_VAR

# The logger's current record fields, named separately from the four project
# provenance fields so their ownership remains visible in assertions.
LOGGER_ENTRY_KEYS = {
    "ts", "cwd", "git_rev", "host", "session",
    "skill", "ticket", "run", "observed", "expected",
}
PROVENANCE_KEYS = {"project", "project_source", "workspace", "sink_convention"}
REQUIRED_ENTRY_KEYS = LOGGER_ENTRY_KEYS | PROVENANCE_KEYS


class _IsolatedRepoTestCase(unittest.TestCase):
    """Base for tests that run friction.main() against a synthetic repo root.

    Never touches the real sink — the sink env var is pointed at a
    fresh tempdir for the duration, and cwd is pinned to a repository
    inside it and restored via addCleanup even if the test body raises.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        self.sink = self.tmp / "sink"
        patcher = mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(self.sink)})
        patcher.start()
        self.addCleanup(patcher.stop)
        # A run this host declared for its own process would answer for
        # every case below that asserts an unresolved run. Popped after the
        # patch starts, so `patcher.stop` puts the caller's own back.
        os.environ.pop(friction.RUN_ENV_VAR, None)
        before = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, before)

    def _log_path(self):
        stamp = friction.datetime.now(friction.timezone.utc).strftime("%Y-%m")
        return self.sink / "friction" / f"{stamp}.jsonl"

    def _run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = friction.main(argv)
        return rc, buf.getvalue()
