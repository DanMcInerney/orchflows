"""Arm, evaluate, and advance one loop stub without an engine.

A loop is a ticket carrying the ``loop: true`` marker beside its own
``done`` predicate (contracts/work-item.md). No LLM holds loop state: the
ticket set is the state, the worklog its rendered view. The driver treats
a ready loop stub as arm -> run the iteration to terminal -> evaluate ->
advance, and every command here replays after a kill.

The iteration's verb is the stub's own ``executor``, and the predicate its
own ``done`` -- the marker restates neither. That binding takes exactly one
of two closed forms: a deterministic command whose exit 0 is the done
reading (that run is the one outside execution closing the loop), or a
frozen criterion judged by a fresh ``orch-judge`` ticket minted per
iteration.
"""

from __future__ import annotations

import hashlib
import shlex
import subprocess

if __package__:
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_format import (
        DELIVERED_STATE, DONE_TICKET_SUFFIX, ITERATION_MARKER, REPAIR_MARKER,
        REPORT_SECTION, RESULT_BEARING_STATES, TERMINAL_STATES,
        _executor_of, _sections, _set_frontmatter_field, dequote, is_loop_stub,
        iteration_of, loop_defects, parse_done, ticket_defects,
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
        DELIVERED_STATE, DONE_TICKET_SUFFIX, ITERATION_MARKER, REPAIR_MARKER,
        REPORT_SECTION, RESULT_BEARING_STATES, TERMINAL_STATES,
        _executor_of, _sections, _set_frontmatter_field, dequote, is_loop_stub,
        iteration_of, loop_defects, parse_done, ticket_defects,
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
# The two markers this machinery arms under are `tickets_format`'s, beside
# the grammar that reads them: a loop's body is an `.iter.NN` ticket, and a
# landing whose `done` command refused arms its round two as a `.repair.NN`
# ticket through the same three rules below, because the question -- is there
# anything left to build on, and has it moved? -- is the same question in
# both places. The sealed-admission door reads the same grammar to bind a
# round through the ticket it was minted under.
# Two consecutive terminal iterations with no result delta exit stalled
# (rules/loops.md).
STALL_WINDOW = 2


def iterations(run_dir, parent_id, marker: str = ITERATION_MARKER):
    """(number, id, data) for every iteration ticket, ordered by number.

    One reader for both markers: a loop's `<id>.iter.NN` bodies and the
    `<id>.repair.NN` rounds a failed `done` command arms. The `.done` check
    tickets minted beside them are not rounds -- they judge one -- and the
    grammar `iteration_of` owns does not read them as one.
    """

    found = []
    for path in sorted(run_dir.glob(f"{parent_id}.{marker}.*.md")):
        parsed = iteration_of(path.stem)
        if parsed is None or parsed[0] != parent_id:
            continue
        loaded = _load_ticket(path)
        if "error" in loaded:
            continue
        found.append((parsed[1], path.stem, loaded))
    return sorted(found)


def _iterations(run_dir, loop_id):
    return iterations(run_dir, loop_id, ITERATION_MARKER)


def _loop_parent(run, loop_id):
    """(run_dir, data, text, done, error) for one loop stub."""

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
    if not is_loop_stub(data):
        return None, None, None, None, {
            "error": f"{run}/{loop_id} carries no loop marker; only a loop stub is armed, evaluated, or advanced"
        }
    defects = loop_defects(data.get("loop"), _executor_of(data), data.get("done"))
    if defects:
        return None, None, None, None, {"error": f"loop stub is off contract: " + "; ".join(defects)}
    done = parse_done(data)
    if done is None:
        return None, None, None, None, {
            "error": f"loop stub {run}/{loop_id} carries no readable done predicate"
        }
    return run_dir, data, text, done, None


def _iteration_context(data, text, number, prior):
    """The context-packet lines one iteration receives beside the frozen
    goal: identities and decisions, never transcript prose."""

    sections = _sections(text)
    lines = [sections.get("Context", "").strip()] if sections.get("Context", "").strip() else []
    lines.append(f"- loop: iteration {number} of a bounded loop; the worklog is the state")
    done = parse_done(data) or {}
    lines.append(
        f"- done-check ({done.get('form')}): {done.get('value')}"
    )
    lines.append(f"- bound: {data.get('bound')}")
    if prior is not None:
        prior_number, prior_id, _ = prior
        lines.append(
            f"- prior iteration: {prior_id} — read its `## {REPORT_SECTION}` before working; an identical retry is a defect"
        )
    return "\n\n".join(lines)


def _cmd_loop_arm(rest):
    """Instantiate the next iteration from the frozen goal + worklog tail."""

    if len(rest) != 2:
        return {"error": f"usage: {LOOP_ARM_USAGE}"}
    run, loop_id = rest
    run_dir, data, text, done, error = _loop_parent(run, loop_id)
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
    if sections.get("Details", "").strip():
        body.append(("Details", sections["Details"].strip()))
    body.append((REPORT_SECTION, ""))
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


def _evaluate(run, loop_id, run_dir, data, text, done):
    """The done reading for the latest terminal iteration.

    Deterministic form: run the frozen command; exit 0 is done. Check
    form: mint one fresh `orch-judge` ticket judging the frozen
    criterion; a live one reports pending, a terminal one reports its
    verdict.
    """

    iterations = _iterations(run_dir, loop_id)
    if not iterations:
        return {"error": f"loop stub {run}/{loop_id} has no iteration; arm first"}
    number, iteration_id, iteration = iterations[-1]
    if str(iteration.get("status")) not in TERMINAL_STATES:
        return {"error": f"iteration {iteration_id} is not terminal; evaluate follows the landed iteration"}
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
    goal = (
        f"Judge the loop done-check for `{loop_id}` after iteration {number}: "
        f"{done['value']} Verify against the loop Goal and `{iteration_id}`'s "
        "recorded result, and file every blocker you find with its evidence."
    )
    reading, refusal = check_reading(
        run, run_dir, check_id, data, goal,
        [f"loop stub: {loop_id}", f"iteration: {iteration_id}"],
        depends_on=iteration_id,
    )
    if refusal is not None:
        return refusal
    return {"loop_evaluate": {
        "run": run, "id": loop_id, "iteration": number, "form": "check", **reading,
    }}


def mint_check(run: str, run_dir, check_id: str, source: dict, goal: str,
               context, *, depends_on: str, lock_held: bool = False):
    """Create -- or replay -- the one `orch-judge` ticket judging a criterion.

    The single minter for both homes of the `check` done form: a loop's
    per-iteration done-check and a landing whose predicate names a criterion
    no oracle covers. A second minter would be a second place the check's
    shape could drift from contracts/work-item.md, and the check is the
    surface whose measured yield bought this form its place.

    It carries no `review_kind`: it is ordinary judging work, not a lane of
    the composite gate's immutable ledger, and its verdict is the status its
    join records rather than a token in its prose.
    """

    path = run_dir / f"{check_id}.md"
    fields = {
        "id": check_id, "run": run, "status": "pending",
        "admission": ADMISSION_PENDING, "executor": "orch-judge",
        "pack": dequote(source.get("pack")) or None,
        "independence": "gate", "depends_on": [depends_on],
        "isolation": "none", "bound": source.get("bound"),
        "root_generation": source.get("root_generation"),
    }
    rendered = _render_ticket(fields, [
        ("Goal", goal),
        ("Context", "\n".join(f"- {line}" for line in context)),
        (REPORT_SECTION, ""),
    ])
    cut_generation = str(source.get("cut_generation") or "").strip()
    if cut_generation:
        rendered = _set_frontmatter_field(rendered, "cut_generation", cut_generation)
    rendered = _set_frontmatter_field(
        rendered, "assignment_seal", assignment_digest(check_id, rendered)
    )
    defects = ticket_defects(rendered)
    if defects:
        return {"error": f"done-check {check_id} is off contract: " + "; ".join(defects)}
    try:
        if lock_held:
            # `land` already holds this run's lock across its whole return,
            # and the lock is one process byte rather than a counter: taking
            # it again here would be a caller waiting on itself.
            if not path.exists():
                _create_text_exclusively(path, rendered)
        else:
            with locked_ticket_write(run, check_id):
                if not path.exists():
                    _create_text_exclusively(path, rendered)
    except TicketWriteRefused as refused:
        return refused.payload
    except OSError as error:
        return {"error": f"unable to create done-check: {error}"}
    return None


def check_reading(run: str, run_dir, check_id: str, source: dict, goal: str,
                  context, *, depends_on: str, lock_held: bool = False):
    """`(reading, refusal)` for the `check` done form's minted judge.

    A verdict here is the check ticket's own joined status: `complete` is
    met and any other terminal state is not. Nothing parses a token out of
    prose -- the child files findings, and the authority that joins the
    check is what records the disposition.
    """

    path = run_dir / f"{check_id}.md"
    if not path.is_file():
        refusal = mint_check(
            run, run_dir, check_id, source, goal, context,
            depends_on=depends_on, lock_held=lock_held,
        )
        if refusal is not None:
            return None, refusal
        return {"pending": check_id, "outcome": "created"}, None
    check = _load_ticket(path)
    if "error" in check:
        return None, {"error": check["error"]}
    status = str(check.get("status"))
    if status not in TERMINAL_STATES:
        return {"pending": check_id, "outcome": "live"}, None
    return {
        "done": status == DELIVERED_STATE,
        "status": status,
        "verdict_ticket": check_id,
    }, None


def _cmd_loop_evaluate(rest):
    if len(rest) != 2:
        return {"error": f"usage: {LOOP_EVALUATE_USAGE}"}
    run, loop_id = rest
    run_dir, data, text, done, error = _loop_parent(run, loop_id)
    if error is not None:
        return error
    return _evaluate(run, loop_id, run_dir, data, text, done)


def _result_reading(run_dir, iteration_id):
    """What one round left behind, as the stall rule compares it.

    The whole report, because the report is the whole of what a round filed:
    two rounds that produced byte-identical reports converged on nothing,
    which is the reading `advance_action` closes `stalled` on.
    """

    try:
        text = (run_dir / f"{iteration_id}.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return _sections(text).get(REPORT_SECTION, "").strip()


def _cmd_loop_advance(rest):
    """Re-arm, or close the stub complete | limited | stalled.

    The transition writes go through ``set-status`` — the one lifecycle
    door — so advance replays idempotently after a kill: a closed stub
    reports its terminal state, an open one re-derives the same decision.
    """

    if len(rest) != 2:
        return {"error": f"usage: {LOOP_ADVANCE_USAGE}"}
    run, loop_id = rest
    run_dir, data, text, done, error = _loop_parent(run, loop_id)
    if error is not None:
        return error
    if str(data.get("status")) in TERMINAL_STATES:
        return {"loop_advance": {"run": run, "id": loop_id, "action": "closed",
                                 "status": str(data.get("status")), "outcome": "replayed"}}
    evaluation = _evaluate(run, loop_id, run_dir, data, text, done)
    if "error" in evaluation:
        return evaluation
    reading = evaluation["loop_evaluate"]
    if "pending" in reading:
        return {"loop_advance": {"run": run, "id": loop_id, "action": "await-done-check",
                                 "pending": reading["pending"]}}
    action = advance_action(run_dir, loop_id, ITERATION_MARKER, reading["done"])
    if action["action"] == "close":
        return _close(run, loop_id, action["status"], reading)
    return {"loop_advance": {"run": run, "id": loop_id, "action": "arm",
                             "next": action["next"]}}


def advance_action(run_dir, parent_id: str, marker: str, done: bool) -> dict:
    """The advance decision for one done reading, over one iteration marker.

    Three rules and no scheduler, and they are the rules `rules/loops.md`
    Section 3 already states: a met done closes `complete`; two consecutive
    delivered iterations with no result delta converge on nothing and close
    `stalled`, as does a latest iteration that left no result to build on;
    anything else arms the next round. The bound is the dispatching
    caller's -- an effort-shaped bound is not a clock this can read.

    A landing whose `done` command refused asks the same question of its
    `.repair.NN` rounds, so this answers for both markers rather than
    growing a second copy under a second name. The one seam between them is
    the first round: a loop only evaluates after an iteration exists, while
    a landing's first refusal has no prior round, and no prior round is a
    reason to arm rather than a reason to give up.
    """

    numbered = iterations(run_dir, parent_id, marker)
    if done:
        return {"action": "close", "status": "complete"}
    if numbered and str(numbered[-1][2].get("status")) not in TERMINAL_STATES:
        # The standing round has not landed. Naming it again is the replay
        # `loop-arm` already answers with, and counting past it would arm a
        # second round against the same unanswered one.
        return {"action": "arm", "next": numbered[-1][0]}
    delivered = [
        item for item in numbered if str(item[2].get("status")) in TERMINAL_STATES
    ]
    if len(delivered) >= STALL_WINDOW:
        tail = [_result_reading(run_dir, item[1]) for item in delivered[-STALL_WINDOW:]]
        if all(entry is not None for entry in tail) and (
            all(not entry for entry in tail) or len(set(tail)) == 1
        ):
            return {"action": "close", "status": "stalled"}
    if delivered and not any(
        str(item[2].get("status")) in RESULT_BEARING_STATES for item in delivered[-1:]
    ):
        return {"action": "close", "status": "stalled"}
    return {"action": "arm", "next": numbered[-1][0] + 1 if numbered else 1}


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
    "DONE_TICKET_SUFFIX", "ITERATION_MARKER", "REPAIR_MARKER", "STALL_WINDOW",
    "LOOP_ARM_USAGE", "LOOP_EVALUATE_USAGE", "LOOP_ADVANCE_USAGE",
    "advance_action", "check_reading", "iterations", "mint_check",
    "_cmd_loop_arm", "_cmd_loop_evaluate", "_cmd_loop_advance",
)
