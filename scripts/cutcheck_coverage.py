"""Read and grade cut coverage maps."""

try:  # repository checkout
    from scripts import cutcheck_contract as _contract
except ImportError:  # installed flat script directory
    import cutcheck_contract as _contract
CANARY_DIR = _contract.CANARY_DIR
COVERAGE_FILE = _contract.COVERAGE_FILE
COVERAGE_MAP_ABSENT = _contract.COVERAGE_MAP_ABSENT
COVERAGE_OWNERS = _contract.COVERAGE_OWNERS
COVERAGE_SUFFIX = _contract.COVERAGE_SUFFIX
GATE_PREFIX_SEPARATOR = _contract.GATE_PREFIX_SEPARATOR
ORPHAN_CRITERION = _contract.ORPHAN_CRITERION
ORPHAN_ITEM = _contract.ORPHAN_ITEM
PRE_EXISTING = _contract.PRE_EXISTING
Path = _contract.Path
RUNS_DIR = _contract.RUNS_DIR
TICKETS_DIR = _contract.TICKETS_DIR
UNCOVERED_GATE_CRITERION = _contract.UNCOVERED_GATE_CRITERION

try:  # repository checkout
    from scripts import cutcheck_commands as _commands
except ImportError:  # installed flat script directory
    import cutcheck_commands as _commands
_criteria = _commands._criteria
_stated_provenance = _commands._stated_provenance

try:  # repository checkout
    from scripts import cutcheck_graph as _graph
except ImportError:  # installed flat script directory
    import cutcheck_graph as _graph
_gate_stub_of = _graph._gate_stub_of
_issued_items = _graph._issued_items
_root_ids = _graph._root_ids

def _coverage_path(run_dir, name=COVERAGE_FILE):
    """Where the acceptance-coverage map lives for a resolved ticket root.

    The map is found beside the root cutcheck already resolved, never at one
    fixed path: a run keeps it with its worklog, a fixture set carries its own
    beside its tickets, and the canary set has none to carry.
    """

    if run_dir.parent.name != TICKETS_DIR:
        return run_dir / name
    if run_dir.parent.parent.name == CANARY_DIR:
        return None
    return run_dir.parent.parent / RUNS_DIR / run_dir.name / name


def _map_for_root(run_dir, root, single: bool):
    """One root's map: ``<root>.coverage.md``, or the legacy single map.

    A run holds one map per root because it holds one cut per root. A
    template instantiates several top-level decomposers into one run, and
    one map for all of them means each root's criteria are read against
    every other root's items -- and the last decomposer to write overwrites
    what the others wrote.

    The legacy ``coverage.md`` is still read where it still means what it
    said: one root, and no map of its own.
    """

    path = _coverage_path(run_dir, root + COVERAGE_SUFFIX)
    if path is not None and path.is_file():
        return path
    legacy = _coverage_path(run_dir, COVERAGE_FILE)
    if single and legacy is not None and legacy.is_file():
        return legacy
    return path


def _issued_under(siblings, root):
    """The ids of one root's cut: ``<root>.NN``, its gate stubs excepted.

    Never a sibling top-level stub. A template's stubs are the template's
    graph, not any one root's decomposition, so grading them against a
    root's map convicts every honest template of orphaning the items it
    never issued.
    """

    prefix = root + GATE_PREFIX_SEPARATOR
    return [
        item_id
        for item_id in sorted(siblings)
        if item_id.startswith(prefix) and _gate_stub_of(item_id, [root]) is None
    ]


def _coverage_rows(path):
    """Each ``| criterion | owner |`` row: a number, and what answers for it."""

    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].isdigit():
            rows.append((int(cells[0]), cells[1]))
    return rows


def _relative(path, roots):
    """A path named the way every other line names one: from its root.

    Always with forward slashes, never the host separator. Every other path in
    a report comes from a ticket, where it is written posix-style, and a reader
    diffing one line against another must not see two spellings of one path.
    On Windows ``str()`` here emitted ``tests\\fixtures\\...`` and every
    recorded verdict missed.
    """

    for root in roots:
        if root is None:
            continue
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            continue
    return Path(path).as_posix()


def _coverage_findings(run, run_dir, siblings, roots):
    """Family 5, once per root the set holds.

    A run with no decomposer at all has one issued set and one map, which is
    what it always had. A run with roots has one of each per root.
    """

    root_ids = _root_ids(siblings)
    if not root_ids:
        return _coverage(
            run, _coverage_path(run_dir), _issued_items(siblings, []), roots,
            siblings=siblings,
        )
    findings = []
    single = len(root_ids) == 1
    for root in root_ids:
        findings.extend(
            _coverage(
                root if not single else run,
                _map_for_root(run_dir, root, single),
                _issued_under(siblings, root),
                roots,
                siblings=siblings,
                root=root,
            )
        )
    return findings


def _gate_independence_findings(run, rows, issued, siblings, root):
    """Gate-deferred units whose authored acceptance is absent at the root."""

    if not siblings or not root or root not in siblings:
        return []
    root_criteria = dict(_criteria(siblings[root].get("__completion_test") or ""))
    findings = []
    for item_id in issued:
        item = siblings.get(item_id) or {}
        if str(item.get("independence") or "checker").strip() != "gate":
            continue
        authored = [
            number
            for number, criterion in _criteria(item.get("__completion_test") or "")
            if _stated_provenance(criterion) != PRE_EXISTING
        ]
        if not authored:
            continue
        covered = [
            number
            for number, owner in rows
            if owner == item_id and number in root_criteria
        ]
        missing = authored[len(covered):]
        if missing:
            findings.append((
                item_id,
                missing[0],
                UNCOVERED_GATE_CRITERION,
                "independence gate leaves authored-here criteria {} absent from "
                "the root acceptance rows owned by this item".format(
                    ", ".join(str(number) for number in missing)
                ),
            ))
    return findings


def _coverage(run, path, issued, roots, siblings=None, root=None):
    """Family 5: the map and the issued set answer for each other, both ways.

    A criterion reaches an item, the gate, or declared remainder; an item is
    named by some criterion. With no map there is nothing to read either
    direction against, so the absence is the only thing reported.
    """

    if path is None or not path.is_file():
        where = (
            _relative(path, roots) if path is not None else "none for this ticket root"
        )
        return [(run, 0, COVERAGE_MAP_ABSENT, where)]
    findings = []
    owned = set()
    rows = _coverage_rows(path)
    for number, owner in rows:
        if owner in COVERAGE_OWNERS:
            continue
        if owner in issued:
            owned.add(owner)
            continue
        findings.append((run, number, ORPHAN_CRITERION, owner))
    findings.extend(
        (item, 0, ORPHAN_ITEM, "named by no criterion in {}".format(path.name))
        for item in issued
        if item not in owned
    )
    findings.extend(
        _gate_independence_findings(run, rows, issued, siblings, root)
    )
    return findings

__all__ = (
    '_coverage_path', '_map_for_root', '_issued_under', '_coverage_rows',
    '_relative', '_coverage_findings', '_gate_independence_findings', '_coverage',
)
