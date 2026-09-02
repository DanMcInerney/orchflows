"""Ticket creation for the sealed semantic assignment."""
from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timezone

if __package__:
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_emission import grade_run_emission
    from .tickets_format import (
        DEFAULT_BOUND_MINUTES, REPORT_SECTION,
        REQUIRED_ISOLATION, _extract_flag,
        _parse_frontmatter, _remove_frontmatter_field,
        _set_frontmatter_field, _split_commas, dequote, ticket_defects,
    )
    from .tickets_issue_render import _frontmatter_list, _render_ticket
    from .tickets_store import (
        NO_SINK_ERROR, _create_text_exclusively, _identity_update,
        _run_lock, _segment_error, _tickets_root, _write_identity,
    )
else:
    from tickets_admission import ADMISSION_PENDING
    from tickets_emission import grade_run_emission
    from tickets_format import (
        DEFAULT_BOUND_MINUTES, REPORT_SECTION,
        REQUIRED_ISOLATION, _extract_flag,
        _parse_frontmatter, _remove_frontmatter_field,
        _set_frontmatter_field, _split_commas, dequote, ticket_defects,
    )
    from tickets_issue_render import _frontmatter_list, _render_ticket
    from tickets_store import (
        NO_SINK_ERROR, _create_text_exclusively, _identity_update,
        _run_lock, _segment_error, _tickets_root, _write_identity,
    )

NEW_USAGE = (
    "new <run> <id> --executor E --goal TEXT --context TEXT "
    "[--details TEXT] [--depends-on a,b] "
    "[--bound B] [--pack P] [--profile P] [--independence gate|checker] "
    "[--isolation required|none]"
)
NEW_DEFAULT_BOUND = f"{DEFAULT_BOUND_MINUTES}m"
INDEPENDENCE_VALUES = ("gate", "checker")
ISOLATION_VALUES = (REQUIRED_ISOLATION, "none")


def _pending_admission(data=None):
    del data
    return ADMISSION_PENDING


def pinned_pack_digest(pack):
    """``(digest, refusal)`` for one stamped pack name at issue time.

    Issue time is where the pin is taken, because that is the last moment
    the assignment is still a draft: from the seal onward the digest is
    what every later command compares against, so taking it later would be
    pinning whatever the pack had already become. A ticket with no pack
    pins nothing.
    """

    name = dequote(pack)
    if not name:
        return None, None
    if __package__:
        from .tickets_adapters import AdapterError, pack_digest
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_adapters import AdapterError, pack_digest
    try:
        return pack_digest(name), None
    except AdapterError as error:
        return None, {"error": f"pack '{name}' cannot be pinned: {error.detail}"}


def pinned_items(sheets, skill):
    """``(fields, refusal)`` for the ring items stamped beside the pack.

    Issue time again, and for the pack's reason above: this module is where
    a ticket's pins are taken, and `scripts/tickets_pins.py` is where the
    two new kinds are resolved, hashed, and refused -- so both minting
    commands take one pin the same way.
    """

    if __package__:
        from .tickets_pins import pin_fields
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_pins import pin_fields
    return pin_fields(sheets, skill)


