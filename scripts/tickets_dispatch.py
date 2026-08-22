"""Ticket dispatch support."""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone
if __package__:
    from .tickets_format import CUT_SECTIONS, EXECUTOR_SECTIONS, PACK_NAME_PREFIX, PACK_NAME_SUFFIX, PLACEHOLDER_RE, ROOT_EXECUTOR, TEMPLATE_FILE, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_all, _extract_flag, _parse_frontmatter, _read_utf8, _set_frontmatter_field, _split_commas, ticket_defects
else:
    from tickets_format import CUT_SECTIONS, EXECUTOR_SECTIONS, PACK_NAME_PREFIX, PACK_NAME_SUFFIX, PLACEHOLDER_RE, ROOT_EXECUTOR, TEMPLATE_FILE, TERMINAL_STATES, VALID_STATUSES, _executor_of, _extract_all, _extract_flag, _parse_frontmatter, _read_utf8, _set_frontmatter_field, _split_commas, ticket_defects
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
    from .tickets_store import DEFAULT_RUN_STATE_TREE, NO_SINK_ERROR, RUN_STATE_TREES, _create_text_exclusively, _identity_update, _improvement_root, _load_ticket, _run_lock, _segment_error, _tickets_root, _write_identity
else:
    from tickets_store import DEFAULT_RUN_STATE_TREE, NO_SINK_ERROR, RUN_STATE_TREES, _create_text_exclusively, _identity_update, _improvement_root, _load_ticket, _run_lock, _segment_error, _tickets_root, _write_identity
if __package__:
    from .tickets_worklog import WORKLOG_USAGE, _closure_defects, _cmd_worklog, _run_tickets, _spec_field_defect, _template_order
else:
    from tickets_worklog import WORKLOG_USAGE, _closure_defects, _cmd_worklog, _run_tickets, _spec_field_defect, _template_order
if __package__:
    from .tickets_admission import ADMISSION_PENDING, batch_cohort, root_cohort
    from .tickets_input_producers import git_head, render_stub, render_ticket_inputs; from .tickets_generations import GENERATION_SUBCOMMANDS
else:
    from tickets_admission import ADMISSION_PENDING, batch_cohort, root_cohort
    from tickets_input_producers import git_head, render_stub, render_ticket_inputs
    try: from tickets_generations import GENERATION_SUBCOMMANDS
    except ModuleNotFoundError: GENERATION_SUBCOMMANDS = {}
