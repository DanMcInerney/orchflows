"""Ticket issue support."""
from __future__ import annotations
import json
from datetime import datetime, timezone
if __package__:
    from .tickets_format import CUT_SECTIONS, CUT_SECTIONS_BY_KEY, DEFAULT_BOUND_MINUTES, EXECUTOR_SECTIONS, GATE_ID_MARKER, INSTRUCTION_BUDGET, REQUIRED_ISOLATION, ROOT_EXECUTOR, TicketFormatError, _executor_of, _extract_all, _extract_flag, _parse_frontmatter, _read_utf8, _remove_frontmatter_field, _sections, _set_frontmatter_field, _split_commas, _write_section, instruction_words, ticket_defects
else:
    from tickets_format import CUT_SECTIONS, CUT_SECTIONS_BY_KEY, DEFAULT_BOUND_MINUTES, EXECUTOR_SECTIONS, GATE_ID_MARKER, INSTRUCTION_BUDGET, REQUIRED_ISOLATION, ROOT_EXECUTOR, TicketFormatError, _executor_of, _extract_all, _extract_flag, _parse_frontmatter, _read_utf8, _remove_frontmatter_field, _sections, _set_frontmatter_field, _split_commas, _write_section, instruction_words, ticket_defects
if __package__:
    from .tickets_store import NO_SINK_ERROR, _create_text_exclusively, _identity_update, _load_ticket, _run_lock, _segment_error, _tickets_root, _write_identity, _write_text_atomically
else:
    from tickets_store import NO_SINK_ERROR, _create_text_exclusively, _identity_update, _load_ticket, _run_lock, _segment_error, _tickets_root, _write_identity, _write_text_atomically
if __package__:
    from .tickets_admission import ADMISSION_PENDING, ADMISSION_V2_PENDING, cohort_sealed, is_v2, ticket_cohort, valid_cohort
    from .tickets_input_producers import render_ticket_inputs
else:
    from tickets_admission import ADMISSION_PENDING, ADMISSION_V2_PENDING, cohort_sealed, is_v2, ticket_cohort, valid_cohort
    from tickets_input_producers import render_ticket_inputs
AMENDABLE_STATUSES = frozenset({'pending', 'ready'})
def _invalidate_assignment(text): v2 = is_v2(_parse_frontmatter(text)); text = _set_frontmatter_field(text, 'admission', ADMISSION_V2_PENDING if v2 else ADMISSION_PENDING); return _remove_frontmatter_field(text, 'assignment_seal') if v2 else text
NEW_USAGE = 'new <run> <id> --executor E --objective TEXT --criterion C [--criterion C ...] [--depends-on a,b] [--write-scope p[,p]] [--mutation create|change|delete|write:path ...] [--bound B] [--pack P] [--input JSON ...] [--excluded X ...] [--profile P] [--independence gate|checker] [--isolation required|none] [--cohort v1:<ticket|root|batch>:<id>] [--return-fields TEXT] | new <run> [<id>] --file <path> [--cohort v1:<ticket|root|batch>:<id>]'
NEW_DEFAULT_BOUND = f'{DEFAULT_BOUND_MINUTES}m'
NEW_DEFAULT_INPUTS = '- input: {"name":"none","type":"literal","value":null}'
NEW_DEFAULT_RETURN_FIELDS = 'status; result (what changed, by identity); verification; feedback; risks'
INDEPENDENCE_VALUES = ('gate', 'checker')
ISOLATION_VALUES = (REQUIRED_ISOLATION, 'none')
AMEND_USAGE = 'amend <run> <id> --section <name> (--file <path> | --text <string>)'
RECUT_USAGE = 'recut <run> <id> --file <candidate>'
def _distinct_gate_lenses(lenses: list) -> list:
    """Return ``lenses`` or refuse a repeated review identity.

    A second adversarial review is represented by another named lens. Two
    critique stubs with one label are one review identity written twice, not
    additional independence.
    """
    seen = set()
    repeated = []
    for lens in lenses:
        identity = lens.casefold()
        if identity in seen and lens not in repeated:
            repeated.append(lens)
        seen.add(identity)
    if repeated:
        raise ValueError('gate review lenses must be distinct; repeated: ' + ', '.join(repeated))
    return lenses
