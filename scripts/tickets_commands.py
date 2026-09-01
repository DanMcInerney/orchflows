"""Closed ticket subcommand and help tables."""
from __future__ import annotations

import sys
from pathlib import Path

if __package__:
    from .tickets_format import EXECUTOR_SECTIONS, TERMINAL_STATES, VALID_STATUSES, _read_utf8
    from .tickets_brick import DO_USAGE, JUDGE_USAGE
    from .tickets_frame import FRAME_CLOSE_USAGE, FRAME_OPEN_USAGE
    from .tickets_issue import NEW_USAGE
    from .tickets_lifecycle import CHECKABLE_STATUSES, CHECK_USAGE
    from .tickets_result import IMPROVEMENT_USAGE, RESULT_USAGE, RUN_STATE_USAGE
    from .tickets_store import DEFAULT_RUN_STATE_TREE, REPAIR_RUN_IDENTITY_USAGE, RUN_STATE_TREES
    from .tickets_worklog import WORKLOG_USAGE
    from .tickets_attempts import DISPATCH_COMMIT_USAGE, DISPATCH_OPEN_USAGE, DISPATCH_REPLACE_USAGE, DISPATCH_RETIRE_USAGE
    from .tickets_join import DISPATCH_JOIN_USAGE
    from .tickets_outcome import DISPATCH_OUTCOME_USAGE
    from .tickets_land import LAND_USAGE
else:
    from tickets_format import EXECUTOR_SECTIONS, TERMINAL_STATES, VALID_STATUSES, _read_utf8
    _brick = __import__('tickets_brick')
    DO_USAGE, JUDGE_USAGE = (_brick.DO_USAGE, _brick.JUDGE_USAGE)
    _frame = __import__('tickets_frame')
    FRAME_CLOSE_USAGE, FRAME_OPEN_USAGE = (_frame.FRAME_CLOSE_USAGE, _frame.FRAME_OPEN_USAGE)
    from tickets_issue import NEW_USAGE
    from tickets_lifecycle import CHECKABLE_STATUSES, CHECK_USAGE
    from tickets_result import IMPROVEMENT_USAGE, RESULT_USAGE, RUN_STATE_USAGE
    from tickets_store import DEFAULT_RUN_STATE_TREE, REPAIR_RUN_IDENTITY_USAGE, RUN_STATE_TREES
    from tickets_worklog import WORKLOG_USAGE
    _attempts = __import__("tickets_attempts")
    DISPATCH_COMMIT_USAGE = _attempts.DISPATCH_COMMIT_USAGE
    DISPATCH_OPEN_USAGE = _attempts.DISPATCH_OPEN_USAGE
    DISPATCH_REPLACE_USAGE = _attempts.DISPATCH_REPLACE_USAGE
    DISPATCH_RETIRE_USAGE = _attempts.DISPATCH_RETIRE_USAGE
    DISPATCH_JOIN_USAGE = __import__("tickets_join").DISPATCH_JOIN_USAGE
    DISPATCH_OUTCOME_USAGE = __import__("tickets_outcome").DISPATCH_OUTCOME_USAGE
    LAND_USAGE = __import__('tickets_land').LAND_USAGE

