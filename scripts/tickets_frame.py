"""The durable call stack: one frame per workflow invocation.

A frame is the ticket a workflow opens for itself. Its sealed Goal says what
that invocation is for, its `parent` hangs it under the call that made it --
so the ticket tree is the call tree -- and its `## Report` is the driver's
journal: one appended line per wave, re-read at the start of the next one.
That last part is the point. The common failure of a prose driver is not
death but degradation: a session whose context compacts mid-workflow
paraphrases the verbatim lines it was trusted to relay, and no crash fires.
Waves are pull-based for the living driver too, and this is what they pull
from.

A frame carries no executor and no standard, because nothing dispatches it: the
orchestrator is a session, not a child. It carries no arbitrating lease for
the same reason -- its driver is singular by construction, so an expiry could
only end a journal somebody is still writing. What ends a frame's attempt is
`frame-close`. The attempt exists at all because the journal rides the
ordinary `result` command, which is fenced to one.

`frame-close` is a recording act rather than a launch, and it refuses one
thing: a close over two or more `do` children whose subtree holds no judge
and whose journal states no `unjudged: <reason>`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

if __package__:
    from . import rings
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_attempts import OUTCOME_RECORD_ID
    from .tickets_bound import parse_bound
    from .tickets_mint import (
        DO_EXECUTOR, JUDGE_EXECUTOR, _context, _mint, _run_dir, _sealed_root,
    )
    from .tickets_format import (
        FRAME_MARKER, REPORT_SECTION, TERMINAL_STATES, _executor_of,
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        _section_body, _sections, declared_parent, done_defects, is_frame,
        lease_of, parse_canonical_json, parse_done, unjudged_reason,
    )
    from .tickets_issue import NEW_DEFAULT_BOUND
    from .tickets_join import JOIN_STATUSES, _cmd_dispatch_join
    from .tickets_lifecycle import _cmd_ready
    from .tickets_outcome import _cmd_dispatch_outcome
    from .tickets_project import recorded_project
    from .tickets_result import (
        RESULT_ATTRIBUTION_PREFIX, _append_event, _cmd_result,
    )
    from .tickets_shape_line import (
        SHAPE_PREFIX, SHAPE_RECORD_ID, SHAPE_USAGE, journal_shape,
        shape_for, shape_record,
    )
    from .tickets_store import (
        NO_SINK_ERROR, UTC_STAMP, _run_lock, _same_project, _segment_error,
        _tickets_root, _writer_identity, segment_refusal,
    )
else:  # pragma: no cover - direct/installed flat script path
    import rings
    from tickets_admission import ADMISSION_PENDING
    from tickets_attempts import OUTCOME_RECORD_ID
    from tickets_bound import parse_bound
    from tickets_mint import (
        DO_EXECUTOR, JUDGE_EXECUTOR, _context, _mint, _run_dir, _sealed_root,
    )
    from tickets_format import (
        FRAME_MARKER, REPORT_SECTION, TERMINAL_STATES, _executor_of,
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        _section_body, _sections, declared_parent, done_defects, is_frame,
        lease_of, parse_canonical_json, parse_done, unjudged_reason,
    )
    from tickets_issue import NEW_DEFAULT_BOUND
    from tickets_join import JOIN_STATUSES, _cmd_dispatch_join
    from tickets_lifecycle import _cmd_ready
    from tickets_outcome import _cmd_dispatch_outcome
    from tickets_project import recorded_project
    from tickets_result import (
        RESULT_ATTRIBUTION_PREFIX, _append_event, _cmd_result,
    )
    from tickets_shape_line import (
        SHAPE_PREFIX, SHAPE_RECORD_ID, SHAPE_USAGE, journal_shape,
        shape_for, shape_record,
    )
    from tickets_store import (
        NO_SINK_ERROR, UTC_STAMP, _run_lock, _same_project, _segment_error,
        _tickets_root, _writer_identity, segment_refusal,
    )

# The four sentences a frame's driver has to hold for the whole run, printed
# by the command that opens the frame rather than copied into each workflow
# body: a paraphrase per body is a chance for each to drift with no way for a
# reader to tell which wording was the law.
FRAME_LAW = (
    "Before each call, re-read this frame's `## Report` and its children's "
    "states.",
    "After each call, append the decision with `tickets.py result <run> "
    "<frame> --by <frame>`; keep every returned `artifact:` and `findings:` "
    "line verbatim and hand the line itself to the next goal file.",
    "Close with `tickets.py frame-close <run> <frame> --done <command>` run "
    "outside the children; a close over two or more `do` children needs a "
    "judging child or an `unjudged: <reason>` line.",
    "Judge once, at the end: a unit lands on its own `done`, and after "
    "the last wave one judging child reads the joined tip with every "
    "unit's artifact together; its blocking findings get one bounded "
    "repair, then the close gate.",
)

FRAME_OPEN_USAGE = (
    "frame-open <run> --goal-file F [--details-file D] [--parent ID] "
    "[--done <canonical-json>] [--bound B] [--workflow NAME] "
    f"[{SHAPE_USAGE}]"
)
FRAME_CLOSE_USAGE = (
    "frame-close <run> <id> [--status S] [--done <canonical-json>]"
)
COMMAND_FORM = "command"


def _done_module():
    if __package__:
        from . import tickets_done
    else:  # pragma: no cover - direct/installed flat script path
        import tickets_done
    return tickets_done


def _frame_fields(run: str, parent, done, bound: str) -> dict:
    """The frontmatter one frame carries: the marker, and no standard binding."""

    return {
        "run": run, "status": ADMISSION_PENDING, "admission": ADMISSION_PENDING,
        "frame": FRAME_MARKER,
        "parent": parent or None,
        "isolation": "none", "bound": bound,
        "done": done,
    }


def _cmd_frame_open(rest):
    """Mint one frame, seal its goal, and open the attempt its journal rides."""

    args = list(rest)
    goal_file = _extract_flag(args, "--goal-file")
    details_file = _extract_flag(args, "--details-file")
    parent = _extract_flag(args, "--parent")
    done = _extract_flag(args, "--done")
    bound = _extract_flag(args, "--bound") or NEW_DEFAULT_BOUND
    workflow = _extract_flag(args, "--workflow")
    shape = _extract_flag(args, "--shape")
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None:
        return {"error": f"frame-open does not accept {stray}. usage: {FRAME_OPEN_USAGE}"}
    if len(args) != 1 or not goal_file:
        return {"error": f"usage: {FRAME_OPEN_USAGE}"}
    run = args[0]
    for kind, value in [("run id", run)] + ([("ticket id", parent)] if parent else []):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    refusal = _done_refusal(done)
    if refusal is not None:
        return refusal
    plan, refusal = shape_for(shape, workflow, parent)
    if refusal is not None:
        return refusal
    workflow_path, refusal = _workflow_path(workflow)
    if refusal is not None:
        return refusal
    goal, failure = _read_utf8(goal_file, "goal file")
    if failure is not None:
        return failure
    if not goal.strip():
        return {"error": f"goal file {goal_file} is empty; Goal is one observable end result"}
    details = None
    if details_file is not None:
        details, failure = _read_utf8(details_file, "details file")
        if failure is not None:
            return failure
    run_dir, failure = _run_dir(run)
    if failure is not None:
        return failure
    sections = [("Goal", goal.strip()), ("Context", _context(parent, None))]
    if (details or "").strip():
        sections.append(("Details", details.strip()))
    sections.append((REPORT_SECTION, ""))
    with _run_lock(run):
        frame_id, failure = _mint(
            run, run_dir, parent, _frame_fields(run, parent, done, bound),
            sections,
        )
    if failure is not None:
        return failure
    if not parent:
        refusal = _sealed_root(run, frame_id)
        if refusal is not None:
            return {**refusal, "id": frame_id}
    opened = _opened(run, frame_id, bound)
    if "error" in opened:
        return {**opened, "id": frame_id}
    if plan is not None:
        filed = _cmd_result([
            run, frame_id,
            "--assignment-seal", opened["assignment_seal"],
            "--dispatch-id", opened["dispatch_id"],
            "--record-id", SHAPE_RECORD_ID, "--by", frame_id,
            "--text", shape_record(plan),
        ])
        if "error" in filed:
            return {**filed, "id": frame_id}
    goal_lines = goal.strip().splitlines()
    _append_event(run, frame_id, "frame-open", {
        "workflow": workflow, "shape": plan,
        "goal_head": (goal_lines[0].strip() if goal_lines else "")[:200],
    })
    return {"frame_open": {
        "run": run, "id": frame_id, "parent": parent,
        "path": str(run_dir / f"{frame_id}.md"),
        "assignment_seal": opened["assignment_seal"],
        "dispatch_id": opened["dispatch_id"],
        "journal_by": frame_id, "shape": plan,
        "workflow_path": workflow_path,
        "law": list(FRAME_LAW),
    }}


def _workflow_path(workflow):
    """The named workflow's body, or a refusal naming the rings searched."""

    if not workflow:
        return None, None
    try:
        record = rings.resolve("workflow", workflow)
    except rings.RingError as error:
        searched = "; ".join(
            f"{ring} {root}" for ring, root in rings.item_roots("workflow")
        )
        return None, {"error": f"{error.detail}. rings searched: {searched}"}
    return str(record["path"]), None


