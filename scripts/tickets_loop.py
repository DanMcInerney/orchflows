"""Arm, evaluate, and advance one loop stub without an engine.

A loop is a ticket whose frontmatter carries a canonical-JSON ``loop``
object (contracts/work-item.md). No LLM holds loop state: the ticket set
is the state, the worklog its rendered view. The driver treats a ready
loop stub as arm -> run the iteration to terminal -> evaluate -> advance,
and every command here replays after a kill.

The iteration's verb is the stub's own ``executor`` — the loop object
does not restate it. The ``done`` binding takes exactly one of two closed
forms: a deterministic command whose exit 0 is the done reading (that run
is the one outside execution closing the loop), or a frozen criterion
judged by a fresh ``orch-check`` ticket minted per iteration.
"""

from __future__ import annotations

import hashlib
import re
import shlex
import subprocess

if __package__:
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_format import (
        RESULT_BEARING_STATES, TERMINAL_STATES, _executor_of, _sections,
        _set_frontmatter_field, dequote, loop_defects, parse_loop,
        ticket_defects,
    )
    from .tickets_generations import assignment_digest
    from .tickets_issue_render import _render_ticket
    from .tickets_store import (
        NO_SINK_ERROR, TicketWriteRefused, _create_text_exclusively,
        _load_ticket, _segment_error, _tickets_root, locked_ticket_write,
    )
else:  # pragma: no cover - direct/installed flat script path
    from tickets_admission import ADMISSION_PENDING
    from tickets_format import (
        RESULT_BEARING_STATES, TERMINAL_STATES, _executor_of, _sections,
        _set_frontmatter_field, dequote, loop_defects, parse_loop,
        ticket_defects,
    )
    from tickets_generations import assignment_digest
    from tickets_issue_render import _render_ticket
    from tickets_store import (
        NO_SINK_ERROR, TicketWriteRefused, _create_text_exclusively,
        _load_ticket, _segment_error, _tickets_root, locked_ticket_write,
    )

LOOP_ARM_USAGE = "loop-arm <run> <id>"
LOOP_EVALUATE_USAGE = "loop-evaluate <run> <id>"
LOOP_ADVANCE_USAGE = "loop-advance <run> <id>"
ITERATION_RE = re.compile(r"\.iter\.(\d+)$")
DONE_TICKET_SUFFIX = ".done"
# Two consecutive terminal iterations with no result delta exit stalled
# (rules/loops.md).
STALL_WINDOW = 2


def _iterations(run_dir, loop_id):
    """(number, id, data) for every iteration ticket, ordered by number."""

    found = []
    for path in sorted(run_dir.glob(f"{loop_id}.iter.*.md")):
        stem = path.stem
        if stem.endswith(DONE_TICKET_SUFFIX):
            continue
        match = ITERATION_RE.search(stem)
        if match is None:
            continue
        loaded = _load_ticket(path)
        if "error" in loaded:
            continue
        found.append((int(match.group(1)), stem, loaded))
    return sorted(found)


