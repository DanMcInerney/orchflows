"""Ticket worklog support."""

from __future__ import annotations
import re
from pathlib import Path
if __package__:
    from .tickets_format import FIELD_GLOSS_RE, FIELD_WORD_RE, PLACEHOLDER_RE, REQUIRED_FIELDS_CELL, REQUIRED_SECTIONS, ROOT_EXECUTOR, SECTION_RANK, TEMPLATE_FILE, TERMINAL_STATES, _executor_of, _parse_frontmatter, _read_utf8, _section_body, _sections, ticket_defects
else:
    from tickets_format import FIELD_GLOSS_RE, FIELD_WORD_RE, PLACEHOLDER_RE, REQUIRED_FIELDS_CELL, REQUIRED_SECTIONS, ROOT_EXECUTOR, SECTION_RANK, TEMPLATE_FILE, TERMINAL_STATES, _executor_of, _parse_frontmatter, _read_utf8, _section_body, _sections, ticket_defects

PACKS_DIR = 'packs'
if __package__:
    from .tickets_store import NO_SINK_ERROR, _load_ticket, _runs_root, _segment_error, _tickets_root
else:
    from tickets_store import NO_SINK_ERROR, _load_ticket, _runs_root, _segment_error, _tickets_root

WORKLOG_NAME = 'worklog.md'
WORKLOG_RENDER_MARKER = '<!-- rendered by tickets.py worklog -->'
WORKLOG_SECTIONS = ('goal', 'iterations', 'failed approaches', 'queued scope', 'terminal')
ITERATION_ID_RE = re.compile('^.+\\.iter\\.\\d+$')
GATE_VERIFY_SUFFIX = '.gate.verify'
WORKLOG_USAGE = 'worklog <run> [--write]'
def _packs_root(directory):
    """The `packs/` beside this template's tree, or None.

    None is the ordinary answer for an installed copy of this script: it
    runs against a target repository that carries no `packs/` at all, and a
    pack it cannot read is not a defect in the stub.
    """
    directory = Path(directory).resolve()
    for parent in (directory, *directory.parents):
        candidate = parent / PACKS_DIR
        if candidate.is_dir():
            return candidate
    return None
def _required_spec_fields(packs_root, pack: str) -> list:
    """The stamped pack's `required_spec_fields` cell, as its field names.

    contracts/pack-signature.md makes the cell a `;`-separated list, and
    contracts/work-item.md makes each entry an entry of the root ticket's
    `## Fixed inputs`.
    """
    text, failure = _read_utf8(packs_root / pack / 'SKILL.md', f'pack {pack}')
    if failure is not None:
        return []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) >= 2 and cells[0] == REQUIRED_FIELDS_CELL:
            return [field.strip() for field in cells[1].split(';') if field.strip()]
    return []
def _spec_field_defect(text: str, directory):
    """The root stub's `## Fixed inputs` against its pack's required fields.

    contracts/work-item.md: "The stamped pack's `required_spec_fields` are
    entries of that `## Fixed inputs`", and `orch-decompose`'s Require
    rejects a root that lacks them, naming what is missing. That refusal
    fires inside the decomposer — after dispatch, against a ticket already
    written and an agent already spending. `packet` grades shape and hands
    these through, so the same refusal is applied here, where the stub is
    admitted.

    A stub engaging with none of the fields is the reported case: the pack
    names each field in its own words and a stub answers in the template's,
    so anything finer would grade phrasing rather than whether the spec was
    supplied at all.
    """
    data = _parse_frontmatter(text)
    if str(data.get('executor') or '').strip().strip('`') != ROOT_EXECUTOR:
        return None
    pack = str(data.get('pack') or '').strip().strip('`')
    if not pack or PLACEHOLDER_RE.search(pack):
        return None
    packs_root = _packs_root(directory)
    if packs_root is None:
        return None
    fields = _required_spec_fields(packs_root, pack)
    if not fields:
        return None
    mentioned = set(FIELD_WORD_RE.findall(_section_body(text, 'Fixed inputs').lower()))
    for field in fields:
        name = FIELD_GLOSS_RE.split(field, 1)[0]
        if mentioned & set(FIELD_WORD_RE.findall(name.lower())):
            return None
    return f"root stub stamps {pack} and its `## Fixed inputs` name none of the fields that pack requires ({'; '.join(fields)}); orch-decompose refuses a root ticket that lacks them (contracts/work-item.md)"
