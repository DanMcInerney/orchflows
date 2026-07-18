#!/usr/bin/env python3
"""Friction logger. Stdlib-only, cross-platform (Windows + POSIX).

Reliability bar: this script must NEVER block, prompt, raise, or exit
non-zero, no matter what. Every code path funnels through ``main``'s
broad ``except Exception`` so an internal failure is silent and the
process still exits 0. Prints exactly one line, ``friction logged``, on
success; nothing on failure.

Usage:
    python friction.py "<observed>" "<expected>" [--category C]
        [--skill S] [--ticket T] [--run R]

Log location: the main repository's ``.orch/friction/<YYYY-MM>.jsonl``
when cwd is inside a git repository or one of its linked worktrees —
a ``.git`` pointer file is resolved to the main checkout, so every
worktree shares one project log — else
``~/.orchflows/friction/<YYYY-MM>.jsonl``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

FLAG_MAP = {
    "--category": "category",
    "--skill": "skill",
    "--ticket": "ticket",
    "--run": "run",
}
SESSION_ENV_VARS = (
    "CLAUDE_SESSION_ID",
    "CLAUDE_CODE_SESSION_ID",
    "CODEX_SESSION_ID",
    "SESSION_ID",
)
GIT_REV_TIMEOUT_SECONDS = 2
MAX_WALK_UP = 200


def _parse_args(argv):
    """Return (observed, expected, options) or None when argv is malformed."""

    positional = []
    options = {"category": None, "skill": None, "ticket": None, "run": None}
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in FLAG_MAP:
            i += 1
            if i >= len(argv):
                return None
            options[FLAG_MAP[token]] = argv[i]
        elif "=" in token and token.split("=", 1)[0] in FLAG_MAP:
            key, _, value = token.partition("=")
            options[FLAG_MAP[key]] = value
        else:
            positional.append(token)
        i += 1
    if len(positional) != 2:
        return None
    return positional[0], positional[1], options


def _main_checkout_root(git_file: Path):
    """Resolve a .git pointer file (worktree/submodule) to its main root."""
    try:
        for line in git_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("gitdir:"):
                continue
            gitdir = Path(line.partition(":")[2].strip())
            if not gitdir.is_absolute():
                gitdir = git_file.parent / gitdir
            parts = gitdir.resolve().parts
            for i in range(len(parts) - 1, -1, -1):
                if parts[i] == ".git":
                    return Path(*parts[:i])
            break
    except Exception:
        pass
    return None


def _find_repo_root(start: Path):
    current = start.resolve()
    for _ in range(MAX_WALK_UP):
        marker = current / ".git"
        if marker.exists():
            if marker.is_file():
                main_root = _main_checkout_root(marker)
                if main_root is not None:
                    return main_root
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent
    return None


def _git_rev(cwd: Path):
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=GIT_REV_TIMEOUT_SECONDS,
        )
        if result.returncode == 0:
            rev = result.stdout.decode("utf-8", errors="replace").strip()
            return rev or None
    except Exception:
        pass
    return None


def _detect_host():
    env = os.environ
    if env.get("CLAUDECODE") or any(key.startswith("CLAUDE_") for key in env):
        return "claude-code"
    if any(key.startswith("CODEX_") for key in env):
        return "codex"
    return "unknown"


def _detect_session():
    for var in SESSION_ENV_VARS:
        value = os.environ.get(var)
        if value:
            return value
    return None


def _target_path(now: datetime):
    stamp = now.strftime("%Y-%m")
    repo_root = _find_repo_root(Path.cwd())
    if repo_root is not None:
        return repo_root / ".orch" / "friction" / f"{stamp}.jsonl"
    return Path.home() / ".orchflows" / "friction" / f"{stamp}.jsonl"


def _build_entry(observed, expected, options, now: datetime):
    return {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cwd": str(Path.cwd()),
        "git_rev": _git_rev(Path.cwd()),
        "host": _detect_host(),
        "session": _detect_session(),
        "category": options.get("category") or "uncategorized",
        "skill": options.get("skill"),
        "ticket": options.get("ticket"),
        "run": options.get("run"),
        "observed": observed,
        "expected": expected,
    }


def _run(argv):
    parsed = _parse_args(argv)
    if parsed is None:
        return False
    observed, expected, options = parsed
    now = datetime.now(timezone.utc)
    entry = _build_entry(observed, expected, options, now)
    path = _target_path(now)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
    return True


def main(argv=None):
    try:
        if _run(sys.argv[1:] if argv is None else argv):
            print("friction logged")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
