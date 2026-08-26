"""Ticket format support."""
from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import datetime, timezone
if __package__:
    from .tickets_markdown import (
        CUT_SECTIONS, CUT_SECTIONS_BY_KEY, EXECUTOR_SECTIONS,
        EXECUTOR_SECTIONS_BY_KEY, OPTIONAL_SECTIONS, REQUIRED_SECTIONS,
        FILEABLE_EXECUTOR_SECTIONS, LEGACY_EXECUTOR_SECTIONS,
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
    from tickets_markdown import (
        CUT_SECTIONS, CUT_SECTIONS_BY_KEY, EXECUTOR_SECTIONS,
        EXECUTOR_SECTIONS_BY_KEY, OPTIONAL_SECTIONS, REQUIRED_SECTIONS,
        FILEABLE_EXECUTOR_SECTIONS, LEGACY_EXECUTOR_SECTIONS,
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
SUCCESSOR_CONTEXT_PREFIXES = ('- state:', '- watch:')
# The instruction ceiling is `tickets_ceiling`'s: one counter, so the lint
# twin and the issue refusal cannot drift apart. Re-exported here because
# this module is where the family and the `tickets` facade already read it.
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
CHECKED_BY_KEY = 'checked_by'
GATE_ID_MARKER = '.gate.'
GATE_EXECUTORS = {'critique': 'orch-critique', 'repair': 'orch-repair', 'verify': 'orch-verify'}
GRANTED_SCOPE_KEY = 'granted_scope'
TEMPLATE_FILE = 'template.md'
PLACEHOLDER_RE = re.compile('\\{\\{\\s*([^{}]*?)\\s*\\}\\}')
MUTATION_OPERATIONS = ('create', 'change', 'delete', 'write')
MUTATION_GLOB_RE = re.compile(r'[*?\[\]]')
RETURN_SIZE_PREFIX = 'return-size: '
RETURN_SIZE_KEYS = ('counter', 'maximum', 'minimum-complete', 'target')
RETURN_SIZE_COUNTERS = ('words-v1', 'lines-v1')
NUMERIC_RETURN_SIZE_RE = re.compile(r'\b\d+\s+(?:words?|lines?)\b', re.IGNORECASE)
ADAPTER_BY_PACK = {
    'orch-code-pack': 'git',
    'orch-content-pack': 'document-tree',
    'orch-design-pack': 'git-plus-render',
    'orch-research-pack': 'evidence-store',
}
PLAIN_ADAPTER = 'plain-artifact'
PACK_EXECUTOR_BINDINGS = {
    'orch-code-pack': frozenset({'orch-tdd'}),
    'orch-content-pack': frozenset({'orch-draft', 'orch-edit'}),
    'orch-design-pack': frozenset({'orch-render'}),
    'orch-research-pack': frozenset({'orch-investigate', 'orch-synthesize'}),
}
def adapter_id(pack) -> str: return ADAPTER_BY_PACK.get(str(pack or '').strip(), PLAIN_ADAPTER)
def executor_bindings(pack) -> set: return set(PACK_EXECUTOR_BINDINGS.get(str(pack or '').strip(), ()))
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
def parse_mutations(data):
    declared = data.get('mutations') if isinstance(data, dict) else data
    if declared is None:
        return ([], [])
    if not isinstance(declared, list):
        return ([], ["frontmatter 'mutations' must be a list of <operation>:<path> entries"])
    parsed, defects, seen = [], [], set()
    for position, raw in enumerate(declared, start=1):
        entry = str(raw).strip()
        operation, separator, path = entry.partition(':')
        if not separator or operation not in MUTATION_OPERATIONS:
            defects.append(f"mutation {position} '{entry}' is not <operation>:<path> with operation one of {list(MUTATION_OPERATIONS)}")
            continue
        defect = None
        if not path or path.startswith('/') or ':' in path or '\\' in path or MUTATION_GLOB_RE.search(path):
            defect = 'must be a repository-relative POSIX path with no glob'
        elif any(part in ('', '.', '..') for part in path.rstrip('/').split('/')):
            defect = "contains an empty, '.' or '..' segment"
        elif operation == 'write' and not path.endswith('/'):
            defect = "uses 'write' without a trailing-slash prefix"
        elif operation != 'write' and path.endswith('/'):
            defect = f"uses '{operation}' on a prefix; file operations require a file path"
        if defect:
            defects.append(f"mutation {position} '{entry}' {defect}")
        elif (operation, path) not in seen:
            parsed.append({'operation': operation, 'path': path})
            seen.add((operation, path))
    return (parsed, defects)
def parse_return_size(section_text):
    candidates = [line for line in section_text.splitlines() if 'return-size:' in line]
    if not candidates:
        return (None, [])
    if len(candidates) != 1:
        return (None, ['Return fields contains more than one return-size clause'])
    line = candidates[0]
    if not line.startswith(RETURN_SIZE_PREFIX):
        return (None, [f"return-size clause must be one exact line beginning '{RETURN_SIZE_PREFIX}'"])
    encoded = line[len(RETURN_SIZE_PREFIX):]
    try:
        clause = parse_canonical_json(encoded)
    except (TypeError, ValueError, json.JSONDecodeError):
        return (None, ['return-size clause is not a canonical JSON object'])
    if not isinstance(clause, dict) or tuple(clause) != RETURN_SIZE_KEYS:
        return (None, [f'return-size keys must be exactly {list(RETURN_SIZE_KEYS)} in canonical order'])
    try:
        canonical = canonical_json(clause)
    except (TypeError, ValueError):
        canonical = ''
    if canonical != encoded:
        return (None, ['return-size clause JSON is not canonical: recursively sorted keys and no insignificant whitespace required'])
    defects, maximum, minimum = [], clause.get('maximum'), clause.get('minimum-complete')
    if clause.get('counter') not in RETURN_SIZE_COUNTERS:
        defects.append(f"return-size counter must be one of {list(RETURN_SIZE_COUNTERS)}")
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum <= 0:
        defects.append('return-size maximum must be a positive integer')
    if not isinstance(minimum, str) or not minimum.strip():
        defects.append('return-size minimum-complete must name one fixed input')
    if clause.get('target') != 'result':
        defects.append("return-size target must be 'result'")
    return (clause if not defects else None, defects)
def parse_result_identity(section_text):
    candidates = [line for line in section_text.splitlines() if line.startswith('result:')]
    if len(candidates) != 1:
        return (None, [f'bounded Result must contain exactly one result identity line; found {len(candidates)}'])
    line = candidates[0]
    if not line.startswith('result: '):
        return (None, ["result identity line must begin exactly 'result: '"])
    encoded = line[len('result: '):]
    try:
        identity = parse_canonical_json(encoded)
    except (TypeError, ValueError, json.JSONDecodeError):
        return (None, ['result identity is not a canonical JSON object'])
    if not isinstance(identity, dict) or not isinstance(identity.get('kind'), str):
        return (None, ["result identity must be an object with string 'kind'"])
    try:
        canonical = canonical_json(identity)
    except (TypeError, ValueError):
        canonical = ''
    if canonical != encoded:
        return (None, ['result identity JSON is not canonical: recursively sorted keys and no insignificant whitespace required'])
    return (identity, [])
def count_return_text(text, counter):
    if counter == 'words-v1':
        return len(text.split())
    if counter == 'lines-v1':
        return len(text.splitlines())
    raise ValueError(f"unknown return-size counter '{counter}'")
def successor_context_defects(body: str) -> list:
    """Return every violation of the optional successor Context grammar."""
    lines = body.splitlines()
    defects = []
    if not 1 <= len(lines) <= 5:
        defects.append('Context must contain one to five top-level bullets')
    for number, line in enumerate(lines, start=1):
        prefix = next((item for item in SUCCESSOR_CONTEXT_PREFIXES if line.startswith(item)), None)
        if prefix is None or not line[len(prefix):].strip():
            defects.append(
                f"Context line {number} must begin exactly '- state:' or '- watch:' and have non-empty content"
            )
    return defects
def successor_section_defects(sections: dict, allow_legacy_carry: bool=False) -> list:
    named = {str(name).lower(): body for name, body in sections.items()}; suffix = ' beside ## Context' if 'context' in named else ''
    defects = ([f'canonical new work cannot contain legacy ## Carry{suffix}']
               if 'carry' in named and not allow_legacy_carry else [])
    if 'context' in named: defects.extend(successor_context_defects(named['context']))
    return defects
def format_policy_defects(text, data, sections):
    defects = []
    for key in _duplicate_frontmatter_keys(text):
        defects.append(f"frontmatter repeats '{key}'")
    return_fields = sections.get('return fields')
    if return_fields is not None:
        clause, parsed_defects = parse_return_size(return_fields)
        defects.extend(parsed_defects)
        if clause is not None:
            if not re.search(r'\bresult\b', return_fields.splitlines()[0].lower()):
                defects.append("bounded Return fields must name 'result'")
            rest = '\n'.join(line for line in return_fields.splitlines() if not line.startswith(RETURN_SIZE_PREFIX))
            parts = [str(data.get('bound') or ''), *_scope_entries(data.get('excluded_actions')), sections.get('objective', ''), sections.get('completion test', ''), rest]
            if any(NUMERIC_RETURN_SIZE_RE.search(part) for part in parts):
                defects.append('bounded ticket carries another numeric word/line constraint outside return-size')
    defects.extend(parse_mutations(data)[1])
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
    if stub:
        defects.extend(successor_section_defects(sections))
    completion = sections.get('completion test')
    if completion is not None:
        defects.extend(criterion_defects(completion))
    defects.extend(format_policy_defects(text, data, sections))
    defects.extend(sequence_defects(data.get('sequence'), _executor_of(data)))
    return defects
# A test invocation says which node it grades, or it grades whatever it finds.
# `discover` names no node by construction; `-k` names one whatever it is
# pointed at; `::` opens the node half of a pytest target. A filter narrows
# only if some node id fails it, and every test node here is a method named
# `test_...`: `-k test` is the whole suite with a flag on, so the token's
# presence is no evidence on its own.
TEST_RUNNERS = ("unittest", "pytest")
DISCOVER = "discover"
NODE_FILTER = "-k"
NODE_SEP = "::"
FILTER_MATCHES_ALL = "test_"
REQUIRED_FIELDS_CELL = 'required_spec_fields'
FIELD_GLOSS_RE = re.compile('\\s+[—-]{1,2}\\s+')
FIELD_WORD_RE = re.compile('[a-z]{4,}')
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
def _whole_target(target, tree):
    """Does this target name a whole module or directory, not a node inside one?
    Decided against the tree, because only the tree knows where the module
    stops: ``tests.test_cutcheck`` is a file and its ``.CleanSetTest`` is a
    class inside that file, and no reading of the two strings tells them
    apart. A unittest target spells the way down with dots and a pytest target
    with slashes; both are one question about where the path stops resolving.
    """
    if NODE_SEP in target:
        return False
    here = tree / (target if "/" in target else target.replace(".", "/"))
    return here.is_dir() or here.with_suffix(".py").is_file()
def _filter_narrows(argv):
    """Does this command's node filter actually exclude any node?
    The token's presence was the whole test once, and that read `-k test` --
    which matches every method in the suite -- as a narrowed oracle. The
    pattern is read instead: anything `test_` starts with matches all of them
    and narrows nothing, and everything else is taken at its word, because
    which nodes a pattern selects is the runner's question and not this one's.
    """
    if NODE_FILTER not in argv:
        return False
    index = argv.index(NODE_FILTER)
    pattern = argv[index + 1].strip("\"'") if index + 1 < len(argv) else ""
    return not FILTER_MATCHES_ALL.startswith(pattern)
def _whole_suite(command, tree):
    """Is this a test invocation naming no node id?
    A whole-module or whole-suite invocation is a bare head with more typing:
    it runs the identical tests under every item it is stated under, so it
    discriminates none of them, and the honest report of it is the gap.
    Reported rather than run, which is what makes the class worth having: this
    repository's own mandated ``discover`` outgrows any command timeout in the
    cleanest store there is, so executing it returned ``unrunnable-oracle``.
    A target resolving to no module at all is some flag's value rather than a
    thing to grade, and one such token is enough to withhold the finding: this
    convicts what it can read whole, and stays quiet over what it cannot. A
    runner carrying flags and no target at all is the widest spelling there is
    -- ``pytest -q``, or the bare ``python3 -m unittest`` documented as
    equivalent to ``discover``. Naming nothing is not naming something
    unreadable, so the finding is withheld over a quoted target, which names a
    node this cannot parse, and made over an empty one, which names none.
    """
    argv = command.split()
    runner = next((i for i, token in enumerate(argv) if token in TEST_RUNNERS), None)
    if runner is None or _filter_narrows(argv):
        return False
    rest = argv[runner + 1:]
    if DISCOVER in rest:
        return True
    if NODE_FILTER in rest:
        # Reaching here means the pattern matched every node, so it is a flag's
        # value and not a target. Left in, it resolves to no module and
        # withholds the finding over the very filter that earned it.
        at = rest.index(NODE_FILTER)
        rest = rest[:at] + rest[at + 2:]
    targets = [token for token in rest if token[:1] not in ("-", '"', "'")]
    if not targets:
        return not any(token[:1] in ('"', "'") for token in rest)
    return all(_whole_target(token, tree) for token in targets)