def _opened(run: str, frame_id: str, bound: str) -> dict:
    """Promote the frame and open the one attempt its journal writes under."""

    if __package__:
        from .tickets_attempts import _cmd_dispatch_open
    else:  # pragma: no cover - direct/installed flat script path
        from tickets_attempts import _cmd_dispatch_open
    promoted = _cmd_ready(["--run", run])
    if "error" in promoted:
        return promoted
    minutes, _kind = parse_bound(bound)
    nominal = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).strftime(
        UTC_STAMP
    )
    opening = _cmd_dispatch_open([
        run, frame_id, "--by", frame_id,
        "--dispatch-id", f"{frame_id}:d1", "--lease-expires-at", nominal,
    ])
    if "error" in opening:
        return opening
    return opening["dispatch"]


def _done_refusal(done):
    """Refuse a frame predicate that is off contract or not a command."""

    if done is None:
        return None
    defects = done_defects(done)
    if defects:
        return {"error": "--done is off contract: " + "; ".join(defects)}
    if parse_done({"done": done}).get("form") != COMMAND_FORM:
        return {"error": (
            "a frame's done is a command: exit 0 is the verdict, run in the "
            "checkout the driver is standing in. A criterion no command "
            "covers is a `tickets.py judge` ticket under this frame, which "
            "brings the standard a frame does not have"
        )}
    return None


