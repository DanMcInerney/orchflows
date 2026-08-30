"""The subcommand router, and the two improvement-channel writes.

What is left here after the family's commands moved to their owners: the
argv-to-handler table `--help` is read off, the usage answer that precedes
every argument, and `improvement` -- `run-state`'s sibling on the same
user-scope channel, kept beside the router because it writes no ticket and
belongs to no ticket module.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
if __package__:
    from . import console
    from .tickets_format import _extract_flag, _read_utf8
    from .tickets_issue import _cmd_new
    from .tickets_lifecycle import _cmd_check, _cmd_join_noop_repair, _cmd_list, _cmd_ready, _cmd_set_status, _cmd_show
    from .tickets_result import COVERAGE_RECORD_NAME, IMPROVEMENT_USAGE, PROPOSALS_DIR, _append_one_line, _cmd_result, _cmd_run_state
    from .tickets_attempts import _cmd_dispatch_commit, _cmd_dispatch_open, _cmd_dispatch_replace, _cmd_dispatch_retire
    from .tickets_dispatch_packet import _cmd_dispatch_packet, _cmd_dispatch_receive
    from .tickets_dispatch_receipt import _cmd_dispatch_receipt
    from .tickets_join import _cmd_dispatch_join
    from .tickets_outcome import _cmd_dispatch_outcome
    from .tickets_store import NO_SINK_ERROR, _cmd_repair_run_identity, _improvement_root, _segment_error, _write_identity
    from .tickets_worklog import _cmd_worklog
    from .tickets_commands import HELP_COMMANDS, HELP_FLAGS, SUBCOMMAND_SUMMARY, SUBCOMMAND_USAGE, VALUE_FLAGS, resolve_payload_flags
    from .tickets_lint import _cmd_lint
    from .tickets_bound import _cmd_bound_check
    from .tickets_grade import _cmd_gate, _cmd_grade
    from .tickets_dispatch_facade import _cmd_dispatch
    from .tickets_land import _cmd_land
    from .tickets_loop import _cmd_loop_advance, _cmd_loop_arm, _cmd_loop_evaluate
    from .tickets_instantiate import _cmd_instantiate, _cmd_stamp_generation, _sealed_template_snapshot, _template_stubs, git_head, render_stub
    from .tickets_seal import GENERATION_SUBCOMMANDS
    from .tickets_dispatch_gate import _cmd_checker_stage, _gate_body, _gate_input, _gate_sections, _gate_stub, _gate_under_run_lock, _input_name, _listed_items, _pack_domain
else:  # pragma: no cover - direct/installed flat script path
    import console
    from tickets_format import _extract_flag, _read_utf8
    from tickets_issue import _cmd_new
    from tickets_lifecycle import _cmd_check, _cmd_join_noop_repair, _cmd_list, _cmd_ready, _cmd_set_status, _cmd_show
    from tickets_result import COVERAGE_RECORD_NAME, IMPROVEMENT_USAGE, PROPOSALS_DIR, _append_one_line, _cmd_result, _cmd_run_state
    from tickets_attempts import _cmd_dispatch_commit, _cmd_dispatch_open, _cmd_dispatch_replace, _cmd_dispatch_retire
    from tickets_dispatch_packet import _cmd_dispatch_packet, _cmd_dispatch_receive
    from tickets_dispatch_receipt import _cmd_dispatch_receipt
    from tickets_join import _cmd_dispatch_join
    from tickets_outcome import _cmd_dispatch_outcome
    from tickets_store import NO_SINK_ERROR, _cmd_repair_run_identity, _improvement_root, _segment_error, _write_identity
    from tickets_worklog import _cmd_worklog
    from tickets_commands import HELP_COMMANDS, HELP_FLAGS, SUBCOMMAND_SUMMARY, SUBCOMMAND_USAGE, VALUE_FLAGS, resolve_payload_flags
    from tickets_lint import _cmd_lint
    _cmd_bound_check = __import__('tickets_bound')._cmd_bound_check
    _grade_module = __import__('tickets_grade'); _cmd_gate = _grade_module._cmd_gate; _cmd_grade = _grade_module._cmd_grade
    from tickets_dispatch_facade import _cmd_dispatch
    _cmd_land = __import__('tickets_land')._cmd_land
    _loop = __import__('tickets_loop')
    _cmd_loop_arm, _cmd_loop_evaluate, _cmd_loop_advance = (_loop._cmd_loop_arm, _loop._cmd_loop_evaluate, _loop._cmd_loop_advance)
    _instantiate_module = __import__('tickets_instantiate'); _cmd_instantiate = _instantiate_module._cmd_instantiate; _cmd_stamp_generation = _instantiate_module._cmd_stamp_generation
    _sealed_template_snapshot = _instantiate_module._sealed_template_snapshot; _template_stubs = _instantiate_module._template_stubs; git_head = _instantiate_module.git_head; render_stub = _instantiate_module.render_stub
    _gate_module = __import__('tickets_dispatch_gate'); _cmd_checker_stage = _gate_module._cmd_checker_stage; _gate_body = _gate_module._gate_body; _gate_input = _gate_module._gate_input; _gate_sections = _gate_module._gate_sections
    _gate_stub = _gate_module._gate_stub; _gate_under_run_lock = _gate_module._gate_under_run_lock; _input_name = _gate_module._input_name; _listed_items = _gate_module._listed_items; _pack_domain = _gate_module._pack_domain
    try: GENERATION_SUBCOMMANDS = __import__("tickets_seal").GENERATION_SUBCOMMANDS
    except ModuleNotFoundError: GENERATION_SUBCOMMANDS = {}
# Installed by `scripts/tickets.py` at facade import, never imported back up
# from here: the facade owns which seams it re-points, and a helper reaching
# up for that is the import cycle `tickets_store` used to close per write.
# `None` is a dispatcher loaded without its facade -- nothing to sync.
_sync_seams = None
def _help_requested(rest) -> bool:
    """Whether a help flag in ``rest`` stands as its own token.
    A help flag consumed as a value-taking flag's value is that value
    (``VALUE_FLAGS``), so ``--note --help`` writes the note and never
    answers usage: a run-state line whose text happens to be a help flag
    must not be swallowed silently.
    """
    return any((token in HELP_FLAGS and (i == 0 or rest[i - 1] not in VALUE_FLAGS) for i, token in enumerate(rest)))
def _cmd_help(command=None):
    """Usage, answered before any argument is resolved.
    A request for usage is a request this script serves, never an unhandled
    case it renders as the ordinary error path. It carries no ``error`` key
    and so exits 0, and it touches no repository: `--help` outside a
    checkout, or on a subcommand whose required arguments are absent, is
    still answerable and is the case a reader most often needs it in.
    """
    if command is None:
        return {'help': {'usage': 'tickets.py <subcommand> [options]', 'subcommands': {name: {'usage': SUBCOMMAND_USAGE[name], 'summary': SUBCOMMAND_SUMMARY[name]} for name in SUBCOMMAND_USAGE}, 'help': f"tickets.py {' | '.join(sorted(HELP_FLAGS))} | help, or <subcommand> --help", 'output': "exactly one JSON document on stdout; a payload carrying 'error' exits 1, every other payload exits 0"}}
    return {'help': {'subcommand': command, 'usage': SUBCOMMAND_USAGE[command], 'summary': SUBCOMMAND_SUMMARY[command]}}
def _cmd_improvement(rest):
    """Write an improvement evidence record into the one user-scope sink.
    ``_cmd_run_state``'s sibling, for the other two records the channel
    rules/visibility.md §6 covers: a proposal and the coverage record.
    Same root resolution, same two shapes — one whole-file, one
    single-call append — and the same refusal to reach for a fallback.
    ``--proposal`` is whole-file, safe because the name partitions it, and
    the name goes through ``_segment_error`` so nothing can climb out of
    ``proposals/``. ``--covered`` appends to a stream every pass shares, so
    it opens in append mode with an explicit ``newline`` and writes one
    line in one call: a read-modify-write here loses a concurrent writer's
    line, which is the whole reason the record is JSONL.
    Neither body is read, parsed or validated. This is a channel; what a
    proposal says and what a coverage line carries belong to
    the improvement composition.
    There is no fallback. A write that cannot reach the resolved root is
    reported as an error and lands nowhere else.
    """
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
        return {'error': 'missing subcommand: new | lint | bound-check | instantiate | grade | gate | checker-stage | stamp-generation | draft-validate | seal | list | show | ready | dispatch | land | loop-arm | loop-evaluate | loop-advance | dispatch-open | dispatch-commit | dispatch-retire | dispatch-replace | dispatch-outcome | dispatch-join | dispatch-packet | dispatch-receive | dispatch-receipt | check | set-status | join-noop-repair | result | worklog | run-state | repair-run-identity | improvement'}
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
    # reads the dispatched set off these comparisons, and a subcommand
    # reachable only through a lookup is one whose `--help` silently errs.
    if command == 'stamp-generation': return _cmd_stamp_generation(rest)
    if command == 'draft-validate': return GENERATION_SUBCOMMANDS[command][2](rest)
    if command == 'seal': return GENERATION_SUBCOMMANDS[command][2](rest)
    if command == 'instantiate': return _cmd_instantiate(rest)
    if command == 'grade': return _cmd_grade(rest)
    if command == 'gate': return _cmd_gate(rest)
    if command == 'checker-stage': return _cmd_checker_stage(rest)
    if command == 'list':
        return _cmd_list(rest)
    if command == 'show':
        return _cmd_show(rest)
    if command == 'ready':
        return _cmd_ready(rest)
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
    if command == 'land': return _cmd_land(rest)
    if command == 'loop-arm': return _cmd_loop_arm(rest)
    if command == 'loop-evaluate': return _cmd_loop_evaluate(rest)
    if command == 'loop-advance': return _cmd_loop_advance(rest)
    if command == 'dispatch-outcome':
        return _cmd_dispatch_outcome(rest)
    if command == 'dispatch-join':
        return _cmd_dispatch_join(rest)
    if command == 'dispatch-packet':
        return _cmd_dispatch_packet(rest)
    if command == 'dispatch-receive':
        return _cmd_dispatch_receive(rest)
    if command == 'dispatch-receipt':
        return _cmd_dispatch_receipt(rest)
    if command == 'check':
        return _cmd_check(rest)
    if command == 'set-status':
        return _cmd_set_status(rest)
    if command == 'join-noop-repair':
        return _cmd_join_noop_repair(rest)
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
