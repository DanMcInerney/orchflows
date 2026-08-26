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
    from .tickets_admission import VCS_ACTION_TOKENS, grade_result
    from .tickets_commands import LINT_USAGE
    from .tickets_context import graded_admission, run_snapshot
    from .tickets_format import GATE_ID_MARKER, INSTRUCTION_BUDGET, ORACLE_RE, ROOT_EXECUTOR, _criteria, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _scope_entries, _sections, _set_frontmatter_field, _whole_suite, canonical_json, effective_write_scope, instruction_words, parse_canonical_json
    from .tickets_issue import AMENDABLE_STATUSES, NEW_DEFAULT_BOUND, _issue_defects
    from .tickets_scope import path_covers
    from .tickets_store import NO_SINK_ERROR, _run_lock, _segment_error, _tickets_root, _write_text_atomically
else:
    from tickets_admission import VCS_ACTION_TOKENS, grade_result
    from tickets_commands import LINT_USAGE
    from tickets_context import graded_admission, run_snapshot
    from tickets_format import GATE_ID_MARKER, INSTRUCTION_BUDGET, ORACLE_RE, ROOT_EXECUTOR, _criteria, _executor_of, _extract_flag, _parse_frontmatter, _read_utf8, _scope_entries, _sections, _set_frontmatter_field, _whole_suite, canonical_json, effective_write_scope, instruction_words, parse_canonical_json
    from tickets_issue import AMENDABLE_STATUSES, NEW_DEFAULT_BOUND, _issue_defects
    from tickets_scope import path_covers
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
# Family 3's reading of a path in prose, restated where the ticket family can
# use it: a token holding a glob is a pattern rather than a path, one holding
# an angle bracket is a placeholder for wherever the run puts its state, and a
# short final extension names a file even with no directory in front of it.
GLOB_CHARS_RE = re.compile(r'[*?\[\]]')
PLACEHOLDER_CHARS_RE = re.compile(r'[<>]')
EXTENSION_RE = re.compile(r'\.[A-Za-z0-9]{1,5}$')
# The other half of that reading: which clause of an exclusion the path sits in.
# A prohibition names the path it forbids; a proviso names one the item must
# re-pin or wait on *in order to* act -- "with tests/pins.json re-pinned" grants
# pins.json rather than reserving it. Adjacency is the whole rule, as
# cutcheck's is: a marker anywhere in the sentence would drop live
# contradictions. Restated, never imported: the architecture map forbids this
# family importing cutcheck, so the agreement pin is what holds the two equal.
# The window is a floor, not a tuning: the pattern is anchored to the path's
# own edge, so every width that holds the longest marker reads alike, and only
# too short a one is felt -- it slices a word open and reads "herewith" as
# "with". Spelled a literal here and an alias of `DENIAL_WINDOW` there, so the
# two are pinned equal by name rather than by either one being the source.
PERMISSION_RE = re.compile(r'\b(?:with|once|after|provided|unless|except)\s+$', re.I)
PERMISSION_WINDOW = 24
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


def _plain(path: str) -> str:
    """One path's plain spelling: ``./x`` and ``x`` name the same file."""
    text = str(path).strip()
    while text[:2] == './':
        text = text[2:]
    return text


def _prohibits(action: str, target: str) -> bool:
    """Is ``target`` what this exclusion forbids, or a proviso attached to it?

    Named once outside a permitting clause, the path is forbidden: an exclusion
    that forbids a path in one clause and permits it in another is still
    forbidding it, so the reading keeps the prohibition.
    """
    start = 0
    while True:
        at = action.find(target, start)
        if at < 0:
            return False
        before = action[:at]
        # ``target`` is the plain spelling and the clause is not: a proviso
        # written ``with ./x re-pinned`` is found past its own ``./``, which
        # ends the window in punctuation and hides the marker standing in
        # front of it. The two halves of this reading have to compose.
        while before[-2:] == './':
            before = before[:-2]
        if not PERMISSION_RE.search(before[max(0, len(before) - PERMISSION_WINDOW):]):
            return True
        start = at + 1


def _path_tokens(entry: str) -> list:
    """The tokens in one prose action that name a path."""
    found = []
    for token in entry.replace('`', ' ').split():
        token = token.lstrip('(<["\'').rstrip(')>],;:."\'')
        if not token or token[:1] == '-' or GLOB_CHARS_RE.search(token):
            continue
        if PLACEHOLDER_CHARS_RE.search(token):
            continue
        plain = _plain(token)
        if plain and ('/' in token or EXTENSION_RE.search(token)):
            found.append(plain)
    return found


