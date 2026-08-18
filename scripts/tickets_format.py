"""Ticket format support."""

from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime, timezone

VALID_STATUSES = {'pending', 'ready', 'claimed', 'suspended', 'complete', 'blocked', 'stalled', 'failed', 'limited'}
LOOP_EXECUTOR = 'orch-loop'
DISPATCHING_EXECUTORS = ('orch-frontier', LOOP_EXECUTOR)
SCRIPT_EXECUTOR_PREFIX = 'script:'
ORACLE_CLASSES = ('deterministic', 'judged', 'evidence')
ORACLE_PROVENANCES = ('pre-existing', 'authored-here')
REQUIRED_TICKET_KEYS = ('id', 'executor', 'depends_on', 'write_scope', 'bound')
REQUIRED_LIFECYCLE_KEYS = ('run', 'status')
CRITERION_BULLET_RE = re.compile('^ {0,3}(?:[-*+]|\\d+[.)])\\s+')
ORACLE_RE = re.compile('oracle:\\s*([^|\\n]*)', re.IGNORECASE)
ORACLE_CLASS_RE = re.compile('oracle_class:\\s*([A-Za-z_-]*)', re.IGNORECASE)
PROVENANCE_RE = re.compile('provenance:\\s*([A-Za-z_-]*)', re.IGNORECASE)
DURATION_RE = re.compile('^(\\d+)(m|h)$')
RESULT_TOKEN_SPLIT_RE = re.compile('[\\s`\\"\'<>()\\[\\]{},;|]+')
RESULT_TOKEN_STRIP = '.:!?*_-'
DEFAULT_BOUND_MINUTES = 60
EXECUTOR_SECTIONS = ('Result', 'Verification', 'Feedback', 'Risks', 'Handoff')
EXECUTOR_SECTIONS_BY_KEY = {name.lower(): name for name in EXECUTOR_SECTIONS}
CUT_SECTIONS = ('Objective', 'Fixed inputs', 'Completion test', 'Return fields')
CUT_SECTIONS_BY_KEY = {name.lower(): name for name in CUT_SECTIONS}
INSTRUCTION_BUDGET = 300
INSTRUCTION_SECTIONS = ('Objective', 'Completion test', 'Return fields')
LINK_TARGET_RE = re.compile('\\]\\([^)]*\\)')
SECTION_ORDER = ('Objective', 'Fixed inputs', 'Completion test', 'Return fields') + EXECUTOR_SECTIONS
SECTION_RANK = {name.lower(): i for i, name in enumerate(SECTION_ORDER)}
OPTIONAL_SECTION = 'Handoff'
REQUIRED_SECTIONS = tuple((name for name in SECTION_ORDER if name != OPTIONAL_SECTION))
REQUIRED_ISOLATION = 'required'
# Each pack's `workspace` cell names its mechanism. This literal mirrors
# packs/ because an installed copy has no library tree to read; the matching
# table assertion in tests/test_validate.py keeps the workspace map in sync.
PACK_WORKSPACE_MECHANISMS = None  # bound by the public tickets facade
GIT_WORKSPACE_MECHANISMS = frozenset({'git', 'git plus render'})
TERMINAL_STATES = ('complete', 'blocked', 'stalled', 'limited', 'failed')
PACK_NAME_PREFIX = 'orch-'
PACK_NAME_SUFFIX = '-pack'
ROOT_EXECUTOR = 'orch-decompose'
GRANTED_SCOPE_KEY = 'granted_scope'
TEMPLATE_FILE = 'template.md'
PLACEHOLDER_RE = re.compile('\\{\\{\\s*([^{}]*?)\\s*\\}\\}')
def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and (value[0] in '"\''):
        return value[1:-1]
    return value
