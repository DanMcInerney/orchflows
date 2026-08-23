"""Where a verdict for one tree may be stored, and what may be served back.

The memo is a deterministic-oracle memo and nothing more: it can only ever
answer "these exact five commands, through this exact interpreter, on this
exact tree, all exited 0". Anything else -- a red exit, a tree that moved
under the run, an unreadable entry -- is not an answer, so the checks run.

The directory is the unit-test runner's own gitignored runtime directory,
named from `tools/run_tests.py`'s cache path rather than restated here, so
one repository has one runtime-state location and no second name for it.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

LEAF = "required_cache"


def runtime_directory_name() -> str:
    """The gitignored runtime directory, asked of the runner that owns it."""

    from tools import run_tests

    return run_tests.CACHE_PATH.parent.name


def runtime_cache_dir(repo: Path) -> Path:
    return Path(repo) / runtime_directory_name() / LEAF


def entry_path(repo: Path, key: str) -> Path:
    return runtime_cache_dir(repo) / "{0}.json".format(key)


def servable(entry) -> bool:
    """A stored record answers only when it is a whole green run."""

    if not isinstance(entry, dict) or entry.get("exit") != 0:
        return False
    commands = entry.get("commands")
    if not isinstance(commands, list) or not commands:
        return False
    return all(
        isinstance(record, dict) and record.get("exit_status") == 0
        for record in commands
    )


def load(repo: Path, key: str):
    """The stored record for this key, or None when there is no answer."""

    try:
        entry = json.loads(entry_path(repo, key).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return entry if servable(entry) else None


def serve(entry: dict) -> dict:
    """The stored record, said again with every command marked cached."""

    served = dict(entry)
    served["commands"] = [dict(record, cached=True) for record in entry["commands"]]
    return served


def store(repo: Path, key: str, payload: dict) -> None:
    """Write one entry atomically; a memo never fails a run for its own sake."""

    path = entry_path(repo, key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=1, sort_keys=True)
        os.replace(temporary, str(path))
    except OSError:
        pass
