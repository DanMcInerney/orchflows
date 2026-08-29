"""Closed ticket subcommand and help tables."""
from __future__ import annotations

import sys
from pathlib import Path

if __package__:
    from .tickets_format import EXECUTOR_SECTIONS, TERMINAL_STATES, VALID_STATUSES, _read_utf8
    from .tickets_issue import NEW_USAGE
    from .tickets_lifecycle import CHECKABLE_STATUSES, CHECK_USAGE, JOIN_NOOP_REPAIR_USAGE
    from .tickets_packet import PACKET_USAGE
    from .tickets_result import IMPROVEMENT_USAGE, RESULT_USAGE, RUN_STATE_USAGE
    from .tickets_store import DEFAULT_RUN_STATE_TREE, RUN_STATE_TREES
    from .tickets_worklog import WORKLOG_USAGE
    from .tickets_generations import GENERATION_SUBCOMMANDS
    from .tickets_attempts import DISPATCH_COMMIT_USAGE, DISPATCH_OPEN_USAGE, DISPATCH_REPLACE_USAGE, DISPATCH_RETIRE_USAGE
    from .tickets_dispatch_packet import DISPATCH_PACKET_USAGE, DISPATCH_RECEIVE_USAGE
    from .tickets_join import DISPATCH_JOIN_USAGE, DISPATCH_OUTCOME_USAGE
else:
    from tickets_format import EXECUTOR_SECTIONS, TERMINAL_STATES, VALID_STATUSES, _read_utf8
    from tickets_issue import NEW_USAGE
    from tickets_lifecycle import CHECKABLE_STATUSES, CHECK_USAGE, JOIN_NOOP_REPAIR_USAGE
    from tickets_packet import PACKET_USAGE
    from tickets_result import IMPROVEMENT_USAGE, RESULT_USAGE, RUN_STATE_USAGE
    from tickets_store import DEFAULT_RUN_STATE_TREE, RUN_STATE_TREES
    from tickets_worklog import WORKLOG_USAGE
    GENERATION_SUBCOMMANDS = __import__("tickets_generations").GENERATION_SUBCOMMANDS
    _attempts = __import__("tickets_attempts")
    DISPATCH_COMMIT_USAGE = _attempts.DISPATCH_COMMIT_USAGE
    DISPATCH_OPEN_USAGE = _attempts.DISPATCH_OPEN_USAGE
    DISPATCH_REPLACE_USAGE = _attempts.DISPATCH_REPLACE_USAGE
    DISPATCH_RETIRE_USAGE = _attempts.DISPATCH_RETIRE_USAGE
    _dispatch_packet = __import__("tickets_dispatch_packet")
    DISPATCH_PACKET_USAGE = _dispatch_packet.DISPATCH_PACKET_USAGE
    DISPATCH_RECEIVE_USAGE = _dispatch_packet.DISPATCH_RECEIVE_USAGE
    _join = __import__("tickets_join")
    DISPATCH_JOIN_USAGE = _join.DISPATCH_JOIN_USAGE
    DISPATCH_OUTCOME_USAGE = _join.DISPATCH_OUTCOME_USAGE

