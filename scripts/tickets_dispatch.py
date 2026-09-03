"""The subcommand router, and the two improvement-channel writes.

The argv-to-handler table `--help` is read off, the usage answer that
precedes every argument, and `improvement` -- `run-state`'s sibling on the
same user-scope channel, kept beside the router because it writes no ticket
and belongs to no ticket module.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
if __package__:
    from . import console
    from .tickets_format import _extract_flag, _read_utf8
    from .tickets_issue import _cmd_new
    from .tickets_lifecycle import _cmd_list, _cmd_ready, _cmd_set_status, _cmd_show
    from .tickets_result import COVERAGE_RECORD_NAME, IMPROVEMENT_USAGE, PROPOSALS_DIR, _append_one_line, _cmd_result, _cmd_run_state
    from .tickets_attempts import _cmd_dispatch_commit, _cmd_dispatch_open, _cmd_dispatch_replace, _cmd_dispatch_retire
    from .tickets_join import _cmd_dispatch_join
    from .tickets_outcome import _cmd_dispatch_outcome
    from .tickets_store import NO_SINK_ERROR, _cmd_repair_run_identity, _improvement_root, _segment_error, _write_identity
    from .tickets_worklog import _cmd_worklog
    from .tickets_commands import HELP_COMMANDS, HELP_FLAGS, SUBCOMMAND_SUMMARY, SUBCOMMAND_USAGE, VALUE_FLAGS, resolve_payload_flags
    from .tickets_lint import _cmd_lint
    from .tickets_bound import _cmd_bound_check
    from .tickets_grade import _cmd_grade
    from .tickets_mint import _cmd_do, _cmd_judge
    from .tickets_frame import _cmd_frame_close, _cmd_frame_open
    from .tickets_dispatch_facade import _cmd_dispatch
    from .tickets_land import _cmd_land
else:  # pragma: no cover - direct/installed flat script path
    import console
    from tickets_format import _extract_flag, _read_utf8
    from tickets_issue import _cmd_new
    from tickets_lifecycle import _cmd_list, _cmd_ready, _cmd_set_status, _cmd_show
    from tickets_result import COVERAGE_RECORD_NAME, IMPROVEMENT_USAGE, PROPOSALS_DIR, _append_one_line, _cmd_result, _cmd_run_state
    from tickets_attempts import _cmd_dispatch_commit, _cmd_dispatch_open, _cmd_dispatch_replace, _cmd_dispatch_retire
    from tickets_join import _cmd_dispatch_join
    from tickets_outcome import _cmd_dispatch_outcome
    from tickets_store import NO_SINK_ERROR, _cmd_repair_run_identity, _improvement_root, _segment_error, _write_identity
    from tickets_worklog import _cmd_worklog
    from tickets_commands import HELP_COMMANDS, HELP_FLAGS, SUBCOMMAND_SUMMARY, SUBCOMMAND_USAGE, VALUE_FLAGS, resolve_payload_flags
    from tickets_lint import _cmd_lint
    _cmd_bound_check = __import__('tickets_bound')._cmd_bound_check
    _cmd_grade = __import__('tickets_grade')._cmd_grade
    _mint = __import__('tickets_mint'); _cmd_do = _mint._cmd_do; _cmd_judge = _mint._cmd_judge
    _frame = __import__('tickets_frame'); _cmd_frame_open = _frame._cmd_frame_open; _cmd_frame_close = _frame._cmd_frame_close
    from tickets_dispatch_facade import _cmd_dispatch
    _cmd_land = __import__('tickets_land')._cmd_land
# Installed by `scripts/tickets.py` at facade import, never imported back up
# from here: the facade owns which seams it re-points. `None` is a
# dispatcher loaded without its facade -- nothing to sync.
_sync_seams = None
def _help_requested(rest) -> bool:
    """Whether a help flag in ``rest`` stands as its own token."""
    return any((token in HELP_FLAGS and (i == 0 or rest[i - 1] not in VALUE_FLAGS) for i, token in enumerate(rest)))
def _cmd_help(command=None):
    """Usage, answered before any argument is resolved."""
    if command is None:
        return {'help': {'usage': 'tickets.py <subcommand> [options]', 'subcommands': {name: {'usage': SUBCOMMAND_USAGE[name], 'summary': SUBCOMMAND_SUMMARY[name]} for name in SUBCOMMAND_USAGE}, 'help': f"tickets.py {' | '.join(sorted(HELP_FLAGS))} | help, or <subcommand> --help", 'output': "exactly one JSON document on stdout; a payload carrying 'error' exits 1, every other payload exits 0"}}
    return {'help': {'subcommand': command, 'usage': SUBCOMMAND_USAGE[command], 'summary': SUBCOMMAND_SUMMARY[command]}}
def _cmd_improvement(rest):
    """Write an improvement evidence record into the one user-scope sink."""
    args = list(rest)
    proposal = _extract_flag(args, '--proposal')
    covered = _extract_flag(args, '--covered')
    file_arg = _extract_flag(args, '--file')
    text_arg = _extract_flag(args, '--text')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'improvement does not accept {stray}. usage: {IMPROVEMENT_USAGE}'}
    if args:
        return {'error': f'improvement takes no positional argument: got {args[0]}. usage: {IMPROVEMENT_USAGE}'}
    if (proposal is None) == (covered is None):
        return {'error': f'improvement takes one of --proposal <name> or --covered <line>. usage: {IMPROVEMENT_USAGE}'}
    body = None
    if proposal is not None:
        invalid = _segment_error('proposal name', proposal)
        if invalid is not None:
            return invalid
        if (file_arg is None) == (text_arg is None):
            return {'error': f'--proposal takes one of --file <path> or --text <string>. usage: {IMPROVEMENT_USAGE}'}
        if file_arg is not None:
            body, failure = _read_utf8(file_arg, 'body file')
            if failure is not None:
                return failure
        else:
            body = text_arg
    elif file_arg is not None or text_arg is not None:
        return {'error': f'--covered carries its own line; --file and --text belong to --proposal. usage: {IMPROVEMENT_USAGE}'}
    improvement_root = _improvement_root()
    if improvement_root is None:
        return {'error': NO_SINK_ERROR}
    try:
        if proposal is not None:
            path = improvement_root / PROPOSALS_DIR / proposal
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8', newline='\n') as handle:
                handle.write(body)
        else:
            path = improvement_root / COVERAGE_RECORD_NAME
            improvement_root.mkdir(parents=True, exist_ok=True)
            _append_one_line(path, covered.rstrip('\r\n') + '\n')
    except OSError as error:
        return {'error': f'unwritable improvement record: {error}'}
    return {'improvement': {'mode': 'proposal' if proposal is not None else 'covered', 'name': proposal, 'path': str(path)}}
def _dispatch(argv):
    if _sync_seams is not None:
        _sync_seams()
    if not argv:
        return {'error': 'missing subcommand: new | do | judge | frame-open | frame-close | lint | bound-check | grade | list | show | dispatch | land | dispatch-open | dispatch-commit | dispatch-retire | dispatch-replace | dispatch-outcome | dispatch-join | set-status | result | worklog | run-state | repair-run-identity | improvement'}
    command, rest = (argv[0], argv[1:])
    if command in HELP_COMMANDS:
        return _cmd_help()
    if command in SUBCOMMAND_USAGE and _help_requested(rest):
        return _cmd_help(command)
    rest, refusal = resolve_payload_flags(command, rest)
    if refusal is not None: return refusal
    if command == 'lint': return _cmd_lint(rest)
    if command == 'bound-check': return _cmd_bound_check(rest)
    if command == 'new': return _cmd_new(rest)
    # Named one per line, not folded into a membership test: `cli_help`
    # reads the dispatched set off these comparisons.
    if command == 'grade': return _cmd_grade(rest)
    if command == 'list':
        return _cmd_list(rest)
    if command == 'show':
        return _cmd_show(rest)
    if command == 'dispatch-open':
        return _cmd_dispatch_open(rest)
    if command == 'dispatch-commit':
        return _cmd_dispatch_commit(rest)
    if command == 'dispatch-retire':
        return _cmd_dispatch_retire(rest)
    if command == 'dispatch-replace':
        return _cmd_dispatch_replace(rest)
    if command == 'dispatch':
        return _cmd_dispatch(rest)
    if command == 'do': return _cmd_do(rest)
    if command == 'judge': return _cmd_judge(rest)
    if command == 'frame-open': return _cmd_frame_open(rest)
    if command == 'frame-close': return _cmd_frame_close(rest)
    if command == 'land': return _cmd_land(rest)
    if command == 'dispatch-outcome':
        return _cmd_dispatch_outcome(rest)
    if command == 'dispatch-join':
        return _cmd_dispatch_join(rest)
    if command == 'set-status':
        return _cmd_set_status(rest)
    if command == 'result':
        return _cmd_result(rest)
    if command == 'worklog':
        return _cmd_worklog(rest)
    if command == 'run-state':
        return _cmd_run_state(rest)
    if command == 'repair-run-identity':
        return _cmd_repair_run_identity(rest)
    if command == 'improvement':
        return _cmd_improvement(rest)
    return {'error': f'unknown subcommand: {command}'}
def main(argv=None):
    console.harden()
    arguments = sys.argv[1:] if argv is None else argv
    try:
        result = _dispatch(arguments)
    except Exception as error:
        result = {'error': str(error)}
    exit_code = result.pop('exit_code', None) if isinstance(result, dict) else None
    encoded = json.dumps(
        result, ensure_ascii=True, separators=(',', ':'), sort_keys=True,
    ) + '\n'
    try:
        sys.stdout.buffer.write(encoded.encode('ascii'))
        sys.stdout.buffer.flush()
    except AttributeError:
        sys.stdout.write(encoded)
    return (1 if 'error' in result else 0) if exit_code is None else int(exit_code)
