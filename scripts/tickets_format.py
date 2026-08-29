"""Ticket format support."""
from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import datetime, timezone
if __package__:
    from .tickets_adapters import adapter_id
    from .tickets_markdown import (
        CUT_SECTIONS, CUT_SECTIONS_BY_KEY, EXECUTOR_SECTIONS,
        EXECUTOR_SECTIONS_BY_KEY, OPTIONAL_SECTIONS, REQUIRED_SECTIONS,
        SECTION_ORDER, SECTION_RANK, TicketFormatError, _body_block,
        _duplicate_frontmatter_keys, _fence_run, _frontmatter_end,
        _frontmatter_line, _heading_lines, _parse_frontmatter,
        _remove_frontmatter_field, _unquote, _scan_sections, _section_body,
        _sections, _set_frontmatter_field, _write_section,
    )
    from .tickets_ceiling import (
        INSTRUCTION_BUDGET, INSTRUCTION_SECTIONS, LINK_TARGET_RE, ceiling_sentence,
        instruction_breakdown, instruction_words,
    )
else:
    from tickets_adapters import adapter_id
    from tickets_markdown import (
        CUT_SECTIONS, CUT_SECTIONS_BY_KEY, EXECUTOR_SECTIONS,
        EXECUTOR_SECTIONS_BY_KEY, OPTIONAL_SECTIONS, REQUIRED_SECTIONS,
        SECTION_ORDER, SECTION_RANK, TicketFormatError, _body_block,
        _duplicate_frontmatter_keys, _fence_run, _frontmatter_end,
        _frontmatter_line, _heading_lines, _parse_frontmatter,
        _remove_frontmatter_field, _unquote, _scan_sections, _section_body,
        _sections, _set_frontmatter_field, _write_section,
    )
    from tickets_ceiling import (
        INSTRUCTION_BUDGET, INSTRUCTION_SECTIONS, LINK_TARGET_RE, ceiling_sentence,
        instruction_breakdown, instruction_words,
    )
# The bound grammar is `tickets_bound`'s and the chain grammar is
# `tickets_sequence`'s, read here so every holder gets the one spelling.
# Reached by name in the sibling branch: the import census is pinned.
if __package__:
    from .tickets_bound import DEFAULT_BOUND_MINUTES, _parse_bound_minutes
    from .tickets_sequence import sequence_defects
else:
    _bound_module = __import__('tickets_bound')
    DEFAULT_BOUND_MINUTES, _parse_bound_minutes = (_bound_module.DEFAULT_BOUND_MINUTES, _bound_module._parse_bound_minutes)
    from tickets_sequence import sequence_defects
VALID_STATUSES = {'pending', 'ready', 'claimed', 'suspended', 'complete', 'blocked', 'stalled', 'failed', 'limited'}
LOOP_EXECUTOR = 'orch-loop'
DISPATCHING_EXECUTORS = ('orch-frontier', LOOP_EXECUTOR)
SCRIPT_EXECUTOR_PREFIX = 'script:'
REQUIRED_TICKET_KEYS = ('id', 'executor', 'depends_on', 'bound')
REQUIRED_LIFECYCLE_KEYS = ('run', 'status')
ALLOWED_TICKET_KEYS = frozenset({
    'id', 'run', 'status', 'admission', 'executor', 'sequence', 'pack',
    'profile', 'independence', 'depends_on', 'isolation', 'bound',
    'claimed_by', 'claimed_at', 'checked_by', 'root_generation',
    'cut_generation', 'assignment_seal', 'workspace_branch',
    'workspace_baseline', 'workspace_path', 'dispatch_v1',
    'review_order', 'review_v1', 'review_stage',
})
DURATION_RE = re.compile('^(\\d+)(m|h)$')
RESULT_TOKEN_SPLIT_RE = re.compile('[\\s`\\"\'<>()\\[\\]{},;|]+')
RESULT_TOKEN_STRIP = '.:!?*_-'
SUCCESSOR_CONTEXT_PREFIXES = ('- state:', '- watch:')
# The instruction ceiling is `tickets_ceiling`'s: one counter, so the lint
# twin and the issue refusal cannot drift apart. Re-exported here because
# this module is where the family and the `tickets` facade already read it.
REQUIRED_ISOLATION = 'required'
TERMINAL_STATES = ('complete', 'blocked', 'stalled', 'limited', 'failed')
PACK_NAME_PREFIX = 'orch-'
PACK_NAME_SUFFIX = '-pack'
ROOT_EXECUTOR = 'orch-decompose'
CHECKED_BY_KEY = 'checked_by'
GATE_ID_MARKER = '.gate.'
GATE_EXECUTORS = {'critique': 'orch-critique', 'repair': 'orch-repair', 'verify': 'orch-verify'}
TEMPLATE_FILE = 'template.md'
PLACEHOLDER_RE = re.compile('\\{\\{\\s*([^{}]*?)\\s*\\}\\}')
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
def format_policy_defects(text, data, sections):
    del data, sections
    return [f"frontmatter repeats '{key}'" for key in _duplicate_frontmatter_keys(text)]
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
        normalized = status.strip().strip('`').strip()
        if normalized not in VALID_STATUSES:
            defects.append(f"status '{normalized}' is not one of {sorted(VALID_STATUSES)}")
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
    defects.extend(sequence_defects(data.get('sequence'), _executor_of(data)))
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
    return str(item.get('executor') or '').strip().strip('`').strip()
