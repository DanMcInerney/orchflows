"""Ticket format support."""
from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import datetime, timezone
if __package__:
    from .tickets_registry import (
        CALLABLE_EXECUTORS, EXECUTOR_REGISTRY,
        executor_refusal, executor_registered,
    )
else:
    from tickets_registry import (
        CALLABLE_EXECUTORS, EXECUTOR_REGISTRY,
        executor_refusal, executor_registered,
    )
if __package__:
    from .tickets_adapters import adapter_id
    from .tickets_shapes import (
        DONE_BINDING_FIELDS, DONE_BINDING_REQUIRED, DONE_BINDING_VALUES,
        TICKET_FRONTMATTER_FIELDS, TICKET_FRONTMATTER_REQUIRED,
        TICKET_FRONTMATTER_VALUES,
    )
    from .tickets_markdown import (
        CUT_SECTIONS, CUT_SECTIONS_BY_KEY, EXECUTOR_SECTIONS,
        EXECUTOR_SECTIONS_BY_KEY, OPTIONAL_SECTIONS, REPORT_SECTION,
        REQUIRED_SECTIONS,
        SECTION_ORDER, SECTION_RANK, STANDARDS_FIELD, TicketFormatError,
        _body_block,
        _duplicate_frontmatter_keys, _fence_run, _frontmatter_end,
        _frontmatter_line, _heading_lines, _parse_frontmatter,
        _remove_frontmatter_field, _unquote, _scan_sections, _section_body,
        _sections, _set_frontmatter_field, _write_section, dequote,
        quote_filed_body, unquote_filed_body,
    )
else:
    from tickets_adapters import adapter_id
    from tickets_shapes import (
        DONE_BINDING_FIELDS, DONE_BINDING_REQUIRED, DONE_BINDING_VALUES,
        TICKET_FRONTMATTER_FIELDS, TICKET_FRONTMATTER_REQUIRED,
        TICKET_FRONTMATTER_VALUES,
    )
    from tickets_markdown import (
        CUT_SECTIONS, CUT_SECTIONS_BY_KEY, EXECUTOR_SECTIONS,
        EXECUTOR_SECTIONS_BY_KEY, OPTIONAL_SECTIONS, REPORT_SECTION,
        REQUIRED_SECTIONS,
        SECTION_ORDER, SECTION_RANK, STANDARDS_FIELD, TicketFormatError,
        _body_block,
        _duplicate_frontmatter_keys, _fence_run, _frontmatter_end,
        _frontmatter_line, _heading_lines, _parse_frontmatter,
        _remove_frontmatter_field, _unquote, _scan_sections, _section_body,
        _sections, _set_frontmatter_field, _write_section, dequote,
        quote_filed_body, unquote_filed_body,
    )
# The bound grammar is `tickets_bound`'s, read here so every holder gets the
# one spelling. Reached by name in the sibling branch: the import census is
# pinned.
if __package__:
    from .tickets_bound import DEFAULT_BOUND_MINUTES, _parse_bound_minutes
else:
    _bound_module = __import__('tickets_bound')
    DEFAULT_BOUND_MINUTES, _parse_bound_minutes = (_bound_module.DEFAULT_BOUND_MINUTES, _bound_module._parse_bound_minutes)