def _children(run_dir, frame_id: str) -> dict:
    """`{id: frontmatter}` for every ticket under one frame, and the frame's."""

    loaded = {}
    for path in sorted(run_dir.glob("*.md")) if run_dir.is_dir() else []:
        if path.stem == frame_id or path.stem.startswith(frame_id + "."):
            text, failure = _read_utf8(path)
            if failure is None:
                loaded[path.stem] = _parse_frontmatter(text)
    return loaded


def _census(frame_id: str, children: dict) -> dict:
    """The counts the close refuses on: do-children, and subtree judges."""

    return {
        "do": sorted(
            identifier for identifier, data in children.items()
            if declared_parent(data) == frame_id
            and _executor_of(data) == DO_EXECUTOR
        ),
        "judge": sorted(
            identifier for identifier, data in children.items()
            if identifier != frame_id
            and _executor_of(data) == JUDGE_EXECUTOR
        ),
    }


def _judgement_refusal(run: str, frame_id: str, census: dict, reason: str):
    """The close refusal, in one sentence, or ``None`` when it may proceed."""

    if len(census["do"]) < 2 or census["judge"] or reason:
        return None
    return {"error": (
        f"frame {run}/{frame_id} closes over {len(census['do'])} do-children "
        f"({', '.join(census['do'])}) and its subtree holds no judge: nobody "
        "has read those artifacts together, and this close would record that "
        "silently. Open one `tickets.py judge` under this frame over the "
        "joined tip, or write one `unjudged: <reason>` line into its journal "
        "(## Report) and close again. Nothing was recorded."
    )}


def _closing_note(census: dict, reason: str, status: str, shape: str) -> str:
    """The evidence the close appends: the plan, the census, and who read it."""

    if not census["do"]:
        read = "no do-children"
    elif census["judge"]:
        read = f"judged by {', '.join(census['judge'])}"
    elif reason:
        read = f"unjudged: {reason}"
    else:
        read = "one do-child, read by its own close"
    return (
        f"shape {shape or 'not recorded'}; frame closed {status} over "
        f"{len(census['do'])} do and {len(census['judge'])} judge children; "
        f"{read}."
    )