INSTANTIATE_USAGE = 'instantiate <template-dir> --run <run> [--set k=v ...]'
GATE_USAGE = 'gate <run> <root-id> [--lens <name>[,<name>]] [--write-scope <path>[,<path>]] [--acceptance-from <id>]'
SUBCOMMAND_USAGE = {'new': NEW_USAGE, 'amend': AMEND_USAGE, 'instantiate': INSTANTIATE_USAGE, 'gate': GATE_USAGE, 'list': 'list [--run R]', 'ready': 'ready [--run R]', 'claim': 'claim <run> <id> --by <name>', 'grant': GRANT_USAGE, 'check': CHECK_USAGE, 'set-status': 'set-status <run> <id> <status>', 'result-grade': RESULT_GRADE_USAGE, 'packet': f"packet <run> <id> --reply-to <name> [--workspace <path>] [--executor {' | '.join(CHECKER_PATH_EXECUTORS)}]", 'result': RESULT_USAGE, 'worklog': WORKLOG_USAGE, 'run-state': RUN_STATE_USAGE, 'improvement': IMPROVEMENT_USAGE, **{name: values[0] for name, values in GENERATION_SUBCOMMANDS.items()}}
SUBCOMMAND_SUMMARY = {'new': 'Issue one ticket into the run, refusing any shape `ticket_defects` reports before anything is written; --file places one already written.', 'amend': f'Repair one cut-time section {list(CUT_SECTIONS)} of an issued ticket, through the same refusal `new` applies; refused once the ticket is claimed or has left {sorted(AMENDABLE_STATUSES)}, and never a section the executor writes (that is `result`).', 'instantiate': "Instantiate one template directory into a run's tickets: placeholders filled, every stub graded, the graph checked for edges, cycles and its single terminal, then written all or none.", 'gate': "Write one root ticket's gate stubs: a read-only critique per lens (--lens; absent, the stamped pack's domain) over the root's whole cut subtree, one repair holding the scope (the root's own, unless --write-scope names one) behind them all, and one verify carrying the acceptance verbatim. Refused if the root has no subtree yet, or if a stub already exists.", 'list': 'Every ticket in the tracker, or in one run, as summaries.', 'ready': 'The tickets whose dependencies are complete and whose claim is free or stale; promotes an eligible `pending` to `ready`.', 'claim': 'Take one ready or stale ticket, losing the race rather than overwriting a live claim.', 'grant': f"Record one caller-side widening of a claimed item's write scope — the paths, the granting caller and the time — as frontmatter bookkeeping every reader of the item's authority then honours. Refused on a ticket that is not {sorted(GRANTABLE_STATUSES)}: before a claim the cut owns the scope.", 'check': f"Record the rules/verification.md §10 checker's pass on one claimed item — `checked_by`, the name the join reads that item's `authored-here` acceptance from. Refused on a ticket that is not {sorted(CHECKABLE_STATUSES)}.", 'set-status': f"Set one ticket's status; complete repeats result-grade before writing. One of {sorted(VALID_STATUSES)}.", 'result-grade': 'Read-only grade of the optional return-size constraint against the resolved result identity.', 'packet': f"The by-reference dispatch packet for one ticket: path, parts, and the commands the child runs from its own workspace. --executor ({' | '.join(CHECKER_PATH_EXECUTORS)}) emits it for one further rules/verification.md §10 child on the same claimed item instead — the checker, which corrects inside the ticket's write scope and records its pass through `check`, or the re-verifier, which is granted no write.", 'result': f"Write one of the executor's own sections {list(EXECUTOR_SECTIONS)}; a section already carrying content is refused without --append or --replace.", 'worklog': "Render this run's worklog view from its tickets — goal, iterations, failed approaches, queued scope, terminal — as markdown on the payload; --write also puts it at the run's worklog path, replacing a view rendered here and never a worklog written by anything else.", 'run-state': f"Write this run's state under the one user-scope sink, in one of {list(RUN_STATE_TREES)} (default {DEFAULT_RUN_STATE_TREE}); an artifact that already exists is refused without --replace. --terminal closes the run's notes, one of {list(TERMINAL_STATES)}, after which no note is written.", 'improvement': 'Write one improvement evidence record under the sink: a named proposal file, or one appended line of the coverage record.', **{name: values[1] for name, values in GENERATION_SUBCOMMANDS.items()}}
SUBCOMMAND_USAGE['recut'] = RECUT_USAGE
SUBCOMMAND_SUMMARY['recut'] = 'Replace one pending or ready cut from a candidate file, preserving executor-owned sections and invalidating its unsealed cohorts.'
HELP_FLAGS = frozenset({'--help', '-h'})
HELP_COMMANDS = HELP_FLAGS | {'help'}
VALUE_FLAGS = frozenset({'--run', '--by', '--executor', '--objective', '--criterion', '--depends-on', '--write-scope', '--lens', '--acceptance-from', '--bound', '--pack', '--input', '--excluded', '--profile', '--independence', '--isolation', '--cohort', '--return-fields', '--set', '--section', '--file', '--text', '--note', '--artifact', '--terminal', '--tree', '--reply-to', '--workspace', '--proposal', '--covered', '--cut-generation', '--correction-bound', '--record'})
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
    unsupplied = [name for name in declared if name not in values]
    if unsupplied:
        return {'error': f'{TEMPLATE_FILE} declares the placeholders {unsupplied} that no --set supplies'}
    builtins = {'run': run}
    baseline = git_head()
    if baseline is not None:
        builtins['baseline'] = baseline
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
        text = _set_frontmatter_field(text, 'run', run)
        text = _set_frontmatter_field(text, 'status', 'pending')
        text = _set_frontmatter_field(text, 'admission', ADMISSION_PENDING)
        text = _set_frontmatter_field(text, 'cohort', cohort)
        text = _set_frontmatter_field(text, 'claimed_by', '')
        text = _set_frontmatter_field(text, 'claimed_at', '')
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
def _pack_domain(pack) -> str:
    """The domain label of a stamped pack: `orch-code-pack` -> `code`.
    contracts/pack-signature.md's `lens` cell binds `orch-critique` with the
    pack's craft `## Lens` and names no label of its own, so there is one
    label a caller never has to invent: the domain the pack is named for.
    """
    name = str(pack or '').strip()
    if name.startswith(PACK_NAME_PREFIX):
        name = name[len(PACK_NAME_PREFIX):]
    if name.endswith(PACK_NAME_SUFFIX):
        name = name[:-len(PACK_NAME_SUFFIX)]
    return name