def _frontmatter_list(key: str, values) -> list:
    """One frontmatter list, as the lines that carry it.

    The inline form ``[a, b]`` splits on the comma and on nothing else —
    a semicolon inside an entry is part of that entry
    (``_parse_frontmatter``). So an entry carrying a comma, or a semicolon
    a reader might take for a separator, is written in the block form
    instead, one ``- entry`` per line: an excluded action is prose, and
    prose has commas in it. No second inline separator is offered, because
    one written shape read two ways is how a scope that was granted and a
    scope that was refused come to be the same line. Both shapes read back
    as the same list.
    """
    items = list(values)
    if any((',' in item or ';' in item for item in items)):
        return [f'{key}:'] + [f'- {item}' for item in items]
    return [f"{key}: [{', '.join(items)}]"]
def _render_ticket(fields: dict, sections: list) -> str:
    """One ticket's markdown: frontmatter in the contract's key order, then
    its body sections in the contract's section order.

    ``fields`` values are already strings or lists; ``None`` omits an
    optional key entirely, so nothing is written that the reader would have
    to interpret as absent.
    """
    lines = ['---']
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, list):
            lines.extend(_frontmatter_list(key, value))
        else:
            lines.append(f'{key}: {value}' if value != '' else f'{key}:')
    lines.append('---')
    body = []
    for heading, content in sections:
        body.append(f'\n## {heading}\n')
        if content:
            body.append(f'\n{content}\n')
    return '\n'.join(lines) + '\n' + ''.join(body)


def _input_record(value: str, position: int=1) -> str:
    """Render one ``--input`` value as the canonical-record bullet shell."""
    stripped = str(value).strip()
    if stripped.startswith('input: '):
        stripped = stripped[len('input: '):]
    try:
        json.loads(stripped)
    except json.JSONDecodeError:
        stripped = json.dumps(
            {'name': f'legacy-input-{position}', 'type': 'literal', 'value': stripped},
            ensure_ascii=False, separators=(',', ':'), sort_keys=True,
        )
    return f'- input: {stripped}'