RESULT_READ_RE = re.compile("([A-Za-z0-9][A-Za-z0-9._-]*)'s\\s+`?(?:##\\s*)?Result`?")
NUMBERED_ID_RE = re.compile('^[0-9]')
CLAIM_DASH_RE = re.compile('\\s+(?:—|–|--)\\s+')
CLAIM_END_RE = re.compile(';|\\||:|\\.(?:\\s|$)')
CLAIM_CLAUSE_RE = re.compile('[|;:,()]')
CLAIM_CARRIER_RE = re.compile('\\s+(?:from|in|of|at|by|against|per)\\s*$')
CLAIM_SPLIT = ','
CLAIM_WORD_RE = re.compile('[a-z]{4,}')
CLAIM_STEM = 4
CLAIM_STOPWORDS = frozenset({'also', 'against', 'another', 'before', 'being', 'both', 'does', 'each', 'else', 'every', 'from', 'have', 'here', 'into', 'itself', 'just', 'like', 'more', 'much', 'name', 'named', 'names', 'naming', 'only', 'other', 'over', 'read', 'reads', 'same', 'some', 'such', 'taken', 'takes', 'than', 'that', 'their', 'them', 'then', 'there', 'these', 'they', 'this', 'those', 'under', 'upon', 'very', 'were', 'what', 'when', 'where', 'which', 'while', 'with', 'within', 'without', 'would'})
def _claim_words(text: str) -> set:
    """One phrase's content words, folded to their first four letters."""
    return {word[:CLAIM_STEM] for word in CLAIM_WORD_RE.findall(text.lower()) if word not in CLAIM_STOPWORDS}
def _bullets(section: str) -> list:
    """One section's bullets, each rejoined from its continuation lines."""
    bullets: list = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('- ') or not bullets:
            bullets.append(stripped[2:] if stripped.startswith('- ') else stripped)
        else:
            bullets[-1] += ' ' + stripped
    return bullets
def _result_reads(bullet: str) -> list:
    """``(producer_id, claim)`` for every upstream Result one bullet reads.

    The claim is the reader's own words for what it is taking, on whichever
    side of the reference it put them: after the dash in a fixed input
    (``<id>'s `## Result` -- the verdicts``), before the reference in an
    oracle (``the verdicts from <id>'s Result``).
    """
    reads = []
    for match in RESULT_READ_RE.finditer(bullet):
        after = bullet[match.end():]
        dash = CLAIM_DASH_RE.search(after)
        if dash is not None and RESULT_READ_RE.search(after[:dash.start()]) is None:
            claim = CLAIM_END_RE.split(after[dash.end():])[0]
            following = RESULT_READ_RE.search(claim)
            if following is not None:
                claim = claim[:following.start()]
        else:
            before = CLAIM_CLAUSE_RE.split(bullet[:match.start()])[-1]
            claim = CLAIM_CARRIER_RE.sub(' ', before)
        reads.append((match.group(1), claim))
    return reads
def _upstream(stubs: dict) -> dict:
    """Each stub id to every stub the graph orders before it."""
    upstream = {stub_id: set(deps) for stub_id, (_, deps) in stubs.items()}
    growing = True
    while growing:
        growing = False
        for stub_id, deps in upstream.items():
            grown = set(deps)
            for dependency in deps:
                grown |= upstream.get(dependency, set())
            grown.discard(stub_id)
            if grown != deps:
                upstream[stub_id] = grown
                growing = True
    return upstream
def _closure_defects(stubs: dict) -> list:
    """``(reader_id, message)`` per producer a stub reads and does not get.

    Three refusals, one per way a read misses: a stub that is not here, a
    stub nothing orders first, and a field the producer's `## Return fields`
    does not name. Aggregated per reader-producer pair, so one broken thread
    is one defect naming both ends of it.
    """
    returns = {stub_id: _claim_words(_section_body(text, 'Return fields')) for stub_id, (text, _) in stubs.items()}
    upstream = _upstream(stubs)
    defects = []
    for stub_id in sorted(stubs):
        text, _ = stubs[stub_id]
        unknown: list = []
        unordered: list = []
        missing: dict = {}
        for heading in ('Fixed inputs', 'Completion test'):
            for bullet in _bullets(_section_body(text, heading)):
                for producer, claim in _result_reads(bullet):
                    if producer == stub_id:
                        continue
                    if producer not in stubs:
                        if NUMBERED_ID_RE.match(producer) and producer not in unknown:
                            unknown.append(producer)
                        continue
                    if producer not in upstream[stub_id]:
                        if producer not in unordered:
                            unordered.append(producer)
                        continue
                    for item in claim.split(CLAIM_SPLIT):
                        item = item.strip(' `."\'')
                        words = _claim_words(PLACEHOLDER_RE.sub(' ', item))
                        if not words or words & returns[producer]:
                            continue
                        named = missing.setdefault(producer, [])
                        if item not in named:
                            named.append(item)
        for producer in unknown:
            defects.append((stub_id, f"stub {stub_id} reads {producer}'s `## Result`, and {producer} is not a stub in this template"))
        for producer in unordered:
            defects.append((stub_id, f"stub {stub_id} reads {producer}'s `## Result` without depending on {producer}: nothing orders {producer} first, so {stub_id} is dispatched against a Result not yet written"))
        for producer, named in missing.items():
            defects.append((stub_id, f"stub {stub_id} reads {producer}'s `## Result` for " + '; '.join((f"'{item}'" for item in named)) + f", which {producer}'s `## Return fields` does not name"))
    return defects
