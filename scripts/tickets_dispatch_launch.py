"""Resolve one dispatch's launch: its host binding and its whole prompt.

Two things meet here and nowhere else. `rules/roles.md` clause 4 resolves a
child's role -- an explicit profile wins, else the applied skill's own
declaration -- through this one function, never two; and the host records
under `hosts/` own the launch verb, the native launch fields, and the
per-role model and effort. Nothing here restates a model name, an effort
value, or an agent identifier, and a host that adds a native field gets it
carried without this module learning its name.

The prompt below is the only child-facing instruction surface there is. There
is no packet, so nothing else reaches the child: twelve of twelve launches
were composed by hand because the generated surfaces named neither the ticket
nor the workspace, and those hand-written prompts were the dominant defect
source. Every fact it carries is one a child cannot derive from the ticket it
is handed, each rendered exactly once, and everything the ticket or the
child's own harness already owns is left to them.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

if __package__:
    from . import state_root
    from .tickets_dispatch_schema import OUTCOME_RECORD_ID, classification
    from .tickets_format import (
        REPORT_SECTION, _executor_of, _parse_frontmatter, _read_utf8,
    )
    from .tickets_registry import EXECUTOR_REGISTRY
    from .tickets_store import NO_SINK_ERROR, _tickets_root
else:  # pragma: no cover - direct/installed flat script path
    import state_root
    from tickets_dispatch_schema import OUTCOME_RECORD_ID, classification
    from tickets_format import (
        REPORT_SECTION, _executor_of, _parse_frontmatter, _read_utf8,
    )
    from tickets_registry import EXECUTOR_REGISTRY
    from tickets_store import NO_SINK_ERROR, _tickets_root

HOST_ENV_VAR = "ORCHFLOWS_HOST"
DEFAULT_HOST = "claude"
HOSTS_DIR_NAME = "hosts"
# The two role names `rules/roles.md` clause 2 closes, and the profile name
# each is spelled with. One mapping, both directions, because the resolution
# below turns a profile back into a role and a role back into a profile.
PROFILE_ROLES = ("planner", "worker")
ROLE_PROFILES = {f"orch-{role}": role for role in PROFILE_ROLES}
ROLE_RE = re.compile(r"^role:\s*(worker|planner|none)\s*$", re.MULTILINE)
AGENT_FIELD_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
EFFORT_SUFFIX = "_effort"
EFFORT_KEY = "effort"
SHELL_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_./:\\=-]+$")


def declared_role(executor: str):
    """The `role:` the applied skill declares, or None.

    Read off the skill's own frontmatter rather than a table here: the skill
    is the owner of what it is, and a second census in this family would go
    stale the first time a skill changed its declaration.
    """

    here = Path(__file__).resolve()
    roots = (here.parent.parent, here.parent.parent / "lib")
    groups = ("kernel", "workflows")
    for root in roots:
        for group in groups:
            path = root / "skills" / group / executor / "SKILL.md"
            text, failure = _read_utf8(path, "executor role declaration")
            if failure is not None:
                continue
            match = ROLE_RE.search(text)
            if match is not None:
                return match.group(1)
    return None


def resolved_role_profile(executor, profile):
    """`rules/roles.md` clause 4's order, as one `(role, profile)` answer.

    An explicit profile naming one of the two canonical roles wins; else the
    applied skill's own declaration decides. A profile that names neither is
    still the caller's answer for what to establish, so it is carried
    through untouched and the role stays the skill's -- the pre-open check and
    this launch have to agree on both, and they agree by asking here.
    """

    declared = declared_role(str(executor or ""))
    role = ROLE_PROFILES.get(profile) or declared
    named = profile or (f"orch-{role}" if role in PROFILE_ROLES else None)
    return role, named


def hosts_dir():
    """The directory holding the host records, source tree or installed."""

    here = Path(__file__).resolve()
    roots = [here.parent.parent, here.parent.parent / "lib"]
    try:
        roots.append(state_root.orchflows_home() / "lib")
    except (OSError, RuntimeError):  # pragma: no cover - no resolvable home
        pass
    for root in roots:
        candidate = root / HOSTS_DIR_NAME
        if candidate.is_dir() and any(candidate.glob("*.json")):
            return candidate
    return None


def host_names() -> tuple:
    """Every host this checkout or install can resolve, by its own files."""

    directory = hosts_dir()
    if directory is None:
        return ()
    return tuple(sorted(path.stem for path in directory.glob("*.json")))


def resolve_host(host):
    """`(record, failure)` for one named host record.

    The name is graded against the directory listing rather than a census
    spelled here, which also closes it: nothing outside `hosts/` can be
    opened by naming it.
    """

    name = str(host or "").strip()
    known = host_names()
    if not known:
        return None, classification(
            "host-unresolved",
            "no host records resolve from this install; reinstall to restore "
            f"the {HOSTS_DIR_NAME} directory",
        )
    if name not in known:
        return None, classification(
            "host-unresolved",
            f"'{name or '<missing>'}' is no known host; this install carries "
            f"{', '.join(known)}",
        )
    path = hosts_dir() / f"{name}.json"
    try:
        record = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return None, classification(
            "host-unresolved", f"unreadable host record {path}: {error}"
        )
    if not isinstance(record, dict) or record.get("id") != name:
        return None, classification(
            "host-unresolved", f"host record {path} does not declare id {name}"
        )
    return record, None


def selected_host(named):
    """The host a caller named, else the environment's, else the default."""

    return str(
        named or os.environ.get(HOST_ENV_VAR, "").strip() or DEFAULT_HOST
    ).strip()


