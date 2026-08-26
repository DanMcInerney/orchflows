"""Gate-stub construction: the one owner of what `tickets.py gate` emits.

Split out of `tickets_dispatch.py`, which had reached its size ceiling with
the gate family inside it. The family is one subject -- the stubs a root's
gate issues: a critique per lens, a repair behind several, a verify -- so it
moves whole: the stub's frontmatter, the four cut-time sections each kind
states, and the two command halves that read the run and write the family
all-or-none. With exactly one lens the family collapses to two stubs: the
critique chains `orch-repair` as its `sequence` and verify follows it.

The law this module owns beyond assembly is inheritance. A gate is the last
door before terminal, so a stub that lost the root's authority would grade
with less authority than the work it judges: a stub copies the root's
isolation, excluded_actions and fixed-input records byte-for-byte and adds
only the records its own job needs. Each stub issues in its own ticket
cohort -- a gate's broad write grant and the root's collide under
same-cohort sole-owner closure, and the escape used to be a hand edit.

A stub's pack is that inheritance too, and per stub. The root's is the floor,
since every stub carries the root's records; the cut raises it only to a pack
whose adapter carries those records too. The repair and verify take that
ceiling; a critique takes its lens's pack where the root lends it.
"""
from __future__ import annotations
import json
import re
if __package__:
    from .tickets_admission import ADMISSION_PENDING, ADMISSION_V2_PENDING, ticket_cohort
    from .tickets_transitions import declared_version
    from .tickets_commands import GATE_USAGE
    from .tickets_emission import grade_run_emission
    from .tickets_format import ADAPTER_BY_PACK, PACK_NAME_PREFIX, PACK_NAME_SUFFIX, ROOT_EXECUTOR, parse_canonical_json, _criteria, _executor_of, _extract_flag, _split_commas, ticket_defects
    from .tickets_generations import _coverage_map
    from .tickets_gate_mutations import _canonical_gate_mutation_plan
    from .tickets_input_producers import GIT_PACKS, git_head, input_groups, render_ticket_inputs
    from .tickets_issue import GATE_ID_MARKER, NEW_DEFAULT_BOUND, _distinct_gate_lenses, _render_ticket
    from .tickets_packet import GATE_CRITIQUE_ID, GATE_EXECUTORS, GATE_EXECUTOR_SECTIONS, GATE_REPAIR_ID, GATE_VERIFY_ID
    from .tickets_store import NO_SINK_ERROR, _create_text_exclusively, _run_lock, _segment_error, _tickets_root
    from .tickets_worklog import _run_tickets
else:
    from tickets_admission import ADMISSION_PENDING, ADMISSION_V2_PENDING, ticket_cohort
    from tickets_transitions import declared_version
    from tickets_commands import GATE_USAGE
    from tickets_emission import grade_run_emission
    from tickets_format import ADAPTER_BY_PACK, PACK_NAME_PREFIX, PACK_NAME_SUFFIX, ROOT_EXECUTOR, parse_canonical_json, _criteria, _executor_of, _extract_flag, _split_commas, ticket_defects
    from tickets_generations import _coverage_map
    from tickets_gate_mutations import _canonical_gate_mutation_plan
    from tickets_input_producers import GIT_PACKS, git_head, input_groups, render_ticket_inputs
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
def _pack_for_domain(domain):
    """The stamped pack a gate lens label names, or ``None``.

    `_pack_domain`'s inverse, and deliberately partial. A lens is a
    free-form review identity -- `security`, `style`, `cut-lens` -- and most
    name no pack at all; only a label a pack is actually named for names one.
    A total inverse would stamp `orch-security-pack` on a stub, and no
    adapter resolves a pack no table holds: the emission then refuses the
    whole family for a record nobody wrote.
    """
    name = PACK_NAME_PREFIX + str(domain or '').strip().casefold() + PACK_NAME_SUFFIX
    return name if name in ADAPTER_BY_PACK else None
