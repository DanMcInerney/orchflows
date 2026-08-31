"""Stand a fixture's candidate workspace up the way a dispatch does.

An isolation-required item runs in a tree `workspace.py` established, and
several suites need that tree to be a real Git top-level rather than a bare
directory: the establishment grade, the join's isolation check, and the
launch fixtures all read git from inside it. The two moves a fixture makes
-- create the checkout, and record it on the open attempt -- are owned here
instead of being spelled out once per suite.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import unittest


def record_established_workspace(ticket_path, workspace, *, strict=True) -> None:
    """Put the established tree on the ticket's live attempt.

    What `workspace.py establish` writes, for a fixture that stands the
    establishment up by hand. It goes on the attempt because that is the
    field's one owner (`contracts/dispatch.md`), so it can only be recorded
    once an attempt is open -- which is also the order the dispatch facade
    runs the two steps in.

    ``strict=False`` for a fixture standing in for the establishment inside a
    composition whose open is itself stubbed: the real verb records nothing
    when there is no attempt and still answers with the path, and a stub that
    raised there would fail the case for the stub rather than the code.
    """

    from scripts import workspace_record

    path = Path(ticket_path)
    text = path.read_text(encoding="utf-8")
    updated, recorded = workspace_record.recorded_on_attempt(text, str(workspace))
    if not recorded:
        if strict:
            raise AssertionError(f"{path} has no live attempt to record a workspace on")
        return
    path.write_text(updated, encoding="utf-8")


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