def template_defects(directory) -> list:
    """Every way the template at ``directory`` is off contract, as
    ``(path, message)`` pairs.

    The same law ``instantiate`` applies, read before substitution so the
    tree's uninstantiated templates can be graded where they sit: each stub
    against ``ticket_defects(text, stub=True)``, its id against its file
    stem, its list fields against being lists, its sections against the
    contract's order, then the graph — edges, cycle, single terminal — through
    ``_template_order``, and along those edges the producer/consumer closure
    through ``_closure_defects``. A ``{{placeholder}}`` is left alone: it is
    a defect only once instantiation has refused to fill it, and whether the
    manifest declares one is ``tools/validate.py``'s, which owns the
    manifest and reports it there in one spelling.

    Exposed for ``tools/validate.py``, which admits templates into the tree
    and must admit exactly what this script will instantiate. Two spellings
    of one law is how a stub the validator passes is refused at
    instantiation; the paths are returned so the validator can label each
    finding with the file it is about, and the messages are this script's
    own words so both report the same refusal.
    """
    directory = Path(directory)
    manifest = directory / TEMPLATE_FILE
    paths = sorted((path for path in directory.glob('*.md') if path.name != TEMPLATE_FILE))
    if not paths:
        return [(manifest, f'template {directory.name} holds no stub: a template is {TEMPLATE_FILE} plus one or more <id>.md ticket stubs')]
    defects = []
    stubs = {}
    stub_paths = {}
    for path in paths:
        text, failure = _read_utf8(path, f'stub {path.name}', encoding='utf-8-sig')
        if failure is not None:
            defects.append((path, failure['error']))
            continue
        for defect in ticket_defects(text, stub=True):
            defects.append((path, defect))
        data = _parse_frontmatter(text)
        declared_id = str(data.get('id') or '').strip()
        if declared_id and declared_id != path.stem:
            defects.append((path, f"stub {path.name} names id '{declared_id}': a stub's id is its file stem, and `depends_on` names ids"))
        for key in ('depends_on', 'write_scope'):
            if key in data and (not isinstance(data[key], list)):
                defects.append((path, f"'{key}' is not a list; write [] when the stub names none"))
        ordered = [SECTION_RANK[name.strip().lower()] for name in _sections(text) if name.strip().lower() in SECTION_RANK]
        if ordered != sorted(ordered):
            defects.append((path, 'stub body sections are out of contract order; expected ' + ', '.join(REQUIRED_SECTIONS)))
        spec_defect = _spec_field_defect(text, directory)
        if spec_defect is not None:
            defects.append((path, spec_defect))
        dependencies = data.get('depends_on')
        stubs[path.stem] = (text, dependencies if isinstance(dependencies, list) else [])
        stub_paths[path.stem] = path
    _, error = _template_order(stubs)
    if error is not None:
        defects.append((manifest, error['error']))
    else:
        for stub_id, message in _closure_defects(stubs):
            defects.append((stub_paths.get(stub_id, manifest), message))
    return defects
