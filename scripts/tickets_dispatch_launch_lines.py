"""The prompt's line groups: each one composes its own lines and nothing else.

The prompt these compose is the only child-facing instruction surface there
is. There is no packet, so nothing else reaches the child: twelve of twelve
launches were composed by hand because the generated surfaces named neither
the ticket nor the workspace, and those hand-written prompts were the
dominant defect source. Every fact it carries is one a child cannot derive
from the ticket it is handed, each rendered exactly once, and everything the
ticket or the child's own harness already owns is left to them.

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
    """The prompt's first fact: which skill, how to enter it, for which ticket.

    The skill is entered through the host's Skill tool with this whole
    prompt as the arguments. "Apply skill X" named no mechanism, and the
    2026-09-01 transcript census (56 dispatches, 9 runs) showed the
    children splitting on the guess: 33 called the Skill tool, whose
    installed adapter forks a fresh agent of the same role, and every one
    of those forks arrived holding no assignment and refused (32 refusals,
    ~24s each) before the child re-called it with hand-typed arguments --
    18 verbatim, 6 paraphrased with lines dropped. The other 23 read the
    skill file and worked in-context. Naming the mechanism and the
    argument -- the prompt itself, verbatim -- makes the first call the
    one that works and closes the paraphrase channel. The second sentence
    is the recursion guard: the fork reads this same prompt as its
    arguments, and the installed fork-arrival clause says the same thing
    from its side (`installer.packages.FORK_ARRIVAL_CLAUSE`).

    S7(a): the skill's resolved file still rides along -- a child on a
    host without a Skill tool, or one reading the body for itself, has
    nothing left to search the filesystem for. `tickets_assignment.py`
    resolves it through the one ring resolver; `None` only for a
    hand-built assignment that skips that resolution.

    U2: the skill named here is the *applied* one when the ticket pinned
    one, because that is the skill the child is to be running -- the
    kernel verb is its contract, not its method, and `_contract_lines`
    below is where the verb is named. A ticket with no applied skill is
    the case this line was written for and is unchanged, byte for byte.
    """

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
    """Which contract binds a child whose method is somebody else's skill.

    Only an applied skill renders anything here. Entering that skill in
    place of the kernel verb answers "what do I do"; it answers none of
    what the verb owns -- the Require it may not start without, the Never
    it may not cross, and the Return whose exact lines a parent relays --
    and a child that read only the method would have no contract at all.
    The path is the flat `by-name/<verb>/SKILL.md` the installer mints
    (`installer/planning.py`), the one spelling of a canonical name that
    holds on every host.

    The environment line is the same fact `orchflows env` answers, said
    where the child will need it: an applied skill declaring its own
    `requirements.txt` runs in a private interpreter (PR #170), and the
    verified interpreter this prompt already names is the *library's*, not
    that item's. Nothing is spelled out here -- the command prints the
    path -- so the line cannot go stale against a rebuilt environment.
    """

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
    """Whether this lane's product is findings over fixed artifacts.

    The judging verb is named once, in the registry: read here so the two
    places the prompt turns on it -- which `## Lens` entry sentence it
    renders, and whether it asks for the findings line -- read one fact.
    """

    return bool(EXECUTOR_REGISTRY.get(
        str(assignment.get("executor") or ""), {},
    ).get("files_findings"))


def _craft_lines(assignment: dict) -> list:
    """The pack's craft, handed as a path, the entry it is read at, and how
    far its checks reach.

    A craft's `## Lens` carries one entry per artifact kind its domain
    produces, so handing the path alone left the child to pick which entry
    was its own. The kind the assignment resolved names the entry, in the
    direction this lane runs it: a `do` makes toward the entry and a judge
    checks against it. Nothing renders for an assignment whose kind did not
    resolve -- a child sent to `### None` would read no entry at all.

    One scope statement, whichever owns it: the craft's own quoted sentence
    where the craft declares one, else the standing gate line -- the two said
    the same law twice on every code dispatch until the quote was made the
    answer.
    """

    lines = []
    craft = assignment.get("craft")
    scope = None
    if craft is not None:
        lines.append(
            f"Read your stamped pack's craft at {craft} and run its declared "
            "stages in order through this one role."
        )
        key = assignment.get("lens_key")
        if key:
            lines.append(
                f"You judge `{key}` artifacts: the craft's `## Lens` entry "
                f"`### {key}` is your criteria."
                if _files_findings(assignment) else
                f"You make a `{key}`: the craft's `## Lens` entry `### {key}` "
                "is what your artifact must satisfy."
            )
        scope = assignment.get("craft_scope")
        if scope is not None:
            lines.append(f'That craft sets your verification scope: "{scope}"')
    if scope is None:
        lines.append(
            "The full required suite is the gate's row, never a unit's: run it "
            "here only if this ticket is the gate."
        )
    return lines


def _sheet_lines(assignment: dict) -> list:
    """One line per stamped sheet: where it is, at which digest, and how far
    it reaches into the craft the line above already handed over.

    A sheet is extra craft, so it renders here, after the craft and before
    anything else -- the child reads the pack's law and then the narrowing
    the ticket stamped on top of it, in that order. Three facts a child
    cannot derive from its ticket ride each line: the sheet's resolved path
    (the ticket carries a name, and a name is a ring search), the digest the
    assignment sealed (so a child reading different bytes than the judge
    reads has something to compare), and the direction -- a maker's `##
    Craft` binds what it makes, a judge's `## Lens` adds criteria it checks.

    The `### <kind>` key is the craft line's own: a sheet's Lens is keyed by
    artifact kind exactly as a craft's is, so a child with no resolved kind
    would be sent to `### None` in both files at once. Nothing renders for
    that assignment, for `_craft_lines`' reason.

    The tighten-only rule is stated in the direction each verb needs it. A
    maker is told the sheet never loosens the craft, because a maker
    following a looser clause would build to the wrong bar; a judge is told
    the craft wins and the conflict is its own `sheet-defect` finding,
    because a judge is the one who reports it.
    """

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
    """The host block's always-on friction law, restated for a forked child.

    U13(c), 2026-09-01: a forked child's context carries this
    repository's AGENTS.md (a project-scope CLAUDE.md import Claude
    Code does expand), which names the friction command, but not
    `templates/host-block.md`'s "Friction law (always on)" paragraph
    that states when to use it -- the user-scope CLAUDE.md import that
    carries the installed host block is not expanded into a fork's
    context (confirmed directly: a forked child's own transcript shows
    the unexpanded `@`-line where that host block's text should be,
    beside the sibling project import that did expand). Evidence run
    20260901T155911Z's five dispatched children hit at least four
    log-worthy walls -- two causal-order refusals, a no-commit
    deviation, an agent-name collision -- and logged none, while the
    root coordinator, whose interactive session does receive the
    expansion, logged all six of the run's entries (friction entry
    2026-09-01T17:53:59Z). This is the one line that earns its budget
    line by naming the law those four walls never reached.
    """

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
    without rewriting.

    Two of four workers on 2026-08-31 closed without committing inside the
    candidate, so the tree the landing merged held nothing; and the artifact
    a parent passed to the next callable rode through paraphrase because the
    child never printed one exact form. Both are said here, once, in the one
    surface a child is guaranteed to read. Three of five research children
    on 2026-09-01 skipped that same commit line for a workspace with nothing
    to commit: an adapter whose identity carries no commit (evidence-store
    alone) gets its own craft's `## Workspace` sentence instead, never the
    commit clause. A document-tree child does commit -- straight onto the
    coordinator's own branch -- so it keeps the clause, minus the sentence
    naming a candidate branch nothing was isolated to merge (finding F4).
    The clause's own noun follows `git_candidate` too: a document-tree
    lane has no candidate to be "inside", so it is told to commit in the
    tree it is standing in instead of a noun with no antecedent (A2).
    """

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
