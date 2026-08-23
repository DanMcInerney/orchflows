"""The closed subcommand tables, and the payload flags that name a file.

Pure tables: dispatch reads them, and a later subcommand extends them here
rather than in a router already at the source-size ceiling. Nothing in this
module reads the sink or writes anything; the one behaviour it owns is
``resolve_payload_flags``, which turns a payload named by a path -- or by
``-``, meaning stdin -- into the literal value the owning command already
knows how to read, before the router sees it.
"""
from __future__ import annotations
import sys
from pathlib import Path
if __package__:
    from .tickets_format import CUT_SECTIONS, EXECUTOR_SECTIONS, TERMINAL_STATES, VALID_STATUSES, _read_utf8
    from .tickets_issue import AMENDABLE_STATUSES, AMEND_USAGE, NEW_USAGE, RECUT_USAGE
    from .tickets_lifecycle import CHECKABLE_STATUSES, CHECK_USAGE, GRANTABLE_STATUSES, GRANT_USAGE, RESULT_GRADE_USAGE
    from .tickets_packet import CHECKER_PATH_EXECUTORS
    from .tickets_result import IMPROVEMENT_USAGE, RESULT_USAGE, RUN_STATE_USAGE
    from .tickets_store import DEFAULT_RUN_STATE_TREE, RUN_STATE_TREES
    from .tickets_worklog import WORKLOG_USAGE
    from .tickets_generations import GENERATION_SUBCOMMANDS
else:
    from tickets_format import CUT_SECTIONS, EXECUTOR_SECTIONS, TERMINAL_STATES, VALID_STATUSES, _read_utf8
    from tickets_issue import AMENDABLE_STATUSES, AMEND_USAGE, NEW_USAGE, RECUT_USAGE
    from tickets_lifecycle import CHECKABLE_STATUSES, CHECK_USAGE, GRANTABLE_STATUSES, GRANT_USAGE, RESULT_GRADE_USAGE
    from tickets_packet import CHECKER_PATH_EXECUTORS
    from tickets_result import IMPROVEMENT_USAGE, RESULT_USAGE, RUN_STATE_USAGE
    from tickets_store import DEFAULT_RUN_STATE_TREE, RUN_STATE_TREES
    from tickets_worklog import WORKLOG_USAGE
    try: GENERATION_SUBCOMMANDS = __import__("tickets_generations").GENERATION_SUBCOMMANDS
    except ModuleNotFoundError: GENERATION_SUBCOMMANDS = {}