def _template_order(stubs: dict):
    """``(ids_in_topological_order, error)`` for one template's graph.

    Three refusals, in the order that makes each message true: an edge to a
    stub that is not here, then a cycle, then a terminal count that is not
    one. The terminal stub's completion test is the template's done check,
    so two of them is two done checks and none is a graph with no end.
    """
    for stub_id, (_, dependencies) in stubs.items():
        for dependency in dependencies:
            if dependency not in stubs:
                return (None, {'error': f"stub {stub_id} depends on '{dependency}', which is not a stub in this template"})
    remaining = {stub_id: set(deps) for stub_id, (_, deps) in stubs.items()}
    ordered = []
    while remaining:
        ready = sorted((stub_id for stub_id, deps in remaining.items() if not deps))
        if not ready:
            return (None, {'error': f'template is cyclic: no stub in {sorted(remaining)} is free of dependencies'})
        for stub_id in ready:
            del remaining[stub_id]
            ordered.append(stub_id)
        for deps in remaining.values():
            deps.difference_update(ready)
    depended_on = {dependency for _, deps in stubs.values() for dependency in deps}
    terminals = sorted(set(stubs) - depended_on)
    if len(terminals) != 1:
        return (None, {'error': f"template has {len(terminals)} terminal stubs {terminals}; exactly one stub is terminal, and its completion test is the template's done check"})
    return (ordered, None)
def _run_tickets(run: str):
    """``(tickets, error)`` — every ticket in one run, sections included.

    An empty or absent run is an error rather than an empty view: a view
    of nothing reads as a run that did nothing, which is the one thing it
    must not be mistakable for.
    """
    tickets_root = _tickets_root()
    if tickets_root is None:
        return (None, {'error': NO_SINK_ERROR})
    invalid = _segment_error('run id', run)
    if invalid is not None:
        return (None, invalid)
    run_dir = tickets_root / run
    items = []
    for path in sorted(run_dir.glob('*.md')) if run_dir.is_dir() else []:
        loaded = _load_ticket(path)
        text, failure = _read_utf8(path)
        loaded['sections'] = {} if failure is not None else _sections(text)
        items.append(loaded)
    if not items:
        return (None, {'error': f"run '{run}' holds no ticket to render: {run_dir}"})
    return (items, None)
def _run_goal(items: list) -> tuple:
    """``(ticket, kind)`` — the ticket this run's goal is read from.

    One decomposer and a subtree under it is a cut: the root ticket is the
    goal, because the acceptance the run is graded on is the one it wrote.
    A template is not that shape. Its stubs are top-level ids with edges
    between them and several of them may be decomposers, and SPEC-ticket-
    set.md §2 makes the *terminal* stub's completion test the template's
    done check — so reading the alphabetically-first decomposer rendered
    the goal of a stub in the middle of the graph and called it the run's.

    Which shape a run is, from the run: a stub graph is edges among
    top-level ids, or more than one decomposer. Then the terminal, which is
    the one ticket nothing depends on. A directory of unrelated ad-hoc
    tickets falls through to the first id, so it renders a view rather than
    refusing one.
    """
    ordered = sorted(items, key=lambda item: item['id'])
    ids = {item['id'] for item in ordered}
    depended = {dependency for item in ordered for dependency in item.get('depends_on') or []}
    free = [item for item in ordered if item['id'] not in depended]
    roots = [item for item in ordered if _executor_of(item) == ROOT_EXECUTOR]
    top_level = [item for item in ordered if '.' not in item['id']]
    graph = len(roots) > 1 or any((dependency in ids for item in top_level for dependency in item.get('depends_on') or [] if '.' not in str(dependency)))
    if graph and len(free) == 1:
        return (free[0], 'terminal')
    if roots:
        return (roots[0], 'root')
    if len(free) == 1:
        return (free[0], 'terminal')
    return (ordered[0], 'root')
def _quoted(body: str) -> list:
    """One ticket's section body, as lines of a markdown quotation.

    Quoted rather than inlined because a ticket body carries headings of
    its own — every deliverable here is markdown and executors quote
    theirs at length — and a view whose structure a quotation can add to
    is a view no reader can trust the shape of.
    """
    text = str(body or '').strip()
    if not text:
        return ['> (empty)']
    return [f'> {line}' if line.strip() else '>' for line in text.splitlines()]
def _claim_order(items: list) -> list:
    """Tickets in `claimed_at` order, the never-claimed last by id."""
    return sorted(items, key=lambda item: (not str(item.get('claimed_at') or '').strip(), str(item.get('claimed_at') or ''), item['id']))
