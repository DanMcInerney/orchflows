"""The prompt's line groups: each one composes its own lines and nothing else.

The prompt these compose is the only child-facing instruction surface there
is. There is no packet, so nothing else reaches the child. Every fact it
carries is one a child cannot derive from the ticket it is handed, each
rendered exactly once, and everything the ticket or the child's own harness
already owns is left to them.

Every group below takes the one graded assignment dict and returns its own
lines; they share nothing else, which is the seam this module is cut at.
`tickets_dispatch_launch.py` owns the order they are rendered in.
"""

from __future__ import annotations

import re
import shlex
import sys
from pathlib import Path

if __package__:
    from .tickets_format import REPORT_SECTION
    from .tickets_registry import EXECUTOR_REGISTRY
else:  # pragma: no cover - direct/installed flat script path
    from tickets_format import REPORT_SECTION
    from tickets_registry import EXECUTOR_REGISTRY

SHELL_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_./:\\=-]+$")


def _command(*arguments) -> str:
    """One runnable command line, quoted for the shell the child is in."""

    values = [str(argument) for argument in arguments]
    if all(SHELL_SAFE_TOKEN.fullmatch(value) for value in values):
        return " ".join(values)
    if sys.platform == "win32":
        return "& " + " ".join("'" + value.replace("'", "''") + "'" for value in values)
    return shlex.join(values)


def _identity_line(assignment: dict) -> str:
    """The prompt's first fact: which skill, how to enter it, for which ticket."""

    skill_path = assignment.get("skill_path")
    located = (
        f"That skill's file is {skill_path}; your ticket is "
        if skill_path else "Your ticket is "
    )
    entered = assignment.get("applied_skill") or assignment["executor"]
    return (
        f"Call the Skill tool with skill `{entered}` and pass "
        "this entire prompt, verbatim, as its arguments. Already running as "
        "that skill, do the work here and never invoke it again. "
        f"{located}{assignment['ticket_path']}. Read that ticket whole: it is "
        "your assignment, and there is no other copy of it."
    )


def _contract_lines(assignment: dict) -> list:
    """Which contract binds a child whose method is somebody else's skill."""

    applied = assignment.get("applied_skill")
    if not applied:
        return []
    lines = [
        f"Your kernel contract is `{assignment['executor']}` at "
        f"{assignment.get('kernel_contract')}: read it; its Require, Never "
        "and Return bind this ticket; the applied skill is the method."
    ]
    if assignment.get("applied_skill_environment"):
        lines.append(
            "Its scripts run through the interpreter `orchflows env skill "
            f"{applied}` prints."
        )
    return lines


def _lane_lines(assignment: dict) -> list:
    """What this lane asks of the child, beyond reading its ticket."""

    script = assignment.get("executor_script")
    if script is not None:
        return [
            f"Run the script {script} with the ticket path above, and report its "
            "stdout and its exit status.",
        ]
    return [
        "Goal is the end result you answer for, Context is the evidence behind "
        "it, and Details is the planner's guidance: where it prescribes, follow "
        "it and say so; where following it would break Goal, deviate and report "
        "the deviation with its evidence.",
    ]


def _reading_lines(assignment: dict) -> list:
    """The documents beyond the ticket this child has to read to be right."""

    lines = []
    dependencies = assignment.get("dependencies") or []
    if dependencies:
        lines.append(
            "Dependency results are system-owned inputs. Read these completed "
            f"tickets' `## {REPORT_SECTION}`: " + ", ".join(dependencies)
        )
    return lines


def _files_findings(assignment: dict) -> bool:
    """Whether this lane's product is findings over fixed artifacts."""

    return bool(EXECUTOR_REGISTRY.get(
        str(assignment.get("executor") or ""), {},
    ).get("files_findings"))


def _craft_lines(assignment: dict) -> list:
    """The pack's craft, handed as a path, and the entry it is read at."""

    lines = []
    craft = assignment.get("craft")
    if craft is not None:
        lines.append(f"Read your stamped pack's craft at {craft}.")
        key = assignment.get("lens_key")
        if key:
            lines.append(
                f"You judge `{key}` artifacts: the craft's `## Lens` entry "
                f"`### {key}` is your criteria."
                if _files_findings(assignment) else
                f"You make a `{key}`: the craft's `## Lens` entry `### {key}` "
                "is what your artifact must satisfy."
            )
    lines.append(
        "The full required suite is the gate's row, never a unit's: run it "
        "here only if this ticket is the gate."
    )
    return lines


def _sheet_lines(assignment: dict) -> list:
    """One line per stamped sheet: where it is, at which digest, and how far
    it reaches into the craft the line above already handed over."""

    key = assignment.get("lens_key")
    if not key:
        return []
    lines = []
    for sheet in assignment.get("sheets") or ():
        digest = str(sheet.get("digest") or "")
        opening = (
            f"Read the sheet `{sheet['name']}` at {sheet['path']} whole "
            f"(sha256 {digest.split(':', 1)[-1]})."
        )
        lines.append(
            f"{opening} Its `## Lens` `### {key}` entry adds criteria you "
            "check beside the craft's; where it loosens the craft's, the "
            "craft wins and you report the conflict as a `sheet-defect` "
            "finding."
            if _files_findings(assignment) else
            f"{opening} Its `## Craft` binds your making; its `## Lens` "
            f"`### {key}` entry adds to the craft's `### {key}` and never "
            "loosens it."
        )
    return lines


def _friction_lines() -> list:
    """The host block's always-on friction law, restated for a forked child."""

    script = Path(__file__).with_name("friction.py").resolve()
    return [
        "After two attempts, missing input/tool/document, surprising "
        "output, skill/rule/contract gap, or workaround: log friction, "
        "then continue:",
        _command(sys.executable, script, "<what happened>",
                 "<what was expected or missing>"),
    ]


ARTIFACT_LINE_FORMS = {
    "git": "artifact: git:<full-commit-id>",
    "doc": "artifact: doc:<path>@sha256:<digest-of-the-document-bytes>",
    "evidence": "artifact: evidence:<store-id>",
}
FINDINGS_LINE = "findings: <path>"


def _return_lines(assignment: dict) -> list:
    """The commit or workspace line, and the machine lines a parent relays
    without rewriting."""

    kind = assignment.get("artifact_kind")
    if assignment.get("commits_in_place"):
        commit_lead = (
            "Commit your work inside this candidate before you close;"
            if assignment.get("git_candidate")
            else "Commit your work in the tree you are standing in before you close;"
        )
        merge_sentence = (
            ", and the landing merges the candidate, not your working tree."
            if assignment.get("git_candidate") else "."
        )
        lines = [
            f"{commit_lead} the closing "
            "note names that commit. Uncommitted bytes are not evidence" + merge_sentence,
        ]
    else:
        workspace_line = assignment.get("workspace_line")
        lines = [
            "Your stamped pack commits nothing; its workspace channel is: "
            f'"{workspace_line}"'
        ] if workspace_line else []
    if kind in ARTIFACT_LINE_FORMS:
        lines.append(
            "Print this line verbatim in your closing note, as its own line, "
            f"filled in and with no other text on it: {ARTIFACT_LINE_FORMS[kind]}"
        )
    if _files_findings(assignment):
        lines.append(
            "Print this second line verbatim beside it, naming the findings "
            f"file you wrote in this workspace: {FINDINGS_LINE}"
        )
    return lines
