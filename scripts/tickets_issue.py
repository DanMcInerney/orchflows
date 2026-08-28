"""Ticket creation for the sealed semantic assignment."""
from __future__ import annotations

from datetime import datetime, timezone

if __package__:
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_emission import grade_run_emission
    from .tickets_format import (
        DEFAULT_BOUND_MINUTES, GATE_ID_MARKER, REQUIRED_ISOLATION,
        ROOT_EXECUTOR, _executor_of, _extract_all, _extract_flag,
        _parse_frontmatter, _read_utf8, _remove_frontmatter_field,
        _set_frontmatter_field, _split_commas, ticket_defects,
    )
    from .tickets_issue_render import _ceiling_error, _frontmatter_list, _render_ticket
    from .tickets_store import (
        NO_SINK_ERROR, _create_text_exclusively, _identity_update,
        _run_lock, _runs_root, _segment_error, _tickets_root,
        _write_identity, _write_text_atomically,
    )
    from .tickets_root_reservation import reserve as _reserve_root
else:
    from tickets_admission import ADMISSION_PENDING
    from tickets_emission import grade_run_emission
    from tickets_format import (
        DEFAULT_BOUND_MINUTES, GATE_ID_MARKER, REQUIRED_ISOLATION,
        ROOT_EXECUTOR, _executor_of, _extract_all, _extract_flag,
        _parse_frontmatter, _read_utf8, _remove_frontmatter_field,
        _set_frontmatter_field, _split_commas, ticket_defects,
    )
    from tickets_issue_render import _ceiling_error, _frontmatter_list, _render_ticket
    from tickets_store import (
        NO_SINK_ERROR, _create_text_exclusively, _identity_update,
        _run_lock, _runs_root, _segment_error, _tickets_root,
        _write_identity, _write_text_atomically,
    )
    from tickets_root_reservation import reserve as _reserve_root

NEW_USAGE = (
    "new <run> <id> --executor E --goal TEXT --context TEXT "
    "[--suggested-file PATH ...] [--sequence E[,E...]] [--depends-on a,b] "
    "[--bound B] [--pack P] [--profile P] [--independence gate|checker] "
    "[--isolation required|none] | new <run> [<id>] --file <path>"
)
NEW_DEFAULT_BOUND = f"{DEFAULT_BOUND_MINUTES}m"
INDEPENDENCE_VALUES = ("gate", "checker")
ISOLATION_VALUES = (REQUIRED_ISOLATION, "none")


def _pending_admission(data=None):
    del data
    return ADMISSION_PENDING


def _invalidate_assignment(text):
    data = _parse_frontmatter(text)
    root_generation = str(data.get("root_generation") or "")
    text = _set_frontmatter_field(text, "admission", ADMISSION_PENDING)
    for field in ("cut_generation", "assignment_seal"):
        text = _remove_frontmatter_field(text, field)
    if root_generation.startswith(f"root:{data.get('id')}:"):
        text = _remove_frontmatter_field(text, "root_generation")
    return text


def _distinct_gate_lenses(lenses: list) -> list:
    seen, repeated = set(), []
    for lens in lenses:
        identity = lens.casefold()
        if identity in seen and lens not in repeated:
            repeated.append(lens)
        seen.add(identity)
    if repeated:
        raise ValueError("gate review lenses must be distinct; repeated: " + ", ".join(repeated))
    return lenses


