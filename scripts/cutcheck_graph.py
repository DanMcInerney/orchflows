"""Grade ticket graph layout and render graph readings."""

import functools
import importlib.util

try:  # repository checkout
    from scripts import cutcheck_contract as _contract
except ImportError:  # installed flat script directory
    import cutcheck_contract as _contract
CHECKED_BY_KEY = _contract.CHECKED_BY_KEY
Path = _contract.Path
SHARED_TEST_MODULE = _contract.SHARED_TEST_MODULE
COMPLETION_SECTION = _contract.COMPLETION_SECTION
CRITICAL_PATH = _contract.CRITICAL_PATH
GATE_EXECUTORS = _contract.GATE_EXECUTORS
GATE_ID_MARKER = _contract.GATE_ID_MARKER
GATE_INFIX = _contract.GATE_INFIX
LEVEL_WIDTH = _contract.LEVEL_WIDTH
MALFORMED_GATE = _contract.MALFORMED_GATE
MIXED_INDEPENDENCE = _contract.MIXED_INDEPENDENCE
MULTIPLE_GATE_SYSTEMS = _contract.MULTIPLE_GATE_SYSTEMS
MULTIPLE_ROOTS = _contract.MULTIPLE_ROOTS
ROOT_EXECUTOR = _contract.ROOT_EXECUTOR
SCOPE_COLLISION = _contract.SCOPE_COLLISION
STAGED_INVALIDATION = _contract.STAGED_INVALIDATION
_sections = _contract._sections

try:  # repository checkout
    from scripts import cutcheck_commands as _commands_module
except ImportError:  # installed flat script directory
    import cutcheck_commands as _commands_module
_commands = _commands_module._commands
_criteria = _commands_module._criteria

try:  # repository checkout
    from scripts import cutcheck_scope as _scope
except ImportError:  # installed flat script directory
    import cutcheck_scope as _scope
_listed = _scope._listed
_overlaps = _scope._overlaps
_path_args = _scope._path_args


def _issued_under(siblings, root):
    """Defer the graph-to-coverage edge until coverage is loaded."""
    try:
        from scripts.cutcheck_coverage import _issued_under as issued_under
    except ImportError:  # installed flat script directory
        from cutcheck_coverage import _issued_under as issued_under
    return issued_under(siblings, root)


def _oracle_reads(text):
    """Every path this item's oracles reach for, across its completion test."""

    found = []
    for _, criterion in _criteria(_sections(text).get(COMPLETION_SECTION, "")):
        for command in _commands(criterion):
            found.extend(_path_args(command))
    return found


def _ancestors(item, siblings):
    """Every item reachable from ``item`` through ``depends_on``."""

    seen = set()
    pending = _listed(siblings.get(item) or {}, "depends_on")
    while pending:
        node = pending.pop()
        if node in seen or node not in siblings:
            continue
        seen.add(node)
        pending.extend(_listed(siblings[node], "depends_on"))
    return seen


def _first_overlap(paths, scopes):
    for path in paths:
        for entry in scopes:
            if _overlaps(path, entry):
                return path
    return None


def _shared_artifacts(left, right):
    """Every distinct path overlapped by two scopes, most-specific first."""

    shared = set()
    for left_path in left:
        for right_path in right:
            if not _overlaps(left_path, right_path):
                continue
            left_value = str(left_path).replace("\\", "/").rstrip("/")
            right_value = str(right_path).replace("\\", "/").rstrip("/")
            shared.add(left_value if len(left_value) >= len(right_value) else right_value)
    return sorted(shared)


AFFECTED_TESTS = "tools/affected_tests.py"
# One resolver per graded tree, its parses cached: a cut asks it per item.
_AFFECTED_TOOLS = {}


def _affected_tool(tree):
    """The graded revision's own scope-to-shard resolver, or None.

    From the tree under test, the shards it names being that revision's.
    `tools/` is never installed and a repository may hold none, so the reading
    is skipped where it is absent -- in silence, every line printed here being
    one some filter selects on.
    """

    key = str(tree)
    if key in _AFFECTED_TOOLS:
        return _AFFECTED_TOOLS[key]
    _AFFECTED_TOOLS[key] = None
    path = Path(tree) / AFFECTED_TESTS
    spec = importlib.util.spec_from_file_location("cutcheck_affected", str(path)) if path.is_file() else None
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:  # a tree's own file, and no reading of a cut rests on it
        return None
    module.read_facts = functools.lru_cache(maxsize=None)(module.read_facts)
    _AFFECTED_TOOLS[key] = module
    return module


