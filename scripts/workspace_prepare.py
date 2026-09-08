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

try:
    from scripts import orchflows_node, orchflows_tools
except ImportError:
    import orchflows_node
    import orchflows_tools

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

    pinned = orchflows_node.lockfile_of(top)
    if pinned is None:
        unsupported = next((name for name in ("yarn.lock", "bun.lock", "bun.lockb") if (top / name).is_file()), None)
        if unsupported:
            return f"skipped: unsupported-lockfile {unsupported}"
        return "skipped: missing-lockfile" if (top / "package.json").is_file() else "skipped: no-lockfile"
    lockfile, command = pinned
    manager = shutil.which(command[0], path=env.get("PATH"))
    if manager is None:
        return f"skipped: {command[0]}-missing"
    arguments = INSTALL_ARGV if lockfile.name == LOCKFILE else command[1:]
    try:
        with orchflows_node.package_lock(top):
            completed = run([manager, *arguments], top, env, CEILING_SECONDS)
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


def _cached_browser(env):
    """Executable candidates in known Playwright Chromium layouts."""

    try:
        return [candidate for child in _cache_root(env).iterdir()
                if child.name.startswith(BROWSER_PREFIX) and child.is_dir()
                for relative in ("chrome-win/chrome.exe", "chrome-win64/chrome.exe",
                                 "chrome-linux/chrome", "chrome-linux64/chrome",
                                 "chrome-mac/Chromium.app/Contents/MacOS/Chromium",
                                 "chrome-headless-shell-linux64/headless_shell",
                                 "chrome-headless-shell-win64/headless_shell.exe")
                if (candidate := child / relative).is_file()]
    except OSError:  # no cache directory at all is an answer, not an error
        return []


def _browser(top: Path, pnpm, env, run, declared: bool) -> str:
    """``present``, ``missing``, or ``unknown`` -- never a fetch."""

    named = (env.get(BROWSER_ENV_VAR) or "").strip()
    candidates = [Path(named)] if named else _cached_browser(env)
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            completed = run([str(candidate), "--version"], top, env, VERSION_CEILING_SECONDS)
        except (subprocess.TimeoutExpired, OSError):
            continue
        if completed.returncode == 0:
            return "present"
    return "missing" if named or declared or candidates else "unknown"


def prepare(top, env=None, run=_run, *, packages=(), tools=()) -> dict:
    """Install what the tree declares and report what a render check would find."""

    top = Path(top)
    env = dict(os.environ if env is None else env)
    # resolved against the PATH being passed on, never the ambient one: a
    # caller that hands this a stripped environment means it
    pnpm = shutil.which("pnpm", path=env.get("PATH"))
    declared = orchflows_node.lockfile_of(top) is not None
    def contained(value):
        path = (top / value).resolve()
        if Path(value).is_absolute() or top.resolve() not in (path, *path.parents):
            raise ValueError(f"preparation directory must be relative and inside workspace: {value}")
        if not path.is_dir():
            raise ValueError(f"preparation directory missing: {value}")
        return path

    # Only exact caller declarations run. A nested manifest is not consent
    # to execute its install hooks or tool probes.
    package_paths = [(value, contained(value)) for value in packages]
    tool_paths = [(value, contained(value)) for value in tools]
    for value, path in tool_paths:
        if orchflows_tools.tools_of(path) is None:
            raise ValueError(f"tool preparation directory has no tools.txt declaration: {value}")
    result = {
        "frontend": _frontend(top, pnpm, env, run),
        "playwright_browser": _browser(top, pnpm, env, run, declared),
    }
    if packages:
        result["packages"] = {str(value): _frontend(path, pnpm, env, run)
                              for value, path in package_paths}
    if tools:
        result["tools"] = {str(value): orchflows_tools.check(
            path, environ=env, which=lambda name: shutil.which(name, path=env.get("PATH")),
            runner=lambda argv, timeout: _tool_probe(argv, path, env, run, timeout),
        ) for value, path in tool_paths}
    return result


def _tool_probe(argv, top, env, run, timeout):
    argv = [shutil.which(argv[0], path=env.get("PATH")) or argv[0], *argv[1:]]
    try:
        completed = run(argv, top, env, timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None, ""
    output = (completed.stdout or b"") + (completed.stderr or b"")
    return completed.returncode, output.decode(errors="replace") if isinstance(output, bytes) else output