def _gate_stub(run: str, ticket_id: str, executor: str, depends_on: list, write_scope: list, sections: list, pack=None, cohort=None, inherited_inputs='', baseline=None) -> str:
    normalized_scope = [str(path).replace('\\', '/') for path in write_scope]
    mutations = [f"{'write' if path.endswith('/') else 'change'}:{path}" for path in normalized_scope]
    fields = {'id': ticket_id, 'run': run, 'status': 'pending', 'admission': ADMISSION_PENDING, 'cohort': cohort or root_cohort(ticket_id.split('.gate.', 1)[0]), 'executor': executor, 'pack': pack, 'independence': 'gate', 'depends_on': list(depends_on), 'write_scope': list(write_scope), 'mutations': mutations, 'bound': NEW_DEFAULT_BOUND, 'claimed_by': '', 'claimed_at': ''}
    text, error = render_ticket_inputs(_render_ticket(fields, sections), run, inherited_inputs, baseline=baseline)
    if error is not None:
        raise ValueError(error)
    return text
def _gate_sections(kind: str, root_id: str, lens: str, scope: list, acceptance_id: str, acceptance: str, units: list, run: str='') -> list:
    """The body of one gate stub. One place, so the three read as one gate."""
    return _gate_body(kind, root_id, lens, scope, acceptance_id, acceptance, units, run) + GATE_EXECUTOR_SECTIONS
def _listed_items(values, indent: str='') -> str:
    """A frontmatter list stated in prose as the items it holds.
    Never the Python repr of the list. An executor greps its own ticket for
    the path it may write, and `repr` doubles every separator a Windows path
    carries, so the body named `scripts\\\\one.py` where the frontmatter --
    and the filesystem -- said `scripts\\one.py`.
    """
    return '\n'.join((f'{indent}- `{value}`' for value in values))