def _affected_modules(tree, scope):
    """The shard modules this write scope can be observed by, or None."""

    tool = _affected_tool(tree)
    try:
        return frozenset(tool.affected(list(scope), root=Path(tree))["modules"])
    except Exception:  # absent, unloadable, or unable to read this tree
        return None


def _decomposers(siblings):
    """Every id in this set whose executor is the decomposer."""

    return sorted(
        item_id
        for item_id, frontmatter in siblings.items()
        if str(frontmatter.get("executor") or "").strip() == ROOT_EXECUTOR
    )


def _root_ids(siblings):
    """Every id in this set whose executor and position make it a root ticket.

    The executor alone does not: a `<root>.NN` unit issued with it is a
    nested decomposition, which ``rules/topology.md`` §7 leaves undefined,
    and reading it as a root would grant it the root's exemption from
    families 4, 5 and 6 -- the honest layout's exemption sheltering the one
    shape it was never written for. A decomposer no other decomposer's id
    prefixes is a root, so a template's top-level stub stands as a root
    beside its siblings.
    """

    decomposers = _decomposers(siblings)
    return [
        item_id
        for item_id in decomposers
        if not any(
            other != item_id and item_id.startswith(other + ".")
            for other in decomposers
        )
    ]


def _gate_stub_of(ticket_id, roots):
    """The root this id is a gate stub of, or None.

    Anchored to a root the set actually holds, never to the infix alone: a
    unit ticket may be named anything, and the gate stubs are the ones one of
    these roots owns.
    """

    for root in roots:
        if ticket_id.startswith(root + GATE_INFIX):
            return root
    return None


def _gate_owners(siblings):
    """The root ids whose gate stubs this set already carries.

    Read from the same marker ``tickets.py gate`` writes, not only from roots
    that remain readable in the set. A manually assembled second gate is a
    defect even where its root ticket is missing or malformed.
    """

    return sorted(
        {
            ticket_id.split(GATE_ID_MARKER, 1)[0]
            for ticket_id in siblings
            if GATE_ID_MARKER in ticket_id
        }
    )


def _staged_template_roots(roots, siblings):
    """Whether several decomposers are stages of one top-level template.

    Canonical templates intentionally contain more than one decomposer, but
    each later one is downstream of an earlier one.  Two unrelated
    decomposers are two physical roots, the prohibited ad-hoc shape.
    """

    if len(roots) < 2:
        return False
    root_set = set(roots)
    first = [root for root in roots if not (_ancestors(root, siblings) & root_set)]
    return len(first) == 1 and all(
        root == first[0] or bool(_ancestors(root, siblings) & root_set)
        for root in roots
    )


def _gate_shape(root, siblings):
    """One detail when ``root`` does not own the canonical composite gate."""

    prefix = root + GATE_INFIX
    ids = sorted(ticket_id for ticket_id in siblings if ticket_id.startswith(prefix))
    critiques = [
        ticket_id for ticket_id in ids
        if ticket_id.startswith(prefix + "critique.")
    ]
    repair = root + ".gate.repair"
    verify = root + ".gate.verify"
    expected = set(critiques + [repair, verify])
    unknown = sorted(set(ids) - expected)
    if not critiques or repair not in siblings or verify not in siblings or unknown:
        return "expected one or more critiques, exactly one repair and one verify; got {}".format(
            ", ".join(ids) or "none"
        )
    units = _issued_under(siblings, root)
    wrong = []
    for ticket_id in critiques:
        item = siblings[ticket_id]
        if str(item.get("executor") or "").strip() != GATE_EXECUTORS["critique"]:
            wrong.append("{} executor".format(ticket_id))
        if sorted(_listed(item, "depends_on")) != sorted(units):
            wrong.append("{} dependencies".format(ticket_id))
    repair_item = siblings[repair]
    if str(repair_item.get("executor") or "").strip() != GATE_EXECUTORS["repair"]:
        wrong.append("{} executor".format(repair))
    if sorted(_listed(repair_item, "depends_on")) != critiques:
        wrong.append("{} dependencies".format(repair))
    verify_item = siblings[verify]
    if str(verify_item.get("executor") or "").strip() != GATE_EXECUTORS["verify"]:
        wrong.append("{} executor".format(verify))
    if _listed(verify_item, "depends_on") != [repair]:
        wrong.append("{} dependencies".format(verify))
    return ", ".join(wrong) if wrong else None