VALID_STATUSES = set(TICKET_FRONTMATTER_VALUES['status'])
# The one value the `frame` marker takes, read off the declared shape rather
# than spelled twice. A frame is the durable record of one workflow
# invocation, and the marker tells every reader that the ticket binds no
# executor because nothing dispatches it.
FRAME_MARKER = TICKET_FRONTMATTER_VALUES['frame'][0]
# The field a planning `do` records its artifact kind under, named here and
# nowhere else, its two values read off the declared shape. A standard's
# `## Lens` has one entry per artifact kind: a `do` takes its kind from the
# adapter and a `judge` from its Context, so this names what neither does.
MAKES_FIELD = 'makes'
PLANNING_KINDS = tuple(TICKET_FRONTMATTER_VALUES[MAKES_FIELD])
# The Context clause a judge's typed artifact identities are written on:
# `tickets_mint.py` writes them, `tickets_assignment.py` reads their kind.
ARTIFACT_CLAUSE = '- artifact: '
SCRIPT_EXECUTOR_PREFIX = 'script:'
REQUIRED_LIFECYCLE_KEYS = ('run', 'status')
REQUIRED_TICKET_KEYS = tuple(
    key for key in TICKET_FRONTMATTER_REQUIRED if key not in REQUIRED_LIFECYCLE_KEYS
)
ALLOWED_TICKET_KEYS = frozenset(TICKET_FRONTMATTER_FIELDS)
DURATION_RE = re.compile('^(\\d+)(m|h)$')
RESULT_TOKEN_SPLIT_RE = re.compile('[\\s`\\"\'<>()\\[\\]{},;|]+')
RESULT_TOKEN_STRIP = '.:!?*_-'
SUCCESSOR_CONTEXT_PREFIXES = ('- state:', '- watch:')
REQUIRED_ISOLATION = 'required'
DELIVERED_STATE = 'complete'
TERMINAL_STATES = (DELIVERED_STATE, 'blocked', 'stalled', 'limited', 'failed')
# The terminal states that leave a Result behind for a dependent to read.
# `complete` delivered the whole Goal and `limited` delivered part of it with
# honest accounting; both file the evidence the next item is written against.
# `blocked`, `failed` and `stalled` filed no such artifact, so a dependent
# admitted over them would be reading an absence. Beside the states it is
# drawn from rather than in one of its two readers, `tickets_admission` and
# `tickets_readiness`, which had drifted apart while each held a copy.
RESULT_BEARING_STATES = (DELIVERED_STATE, 'limited')
# The ids the round machinery mints after a cut is already sealed, and the
# one grammar that names them. A landing whose `done` command refused arms
# its `<id>.repair.NN` round, and the `check` done form mints a
# `<round>.done` judge beside one. The advance and the sealed-admission
# command have to agree on which ids those are, or the second reads every
# armed round as an assignment the seal did not name.
REPAIR_MARKER = 'repair'
DONE_TICKET_SUFFIX = '.done'
ROUND_ID_RE = re.compile(
    f'^(?P<parent>.+)\\.{REPAIR_MARKER}\\.(?P<number>\\d+)$'
)
# The auto id grammar of the two minting commands. A runtime child is minted
# under the ticket that called it -- `<parent>.<n>` -- and a parentless one
# roots its own tree as `B<n>`, so the id alone says where in the call tree a
# ticket hangs. Ordinals are per parent and never reused inside one run: the
# command mints under the run lock.
MINT_ROOT_ID_RE = re.compile('^B(?P<number>\\d+)$')
MINT_CHILD_ID_RE = re.compile('^(?P<parent>.+)\\.(?P<number>\\d+)$')
ESCAPED_NEWLINE_RE = re.compile('\\\\n')
# A literal backslash then the letter 'n' -- the two-character escape a shell
# or a hand can type in place of the one byte it stands for. A real newline
# never matches this: it is one byte, not two.
_PATH_RUN_RE = re.compile('(?:\\\\[^\\s\\\\]*)+')
_DRIVE_LETTER_RE = re.compile('[A-Za-z]:')
_INLINE_CODE_RE = re.compile('`[^`]*`')
class DuplicateJsonKey(ValueError):
    """A canonical JSON object repeated one key."""
def _json_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateJsonKey(str(key))
        value[key] = item
    return value
def _nonfinite_json(value):
    raise ValueError(f"non-finite JSON number {value}")
def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True, allow_nan=False)
def parse_canonical_json(encoded: str):
    """Parse the portable canonical JSON grammar shared by ticket fields."""
    return json.loads(encoded, object_pairs_hook=_json_object, parse_constant=_nonfinite_json)
def _windows_path_spans(line: str) -> list:
    """Character spans in ``line`` that read as a Windows path, not prose."""
    spans = []
    for match in _PATH_RUN_RE.finditer(line):
        run = match.group()
        prefix = line[max(0, match.start() - 2):match.start()]
        rooted = run.startswith('\\\\') or bool(_DRIVE_LETTER_RE.fullmatch(prefix))
        segments = [part for part in run.split('\\') if part]
        if rooted and segments:
            spans.append(match.span())
        elif not rooted and len(segments) >= 2 and all(len(part) >= 2 for part in segments):
            spans.append(match.span())
    return spans
def _inline_code_spans(line: str) -> list:
    """Character spans in ``line`` between paired single backticks."""
    return [match.span() for match in _INLINE_CODE_RE.finditer(line)]
def _section_has_escaped_newline(body) -> bool:
    """Whether one section body carries a literal backslash-n outside code
    and outside a Windows path."""
    lines, fence = str(body or '').split('\n'), None
    for line in lines:
        run = _fence_run(line)
        if fence is not None:
            if run is not None and run[0] == fence[0] and len(run) >= len(fence) and not line.strip()[len(run):].strip():
                fence = None
            continue
        if run is not None:
            fence = run
            continue
        protected = _windows_path_spans(line) + _inline_code_spans(line)
        for match in ESCAPED_NEWLINE_RE.finditer(line):
            if not any(start <= match.start() < end for start, end in protected):
                return True
    return False
