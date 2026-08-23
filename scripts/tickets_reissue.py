#!/usr/bin/env python3
"""`reissue`: one taken-up ticket superseded into a successor run.

A ticket that blocks on a field problem is not a ticket anybody may edit:
its cut is the packet a child was dispatched with, `amend` closes at the
claim, and what is left is writing the successor by hand -- the one path
around every refusal `new` applies to the same bytes. This writes it
instead, and writes it through `new --file`, so the successor is admitted
exactly as an issued ticket is.

What is dropped is lifecycle: a claim, a checker's pass, a workspace, the
v2 generation and seal fields, and the cohort, which names a set of items
cut together in one run and cannot follow one member into another. What is
kept is the cut. What is added is one fixed input naming the predecessor's
cited section by identity and digest, so the successor's reader can reach
what the blocked item actually said without the run that said it being
open. The source is never written.
"""
from __future__ import annotations
import hashlib
import tempfile
from pathlib import Path
if __package__:
    from .tickets_admission import ADMISSION_PENDING, batch_cohort, root_cohort, ticket_cohort, valid_cohort
    from .tickets_commands import REISSUE_USAGE
    from .tickets_format import EXECUTOR_SECTIONS_BY_KEY, ROOT_EXECUTOR, _executor_of, _extract_all, _extract_flag, _parse_frontmatter, _read_utf8, _remove_frontmatter_field, _scope_entries, _sections, _set_frontmatter_field, _split_commas, _write_section, canonical_json, parse_canonical_json
    from .tickets_inputs import section_body
    from .tickets_issue import _place_ticket
    from .tickets_lint import _cmd_lint
    from .tickets_store import NO_SINK_ERROR, _load_ticket, _segment_error, _tickets_root
else:
    from tickets_admission import ADMISSION_PENDING, batch_cohort, root_cohort, ticket_cohort, valid_cohort
    from tickets_commands import REISSUE_USAGE
    from tickets_format import EXECUTOR_SECTIONS_BY_KEY, ROOT_EXECUTOR, _executor_of, _extract_all, _extract_flag, _parse_frontmatter, _read_utf8, _remove_frontmatter_field, _scope_entries, _sections, _set_frontmatter_field, _split_commas, _write_section, canonical_json, parse_canonical_json
    from tickets_inputs import section_body
    from tickets_issue import _place_ticket
    from tickets_lint import _cmd_lint
    from tickets_store import NO_SINK_ERROR, _load_ticket, _segment_error, _tickets_root

# Removed outright: every one of these is a fact about an execution, and the
# successor has had none. `claimed_by` and `claimed_at` are blanked rather
# than removed because `new` writes them empty and a reader distinguishes an
# unclaimed ticket from one whose claim field is missing.
LIFECYCLE_FIELDS = ('checked_by', 'workspace_branch', 'workspace_baseline',
                    'root_generation', 'cut_generation', 'ownership_regions',
                    'assignment_seal')
BLANKED_FIELDS = ('claimed_by', 'claimed_at')
# `amend` and `recut` own a cut nobody has taken up yet; this owns the one
# that has been. The two are refused here so the cheaper repair is not
# reached for by writing a second ticket.
AMENDABLE_SOURCE = frozenset({'pending', 'ready'})
CITE_SECTIONS = {'result': 'Result', 'handoff': 'Handoff'}
PREDECESSOR = 'predecessor'
INPUT_PREFIX = '- input: '
# The neutral file operation: a widened path is authority the caller is
# adding, and whether it will be created or changed is the executor's to
# find out. `write:` is a directory prefix and would grade a file wrong.
ADDED_OPERATION = 'change'


def _refusal(message: str) -> dict:
    """One refusal, at the exit code that separates it from a finding."""
    return {'error': message, 'exit_code': 2}


