"""The ticket's `done` predicate, read and run by `land` and nowhere else.

Done is a checked condition, not a recorded claim. A ticket may carry the
same closed `{form, value}` binding a loop stub carries for its iterations
(contracts/work-item.md), and `tickets.py land` is the one caller that
evaluates it: a deterministic command whose exit 0 is the verdict, or a
frozen criterion no oracle covers, judged by one minted `orch-judge`
ticket. A ticket that carries neither is graded the way it always was, by
the driver, through `land --status`.

The command form is the one outside execution `rules/verification.md`
Section 6 names, and it runs in the integrated tree rather than in the
candidate: the fact under test is what the repository does with the
candidate's commits in it, which is why `land` merges before it asks.

A refused command does not wedge the run and does not close the ticket. It
arms the next `<id>.repair.NN` round through the advance rules below, and
`land` run again after that round re-runs the predicate against the
further-integrated tree. Round two is a lawful slot, not hand surgery.

The round machinery lives here because `land` is its one reader. It was
written inside the loop lane, whose iterations advanced by the same three
rules; the lane is gone and the rules moved to the door that still asks
them.
"""

from __future__ import annotations

import shlex
import subprocess

if __package__:
    from .tickets_admission import ADMISSION_PENDING
    from .tickets_format import (
        DELIVERED_STATE, DONE_TICKET_SUFFIX, REPAIR_MARKER, REPORT_SECTION,
        RESULT_BEARING_STATES, TERMINAL_STATES,
        _sections, _set_frontmatter_field,
        _write_section, dequote, done_defects, round_of, parse_done,
        ticket_defects,
    )
    from .tickets_generations import assignment_digest
    from .tickets_issue_render import _render_ticket
    from .tickets_result import RESULT_ATTRIBUTION_PREFIX
    from .tickets_store import (
        TicketWriteRefused, _create_text_exclusively, _load_ticket,
        _write_text_atomically, locked_ticket_write,
    )
else:  # pragma: no cover - direct/installed flat script path
    from tickets_admission import ADMISSION_PENDING
    from tickets_format import (
        DELIVERED_STATE, DONE_TICKET_SUFFIX, REPAIR_MARKER, REPORT_SECTION,
        RESULT_BEARING_STATES, TERMINAL_STATES,
        _sections, _set_frontmatter_field,
        _write_section, dequote, done_defects, round_of, parse_done,
        ticket_defects,
    )
    from tickets_generations import assignment_digest
    from tickets_issue_render import _render_ticket
    from tickets_result import RESULT_ATTRIBUTION_PREFIX
    from tickets_store import (
        TicketWriteRefused, _create_text_exclusively, _load_ticket,
        _write_text_atomically, locked_ticket_write,
    )

# The evidence line `land` files. It names the three facts a reader has to
# have to re-run the check for themselves and get the same answer: what was
# run, what it answered, and where it stood while it answered.
COMMAND_VERIFICATION = "done command `{command}` exited {exit} in {tree}"
CHECK_VERIFICATION = "done check `{criterion}` judged {status} by {ticket}"
COMMAND_TIMEOUT_SECONDS = 1800
# Two consecutive terminal rounds with no result delta exit stalled.
STALL_WINDOW = 2


def rounds(run_dir, parent_id, marker: str = REPAIR_MARKER):
    """(number, id, data) for every round ticket, ordered by number.

    The `.done` check tickets minted beside a round are not rounds -- they
    judge one -- and the grammar `round_of` owns does not read them as
    one.
    """

    found = []
    for path in sorted(run_dir.glob(f"{parent_id}.{marker}.*.md")):
        parsed = round_of(path.stem)
        if parsed is None or parsed[0] != parent_id:
            continue
        loaded = _load_ticket(path)
        if "error" in loaded:
            continue
        found.append((parsed[1], path.stem, loaded))
    return sorted(found)


