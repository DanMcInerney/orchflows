#!/usr/bin/env python3
"""Every grader a later command runs, over one ticket or draft, all at once.

``new``, ``ready``, ``claim`` and ``packet`` each refuse at the first defect
they reach, which is right where they stand -- they are about to write -- and
wrong for the cutter still holding the draft: one refusal per round trip
turns a five-defect draft into five dispatches. This runs the same graders,
never stopping at the first, and reports what each of them found.

A finding is ``{code, severity, kind, message, fix}``. ``kind`` is the whole
question ``--fix`` asks: *syntactic* means the repair is mechanical and this
module knows it exactly -- re-emit the record canonically, write the one
value the executor's pack requires, spell a prose exclusion as its reserved
token. *semantic* means the repair is a decision -- what the second ticket
is, which oracle class the criterion is graded under -- and nothing here may
make it. Exit 0 with no finding, 1 while any semantic one stands, 2 when the
input cannot be read or the target may not be rewritten.
"""
from __future__ import annotations
import re
from pathlib import Path
if __package__:
    from .tickets_admission import VCS_ACTION_TOKENS, cohort_sealed, grade_admission, grade_result
    from .tickets_commands import LINT_USAGE
    from .tickets_format import GATE_ID_MARKER, INSTRUCTION_BUDGET, ORACLE_RE, ROOT_EXECUTOR, _criteria, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _scope_entries, _sections, _set_frontmatter_field, _whole_suite, canonical_json, instruction_words, parse_canonical_json
    from .tickets_issue import AMENDABLE_STATUSES, NEW_DEFAULT_BOUND, _issue_defects
    from .tickets_store import NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root, _write_text_atomically
else:
    from tickets_admission import VCS_ACTION_TOKENS, cohort_sealed, grade_admission, grade_result
    from tickets_commands import LINT_USAGE
    from tickets_format import GATE_ID_MARKER, INSTRUCTION_BUDGET, ORACLE_RE, ROOT_EXECUTOR, _criteria, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _scope_entries, _sections, _set_frontmatter_field, _whole_suite, canonical_json, instruction_words, parse_canonical_json
    from tickets_issue import AMENDABLE_STATUSES, NEW_DEFAULT_BOUND, _issue_defects
    from tickets_store import NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root, _write_text_atomically

SYNTACTIC = 'syntactic'
SEMANTIC = 'semantic'
MISSING_KEY_RE = re.compile(r"^frontmatter has no '([a-z_]+)'$")
INPUT_PREFIX = '- input: '
# The frontmatter values a contract states a default for. Everything else a
# ticket lacks -- its id, its run, its executor, its write scope -- is the
# cutter's decision and stays semantic.
DEFAULTABLE = {'depends_on': '[]', 'bound': NEW_DEFAULT_BOUND, 'status': 'pending'}
# Prose that names exactly one reserved action. A word naming two -- `git`,
# `branch` -- maps to none of them on purpose: the rewrite would be a guess.
VCS_PROSE_TOKENS = (
    ('pull request', 'vcs.open-pr'),
    ('open a pr', 'vcs.open-pr'),
    ('push', 'vcs.push'),
    ('integrate', 'vcs.integrate'),
    ('merge', 'vcs.integrate'),
    ('commit', 'vcs.commit'),
    ('worktree', 'vcs.isolate'),
)
# The admission codes whose repair is exactly one mechanical rewrite.
FIXABLE_ADMISSION = {
    'input-json-noncanonical': 're-emit the record as canonical JSON',
    'vcs-isolation-required': 'set `isolation: required`',
    'vcs-exclusion-not-tokenized': 'spell the exclusion as its reserved vcs.* token',
}


def _finding(code, message, kind=SEMANTIC, severity='error', fix=None) -> dict:
    return {'code': code, 'severity': severity, 'kind': kind, 'message': message, 'fix': fix}


def _repo_tree() -> Path:
    """The checkout an oracle's module path is resolved against."""
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / '.git').exists():
            return candidate
    return here


def _prose_token(entry: str):
    """The one reserved token a prose exclusion names, or ``None``."""
    normalized = re.sub(r'[-_\s]+', ' ', entry.casefold())
    tokens = {token for word, token in VCS_PROSE_TOKENS if word in normalized}
    return tokens.pop() if len(tokens) == 1 else None


def _ceiling_finding(ticket_id: str, text: str, data: dict):
    """The ceiling with its count and its overage, or ``None``.

    Exempt exactly where ``_ceiling_error`` is: a root states a whole run,
    and a ``.gate.`` stub carries the root's completion test verbatim.
    """
    if GATE_ID_MARKER in str(ticket_id or '') or _executor_of(data) == ROOT_EXECUTOR:
        return None
    count = instruction_words(text)
    if count <= INSTRUCTION_BUDGET:
        return None
    return _finding(
        'instruction-ceiling',
        f'{count}-word instruction, {count - INSTRUCTION_BUDGET} over the {INSTRUCTION_BUDGET}-word ceiling '
        '(rules/token-economy.md, section 11): a compound objective is two items, not one longer ticket',
    )


