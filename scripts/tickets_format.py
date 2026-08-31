"""Ticket format support."""
from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import datetime, timezone
if __package__:
    from .tickets_registry import (
        CALLABLE_EXECUTORS, EXECUTOR_REGISTRY, REVIEW_KINDS,
        executor_refusal, executor_registered,
    )
else:
    from tickets_registry import (
        CALLABLE_EXECUTORS, EXECUTOR_REGISTRY, REVIEW_KINDS,
        executor_refusal, executor_registered,
    )
if __package__:
    from .tickets_adapters import adapter_id
    from .tickets_shapes import (
        DONE_BINDING_FIELDS, DONE_BINDING_REQUIRED, DONE_BINDING_VALUES,
        LOOP_STUB_FIELDS, LOOP_STUB_REQUIRED,
        TICKET_FRONTMATTER_FIELDS, TICKET_FRONTMATTER_REQUIRED,
        TICKET_FRONTMATTER_VALUES,
    )
    from .tickets_markdown import (
        CUT_SECTIONS, CUT_SECTIONS_BY_KEY, EXECUTOR_SECTIONS,
        EXECUTOR_SECTIONS_BY_KEY, OPTIONAL_SECTIONS, REPORT_SECTION,
        REQUIRED_SECTIONS,
        SECTION_ORDER, SECTION_RANK, TicketFormatError, _body_block,
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
        LOOP_STUB_FIELDS, LOOP_STUB_REQUIRED,
        TICKET_FRONTMATTER_FIELDS, TICKET_FRONTMATTER_REQUIRED,
        TICKET_FRONTMATTER_VALUES,
    )
    from tickets_markdown import (
        CUT_SECTIONS, CUT_SECTIONS_BY_KEY, EXECUTOR_SECTIONS,
        EXECUTOR_SECTIONS_BY_KEY, OPTIONAL_SECTIONS, REPORT_SECTION,
        REQUIRED_SECTIONS,
        SECTION_ORDER, SECTION_RANK, TicketFormatError, _body_block,
        _duplicate_frontmatter_keys, _fence_run, _frontmatter_end,
        _frontmatter_line, _heading_lines, _parse_frontmatter,
        _remove_frontmatter_field, _unquote, _scan_sections, _section_body,
        _sections, _set_frontmatter_field, _write_section, dequote,
        quote_filed_body, unquote_filed_body,
    )
# The bound grammar is `tickets_bound`'s, read here so every holder
# gets the one spelling.
# Reached by name in the sibling branch: the import census is pinned.
if __package__:
    from .tickets_bound import DEFAULT_BOUND_MINUTES, _parse_bound_minutes
else:
    _bound_module = __import__('tickets_bound')
    DEFAULT_BOUND_MINUTES, _parse_bound_minutes = (_bound_module.DEFAULT_BOUND_MINUTES, _bound_module._parse_bound_minutes)
VALID_STATUSES = set(TICKET_FRONTMATTER_VALUES['status'])
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
# drawn from rather than in one of its two readers: `tickets_admission`
# grades a sealed assignment against it and `tickets_readiness` answers the
# reader's promotion question with it, and the two disagreed -- readiness
# went on requiring `complete` after admission stopped.
RESULT_BEARING_STATES = (DELIVERED_STATE, 'limited')
PACK_NAME_PREFIX = 'orch-'
PACK_NAME_SUFFIX = '-pack'
ROOT_EXECUTOR = 'orch-slice'
CHECKED_BY_KEY = 'checked_by'
GATE_ID_MARKER = '.gate.'
GATE_CRITIQUE_MARKER = '.gate.critique.'
CHECKER_STAGE_SUFFIX = '.check'
TEMPLATE_FILE = 'template.md'
PLACEHOLDER_RE = re.compile('\\{\\{\\s*([^{}]*?)\\s*\\}\\}')
ESCAPED_NEWLINE_RE = re.compile('\\\\n')
# A literal backslash then the letter 'n' -- the two-character escape a
# shell or a hand can type in place of the one byte it was meant to stand
# for. A real newline never matches this: it is one byte, not two.
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
    """Character spans in ``line`` that read as a Windows path, not prose.

    A drive letter or a UNC's doubled backslash roots a path outright, so
    even its first segment counts. Unrooted needs two real (2+ character)
    segments, so a doubled escape (``\\n\\n``) is never misread as the
    two one-letter segments of a path nothing names -- the exact shape a
    collapsed multi-bullet ``--context`` value takes.
    """
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
    """Character spans in ``line`` between paired single backticks.

    A fenced block already reads as code, never prose; this is the same
    exemption for the inline case -- the repository's own idiom for naming
    a newline in running text, as in `newline=` or "rstrip of a newline".
    An unpaired backtick protects nothing: only a closed span counts.
    """
    return [match.span() for match in _INLINE_CODE_RE.finditer(line)]