def _binding(record, role):
    profile = (record.get("role_profiles") or {}).get(role)
    binding = profile.get("binding") if isinstance(profile, dict) else None
    return (profile if isinstance(profile, dict) else {}), (
        binding if isinstance(binding, dict) else {}
    )


def _agent_identity(record, role) -> str:
    """The name this host's launch verb establishes a child under.

    Derived, never mapped: the host's own `role_agent` installed-item path
    names the field its launch identifies an agent by, so a host whose
    binding carries that field answers with it and a host whose path names
    the profile answers with the profile's declared name.
    """

    profile, binding = _binding(record, role)
    template = str((record.get("installed_items") or {}).get("role_agent") or "")
    for name in AGENT_FIELD_RE.findall(template):
        if name in binding:
            return str(binding[name])
    return str(profile.get("name") or "")


def _effort(binding):
    """The binding's effort, under whichever name this host spells it."""

    if EFFORT_KEY in binding:
        return binding[EFFORT_KEY]
    named = sorted(key for key in binding if key.endswith(EFFORT_SUFFIX))
    return binding[named[0]] if len(named) == 1 else None


def _native_fields(record, role, binding) -> dict:
    """Every field this host's launch verb takes, filled from its own data."""

    native = tuple((record.get("launch") or {}).get("native_fields") or ())
    fields = {key: value for key, value in binding.items() if key in native}
    declared = (record.get("frontmatter") or {}).get("role_fields") or {}
    for key, template in declared.items():
        if key in native and key not in fields:
            fields[key] = str(template).format(role=role)
    return fields