def _parse_frontmatter(text: str) -> dict:
    """Parse the leading ``---``-delimited block: scalars and simple lists."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return {}
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end = i
            break
    if end is None:
        return {}
    data: dict = {}
    i = 1
    while i < end:
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or ':' not in line:
            i += 1
            continue
        key, _, rest = line.partition(':')
        key = key.strip()
        rest = rest.strip()
        if rest == '':
            items = []
            j = i + 1
            while j < end:
                item_stripped = lines[j].strip()
                if item_stripped.startswith('- '):
                    items.append(_unquote(item_stripped[2:].strip()))
                    j += 1
                elif item_stripped == '-':
                    j += 1
                else:
                    break
            data[key] = items
            i = j if items else i + 1
        elif rest.startswith('[') and rest.endswith(']'):
            inner = rest[1:-1].strip()
            data[key] = [] if not inner else [_unquote(p.strip()) for p in inner.split(',')]
            i += 1
        else:
            data[key] = _unquote(rest)
            i += 1
        continue
    return data
def _set_frontmatter_field(text: str, key: str, value: str) -> str:
    """Replace or insert one scalar frontmatter field, leaving the rest byte-exact."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip('\r\n') != '---':
        raise ValueError('ticket is missing frontmatter')
    end = None
    for i in range(1, len(lines)):
        if lines[i].rstrip('\r\n') == '---':
            end = i
            break
    if end is None:
        raise ValueError('ticket frontmatter is not terminated')
    newline = '\r\n' if lines[0].endswith('\r\n') else '\n'
    for i in range(1, end):
        line_key = lines[i].split(':', 1)[0].strip()
        if line_key == key:
            lines[i] = _frontmatter_line(key, value, newline)
            return ''.join(lines)
    lines.insert(end, _frontmatter_line(key, value, newline))
    return ''.join(lines)
def _frontmatter_line(key: str, value: str, newline: str) -> str:
    """One scalar frontmatter line. An empty value carries no trailing space:
    `claimed_by:` is how an unclaimed ticket reads on disk."""
    return f'{key}: {value}{newline}' if value != '' else f'{key}:{newline}'
class TicketFormatError(ValueError):
    """The ticket's markdown cannot be written safely as it stands."""
def _fence_run(line: str):
    """The ``` or ~~~ run this line opens or closes a fenced block with.

    None at four or more columns of indentation: CommonMark 4.4-4.5 makes
    that indented-code content rather than a fence, and a ticket quoting an
    indented snippet is ordinary. Opening a block there opens one nothing
    closes, which now costs the whole write (`_write_section`).
    """
    if line.startswith('\t') or len(line) - len(line.lstrip(' ')) >= 4:
        return None
    stripped = line.strip()
    for char in ('`', '~'):
        if stripped.startswith(char * 3):
            return char * (len(stripped) - len(stripped.lstrip(char)))
    return None
def _scan_sections(lines, start: int=0):
    """The ``## `` boundary indices below ``start``, and any unclosed fence.

    A ``## `` line inside a fenced block is quoted content, not a heading:
    every deliverable in this repository is markdown with ``## `` headings
    and executors quote them at length. Counting a quotation as a boundary
    truncates the span a replacement rewrites -- deleting the opening
    fence, orphaning the closing one, and promoting the quoted heading to
    a real one that `_sections` then resolves last-writer-wins.

    The second return value is the index of a fence still open at the end
    of the scan. Below it no heading is findable, so a reader sees fewer
    sections than the file means and a writer would create a duplicate of
    one that is already there; only the writer treats it as fatal.
    """
    found = []
    fence = None
    opened_at = None
    for i in range(start, len(lines)):
        line = lines[i]
        run = _fence_run(line)
        if fence is None:
            if run is not None:
                fence = run
                opened_at = i
            elif line.startswith('## '):
                found.append(i)
        elif run is not None and run[0] == fence[0] and (len(run) >= len(fence)) and (not line.strip()[len(run):].strip()):
            fence = None
            opened_at = None
    return (found, opened_at)
def _heading_lines(lines, start: int=0) -> list:
    """Indices of the ``## `` lines that are section boundaries."""
    return _scan_sections(lines, start)[0]
def _sections(text: str) -> dict:
    """Map each ``## Heading`` to its stripped body text."""
    sections: dict = {}
    heading = None
    body: list = []
    lines = text.splitlines()
    starts = set(_heading_lines(lines))
    for i, line in enumerate(lines):
        if i in starts:
            if heading is not None:
                sections[heading] = '\n'.join(body).strip()
            heading = line[3:].strip()
            body = []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        sections[heading] = '\n'.join(body).strip()
    return sections