# Which pack a gate stub may be stamped with in place of the root's. A table
# rather than a derivation, so this writing door need not import the grading
# slice: `tickets_inputs.ADAPTER_KINDS` nests exactly once -- `git-plus-render`
# resolves every kind `git` does and adds `view-identity` -- and
# `tickets_input_producers.ROOT_BY_PACK` forbids every other promotion, since
# `document-tree` and `evidence-store` each require a root literal a git or
# plain root states no source for. tests/test_tickets_gate_packs.py derives the
# relation from both tables and asserts this literal.
PACK_WIDENINGS = {'orch-code-pack': ('',), 'orch-design-pack': ('', 'orch-code-pack')}
def _pack_widens(pack, base) -> bool:
    """Whether a stub stamped ``pack`` carries every record one stamped ``base`` does."""
    pack, base = str(pack or '').strip(), str(base or '').strip()
    return pack == base or base in PACK_WIDENINGS.get(pack, ())
def _stub_pack_ceiling(base, packs):
    """The pack the repair and verify carry: the root's, widened to the widest
    pack the cut stamps that can still carry every record the root states.

    The repair changes what every unit produced, so a unit's pack reading a
    kind the root's does not -- a design unit's `view-identity` over a code
    root -- would leave the repair with no vocabulary for the finding. Only a
    widening is taken: a promotion across any other pair adds a root literal
    the promoted stub has no source for, refusing the family at render. A pack
    that widens nothing simply does not raise the ceiling, because refusing
    there would refuse a family admissible exactly as it stands, and
    `compositions/benchmaker` is that family.

    A root naming no pack promotes to nothing: a stub inherits what the root
    held and never invents what it did not.
    """
    if not str(base or '').strip():
        return base
    ceiling = base
    for pack in sorted({str(item or '').strip() for item in packs} - {''}):
        if _pack_widens(pack, ceiling):
            ceiling = pack
    return ceiling
def _critique_pack(lens, base, ceiling):
    """One critique stub's pack: its lens's, where the root can lend it.

    An unstamped root lends nothing, the ceiling's rule: a lens naming a pack
    would otherwise stamp one the root never held, and a root carrying a
    `git-tree` under no pack is a defect the gate reports rather than repairs.
    """
    if not str(base or '').strip():
        return ceiling
    named = _pack_for_domain(lens)
    return named if named and _pack_widens(named, base) else ceiling
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
def _gate_stub(run: str, ticket_id: str, executor: str, depends_on: list, write_scope: list, sections: list, pack=None, cohort=None, inherited_inputs='', baseline=None, isolation=None, excluded_actions=None, sequence=None, version=1, root_generation=None) -> str:
    """One gate stub at the root's version, on the root's authority.
    ``isolation`` and ``excluded_actions`` are the root's, passed in rather
    than defaulted, so a root that holds neither lends neither: what is
    copied is what was granted, never a safe-looking value invented here.
    ``version`` is the root's declared admission version, never this
    module's spelling of it. Under v1 the cohort is the stub's own: a gate
    stub holds a broad write grant and so does its root, and under
    same-cohort sole-owner closure those two collide; `v1:ticket:<its id>`
    keeps the collision from forming. Under v2 there is no cohort to issue
    -- a v2 ticket is frozen by its assignment seal -- so the stub joins
    as a drafting member: the root's current `root_generation` and the v2
    pending sentinel, exactly what `stamp-generation` leaves on a member,
    with the next `draft-validate` and `seal` covering the family.
    ``sequence`` is the single-lens chain (rules/delegation.md §4): stated
    beside `executor` so the chain's head visibly is the executor.
    """
    normalized_scope = [str(path).replace('\\', '/') for path in write_scope]
    mutations = [f"{'write' if path.endswith('/') else 'change'}:{path}" for path in normalized_scope]
    exclusions = [str(entry) for entry in (excluded_actions or [])]
    isolation = str(isolation).strip() if isolation else ''
    v2 = int(version) == 2
    fields = {'id': ticket_id, 'run': run, 'status': 'pending', 'admission': ADMISSION_V2_PENDING if v2 else ADMISSION_PENDING, 'cohort': None if v2 else cohort or ticket_cohort(ticket_id), 'executor': executor, 'sequence': list(sequence) if sequence else None, 'pack': pack, 'independence': 'gate', 'depends_on': list(depends_on), 'write_scope': list(write_scope), 'mutations': mutations, 'excluded_actions': exclusions or None, 'isolation': isolation or None, 'bound': NEW_DEFAULT_BOUND, 'claimed_by': '', 'claimed_at': '', 'root_generation': str(root_generation) if v2 and root_generation else None}
    body = _render_ticket(fields, _with_inherited_inputs(sections, inherited_inputs))
    text, error = render_ticket_inputs(body, run, inherited_inputs, baseline=baseline)
    if error is not None:
        raise ValueError(error)
    return text