def binding_failure(record, role):
    """Why this host cannot launch that role, or None.

    Every one of these is refusable before a dispatch takes its first side
    effect, which is the point of asking here first: a launch that cannot be
    resolved after the attempt is open leaves an opened attempt nobody can
    start.
    """

    host = record.get("id")
    if role not in PROFILE_ROLES:
        return classification(
            "role-unresolved",
            "the ticket's executor declares no worker or planner role, so no "
            "launch binding resolves; name profile orch-planner or profile "
            "orch-worker on the ticket (rules/roles.md clause 4)",
        )
    profile, binding = _binding(record, role)
    if not binding:
        return classification(
            "profile-unresolved", f"host '{host}' declares no {role} launch binding"
        )
    if not str((record.get("launch") or {}).get("verb") or "").strip():
        return classification(
            "launch-unresolved", f"host '{host}' declares no launch verb"
        )
    if not str(binding.get("model") or "").strip():
        return classification(
            "profile-unresolved", f"host '{host}' {role} binding names no model"
        )
    if not _agent_identity(record, role):
        return classification(
            "profile-unresolved",
            f"host '{host}' names no agent identity for {role}",
        )
    return None


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
    """

    skill_path = assignment.get("skill_path")
    located = (
        f"That skill's file is {skill_path}; your ticket is "
        if skill_path else "Your ticket is "
    )
    return (
        f"Call the Skill tool with skill `{assignment['executor']}` and pass "
        "this entire prompt, verbatim, as its arguments. Already running as "
        "that skill, do the work here and never invoke it again. "
        f"{located}{assignment['ticket_path']}. Read that ticket whole: it is "
        "your assignment, and there is no other copy of it."
    )


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


def _craft_lines(assignment: dict) -> list:
    """The pack's craft, handed as a path, and how far its checks reach.

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
        scope = assignment.get("craft_scope")
        if scope is not None:
            lines.append(f'That craft sets your verification scope: "{scope}"')
    if scope is None:
        lines.append(
            "The full required suite is the gate's row, never a unit's: run it "
            "here only if this ticket is the gate."
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
    if EXECUTOR_REGISTRY.get(
        str(assignment.get("executor") or ""), {},
    ).get("files_findings"):
        lines.append(
            "Print this second line verbatim beside it, naming the findings "
            f"file you wrote in this workspace: {FINDINGS_LINE}"
        )
    return lines


def launch_prompt(assignment: dict) -> str:
    """The one child-facing surface, filled from the graded assignment.

    Every line is a fact the child cannot derive from the ticket it is pointed
    at, rendered once. Nothing here paraphrases a contract, restates the
    ticket's own Goal and Context, or repeats what the child's harness already
    gives it. There is no accept step: the child's first filed record is its
    acceptance, and the identities below are what proves it, because `result`
    validates the same three on every write.
    """

    # Deferred like every tickets->workspace import: a flat `tickets.py`
    # call that never dispatches must not require the workspace family.
    if __package__:
        from .workspace_git import NOTES_DIR
    else:  # pragma: no cover - direct/installed flat script path
        from workspace_git import NOTES_DIR
    script = Path(__file__).with_name("tickets.py").resolve()
    run, ticket_id = assignment["run"], assignment["id"]
    identity = [
        "--assignment-seal", assignment["assignment_seal"],
        "--dispatch-id", assignment["dispatch_id"],
        "--record-id", "RECORD_ID",
        "--by", assignment["assigned_name"],
    ]
    lines = [
        _identity_line(assignment),
        *_lane_lines(assignment),
        *_reading_lines(assignment),
        f"Work in {assignment['workspace']}: change into that directory first "
        "and run every command from inside it.",
        f"Every Python command runs through this host's verified interpreter, "
        f"{sys.executable}, never a bare `python`.",
        *_craft_lines(assignment),
        "Run every check to completion in the turn it starts, with an explicit "
        "timeout longer than the check; never background a gate or a test run, "
        "kill anything you background once it is superseded, and never report "
        "a check you did not watch finish.",
        *_friction_lines(),
        f"Your assigned name is `{assignment['assigned_name']}`; use exactly it "
        "wherever a command takes --by.",
        f"Your lease expires at {assignment['lease_expires_at']}; it is absolute "
        "and is never extended.",
        f"File as you go into `## {REPORT_SECTION}`, the one channel: every "
        "write appends there, in whatever form you judge useful. RECORD_ID is a "
        "fresh identity of your own for each record, and PATH -- here and in "
        f"the close below -- is a file you write under {NOTES_DIR}/ in this "
        "workspace, the reserved scratch directory the join never grades. "
        "`--file PATH` in place of `--text TEXT` files a whole note:",
        _command(sys.executable, script, "result", run, ticket_id, *identity,
                 "--text", "TEXT"),
        *_return_lines(assignment),
        "Report what a reader would need and cannot re-derive: the exit code of "
        "every command you ran as you observed it, what you changed and why, what "
        "you deliberately did not do and why, and anything the assignment asked "
        "you to cover. The join alone sets terminal status.",
        "Close only after everything you dispatched has returned.",
        f"Close exactly once with the reserved `{OUTCOME_RECORD_ID}` note, which "
        "names no status because what this ticket became is checked at the join "
        "and never claimed here:",
        _command(sys.executable, script, "dispatch-outcome", run, ticket_id,
                 "--note-file", "PATH"),
        "A coordinator relaying a whole canonical envelope for you passes it "
        "through `--file` instead; a wrong or non-canonical envelope is "
        "refused with the exact fields and encoding it needs named.",
    ]
    return "\n".join(lines)


def launch_spec(record, assignment: dict):
    """`(launch, failure)` -- the concrete invocation for one assignment."""

    role = assignment.get("role")
    failure = binding_failure(record, role)
    if failure is not None:
        return None, failure
    _profile, binding = _binding(record, role)
    return {
        "host": record.get("id"),
        "verb": (record.get("launch") or {}).get("verb"),
        "agent": _agent_identity(record, role),
        "model": binding.get("model"),
        "effort": _effort(binding),
        "fields": _native_fields(record, role, binding),
        "prompt": launch_prompt(assignment),
    }, None


def precheck(run: str, ticket_id: str, host):
    """`(record, failure)` before a dispatch takes any side effect.

    The ticket is read for its executor and profile alone, and the role that
    comes back is the same function the assignment reading will call once the
    attempt is open -- under the caller's run lock, so the answer cannot
    move between the two.
    """

    record, failure = resolve_host(host)
    if failure is not None:
        return None, failure
    root = _tickets_root()
    if root is None:
        return None, {"error": NO_SINK_ERROR}
    text, failure = _read_utf8(root / run / f"{ticket_id}.md")
    if failure is not None:
        return None, failure
    data = _parse_frontmatter(text)
    role, _profile = resolved_role_profile(_executor_of(data), data.get("profile"))
    failure = binding_failure(record, role)
    if failure is not None:
        return None, failure
    return record, None


__all__ = (
    "ARTIFACT_LINE_FORMS", "DEFAULT_HOST", "FINDINGS_LINE",
    "HOST_ENV_VAR", "PROFILE_ROLES",
    "ROLE_PROFILES", "binding_failure", "declared_role", "host_names",
    "hosts_dir", "launch_prompt", "launch_spec", "precheck", "resolve_host",
    "resolved_role_profile", "selected_host",
)
