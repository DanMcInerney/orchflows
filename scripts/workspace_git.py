"""Git lifecycle and guarded ticket stamps for ``workspace.py``."""

from __future__ import annotations

import subprocess
from pathlib import Path

import state_root
import tickets


EXIT_ERROR = 1


class Refused(Exception):
    """What the workspace CLI will not do, with its named exit code."""

    def __init__(self, message: str, code: int = EXIT_ERROR, **detail):
        super().__init__(message)
        self.code = code
        self.detail = detail


def _git(cwd, *args: str):
    """Run git in the caller-selected tree under grade."""

    completed = subprocess.run(
        ["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
    )
    return (
        completed.returncode,
        completed.stdout.decode("utf-8", "replace"),
        completed.stderr.decode("utf-8", "replace"),
    )


def _dirty_paths(cwd, git=_git) -> list:
    """Every path ``git status`` reports, both ends of a rename included."""

    code, out, err = git(cwd, "status", "--porcelain", "-z")
    if code != 0:
        raise Refused(f"git status: {err.strip()}")
    fields = out.split("\0")
    found, index = [], 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        status, path = entry[:2], entry[3:]
        found.append(path)
        if "R" in status or "C" in status:
            if index < len(fields):
                found.append(fields[index])
                index += 1
    return found


def _graded(payload, what: str) -> dict:
    """Grade a ``tickets.py`` result by its payload, never by exit status."""

    if not isinstance(payload, dict):
        raise Refused(f"{what}: tickets.py returned no payload")
    if "error" in payload:
        raise Refused(f"{what}: {payload['error']}")
    return payload


def _locate(run: str, ticket_id: str, where=None):
    """This workspace's repository root, and its ticket in the state sink."""

    start = Path(where) if where is not None else Path.cwd()
    root = state_root.find_repo_root(start)
    if root is None:
        raise Refused(f"not inside a git repository: {start}")
    path = state_root.tickets_root() / run / f"{ticket_id}.md"
    if not path.is_file():
        raise Refused(f"ticket not found: {run}/{ticket_id}")
    return root, path


def _record(ticket_path, prior_text: str, branch: str, baseline: str) -> dict:
    """Write both stamps against the snapshot the caller read."""

    try:
        current_text = ticket_path.read_text(encoding="utf-8")
    except OSError as error:
        return {"error": f"unreadable ticket: {error}"}
    if current_text != prior_text:
        return {"error": "ticket changed since read; lost the frontmatter write race, retry"}
    try:
        updated = tickets._set_frontmatter_field(prior_text, "workspace_branch", branch)
        updated = tickets._set_frontmatter_field(updated, "workspace_baseline", baseline)
        ticket_path.write_text(updated, encoding="utf-8")
    except (OSError, ValueError) as error:
        return {"error": f"unwritable ticket: {error}"}
    return {
        "recorded": {
            "workspace_branch": branch,
            "workspace_baseline": baseline,
        }
    }


def _is_ancestor(git, ancestor: str, descendant: str) -> bool:
    code, _, err = git("merge-base", "--is-ancestor", ancestor, descendant)
    if code in (0, 1):
        return code == 0
    raise Refused(
        f"git merge-base --is-ancestor {ancestor} {descendant}: {err.strip()}"
    )