def _oracle_findings(text: str, tree: Path) -> list:
    """One finding per criterion whose oracle runs the suite it is stated under."""
    findings = []
    for number, criterion in enumerate(_criteria(_sections(text).get('Completion test', '')), start=1):
        match = ORACLE_RE.search(criterion)
        command = match.group(1).strip(' `.,;*') if match else ''
        if command and _whole_suite(command, tree):
            findings.append(_finding(
                'whole-suite-oracle',
                f'criterion {number} names `{command}`, which runs the identical tests under every item '
                'it is stated under and so discriminates none of them',
                severity='warning',
            ))
    return findings


def lint_findings(text: str, *, ticket_id: str, siblings=None, tree=None) -> list:
    """Every finding the graders report on this exact snapshot, deduplicated."""
    data = _parse_frontmatter(text)
    if not data:
        return [_finding('no-frontmatter', "a ticket opens with a '---' block (contracts/work-item.md)")]
    findings = []
    for defect in _issue_defects(text):
        missing = MISSING_KEY_RE.match(defect)
        key = missing.group(1) if missing else None
        if key in DEFAULTABLE:
            findings.append(_finding(
                'frontmatter-default-missing', defect, kind=SYNTACTIC,
                fix=f'write `{key}: {DEFAULTABLE[key]}`',
            ))
        else:
            findings.append(_finding('ticket-defect', defect))
    ceiling = _ceiling_finding(ticket_id, text, data)
    if ceiling is not None:
        findings.append(ceiling)
    graded = grade_admission(ticket_id, text, dict(siblings or {}))
    for item in graded['findings']:
        code = str(item.get('code') or '')
        fix = FIXABLE_ADMISSION.get(code)
        if code == 'vcs-exclusion-not-tokenized':
            entry = str(item.get('detail') or '').rsplit(': ', 1)[-1]
            fix = fix if _prose_token(entry) else None
        findings.append(_finding(
            code, f"{item.get('field')}: {item.get('detail')}",
            kind=SYNTACTIC if fix else SEMANTIC, fix=fix,
        ))
    if _sections(text).get('Result', '').strip():
        for item in grade_result(ticket_id, text, dict(siblings or {}))['findings']:
            findings.append(_finding(str(item.get('code') or ''), f"{item.get('field')}: {item.get('detail')}"))
    findings.extend(_oracle_findings(text, tree or _repo_tree()))
    seen, ordered = set(), []
    for item in sorted(findings, key=lambda row: (row['code'], row['message'])):
        key = (item['code'], item['message'])
        if key not in seen:
            seen.add(key)
            ordered.append(item)
    return ordered


def _canonicalize_inputs(text: str) -> str:
    """Re-emit every fixed-input record through the one normaliser."""
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        stripped = line.rstrip('\r\n')
        if not stripped.startswith(INPUT_PREFIX):
            continue
        try:
            record = parse_canonical_json(stripped[len(INPUT_PREFIX):])
        except (TypeError, ValueError):
            continue
        ending = line[len(stripped):]
        lines[index] = INPUT_PREFIX + canonical_json(record) + ending
    return ''.join(lines)


def _tokenize_exclusions(text: str, data: dict) -> str:
    """Spell each prose VCS exclusion as the one reserved token it names."""
    for entry in _scope_entries(data.get('excluded_actions')):
        if entry.casefold() in VCS_ACTION_TOKENS:
            continue
        token = _prose_token(entry)
        if token is None:
            continue
        head, marker, rest = text.partition('\n---\n')
        if marker:
            text = head.replace(entry, token) + marker + rest
    return text


def apply_fixes(text: str, findings) -> tuple:
    """``(text, applied)`` -- the syntactic findings rewritten, nothing else."""
    applied = []
    for item in findings:
        if item['kind'] != SYNTACTIC:
            continue
        code = item['code']
        if code == 'input-json-noncanonical':
            text = _canonicalize_inputs(text)
        elif code == 'vcs-isolation-required':
            text = _set_frontmatter_field(text, 'isolation', 'required')
        elif code == 'vcs-exclusion-not-tokenized':
            text = _tokenize_exclusions(text, _parse_frontmatter(text))
        elif code == 'frontmatter-default-missing':
            missing = MISSING_KEY_RE.match(item['message'])
            if missing is None:
                continue
            text = _set_frontmatter_field(text, missing.group(1), DEFAULTABLE[missing.group(1)])
        else:
            continue
        applied.append(code)
    return (text, applied)


def _draft_target(file_arg: str, executor, pack):
    """One draft's ``(path, id, text, siblings)``, or a refusal."""
    path = Path(file_arg)
    text, failure = _read_utf8(path, 'draft')
    if failure is not None:
        return (None, {**failure, 'exit_code': 2})
    for key, value in (('executor', executor), ('pack', pack)):
        if value is not None:
            try:
                text = _set_frontmatter_field(text, key, value)
            except ValueError as error:
                return (None, {'error': str(error), 'exit_code': 2})
    ticket_id = str(_parse_frontmatter(text).get('id') or path.stem).strip()
    return ((path, ticket_id, text, {}), None)