def _result_reading(run_dir, round_id):
    """What one round left behind, as the stall rule compares it.

    The whole report, because the report is the whole of what a round filed:
    two rounds that produced byte-identical reports converged on nothing,
    which is the reading `advance_action` closes `stalled` on.
    """

    try:
        text = (run_dir / f"{round_id}.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return _sections(text).get(REPORT_SECTION, "").strip()


def advance_action(run_dir, parent_id: str, marker: str, done: bool) -> dict:
    """The advance decision for one done reading, over one round marker.

    Three rules and no scheduler: a met done closes `complete`; two
    consecutive delivered rounds with no result delta converge on nothing
    and close `stalled`, as does a latest round that left no result to build
    on; anything else arms the next round. The bound is the dispatching
    caller's -- an effort-shaped bound is not a clock this can read. No
    prior round is a reason to arm rather than a reason to give up.
    """

    numbered = rounds(run_dir, parent_id, marker)
    if done:
        return {"action": "close", "status": "complete"}
    if numbered and str(numbered[-1][2].get("status")) not in TERMINAL_STATES:
        # The standing round has not landed. Counting past it would arm a
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


def mint_check(run: str, run_dir, check_id: str, source: dict, goal: str,
               context, *, depends_on: str, lock_held: bool = False):
    """Create -- or replay -- the one `orch-judge` ticket judging a criterion.

    The single minter for the `check` done form: a landing whose predicate
    names a criterion no oracle covers. A second minter would be a second
    place the check's shape could drift from contracts/work-item.md, and the
    check is the surface whose measured yield bought this form its place.

    It carries no `review_kind`: it is ordinary judging work, and its verdict
    is the status its join records rather than a token in its prose.
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


def predicate(data: dict):
    """`(binding, refusal)` for one ticket's `done` field, or `(None, None)`.

    Graded here rather than trusted: the lint that grades a ticket's bytes
    runs at issue, and a hand-edited frontmatter reaching `land` with a
    malformed predicate must refuse rather than be read as absent -- an
    absent predicate means the driver grades, and silently promoting a
    broken one into that is the failure this whole stage exists against.
    """

    raw = str(data.get("done") or "").strip()
    if not raw:
        return None, None
    defects = done_defects(raw)
    if defects:
        return None, {"error": "done predicate is off contract: " + "; ".join(defects)}
    return parse_done(data), None


def _command_reading(command: str, tree):
    """Run the frozen command in the integrated tree; exit 0 is the verdict."""

    argv = shlex.split(str(command))
    if not argv:
        return None, {"error": "done command is empty"}
    try:
        completed = subprocess.run(
            argv, cwd=None if tree is None else str(tree), capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return None, {"error": f"done command failed to run: {error}"}
    return {
        "form": "command", "command": command, "exit": completed.returncode,
        "done": completed.returncode == 0, "tree": None if tree is None else str(tree),
        "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-4000:],
    }, None


def verification_line(reading: dict) -> str:
    """The one sentence `land` files, for either form."""

    if reading.get("form") == "command":
        return COMMAND_VERIFICATION.format(
            command=reading["command"], exit=reading["exit"],
            tree=reading.get("tree") or "the caller's own checkout",
        )
    return CHECK_VERIFICATION.format(
        criterion=reading["criterion"], status=reading.get("status"),
        ticket=reading.get("verdict_ticket"),
    )


def record_verification(path, reading: dict, by: str):
    """Write the predicate's own evidence into the ticket, attributed to land.

    Into `## Report`, beside what the child filed, because there is one
    channel and this is one more thing worth reading about the item. System-
    written and attributed to the driver that landed, never to a child: no
    child ran this, and evidence whose writer is wrong is evidence a reader
    cannot weigh. Filed once -- a re-landed ticket whose predicate answers
    the same way finds its own line already in the section and leaves it
    there rather than stacking a second copy.
    """

    body = f"{RESULT_ATTRIBUTION_PREFIX}`{by}`\n\n{verification_line(reading)}"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return "replayed", {"error": f"unreadable ticket for done evidence: {error}"}
    prior = _sections(text).get(REPORT_SECTION, "")
    if body.rstrip() and body.rstrip() in prior:
        return "replayed", None
    try:
        _write_text_atomically(
            path, _write_section(text, REPORT_SECTION, body, bool(prior.strip())),
        )
    except (OSError, ValueError) as error:
        return "refused", {"error": f"unable to file done evidence: {error}"}
    return "filed", None


def _repair_round(run: str, run_dir, ticket_id: str, source: dict, reading: dict,
                  number: int):
    """Create the next round-two repair ticket, or replay the one standing."""

    repair_id = f"{ticket_id}.{REPAIR_MARKER}.{number}"
    path = run_dir / f"{repair_id}.md"
    if path.exists():
        return repair_id, "replayed", None
    rendered = _render_ticket({
        "id": repair_id, "run": run, "status": "pending",
        "admission": ADMISSION_PENDING, "executor": "orch-do",
        "pack": dequote(source.get("pack")) or None,
        "independence": "gate", "depends_on": [],
        "isolation": "none", "bound": source.get("bound"),
        "root_generation": source.get("root_generation"),
    }, [
        ("Goal", f"Make `{ticket_id}`'s done predicate pass on the integrated "
                 f"tree: `{reading['command']}` exits {reading['exit']} there now."),
        ("Context", "\n".join(f"- {line}" for line in [
            f"landed ticket: {ticket_id}",
            f"integrated tree: {reading.get('tree')}",
            f"round: {number}",
            "The candidate is already merged; repair in this tree.",
        ])),
        (REPORT_SECTION, ""),
    ])
    cut_generation = str(source.get("cut_generation") or "").strip()
    if cut_generation:
        rendered = _set_frontmatter_field(rendered, "cut_generation", cut_generation)
    rendered = _set_frontmatter_field(
        rendered, "assignment_seal", assignment_digest(repair_id, rendered),
    )
    try:
        _create_text_exclusively(path, rendered)
    except OSError as error:
        return None, None, {"error": f"unable to arm the repair round: {error}"}
    return repair_id, "created", None


def resolve(run: str, ticket_id: str, run_dir, path, data: dict, tree,
            driver_status, by: str):
    """`(decision, refusal)` -- what this landing records, and why.

    `status` is the disposition the join will write, or `None` when there is
    nothing to join yet: a check still out, or a repair round just armed.
    """

    binding, refusal = predicate(data)
    if refusal is not None:
        return None, refusal
    if binding is None:
        if driver_status is None:
            return None, {"error": (
                f"{run}/{ticket_id} carries no done predicate, so the driver "
                "grades it: pass the disposition with --status"
            )}
        return {"form": None, "status": driver_status}, None
    if driver_status is not None:
        return None, {"error": (
            f"{run}/{ticket_id} carries a done predicate, which land evaluates; "
            "--status is the grade path for a ticket that carries none"
        )}
    if binding["form"] == "command":
        reading, refusal = _command_reading(binding["value"], tree)
        if refusal is not None:
            return None, refusal
    else:
        check_id = f"{ticket_id}{DONE_TICKET_SUFFIX}"
        reading, refusal = check_reading(
            run, run_dir, check_id, data,
            f"Judge the done criterion for `{ticket_id}`: {binding['value']} "
            "Judge it against that ticket's Goal and its recorded result, and "
            "file every blocker you find with its evidence.",
            [f"landed ticket: {ticket_id}", f"criterion: {binding['value']}"],
            depends_on=ticket_id, lock_held=True,
        )
        if refusal is not None:
            return None, refusal
        reading = dict(reading, form="check", criterion=binding["value"])
        if "pending" in reading:
            return {"form": "check", "status": None, "reading": reading,
                    "action": "await-done-check"}, None
    evidence, refusal = record_verification(path, reading, by)
    if refusal is not None:
        return None, refusal
    decision = {"form": reading["form"], "reading": reading, "evidence": evidence}
    if reading["done"]:
        return dict(decision, status=DELIVERED_STATE), None
    action = advance_action(run_dir, ticket_id, REPAIR_MARKER, False)
    if action["action"] != "arm":
        return dict(decision, status=action["status"], action="close"), None
    repair_id, outcome, refusal = _repair_round(
        run, run_dir, ticket_id, data, reading, action["next"],
    )
    if refusal is not None:
        return None, refusal
    # `outcome_detail`, not `outcome`: the step report's own `outcome` says
    # what the predicate did, and a second key spelled the same would take
    # its place on the way out.
    return dict(
        decision, status=None, action="arm", repair=repair_id,
        outcome_detail=outcome,
    ), None


__all__ = (
    "CHECK_VERIFICATION", "COMMAND_VERIFICATION", "REPAIR_MARKER",
    "STALL_WINDOW", "advance_action", "check_reading", "mint_check",
    "predicate", "record_verification", "resolve", "rounds",
    "verification_line",
)
