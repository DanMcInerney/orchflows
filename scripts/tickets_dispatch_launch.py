"""Resolve one dispatch's role, profile, and concrete host launch binding.

Three facts meet here and nowhere else. `rules/roles.md` clause 4 resolves a
child's role -- an explicit profile wins, else the applied skill's own
declaration -- and that resolution is read by packet projection and by the
launch below through this one function, never two. The host records under
`hosts/` own the launch verb, the native launch fields, and the per-role
model and effort; nothing here restates a model name, an effort value, or
an agent identifier, and a host that adds a native field gets it carried
without this module learning its name.

What leaves here is CLI output. A launch object is never persisted and never
crosses the dispatch wire, so it is not one of `contracts/dispatch.md`'s
shapes: it is the hop the orchestrator used to transcribe by hand -- read
the host file, pick the profile row, type a model into the launch verb --
and typing the wrong model there has killed a dispatch.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

if __package__:
    from . import state_root
    from .tickets_dispatch_schema import OUTCOME_RECORD_ID, classification
    from .tickets_format import _executor_of, _parse_frontmatter, _read_utf8
    from .tickets_store import NO_SINK_ERROR, _tickets_root
else:  # pragma: no cover - direct/installed flat script path
    import state_root
    from tickets_dispatch_schema import OUTCOME_RECORD_ID, classification
    from tickets_format import _executor_of, _parse_frontmatter, _read_utf8
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
    groups = ("kernel", "engines", "workflows")
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
    through untouched and the role stays the skill's -- the packet and this
    launch have to agree on both, and they agree by asking here.
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


def launch_prompt(packet: dict, packet_file=None) -> str:
    """Where the packet is, and what every record the child files names.

    Deliberately short and deliberately not a second copy of the assignment:
    the packet carries its own prompt, and this points at it. What is
    repeated here are only `contracts/work-item.md`'s fixed executor-record
    identities, which the child needs before it has read anything.

    There is no accept step. The child's first filed record is its
    acceptance, and the identities below are what proves it: `result`
    validates the same three on every write.
    """

    where = (
        f"Your dispatch packet is the JSON document at {packet_file}."
        if packet_file is not None
        else "Your dispatch packet is the `.packet` member of the dispatch "
        "response this launch came from."
    )
    return "\n".join((
        where,
        f"Every record you file names assignment_seal {packet.get('assignment_seal')}, "
        f"dispatch_id {packet.get('dispatch_id')}, writer {packet.get('assigned_name')}, "
        f"and a fresh record id of your own; the one reserved closing identity "
        f"is {OUTCOME_RECORD_ID}.",
        "The packet's own prompt is the assignment: follow it exactly.",
    ))


def launch_spec(record, packet: dict, *, packet_file=None):
    """`(launch, failure)` -- the concrete invocation for one committed packet."""

    role = packet.get("role")
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
        "prompt": launch_prompt(packet, packet_file),
    }, None


def precheck(run: str, ticket_id: str, host):
    """`(record, failure)` before a dispatch takes any side effect.

    The ticket is read for its executor and profile alone, and the role that
    comes back is the same function packet projection will call once the
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
    "DEFAULT_HOST", "HOST_ENV_VAR", "PROFILE_ROLES", "ROLE_PROFILES",
    "binding_failure", "declared_role", "host_names", "hosts_dir",
    "launch_prompt", "launch_spec", "precheck", "resolve_host",
    "resolved_role_profile", "selected_host",
)
