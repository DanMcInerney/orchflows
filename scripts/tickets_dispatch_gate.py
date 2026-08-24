"""Gate-stub construction: the one owner of what `tickets.py gate` emits.

Split out of `tickets_dispatch.py`, which had reached its size ceiling with
the gate family inside it. The family is one subject -- the three stubs a
root's gate issues -- so it moves whole: the stub's frontmatter, the four
cut-time sections each kind states, and the two command halves that read the
run and write the family all-or-none.

The law this module owns beyond assembly is inheritance. A gate is the last
door before terminal, so a stub that lost the root's authority would grade
with less authority than the work it judges: a stub copies the root's
isolation, excluded_actions and fixed-input records byte-for-byte and adds
only the records its own job needs. Each stub issues in its own ticket
cohort -- a gate's broad write grant and the root's collide under
same-cohort sole-owner closure, and the escape used to be a hand edit.
"""
from __future__ import annotations
import json
import re
if __package__:
    from .tickets_admission import ADMISSION_PENDING, ticket_cohort
    from .tickets_commands import GATE_USAGE
    from .tickets_format import PACK_NAME_PREFIX, PACK_NAME_SUFFIX, ROOT_EXECUTOR, parse_canonical_json, _executor_of, _extract_flag, _split_commas, ticket_defects
    from .tickets_gate_mutations import _canonical_gate_mutation_plan
    from .tickets_input_producers import git_head, input_groups, render_ticket_inputs
    from .tickets_issue import GATE_ID_MARKER, NEW_DEFAULT_BOUND, _distinct_gate_lenses, _render_ticket
    from .tickets_packet import GATE_CRITIQUE_ID, GATE_EXECUTORS, GATE_EXECUTOR_SECTIONS, GATE_REPAIR_ID, GATE_VERIFY_ID
    from .tickets_store import NO_SINK_ERROR, _create_text_exclusively, _run_lock, _segment_error, _tickets_root
    from .tickets_worklog import _run_tickets
else:
    from tickets_admission import ADMISSION_PENDING, ticket_cohort
    from tickets_commands import GATE_USAGE
    from tickets_format import PACK_NAME_PREFIX, PACK_NAME_SUFFIX, ROOT_EXECUTOR, parse_canonical_json, _executor_of, _extract_flag, _split_commas, ticket_defects
    from tickets_gate_mutations import _canonical_gate_mutation_plan
    from tickets_input_producers import git_head, input_groups, render_ticket_inputs
    from tickets_issue import GATE_ID_MARKER, NEW_DEFAULT_BOUND, _distinct_gate_lenses, _render_ticket
    from tickets_packet import GATE_CRITIQUE_ID, GATE_EXECUTORS, GATE_EXECUTOR_SECTIONS, GATE_REPAIR_ID, GATE_VERIFY_ID
    from tickets_store import NO_SINK_ERROR, _create_text_exclusively, _run_lock, _segment_error, _tickets_root
    from tickets_worklog import _run_tickets
def _pack_domain(pack) -> str:
    """The domain label of a stamped pack: `orch-code-pack` -> `code`.
    contracts/pack-signature.md's `lens` cell binds `orch-critique` with the
    pack's craft `## Lens` and names no label of its own, so there is one
    label a caller never has to invent: the domain the pack is named for.
    """
    name = str(pack or '').strip()
    if name.startswith(PACK_NAME_PREFIX):
        name = name[len(PACK_NAME_PREFIX):]
    if name.endswith(PACK_NAME_SUFFIX):
        name = name[:-len(PACK_NAME_SUFFIX)]
    return name
def _is_record(group: list) -> bool:
    """Whether ``group`` opens on a canonical ``- input:`` record line.
    Judged on the opening line alone, never on the group's length. A
    canonical record is one line, but `input_groups` hands back every later
    non-blank line attached to the group the last `- ` opened -- so a root
    that ends `## Fixed inputs` with a line of prose delivers its final
    record inside a two-line group. Reading the length there would drop a
    record the root plainly states, silently, and 16 of this host's 90 root
    tickets carry exactly that shape. A record wrapped across lines is
    still skipped: its opening line is partial JSON and fails to parse.
    """
    return bool(group) and group[0].startswith('- input: ')