def _ticket_target(run: str, ticket_id: str):
    """One issued ticket's ``(path, id, text, siblings)``, or a refusal."""
    for kind, value in (('run id', run), ('ticket id', ticket_id)):
        refusal = _segment_error(kind, value)
        if refusal is not None:
            return (None, {**refusal, 'exit_code': 2})
    root = _tickets_root()
    if root is None:
        return (None, {'error': NO_SINK_ERROR, 'exit_code': 2})
    run_dir = root / run
    path = run_dir / f'{ticket_id}.md'
    text, failure = _read_utf8(path, f'ticket {run}/{ticket_id}')
    if failure is not None:
        return (None, {**failure, 'exit_code': 2})
    siblings = {}
    for sibling in sorted(run_dir.glob('*.md')):
        body, failure = _read_utf8(sibling, f'ticket {run}/{sibling.stem}')
        if failure is None:
            siblings[sibling.stem] = body
    return ((path, ticket_id, text, siblings), None)


def _rewritable(text: str, path: Path, ticket_id: str = '', siblings=None):
    """``None`` when ``--fix`` may write this target, else its refusal.

    Refuses exactly where ``amend`` refuses a cut-time rewrite, because this
    is one: a claim, a status outside ``AMENDABLE_STATUSES``, an immutable
    ``checked_by``, a sealed cohort, and the v2 ``assignment_seal`` computed
    over the very authority fields ``--fix`` writes.
    """
    data = _parse_frontmatter(text)
    status = str(data.get('status') or '').strip().strip('`').strip()
    if str(data.get('claimed_by') or '').strip():
        return {'error': f'{path} is claimed by {data.get("claimed_by")}: --fix rewrites a draft or an unclaimed ticket, never an item a child is executing', 'exit_code': 2}
    if status and status not in AMENDABLE_STATUSES:
        return {'error': f"{path} is '{status}': --fix rewrites only {sorted(AMENDABLE_STATUSES)}, the statuses `amend` itself accepts", 'exit_code': 2}
    if str(data.get('checked_by') or '').strip():
        return {'error': f'{path} has an immutable checked_by cut reader: --fix refuses the cut-time rewrite `amend` refuses here', 'exit_code': 2}
    if str(data.get('assignment_seal') or '').strip():
        return {'error': f'{path} carries an assignment_seal: --fix writes the authority fields the seal is computed over, and cannot reseal them', 'exit_code': 2}
    if cohort_sealed(str(ticket_id or data.get('id') or ''), text, dict(siblings or {})):
        return {'error': f'{path} belongs to a sealed cohort: --fix refuses the cut-time rewrite `amend` refuses here', 'exit_code': 2}
    return None


def _cmd_lint(rest) -> dict:
    args = list(rest)
    fix = '--fix' in args
    args = [arg for arg in args if arg != '--fix']
    file_arg = _extract_flag(args, '--file')
    executor = _extract_flag(args, '--executor')
    pack = _extract_flag(args, '--pack')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'lint does not accept {stray}. usage: {LINT_USAGE}', 'exit_code': 2}
    if file_arg is not None:
        if args:
            return {'error': f'lint --file takes no run or id. usage: {LINT_USAGE}', 'exit_code': 2}
        target, refusal = _draft_target(file_arg, executor, pack)
    else:
        if len(args) != 2:
            return {'error': f'usage: {LINT_USAGE}', 'exit_code': 2}
        target, refusal = _ticket_target(args[0], args[1])
    if refusal is not None:
        return refusal
    path, ticket_id, text, siblings = target
    findings = lint_findings(text, ticket_id=ticket_id, siblings=siblings)
    applied = []
    if fix:
        blocked = _rewritable(text, path, ticket_id, siblings)
        if blocked is not None:
            return blocked
        try:
            updated, applied = apply_fixes(text, findings)
            if updated != text:
                if file_arg is None:
                    with _run_lock(str(_parse_frontmatter(text).get('run') or '')):
                        _write_text_atomically(path, updated)
                else:
                    _write_text_atomically(path, updated)
            text = updated
        except (OSError, ValueError) as error:
            return {'error': f'unwritable {path}: {error}', 'exit_code': 2}
        findings = lint_findings(text, ticket_id=ticket_id, siblings=siblings)
    remaining = [item for item in findings if item['kind'] == SEMANTIC]
    return {
        'lint': {
            'target': str(path), 'id': ticket_id, 'fixed': sorted(set(applied)),
            'findings': findings,
            'counts': {'total': len(findings), 'semantic': len(remaining),
                       'syntactic': len(findings) - len(remaining)},
        },
        'exit_code': 1 if remaining else 0,
    }


__all__ = ('LINT_USAGE', 'apply_fixes', 'lint_findings', '_cmd_lint')
