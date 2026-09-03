"""Prepare a workspace's tree, and report what it found, for ``workspace.py``.

A workspace whose tree declares frontend dependencies is not yet usable: the
item executed in it would spend its bound installing what the host could
have installed once. ``start`` is the one act every isolated item performs
before any other, so the install belongs here.

Two rules are the caller's to decide and not this script's. It installs from
the lockfile the tree already carries -- ``--frozen-lockfile``, so a tree is
never silently resolved to different versions than its revision names -- and
it never fetches a browser: whether one is already here is reported so the
item can plan around the answer.

Stdlib-only, Python 3.9 and up. Every subprocess call carries a ceiling.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

LOCKFILE = "pnpm-lock.yaml"
INSTALL_ARGV = ("install", "--frozen-lockfile", "--prefer-offline")
VERSION_ARGV = ("exec", "playwright", "--version")
# ten minutes for a cold install off a populated store; seconds for a version
# string, which is a process start and a print
CEILING_SECONDS = 600
VERSION_CEILING_SECONDS = 120
BROWSER_ENV_VAR = "ORCHFLOWS_BROWSER_EXECUTABLE"
CACHE_ENV_VAR = "PLAYWRIGHT_BROWSERS_PATH"
CACHE_DIRECTORY = "ms-playwright"
BROWSER_PREFIX = "chromium"


def _run(argv, cwd, env, timeout):
    """Run one prepared command in the tree, output captured, never inherited."""

    return subprocess.run(
        list(argv),
        cwd=str(cwd),
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def _frontend(top: Path, pnpm, env, run) -> str:
    """``installed``, ``skipped: <reason>`` or ``failed: <exit>``."""

    if not (top / LOCKFILE).is_file():
        return "skipped: no-lockfile"
    if pnpm is None:
        return "skipped: pnpm-missing"
    try:
        completed = run([pnpm, *INSTALL_ARGV], top, env, CEILING_SECONDS)
    except subprocess.TimeoutExpired:
        return "failed: timeout"
    except OSError as error:  # a pnpm on PATH the platform cannot launch
        return f"failed: {error.errno}"
    return "installed" if completed.returncode == 0 else f"failed: {completed.returncode}"


def _cache_root(env) -> Path:
    """Where Playwright keeps its browsers on this platform."""

    named = (env.get(CACHE_ENV_VAR) or "").strip()
    if named:
        return Path(named)
    home = Path.home()
    if sys.platform == "win32":
        local = (env.get("LOCALAPPDATA") or "").strip()
        return (Path(local) if local else home / "AppData" / "Local") / CACHE_DIRECTORY
    if sys.platform == "darwin":
        return home / "Library" / "Caches" / CACHE_DIRECTORY
    return home / ".cache" / CACHE_DIRECTORY


def _cached_browser(env) -> bool:
    """Whether a chromium build is already in the cache directory."""

    try:
        return any(
            child.name.startswith(BROWSER_PREFIX) for child in _cache_root(env).iterdir()
        )
    except OSError:  # no cache directory at all is an answer, not an error
        return False


def _browser(top: Path, pnpm, env, run, declared: bool) -> str:
    """``present``, ``missing``, or ``unknown`` -- never a fetch."""

    named = (env.get(BROWSER_ENV_VAR) or "").strip()
    if named and Path(named).exists():
        return "present"
    if pnpm is None or not declared:
        return "unknown"
    try:
        completed = run([pnpm, *VERSION_ARGV], top, env, VERSION_CEILING_SECONDS)
    except (subprocess.TimeoutExpired, OSError):
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    return "present" if _cached_browser(env) else "missing"


def prepare(top, env=None, run=_run) -> dict:
    """Install what the tree declares and report what a render check would find."""

    top = Path(top)
    env = dict(os.environ if env is None else env)
    # resolved against the PATH being passed on, never the ambient one: a
    # caller that hands this a stripped environment means it
    pnpm = shutil.which("pnpm", path=env.get("PATH"))
    declared = (top / LOCKFILE).is_file()
    return {
        "frontend": _frontend(top, pnpm, env, run),
        "playwright_browser": _browser(top, pnpm, env, run, declared),
    }