def _root_gate_layout(siblings):
    """Family 6: one root/gate system and one independence path per ticket.

    Runtime writers refuse each contradiction before writing it. Cutcheck
    reads the other ingress -- legacy or manually assembled ticket sets -- so
    those same shapes cannot become accepted merely because they already sit
    on disk. A root's ``checked_by`` remains the cut-reader record the
    work-item contract requires; only non-root gate-deferred tickets have no
    checker path.
    """

    findings = []
    roots = _root_ids(siblings)
    root_set = set(roots)
    gate_owners = _gate_owners(siblings)
    # Staged template decomposers remain lawful and carry no composite gate of
    # their own. Unrelated roots are prohibited even before either gate exists.
    if len(roots) > 1 and (gate_owners or not _staged_template_roots(roots, siblings)):
        findings.append(
            (
                roots[1],
                0,
                MULTIPLE_ROOTS,
                "one physical run has one root/gate system; found roots {}".format(
                    ", ".join(roots)
                ),
            )
        )
    if len(gate_owners) > 1:
        findings.append(
            (
                gate_owners[1],
                0,
                MULTIPLE_GATE_SYSTEMS,
                "one physical run has one composite gate; found owners {}".format(
                    ", ".join(gate_owners)
                ),
            )
        )
    for owner in gate_owners:
        if owner not in root_set:
            detail = "gate owner {} is not an orch-decompose root".format(owner)
        else:
            detail = _gate_shape(owner, siblings)
        if detail:
            findings.append((owner, 0, MALFORMED_GATE, detail))
    for ticket_id in sorted(siblings):
        frontmatter = siblings[ticket_id]
        independence = str(frontmatter.get("independence") or "checker").strip()
        checked_by = str(frontmatter.get(CHECKED_BY_KEY) or "").strip()
        if ticket_id not in root_set and independence == "gate" and checked_by:
            findings.append(
                (
                    ticket_id,
                    0,
                    MIXED_INDEPENDENCE,
                    "gate-deferred non-root ticket also carries checked_by {}".format(
                        checked_by
                    ),
                )
            )
    return findings


def _issued_items(siblings, roots):
    """The ids that are work items of this cut, root and gate stubs excepted.

    A root is the acceptance's source, so no criterion of the map it wrote
    names it; the gate stubs are named by the keyword ``gate``, never by id.
    Neither is a parallel work item either: a root does not run beside its own
    subtree, and a gate runs behind all of it, so the pairs family 4 asks
    about are the pairs among these ids. Grading either as an issued item
    fails every honest cut in the layout the work-item contract requires.
    """

    return [
        item_id
        for item_id in sorted(siblings)
        if item_id not in roots and _gate_stub_of(item_id, roots) is None
    ]


def _pairwise(siblings, reads, region_prover=None, tree=None):
    """Family 4: the pairs the DAG leaves free to run at the same time.

    Ordering is reachability, not adjacency -- a pair joined through a third
    item is staged, and staging is what makes a shared path safe. For every
    unordered pair the write scopes must be disjoint and neither item's oracle
    may read what the other writes, or the first result to land invalidates the
    second's evidence.

    Given a tree, one more reading of the same pair, and advisory: two scopes
    sharing no file may still be graded by one shard, so whichever lands first
    decides what the other's regression read. Never counted: the resolver
    over-approximates on purpose.

    ``region_prover`` is accepted and ignored. `ownership_regions` once
    bought an exemption from the collision above, behind a prover this
    function's only production caller never passed and no adapter ever
    supplied -- so a flawless region pair could draw one verdict,
    `region-proof-failed`. A refusal dressed as a proof is worse than the
    refusal, and a prover that admitted on selector shape alone would be
    worse than both, so the exemption is gone: sharing an artifact is
    collision again, and same-artifact work orders its dependencies or
    takes a sole owner. Restoring it means a resolver that reads the
    artifact at the pinned identity, and this caller handing one over.
    """

    findings = []
    ids = _issued_items(siblings, _root_ids(siblings))
    ancestors = {item: _ancestors(item, siblings) for item in ids}
    shards = {}
    for index, left in enumerate(ids):
        for right in ids[index + 1:]:
            if right in ancestors[left] or left in ancestors[right]:
                continue
            scopes = {
                item: _listed(siblings[item], "write_scope") for item in (left, right)
            }
            for shared in _shared_artifacts(scopes[left], scopes[right]):
                findings.append(
                    (left, 0, SCOPE_COLLISION, "with {}: {}".format(right, shared))
                )
            for reader, writer in ((left, right), (right, left)):
                path = _first_overlap(reads.get(reader) or [], scopes[writer])
                if path is not None:
                    findings.append(
                        (
                            reader,
                            0,
                            STAGED_INVALIDATION,
                            "with {}: {}".format(writer, path),
                        )
                    )
            if tree is None:
                continue
            for item in (left, right):
                if item not in shards:
                    shards[item] = _affected_modules(tree, scopes[item]) or frozenset()
            both = sorted(shards[left] & shards[right])
            if both:
                detail = "with {}: {}".format(right, ", ".join(both))
                findings.append((left, 0, SHARED_TEST_MODULE, detail))
    return findings