LINT_USAGE = "lint (<run> <id> | <run> [<id>] --file <path>) [--fix]"
INSTANTIATE_USAGE = "instantiate <template-dir> --run <run> [--set k=v ...]"
DISPATCH_USAGE = (
    "dispatch <run> <id> --by <name> --dispatch-id <id> "
    "--lease-expires-at <absolute-iso> --reply-to <name> "
    "[--workspace <path>] [--artifact <fixed-identity>] "
    "[--form reference | inline]"
)
GATE_USAGE = "gate <run> <root-or-checked-id> [--lens <name>[,<name>] | --ordered-lens-bundle <name>[,<name>]]"
GRADE_USAGE = "grade <run> <root>"
CHECKER_STAGE_USAGE = "checker-stage <run> <id>"
BOUND_CHECK_USAGE = "bound-check <run> [--now <iso>]"
STAMP_GENERATION_USAGE = "stamp-generation <run> <root-id>"
SUBCOMMAND_USAGE = {
    "new": NEW_USAGE,
    "instantiate": INSTANTIATE_USAGE,
    "gate": GATE_USAGE,
    "grade": GRADE_USAGE,
    "checker-stage": CHECKER_STAGE_USAGE,
    "stamp-generation": STAMP_GENERATION_USAGE,
    "list": "list [--run R]",
    "show": "show <run> <id>",
    "ready": "ready [--run R]",
    "dispatch": DISPATCH_USAGE,
    "dispatch-open": DISPATCH_OPEN_USAGE,
    "dispatch-commit": DISPATCH_COMMIT_USAGE,
    "dispatch-retire": DISPATCH_RETIRE_USAGE,
    "dispatch-replace": DISPATCH_REPLACE_USAGE,
    "dispatch-outcome": DISPATCH_OUTCOME_USAGE,
    "dispatch-join": DISPATCH_JOIN_USAGE,
    "dispatch-packet": DISPATCH_PACKET_USAGE,
    "dispatch-receive": DISPATCH_RECEIVE_USAGE,
    "check": CHECK_USAGE,
    "set-status": "set-status <run> <id> <status>",
    "join-noop-repair": JOIN_NOOP_REPAIR_USAGE,
    "result": RESULT_USAGE,
    "worklog": WORKLOG_USAGE,
    "run-state": RUN_STATE_USAGE,
    "improvement": IMPROVEMENT_USAGE,
    "bound-check": BOUND_CHECK_USAGE,
    "lint": LINT_USAGE,
    **{name: values[0] for name, values in GENERATION_SUBCOMMANDS.items()},
}
SUBCOMMAND_SUMMARY = {
    "new": "Create one Goal/Context ticket; Suggested files are optional and non-binding.",
    "instantiate": "Instantiate, validate, and seal one current-format template graph all or none.",
    "gate": "Create a composite gate, or materialize repair and fresh verification after an ordinary checker accepts blockers.",
    "grade": "Report deterministic width, shape, pack coverage, adapter capability, and decomposition state.",
    "checker-stage": "Create or replay one explicit ordinary read-only checker stage.",
    "stamp-generation": "Stamp one unclaimed direct or decomposed root and its members.",
    "list": "List tickets.",
    "show": "Inspect one ticket's parsed identity and sections without mutation.",
    "ready": "Promote sealed tickets whose dependencies are complete.",
    "dispatch": "Atomically ready, establish, open, and project one dispatch packet.",
    "dispatch-open": "Atomically open or replay one fenced dispatch-v1 execution attempt.",
    "dispatch-commit": "Commit or replay one idempotent record on a live dispatch-v1 attempt.",
    "dispatch-retire": "Retire or replay retirement of one dispatch-v1 attempt.",
    "dispatch-replace": "Atomically replace one live dispatch-v1 attempt with a unique successor.",
    "dispatch-outcome": "Commit or replay the attempt's one reserved executor outcome envelope.",
    "dispatch-join": "Commit or replay one outcome-fenced join and its lifecycle transition.",
    "dispatch-packet": "Commit or replay one reference or inline dispatch-v1 packet projection.",
    "dispatch-receive": "Validate one dispatch-v1 packet against its receipt identity and authority.",
    "check": "Anchor one completed durable checker stage to its target's checked_by field.",
    "set-status": f"Set lifecycle status to one of {sorted(VALID_STATUSES)}.",
    "join-noop-repair": "Atomically attribute and complete a clean repair at the join without dispatch.",
    "result": f"Append one executor-owned record section {list(EXECUTOR_SECTIONS)}.",
    "worklog": "Render the run worklog.",
    "run-state": f"Write run state under {list(RUN_STATE_TREES)} (default {DEFAULT_RUN_STATE_TREE}).",
    "improvement": "Write improvement evidence.",
    "bound-check": "Report live claims against their operational bound.",
    "lint": "Grade the exact pre-issue file projection or one current ticket.",
    **{name: values[1] for name, values in GENERATION_SUBCOMMANDS.items()},
}
HELP_FLAGS = frozenset({"--help", "-h"})
HELP_COMMANDS = HELP_FLAGS | {"help"}
VALUE_FLAGS = frozenset({
    "--run", "--by", "--executor", "--goal", "--context", "--suggested-file",
    "--depends-on", "--lens", "--ordered-lens-bundle", "--bound", "--pack",
    "--profile", "--independence", "--isolation", "--sequence", "--set",
    "--section", "--file", "--text", "--note", "--artifact", "--terminal",
    "--tree", "--reply-to", "--workspace", "--proposal", "--covered",
    "--cut-generation", "--correction-bound", "--now", "--dispatch-id",
    "--assignment-seal",
    "--lease-expires-at", "--replacement-dispatch-id", "--record-id", "--content",
    "--form", "--role", "--outcome-record-id", "--status", "--stage",
    "--review-kind",
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