def _cmd_new(rest):
    """Issue one ticket into the run, or place one already written.

    The cut's own refusal: everything ``ticket_defects`` reports is refused
    here, before any directory is created, so a ticket that reaches the sink
    is one every later subcommand accepts. An off-contract cut that lands
    and is refused at dispatch costs the dispatch; refusing it here costs
    the flag that was wrong.

    ``--file`` places a ticket its author already wrote, through the same
    validation and the same refusal to overwrite an id that exists. The run
    argument and the file's own ``run`` must agree: the argument decides
    where it lands, and a ticket landing in a run it does not name is a
    ticket no reader can trace back.
    """
    args = list(rest)
    file_arg = _extract_flag(args, '--file')
    executor = _extract_flag(args, '--executor')
    objective = _extract_flag(args, '--objective')
    criteria = _extract_all(args, '--criterion')
    depends_on = _extract_flag(args, '--depends-on')
    write_scope = _extract_flag(args, '--write-scope')
    bound = _extract_flag(args, '--bound')
    pack = _extract_flag(args, '--pack')
    inputs = _extract_all(args, '--input')
    mutations = _extract_all(args, '--mutation')
    excluded = _extract_all(args, '--excluded')
    profile = _extract_flag(args, '--profile')
    independence = _extract_flag(args, '--independence')
    isolation = _extract_flag(args, '--isolation')
    cohort = _extract_flag(args, '--cohort')
    return_fields = _extract_flag(args, '--return-fields')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'new does not accept {stray}. usage: {NEW_USAGE}'}
    if file_arg is not None:
        supplied = [name for name, value in (('--executor', executor), ('--objective', objective), ('--criterion', criteria or None), ('--depends-on', depends_on), ('--write-scope', write_scope), ('--mutation', mutations or None), ('--bound', bound), ('--pack', pack), ('--input', inputs or None), ('--excluded', excluded or None), ('--profile', profile), ('--independence', independence), ('--isolation', isolation), ('--return-fields', return_fields)) if value is not None]
        if supplied:
            return {'error': f'--file places a ticket already written; it takes none of {supplied}. usage: {NEW_USAGE}'}
        if not 1 <= len(args) <= 2:
            return {'error': f'usage: {NEW_USAGE}'}
        return _place_ticket(args[0], file_arg, args[1] if len(args) == 2 else None, cohort)
    if len(args) != 2:
        return {'error': f'usage: {NEW_USAGE}'}
    run, ticket_id = args
    for kind, value in (('run id', run), ('ticket id', ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    missing = [name for name, value in (('--executor', executor), ('--objective', objective), ('--criterion', criteria or None)) if value is None]
    if missing:
        return {'error': f"new requires {', '.join(missing)}. usage: {NEW_USAGE}"}
    for flag, value, allowed in (('--independence', independence, INDEPENDENCE_VALUES), ('--isolation', isolation, ISOLATION_VALUES)):
        if value is not None and value.strip() not in allowed:
            return {'error': f"{flag} '{value}' is not one of {list(allowed)} (contracts/work-item.md)"}
    cohort = cohort or ticket_cohort(ticket_id)
    if not valid_cohort(cohort):
        return {'error': f"--cohort '{cohort}' is not v1:<ticket|root|batch>:<id-segment>"}
    dependencies = _split_commas(depends_on)
    fields = {'id': ticket_id, 'run': run, 'status': 'pending', 'admission': ADMISSION_PENDING, 'cohort': cohort, 'executor': executor, 'pack': pack, 'independence': independence, 'depends_on': dependencies, 'write_scope': _split_commas(write_scope), 'mutations': mutations, 'excluded_actions': excluded or None, 'isolation': isolation, 'bound': bound or NEW_DEFAULT_BOUND, 'claimed_by': '', 'claimed_at': '', 'profile': profile}
    sections = [('Objective', objective), ('Fixed inputs', '\n'.join((_input_record(item, position) for position, item in enumerate(inputs, start=1))) or NEW_DEFAULT_INPUTS), ('Completion test', '\n'.join((f'- {item}' for item in criteria))), ('Return fields', return_fields or NEW_DEFAULT_RETURN_FIELDS), ('Result', ''), ('Verification', ''), ('Feedback', '[]'), ('Risks', '[]')]
    text, input_error = render_ticket_inputs(_render_ticket(fields, sections), run)
    if input_error is not None:
        return {'error': input_error}
    return _issue_ticket(run, ticket_id, text)
def _place_ticket(run: str, source: str, declared_id=None, cohort=None):
    """``new --file``: one already-written ticket, validated and placed.

    ``declared_id`` is the id the caller stated on the line. The file's own
    ``id`` is what decides, exactly as its ``run`` field does not: both are
    checked against the arguments so a ticket landing under a name it does
    not carry is refused rather than written.
    """
    invalid = _segment_error('run id', run)
    if invalid is not None:
        return invalid
    text, failure = _read_utf8(source, 'ticket file')
    if failure is not None:
        return failure
    data = _parse_frontmatter(text)
    ticket_id = data.get('id') if isinstance(data.get('id'), str) else None
    if not ticket_id:
        return {'error': f"ticket file {source} names no 'id' in its frontmatter"}
    invalid = _segment_error('ticket id', ticket_id)
    if invalid is not None:
        return invalid
    if declared_id is not None and declared_id.strip() != ticket_id.strip():
        return {'error': f"placed as '{declared_id}', but ticket file {source} names id '{ticket_id}': an id is the file's, and one ticket has one id"}
    declared = data.get('run')
    if isinstance(declared, str) and declared.strip() and (declared.strip() != run):
        return {'error': f"ticket file {source} names run '{declared.strip()}', placed into run '{run}': one ticket belongs to one run"}
    cohort = cohort or ticket_cohort(ticket_id)
    if not valid_cohort(cohort):
        return {'error': f"--cohort '{cohort}' is not v1:<ticket|root|batch>:<id-segment>"}
    text = _set_frontmatter_field(text, 'status', 'pending')
    text = _set_frontmatter_field(text, 'admission', ADMISSION_PENDING)
    text = _set_frontmatter_field(text, 'cohort', cohort)
    text = _set_frontmatter_field(text, 'claimed_by', '')
    text = _set_frontmatter_field(text, 'claimed_at', '')
    text, input_error = render_ticket_inputs(text, run)
    if input_error is not None:
        return {'error': input_error}
    return _issue_ticket(run, ticket_id, text)
def _cmd_amend(rest):
    probe = list(rest)
    for flag in ('--section', '--file', '--text'):
        _extract_flag(probe, flag)
    if len(probe) != 2 or _segment_error('run id', probe[0]) is not None:
        return _amend_under_run_lock(rest)
    try:
        with _run_lock(probe[0]):
            return _amend_under_run_lock(rest)
    except OSError as error:
        return {'error': f'unwritable ticket: {error}'}
def _amend_under_run_lock(rest):
    """Repair one cut-time section of an issued, unclaimed ticket.

    `cutcheck.py` reports cut defects and never edits; the decomposer
    repairs. Without this the repair had to be a hand edit of the file in the
    sink, which is the one write path around every refusal `new` applies to
    the same bytes -- so the amended ticket is graded here exactly as an
    issued one, and refused whole rather than written half.

    The claim is the closing condition. A cut-time section is the packet the
    child was dispatched with; moving one under a working executor is the
    moving target rules/verification.md §3 forbids, and what an executor
    writes is `result`'s in either direction.
    """
    args = list(rest)
    section = _extract_flag(args, '--section')
    file_arg = _extract_flag(args, '--file')
    text_arg = _extract_flag(args, '--text')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'amend does not accept {stray}. usage: {AMEND_USAGE}'}
    if len(args) != 2:
        return {'error': f'usage: {AMEND_USAGE}'}
    run, ticket_id = args
    if section is None:
        return {'error': f'amend requires --section <name>, one of {list(CUT_SECTIONS)}. usage: {AMEND_USAGE}'}
    canonical = CUT_SECTIONS_BY_KEY.get(section.strip().strip('#').strip().lower())
    if canonical is None:
        return {'error': f"section '{section}' is not one of the cut-time sections {list(CUT_SECTIONS)}; the sections an executor writes are written with `result`"}
    if (file_arg is None) == (text_arg is None):
        return {'error': f'amend takes one of --file <path> or --text <string>. usage: {AMEND_USAGE}'}
    if file_arg is not None:
        body, failure = _read_utf8(file_arg, 'body file')
        if failure is not None:
            return failure
    else:
        body = text_arg
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    ticket_path = tickets_root / run / f'{ticket_id}.md'
    if not ticket_path.is_file():
        return {'error': f'ticket not found: {run}/{ticket_id}'}
    text, failure = _read_utf8(ticket_path)
    if failure is not None:
        return failure
    frontmatter = _parse_frontmatter(text)
    claimed_by = str(frontmatter.get('claimed_by') or '').strip()
    if claimed_by:
        return {'error': f"ticket {run}/{ticket_id} is claimed by '{claimed_by}': its cut-time sections are frozen once an executor is working against them (rules/verification.md §3). Queue the change as its own scope, or take the claim back first"}
    status = str(frontmatter.get('status') or '').strip()
    if status not in AMENDABLE_STATUSES:
        return {'error': f"ticket {run}/{ticket_id} is '{status}': its cut-time sections are frozen outside {sorted(AMENDABLE_STATUSES)} (rules/verification.md §3). Queue the change as its own scope"}
    snapshot, failure = _exact_run_snapshot(ticket_path.parent)
    if failure is not None:
        return failure
    if str(frontmatter.get('checked_by') or '').strip():
        return {'error': f"ticket {run}/{ticket_id} has an immutable checked_by cut reader: further cut-time amendment is refused"}
    if cohort_sealed(ticket_id, text, snapshot):
        return {'error': f"ticket {run}/{ticket_id} belongs to a sealed cohort: cut-time amendment is refused"}
    try:
        rendered = _write_section(text, canonical, body)
    except TicketFormatError as error:
        return {'error': f'{error}. ticket: {ticket_path}'}
    defects = ticket_defects(rendered)
    if defects:
        return {'error': f'the amended ticket {run}/{ticket_id} would be off contract (contracts/work-item.md): ' + '; '.join(defects)}
    over = _ceiling_error(f'the amended ticket {run}/{ticket_id}', ticket_id, rendered)
    if over is not None:
        return over
    cohort = str(frontmatter.get('cohort') or '').strip() or ticket_cohort(ticket_id)
    rendered = _set_frontmatter_field(rendered, 'status', 'pending')
    rendered = _invalidate_assignment(rendered)
    rendered = _set_frontmatter_field(rendered, 'cohort', cohort)
    failure = _replace_and_invalidate(ticket_path.parent, snapshot, ticket_id, rendered, {cohort})
    if failure is not None:
        return failure
    return {'amend': {'run': run, 'id': ticket_id, 'section': canonical, 'path': str(ticket_path)}}


def _exact_run_snapshot(run_dir):
    texts = {}
    for path in sorted(run_dir.glob('*.md')):
        text, failure = _read_utf8(path)
        if failure is not None:
            return (None, failure)
        texts[path.stem] = text
    return (texts, None)


def _replace_and_invalidate(run_dir, snapshot, ticket_id, replacement, cohorts):
    """Write one replacement and invalidate every old/new cohort member."""
    updates = {}
    for member_id, prior in snapshot.items():
        data = _parse_frontmatter(prior)
        if member_id != ticket_id and str(data.get('cohort') or '') not in cohorts:
            continue
        source = replacement if member_id == ticket_id else prior
        status = str(data.get('status') or '')
        if member_id != ticket_id and status not in AMENDABLE_STATUSES:
            continue
        source = _set_frontmatter_field(source, 'status', 'pending')
        source = _invalidate_assignment(source)
        updates[member_id] = source
    written = []
    try:
        for member_id in sorted(updates):
            _write_text_atomically(run_dir / f'{member_id}.md', updates[member_id])
            written.append(member_id)
    except OSError as error:
        for member_id in written:
            try:
                _write_text_atomically(run_dir / f'{member_id}.md', snapshot[member_id])
            except OSError:
                pass
        return {'error': f'unwritable ticket cohort: {error}'}
    return None


def _cmd_recut(rest):
    probe = list(rest)
    _extract_flag(probe, '--file')
    if len(probe) != 2 or _segment_error('run id', probe[0]) is not None:
        return _recut_under_run_lock(rest)
    try:
        with _run_lock(probe[0]):
            return _recut_under_run_lock(rest)
    except OSError as error:
        return {'error': f'unwritable ticket: {error}'}


def _recut_under_run_lock(rest):
    args = list(rest)
    candidate_path = _extract_flag(args, '--file')
    if len(args) != 2 or candidate_path is None:
        return {'error': f'usage: {RECUT_USAGE}'}
    run, ticket_id = args
    for kind, value in (('run id', run), ('ticket id', ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    target = tickets_root / run / f'{ticket_id}.md'
    if not target.is_file():
        return {'error': f'ticket not found: {run}/{ticket_id}'}
    current, failure = _read_utf8(target)
    if failure is not None:
        return failure
    current_data = _parse_frontmatter(current)
    status = str(current_data.get('status') or '')
    if status not in AMENDABLE_STATUSES:
        return {'error': f"ticket {run}/{ticket_id} is '{status}': recut accepts only pending or ready tickets"}
    snapshot, failure = _exact_run_snapshot(target.parent)
    if failure is not None:
        return failure
    if str(current_data.get('checked_by') or '').strip():
        return {'error': f"ticket {run}/{ticket_id} has an immutable checked_by cut reader: recut is refused"}
    if cohort_sealed(ticket_id, current, snapshot):
        return {'error': f"ticket {run}/{ticket_id} belongs to a sealed cohort: recut is refused"}
    candidate, failure = _read_utf8(candidate_path, 'recut candidate')
    if failure is not None:
        return failure
    candidate_data = _parse_frontmatter(candidate)
    if str(candidate_data.get('id') or '').strip() != ticket_id or str(candidate_data.get('run') or '').strip() != run:
        return {'error': f'recut candidate must preserve id {ticket_id!r} and run {run!r}'}
    old_cohort = str(current_data.get('cohort') or '').strip()
    new_cohort = str(candidate_data.get('cohort') or '').strip() or old_cohort or ticket_cohort(ticket_id)
    if not valid_cohort(new_cohort):
        return {'error': f"candidate cohort '{new_cohort}' is not v1:<ticket|root|batch>:<id-segment>"}
    for key in ('checked_by', 'workspace_branch', 'workspace_baseline', 'granted_scope', 'granted_by', 'granted_at'):
        candidate = _remove_frontmatter_field(candidate, key)
    candidate = _set_frontmatter_field(candidate, 'status', 'pending')
    candidate = _set_frontmatter_field(candidate, 'admission', ADMISSION_PENDING)
    candidate = _set_frontmatter_field(candidate, 'cohort', new_cohort)
    candidate = _set_frontmatter_field(candidate, 'claimed_by', '')
    candidate = _set_frontmatter_field(candidate, 'claimed_at', '')
    candidate, input_error = render_ticket_inputs(candidate, run)
    if input_error is not None:
        return {'error': input_error}
    current_sections = _sections(current)
    for heading in EXECUTOR_SECTIONS:
        if heading in current_sections:
            candidate = _write_section(candidate, heading, current_sections[heading])
    defects = _issue_defects(candidate)
    if defects:
        return {'error': f'the recut ticket {run}/{ticket_id} would be off contract (contracts/work-item.md): ' + '; '.join(defects)}
    over = _ceiling_error(f'the recut ticket {run}/{ticket_id}', ticket_id, candidate)
    if over is not None:
        return over
    failure = _replace_and_invalidate(target.parent, snapshot, ticket_id, candidate, {value for value in (old_cohort, new_cohort) if value})
    if failure is not None:
        return failure
    return {'recut': {'run': run, 'id': ticket_id, 'path': str(target), 'cohort': new_cohort, 'status': 'pending', 'admission': ADMISSION_PENDING}}
def _ceiling_error(subject: str, ticket_id: str, text: str):
    """The refusal a ticket over the instruction ceiling gets, or ``None``.

    Applied where the cutter still holds the flag that was wrong. An
    objective enumerating (1)...(5) cannot fit inside the ceiling, which is
    the point: the ticket that does not fit is two tickets.

    The ceiling is a unit's. A root ticket states a whole run, and each
    `.gate.` stub carries the root's `## Completion test` verbatim -- `gate`
    renders them from it -- so grading either against the unit ceiling would
    refuse what this script itself writes.
    """
    if GATE_ID_MARKER in str(ticket_id or ''):
        return None
    if _executor_of(_parse_frontmatter(text)) == ROOT_EXECUTOR:
        return None
    count = instruction_words(text)
    if count <= INSTRUCTION_BUDGET:
        return None
    return {'error': f'{subject} has a {count}-word instruction, over the {INSTRUCTION_BUDGET}-word ceiling (rules/token-economy.md, section 11): the objective, completion test, excluded actions and return fields a child loads every dispatch, never its fixed inputs. A compound objective is two items, not one longer ticket'}
def _issue_defects(text: str, *, issued: bool=False) -> list:
    """Contract and pre-dispatch defects in one ticket being issued.

    Existing tickets may legitimately carry the immutable checker identity
    written by ``tickets.py check``. An unissued ticket cannot: admitting it
    would let a caller suppress the checker before dispatch.

    ``issued=True`` grades a ticket already in the sink, where that one rule
    has nothing left to protect -- the dispatch it guards has happened, and
    `check` is what wrote the field. Every other defect here is a contract
    defect at any point in the lifecycle and is reported either way.
    """
    defects = ticket_defects(text)
    data = _parse_frontmatter(text)
    if not data:
        return defects
    independence = 'checker'
    if 'independence' in data:
        independence = str(data.get('independence') or '').strip().strip('`').strip()
        if independence not in INDEPENDENCE_VALUES:
            defects.append(
                f"independence '{independence}' is not one of {list(INDEPENDENCE_VALUES)}"
            )
    checked_by = str(data.get('checked_by') or '').strip()
    if checked_by:
        if independence == 'gate' and _executor_of(data) != ROOT_EXECUTOR:
            defects.append(
                "non-root independence 'gate' cannot carry 'checked_by' "
                "(contracts/work-item.md)"
            )
        elif not issued:
            defects.append(
                "an unissued ticket cannot carry 'checked_by': only "
                "`tickets.py check` sets it after checker dispatch"
            )
    return defects
def _issue_ticket(run: str, ticket_id: str, text: str):
    """Grade one rendered ticket, then write it — in that order.

    Nothing is created before the grade: a refused cut leaves the run
    directory exactly as it found it, including not existing.
    """
    defects = _issue_defects(text)
    if defects:
        return {'error': f'ticket {run}/{ticket_id} is off contract (contracts/work-item.md): ' + '; '.join(defects)}
    over = _ceiling_error(f'ticket {run}/{ticket_id}', ticket_id, text)
    if over is not None:
        return over
    if GATE_ID_MARKER in ticket_id:
        return {'error': f"ticket id '{ticket_id}' is reserved for `tickets.py gate`; new and new --file cannot assemble a partial or alternate gate family"}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    ticket_path = tickets_root / run / f'{ticket_id}.md'
    try:
        with _run_lock(run):
            if ticket_path.exists():
                return {'error': f"ticket id '{ticket_id}' is already issued in run '{run}': {ticket_path}. An id is stable once issued (contracts/work-item.md)"}
            data = _parse_frontmatter(text)
            if _executor_of(data) == ROOT_EXECUTOR:
                existing_roots = []
                run_dir = ticket_path.parent
                for path in sorted(run_dir.glob('*.md')) if run_dir.is_dir() else []:
                    loaded = _load_ticket(path)
                    if 'error' not in loaded and _executor_of(loaded) == ROOT_EXECUTOR:
                        existing_roots.append(str(loaded.get('id') or path.stem))
                if existing_roots:
                    return {'error': f"run '{run}' already has root ticket '{existing_roots[0]}': one physical run has one root and one composite gate. Open a successor run for another deliverable kind. Nothing was written"}
            identity_dir, identity, refusal = _identity_update(run, datetime.now(timezone.utc))
            if refusal is not None:
                return refusal
            ticket_path.parent.mkdir(parents=True, exist_ok=True)
            _create_text_exclusively(ticket_path, text)
            try:
                if identity is not None:
                    identity_dir.mkdir(parents=True, exist_ok=True)
                    _write_identity(identity_dir, identity)
            except OSError:
                ticket_path.unlink(missing_ok=True)
                raise
    except FileExistsError:
        return {'error': f"ticket id '{ticket_id}' is already issued in run '{run}': {ticket_path}. An id is stable once issued (contracts/work-item.md)"}
    except OSError as error:
        ticket_path.unlink(missing_ok=True)
        return {'error': f'unwritable ticket: {error}'}
    return {'new': {'run': run, 'id': ticket_id, 'path': str(ticket_path), 'status': _parse_frontmatter(text).get('status')}}