def _render_worklog(run: str, items: list, root: dict, kind: str='root') -> str:
    """The run view: contracts/worklog.md's fields, answered from tickets."""
    sections = root.get('sections') or {}
    lines = [WORKLOG_RENDER_MARKER, '', f'# run {run}', '', f"Rendered from this run's tickets by `tickets.py worklog {run}`. The ticket directory is the state; this file is a view of it, and an edit made here is lost at the next render.", '', '## goal', '', f'{kind.capitalize()} ticket `{root["id"]}` — executor `{_executor_of(root) or "none"}`.', '', 'Objective:', '', *_quoted(sections.get('Objective')), '', 'Completion test:', '', *_quoted(sections.get('Completion test')), '', '## iterations', '']
    for item in _claim_order(items):
        stamp = str(item.get('claimed_at') or '').strip()
        lines.append(f'- `{item["id"]}` — executor `{_executor_of(item) or "none"}` — status `{item.get("status") or "none"}` — ' + (f'claimed {stamp}' if stamp else 'never claimed'))
        verification = (item.get('sections') or {}).get('Verification')
        if str(verification or '').strip():
            lines.extend(['', *_quoted(verification), ''])
    lines.extend(['', '## failed approaches', ''])
    abandoned = [item for item in _claim_order(items) if item.get('status') in ('failed', 'limited') or ITERATION_ID_RE.match(item['id'])]
    if not abandoned:
        lines.extend(['None recorded.', ''])
    for item in abandoned:
        body = item.get('sections') or {}
        lines.extend([f'### `{item["id"]}` — status `{item.get("status") or "none"}`', '', 'Result:', '', *_quoted(body.get('Result')), '', 'Feedback:', '', *_quoted(body.get('Feedback')), ''])
    lines.extend(['## queued scope', ''])
    queued = [(item, dependency) for item in sorted(items, key=lambda item: item['id']) for dependency in item.get('depends_on') or [] if str(dependency).strip().endswith(GATE_VERIFY_SUFFIX)]
    if not queued:
        lines.append('None recorded.')
    for item, dependency in queued:
        lines.append(f'- `{item["id"]}` — status `{item.get("status") or "none"}` — waits behind `{str(dependency).strip()}`')
    status = str(root.get('status') or '').strip()
    lines.extend(['', '## terminal', ''])
    if status in TERMINAL_STATES:
        lines.extend([f"`{status}` — the {kind} ticket `{root['id']}`'s status. A run exits when its {kind} ticket does.", ''])
    return '\n'.join(lines)
def _write_rendered_worklog(run: str, markdown: str):
    """``(path, error)`` — the view at contracts/worklog.md's own location.

    A worklog this subcommand did not render is refused, not replaced: a
    file written by hand here is the only record of what it holds. The
    free notes a run appends land beside it under RUN_NOTES_NAME, so this
    path has one writer; refusing by marker rather than by mtime or by
    name means the refusal survives a run that predates that split.
    """
    runs_root = _runs_root()
    if runs_root is None:
        return (None, {'error': NO_SINK_ERROR})
    path = runs_root / run / WORKLOG_NAME
    if path.exists():
        existing, failure = _read_utf8(path, f'worklog {path}')
        if failure is not None:
            return (None, failure)
        if not existing.lstrip('\ufeff').startswith(WORKLOG_RENDER_MARKER):
            return (None, {'error': f"{path} was not rendered by this subcommand (it does not open with '{WORKLOG_RENDER_MARKER}'): refusing to overwrite a worklog someone else wrote. Move it aside first"})
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(markdown)
    except OSError as error:
        return (None, {'error': f'unwritable worklog: {error}'})
    return (path, None)
def _cmd_worklog(rest):
    """Render one run's worklog view from its tickets.

    The markdown rides the JSON payload rather than standing alone on
    stdout: this script's one output convention is a single JSON document
    per invocation, which is what lets every caller read a failure the
    same way, and `packet` already delivers a multi-line prompt the same
    way. `--write` puts the same bytes where contracts/worklog.md's
    readers look.
    """
    args = list(rest)
    write = '--write' in args
    while '--write' in args:
        args.remove('--write')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'worklog does not accept {stray}. usage: {WORKLOG_USAGE}'}
    if len(args) != 1:
        return {'error': f'usage: {WORKLOG_USAGE}'}
    run = args[0]
    items, error = _run_tickets(run)
    if error is not None:
        return error
    root, kind = _run_goal(items)
    markdown = _render_worklog(run, items, root, kind)
    path = None
    if write:
        path, error = _write_rendered_worklog(run, markdown)
        if error is not None:
            return error
    return {'worklog': {'run': run, 'root': root['id'], 'goal_kind': kind, 'tickets': len(items), 'path': str(path) if path is not None else None, 'markdown': markdown}}