def instruction_words(text: str) -> int:
    """One ticket's instruction in words, markdown link targets stripped.

    The objective, the completion test, the return fields and the
    frontmatter `excluded_actions` -- what a child loads on every dispatch.
    Never `## Fixed inputs`: those are identities, and counting them would
    charge a cutter for supplying evidence (rules/token-economy.md §11).
    """
    sections = _sections(text)
    parts = [str(item) for item in _parse_frontmatter(text).get('excluded_actions') or []]
    parts += [sections.get(name, '') for name in INSTRUCTION_SECTIONS]
    return sum((len(LINK_TARGET_RE.sub(']', part).split()) for part in parts))
def _frontmatter_end(lines) -> int:
    """The first index below the frontmatter block; 0 when there is none.

    Both the writer and the overwrite guard look for headings only below
    this line: a wrapped frontmatter value can begin a line with ``## ``,
    and reading one as a section is how a guard comes to report on a
    heading that is not a section at all.
    """
    if not lines or lines[0].rstrip('\r\n') != '---':
        return 0
    for i in range(1, len(lines)):
        if lines[i].rstrip('\r\n') == '---':
            return i + 1
    return 0
def _section_body(text: str, heading: str) -> str:
    """One section's current body, found the way ``_write_section`` finds it.

    Same frontmatter skip, same fence-aware scan, same case-insensitive
    match, so the content the overwrite guard reads is the content of the
    very span the writer is about to overwrite. A guard resolving a
    different heading than the writer writes is a guard that passes while
    the clobber happens.
    """
    lines = text.splitlines()
    starts, _ = _scan_sections(lines, _frontmatter_end(lines))
    for position, index in enumerate(starts):
        if lines[index][3:].strip().lower() != heading.strip().lower():
            continue
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        return '\n'.join(lines[index + 1:end]).strip()
    return ''
def _body_block(body: str, newline: str) -> str:
    """Normalize a body to the file's line ending, ending in exactly one."""
    normalized = body.replace('\r\n', '\n').replace('\r', '\n').strip('\n')
    if not normalized:
        return ''
    return newline.join(normalized.split('\n')) + newline
def _write_section(text: str, heading: str, body: str, append: bool=False) -> str:
    """Replace or create one ``## Heading`` body, leaving every other byte alone."""
    lines = text.splitlines(keepends=True)
    newline = '\r\n' if lines and lines[0].endswith('\r\n') else '\n'
    starts, unclosed = _scan_sections(lines, _frontmatter_end(lines))
    if unclosed is not None:
        raise TicketFormatError(f"unterminated fence opened at line {unclosed + 1} ({lines[unclosed].strip()}): every heading below it reads as quoted content, so writing '## {heading}' would create a second one. Close the fence in the ticket, then retry")
    found = None
    for i in starts:
        if lines[i][3:].strip().lower() == heading.lower():
            found = i
            break
    if found is None:
        block = _body_block(body, newline)
        segment = f'## {heading}{newline}{newline}{block}' if block else f'## {heading}{newline}'
        insert_at = None
        target_rank = SECTION_RANK.get(heading.lower())
        if target_rank is not None:
            for i in starts:
                rank = SECTION_RANK.get(lines[i][3:].strip().lower())
                if rank is not None and rank > target_rank:
                    insert_at = i
                    break
        if insert_at is None:
            prefix = ''.join(lines).rstrip('\r\n')
            if prefix:
                prefix += newline + newline
            return prefix + segment
        return ''.join(lines[:insert_at]) + segment + newline + ''.join(lines[insert_at:])
    end = next((i for i in starts if i > found), len(lines))
    if append:
        prior = ''.join(lines[found + 1:end]).rstrip().lstrip('\r\n')
        if prior:
            body = f'{prior}\n\n{body}'
    block = _body_block(body, newline)
    head = lines[found]
    if not head.endswith('\n'):
        head += newline
    segment = head + newline + block if block else head
    if end < len(lines):
        segment += newline
    return ''.join(lines[:found]) + segment + ''.join(lines[end:])
