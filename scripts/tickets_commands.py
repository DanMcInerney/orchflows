"""Closed ticket subcommand and help tables."""
from __future__ import annotations

import sys
from pathlib import Path

if __package__:
    from .tickets_format import EXECUTOR_SECTIONS, TERMINAL_STATES, VALID_STATUSES, _read_utf8
    from .tickets_issue import NEW_USAGE
    from .tickets_lifecycle import CHECKABLE_STATUSES, CHECK_USAGE, JOIN_NOOP_REPAIR_USAGE
    from .tickets_packet import CHECKER_PATH_EXECUTORS, PACKET_USAGE
    from .tickets_result import IMPROVEMENT_USAGE, RESULT_USAGE, RUN_STATE_USAGE
    from .tickets_store import DEFAULT_RUN_STATE_TREE, RUN_STATE_TREES
    from .tickets_worklog import WORKLOG_USAGE
    from .tickets_generations import GENERATION_SUBCOMMANDS
else:
    from tickets_format import EXECUTOR_SECTIONS, TERMINAL_STATES, VALID_STATUSES, _read_utf8
    from tickets_issue import NEW_USAGE
    from tickets_lifecycle import CHECKABLE_STATUSES, CHECK_USAGE, JOIN_NOOP_REPAIR_USAGE
    from tickets_packet import CHECKER_PATH_EXECUTORS, PACKET_USAGE
    from tickets_result import IMPROVEMENT_USAGE, RESULT_USAGE, RUN_STATE_USAGE
    from tickets_store import DEFAULT_RUN_STATE_TREE, RUN_STATE_TREES
    from tickets_worklog import WORKLOG_USAGE
    GENERATION_SUBCOMMANDS = __import__("tickets_generations").GENERATION_SUBCOMMANDS

LINT_USAGE = "lint (<run> <id> | --file <path> [--executor E] [--pack P]) [--fix]"
INSTANTIATE_USAGE = "instantiate <template-dir> --run <run> [--set k=v ...]"
GATE_USAGE = "gate <run> <root-id> [--lens <name>[,<name>] | --ordered-lens-bundle <name>[,<name>]]"
BOUND_CHECK_USAGE = "bound-check <run> [--now <iso>]"
STAMP_GENERATION_USAGE = "stamp-generation <run> <root-id>"
SUBCOMMAND_USAGE = {
    "new": NEW_USAGE,
    "instantiate": INSTANTIATE_USAGE,
    "gate": GATE_USAGE,
    "stamp-generation": STAMP_GENERATION_USAGE,
    "list": "list [--run R]",
    "ready": "ready [--run R]",
    "claim": "claim <run> <id> --by <name>",
    "check": CHECK_USAGE,
    "set-status": "set-status <run> <id> <status>",
    "join-noop-repair": JOIN_NOOP_REPAIR_USAGE,
    "packet": PACKET_USAGE,
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
    "gate": "Create blocker-only critique/repair/verify tickets; repair handles actual overlap and Git conflicts.",
    "stamp-generation": "Stamp one unclaimed direct or decomposed root and its members.",
    "list": "List tickets.",
    "ready": "Promote sealed tickets whose dependencies are complete.",
    "claim": "Claim one ready ticket.",
    "check": f"Record one blocker-only checker pass while status is one of {sorted(CHECKABLE_STATUSES)}.",
    "set-status": f"Set lifecycle status to one of {sorted(VALID_STATUSES)}.",
    "join-noop-repair": "Atomically attribute and complete a clean repair at the join without dispatch.",
    "packet": f"Emit a semantic dispatch packet; --executor may be {' or '.join(CHECKER_PATH_EXECUTORS)}.",
    "result": f"Append one executor-owned record section {list(EXECUTOR_SECTIONS)}.",
    "worklog": "Render the run worklog.",
    "run-state": f"Write run state under {list(RUN_STATE_TREES)} (default {DEFAULT_RUN_STATE_TREE}).",
    "improvement": "Write improvement evidence.",
    "bound-check": "Report live claims against their operational bound.",
    "lint": "Report current contract, ceiling, seal, and admission findings.",
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
    "--cut-generation", "--correction-bound", "--now",
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