def _loop_parent(run, loop_id):
    """(run_dir, data, text, loop, error) for one loop stub."""

    for kind, value in (("run id", run), ("ticket id", loop_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return None, None, None, None, invalid
    root = _tickets_root()
    if root is None:
        return None, None, None, None, {"error": NO_SINK_ERROR}
    run_dir = root / run
    path = run_dir / f"{loop_id}.md"
    if not path.is_file():
        return None, None, None, None, {"error": f"loop stub not found: {run}/{loop_id}"}
    data = _load_ticket(path)
    if "error" in data:
        return None, None, None, None, {"error": data["error"]}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return None, None, None, None, {"error": f"unreadable loop stub: {error}"}
    loop = parse_loop(data)
    if loop is None:
        return None, None, None, None, {
            "error": f"{run}/{loop_id} carries no loop object; only a loop stub is armed, evaluated, or advanced"
        }
    defects = loop_defects(data.get("loop"), _executor_of(data))
    if defects:
        return None, None, None, None, {"error": f"loop stub is off contract: " + "; ".join(defects)}
    return run_dir, data, text, loop, None


def _iteration_context(data, text, number, prior):
    """The context-packet lines one iteration receives beside the frozen
    goal: identities and decisions, never transcript prose."""

    sections = _sections(text)
    lines = [sections.get("Context", "").strip()] if sections.get("Context", "").strip() else []
    lines.append(f"- loop: iteration {number} of a bounded loop; the worklog is the state")
    done = parse_loop(data).get("done", {})
    lines.append(
        f"- done-check ({done.get('form')}): {done.get('value')}"
    )
    lines.append(f"- bound: {data.get('bound')}")
    if prior is not None:
        prior_number, prior_id, _ = prior
        lines.append(
            f"- prior iteration: {prior_id} — read its `## Result` before working; an identical retry is a defect"
        )
    return "\n\n".join(lines)


def _cmd_loop_arm(rest):
    """Instantiate the next iteration from the frozen goal + worklog tail."""

    if len(rest) != 2:
        return {"error": f"usage: {LOOP_ARM_USAGE}"}
    run, loop_id = rest
    run_dir, data, text, loop, error = _loop_parent(run, loop_id)
    if error is not None:
        return error
    if str(data.get("status")) in TERMINAL_STATES:
        return {"error": f"loop stub {run}/{loop_id} is terminal; a closed loop is not re-armed"}
    if not str(data.get("root_generation") or "").strip() or not str(data.get("assignment_seal") or "").strip():
        return {"error": f"loop stub {run}/{loop_id} is not stamped and sealed; arm follows the seal"}
    iterations = _iterations(run_dir, loop_id)
    if iterations and str(iterations[-1][2].get("status")) not in TERMINAL_STATES:
        number, ticket_id, _ = iterations[-1]
        return {"loop_arm": {"run": run, "id": loop_id, "iteration": number,
                             "ticket": ticket_id, "outcome": "replayed"}}
    number = iterations[-1][0] + 1 if iterations else 1
    ticket_id = f"{loop_id}.iter.{number}"
    prior = iterations[-1] if iterations else None
    sections = _sections(text)
    fields = {
        "id": ticket_id, "run": run, "status": "pending",
        "admission": ADMISSION_PENDING, "executor": _executor_of(data),
        "pack": dequote(data.get("pack")) or None,
        "profile": dequote(data.get("profile")) or None,
        "independence": dequote(data.get("independence")) or "checker",
        "depends_on": [],
        "isolation": dequote(data.get("isolation")) or None,
        "bound": data.get("bound"),
        "root_generation": data.get("root_generation"),
    }
    body = [
        ("Goal", sections.get("Goal", "").strip()),
        ("Context", _iteration_context(data, text, number, prior)),
    ]
    if sections.get("Suggested files", "").strip():
        body.append(("Suggested files", sections["Suggested files"].strip()))
    body += [("Result", ""), ("Verification", ""), ("Feedback", "[]"), ("Risks", "[]")]
    rendered = _render_ticket(fields, body)
    cut_generation = str(data.get("cut_generation") or "").strip()
    if cut_generation:
        rendered = _set_frontmatter_field(rendered, "cut_generation", cut_generation)
    rendered = _set_frontmatter_field(
        rendered, "assignment_seal", assignment_digest(ticket_id, rendered)
    )
    defects = ticket_defects(rendered)
    if defects:
        return {"error": f"iteration {ticket_id} is off contract: " + "; ".join(defects)}
    try:
        with locked_ticket_write(run, ticket_id):
            path = run_dir / f"{ticket_id}.md"
            if path.exists():
                return {"loop_arm": {"run": run, "id": loop_id, "iteration": number,
                                     "ticket": ticket_id, "outcome": "replayed"}}
            _create_text_exclusively(path, rendered)
    except TicketWriteRefused as refused:
        return refused.payload
    except OSError as error:
        return {"error": f"unable to create iteration: {error}"}
    return {"loop_arm": {"run": run, "id": loop_id, "iteration": number,
                         "ticket": ticket_id, "outcome": "created"}}


def _evaluate(run, loop_id, run_dir, data, text, loop):
    """The done reading for the latest terminal iteration.

    Deterministic form: run the frozen command; exit 0 is done. Check
    form: mint one fresh `orch-check` ticket judging the frozen
    criterion; a live one reports pending, a terminal one reports its
    verdict.
    """

    iterations = _iterations(run_dir, loop_id)
    if not iterations:
        return {"error": f"loop stub {run}/{loop_id} has no iteration; arm first"}
    number, iteration_id, iteration = iterations[-1]
    if str(iteration.get("status")) not in TERMINAL_STATES:
        return {"error": f"iteration {iteration_id} is not terminal; evaluate follows the landed iteration"}
    done = loop["done"]
    if done["form"] == "command":
        argv = shlex.split(str(done["value"]))
        if not argv:
            return {"error": "loop done command is empty"}
        try:
            completed = subprocess.run(argv, capture_output=True, text=True, timeout=1800)
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            return {"error": f"loop done command failed to run: {error}"}
        reading = hashlib.sha256(
            (completed.stdout + completed.stderr).encode("utf-8", "replace")
        ).hexdigest()
        return {"loop_evaluate": {
            "run": run, "id": loop_id, "iteration": number, "form": "command",
            "done": completed.returncode == 0, "exit": completed.returncode,
            "output_sha256": reading,
        }}
    check_id = f"{iteration_id}{DONE_TICKET_SUFFIX}"
    check_path = run_dir / f"{check_id}.md"
    if not check_path.is_file():
        fields = {
            "id": check_id, "run": run, "status": "pending",
            "admission": ADMISSION_PENDING, "executor": "orch-check",
            "pack": dequote(data.get("pack")) or None,
            "independence": "gate", "depends_on": [iteration_id],
            "isolation": "none", "bound": data.get("bound"),
            "root_generation": data.get("root_generation"),
            "review_kind": "verify", "review_order": 0,
        }
        goal = (
            f"Judge the loop done-check for `{loop_id}` after iteration {number}: "
            f"{done['value']} Verify against the loop Goal and `{iteration_id}`'s "
            "recorded result; begin the verdict with exactly `PASS:`, `FAIL:`, or `UNVERIFIED:`."
        )
        sections = [
            ("Goal", goal),
            ("Context", f"- loop stub: {loop_id}\n- iteration: {iteration_id}"),
            ("Result", ""), ("Verification", ""), ("Feedback", "[]"), ("Risks", "[]"),
        ]
        rendered = _render_ticket(fields, sections)
        cut_generation = str(data.get("cut_generation") or "").strip()
        if cut_generation:
            rendered = _set_frontmatter_field(rendered, "cut_generation", cut_generation)
        rendered = _set_frontmatter_field(
            rendered, "assignment_seal", assignment_digest(check_id, rendered)
        )
        defects = ticket_defects(rendered)
        if defects:
            return {"error": f"done-check {check_id} is off contract: " + "; ".join(defects)}
        try:
            with locked_ticket_write(run, check_id):
                if not check_path.exists():
                    _create_text_exclusively(check_path, rendered)
        except TicketWriteRefused as refused:
            return refused.payload
        except OSError as error:
            return {"error": f"unable to create done-check: {error}"}
        return {"loop_evaluate": {"run": run, "id": loop_id, "iteration": number,
                                  "form": "check", "pending": check_id, "outcome": "created"}}
    check = _load_ticket(check_path)
    if "error" in check:
        return {"error": check["error"]}
    if str(check.get("status")) not in TERMINAL_STATES:
        return {"loop_evaluate": {"run": run, "id": loop_id, "iteration": number,
                                  "form": "check", "pending": check_id, "outcome": "live"}}
    try:
        verdict_text = _sections(check_path.read_text(encoding="utf-8")).get("Verification", "")
    except (OSError, UnicodeDecodeError) as error:
        return {"error": f"unreadable done-check: {error}"}
    stripped = verdict_text.strip()
    if stripped.startswith("PASS"):
        verdict = True
    elif stripped.startswith("FAIL"):
        verdict = False
    else:
        return {"error": f"done-check {check_id} closed without a PASS/FAIL verdict; the loop cannot read done off it"}
    return {"loop_evaluate": {"run": run, "id": loop_id, "iteration": number,
                              "form": "check", "done": verdict, "verdict_ticket": check_id}}


def _cmd_loop_evaluate(rest):
    if len(rest) != 2:
        return {"error": f"usage: {LOOP_EVALUATE_USAGE}"}
    run, loop_id = rest
    run_dir, data, text, loop, error = _loop_parent(run, loop_id)
    if error is not None:
        return error
    return _evaluate(run, loop_id, run_dir, data, text, loop)


def _result_reading(run_dir, iteration_id):
    try:
        text = (run_dir / f"{iteration_id}.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return _sections(text).get("Result", "").strip()


def _cmd_loop_advance(rest):
    """Re-arm, or close the stub complete | limited | stalled.

    The transition writes go through ``set-status`` — the one lifecycle
    door — so advance replays idempotently after a kill: a closed stub
    reports its terminal state, an open one re-derives the same decision.
    """

    if len(rest) != 2:
        return {"error": f"usage: {LOOP_ADVANCE_USAGE}"}
    run, loop_id = rest
    run_dir, data, text, loop, error = _loop_parent(run, loop_id)
    if error is not None:
        return error
    if str(data.get("status")) in TERMINAL_STATES:
        return {"loop_advance": {"run": run, "id": loop_id, "action": "closed",
                                 "status": str(data.get("status")), "outcome": "replayed"}}
    evaluation = _evaluate(run, loop_id, run_dir, data, text, loop)
    if "error" in evaluation:
        return evaluation
    reading = evaluation["loop_evaluate"]
    if "pending" in reading:
        return {"loop_advance": {"run": run, "id": loop_id, "action": "await-done-check",
                                 "pending": reading["pending"]}}
    iterations = _iterations(run_dir, loop_id)
    if reading["done"]:
        return _close(run, loop_id, "complete", reading)
    delivered = [item for item in iterations if str(item[2].get("status")) in TERMINAL_STATES]
    if len(delivered) >= STALL_WINDOW:
        tail = [_result_reading(run_dir, item[1]) for item in delivered[-STALL_WINDOW:]]
        if all(entry is not None for entry in tail) and (
            all(not entry for entry in tail) or len(set(tail)) == 1
        ):
            return _close(run, loop_id, "stalled", reading)
    if not any(
        str(item[2].get("status")) in RESULT_BEARING_STATES for item in delivered[-1:]
    ):
        # The latest iteration closed without a result to build on; a loop
        # over blocked/failed iterations converges on nothing.
        return _close(run, loop_id, "stalled", reading)
    return {"loop_advance": {"run": run, "id": loop_id, "action": "arm",
                             "next": iterations[-1][0] + 1 if iterations else 1}}


def _close(run, loop_id, status, reading):
    if __package__:
        from .tickets_lifecycle import _cmd_set_status
    else:  # pragma: no cover - flat script path
        from tickets_lifecycle import _cmd_set_status
    result = _cmd_set_status([run, loop_id, status])
    if "error" in result:
        return result
    return {"loop_advance": {"run": run, "id": loop_id, "action": "closed",
                             "status": status, "evaluation": reading}}


__all__ = (
    "LOOP_ARM_USAGE", "LOOP_EVALUATE_USAGE", "LOOP_ADVANCE_USAGE",
    "_cmd_loop_arm", "_cmd_loop_evaluate", "_cmd_loop_advance",
)