def format_policy_defects(text, data, sections):
    del data
    defects = [f"frontmatter repeats '{key}'" for key in _duplicate_frontmatter_keys(text)]
    for key, body in sections.items():
        if _section_has_escaped_newline(body):
            name = CUT_SECTIONS_BY_KEY.get(key) or EXECUTOR_SECTIONS_BY_KEY.get(key) or key
            defects.append(
                f"'## {name}' carries a literal backslash-n: an escaped newline "
                "that never reached stored bytes as one (write a real line "
                "break, or fence the code that needs the literal)"
            )
    return defects
def _read_utf8(path, subject: str='ticket', encoding: str='utf-8'):
    """One file's text as ``(text, None)``, or ``(None, {"error": ...})``."""
    reader = path if hasattr(path, 'read_text') else Path(path)
    try:
        return (reader.read_text(encoding=encoding), None)
    except (OSError, UnicodeDecodeError) as error:
        return (None, {'error': f'unreadable {subject}: {error}'})
def ticket_defects(text: str) -> list:
    """Every way ``text`` is not a ticket per contracts/work-item.md."""
    data = _parse_frontmatter(text)
    if not data:
        return ["no frontmatter: a ticket opens with a '---' block (contracts/work-item.md)"]
    defects = []
    required = REQUIRED_TICKET_KEYS + REQUIRED_LIFECYCLE_KEYS
    # `executor` is required of every ticket a command may dispatch, and a
    # frame is the one kind no command may. Exempted here rather than dropped
    # from the declared shape, because every other ticket still owes it.
    if is_frame(data):
        required = tuple(key for key in required if key != 'executor')
    for key in ('id', 'run', 'status', 'executor', 'depends_on', 'bound'):
        if key in required and key not in data:
            defects.append(f"frontmatter has no '{key}'")
    for key in sorted(set(data) - ALLOWED_TICKET_KEYS):
        defects.append(f"unknown ticket frontmatter field '{key}'")
    status = data.get('status')
    if isinstance(status, str) and status.strip():
        normalized = dequote(status)
        if normalized not in VALID_STATUSES:
            defects.append(f"status '{normalized}' is not one of {sorted(VALID_STATUSES)}")
    executor = _executor_of(data)
    if executor:
        if not executor.startswith(SCRIPT_EXECUTOR_PREFIX) and not executor_registered(executor):
            defects.append(executor_refusal(executor))
        elif EXECUTOR_REGISTRY.get(executor, {}).get("requires_standard") and not data.get(STANDARDS_FIELD):
            defects.append(
                f"executor-standard-required: {executor} reads a resolved standard and "
                "requires one stamped"
            )
    parsed_sections = _sections(text)
    sections = {name.strip().lower(): body for name, body in parsed_sections.items()}
    for name in REQUIRED_SECTIONS:
        if name.lower() not in sections:
            defects.append(f"no '## {name}' section")
    allowed_sections = {name.lower() for name in SECTION_ORDER}
    for name in sections:
        if name not in allowed_sections:
            defects.append(f"unknown ticket section '## {name}'")
    if not sections.get('goal', '').strip():
        defects.append("Goal must state a non-empty observable end result")
    if not sections.get('context', '').strip():
        defects.append("Context must be present; use [] when no exceptional facts apply")
    defects.extend(format_policy_defects(text, data, sections))
    defects.extend(frame_defects(data.get('frame'), data.get('executor'), data.get(STANDARDS_FIELD)))
    defects.extend(done_defects(data.get('done')))
    return defects
def lease_of(data):
    """(owner, opened_at) of the ticket's current dispatch attempt."""
    raw = str(data.get('dispatch_v1') or '').strip()
    if not raw:
        return '', ''
    try:
        state = json.loads(raw)
    except ValueError:
        return '', ''
    attempts = state.get('attempts') if isinstance(state, dict) else None
    if not isinstance(attempts, list) or not attempts:
        return '', ''
    attempt = next(
        (item for item in reversed(attempts)
         if isinstance(item, dict) and item.get('state') == 'live'),
        attempts[-1],
    )
    if not isinstance(attempt, dict):
        return '', ''
    return str(attempt.get('owner') or ''), str(attempt.get('opened_at') or '')