def _levels(siblings, ids):
    """Each issued item's level, and the ids no level resolves for.

    Level 1 is an item depending on nothing inside the set; every other item's
    level is one past the greatest level among its ``depends_on`` here. Only
    edges inside the set count, because an id naming something this cut does
    not hold orders nothing in it.

    An item whose dependencies never all resolve is inside a ``depends_on``
    cycle or behind one. It is returned unresolved and named in the reading
    rather than raised: a cut this tool cannot order is a fact about the cut,
    and a reader who asked for a shape gets the shape and the reason the rest
    of it is missing. Raising would take the whole report -- findings included
    -- down with the one set that most needs reading.
    """

    deps = {item: [d for d in _listed(siblings[item], "depends_on") if d in ids]
            for item in ids}
    level = {}
    pending = list(ids)
    while pending:
        ready = [item for item in pending if all(d in level for d in deps[item])]
        if not ready:
            break
        for item in ready:
            level[item] = 1 + max([level[d] for d in deps[item]] or [0])
        pending = [item for item in pending if item not in level]
    return level, deps, sorted(pending)


def _critical_path(level, deps):
    """The longest ``depends_on`` chain, read back from its deepest item.

    Every dependency of a levelled item is levelled, and an item's level is one
    past the greatest of theirs, so stepping to the deepest dependency at each
    hop walks a chain as long as the level says it is. Ties are broken on the
    id so that one cut reads the same twice: the chain is a reading a decomposer
    compares between revisions, and an arbitrary tie would make it move on its
    own.
    """

    if not level:
        return []
    node = max(sorted(level), key=lambda item: level[item])
    chain = [node]
    while deps[node]:
        node = max(sorted(deps[node]), key=lambda item: level[item])
        chain.append(node)
    chain.reverse()
    return chain


def _graph_reading(run, siblings):
    """The cut's shape: how deep it is, and how wide at each level.

    Against the run rather than any ticket, because neither reading is a
    property of one item -- the chain is the run's length in dispatches and the
    widths are what each frontier asks of the host at once. Over the issued
    items alone, for the reason `_issued_items` gives: a root does not run
    beside its own subtree and a gate runs behind all of it, so counting either
    would report a shape no frontier ever executes.

    A set with no issued item is read as nothing at all rather than as a shape
    of zero: there is no cut there to have one.
    """

    ids = _issued_items(siblings, _root_ids(siblings))
    if not ids:
        return []
    level, deps, cycled = _levels(siblings, ids)
    chain = _critical_path(level, deps)
    detail = "{}: {}".format(len(chain), " > ".join(chain)) if chain else "0"
    if cycled:
        detail += "; cycle: {}".format(", ".join(cycled))
    deepest = max(level.values()) if level else 0
    widths = [
        sum(1 for item in level if level[item] == depth)
        for depth in range(1, deepest + 1)
    ]
    return [
        (run, 0, CRITICAL_PATH, detail),
        # `0` where nothing resolved: every item is in a cycle or behind one,
        # and the chain's line names which.
        (run, 0, LEVEL_WIDTH, " ".join(str(width) for width in widths) or "0"),
    ]

__all__ = (
    '_affected_tool', '_affected_modules',
    '_oracle_reads', '_ancestors', '_first_overlap', '_decomposers',
    '_root_ids', '_gate_stub_of', '_gate_owners', '_staged_template_roots',
    '_gate_shape', '_root_gate_layout', '_issued_items', '_pairwise',
    '_levels', '_critical_path', '_graph_reading',
)