def _record_names(body: str) -> set:
    """The ``name`` of every canonical input record stated in ``body``."""
    names = set()
    for group in input_groups(body or ''):
        if not _is_record(group):
            continue
        try:
            record = parse_canonical_json(group[0][len('- input: '):])
        except ValueError:
            continue
        name = record.get('name') if isinstance(record, dict) else None
        if isinstance(name, str):
            names.add(name)
    return names
def _inherited_input_lines(own: str, inherited: str) -> list:
    """The root's fixed-input records the gate does not already state.
    Each is carried as the exact line the root states it on. A gate grades a
    delivery against the root's authority, so what it reads is the root's
    own bytes and not a paraphrase reassembled here.
    A record whose name the gate already uses stays the gate's: the gate's
    record is the one that names its own job, and `render_inputs` refuses a
    duplicate name outright, so one of the two has to yield.
    """
    names = _record_names(own)
    lines = []
    for group in input_groups(inherited or ''):
        if not _is_record(group):
            continue
        try:
            record = parse_canonical_json(group[0][len('- input: '):])
        except ValueError:
            continue
        name = record.get('name') if isinstance(record, dict) else None
        if not isinstance(name, str) or name in names:
            continue
        names.add(name)
        lines.append(group[0])
    return lines
def _with_inherited_inputs(sections: list, inherited: str) -> list:
    """``sections``, with the root's records appended to its Fixed inputs."""
    extended = []
    for heading, content in sections:
        if heading == 'Fixed inputs':
            lines = _inherited_input_lines(content, inherited)
            if lines:
                content = '\n'.join(([content] if content.strip() else []) + lines)
        extended.append((heading, content))
    return extended
def _gate_stub(run: str, ticket_id: str, executor: str, depends_on: list, write_scope: list, sections: list, pack=None, cohort=None, inherited_inputs='', baseline=None, isolation=None, excluded_actions=None) -> str:
    """One gate stub: its own cohort, the root's authority, its own records.
    ``isolation`` and ``excluded_actions`` are the root's, passed in rather
    than defaulted, so a root that holds neither lends neither: what is
    copied is what was granted, never a safe-looking value invented here.
    The cohort is the stub's own. A gate stub holds a broad write grant and
    so does its root, and under same-cohort sole-owner closure those two
    collide; issuing each stub in `v1:ticket:<its id>` keeps the collision
    from forming instead of leaving a hand edit to undo it.
    """
    normalized_scope = [str(path).replace('\\', '/') for path in write_scope]
    mutations = [f"{'write' if path.endswith('/') else 'change'}:{path}" for path in normalized_scope]
    exclusions = [str(entry) for entry in (excluded_actions or [])]
    isolation = str(isolation).strip() if isolation else ''
    fields = {'id': ticket_id, 'run': run, 'status': 'pending', 'admission': ADMISSION_PENDING, 'cohort': cohort or ticket_cohort(ticket_id), 'executor': executor, 'pack': pack, 'independence': 'gate', 'depends_on': list(depends_on), 'write_scope': list(write_scope), 'mutations': mutations, 'excluded_actions': exclusions or None, 'isolation': isolation or None, 'bound': NEW_DEFAULT_BOUND, 'claimed_by': '', 'claimed_at': ''}
    body = _render_ticket(fields, _with_inherited_inputs(sections, inherited_inputs))
    text, error = render_ticket_inputs(body, run, inherited_inputs, baseline=baseline)
    if error is not None:
        raise ValueError(error)
    return text
def _gate_sections(kind: str, root_id: str, lens: str, scope: list, acceptance_id: str, acceptance: str, units: list, run: str='', mutation_plan=None) -> list:
    """The body of one gate stub. One place, so the three read as one gate."""
    return _gate_body(kind, root_id, lens, scope, acceptance_id, acceptance, units, run, mutation_plan) + GATE_EXECUTOR_SECTIONS