def _gate_sections(kind: str, root_id: str, lens: str, scope: list, acceptance_id: str, acceptance: str, units: list, run: str='', mutation_plan=None, chained: bool=False, repaired_by=None) -> list:
    """The body of one gate stub. One place, so the family reads as one gate."""
    return _gate_body(kind, root_id, lens, scope, acceptance_id, acceptance, units, run, mutation_plan, chained=chained, repaired_by=repaired_by) + GATE_EXECUTOR_SECTIONS
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
def _ordered_lens_bundle(value) -> list:
    lenses = [part.strip() for part in str(value or '').split(',')]
    if not lenses or any(not lens for lens in lenses):
        raise ValueError('ordered lens bundle must not contain an empty lens identity')
    return _distinct_gate_lenses(lenses)
def _gate_complete_coverage(root: dict, coverage: str) -> bool:
    rows = []
    for line in str(coverage or '').splitlines():
        cells = [cell.strip().strip('`') for cell in line.strip().strip('|').split('|')]
        if len(cells) >= 2 and cells[0].isdigit(): rows.append((int(cells[0]), cells[1]))
    criteria = _criteria((root.get('sections') or {}).get('Completion test', ''))
    return bool(criteria) and rows == [(number, 'gate') for number in range(1, len(criteria) + 1)]
def _input_name(prefix: str, value: str, position: int) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', str(value).lower()).strip('-')
    return f'{prefix}-{slug or position}'
def _gate_body(kind: str, root_id: str, lens: str, scope: list, acceptance_id: str, acceptance: str, units: list, run: str='', mutation_plan=None, chained: bool=False, repaired_by=None) -> list:
    """The four cut-time sections of one gate stub.
    ``chained`` marks the single-lens critique that carries the repair as
    its `sequence` continuation: its body gains the repair half's objective
    sentence and criteria, since the chained ticket is the complete packet
    for both skills. ``repaired_by`` names the stub whose `## Result` holds
    the repaired revision the verify decides at -- the repair stub where one
    stands, the chained critique where none does.
    """
    if kind == 'critique':
        inputs = [_gate_input('lens', literal=lens)]
        inputs.extend(
            _gate_input(_input_name('unit-result', unit, position), run=run, ticket=unit, section='Result')
            for position, unit in enumerate(units, start=1)
        )
        inputs.append(_gate_input('acceptance', run=run, ticket=acceptance_id, section='Completion test'))
        objective = f"Every defect in `{root_id}`'s delivered result that the `{lens}` lens finds is reported by identity with its evidence: an open search over what the subtree produced, not a re-run of the criteria it already states."
        criteria = [f"- every finding names the artifact identity it was found at and the evidence that shows it | oracle: this ticket's `## Result` read under the `{lens}` lens | oracle_class: judged | provenance: pre-existing", f"- every `## Result` named in the fixed inputs was read | oracle: this ticket's `## Result` against that list | oracle_class: deterministic | provenance: pre-existing"]
        returns = 'status; result — ranked findings, each with its artifact identity and evidence; verification; feedback; risks'
        if chained:
            objective += " Then, as this chain's second skill, every accepted blocking finding is repaired inside this ticket's own write scope or declined with a stated reason, every accepted non-blocking finding is queued as candidate scope per verification §9, and nothing outside that scope changes."
            criteria.extend(["- every accepted blocking finding is repaired or declined with a stated reason, and every accepted non-blocking finding is queued as candidate scope | oracle: this ticket's own ranked findings against its `## Result` | oracle_class: deterministic | provenance: pre-existing", "- nothing outside the write scope changed | oracle: `git status --porcelain` in the run's workspace | oracle_class: deterministic | provenance: pre-existing"])
            returns = "status; result — ranked findings, each with its artifact identity and evidence, then each finding's disposition and the changed artifact by identity; verification; feedback; risks"
        return [('Objective', objective), ('Fixed inputs', '\n'.join(inputs)), ('Completion test', '\n'.join(criteria)), ('Return fields', returns)]
    if kind == 'repair':
        inputs = [
            _gate_input(_input_name('critique-result', unit, position), run=run, ticket=unit, section='Result')
            for position, unit in enumerate(units, start=1)
        ]
        return [('Objective', f"Every accepted blocking finding against `{root_id}` is repaired inside this ticket's own write scope, or declined with a stated reason; every accepted non-blocking finding is queued as candidate scope per verification §9, and nothing outside that scope changes."), ('Fixed inputs', '\n'.join(inputs)), ('Completion test', '\n'.join(["- every accepted blocking finding is repaired or declined with a stated reason, and every accepted non-blocking finding is queued as candidate scope | oracle: the critique tickets' findings against this ticket's `## Result` | oracle_class: deterministic | provenance: pre-existing", "- nothing outside the write scope changed | oracle: `git status --porcelain` in the run's workspace | oracle_class: deterministic | provenance: pre-existing"])), ('Return fields', 'status; result — each finding, its disposition and the changed artifact by identity; verification; feedback; risks')]
    repair_id = repaired_by or GATE_REPAIR_ID.format(root=root_id); inputs = [_gate_input('acceptance', run=run, ticket=acceptance_id, section='Completion test'), _gate_input('repair-result', run=run, ticket=repair_id, section='Result'), _gate_input('mutation-plan-paths', literal=mutation_plan)]
    return [('Objective', f"`{acceptance_id}`'s acceptance is decided at the revision `{repair_id}` left: one verdict per criterion, from the oracle that criterion names."), ('Fixed inputs', '\n'.join(inputs)), ('Completion test', acceptance), ('Return fields', "status; verification — one verdict per criterion with the oracle's output; result; feedback; risks")]
