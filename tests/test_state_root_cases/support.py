"""Shared fixtures and seam helpers for state-root regression cases."""

import ast
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import scripts.friction as friction_mod
import scripts.state_root as state_root
import scripts.tickets as tickets_mod
import scripts.workspace as workspace_mod

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
STATE_ROOT_PY = SCRIPTS_DIR / "state_root.py"
TICKETS_PY = SCRIPTS_DIR / "tickets.py"
FRICTION_PY = SCRIPTS_DIR / "friction.py"
ENV_VAR = state_root.ENV_VAR

OWNED_FUNCTIONS = (
    "state_root",
    "runs_root",
    "tickets_root",
    "friction_root",
    "improvement_root",
    "find_repo_root",
    "main_checkout_root",
)
RETIRED_FUNCTIONS = ("_find_repo_root", "_main_checkout_root")

TICKET = """---
id: T1
run: testrun
status: ready
executor: orch-tdd
depends_on: []
write_scope: scratch/t1.txt
bound: 30m
---

## Objective

Test ticket.
"""


def function_names(path: Path) -> list:
    """Every function this module defines, at any nesting depth."""

    names = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)
    return names


def script_sources() -> list:
    return sorted(SCRIPTS_DIR.glob("*.py"))


def run_script(script: Path, *args, cwd: Path, sink=None, env_extra=None):
    env = dict(os.environ)
    if sink is not None:
        env[ENV_VAR] = str(sink)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd),
        env=env,
    )


def listing(root: Path) -> list:
    if not root.exists():
        return []
    return sorted(str(path.relative_to(root)) for path in root.rglob("*"))


class SinkFixture(unittest.TestCase):
    """A repository with no ``.orch/`` in it and an external sink."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        self.sink = self.tmp / "sink"

    @staticmethod
    def give_origin(repo: Path, url: str) -> None:
        (repo / ".git" / "config").write_text(
            f'[remote "origin"]\n\turl = {url}\n', encoding="utf-8"
        )

    def stamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")
