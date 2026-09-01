"""Shared fixtures for the migrate-state regression seams."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
# migrate_state.py imports its siblings as `scripts.x` in-repo, falling back
# to a flat `x` beside it once installed. Neither name is importable from
# `tests/` alone, so put the repository root on the path before the module
# body runs.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "migrate_state", ROOT / "scripts" / "migrate_state.py"
)
migrate_state = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_spec and migrate_state)

from scripts import state_root, tickets  # noqa: E402  the owner of project identity

STATE_HOME_ENV_VAR = state_root.ENV_VAR
# A legacy entry: the shape the stream carried before it said which project
# an entry arose in. No `project`, no `project_source`, no
# `sink_convention` -- exactly what migration has to answer for.
LEGACY_KEYS = ("ts", "cwd", "git_rev", "host", "session",
               "category", "skill", "ticket", "run", "observed", "expected")


def legacy_entry(cwd, observed="something happened", **overrides):
    entry = {
        "ts": "2026-01-02T03:04:05Z",
        "cwd": str(cwd),
        "git_rev": "abc1234",
        "host": "claude-code",
        "session": None,
        "category": "workaround",
        "skill": None,
        "ticket": None,
        "run": None,
        "observed": observed,
        "expected": "it not to",
    }
    entry.update(overrides)
    return json.dumps(entry, ensure_ascii=False)


def make_repo(path: Path, origin=None) -> Path:
    """A directory that answers "which project" the way a checkout does.

    ``state_root.find_repo_root`` looks for ``.git`` and ``tickets.py``
    reads ``origin`` out of ``.git/config``; neither shells out to git, so
    a real repository is not needed to exercise either.
    """

    (path / ".git").mkdir(parents=True, exist_ok=True)
    config = '[core]\n\trepositoryformatversion = 0\n'
    if origin is not None:
        config += f'[remote "origin"]\n\turl = {origin}\n'
    (path / ".git" / "config").write_text(config, encoding="utf-8")
    return path


def write(path: Path, text: str) -> Path:
    """``Path.write_text`` takes no ``newline`` before 3.10, and the floor
    here is 3.9; these fixtures are byte-compared, so the line ending has to
    be the same one on every platform."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return path


def tree_state(root: Path):
    """Every file under ``root`` by relative path -> (sha256, size, mtime_ns).

    mtime is part of the identity on purpose: criterion 2 is that a source
    is untouched, and a tool that rewrote a file with identical bytes would
    still be a tool that wrote to a source.
    """

    if not root.exists():
        return {}
    state = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        info = path.stat()
        state[str(path.relative_to(root))] = (
            hashlib.sha256(data).hexdigest(), info.st_size, info.st_mtime_ns
        )
    return state


def sink_bytes(root: Path):
    """Every file under ``root`` by relative path -> bytes. mtime is excluded:
    ``shutil.copy2`` carries a source's mtime across, so a destination's
    timestamps say nothing about whether a second run wrote anything."""

    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def lines_of(path: Path):
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class MigrationCase(unittest.TestCase):
    """A temporary home, a sink inside it, and sources built per test."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="orchflows-migrate-")
        self.addCleanup(self._tmp.cleanup)
        self.home = Path(self._tmp.name).resolve()
        self.sink = self.home / "sink"
        previous = os.environ.get(STATE_HOME_ENV_VAR)
        os.environ[STATE_HOME_ENV_VAR] = str(self.sink)

        def restore():
            if previous is None:
                os.environ.pop(STATE_HOME_ENV_VAR, None)
            else:
                os.environ[STATE_HOME_ENV_VAR] = previous

        self.addCleanup(restore)

    def migrate(self, *roots, dry_run=False):
        argv = []
        for root in roots:
            argv += ["--from", str(root)]
        if dry_run:
            argv.append("--dry-run")
        result = migrate_state.run(argv)
        self.assertNotIn("error", result, result)
        return result["migrate_state"]

    def source_root(self, repo_name, origin=None):
        """A ``<repo>/.orch`` in its own checkout, the shape being migrated."""

        repo = make_repo(self.home / repo_name, origin=origin)
        root = repo / ".orch"
        root.mkdir(parents=True, exist_ok=True)
        return root