def _ordered_bundle_sections(root_id: str, lenses: list, scope: list, acceptance_id: str, acceptance: str, units: list, run: str='') -> list:
    """One closer packet whose canonical literal seals the lens order."""
    inputs = [_gate_input('ordered-lens-bundle', literal=list(lenses))]
    inputs.extend(_gate_input(_input_name('unit-result', unit, position), run=run, ticket=unit, section='Result') for position, unit in enumerate(units, start=1))
    inputs.append(_gate_input('acceptance', run=run, ticket=acceptance_id, section='Completion test'))
    named = ', '.join(f'`{lens}`' for lens in lenses)
    objective = (f"Every defect in `{root_id}`'s delivered result found by the ordered lens bundle {named} is reported by identity with its evidence, applying each lens in the stated order as an open search over what the subtree produced. Then, as this chain's second skill, every accepted blocking finding is repaired inside this ticket's own write scope or declined with a stated reason, every accepted non-blocking finding is queued as candidate scope per verification §9, and nothing outside that scope changes.")
    criteria = ["- every finding names the artifact identity it was found at, the lens that found it, and the evidence that shows it | oracle: this ticket's `## Result` read under the `ordered-lens-bundle` in its stated order | oracle_class: judged | provenance: pre-existing", "- every `## Result` named in the fixed inputs was read | oracle: this ticket's `## Result` against that list | oracle_class: deterministic | provenance: pre-existing", "- every accepted blocking finding is repaired or declined with a stated reason, and every accepted non-blocking finding is queued as candidate scope | oracle: this ticket's own ranked findings against its `## Result` | oracle_class: deterministic | provenance: pre-existing", "- nothing outside the write scope changed | oracle: `git status --porcelain` in the run's workspace | oracle_class: deterministic | provenance: pre-existing"]
    returns = "status; result — ranked findings in ordered-lens-bundle order, each with its lens, artifact identity and evidence, then each finding's disposition and the changed artifact by identity; verification; feedback; risks"
    return [('Objective', objective), ('Fixed inputs', '\n'.join(inputs)), ('Completion test', '\n'.join(criteria)), ('Return fields', returns)] + GATE_EXECUTOR_SECTIONS