def _listed_items(values, indent: str='') -> str:
    """A frontmatter list stated in prose as the items it holds.
    Never the Python repr of the list. An executor greps its own ticket for
    the path it may write, and `repr` doubles every separator a Windows path
    carries, so the body named `scripts\\\\one.py` where the frontmatter --
    and the filesystem -- said `scripts\\one.py`.
    """
    return '\n'.join((f'{indent}- `{value}`' for value in values))
def _gate_input(name: str, *, literal=None, run: str='', ticket: str='', section: str='') -> str:
    """One canonical fixed-input record for a generated gate."""
    if ticket:
        record = {
            'identity': {'kind': 'ticket-section', 'run': run, 'section': section, 'ticket': ticket},
            'name': name,
            'type': 'identity',
        }
    else:
        record = {'name': name, 'type': 'literal', 'value': literal}
    return '- input: ' + json.dumps(record, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
def _input_name(prefix: str, value: str, position: int) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', str(value).lower()).strip('-')
    return f'{prefix}-{slug or position}'
def _gate_body(kind: str, root_id: str, lens: str, scope: list, acceptance_id: str, acceptance: str, units: list, run: str='', mutation_plan=None) -> list:
    """The four cut-time sections of one gate stub."""
    if kind == 'critique':
        inputs = [_gate_input('lens', literal=lens)]
        inputs.extend(
            _gate_input(_input_name('unit-result', unit, position), run=run, ticket=unit, section='Result')
            for position, unit in enumerate(units, start=1)
        )
        inputs.append(_gate_input('acceptance', run=run, ticket=acceptance_id, section='Completion test'))
        return [('Objective', f"Every defect in `{root_id}`'s delivered result that the `{lens}` lens finds is reported by identity with its evidence: an open search over what the subtree produced, not a re-run of the criteria it already states."), ('Fixed inputs', '\n'.join(inputs)), ('Completion test', '\n'.join([f"- every finding names the artifact identity it was found at and the evidence that shows it | oracle: this ticket's `## Result` read under the `{lens}` lens | oracle_class: judged | provenance: pre-existing", f"- every `## Result` named in the fixed inputs was read | oracle: this ticket's `## Result` against that list | oracle_class: deterministic | provenance: pre-existing"])), ('Return fields', 'status; result — ranked findings, each with its artifact identity and evidence; verification; feedback; risks')]
    if kind == 'repair':
        inputs = [
            _gate_input(_input_name('critique-result', unit, position), run=run, ticket=unit, section='Result')
            for position, unit in enumerate(units, start=1)
        ]
        return [('Objective', f"Every accepted blocking finding against `{root_id}` is repaired inside this ticket's own write scope, or declined with a stated reason; every accepted non-blocking finding is queued as candidate scope per verification §9, and nothing outside that scope changes."), ('Fixed inputs', '\n'.join(inputs)), ('Completion test', '\n'.join(["- every accepted blocking finding is repaired or declined with a stated reason, and every accepted non-blocking finding is queued as candidate scope | oracle: the critique tickets' findings against this ticket's `## Result` | oracle_class: deterministic | provenance: pre-existing", "- nothing outside the write scope changed | oracle: `git status --porcelain` in the run's workspace | oracle_class: deterministic | provenance: pre-existing"])), ('Return fields', 'status; result — each finding, its disposition and the changed artifact by identity; verification; feedback; risks')]
    repair_id = GATE_REPAIR_ID.format(root=root_id); inputs = [_gate_input('acceptance', run=run, ticket=acceptance_id, section='Completion test'), _gate_input('repair-result', run=run, ticket=repair_id, section='Result'), _gate_input('mutation-plan-paths', literal=mutation_plan)]
    return [('Objective', f"`{acceptance_id}`'s acceptance is decided at the revision `{repair_id}` left: one verdict per criterion, from the oracle that criterion names."), ('Fixed inputs', '\n'.join(inputs)), ('Completion test', acceptance), ('Return fields', "status; verification — one verdict per criterion with the oracle's output; result; feedback; risks")]
def _cmd_gate(rest, head_probe=None):
    """Serialize the gate's complete state read and all-or-none creation.
    ``head_probe`` is the revision reading the whole family is sealed at.
    It is taken once, by the caller's own probe when one is supplied, so
    that every sibling stub names one revision even though three of them
    are rendered: a family whose stubs disagreed about the baseline would
    grade one delivery at two identities.
    """
    probe = list(rest)
    for flag in ('--lens', '--write-scope', '--acceptance-from'):
        _extract_flag(probe, flag)
    if len(probe) != 2 or _segment_error('run id', probe[0]) is not None:
        return _gate_under_run_lock(rest, head_probe)
    try:
        with _run_lock(probe[0]):
            return _gate_under_run_lock(rest, head_probe)
    except OSError as error:
        return {'error': f'unable to create gate: {error}. Nothing was written'}
def _gate_under_run_lock(rest, head_probe=None):
    """Write one root ticket's gate stubs into its run.
    Refused rather than half-written: a root with no `<root>.NN` units has
    nothing for a critique to close over, and a stub id already issued
    means a gate is already standing — writing a second one would put two
    repairs on one scope. Nothing lands until every stub is graded.
    """
    args = list(rest)
    lens_arg = _extract_flag(args, '--lens')
    scope_arg = _extract_flag(args, '--write-scope')
    acceptance_from = _extract_flag(args, '--acceptance-from')
    stray = next((arg for arg in args if arg.startswith('-')), None)
    if stray is not None:
        return {'error': f'gate does not accept {stray}. usage: {GATE_USAGE}'}
    if len(args) != 2:
        return {'error': f'usage: {GATE_USAGE}'}
    run, root_id = args
    for kind, value in (('run id', run), ('root id', root_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    lenses = _split_commas(lens_arg)
    items, error = _run_tickets(run)
    if error is not None:
        return error
    by_id = {item['id']: item for item in items}
    root = by_id.get(root_id)
    if root is None:
        return {'error': f"root ticket '{root_id}' is not in run '{run}'"}
    roots = sorted((str(item.get('id') or '') for item in items if _executor_of(item) == ROOT_EXECUTOR))
    if _executor_of(root) != ROOT_EXECUTOR or roots != [root_id]:
        return {'error': f"gate root '{root_id}' is not the run's sole orch-decompose root ({roots or 'none'}). One physical run's one gate belongs only to that root. Nothing was written"}
    if not lenses:
        lenses = _split_commas(_pack_domain(root.get('pack')))
    if not lenses:
        return {'error': f"gate requires --lens: one critique stub per stamped lens, and root ticket '{root_id}' names no pack whose domain could stand in. usage: " + GATE_USAGE}
    try:
        lenses = _distinct_gate_lenses(lenses)
    except ValueError as error:
        return {'error': str(error) + '. Nothing was written'}
    gate_roots = sorted({str(item.get('id') or '').split(GATE_ID_MARKER, 1)[0] for item in items if GATE_ID_MARKER in str(item.get('id') or '')})
    other_gate_roots = [owner for owner in gate_roots if owner != root_id]
    if other_gate_roots:
        return {'error': f"run '{run}' already has the one gate owned by root '{other_gate_roots[0]}': root '{root_id}' cannot create a second gate family. Nothing was written"}
    scope = (_split_commas(scope_arg) if scope_arg is not None
             else list(root.get('write_scope') or []))
    if not scope:
        return {'error': f"gate requires --write-scope: the scope the repair holds, and root ticket '{root_id}' declares none to default to. usage: " + GATE_USAGE}
    mutation_plan, mutation_error = _canonical_gate_mutation_plan(root.get('mutations'))
    if mutation_error is not None:
        return {'error': mutation_error + '. Nothing was written'}
    gate_prefix = f'{root_id}.gate.'
    units = sorted((item_id for item_id in by_id if item_id.startswith(f'{root_id}.') and (not item_id.startswith(gate_prefix))))
    if not units:
        return {'error': f"root ticket '{root_id}' has no `{root_id}.` subtree ticket yet: a gate closes over a cut subtree, so there is nothing here for a critique to read"}
    acceptance_id = acceptance_from or root_id
    source = by_id.get(acceptance_id)
    if source is None:
        return {'error': f"--acceptance-from names '{acceptance_id}', which is not a ticket in run '{run}'"}
    acceptance = (source.get('sections') or {}).get('Completion test', '').strip()
    if not acceptance:
        return {'error': f"ticket '{acceptance_id}' states no `## Completion test`, so the verify stub would carry no acceptance"}
    pack = root.get('pack')
    inherited_inputs = (root.get('sections') or {}).get('Fixed inputs', '')
    isolation = root.get('isolation')
    exclusions = list(root.get('excluded_actions') or [])
    gate_baseline = (head_probe or git_head)()
    if pack in ('orch-code-pack', 'orch-design-pack') and gate_baseline is None:
        return {'error': f'{pack} gate input rendering cannot resolve the run-project HEAD. Nothing was written'}
    rendered = []
    critique_ids = []
    def stub(stub_id, executor, depends, stub_scope, stub_sections):
        """One stub of this family, on this root's authority."""
        return _gate_stub(run, stub_id, executor, depends, stub_scope, stub_sections, pack, inherited_inputs=inherited_inputs, baseline=gate_baseline, isolation=isolation, excluded_actions=exclusions)
    try:
        for lens in lenses:
            invalid = _segment_error('lens', lens)
            if invalid is not None:
                return invalid
            stub_id = GATE_CRITIQUE_ID.format(root=root_id, lens=lens)
            critique_ids.append(stub_id)
            rendered.append((stub_id, stub(stub_id, GATE_EXECUTORS['critique'], units, [], _gate_sections('critique', root_id, lens, scope, acceptance_id, acceptance, units, run))))
        repair_id = GATE_REPAIR_ID.format(root=root_id)
        rendered.append((repair_id, stub(repair_id, GATE_EXECUTORS['repair'], critique_ids, scope, _gate_sections('repair', root_id, '', scope, acceptance_id, acceptance, critique_ids, run))))
        verify_id = GATE_VERIFY_ID.format(root=root_id)
        rendered.append((verify_id, stub(verify_id, GATE_EXECUTORS['verify'], [repair_id], [], _gate_sections('verify', root_id, '', scope, acceptance_id, acceptance, units, run, mutation_plan))))
    except ValueError as error:
        return {'error': str(error) + '. Nothing was written'}
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {'error': NO_SINK_ERROR}
    run_dir = tickets_root / run
    for stub_id, text in rendered:
        defects = ticket_defects(text)
        if defects:
            return {'error': f'gate stub {stub_id} is off contract (contracts/work-item.md): ' + '; '.join(defects)}
        if (run_dir / f'{stub_id}.md').exists():
            return {'error': f"gate stub '{stub_id}' is already issued in run '{run}': a root ticket has one gate. Nothing was written"}
    written = []
    try:
        for stub_id, text in rendered:
            path = run_dir / f'{stub_id}.md'
            _create_text_exclusively(path, text)
            written.append(path)
    except OSError as error:
        for path in written:
            path.unlink(missing_ok=True)
        return {'error': f'unwritable gate stub: {error}. Nothing was written'}
    return {'gate': {'run': run, 'root': root_id, 'lenses': lenses, 'acceptance_from': acceptance_id, 'ids': [stub_id for stub_id, _ in rendered], 'paths': [str(path) for path in written]}}
__all__ = (
    '_cmd_gate', '_gate_body', '_gate_input', '_gate_sections', '_gate_stub',
    '_gate_under_run_lock', '_inherited_input_lines', '_input_name',
    '_is_record', '_listed_items', '_pack_domain', '_record_names',
    '_with_inherited_inputs',
)