def _block_form(text: str, key: str) -> bool:
    """Whether ``key`` is written as a list of ``- entry`` lines."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return False
    for line in lines[1:]:
        if line.strip() == '---':
            break
        if ':' in line and line.split(':', 1)[0].strip() == key:
            return line.split(':', 1)[1].strip() == ''
    return False


def _assign(text: str, key: str, value: str) -> str:
    """Write one frontmatter field, replacing a block-form list whole.

    ``_set_frontmatter_field`` rewrites the key's own line, which is the
    whole field only while the field is inline: a list written as ``- entry``
    lines would keep its old entries under a new header. Removing the field
    first is what makes both shapes one operation.
    """
    if _block_form(text, key):
        text = _remove_frontmatter_field(text, key)
    return _set_frontmatter_field(text, key, value)


def _list_value(entries) -> str:
    return '[' + ', '.join(entries) + ']'


def _fresh_cohort(source_cohort: str, new_id: str) -> str:
    """A cohort of the source's shape, naming the successor.

    A cohort is a set of items cut together in one run, and no member of the
    old run is in the new one; the shape is kept because it is a statement
    about how the item is sealed, and the identity is the successor's own.
    """
    parts = str(source_cohort or '').split(':')
    kind = parts[1] if len(parts) >= 3 else 'ticket'
    if kind == 'root':
        return root_cohort(new_id)
    if kind == 'batch':
        return batch_cohort([new_id])
    return ticket_cohort(new_id)


def _input_names(body: str) -> set:
    """Every name the Fixed-input records already carry."""
    names = set()
    for line in body.splitlines():
        if not line.startswith(INPUT_PREFIX):
            continue
        try:
            record = parse_canonical_json(line[len(INPUT_PREFIX):])
        except (TypeError, ValueError):
            continue
        if isinstance(record, dict) and isinstance(record.get('name'), str):
            names.add(record['name'])
    return names


def _with_predecessor(text: str, run: str, ticket_id: str, section: str, digest: str) -> str:
    """Append the one record naming what the superseded item said."""
    body = section_body(text, 'Fixed inputs')
    names = _input_names(body)
    name, suffix = PREDECESSOR, 2
    while name in names:
        name = f'{PREDECESSOR}-{suffix}'
        suffix += 1
    record = INPUT_PREFIX + canonical_json({
        'identity': {'kind': 'ticket-section', 'run': run, 'section': section,
                     'sha256': digest, 'ticket': ticket_id},
        'name': name, 'type': 'identity',
    })
    kept = [line for line in body.splitlines() if line.strip()]
    return _write_section(text, 'Fixed inputs', '\n'.join(kept + [record]))


def _existing_root(run_dir: Path):
    """The id of the root already in ``run_dir``, or ``None``."""
    for path in sorted(run_dir.glob('*.md')) if run_dir.is_dir() else []:
        loaded = _load_ticket(path)
        if 'error' not in loaded and _executor_of(loaded) == ROOT_EXECUTOR:
            return str(loaded.get('id') or path.stem)
    return None


def _settings(entries) -> tuple:
    """``(fields, refusal)`` for the ``--set`` pairs, in the order given."""
    fields = []
    for entry in entries:
        key, separator, value = str(entry).partition('=')
        key = key.strip()
        if not separator or not key:
            return (None, _refusal(f"--set '{entry}' is not <key>=<value>. usage: {REISSUE_USAGE}"))
        section = EXECUTOR_SECTIONS_BY_KEY.get(key.lower())
        if section is not None:
            return (None, _refusal(
                f"--set '{key}' names the executor-owned section '{section}': reissue carries the cut "
                'forward and what an executor writes is `result`\'s, in either direction'
            ))
        fields.append((key, value.strip()))
    return (fields, None)


def _cited_section(text: str, cite, run: str, ticket_id: str) -> tuple:
    """``(section, digest, refusal)`` for the section the successor cites."""
    sections = _sections(text)
    if cite is None:
        section = 'Handoff' if 'Handoff' in sections else 'Result'
    else:
        section = CITE_SECTIONS.get(str(cite).strip().lower())
        if section is None:
            return (None, None, _refusal(f"--cite '{cite}' is not one of {sorted(CITE_SECTIONS)}. usage: {REISSUE_USAGE}"))
    if section not in sections:
        return (None, None, _refusal(
            f'{run}/{ticket_id} has no ## {section} section: a successor cites what the superseded item said'
        ))
    return (section, hashlib.sha256(section_body(text, section).encode('utf-8')).hexdigest(), None)


def _successor(text: str, data: dict, plan: dict) -> str:
    """The source's cut, with its lifecycle dropped and the plan applied."""
    for key in LIFECYCLE_FIELDS:
        text = _remove_frontmatter_field(text, key)
    for key in BLANKED_FIELDS:
        text = _assign(text, key, '')
    text = _assign(text, 'id', plan['id'])
    text = _assign(text, 'run', plan['run'])
    text = _assign(text, 'status', 'pending')
    text = _assign(text, 'admission', ADMISSION_PENDING)
    text = _assign(text, 'cohort', plan['cohort'])
    if plan['added']:
        scope = _scope_entries(data.get('write_scope'))
        mutations = _scope_entries(data.get('mutations'))
        for path in plan['added']:
            if path not in scope:
                scope.append(path)
            mutation = f'{ADDED_OPERATION}:{path}'
            if mutation not in mutations:
                mutations.append(mutation)
        text = _assign(text, 'write_scope', _list_value(scope))
        text = _assign(text, 'mutations', _list_value(mutations))
    for key, value in plan['fields']:
        text = _assign(text, key, value)
    return _with_predecessor(text, plan['from_run'], plan['from_id'], plan['cite'], plan['sha256'])


