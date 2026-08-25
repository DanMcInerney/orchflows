"""Ticket dispatch support."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
if __package__:
    from .tickets_format import CUT_SECTIONS, EXECUTOR_SECTIONS, _remove_frontmatter_field, PACK_NAME_PREFIX, PACK_NAME_SUFFIX, PLACEHOLDER_RE, ROOT_EXECUTOR, TEMPLATE_FILE, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_all, _extract_flag, _parse_frontmatter, _read_utf8, _set_frontmatter_field, _split_commas, ticket_defects
else:
    from tickets_format import CUT_SECTIONS, EXECUTOR_SECTIONS, _remove_frontmatter_field, PACK_NAME_PREFIX, PACK_NAME_SUFFIX, PLACEHOLDER_RE, ROOT_EXECUTOR, TEMPLATE_FILE, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_all, _extract_flag, _parse_frontmatter, _read_utf8, _set_frontmatter_field, _split_commas, ticket_defects
if __package__:
    from .tickets_issue import AMENDABLE_STATUSES, AMEND_USAGE, GATE_ID_MARKER, NEW_DEFAULT_BOUND, NEW_USAGE, RECUT_USAGE, _cmd_amend, _cmd_new, _cmd_recut, _distinct_gate_lenses, _render_ticket
else:
    from tickets_issue import AMENDABLE_STATUSES, AMEND_USAGE, GATE_ID_MARKER, NEW_DEFAULT_BOUND, NEW_USAGE, RECUT_USAGE, _cmd_amend, _cmd_new, _cmd_recut, _distinct_gate_lenses, _render_ticket
if __package__:
    from .tickets_lifecycle import CHECKABLE_STATUSES, CHECK_USAGE, GRANTABLE_STATUSES, GRANT_USAGE, RESULT_GRADE_USAGE, _cmd_check, _cmd_claim, _cmd_grant, _cmd_list, _cmd_ready, _cmd_result_grade, _cmd_set_status
else:
    from tickets_lifecycle import CHECKABLE_STATUSES, CHECK_USAGE, GRANTABLE_STATUSES, GRANT_USAGE, RESULT_GRADE_USAGE, _cmd_check, _cmd_claim, _cmd_grant, _cmd_list, _cmd_ready, _cmd_result_grade, _cmd_set_status
if __package__:
    from .tickets_packet import CHECKER_PATH_EXECUTORS, GATE_CRITIQUE_ID, GATE_EXECUTORS, GATE_EXECUTOR_SECTIONS, GATE_REPAIR_ID, GATE_VERIFY_ID, _cmd_packet
else:
    from tickets_packet import CHECKER_PATH_EXECUTORS, GATE_CRITIQUE_ID, GATE_EXECUTORS, GATE_EXECUTOR_SECTIONS, GATE_REPAIR_ID, GATE_VERIFY_ID, _cmd_packet
if __package__:
    from .tickets_result import COVERAGE_RECORD_NAME, IMPROVEMENT_USAGE, PROPOSALS_DIR, RESULT_USAGE, RUN_STATE_USAGE, _append_one_line, _cmd_result, _cmd_run_state
else:
    from tickets_result import COVERAGE_RECORD_NAME, IMPROVEMENT_USAGE, PROPOSALS_DIR, RESULT_USAGE, RUN_STATE_USAGE, _append_one_line, _cmd_result, _cmd_run_state
if __package__:
    from .tickets_store import DEFAULT_RUN_STATE_TREE, NO_SINK_ERROR, RUN_STATE_TREES, _create_text_exclusively, _identity_update, _improvement_root, _load_ticket, _run_lock, _segment_error, _tickets_root, _write_identity, _write_text_atomically
else:
    from tickets_store import DEFAULT_RUN_STATE_TREE, NO_SINK_ERROR, RUN_STATE_TREES, _create_text_exclusively, _identity_update, _improvement_root, _load_ticket, _run_lock, _segment_error, _tickets_root, _write_identity, _write_text_atomically
if __package__:
    from .tickets_worklog import WORKLOG_USAGE, _closure_defects, _cmd_worklog, _run_tickets, _spec_field_defect, _template_order
else:
    from tickets_worklog import WORKLOG_USAGE, _closure_defects, _cmd_worklog, _run_tickets, _spec_field_defect, _template_order
if __package__:
    from .tickets_admission import batch_cohort, is_v2, root_cohort; from .tickets_emission import grade_run_emission; from .tickets_context import run_snapshot; from .tickets_generations import _root_payload, generation_identity; from .tickets_transitions import pending_admission, stamp; from .tickets_commands import STAMP_GENERATION_USAGE, GATE_USAGE, HELP_COMMANDS, HELP_FLAGS, INSTANTIATE_USAGE, LINT_USAGE, SUBCOMMAND_SUMMARY, SUBCOMMAND_USAGE, VALUE_FLAGS, resolve_payload_flags; from .tickets_lint import _cmd_lint; from .tickets_bound import _cmd_bound_check; from .tickets_reissue import _cmd_reissue
    from .tickets_input_producers import git_head, render_stub, render_ticket_inputs; from .tickets_generations import GENERATION_SUBCOMMANDS; from .tickets_gate_mutations import _canonical_gate_mutation_plan
    from .tickets_dispatch_gate import _gate_body, _gate_input, _gate_sections, _gate_stub, _gate_under_run_lock, _input_name, _listed_items, _pack_domain; from .tickets_dispatch_gate import _cmd_gate as _gate_command
else:
    from tickets_admission import batch_cohort, is_v2, root_cohort; from tickets_emission import grade_run_emission; from tickets_context import run_snapshot; from tickets_transitions import pending_admission, stamp; _generations = __import__('tickets_generations'); _root_payload = _generations._root_payload; generation_identity = _generations.generation_identity; from tickets_commands import STAMP_GENERATION_USAGE, GATE_USAGE, HELP_COMMANDS, HELP_FLAGS, INSTANTIATE_USAGE, LINT_USAGE, SUBCOMMAND_SUMMARY, SUBCOMMAND_USAGE, VALUE_FLAGS, resolve_payload_flags; from tickets_lint import _cmd_lint
    from tickets_input_producers import git_head, render_stub, render_ticket_inputs; from tickets_gate_mutations import _canonical_gate_mutation_plan
    _cmd_bound_check = __import__('tickets_bound')._cmd_bound_check; _cmd_reissue = __import__('tickets_reissue')._cmd_reissue  # by name: the family's import census is pinned
    _gate_module = __import__('tickets_dispatch_gate'); _gate_command = _gate_module._cmd_gate; _gate_body = _gate_module._gate_body; _gate_input = _gate_module._gate_input; _gate_sections = _gate_module._gate_sections
    _gate_stub = _gate_module._gate_stub; _gate_under_run_lock = _gate_module._gate_under_run_lock; _input_name = _gate_module._input_name; _listed_items = _gate_module._listed_items; _pack_domain = _gate_module._pack_domain
    try: GENERATION_SUBCOMMANDS = __import__("tickets_generations").GENERATION_SUBCOMMANDS
    except ModuleNotFoundError: GENERATION_SUBCOMMANDS = {}
def _cmd_gate(rest):
    """`gate`, with this module's HEAD probe sealed into the family.

    The probe is supplied from here rather than read inside the gate module
    so that one revision reaches every stub the family writes, and so that
    the seam a caller substitutes is the one this façade names.

    No version door stands in front of the builder any more: the builder
    emits at the root's declared version, and a member at the wrong one is
    the one grade's own `version-root-divergence` refusal at every door.
    """
    return _gate_command(rest, head_probe=git_head)
def _template_stubs(directory: Path, values: dict):
    """``(stubs, error)`` — every stub in the template, substituted and graded.
    ``stubs`` maps a stub id to its text and its dependency ids, in file
    order. Each stub is substituted first and graded after, because a
    placeholder standing where an executor or a bound belongs is a defect
    only until it is filled.
    """
    paths = sorted((path for path in directory.glob('*.md') if path.name != TEMPLATE_FILE))
    if not paths:
        return (None, {'error': f'template {directory} holds no stub: a template is {TEMPLATE_FILE} plus one or more <id>.md ticket stubs'})
    stubs = {}
    sources = []
    for path in paths:
        text, failure = _read_utf8(path, f'stub {path.name}')
        if failure is not None:
            return (None, failure)
        sources.append((path, text))
    for path, text in sources:
        text, render_error = render_stub(text, values)
        if render_error is not None:
            return (None, {'error': f'stub {path.stem} carries {render_error}'})
        defects = ticket_defects(text, stub=True)
        if defects:
            return (None, {'error': f'stub {path.stem} is off contract (contracts/work-item.md): ' + '; '.join(defects)})
        data = _parse_frontmatter(text)
        declared_id = str(data.get('id') or '').strip()
        if declared_id != path.stem:
            return (None, {'error': f"stub {path.name} names id '{declared_id}': a stub's id is its file stem, and `depends_on` names ids"})
        spec_defect = _spec_field_defect(text, directory)
        if spec_defect is not None:
            return (None, {'error': f'stub {path.stem}: {spec_defect}'})
        stubs[path.stem] = (text, list(data.get('depends_on') or []))
    return (stubs, None)
def _cmd_instantiate(rest):
    """Instantiate one template into one run's tickets.
    A template is a directory: ``template.md`` and one file per stub. What
    happens here is substitution, the same grading every issued ticket gets,
    the graph checks a directory of files cannot carry (edges, a cycle, the
    single terminal), and then one write per stub — in that order, so a
    template refused for its last stub has written none of the others.
    """
    args = list(rest)
    run = _extract_flag(args, '--run')
    settings = _extract_all(args, '--set')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'instantiate does not accept {stray}. usage: {INSTANTIATE_USAGE}'}
    if len(args) != 1:
        return {'error': f'usage: {INSTANTIATE_USAGE}'}
    if run is None:
        return {'error': f'instantiate requires --run <run>. usage: {INSTANTIATE_USAGE}'}
    invalid = _segment_error('run id', run)
    if invalid is not None:
        return invalid
    directory = Path(args[0])
    if not directory.is_dir():
        return {'error': f'template directory not found: {directory}'}
    template_path = directory / TEMPLATE_FILE
    if not template_path.is_file():
        return {'error': f"template directory {directory} has no {TEMPLATE_FILE}: it declares the template's name, entry and placeholders"}
    values = {}
    for setting in settings:
        key, separator, value = setting.partition('=')
        if not separator or not key.strip():
            return {'error': f"--set takes k=v: '{setting}' names no value. usage: {INSTANTIATE_USAGE}"}
        values[key.strip()] = value
    manifest, failure = _read_utf8(template_path, TEMPLATE_FILE)
    if failure is not None:
        return failure
    template = _parse_frontmatter(manifest)
    declared = template.get('placeholders')
    declared = declared if isinstance(declared, list) else []
    builtins = {'run': run}
    baseline = git_head()
    if baseline is not None:
        builtins['baseline'] = baseline
    # A declared builtin is supplied, not unsupplied. `run` and `baseline`
    # are this command's to fill, and a stub that names one must be able to
    # declare it: every `{{name}}` a stub uses has to appear in the
    # manifest's `placeholders` (tools/validate_support/structure.py), so
    # without this a template could use a builtin or validate, never both.
    unsupplied = [name for name in declared if name not in values and name not in builtins]
    if unsupplied:
        return {'error': f'{TEMPLATE_FILE} declares the placeholders {unsupplied} that no --set supplies'}
    stubs, error = _template_stubs(directory, {**values, **builtins})
    if error is not None:
        return error
    ordered, error = _template_order(stubs)
    if error is not None:
        return error
    unsubstituted = {}
    for stub_id, (_, dependencies) in stubs.items():
        text, failure = _read_utf8(directory / f'{stub_id}.md', f'stub {stub_id}.md')
        if failure is not None:
            return failure
        unsubstituted[stub_id] = (text, dependencies)
    closure = _closure_defects(unsubstituted)
    if closure:
        return {'error': '; '.join((message for _, message in closure))}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    run_dir = tickets_root / run
    rendered = []
    cohort = batch_cohort(ordered)
    for stub_id in ordered:
        text, dependencies = stubs[stub_id]
        # The stamp is the table's row, not this site's spelling of it: a
        # stub declaring one of the four v2 fields is a v2 producer, and a
        # hand-written `v1:pending` would leave its version and its
        # sentinel disagreeing from the moment the ticket exists.
        entry = stamp('stamp', 2 if is_v2(_parse_frontmatter(text)) else 1)
        text = _set_frontmatter_field(text, 'run', run)
        text = _set_frontmatter_field(text, 'status', entry.status)
        text = _set_frontmatter_field(text, 'admission', entry.admission)
        text = _set_frontmatter_field(text, 'cohort', cohort)
        for field in entry.blanks:
            text = _set_frontmatter_field(text, field, '')
        path = run_dir / f'{stub_id}.md'
        if GATE_ID_MARKER in stub_id:
            return {'error': f"template stub id '{stub_id}' is reserved for `tickets.py gate`; a template cannot assemble a partial or alternate gate family. Nothing was written"}
        rendered.append((path, text))
    incoming_roots = [path.stem for path, text in rendered if _executor_of(_parse_frontmatter(text)) == ROOT_EXECUTOR]
    written = []
    try:
        with _run_lock(run):
            for path, _ in rendered:
                if path.exists():
                    return {'error': f"ticket id '{path.stem}' is already issued in run '{run}': {path}. Nothing was written"}
            existing_roots = []
            for path in sorted(run_dir.glob('*.md')) if run_dir.is_dir() else []:
                loaded = _load_ticket(path)
                if 'error' not in loaded and _executor_of(loaded) == ROOT_EXECUTOR:
                    existing_roots.append(str(loaded.get('id') or path.stem))
            if existing_roots and incoming_roots:
                return {'error': f"run '{run}' would have root tickets {existing_roots + incoming_roots}: one physical run has one root and one composite gate. Nothing was written"}
            emission = grade_run_emission('instantiate', run, run_dir, {path.stem: text for path, text in rendered})
            if emission is not None:
                return {**emission, 'error': emission['error'] + '. Nothing was written'}
            identity_dir, identity, refusal = _identity_update(run, datetime.now(timezone.utc))
            if refusal is not None:
                return refusal
            run_dir.mkdir(parents=True, exist_ok=True)
            for path, text in rendered:
                _create_text_exclusively(path, text)
                written.append(path)
            if identity is not None:
                identity_dir.mkdir(parents=True, exist_ok=True)
                _write_identity(identity_dir, identity)
    except OSError as error:
        for path in written:
            path.unlink(missing_ok=True)
        return {'error': f'unwritable ticket: {error}. Nothing was written'}
    return {'instantiate': {'template': str(template.get('name') or directory.name), 'run': run, 'ids': ordered, 'paths': [str(path) for path, _ in rendered]}}
def _cmd_stamp_generation(rest):
    """Open the v2 generation lifecycle on one v1 root and its cut.

    `draft-validate` grades nothing that has not already declared itself
    v2 -- a `root_generation`, a seal, or a v2 admission -- and no
    subcommand wrote one. The only thing that produced the opt-in was a
    hand edit of the file in the sink: the one write path around every
    refusal the emitting doors apply to those same bytes, and so the way a
    root could enter the sealed lifecycle carrying whatever a hand left on
    it. This is that write, under the run lock, graded before it lands.

    It sits here beside `instantiate` rather than in `tickets_generations`
    because that module is the generation algebra and is at its source
    ceiling; what it exports is called, not extended.

    The identity comes from the exact snapshot, so a stamp is reproducible
    from what it stamped. The v1 cohort is dropped as the stamp is
    written: a v2 ticket is frozen by its assignment seal, and a member
    carrying both is one two mechanisms claim at once.

    Refused on a cut any member of which is already taken up -- a stamp
    rewrites the assignment a member is graded against, and doing that
    under a working executor is the moving target rules/verification.md §3
    forbids.
    """
    args = list(rest)
    if len(args) != 2:
        return {'error': f'usage: {STAMP_GENERATION_USAGE}'}
    run, root_id = args
    for kind, value in (('run id', run), ('ticket id', root_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None: return invalid
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    run_dir = tickets_root / run
    try:
        with _run_lock(run):
            snapshot, unreadable = run_snapshot(run_dir) if run_dir.is_dir() else ({}, [])
            if unreadable:
                return {'error': f'unreadable ticket: {unreadable[0][0]}'}
            if root_id not in snapshot:
                return {'error': f'root ticket not found in exact snapshot: {root_id}'}
            members = [root_id] + sorted(i for i in snapshot if i.startswith(root_id + '.'))
            for member_id in members:
                data = _parse_frontmatter(snapshot[member_id])
                status = str(data.get('status') or '')
                if status not in AMENDABLE_STATUSES or str(data.get('claimed_by') or '').strip():
                    return {'error': f"stamp-generation refused: {run}/{member_id} is '{status or '<missing>'}', and a stamp rewrites the assignment it would be working against (rules/verification.md §3). Nothing was written"}
                if is_v2(data):
                    return {'error': f'stamp-generation refused: {run}/{member_id} already carries a v2 generation; the lifecycle is opened once. Nothing was written'}
            if _executor_of(_parse_frontmatter(snapshot[root_id])) != ROOT_EXECUTOR:
                return {'error': f'stamp-generation refused: {run}/{root_id} is not a root ticket, and a root generation belongs to a root. Nothing was written'}
            identity = generation_identity('root', root_id, 1, _root_payload(root_id, snapshot))
            stamped = {}
            for member_id in members:
                text = _set_frontmatter_field(snapshot[member_id], 'root_generation', identity)
                text = _set_frontmatter_field(text, 'admission', pending_admission(2))
                stamped[member_id] = _remove_frontmatter_field(text, 'cohort')
            emission = grade_run_emission('stamp-generation', run, run_dir, stamped, repairs=True)
            if emission is not None:
                return {**emission, 'error': emission['error'] + '. Nothing was written'}
            written = {}
            try:
                for member_id, text in stamped.items():
                    written[member_id] = snapshot[member_id]
                    _write_text_atomically(run_dir / f'{member_id}.md', text)
            except OSError:
                for member_id, text in written.items():
                    _write_text_atomically(run_dir / f'{member_id}.md', text)
                raise
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return {'error': str(error)}
    return {'stamp_generation': {'root_generation': identity, 'run': run, 'root_id': root_id, 'ids': members, 'state': 'drafting'}}
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
    ``orch-self-improve``.
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
    if __package__:
        from .tickets import _sync_seams
    else:
        from tickets import _sync_seams
    _sync_seams()
    if not argv:
        return {'error': 'missing subcommand: new | amend | recut | reissue | lint | bound-check | instantiate | gate | stamp-generation | draft-validate | seal | amendment-request | list | ready | claim | grant | check | set-status | result-grade | packet | result | worklog | run-state | improvement'}
    command, rest = (argv[0], argv[1:])
    if command in HELP_COMMANDS:
        return _cmd_help()
    if command in SUBCOMMAND_USAGE and _help_requested(rest):
        return _cmd_help(command)
    rest, refusal = resolve_payload_flags(command, rest)
    if refusal is not None: return refusal
    if command == 'lint': return _cmd_lint(rest)
    if command == 'bound-check': return _cmd_bound_check(rest)
    if command == 'reissue': return _cmd_reissue(rest)
    if command == 'new': return _cmd_new(rest)
    if command == 'amend': return _cmd_amend(rest)
    if command == 'recut': return _cmd_recut(rest)
    # Named one per line, not folded into a membership test: `cli_help`
    # reads the dispatched set off these comparisons, and a subcommand
    # reachable only through a lookup is one whose `--help` silently errs.
    if command == 'stamp-generation': return _cmd_stamp_generation(rest)
    if command == 'draft-validate': return GENERATION_SUBCOMMANDS[command][2](rest)
    if command == 'seal': return GENERATION_SUBCOMMANDS[command][2](rest)
    if command == 'amendment-request': return GENERATION_SUBCOMMANDS[command][2](rest)
    if command == 'instantiate': return _cmd_instantiate(rest)
    if command == 'gate': return _cmd_gate(rest)
    if command == 'list':
        return _cmd_list(rest)
    if command == 'ready':
        return _cmd_ready(rest)
    if command == 'claim':
        return _cmd_claim(rest)
    if command == 'grant':
        return _cmd_grant(rest)
    if command == 'check':
        return _cmd_check(rest)
    if command == 'set-status':
        return _cmd_set_status(rest)
    if command == 'result-grade':
        return _cmd_result_grade(rest)
    if command == 'packet':
        return _cmd_packet(rest)
    if command == 'result':
        return _cmd_result(rest)
    if command == 'worklog':
        return _cmd_worklog(rest)
    if command == 'run-state':
        return _cmd_run_state(rest)
    if command == 'improvement':
        return _cmd_improvement(rest)
    return {'error': f'unknown subcommand: {command}'}
def main(argv=None):
    try:
        sys.stdout.reconfigure(errors='replace')
    except (AttributeError, ValueError):
        pass
    arguments = sys.argv[1:] if argv is None else argv
    try:
        result = _dispatch(arguments)
    except Exception as error:
        result = {'error': str(error)}
    exit_code = result.pop('exit_code', None) if isinstance(result, dict) else None
    print(json.dumps(result, ensure_ascii=False))
    return (1 if 'error' in result else 0) if exit_code is None else int(exit_code)
