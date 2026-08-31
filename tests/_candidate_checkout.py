"""Stand a fixture in a real candidate checkout.

An isolation-required item runs in a tree `workspace.py` established, and
several suites need that tree to be a real Git top-level rather than a bare
directory: the establishment grade, the join's isolation check, and the
launch fixtures all read git from inside it. Both moves -- make the checkout,
and run a block from inside it -- are owned here instead of being spelled out
once per suite.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
import subprocess
import unittest


@contextlib.contextmanager
def standing_in(path):
    """Run the enclosed block with the process cwd at ``path``."""

    previous = Path.cwd()
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(str(previous))


def git_checkout(path) -> Path:
    """Initialize ``path`` as a real Git top-level a fixture can work in."""

    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "-c", "init.defaultBranch=main", "init", "--quiet"],
        cwd=str(path), capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise unittest.SkipTest(f"git init failed: {completed.stderr.strip()}")
    return path.resolve()