def _cmd_gate(rest, head_probe=None):
    """Serialize the gate's complete state read and all-or-none creation.
    ``head_probe`` is the revision reading the whole family is sealed at.
    It is taken once, by the caller's own probe when one is supplied, so
    that every sibling stub names one revision even though three of them
    are rendered: a family whose stubs disagreed about the baseline would
    grade one delivery at two identities.
    """
    probe = list(rest)
    for flag in ('--lens', '--ordered-lens-bundle', '--write-scope', '--acceptance-from'):
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
    lens_present = '--lens' in args
    bundle_present = '--ordered-lens-bundle' in args
    lens_arg = _extract_flag(args, '--lens')
    bundle_arg = _extract_flag(args, '--ordered-lens-bundle')
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
    if lens_present and bundle_present:
        return {'error': 'gate accepts either --lens or --ordered-lens-bundle, not both. Nothing was written'}
    try:
        lenses = _ordered_lens_bundle(bundle_arg) if bundle_present else _split_commas(lens_arg)
    except ValueError as error:
        return {'error': str(error) + '. Nothing was written'}
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
    gate_prefix = f'{root_id}.gate.'
    units = sorted((item_id for item_id in by_id if item_id.startswith(f'{root_id}.') and (not item_id.startswith(gate_prefix))))
    if not lenses and not bundle_present:
        # The cut's domains, not the root's alone: a mixed cut whose default
        # lens set was the root's shipped one domain unreviewed. The root's
        # label leads and is unfiltered -- a custom pack keeps yielding its own
        # domain, as it did -- while an added unit's domain must name a pack
        # this host knows, since a garbage stamp would otherwise mint a lens
        # whose critique stub refuses. For any single-pack cut this is the
        # root's label alone, which is what it has always been.
        domains = [_pack_domain(root.get('pack'))]
        domains.extend(_pack_domain(by_id[unit].get('pack')) for unit in units
                       if _pack_for_domain(_pack_domain(by_id[unit].get('pack'))))
        lenses = [label for label in dict.fromkeys(domains) if label]
    if not lenses:
        return {'error': f"gate requires --lens: one critique stub per stamped lens, and neither root ticket '{root_id}' nor its cut names a pack whose domain could stand in. usage: " + GATE_USAGE}
    if not bundle_present:
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
    if not units:
        if not bundle_present:
            return {'error': f"root ticket '{root_id}' has no `{root_id}.` subtree ticket yet: a gate closes over a cut subtree, so there is nothing here for a critique to read"}
        if declared_version(root) != 2:
            return {'error': f"root ticket '{root_id}' has no implementation members: a gate-only ordered lens bundle requires a v2 root. Nothing was written"}
        try:
            coverage = _coverage_map(run, root_id)
        except ValueError as error:
            return {'error': str(error) + '. Nothing was written'}
        if not _gate_complete_coverage(root, coverage):
            return {'error': f"root ticket '{root_id}' has no implementation members: its coverage map must assign every root criterion exactly once to gate. Nothing was written"}
    acceptance_id = acceptance_from or root_id
    source = by_id.get(acceptance_id)
    if source is None:
        return {'error': f"--acceptance-from names '{acceptance_id}', which is not a ticket in run '{run}'"}
    acceptance = (source.get('sections') or {}).get('Completion test', '').strip()
    if not acceptance:
        return {'error': f"ticket '{acceptance_id}' states no `## Completion test`, so the verify stub would carry no acceptance"}
    pack = root.get('pack')
    ceiling = _stub_pack_ceiling(pack, (by_id[unit].get('pack') for unit in units))
    critique_packs = {lens: _critique_pack(lens, pack, ceiling) for lens in lenses}
    inherited_inputs = (root.get('sections') or {}).get('Fixed inputs', '')
    isolation = root.get('isolation')
    exclusions = list(root.get('excluded_actions') or [])
    version = declared_version(root)
    root_generation = str(root.get('root_generation') or '') or None
    gate_baseline = (head_probe or git_head)()
    # Asked of the packs this family will actually be stamped with, and read
    # off `GIT_PACKS` rather than a second copy of its membership here.
    needs_head = sorted({name for name in {ceiling, *critique_packs.values()} if name in GIT_PACKS})
    if needs_head and gate_baseline is None:
        return {'error': f"{', '.join(needs_head)} gate input rendering cannot resolve the run-project HEAD. Nothing was written"}
    rendered = []
    critique_ids = []
    # One lens pools nothing: that critique's findings are already the whole
    # repair bill, so the repair rides the same child as a stated `sequence`
    # (rules/delegation.md §4) and no separate repair stub is emitted. The
    # chained stub is built by the same `stub` closure as the repair stub
    # was, so everything the repair inherited -- the root's fixed inputs,
    # isolation and exclusions verbatim -- reaches it, and the gate scope
    # becomes its own write_scope: the chain's second skill holds exactly
    # the authority the separate stub held, but not its own role: a chain
    # runs at its head's (rules/roles.md §4), so the repair half spends
    # the critique's planner binding -- the price of the spawn it saves.
    # Several lenses keep that stub:
    # pooled findings take one fix per shared cause, and a per-lens critique
    # owning its own repair bill has an incentive to soften findings.
    chained = bundle_present or len(lenses) == 1
    def stub(stub_id, executor, depends, stub_scope, stub_sections, sequence=None, stub_pack=None):
        """One stub of this family, on this root's authority, version and pack.

        `stub_pack` defaults to the ceiling: the repair and the verify write and
        decide across every unit, so they carry the widest pack the cut lends.
        A critique passes its lens's.
        """
        return _gate_stub(run, stub_id, executor, depends, stub_scope, stub_sections, ceiling if stub_pack is None else stub_pack, inherited_inputs=inherited_inputs, baseline=gate_baseline, isolation=isolation, excluded_actions=exclusions, sequence=sequence, version=version, root_generation=root_generation)
    try:
        for lens in lenses:
            invalid = _segment_error('lens', lens)
            if invalid is not None:
                return invalid
        if bundle_present:
            stub_id = GATE_CRITIQUE_ID.format(root=root_id, lens='bundle')
            critique_ids.append(stub_id)
            sections = _ordered_bundle_sections(root_id, lenses, scope, acceptance_id, acceptance, units, run)
            chain = [GATE_EXECUTORS['critique'], GATE_EXECUTORS['repair']]
            rendered.append((stub_id, stub(stub_id, GATE_EXECUTORS['critique'], units, scope, sections, sequence=chain)))
        else:
            for lens in lenses:
                stub_id = GATE_CRITIQUE_ID.format(root=root_id, lens=lens)
                critique_ids.append(stub_id)
                sections = _gate_sections('critique', root_id, lens, scope, acceptance_id, acceptance, units, run, chained=chained)
                chain = [GATE_EXECUTORS['critique'], GATE_EXECUTORS['repair']] if chained else None
                # A chained critique is also the repair, and the write half is the
                # half a pack is authority for: it takes the ceiling, which always
                # widens any lens pack eligible to be used at all.
                rendered.append((stub_id, stub(stub_id, GATE_EXECUTORS['critique'], units, scope if chained else [], sections, sequence=chain, stub_pack=None if chained else critique_packs[lens])))
        if chained:
            repaired_by = critique_ids[0]
        else:
            repaired_by = GATE_REPAIR_ID.format(root=root_id)
            rendered.append((repaired_by, stub(repaired_by, GATE_EXECUTORS['repair'], critique_ids, scope, _gate_sections('repair', root_id, '', scope, acceptance_id, acceptance, critique_ids, run))))
        verify_id = GATE_VERIFY_ID.format(root=root_id)
        rendered.append((verify_id, stub(verify_id, GATE_EXECUTORS['verify'], [repaired_by], [], _gate_sections('verify', root_id, '', scope, acceptance_id, acceptance, units, run, mutation_plan, repaired_by=repaired_by))))
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
    # The fifth emitting door's grade. `ticket_defects` above reads contract
    # shape only, so a family that is well-formed and collides with nothing
    # still reached the disk carrying whatever the next door refuses -- the
    # instance this run is named for. Graded as one batch, like `instantiate`:
    # the family's stubs are written all-or-none, so a refusal naming only
    # whichever was graded first is one the caller cannot act on.
    emission = grade_run_emission('gate', run, run_dir, dict(rendered))
    if emission is not None:
        return {**emission, 'error': emission['error'] + '. Nothing was written'}
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
    payload = {'run': run, 'root': root_id, 'lenses': lenses, 'acceptance_from': acceptance_id, 'ids': [stub_id for stub_id, _ in rendered], 'paths': [str(path) for path in written]}
    if bundle_present:
        payload['ordered_lens_bundle'] = list(lenses)
    if version == 2:
        # A v2 family lands drafting: the seal is the one door that writes
        # generation fields, so completion is named rather than imitated.
        payload['next'] = [f'draft-validate {run} {root_id}', f'seal {run} {root_id} --cut-generation <the new draft identity>']
    return {'gate': payload}
__all__ = (
    'PACK_WIDENINGS', '_cmd_gate', '_critique_pack', '_gate_body', '_gate_input',
    '_gate_sections', '_gate_stub', '_gate_under_run_lock',
    '_inherited_input_lines', '_input_name', '_is_record', '_listed_items',
    '_gate_complete_coverage', '_ordered_bundle_sections', '_ordered_lens_bundle', '_pack_domain', '_pack_for_domain', '_pack_widens', '_record_names',
    '_stub_pack_ceiling', '_with_inherited_inputs',
)