def _applied_skill_refusal(skill, executor):
    """Why this `--skill` may not be the method of this verb, or None.

    Two refusals, both taken before anything is minted, because both are
    facts about the flag rather than about the ticket it would become.

    The reserved prefix is `scripts/rings.py`'s mechanical floor, said one
    door earlier. That floor refuses an `orch-` name in a *ring*, and a
    kernel verb resolves from the library, so nothing downstream would have
    stopped `--skill orch-do`: the child would have been told to enter its
    own contract as its method, reading the verb twice and the method never.

    The role is `rules/roles.md` clause 4's. The launch binding -- agent,
    model, effort -- is chosen off the verb's own declared role, so a
    planner-role skill applied on a `do` would be entered by a worker agent
    under a prompt written for the other role. The verb's requirement is
    read off the kernel skill's own frontmatter rather than tabled here,
    which is what keeps the pair from drifting into two spellings.

    Resolution here is untrusted on purpose. `pin_fields` resolves the same
    name a moment later and is the caller that *acts* on the item, so it is
    the one that spends the user's grant; a use-once token consumed twice
    in one mint would refuse the second read of the skill it had just
    admitted. This end reads one frontmatter field to decide whether the
    flag is even applicable, which is the same "report, do not act" case
    `rings.resolve`'s `trust` switch exists for.
    """

    name = dequote(skill)
    if not name:
        return None
    if __package__:
        from . import rings
        from .tickets_dispatch_launch import declared_role, manifest_role
    else:  # pragma: no cover - direct/installed flat script path
        import rings
        from tickets_dispatch_launch import declared_role, manifest_role
    if name.startswith(rings.RESERVED_PREFIX):
        return {"error": (
            f"--skill '{name}' takes the reserved '{rings.RESERVED_PREFIX}' "
            "prefix. The library's own verbs and packs are what a ticket "
            "stamps as its executor and its pack; an applied skill is the "
            "method that runs inside one, and no kernel verb is a method of "
            "itself. Name a ring skill outside "
            f"'{rings.RESERVED_PREFIX}*'."
        )}
    try:
        record = rings.resolve("skill", name, trust=False)
    except rings.RingError as error:
        return {"error": f"skill '{name}' cannot be applied: {error.detail}"}
    required = declared_role(executor)
    role = manifest_role(record["path"])
    if role != required:
        return {"error": (
            f"skill '{name}' at {record['path']} declares role "
            f"'{role or 'none'}', and {executor} launches a {required}: an "
            f"applied skill is the method one {required} runs, so it declares "
            f"`role: {required}` or it is not applicable on this verb."
        )}
    return None


def _invalidate_assignment(text):
    data = _parse_frontmatter(text)
    root_generation = str(data.get("root_generation") or "")
    text = _set_frontmatter_field(text, "admission", ADMISSION_PENDING)
    for field in ("cut_generation", "assignment_seal"):
        text = _remove_frontmatter_field(text, field)
    if root_generation.startswith(f"root:{data.get('id')}:"):
        text = _remove_frontmatter_field(text, "root_generation")
    return text