def round_of(ticket_id):
    """`(parent_id, number)` when an id names one bounded round, else None."""
    match = ROUND_ID_RE.fullmatch(str(ticket_id or ''))
    if match is None:
        return None
    return match.group('parent'), int(match.group('number'))
def round_parent(ticket_id):
    """The ticket whose post-seal round machinery minted this id, or None."""
    text = str(ticket_id or '')
    if text.endswith(DONE_TICKET_SUFFIX):
        text = text[:-len(DONE_TICKET_SUFFIX)]
    parsed = round_of(text)
    return None if parsed is None else parsed[0]
def mint_ordinal(ticket_id, parent=None):
    """The ordinal an auto-minted callable id carries under ``parent``, or
    None."""
    text = str(ticket_id or '')
    if not str(parent or ''):
        match = MINT_ROOT_ID_RE.fullmatch(text)
        return None if match is None else int(match.group('number'))
    match = MINT_CHILD_ID_RE.fullmatch(text)
    if match is None or match.group('parent') != str(parent):
        return None
    return int(match.group('number'))
def next_mint_id(parent, ticket_ids) -> str:
    """The next unused auto id under ``parent``, or the next root `B<n>`."""
    ordinals = [
        number for number in (
            mint_ordinal(ticket_id, parent) for ticket_id in ticket_ids or ()
        ) if number is not None
    ]
    number = max(ordinals, default=0) + 1
    return f'{parent}.{number}' if str(parent or '') else f'B{number}'
def declared_parent(data) -> str:
    """The ticket this one was minted under at runtime, or ''."""
    return dequote(data.get('parent'))
def is_frame(data) -> bool:
    """Whether this ticket is one call-stack frame rather than dispatched work."""
    return dequote(data.get('frame')) == FRAME_MARKER
def frame_defects(value, executor, standard) -> list:
    """Shape defects for one frontmatter ``frame`` marker, or []."""
    raw = dequote(value)
    if not raw:
        return []
    if raw != FRAME_MARKER:
        return [
            f'frame is the marker `{FRAME_MARKER}` and takes no other value: '
            f"got '{raw}'"
        ]
    return [
        f'a frame binds no {field}: {reason}'
        for field, present, reason in (
            ('executor', dequote(executor),
             'the orchestrator session drives it, and nothing dispatches it'),
            ('standard', ', '.join(standard or ()),
             'a frame is a journal, not standard-governed work'),
        ) if present
    ]
# The one line a driver writes into a frame's journal to close over unjudged
# work. One prefix, owned here beside the id grammar, because the close reads
# it and the contract names it and two spellings would let a stated reason go
# unread.
UNJUDGED_PREFIX = 'unjudged:'
def unjudged_reason(journal) -> str:
    """The stated reason a frame's journal closes over unjudged work, or ''."""
    for line in str(journal or '').splitlines():
        text = line.strip()
        if text.startswith(UNJUDGED_PREFIX):
            reason = text[len(UNJUDGED_PREFIX):].strip()
            if reason:
                return reason
    return ''
def parse_done(data):
    """The parsed frontmatter ``done`` predicate of one ticket, or None."""
    raw = str(data.get('done') or '').strip()
    if not raw:
        return None
    try:
        done = json.loads(raw)
    except ValueError:
        return None
    return done if isinstance(done, dict) else None
def done_binding_defects(done, subject: str) -> list:
    """Shape defects for one ``{form, value}`` done binding, or []."""
    if not isinstance(done, dict):
        return [f'{subject} must be one JSON object']
    defects = []
    for key in sorted(set(done) - set(DONE_BINDING_FIELDS)):
        defects.append(f"{subject} carries unknown field '{key}'")
    for key in sorted(DONE_BINDING_REQUIRED):
        if key not in done:
            defects.append(f"{subject} is missing required field '{key}'")
    form = str(done.get('form') or '')
    if 'form' in done and form not in DONE_BINDING_VALUES['form']:
        defects.append(
            f'{subject} form must be one of '
            + ', '.join(DONE_BINDING_VALUES['form']) + f": got '{form}'"
        )
    if 'value' in done and not str(done.get('value') or '').strip():
        defects.append(f'{subject} value is empty')
    return defects
def done_defects(value) -> list:
    """Shape defects for one frontmatter ``done`` value, or []."""
    raw = str(value or '').strip()
    if not raw:
        return []
    try:
        done = json.loads(raw)
    except ValueError:
        return ['done is not canonical JSON']
    return done_binding_defects(done, 'done')
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
    """Remove every repeated flag value in order, tolerating a trailing flag."""
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
    return dequote(item.get('executor'))