LINT_USAGE = 'lint (<run> <id> | --file <path> [--executor E] [--pack P]) [--fix]'
INSTANTIATE_USAGE = 'instantiate <template-dir> --run <run> [--set k=v ...]'
GATE_USAGE = 'gate <run> <root-id> [--lens <name>[,<name>]] [--write-scope <path>[,<path>]] [--acceptance-from <id>]'
SUBCOMMAND_USAGE = {'new': NEW_USAGE, 'amend': AMEND_USAGE, 'instantiate': INSTANTIATE_USAGE, 'gate': GATE_USAGE, 'list': 'list [--run R]', 'ready': 'ready [--run R]', 'claim': 'claim <run> <id> --by <name>', 'grant': GRANT_USAGE, 'check': CHECK_USAGE, 'set-status': 'set-status <run> <id> <status>', 'result-grade': RESULT_GRADE_USAGE, 'packet': f"packet <run> <id> --reply-to <name> [--workspace <path>] [--executor {' | '.join(CHECKER_PATH_EXECUTORS)}]", 'result': RESULT_USAGE, 'worklog': WORKLOG_USAGE, 'run-state': RUN_STATE_USAGE, 'improvement': IMPROVEMENT_USAGE, **{name: values[0] for name, values in GENERATION_SUBCOMMANDS.items()}}
SUBCOMMAND_SUMMARY = {'new': 'Issue one ticket into the run, refusing any shape `ticket_defects` reports before anything is written; --file places one already written.', 'amend': f'Repair one cut-time section {list(CUT_SECTIONS)} of an issued ticket, through the same refusal `new` applies; refused once the ticket is claimed or has left {sorted(AMENDABLE_STATUSES)}, and never a section the executor writes (that is `result`).', 'instantiate': "Instantiate one template directory into a run's tickets: placeholders filled, every stub graded, the graph checked for edges, cycles and its single terminal, then written all or none.", 'gate': "Write one root ticket's gate stubs: a read-only critique per lens (--lens; absent, the stamped pack's domain) over the root's whole cut subtree, one repair holding the scope (the root's own, unless --write-scope names one) behind them all, and one verify carrying the acceptance verbatim. Refused if the root has no subtree yet, or if a stub already exists.", 'list': 'Every ticket in the tracker, or in one run, as summaries.', 'ready': 'The tickets whose dependencies are complete and whose claim is free or stale; promotes an eligible `pending` to `ready`.', 'claim': 'Take one ready or stale ticket, losing the race rather than overwriting a live claim.', 'grant': f"Record one caller-side widening of a claimed item's write scope — the paths, the granting caller and the time — as frontmatter bookkeeping every reader of the item's authority then honours. Refused on a ticket that is not {sorted(GRANTABLE_STATUSES)}: before a claim the cut owns the scope.", 'check': f"Record the rules/verification.md §10 checker's pass on one claimed item — `checked_by`, the name the join reads that item's `authored-here` acceptance from. Refused on a ticket that is not {sorted(CHECKABLE_STATUSES)}.", 'set-status': f"Set one ticket's status; complete repeats result-grade before writing. One of {sorted(VALID_STATUSES)}.", 'result-grade': 'Read-only grade of the optional return-size constraint against the resolved result identity.', 'packet': f"The by-reference dispatch packet for one ticket: path, parts, and the commands the child runs from its own workspace. --executor ({' | '.join(CHECKER_PATH_EXECUTORS)}) emits it for one further rules/verification.md §10 child on the same claimed item instead — the checker, which corrects inside the ticket's write scope and records its pass through `check`, or the re-verifier, which is granted no write.", 'result': f"Write one of the executor's own sections {list(EXECUTOR_SECTIONS)}; a section already carrying content is refused without --append or --replace.", 'worklog': "Render this run's worklog view from its tickets — goal, iterations, failed approaches, queued scope, terminal — as markdown on the payload; --write also puts it at the run's worklog path, replacing a view rendered here and never a worklog written by anything else.", 'run-state': f"Write this run's state under the one user-scope sink, in one of {list(RUN_STATE_TREES)} (default {DEFAULT_RUN_STATE_TREE}); an artifact that already exists is refused without --replace. --terminal closes the run's notes, one of {list(TERMINAL_STATES)}, after which no note is written.", 'improvement': 'Write one improvement evidence record under the sink: a named proposal file, or one appended line of the coverage record.', **{name: values[1] for name, values in GENERATION_SUBCOMMANDS.items()}}
SUBCOMMAND_USAGE['recut'] = RECUT_USAGE
SUBCOMMAND_SUMMARY['recut'] = 'Replace one pending or ready cut from a candidate file, preserving executor-owned sections and invalidating its unsealed cohorts.'
HELP_FLAGS = frozenset({'--help', '-h'})
HELP_COMMANDS = HELP_FLAGS | {'help'}
VALUE_FLAGS = frozenset({'--run', '--by', '--executor', '--objective', '--criterion', '--depends-on', '--write-scope', '--lens', '--acceptance-from', '--bound', '--pack', '--input', '--excluded', '--profile', '--independence', '--isolation', '--cohort', '--return-fields', '--set', '--section', '--file', '--text', '--note', '--artifact', '--terminal', '--tree', '--reply-to', '--workspace', '--proposal', '--covered', '--cut-generation', '--correction-bound', '--record'})
BOUND_CHECK_USAGE = 'bound-check <run> [--now <iso>]'
SUBCOMMAND_USAGE['bound-check'] = BOUND_CHECK_USAGE
SUBCOMMAND_SUMMARY['bound-check'] = "Every live claim in one run measured against its own bound -- the bound as written, the kind the grammar read it as, its minutes, the claim time, the last motion on the item, the elapsed minutes, whether it is overdue, and whether nothing has moved since the bound elapsed. Exits 1 when any is overdue, so a re-check reads the answer off the status alone; --now pins the clock."
SUBCOMMAND_USAGE['lint'] = LINT_USAGE
SUBCOMMAND_SUMMARY['lint'] = "Report every finding a later `new`, `ready`, `claim` or `packet` would refuse one ticket or draft for -- contract defects, the instruction ceiling with its count and overage, admission, the graded result, and the whole-suite oracle -- as one list rather than the first one reached. --fix rewrites only the syntactic ones, and only on a draft or an unclaimed ticket."
VALUE_FLAGS = VALUE_FLAGS | {'--record-file'}
def read_payload(source, subject: str='payload file'):
    """One flag's value read from a file, or from stdin when ``source`` is ``-``.

    Decoded as UTF-8 exactly, because the payloads that need a file at all
    are the ones a shell mangles: quotes, backticks, dollars, newlines, and
    glyphs outside the console codepage.
    """
    if source == '-':
        try:
            return (sys.stdin.buffer.read().decode('utf-8'), None)
        except (OSError, ValueError, UnicodeDecodeError, AttributeError) as error:
            return (None, {'error': f'unreadable {subject}: {error}'})
    return _read_utf8(Path(source), subject)
def resolve_payload_flags(command: str, rest):
    """``(argv, None)`` with any by-file payload replaced by its literal value.

    Resolved before the router, so the owning subcommand keeps one code path
    for a payload however it arrived. ``run-state --note --file <path>``
    fills the note; ``amendment-request --record-file <path>`` fills
    ``--record``, stripped because canonical JSON carries no surrounding
    whitespace and a file carries a trailing newline.
    """
    args = list(rest)
    if command == 'run-state' and '--note' in args:
        at = args.index('--note')
        if at + 1 >= len(args) or args[at + 1] != '--file':
            return (args, None)
        if at + 2 >= len(args):
            return (None, {'error': f'run-state --note --file takes one path, or - for stdin. usage: {RUN_STATE_USAGE}'})
        body, failure = read_payload(args[at + 2], 'note file')
        return (None, failure) if failure is not None else (args[:at + 1] + [body] + args[at + 3:], None)
    if command == 'amendment-request' and '--record-file' in args:
        at = args.index('--record-file')
        if at + 1 >= len(args):
            return (None, {'error': f"amendment-request --record-file takes one path, or - for stdin. usage: {SUBCOMMAND_USAGE.get('amendment-request', 'amendment-request')}"})
        encoded, failure = read_payload(args[at + 1], 'amendment request file')
        return (None, failure) if failure is not None else (args[:at] + ['--record', encoded.strip()] + args[at + 2:], None)
    return (args, None)