def _live_attempt(data: dict):
    """The frame's one open attempt, or ``None`` when it holds none."""

    raw = str(data.get("dispatch_v1") or "").strip()
    if not raw:
        return None
    try:
        state = parse_canonical_json(raw)
    except (TypeError, ValueError):
        return None
    attempts = state.get("attempts") if isinstance(state, dict) else None
    if not isinstance(attempts, list):
        return None
    live = [
        item for item in attempts
        if isinstance(item, dict) and item.get("state") == "live"
    ]
    return live[-1] if live else None


def _cmd_frame_close(rest):
    """Record what this frame's invocation became, once its gate has answered."""

    args = list(rest)
    status = _extract_flag(args, "--status")
    done = _extract_flag(args, "--done")
    stray = next((arg for arg in args if arg.startswith("-")), None)
    if stray is not None:
        return {"error": f"frame-close does not accept {stray}. usage: {FRAME_CLOSE_USAGE}"}
    if len(args) != 2:
        return {"error": f"usage: {FRAME_CLOSE_USAGE}"}
    run, frame_id = args
    invalid = segment_refusal(run, frame_id)
    if invalid is not None:
        return invalid
    root = _tickets_root()
    if root is None:
        return {"error": NO_SINK_ERROR}
    run_dir = root / run
    path = run_dir / f"{frame_id}.md"
    text, failure = _read_utf8(path, f"ticket {run}/{frame_id}")
    if failure is not None:
        return failure
    data = _parse_frontmatter(text)
    if not is_frame(data):
        return {"error": (
            f"{run}/{frame_id} is not a frame; `tickets.py land` closes a "
            "callable, and it is the command that integrates and retires a candidate"
        )}
    sealed = str(data.get("done") or "").strip()
    if sealed and (status is not None or done is not None):
        return {"error": (
            f"frame {run}/{frame_id} sealed its own done at open, and the "
            "close evaluates that one: --status and --done are for a frame "
            "that sealed none"
        )}
    if not sealed:
        chosen = [
            name for name, value in (("--status", status), ("--done", done))
            if value is not None
        ]
        if len(chosen) != 1:
            return {"error": (
                f"frame-close takes exactly one of --status <disposition> or "
                f"--done <canonical-json>; got {chosen or 'none'}. "
                f"usage: {FRAME_CLOSE_USAGE}"
            )}
    if status is not None and status not in JOIN_STATUSES:
        return {"error": (
            "the close records the disposition and it must be one of "
            + ", ".join(sorted(JOIN_STATUSES))
        )}
    refusal = _done_refusal(done or sealed or None)
    if refusal is not None:
        return refusal
    attempt = _live_attempt(data)
    if attempt is None:
        return {"error": (
            f"frame {run}/{frame_id} holds no open attempt: it was closed "
            "already, or never opened through `tickets.py frame-open`"
        )}
    census = _census(frame_id, _children(run_dir, frame_id))
    journal = _section_body(text, REPORT_SECTION)
    reason = unjudged_reason(journal)
    refusal = _judgement_refusal(run, frame_id, census, reason)
    if refusal is not None:
        return refusal
    with _run_lock(run):
        closed = _closed_under_run_lock(
            run, frame_id, path, attempt, census, reason,
            shape=journal_shape(journal),
            status=status, done=done or sealed or None,
        )
    if "frame_close" in closed:
        result = closed["frame_close"]
        done_reading = result.get("done")
        _append_event(run, frame_id, "frame-close", {
            "children": len(result["do_children"]) + len(result["judges"]),
            "judged": result["unjudged"] is None,
            "unjudged_reason": result["unjudged"],
            "done_exit": (done_reading or {}).get("exit"),
            "status": result["status"],
        })
    return closed