def _read_utf8(path, subject: str='ticket', encoding: str='utf-8'):
    """One file's text as ``(text, None)``, or ``(None, {"error": ...})``.

    Both exceptions in one place because they are one failure to a caller --
    the file is there and its bytes cannot be read -- and because they are
    not one exception to Python: ``UnicodeDecodeError`` is a ``ValueError``,
    not an ``OSError``, so a handler written for unreadable files let
    non-UTF-8 bytes through as a traceback on a channel whose whole contract
    is one JSON document. Every read site in this script goes through here,
    so the next one cannot be written with half the handler.
    """
    reader = path if hasattr(path, 'read_text') else Path(path)
    try:
        return (reader.read_text(encoding=encoding), None)
    except (OSError, UnicodeDecodeError) as error:
        return (None, {'error': f'unreadable {subject}: {error}'})
def _scope_entries(declared) -> list:
    """One scope field as its entries, whichever shape it was written in.

    A bare scalar is the one-entry list it means — the shape half the
    tickets in the sink carry — and iterating the string instead yields its
    characters, a scope of letters that matches nothing and grades nothing.
    """
    if isinstance(declared, str):
        entry = declared.strip()
        return [entry] if entry else []
    return [str(entry).strip() for entry in declared or [] if str(entry).strip()]
def effective_write_scope(data: dict) -> list:
    """The paths this item may change: its cut ``write_scope``, then every
    caller-side grant, in the order the grants landed.

    One reader for both halves, because they are two writers of one fact.
    ``write_scope`` is the cut's and is frozen with the cut
    (contracts/work-item.md: a ticket never widens its own scope);
    ``granted_scope`` is the caller widening an already-claimed item's
    authority mid-flight, recorded by ``grant``. Read separately, a result
    that used a granted path is a scope breach at the join and the grant is
    a message nobody kept.
    """
    scope = _scope_entries(data.get('write_scope'))
    for entry in _scope_entries(data.get(GRANTED_SCOPE_KEY)):
        if entry not in scope:
            scope.append(entry)
    return scope
def _criteria(section_text: str) -> list:
    """The completion-test criteria in ``section_text``, one string each.

    A criterion is a bullet; the lines under it that are not bullets are its
    own continuation, because a criterion long enough to wrap carries its
    oracle on the second line and reading each line as a criterion would
    report a defect on a clean one. A bullet inside a fenced block is quoted
    content — every deliverable here is markdown and executors quote ticket
    bodies at length — so fences are skipped exactly as ``_scan_sections``
    skips them.

    Indentation is the second signal and it is relative: a bullet indented
    deeper than the bullet that opened the criterion now open is that
    criterion's own text — a sentence wrapping onto a digit and a period, or
    a list nested under it — and opens nothing. A bullet at that opening
    indentation or less opens the next criterion, so a section whose criteria
    are themselves written indented is still a list.

    An unindented prose line ends the open criterion's continuation and never
    the list: a criterion written after such a line still surfaces. This
    function is criterion parsing's one owner — ``criterion_defects`` and
    ``scripts/cutcheck.py`` both read a completion test through it, and a
    second spelling is how a section reads one way to the cutter and another
    way to the refusal that issues it.
    """
    criteria: list = []
    fence = None
    opened_at = 0
    open_item = False
    for line in section_text.splitlines():
        run = _fence_run(line)
        if fence is not None:
            if run is not None and run[0] == fence[0] and (len(run) >= len(fence)):
                fence = None
            continue
        if run is not None:
            fence = run
            continue
        stripped = line.strip()
        if not stripped:
            continue
        match = CRITERION_BULLET_RE.match(line)
        if match:
            depth = len(line) - len(line.lstrip())
            if open_item and depth > opened_at:
                criteria[-1] = f'{criteria[-1]} {stripped}'
                continue
            opened_at = depth
            open_item = True
            criteria.append(line[match.end():].strip())
            continue
        if not open_item:
            continue
        if not line[0].isspace():
            open_item = False
            continue
        criteria[-1] = f'{criteria[-1]} {stripped}'
    return criteria