def _contradiction_findings(data: dict) -> list:
    """Cutcheck family 3's judgment, reported while the text can still change.

    An exclusion naming a path the write scope grants states two things about
    one path: the item may write it, and the item may not. `cutcheck` reports
    it, but only on the cut -- and by then the root is sealed, so the exclusion
    lives in a statement the decomposer holds no authority to edit and no cut
    it may make reaches exit 0. Reported here, the producer sees it while the
    draft is still a draft. Semantic on purpose: which of the two the author
    meant is a decision, so `--fix` may not pick one.

    The path has to be the one the exclusion *forbids*: named under a proviso
    it is granted, not reserved, and `./x` and `x` are one path on both sides.
    """
    scope = _scope_entries(data.get('write_scope'))
    findings = []
    for action in _scope_entries(data.get('excluded_actions')):
        for target in _path_tokens(action):
            if not _prohibits(action, target):
                continue
            for entry in scope:
                plain = _plain(entry)
                if path_covers(target, plain) or path_covers(plain, target):
                    findings.append(_finding(
                        'scope-contradiction', f'excluded_actions: {action} | {entry}',
                    ))
                    break
    return findings


def _own_modules(command: str, tree: Path, scope: list) -> bool:
    """Does every module this oracle names sit inside this item's own scope?

    `_whole_suite` owns the shape question -- whether a command names a node
    or a whole module -- and this owns a different one, so it reads the scope
    rather than re-asking that. A whole module discriminates nothing *between
    siblings*, which is the finding's whole subject; but a module the item
    itself was granted is the item's own artifact, and no sibling runs it
    because no sibling may write it. Naming it whole names exactly this
    item's work, so the finding over it is a false one -- the shape it
    convicts is the shape a unit that authors its own test module has.

    Every resolvable module must be covered, not merely one: an oracle
    naming its own module beside the whole suite still runs the suite.
    """
    named = []
    for token in command.split():
        if token[:1] in ('-', '"', "'"):
            continue
        path = token if '/' in token else token.replace('.', '/')
        path = path if path.endswith('.py') else path + '.py'
        if (tree / path).is_file():
            named.append(path)
    if not named:
        return False
    return all(any(path_covers(entry, path) for entry in scope) for path in named)


def _oracle_findings(text: str, tree: Path, scope=None) -> list:
    """One finding per criterion whose oracle runs the suite it is stated under."""
    scope = list(scope or [])
    findings = []
    for number, criterion in enumerate(_criteria(_sections(text).get('Completion test', '')), start=1):
        match = ORACLE_RE.search(criterion)
        command = match.group(1).strip(' `.,;*') if match else ''
        if command and _whole_suite(command, tree) and not _own_modules(command, tree, scope):
            findings.append(_finding(
                'whole-suite-oracle',
                f'criterion {number} names `{command}`, which runs the identical tests under every item '
                'it is stated under and so discriminates none of them',
                severity='warning',
            ))
    return findings


def lint_findings(text: str, *, ticket_id: str, siblings=None, tree=None, issued: bool=False) -> list:
    """Every finding the graders report on this exact snapshot, deduplicated.

    ``issued`` says which of the two targets this is. A draft is graded as
    ``new`` would grade it; a ticket already in the sink is not, because
    ``new``'s issue-time rules grade a state it has lawfully left -- the
    checker identity `check` wrote is the one this module kept reporting as
    a defect, so `lint <run> <id>` could not return to exit 0 after a check.
    """
    data = _parse_frontmatter(text)
    if not data:
        return [_finding('no-frontmatter', "a ticket opens with a '---' block (contracts/work-item.md)")]
    findings = []
    for defect in _issue_defects(text, issued=issued):
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
    findings.extend(_contradiction_findings(data))
    graded = graded_admission(ticket_id, text, siblings, data.get('run'))
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
    findings.extend(_oracle_findings(text, tree or _repo_tree(), effective_write_scope(data)))
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
    # Every member this reader could read: lint reports on what is there, and
    # an unreadable sibling is the finding its own `lint` call will carry.
    siblings, _unreadable = run_snapshot(run_dir)
    return ((path, ticket_id, text, siblings), None)


def _rewritable(text: str, path: Path, ticket_id: str = '', siblings=None):
    """``None`` when ``--fix`` may write this target, else its refusal.

    Refuses exactly where ``amend`` refuses a cut-time rewrite, because this
    is one: a claim, a status outside ``AMENDABLE_STATUSES``, an immutable
    ``checked_by``, and the ``assignment_seal`` computed
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
    issued = file_arg is None
    findings = lint_findings(text, ticket_id=ticket_id, siblings=siblings, issued=issued)
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
        findings = lint_findings(text, ticket_id=ticket_id, siblings=siblings, issued=issued)
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