def _section_has_escaped_newline(body) -> bool:
    """Whether one section body carries a literal backslash-n outside code
    and outside a Windows path -- fenced lines are read as code, never
    prose, via the same ``_fence_run`` tracking `_scan_sections` uses to
    find the next heading. An inline single-backtick span is the same
    exemption for one unfenced line, the idiom prose uses to name the
    escape without writing it.
    """
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
    if executor and not PLACEHOLDER_RE.search(executor):
        if not executor.startswith(SCRIPT_EXECUTOR_PREFIX) and not executor_registered(executor):
            defects.append(executor_refusal(executor))
        elif EXECUTOR_REGISTRY.get(executor, {}).get("requires_pack") and not str(data.get("pack") or "").strip():
            defects.append(
                f"executor-pack-required: {executor} consumes resolved pack cells and "
                "requires a stamped pack"
            )
    review_kind = dequote(data.get('review_kind'))
    if review_kind and review_kind not in REVIEW_KINDS:
        defects.append(
            f"review_kind '{review_kind}' is not one of {list(REVIEW_KINDS)}"
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
    defects.extend(loop_defects(data.get('loop'), _executor_of(data)))
    defects.extend(done_defects(data.get('done')))
    return defects
def lease_of(data):
    """(owner, opened_at) of the ticket's current dispatch attempt.

    The dispatch record owns the lease (contracts/dispatch.md); the ticket
    carries no claimed_by/claimed_at projection beside it. This is the
    light display/ordering read: the live attempt if one exists, else the
    latest attempt, else ('', ''). Lease-law decisions read the validated
    window in tickets_dispatch_schema instead.
    """
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
def parse_loop(data):
    """The parsed frontmatter ``loop`` object of one ticket, or None."""
    raw = str(data.get('loop') or '').strip()
    if not raw:
        return None
    try:
        loop = json.loads(raw)
    except ValueError:
        return None
    return loop if isinstance(loop, dict) else None
def parse_done(data):
    """The parsed frontmatter ``done`` predicate of one ticket, or None.

    The top-level home of the same binding a loop stub carries inside its
    ``loop`` object. One grammar, read here for both.
    """
    raw = str(data.get('done') or '').strip()
    if not raw:
        return None
    try:
        done = json.loads(raw)
    except ValueError:
        return None
    return done if isinstance(done, dict) else None
def done_binding_defects(done, subject: str) -> list:
    """Shape defects for one ``{form, value}`` done binding, or [].

    contracts/work-item.md's done_binding shape, and the sole owner of that
    grammar. It has two homes -- a ticket's own ``done`` predicate, which
    `tickets.py land` evaluates, and the ``done`` a loop stub carries for
    its iterations -- and one owner: a second copy is how the two spellings
    of a closed form drift.
    """
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
def loop_defects(value, executor) -> list:
    """Shape defects for one frontmatter ``loop`` value, or [].

    contracts/work-item.md's loop_stub shape: a loop stub's executor is the
    iteration body's verb, and ``done`` binds the external done-check
    through the one grammar ``done_binding_defects`` owns.
    """
    raw = str(value or '').strip()
    if not raw:
        return []
    try:
        loop = json.loads(raw)
    except ValueError:
        return ['loop is not canonical JSON']
    if not isinstance(loop, dict):
        return ['loop must be one JSON object']
    defects = []
    for key in sorted(set(loop) - set(LOOP_STUB_FIELDS)):
        defects.append(f"loop carries unknown field '{key}'")
    for key in sorted(LOOP_STUB_REQUIRED):
        if key not in loop:
            defects.append(f"loop is missing required field '{key}'")
    if 'done' in loop:
        defects.extend(done_binding_defects(loop.get('done'), 'loop done'))
    verb = dequote(executor)
    if not defects and not executor_registered(verb):
        defects.append(
            f"loop stub executor '{verb}' is not a registered callable; "
            "the stub's executor is the iteration body's verb"
        )
    return defects
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
def is_review_stage_id(ticket_id) -> bool:
    """Whether an id names a derived review stage rather than executor work.

    The composite gate spells it `<root>.gate.<kind>` and the ordinary
    checker spells it `<target>.check`; both are the protocol's, never an
    author's, and both are read off the id because the id is what a caller
    has before the ticket is loaded. Nine sites open-coded the two
    substrings, and the two that spelled only half of it read a checker
    stage as ordinary work.
    """
    text = str(ticket_id or '')
    return GATE_ID_MARKER in text or text.endswith(CHECKER_STAGE_SUFFIX)
def is_critique_stage_id(ticket_id) -> bool:
    """`is_review_stage_id` narrowed to the stages that file findings.

    A repair and a verification stage are review stages that do not: only a
    critique lens and the ordinary checker produce the findings array the
    schema grades and the join adjudicates.
    """
    text = str(ticket_id or '')
    return GATE_CRITIQUE_MARKER in text or text.endswith(CHECKER_STAGE_SUFFIX)
