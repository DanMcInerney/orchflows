"""Installer receipts and conservative uninstall behavior."""

# install.py runs on every interpreter from 3.9 up -- it carries this same
# future import and guards its own optional tomllib. These tests are held to
# the same floor, so the suite runs wherever the installer it covers does.
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path, PurePosixPath
from unittest.mock import patch

import install
from tools import validate

_ENV_GUARD = patch.dict(os.environ)


def setUpModule():
    """Every test here fakes a home dir; a real ``CLAUDE_CONFIG_DIR`` or
    ``CODEX_HOME`` in the developer's environment would send user-scope writes
    outside that fake."""

    _ENV_GUARD.start()
    os.environ.pop("CLAUDE_CONFIG_DIR", None)
    os.environ.pop("CODEX_HOME", None)


_SHARED: dict = {}


def tearDownModule():
    _ENV_GUARD.stop()
    for key in ("root", "uninstall_root"):
        root = _SHARED.pop(key, None)
        if root is not None:
            # Strict, like every other removal in this suite: a root that
            # cannot be removed is a failure worth hearing, and neither shared
            # root can hold a repository, so `tree_removal.remove_repo_tree`
            # is not the owner here (see its docstring's scope clause).
            shutil.rmtree(root)


def relocated_user_install():
    """One user-scope install -- both hosts enabled, both config directories
    relocated -- applied once and shared by every test that only reads it.

    The apply is the whole cost of this module: it copies the library, every
    adapter, every agent and every script, and four tests were each paying
    for their own to read a different corner of one identical result.

    Read-only, and it has to stay that way: a test that writes into what this
    returns changes what the tests after it see. Anything that mutates its
    own install -- a reapply, an uninstall, a dry run proving nothing was
    written, a pre-seeded legacy file -- builds its own below, and the ones
    that grade *where* a surface lands unrelocated do too. Built on first use
    rather than in ``setUpModule`` so running one test costs one test.

    Returns the plan, the fake home, and the two relocated config directories.
    """

    if "value" not in _SHARED:
        root = Path(tempfile.mkdtemp(prefix="orchflows-shared-install-"))
        _SHARED["root"] = root
        home = root / "home"
        home.mkdir()
        claude_dir = root / "elsewhere" / "claude"
        claude_dir.mkdir(parents=True)
        codex_dir = root / "elsewhere" / "codex"
        codex_dir.mkdir(parents=True)
        with patch.object(install.Path, "home", return_value=home), patch.dict(
            os.environ,
            {"CLAUDE_CONFIG_DIR": str(claude_dir), "CODEX_HOME": str(codex_dir)},
        ), mock_host_clis("claude", "codex"):
            plan = install.build_plan("user", None)
            install.apply_plan(plan)
        _SHARED["value"] = (plan, home, claude_dir, codex_dir)
    return _SHARED["value"]


def relocated_user_uninstall():
    """The same install, its own copy, uninstalled once.

    Uninstall is destructive, so it cannot run over the shared read-only
    install -- but its *result* is read-only, and two tests read different
    halves of it: that Claude's adapters followed `CLAUDE_CONFIG_DIR` out of
    the removal and Codex's prompts and skills followed `CODEX_HOME`. One
    apply and one uninstall answer both.

    Returns the plan, the uninstall report, and the two config directories.
    """

    if "uninstalled" not in _SHARED:
        root = Path(tempfile.mkdtemp(prefix="orchflows-shared-uninstall-"))
        _SHARED["uninstall_root"] = root
        home = root / "home"
        home.mkdir()
        claude_dir = root / "elsewhere" / "claude"
        claude_dir.mkdir(parents=True)
        codex_dir = root / "elsewhere" / "codex"
        codex_dir.mkdir(parents=True)
        with patch.object(install.Path, "home", return_value=home), patch.dict(
            os.environ,
            {"CLAUDE_CONFIG_DIR": str(claude_dir), "CODEX_HOME": str(codex_dir)},
        ), mock_host_clis("claude", "codex"):
            plan = install.build_plan("user", None)
            install.apply_plan(plan)
            report = install.run_uninstall("user", None, dry_run=False)
        _SHARED["uninstalled"] = (plan, report, claude_dir, codex_dir)
    return _SHARED["uninstalled"]


def removed_unchanged(report: dict) -> set:
    return {
        action["path"]
        for action in report["skill_actions"]
        if action["action"] == "removed unchanged skill"
    }


def dangling_path_warnings(plan) -> list:
    """The hooks preflight's own warnings, selected by kind.

    A plan carries every true warning the run found, and which ones exist
    depends on the interpreter -- below 3.11 a codex plan also warns that
    the config merge went unparsed. Counting ``plan.warnings`` therefore
    pinned the interpreter, not the preflight; these tests mean "the hooks
    warning is here, once", so they select it and count that."""
    return [
        warning
        for warning in plan.warnings
        if "references a missing orchflows path" in warning
    ]


requires_tomllib = unittest.skipIf(
    install.tomllib is None,
    "reading back generated TOML requires tomllib (Python 3.11+); "
    "install.py guards its own use and still runs here",
)


# Spelled out rather than read off ``install``: a can-fail run against a
# revision that has no such constant must fail on behavior, not on an
# AttributeError raised in setUp. One case pins the constant to this literal.
SINK_ENV_VAR = "ORCHFLOWS_STATE_HOME"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seed_user_frontend(home: Path) -> Path:
    """Give a fake home the frontend precondition a project apply borrows."""

    destination = home / ".orchflows" / "ui"
    shutil.copytree(install.REPO_ROOT / "web" / "dist", destination)
    return destination


def mock_host_clis(*hosts: str):
    """Return a deterministic PATH lookup patch for selected host CLIs."""

    installed = set(hosts)

    def lookup(candidate: str) -> str | None:
        host = candidate.split(".", 1)[0]
        return str(Path("mock-bin") / candidate) if host in installed else None

    return patch.object(install.shutil, "which", side_effect=lookup)


# A bare filename the way a stub writes one: `search_plan.py`, never
# `scripts/search_plan.py`. A stub that spelled the path would be stale the
# day the script moved, so the bare form is the contract and this is what
# reads it.
BARE_SCRIPT_RE = re.compile(r"\b([a-z_]+\.py)\b")