def _closed_under_run_lock(run, frame_id, path, attempt, census, reason,
                           *, shape, status, done):
    """Evaluate the gate, file the close, and join -- in that order."""

    tickets_done = _done_module()
    reading = None
    if done is not None:
        binding = parse_done({"done": done})
        reading, refusal = tickets_done._command_reading(binding["value"], None)
        if refusal is not None:
            return refusal
        if not reading["done"]:
            return {"error": (
                f"frame {run}/{frame_id} is not closed: its done command "
                f"`{binding['value']}` exited {reading['exit']} in the "
                "checkout this close was run from. Nothing was recorded and "
                "the frame stays open"
            ), "done": reading}
        status = "complete"
        _evidence, refusal = tickets_done.record_verification(
            path, reading, frame_id,
        )
        if refusal is not None:
            return refusal
    filed = _cmd_dispatch_outcome([
        run, frame_id, "--note", _closing_note(census, reason, status, shape),
    ], _lock_held=True)
    if "error" in filed:
        return filed
    joined = _cmd_dispatch_join([
        run, frame_id,
        "--assignment-seal", attempt["assignment_seal"],
        "--dispatch-id", attempt["dispatch_id"],
        "--outcome-record-id", OUTCOME_RECORD_ID,
        "--by", frame_id, "--status", status,
    ], _lock_held=True)
    if "error" in joined:
        return joined
    return {"frame_close": {
        "run": run, "id": frame_id, "status": joined["join"]["status"],
        "shape": shape or None,
        "do_children": census["do"], "judges": census["judge"],
        "unjudged": reason or None, "done": reading,
    }}


def _age(opened, now) -> str:
    """One frame's age, at the resolution a person judging staleness needs."""

    started = _parse_iso(opened)
    if started is None:
        return "unknown"
    minutes = max(int((now - started).total_seconds() // 60), 0)
    if minutes < 60:
        return f"{minutes}m"
    if minutes < 60 * 48:
        return f"{minutes // 60}h"
    return f"{minutes // (60 * 24)}d"


def _open_children(frame_id: str, children: dict, now) -> tuple:
    """`(open, leased)` counts for one frame's direct children."""

    direct = [
        data for identifier, data in children.items()
        if identifier != frame_id and declared_parent(data) == frame_id
    ]
    live = [data for data in direct if _live_attempt(data) is not None]
    leased = [
        data for data in live
        if (_parse_iso(_live_attempt(data).get("lease_expires_at")) or now) > now
    ]
    return (
        len([
            data for data in direct
            if str(data.get("status") or "") not in TERMINAL_STATES
        ]),
        len(leased),
    )


def _project_runs(tickets_root):
    """The run directories the invoking project owns, by the admission law."""

    writing, _workspace = _writer_identity()
    for run_dir in sorted(p for p in tickets_root.iterdir() if p.is_dir()):
        recorded = recorded_project(run_dir.name)
        if recorded is not None and _same_project(recorded, writing):
            yield run_dir


def resume_now(text):
    """The instant `resume` reads ages against: the clock, or a stated one."""

    return datetime.now(timezone.utc) if text is None else _parse_iso(text)


def _journalled(journal: str) -> bool:
    """Whether this frame's driver has written a wave down yet."""

    for line in str(journal or "").splitlines():
        text = line.strip()
        if not text or text.startswith(RESULT_ATTRIBUTION_PREFIX):
            continue
        if text.startswith(SHAPE_PREFIX):
            continue
        return True
    return False


def open_frames(now=None) -> list:
    """Every open frame of the invoking project, newest first."""

    now = datetime.now(timezone.utc) if now is None else now
    tickets_root = _tickets_root()
    rows = []
    if tickets_root is None or not tickets_root.is_dir():
        return rows
    for run_dir in _project_runs(tickets_root):
        for path in sorted(run_dir.glob("*.md")):
            text, failure = _read_utf8(path)
            if failure is not None:
                continue
            data = _parse_frontmatter(text)
            if not is_frame(data) or str(
                data.get("status") or ""
            ) in TERMINAL_STATES:
                continue
            children = _children(run_dir, path.stem)
            children_open, leased = _open_children(path.stem, children, now)
            opened = lease_of(data)[1]
            goal = _sections(text).get("Goal", "").strip().splitlines()
            rows.append({
                "run": run_dir.name, "id": path.stem, "opened_at": opened,
                "age": _age(opened, now),
                "journal": _journalled(_section_body(text, REPORT_SECTION)),
                "children": children_open, "leases": leased,
                "goal": goal[0].strip() if goal else "",
            })
    rows.sort(key=lambda row: (row["opened_at"], row["run"], row["id"]), reverse=True)
    return rows


__all__ = (
    "FRAME_CLOSE_USAGE", "FRAME_LAW", "FRAME_OPEN_USAGE", "_cmd_frame_close",
    "_cmd_frame_open", "open_frames", "resume_now",
)