def criterion_defects(section_text: str) -> list:
    """Every defect in one ``## Completion test`` section, criterion by
    criterion.

    Per contracts/work-item.md a criterion names its oracle and its
    oracle_class, and may name its provenance; per contracts/verdict.md the
    classes are a closed set. Graded per criterion rather than over the
    section, because a section whose first criterion names a class and whose
    second names none satisfies any whole-section test while dispatching an
    unverifiable item.
    """
    criteria = _criteria(section_text)
    if not criteria:
        return ['completion test states no criterion: one bullet per criterion, each naming `oracle:` and `oracle_class:`']
    defects = []
    for number, text in enumerate(criteria, start=1):
        oracle = ORACLE_RE.search(text)
        if oracle is None or not oracle.group(1).strip(' `.,;*'):
            defects.append(f'criterion {number} names no `oracle:`, the exact check that decides it: {text[:60]!r}')
        oracle_class = ORACLE_CLASS_RE.search(text)
        value = oracle_class.group(1).strip().lower() if oracle_class else ''
        if not value:
            defects.append(f'criterion {number} names no `oracle_class:`, one of {list(ORACLE_CLASSES)}: {text[:60]!r}')
        elif value not in ORACLE_CLASSES:
            defects.append(f"criterion {number} names oracle_class '{value}', not one of {list(ORACLE_CLASSES)}")
        provenance = PROVENANCE_RE.search(text)
        declared = provenance.group(1).strip().lower() if provenance else ''
        if provenance is not None and declared not in ORACLE_PROVENANCES:
            defects.append(f"criterion {number} names provenance '{declared}', not one of {list(ORACLE_PROVENANCES)}")
    return defects
def ticket_defects(text: str, stub: bool=False) -> list:
    """Every way ``text`` is not a ticket per contracts/work-item.md.

    ``stub=True`` grades a template's stub: a ticket missing only ``run``,
    ``status`` and ``claimed_*``, which instantiation adds. Everything else
    is graded identically, so a stub admitted into a template is a ticket
    the moment it is instantiated.

    A file with no frontmatter is that one defect and no other: every check
    below reads the frontmatter or the body it heads, so listing what a
    non-ticket also lacks says nothing a reader can act on.
    """
    data = _parse_frontmatter(text)
    if not data:
        return ["no frontmatter: a ticket opens with a '---' block (contracts/work-item.md)"]
    defects = []
    required = REQUIRED_TICKET_KEYS if stub else REQUIRED_TICKET_KEYS + REQUIRED_LIFECYCLE_KEYS
    for key in ('id', 'run', 'status', 'executor', 'depends_on', 'write_scope', 'bound'):
        if key in required and key not in data:
            defects.append(f"frontmatter has no '{key}'")
    status = data.get('status')
    if isinstance(status, str) and status.strip():
        normalized = status.strip().strip('`').strip()
        if normalized not in VALID_STATUSES:
            defects.append(f"status '{normalized}' is not one of {sorted(VALID_STATUSES)}")
    sections = {name.strip().lower(): body for name, body in _sections(text).items()}
    for name in REQUIRED_SECTIONS:
        if name.lower() not in sections:
            defects.append(f"no '## {name}' section")
    completion = sections.get('completion test')
    if completion is not None:
        defects.extend(criterion_defects(completion))
    return defects
REQUIRED_FIELDS_CELL = 'required_spec_fields'
FIELD_GLOSS_RE = re.compile('\\s+[—-]{1,2}\\s+')
FIELD_WORD_RE = re.compile('[a-z]{4,}')
def _parse_bound_minutes(bound) -> int:
    if isinstance(bound, str):
        match = DURATION_RE.match(bound.strip())
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            return value * 60 if unit == 'h' else value
    return DEFAULT_BOUND_MINUTES
def _parse_iso(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        text = value.strip()
        if text.endswith('Z'):
            text = text[:-1] + '+00:00'
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None
def _extract_flag(args: list, flag: str):
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            value = args[idx + 1]
            del args[idx:idx + 2]
            return value
        del args[idx:idx + 1]
    return None
def _extract_all(args: list, flag: str) -> list:
    """Every value of a flag that may be repeated, in the order given.

    ``--criterion`` and ``--input`` name one thing each; a ticket has as
    many as the cut found. ``_extract_flag`` answers the first and removes
    it, so draining it is the whole implementation — and a trailing flag
    with no value is removed and ends the drain rather than looping on it.
    """
    values = []
    while flag in args:
        value = _extract_flag(args, flag)
        if value is None:
            break
        values.append(value)
    return values
def _split_commas(value) -> list:
    """One comma-separated flag value as a list, empty entries dropped."""
    return [part.strip() for part in str(value or '').split(',') if part.strip()]
def _executor_of(item: dict) -> str:
    return str(item.get('executor') or '').strip().strip('`').strip()