def _cmd_new(rest):
    """Create one current-format ticket, or place an already-written one."""
    args = list(rest)
    file_arg = _extract_flag(args, "--file")
    executor = _extract_flag(args, "--executor")
    sequence = _extract_flag(args, "--sequence")
    goal = _extract_flag(args, "--goal")
    context = _extract_flag(args, "--context")
    suggested = _extract_all(args, "--suggested-file")
    depends_on = _extract_flag(args, "--depends-on")
    bound = _extract_flag(args, "--bound")
    pack = _extract_flag(args, "--pack")
    profile = _extract_flag(args, "--profile")
    independence = _extract_flag(args, "--independence")
    isolation = _extract_flag(args, "--isolation")
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None:
        return {"error": f"new does not accept {stray}. usage: {NEW_USAGE}"}
    supplied = (
        ("--executor", executor), ("--sequence", sequence), ("--goal", goal),
        ("--context", context), ("--suggested-file", suggested or None),
        ("--depends-on", depends_on), ("--bound", bound), ("--pack", pack),
        ("--profile", profile), ("--independence", independence),
        ("--isolation", isolation),
    )
    if file_arg is not None:
        mixed = [name for name, value in supplied if value is not None]
        if mixed:
            return {"error": f"--file takes none of {mixed}. usage: {NEW_USAGE}"}
        if not 1 <= len(args) <= 2:
            return {"error": f"usage: {NEW_USAGE}"}
        return _place_ticket(args[0], file_arg, args[1] if len(args) == 2 else None)
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
    fields = {
        "id": ticket_id, "run": run, "status": "pending",
        "admission": ADMISSION_PENDING, "executor": executor,
        "sequence": _split_commas(sequence) or None, "pack": pack,
        "independence": independence, "depends_on": _split_commas(depends_on),
        "isolation": isolation, "bound": bound or NEW_DEFAULT_BOUND,
        "claimed_by": "", "claimed_at": "", "profile": profile,
    }
    sections = [("Goal", goal), ("Context", context)]
    if suggested:
        sections.append(("Suggested files", "\n".join(f"- {path}" for path in suggested)))
    sections.extend((("Result", ""), ("Verification", ""), ("Feedback", "[]"), ("Risks", "[]")))
    return _issue_ticket(run, ticket_id, _render_ticket(fields, sections))


def _project_file_ticket(
    run: str, text: str, declared_id=None, *, source="ticket file"
):
    """Project one unissued file exactly as ``new --file`` would persist it."""
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
    text = _set_frontmatter_field(text, "status", "pending")
    text = _invalidate_assignment(text)
    text = _set_frontmatter_field(text, "claimed_by", "")
    text = _set_frontmatter_field(text, "claimed_at", "")
    return (ticket_id, text), None


def _place_ticket(run: str, source: str, declared_id=None):
    text, failure = _read_utf8(source, "ticket file")
    if failure is not None:
        return failure
    projected, failure = _project_file_ticket(
        run, text, declared_id, source=source
    )
    if failure is not None:
        return failure
    ticket_id, text = projected
    return _issue_ticket(run, ticket_id, text)


def _issue_defects(text: str, *, issued: bool=False) -> list:
    defects = ticket_defects(text)
    data = _parse_frontmatter(text)
    if not data:
        return defects
    independence = str(data.get("independence") or "checker").strip().strip("`")
    if independence not in INDEPENDENCE_VALUES:
        defects.append(f"independence '{independence}' is not one of {list(INDEPENDENCE_VALUES)}")
    checked_by = str(data.get("checked_by") or "").strip()
    if checked_by:
        if independence == "gate" and _executor_of(data) != ROOT_EXECUTOR:
            defects.append("a non-root gate-deferred ticket cannot carry checked_by")
        elif not issued:
            defects.append("an unissued ticket cannot carry checked_by")
    return defects


def _issue_ticket(run: str, ticket_id: str, text: str):
    defects = _issue_defects(text)
    if defects:
        return {"error": f"ticket {run}/{ticket_id} is off contract: " + "; ".join(defects)}
    if GATE_ID_MARKER in ticket_id:
        return {"error": f"ticket id '{ticket_id}' is reserved for tickets.py gate"}
    root = _tickets_root()
    if root is None:
        return {"error": NO_SINK_ERROR}
    path = root / run / f"{ticket_id}.md"
    try:
        with _run_lock(run):
            if path.exists():
                return {"error": f"ticket id '{ticket_id}' is already issued in run '{run}': {path}"}
            existing = list(path.parent.glob("*.md")) if path.parent.is_dir() else []
            strict_over = _ceiling_error(
                f"ticket {run}/{ticket_id}", ticket_id, text,
                pre_generation_root=False,
            )
            over = _ceiling_error(
                f"ticket {run}/{ticket_id}", ticket_id, text,
                pre_generation_root=not existing,
            )
            if over is not None:
                return over
            if (held := grade_run_emission("new", run, path.parent, {ticket_id: text})) is not None:
                return held
            if not existing and strict_over is not None:
                runs_root = _runs_root()
                if runs_root is None:
                    return {"error": NO_SINK_ERROR}
                _, reservation_error = _reserve_root(
                    runs_root, run, ticket_id, _write_text_atomically,
                )
                if reservation_error is not None:
                    return {"error": reservation_error}
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
    "_cmd_new", "_distinct_gate_lenses", "_frontmatter_list", "_issue_defects",
    "_issue_ticket", "_place_ticket", "_project_file_ticket", "_render_ticket",
)