LINT_USAGE = "lint (<run> <id> | <run> [<id>] --file <path>) [--fix]"
DISPATCH_USAGE = (
    "dispatch <run> <id> --by <name> --dispatch-id <id> "
    "--lease-expires-at <absolute-iso> "
    "[--workspace <source-tree-to-cut-from>] [--host <name>]"
)
GRADE_USAGE = "grade <run> <root>"
BOUND_CHECK_USAGE = "bound-check <run> [--now <iso>]"
SUBCOMMAND_USAGE = {
    "new": NEW_USAGE,
    "do": DO_USAGE,
    "judge": JUDGE_USAGE,
    "frame-open": FRAME_OPEN_USAGE,
    "frame-close": FRAME_CLOSE_USAGE,
    "grade": GRADE_USAGE,
    "list": "list [--run R]",
    "show": "show <run> <id>",
    "dispatch": DISPATCH_USAGE,
    "land": LAND_USAGE,
    "dispatch-open": DISPATCH_OPEN_USAGE,
    "dispatch-commit": DISPATCH_COMMIT_USAGE,
    "dispatch-retire": DISPATCH_RETIRE_USAGE,
    "dispatch-replace": DISPATCH_REPLACE_USAGE,
    "dispatch-outcome": DISPATCH_OUTCOME_USAGE,
    "dispatch-join": DISPATCH_JOIN_USAGE,
    "check": CHECK_USAGE,
    "set-status": "set-status <run> <id> <status>",
    "result": RESULT_USAGE,
    "worklog": WORKLOG_USAGE,
    "run-state": RUN_STATE_USAGE,
    "repair-run-identity": REPAIR_RUN_IDENTITY_USAGE,
    "improvement": IMPROVEMENT_USAGE,
    "bound-check": BOUND_CHECK_USAGE,
    "lint": LINT_USAGE,
}
SUBCOMMAND_SUMMARY = {
    "new": "Create one Goal/Context ticket; Details is the planner's optional free-form guidance.",
    "do": "Mint, seal, establish, and launch one artifact-making brick under its parent.",
    "judge": "Mint, seal, establish, and launch one read-only brick over the typed artifacts it is handed.",
    "frame-open": "Open one call-stack frame for a workflow invocation: sealed goal, parent link, and the journal its driver appends to.",
    "frame-close": "Record what one frame's invocation became, refusing a close over two or more do-children nobody judged.",
    "grade": "Report deterministic width, shape, pack coverage, and adapter capability.",
    "list": "List tickets.",
    "show": "Inspect one ticket's parsed identity and sections without mutation.",
    "dispatch": "Atomically ready, establish, open, and emit the one launch that starts this ticket's child.",
    "land": "Atomically import the outcome, join it, retire the derived worktree, and report the frontier.",
    "dispatch-open": "Atomically open or replay one fenced dispatch-v1 execution attempt.",
    "dispatch-commit": "Commit or replay one idempotent record on a live dispatch-v1 attempt.",
    "dispatch-retire": "Retire or replay retirement of one dispatch-v1 attempt.",
    "dispatch-replace": "Atomically replace one live dispatch-v1 attempt with a unique successor.",
    "dispatch-outcome": "Commit or replay the attempt's one reserved executor outcome envelope.",
    "dispatch-join": "Commit or replay one outcome-fenced join and its lifecycle transition.",
    "check": "Anchor one completed durable checker stage to its target's checked_by field.",
    "set-status": f"Set lifecycle status to one of {sorted(VALID_STATUSES)}.",
    "result": f"Append one executor-owned record section {list(EXECUTOR_SECTIONS)}.",
    "worklog": "Render the run worklog.",
    "run-state": f"Write run state under {list(RUN_STATE_TREES)} (default {DEFAULT_RUN_STATE_TREE}).",
    "repair-run-identity": "Quarantine an unreadable run identity and rebuild the minimal one from ticket evidence.",
    "improvement": "Write improvement evidence.",
    "bound-check": "Report live claims against their operational bound.",
    "lint": "Grade the exact pre-issue file projection or one current ticket.",
}
HELP_FLAGS = frozenset({"--help", "-h"})
HELP_COMMANDS = HELP_FLAGS | {"help"}
VALUE_FLAGS = frozenset({
    "--run", "--by", "--executor", "--goal", "--context", "--details",
    "--depends-on", "--bound", "--pack",
    "--profile", "--independence", "--isolation",
    "--section", "--file", "--text", "--note", "--artifact", "--terminal",
    "--tree", "--workspace", "--proposal", "--covered",
    "--cut-generation", "--correction-bound", "--now", "--dispatch-id",
    "--assignment-seal",
    "--lease-expires-at", "--replacement-dispatch-id", "--record-id", "--content",
    "--outcome-record-id", "--status", "--stage",
    "--goal-file", "--details-file", "--parent", "--done", "--artifacts",
    "--result-file", "--verification-file",
    "--feedback-file", "--risks-file", "--handoff-file",
    "--host", "--outcome-file",
})


def read_payload(source, subject: str = "payload file"):
    if source == "-":
        try:
            return sys.stdin.buffer.read().decode("utf-8"), None
        except (OSError, ValueError, UnicodeDecodeError, AttributeError) as error:
            return None, {"error": f"unreadable {subject}: {error}"}
    return _read_utf8(Path(source), subject)


def resolve_payload_flags(command: str, rest):
    args = list(rest)
    if command == "run-state" and "--note" in args:
        at = args.index("--note")
        if at + 1 >= len(args) or args[at + 1] != "--file":
            return args, None
        if at + 2 >= len(args):
            return None, {"error": f"run-state --note --file takes one path. usage: {RUN_STATE_USAGE}"}
        body, failure = read_payload(args[at + 2], "note file")
        return (None, failure) if failure is not None else (args[:at + 1] + [body] + args[at + 3:], None)
    return args, None
