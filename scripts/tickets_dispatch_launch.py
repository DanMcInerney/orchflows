"""Resolve one dispatch's launch: its host binding and its whole prompt.

Two things meet here and nowhere else. `rules/roles.md` clause 4 resolves a
child's role -- an explicit profile wins, else the applied skill's own
declaration -- through this one function, never two; and the host records
under `hosts/` own the launch verb, the native launch fields, and the
per-role model and effort. Nothing here restates a model name, an effort
value, or an agent identifier, and a host that adds a native field gets it
carried without this module learning its name.

What the child-facing prompt may carry, and every group of lines that carries
it, is `tickets_dispatch_launch_lines.py`'s; `launch_prompt` below is only the
order they are rendered in.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

if __package__:
    from . import state_root
    from .tickets_dispatch_launch_lines import (
        _command, _craft_lines, _friction_lines, _identity_line, _lane_lines,
        _reading_lines, _return_lines,
    )
    from .tickets_dispatch_schema import OUTCOME_RECORD_ID, classification
    from .tickets_format import (
        REPORT_SECTION, _executor_of, _parse_frontmatter, _read_utf8,
    )
    from .tickets_store import NO_SINK_ERROR, _tickets_root
else:  # pragma: no cover - direct/installed flat script path
    import state_root
    from tickets_dispatch_launch_lines import (
        _command, _craft_lines, _friction_lines, _identity_line, _lane_lines,
        _reading_lines, _return_lines,
    )
    from tickets_dispatch_schema import OUTCOME_RECORD_ID, classification
    from tickets_format import (
        REPORT_SECTION, _executor_of, _parse_frontmatter, _read_utf8,
    )
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