def _gate_input(name: str, *, literal=None, run: str='', ticket: str='', section: str='') -> str:
    """One canonical fixed-input record for a generated gate."""
    if ticket:
        record = {
            'identity': {'kind': 'ticket-section', 'run': run, 'section': section, 'ticket': ticket},
            'name': name,
            'type': 'identity',
        }
    else:
        record = {'name': name, 'type': 'literal', 'value': literal}
    return '- input: ' + json.dumps(record, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
def _input_name(prefix: str, value: str, position: int) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', str(value).lower()).strip('-')
    return f'{prefix}-{slug or position}'
def _gate_body(kind: str, root_id: str, lens: str, scope: list, acceptance_id: str, acceptance: str, units: list, run: str='') -> list:
    """The four cut-time sections of one gate stub."""
    if kind == 'critique':
        inputs = [_gate_input('lens', literal=lens)]
        inputs.extend(
            _gate_input(_input_name('unit-result', unit, position), run=run, ticket=unit, section='Result')
            for position, unit in enumerate(units, start=1)
        )
        inputs.append(_gate_input('acceptance', run=run, ticket=acceptance_id, section='Completion test'))
        return [('Objective', f"Every defect in `{root_id}`'s delivered result that the `{lens}` lens finds is reported by identity with its evidence: an open search over what the subtree produced, not a re-run of the criteria it already states."), ('Fixed inputs', '\n'.join(inputs)), ('Completion test', '\n'.join([f"- every finding names the artifact identity it was found at and the evidence that shows it | oracle: this ticket's `## Result` read under the `{lens}` lens | oracle_class: judged | provenance: pre-existing", f"- every `## Result` named in the fixed inputs was read | oracle: this ticket's `## Result` against that list | oracle_class: deterministic | provenance: pre-existing"])), ('Return fields', 'status; result — ranked findings, each with its artifact identity and evidence; verification; feedback; risks')]
    if kind == 'repair':
        inputs = [
            _gate_input(_input_name('critique-result', unit, position), run=run, ticket=unit, section='Result')
            for position, unit in enumerate(units, start=1)
        ]
        return [('Objective', f"Every accepted finding against `{root_id}` is repaired inside this ticket's own write scope, or declined with a stated reason; nothing outside that scope changes."), ('Fixed inputs', '\n'.join(inputs)), ('Completion test', '\n'.join(["- every accepted finding is repaired or declined with a stated reason | oracle: the critique tickets' findings against this ticket's `## Result` | oracle_class: deterministic | provenance: pre-existing", "- nothing outside the write scope changed | oracle: `git status --porcelain` in the run's workspace | oracle_class: deterministic | provenance: pre-existing"])), ('Return fields', 'status; result — each finding, its disposition and the changed artifact by identity; verification; feedback; risks')]
    repair_id = GATE_REPAIR_ID.format(root=root_id)
    inputs = [
        _gate_input('acceptance', run=run, ticket=acceptance_id, section='Completion test'),
        _gate_input('repair-result', run=run, ticket=repair_id, section='Result'),
    ]
    return [('Objective', f"`{acceptance_id}`'s acceptance is decided at the revision `{repair_id}` left: one verdict per criterion, from the oracle that criterion names."), ('Fixed inputs', '\n'.join(inputs)), ('Completion test', acceptance), ('Return fields', "status; verification — one verdict per criterion with the oracle's output; result; feedback; risks")]
def _cmd_gate(rest):
    """Serialize the gate's complete state read and all-or-none creation."""
    probe = list(rest)
    for flag in ('--lens', '--write-scope', '--acceptance-from'):
        _extract_flag(probe, flag)
    if len(probe) != 2 or _segment_error('run id', probe[0]) is not None:
        return _gate_under_run_lock(rest)
    try:
        with _run_lock(probe[0]):
            return _gate_under_run_lock(rest)
    except OSError as error:
        return {'error': f'unable to create gate: {error}. Nothing was written'}
def _gate_under_run_lock(rest):
    """Write one root ticket's gate stubs into its run.
    Refused rather than half-written: a root with no `<root>.NN` units has
    nothing for a critique to close over, and a stub id already issued
    means a gate is already standing — writing a second one would put two
    repairs on one scope. Nothing lands until every stub is graded.
    """
    args = list(rest)
    lens_arg = _extract_flag(args, '--lens')
    scope_arg = _extract_flag(args, '--write-scope')
    acceptance_from = _extract_flag(args, '--acceptance-from')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'gate does not accept {stray}. usage: {GATE_USAGE}'}
    if len(args) != 2:
        return {'error': f'usage: {GATE_USAGE}'}
    run, root_id = args
    for kind, value in (('run id', run), ('root id', root_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    lenses = _split_commas(lens_arg)
    items, error = _run_tickets(run)
    if error is not None:
        return error
    by_id = {item['id']: item for item in items}
    root = by_id.get(root_id)
    if root is None:
        return {'error': f"root ticket '{root_id}' is not in run '{run}'"}
    roots = sorted((str(item.get('id') or '') for item in items if _executor_of(item) == ROOT_EXECUTOR))
    if _executor_of(root) != ROOT_EXECUTOR or roots != [root_id]:
        return {'error': f"gate root '{root_id}' is not the run's sole orch-decompose root ({roots or 'none'}). One physical run's one gate belongs only to that root. Nothing was written"}
    if not lenses:
        lenses = _split_commas(_pack_domain(root.get('pack')))
    if not lenses:
        return {'error': f"gate requires --lens: one critique stub per stamped lens, and root ticket '{root_id}' names no pack whose domain could stand in. usage: " + GATE_USAGE}
    try:
        lenses = _distinct_gate_lenses(lenses)
    except ValueError as error:
        return {'error': str(error) + '. Nothing was written'}
    gate_roots = sorted({str(item.get('id') or '').split(GATE_ID_MARKER, 1)[0] for item in items if GATE_ID_MARKER in str(item.get('id') or '')})
    other_gate_roots = [owner for owner in gate_roots if owner != root_id]
    if other_gate_roots:
        return {'error': f"run '{run}' already has the one gate owned by root '{other_gate_roots[0]}': root '{root_id}' cannot create a second gate family. Nothing was written"}
    scope = _split_commas(scope_arg) if scope_arg is not None else list(root.get('write_scope') or [])
    if not scope:
        return {'error': f"gate requires --write-scope: the scope the repair holds, and root ticket '{root_id}' declares none to default to. usage: " + GATE_USAGE}
    gate_prefix = f'{root_id}.gate.'
    units = sorted((item_id for item_id in by_id if item_id.startswith(f'{root_id}.') and (not item_id.startswith(gate_prefix))))
    if not units:
        return {'error': f"root ticket '{root_id}' has no `{root_id}.` subtree ticket yet: a gate closes over a cut subtree, so there is nothing here for a critique to read"}
    acceptance_id = acceptance_from or root_id
    source = by_id.get(acceptance_id)
    if source is None:
        return {'error': f"--acceptance-from names '{acceptance_id}', which is not a ticket in run '{run}'"}
    acceptance = (source.get('sections') or {}).get('Completion test', '').strip()
    if not acceptance:
        return {'error': f"ticket '{acceptance_id}' states no `## Completion test`, so the verify stub would carry no acceptance"}
    pack = root.get('pack')
    inherited_inputs = (root.get('sections') or {}).get('Fixed inputs', '')
    gate_baseline = git_head()
    if pack in ('orch-code-pack', 'orch-design-pack') and gate_baseline is None:
        return {'error': f'{pack} gate input rendering cannot resolve the run-project HEAD. Nothing was written'}
    rendered = []
    critique_ids = []
    try:
        for lens in lenses:
            invalid = _segment_error('lens', lens)
            if invalid is not None:
                return invalid
            stub_id = GATE_CRITIQUE_ID.format(root=root_id, lens=lens)
            critique_ids.append(stub_id)
            rendered.append((stub_id, _gate_stub(run, stub_id, GATE_EXECUTORS['critique'], units, [], _gate_sections('critique', root_id, lens, scope, acceptance_id, acceptance, units, run), pack, inherited_inputs=inherited_inputs, baseline=gate_baseline)))
        repair_id = GATE_REPAIR_ID.format(root=root_id)
        rendered.append((repair_id, _gate_stub(run, repair_id, GATE_EXECUTORS['repair'], critique_ids, scope, _gate_sections('repair', root_id, '', scope, acceptance_id, acceptance, critique_ids, run), pack, inherited_inputs=inherited_inputs, baseline=gate_baseline)))
        verify_id = GATE_VERIFY_ID.format(root=root_id)
        rendered.append((verify_id, _gate_stub(run, verify_id, GATE_EXECUTORS['verify'], [repair_id], [], _gate_sections('verify', root_id, '', scope, acceptance_id, acceptance, units, run), pack, inherited_inputs=inherited_inputs, baseline=gate_baseline)))
    except ValueError as error:
        return {'error': str(error) + '. Nothing was written'}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    run_dir = tickets_root / run
    for stub_id, text in rendered:
        defects = ticket_defects(text)
        if defects:
            return {'error': f'gate stub {stub_id} is off contract (contracts/work-item.md): ' + '; '.join(defects)}
        if (run_dir / f'{stub_id}.md').exists():
            return {'error': f"gate stub '{stub_id}' is already issued in run '{run}': a root ticket has one gate. Nothing was written"}
    written = []
    try:
        for stub_id, text in rendered:
            path = run_dir / f'{stub_id}.md'
            _create_text_exclusively(path, text)
            written.append(path)
    except OSError as error:
        for path in written:
            path.unlink(missing_ok=True)
        return {'error': f'unwritable gate stub: {error}. Nothing was written'}
    return {'gate': {'run': run, 'root': root_id, 'lenses': lenses, 'acceptance_from': acceptance_id, 'ids': [stub_id for stub_id, _ in rendered], 'paths': [str(path) for path in written]}}
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
        return {'error': 'missing subcommand: new | amend | recut | instantiate | gate | list | ready | claim | grant | check | set-status | result-grade | packet | result | worklog | run-state | improvement'}
    command, rest = (argv[0], argv[1:])
    if command in HELP_COMMANDS:
        return _cmd_help()
    if command in SUBCOMMAND_USAGE and _help_requested(rest):
        return _cmd_help(command)
    if command == 'new': return _cmd_new(rest)
    if command == 'amend': return _cmd_amend(rest)
    if command == 'recut': return _cmd_recut(rest)
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
    print(json.dumps(result, ensure_ascii=False))
    return 1 if 'error' in result else 0