def _cmd_new(rest):
    """Create one current-format ticket."""
    args = list(rest)
    executor = _extract_flag(args, "--executor")
    goal = _extract_flag(args, "--goal")
    context = _extract_flag(args, "--context")
    details = _extract_flag(args, "--details")
    depends_on = _extract_flag(args, "--depends-on")
    bound = _extract_flag(args, "--bound")
    pack = _extract_flag(args, "--pack")
    profile = _extract_flag(args, "--profile")
    independence = _extract_flag(args, "--independence")
    isolation = _extract_flag(args, "--isolation")
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None:
        return {"error": f"new does not accept {stray}. usage: {NEW_USAGE}"}
    if len(args) != 2:
        return {"error": f"usage: {NEW_USAGE}"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    missing = [name for name, value in (("--executor", executor), ("--goal", goal), ("--context", context)) if value is None]
    if missing:
        return {"error": f"new requires {', '.join(missing)}. usage: {NEW_USAGE}"}
    for flag, value, allowed in (("--independence", independence, INDEPENDENCE_VALUES), ("--isolation", isolation, ISOLATION_VALUES)):
        if value is not None and value.strip() not in allowed:
            return {"error": f"{flag} '{value}' is not one of {list(allowed)}"}
    # Sorted here, at the one command that authors the list from a flag. Two
    # orderings of one edge set are two assignment digests, and the digest
    # cannot absorb the difference without invalidating every historical
    # seal, so the canonical order is established where the list is written.
    pinned, refusal = pinned_pack_digest(pack)
    if refusal is not None:
        return refusal
    fields = {
        "id": ticket_id, "run": run, "status": ADMISSION_PENDING,
        "admission": ADMISSION_PENDING, "executor": executor,
        "pack": pack, "pack_digest": pinned,
        "independence": independence,
        "depends_on": sorted(_split_commas(depends_on)),
        "isolation": isolation, "bound": bound or NEW_DEFAULT_BOUND,
        "profile": profile,
    }
    sections = [("Goal", goal), ("Context", context)]
    if details:
        sections.append(("Details", details))
    sections.append((REPORT_SECTION, ""))
    return _issue_ticket(run, ticket_id, _render_ticket(fields, sections))


def _project_file_ticket(
    run: str, text: str, declared_id=None, *, source="ticket file"
):
    """Project one hand-authored file exactly as issuing it would persist it.

    The one remaining caller is ``lint --file``: grading the exact pre-issue
    shape of a ticket a person wrote by hand, without writing it anywhere.
    Issuing a file this way is no longer live -- ``new`` mints from
    flags and ``do``/``judge`` mint from a goal file -- so this projection is
    now read-only in every live path.
    """
    invalid = _segment_error("run id", run)
    if invalid is not None:
        return None, invalid
    data = _parse_frontmatter(text)
    ticket_id = data.get("id") if isinstance(data.get("id"), str) else None
    if not ticket_id:
        return None, {"error": f"ticket file {source} names no 'id' in its frontmatter"}
    if "admission" in data:
        return None, {
            "error": f"ticket file {source} must omit the issue-time lifecycle field 'admission'"
        }
    invalid = _segment_error("ticket id", ticket_id)
    if invalid is not None:
        return None, invalid
    if declared_id is not None and declared_id.strip() != ticket_id.strip():
        return None, {
            "error": f"placed as '{declared_id}', but ticket file names '{ticket_id}'"
        }
    declared = data.get("run")
    if isinstance(declared, str) and declared.strip() and declared.strip() != run:
        return None, {
            "error": f"ticket file names run '{declared.strip()}', placed into run '{run}'"
        }
    text = _set_frontmatter_field(text, "run", run)
    text = _set_frontmatter_field(text, "status", ADMISSION_PENDING)
    text = _invalidate_assignment(text)
    # Issue time takes the pin, whatever the file said: a placed ticket that
    # carried its own digest would be pinning the author's claim about the
    # pack rather than the pack.
    pinned, refusal = pinned_pack_digest(data.get("pack"))
    if refusal is not None:
        return None, refusal
    text = (
        _set_frontmatter_field(text, "pack_digest", pinned)
        if pinned
        else _remove_frontmatter_field(text, "pack_digest")
    )
    # The stamped sheets and applied skill are *not* re-pinned here. This
    # projection is read-only -- `lint --file` grades the exact bytes a
    # person wrote -- so rewriting the author's pin would replace the thing
    # being graded, and the doors in `tickets_admission` already refuse a
    # pin that names nothing or has drifted.
    return (ticket_id, text), None


def _issue_defects(text: str, *, issued: bool=False) -> list:
    defects = ticket_defects(text)
    data = _parse_frontmatter(text)
    if not data:
        return defects
    independence = dequote(data.get("independence") or "checker")
    if independence not in INDEPENDENCE_VALUES:
        defects.append(f"independence '{independence}' is not one of {list(INDEPENDENCE_VALUES)}")
    return defects


def _issue_ticket(run: str, ticket_id: str, text: str, *, _lock_held: bool = False):
    """Write one ticket into the run, graded, under the run lock.

    ``_lock_held`` is the idiom `dispatch-open` and `_commit_record` already
    use: a caller that minted this id under its own hold of the run lock
    cannot take it again -- the lock is one process byte, not a counter --
    and releasing it to issue would let a second minter choose the same id.
    """

    defects = _issue_defects(text)
    if defects:
        return {"error": f"ticket {run}/{ticket_id} is off contract: " + "; ".join(defects)}
    root = _tickets_root()
    if root is None:
        return {"error": NO_SINK_ERROR}
    path = root / run / f"{ticket_id}.md"
    try:
        with (nullcontext() if _lock_held else _run_lock(run)):
            if path.exists():
                return {"error": f"ticket id '{ticket_id}' is already issued in run '{run}': {path}"}
            if (held := grade_run_emission("new", run, path.parent, {ticket_id: text})) is not None:
                return held
            identity_dir, identity, held = _identity_update(run, datetime.now(timezone.utc))
            if held is not None:
                return held
            path.parent.mkdir(parents=True, exist_ok=True)
            _create_text_exclusively(path, text)
            if identity is not None:
                identity_dir.mkdir(parents=True, exist_ok=True)
                _write_identity(identity_dir, identity)
    except FileExistsError:
        return {"error": f"ticket id '{ticket_id}' is already issued in run '{run}': {path}"}
    except OSError as error:
        path.unlink(missing_ok=True)
        return {"error": f"unwritable ticket: {error}"}
    return {"new": {"run": run, "id": ticket_id, "path": str(path), "status": _parse_frontmatter(text).get("status")}}


__all__ = (
    "INDEPENDENCE_VALUES", "ISOLATION_VALUES", "NEW_DEFAULT_BOUND", "NEW_USAGE",
    "_applied_skill_refusal", "_cmd_new", "_frontmatter_list", "_issue_defects",
    "_issue_ticket", "_project_file_ticket", "_render_ticket",
    "pinned_items", "pinned_pack_digest",
)
