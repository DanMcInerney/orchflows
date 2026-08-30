"""Prove a dispatch receipt's workspace authority the way a real child does.

`dispatch-receive` no longer accepts `--workspace`.  A receiver's authority
is a fact of where that receiver is standing, so it is derived from the Git
top-level of the process cwd and compared with the workspace the dispatcher
established.  A fixture therefore cannot name a tree; it has to stand in one.

Every suite that reaches an accepted receipt needs the same two moves --
carry the packet as UTF-8 bytes rather than a shell literal, and run the
command from the established checkout -- so they are owned here instead of
being spelled out once per suite.
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
    """Initialize ``path`` as a real Git top-level a receiver can prove from."""

    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "-c", "init.defaultBranch=main", "init", "--quiet"],
        cwd=str(path), capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise unittest.SkipTest(f"git init failed: {completed.stderr.strip()}")
    return path.resolve()


def receive_argv(packet_path, packet: dict, by: str, reply_to: str = "root") -> list:
    """The receipt argv for a packet carried through a UTF-8 file."""

    return [
        "dispatch-receive", "--file", str(packet_path),
        "--role", packet["role"], "--profile", packet["profile"],
        "--by", by, "--reply-to", reply_to,
    ]