def _place(new_run: str, new_id: str, cohort: str, text: str) -> dict:
    """Land the successor through `new --file`, and leave no draft behind."""
    handle = tempfile.NamedTemporaryFile('wb', suffix='.md', delete=False)
    try:
        with handle:
            handle.write(text.encode('utf-8'))
        return _place_ticket(new_run, handle.name, new_id, cohort)
    finally:
        try:
            Path(handle.name).unlink()
        except OSError:
            pass


def _cmd_reissue(rest) -> dict:
    args = list(rest)
    new_run = _extract_flag(args, '--run')
    declared_id = _extract_flag(args, '--id')
    settings = _extract_all(args, '--set')
    added = _extract_all(args, '--add-scope')
    cite = _extract_flag(args, '--cite')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return _refusal(f'reissue does not accept {stray}. usage: {REISSUE_USAGE}')
    if len(args) != 2 or new_run is None:
        return _refusal(f'usage: {REISSUE_USAGE}')
    run, ticket_id = args
    new_id = (declared_id or ticket_id).strip()
    for kind, value in (('run id', run), ('ticket id', ticket_id),
                        ('run id', new_run), ('ticket id', new_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return {**invalid, 'exit_code': 2}
    root = _tickets_root()
    if root is None:
        return _refusal(NO_SINK_ERROR)
    source_path = root / run / f'{ticket_id}.md'
    text, failure = _read_utf8(source_path, f'ticket {run}/{ticket_id}')
    if failure is not None:
        return {**failure, 'exit_code': 2}
    data = _parse_frontmatter(text)
    status = str(data.get('status') or '').strip().strip('`').strip()
    if status in AMENDABLE_SOURCE:
        return _refusal(
            f"{run}/{ticket_id} is '{status}': a cut nobody has taken up is repaired in place with "
            '`amend` or `recut`, and reissue supersedes one that has been'
        )
    fields, refusal = _settings(settings)
    if refusal is not None:
        return refusal
    section, digest, refusal = _cited_section(text, cite, run, ticket_id)
    if refusal is not None:
        return refusal
    if _executor_of(data) == ROOT_EXECUTOR:
        holder = _existing_root(root / new_run)
        if holder is not None:
            return _refusal(
                f"run '{new_run}' already has root ticket '{holder}': one physical run has one root, "
                'so a superseded root is reissued into a run of its own. Nothing was written'
            )
    cohort = dict(fields).get('cohort') or _fresh_cohort(str(data.get('cohort') or ''), new_id)
    if not valid_cohort(cohort):
        return _refusal(f"cohort '{cohort}' is not v1:<ticket|root|batch>:<id-segment>")
    plan = {
        'run': new_run, 'id': new_id, 'cohort': cohort, 'fields': fields,
        'added': [path for entry in added for path in _split_commas(entry)],
        'from_run': run, 'from_id': ticket_id, 'cite': section, 'sha256': digest,
    }
    try:
        successor = _successor(text, data, plan)
    except ValueError as error:
        return _refusal(f'{run}/{ticket_id} cannot be rewritten: {error}')
    placed = _place(new_run, new_id, cohort, successor)
    if 'error' in placed:
        return placed
    report = _cmd_lint([new_run, new_id])
    exit_code = report.pop('exit_code', 0)
    return {
        'reissue': {
            'run': new_run, 'id': new_id, 'path': placed['new']['path'],
            'supersedes': {'run': run, 'id': ticket_id, 'status': status},
            'cite': section, 'sha256': digest, 'cohort': cohort,
            'added_scope': plan['added'], 'set': [key for key, _ in fields],
            **({'lint': report['lint']} if 'lint' in report else {'lint_error': report.get('error')}),
        },
        'exit_code': exit_code,
    }


__all__ = ('REISSUE_USAGE', '_cmd_reissue', '_fresh_cohort')
