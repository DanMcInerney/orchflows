"""Resolve pack cells and grade executor legality."""

try:  # repository checkout
    from scripts import cutcheck_contract as _contract
except ImportError:  # installed flat script directory
    import cutcheck_contract as _contract
GATE_STUB_EXECUTORS = _contract.GATE_STUB_EXECUTORS
ILLEGAL_EXECUTOR = _contract.ILLEGAL_EXECUTOR
PACKS_DIR = _contract.PACKS_DIR
PACK_CELL_RE = _contract.PACK_CELL_RE
PACK_NAME_RE = _contract.PACK_NAME_RE
Path = _contract.Path
ROOT_EXECUTOR = _contract.ROOT_EXECUTOR
SKILL_NAME_RE = _contract.SKILL_NAME_RE
state_root = _contract.state_root

try:  # repository checkout
    from scripts import cutcheck_graph as _graph
except ImportError:  # installed flat script directory
    import cutcheck_graph as _graph
_gate_stub_of = _graph._gate_stub_of
_root_ids = _graph._root_ids

try:  # repository checkout
    from scripts import cutcheck_state as _state
except ImportError:  # installed flat script directory
    import cutcheck_state as _state
_unread = _state._unread

def _pack_cells(pack, lib_root):
    """The skills a pack's ``executor`` and ``assembly`` cells name.

    Read from the orchflows library, never from the repository under test. A
    pack that library does not carry, or one whose cells name no skill, binds
    nothing here -- an assembly cell reading "none" is such a cell.
    """

    if lib_root is None or not PACK_NAME_RE.match(pack):
        return set()
    path = Path(lib_root) / PACKS_DIR / pack / "SKILL.md"
    if not path.is_file():
        return set()
    names = set()
    for row in PACK_CELL_RE.findall(path.read_text(encoding="utf-8", errors="replace")):
        names.update(SKILL_NAME_RE.findall(row))
    return names


def _lib_root(declared):
    """The orchflows library whose pack cells family 6 reads, or None.

    Never the target repository. A pack cell is a fact about orchflows and the
    tree under test is whatever repository the run's work lands in, so
    resolving cells against the invoking worktree meant that from any target
    carrying no ``packs/`` -- which is every target but the library's own
    checkout -- the cell set came back empty and family 6 had nothing left to
    grade. The check passed by finding nothing to check.

    ``--lib`` decides it when the caller names one. Otherwise the tree this
    script runs from, which is the library itself in a checkout of it, and
    failing that the install beside the resolved state sink, which is where
    ``install.py`` puts the packs on this host.
    """

    if declared:
        declared_root = Path(declared)
        if not (declared_root / PACKS_DIR).is_dir():
            # Honoured and reported: the caller named this library, so it is
            # the one read, and a library holding no pack cell is family 6
            # grading every executor against nothing.
            _unread("{}: no {}/ there, so family 6 grades nothing".format(
                declared_root, PACKS_DIR))
        return declared_root
    candidates = [Path(__file__).resolve().parent.parent]
    try:
        candidates.append(state_root.state_root().parent / "lib")
    except OSError:  # pragma: no cover - a home directory that will not resolve
        pass
    for candidate in candidates:
        if (candidate / PACKS_DIR).is_dir():
            return candidate
    _unread("no orchflows library found ({}), so family 6 grades nothing".format(
        ", ".join(str(candidate) for candidate in candidates)))
    return None


def _executor_legality(siblings, lib_root):
    """Family 6: an executor its pack's cells name.

    An item naming no pack has no cell to resolve against and is not graded
    here.

    A root ticket and a gate stub are graded against the library instead of
    against the pack. Their executors are structural -- the decomposer is what
    makes a root a root, and the gate's three are what ``tickets.py gate``
    writes -- so no pack's executor cell names them and none should have to.
    Graded against the cell they were all illegal, which failed a cut for
    carrying the shape the contract requires of it. A decomposer that is not
    a root -- an id inside another root's subtree -- gets neither grading and
    is reported here as a nested root.
    """

    findings = []
    cells = {}
    roots = _root_ids(siblings)
    for ticket_id in sorted(siblings):
        frontmatter = siblings[ticket_id]
        executor = str(frontmatter.get("executor") or "").strip()
        if not executor:
            continue
        if ticket_id in roots:
            continue
        if executor == ROOT_EXECUTOR:
            findings.append(
                (
                    ticket_id,
                    0,
                    ILLEGAL_EXECUTOR,
                    "{} here is a nested root: this id sits inside another "
                    "root's subtree, and mixed decomposition inside one graph "
                    "is undefined (rules/topology.md §7)".format(executor),
                )
            )
            continue
        if _gate_stub_of(ticket_id, roots) is not None:
            if executor not in GATE_STUB_EXECUTORS:
                findings.append(
                    (
                        ticket_id,
                        0,
                        ILLEGAL_EXECUTOR,
                        "{} is none of the gate's executors {}".format(
                            executor, sorted(GATE_STUB_EXECUTORS)
                        ),
                    )
                )
            continue
        pack = str(frontmatter.get("pack") or "").strip()
        if not pack:
            continue
        if pack not in cells:
            cells[pack] = _pack_cells(pack, lib_root)
        if cells[pack] and executor not in cells[pack]:
            findings.append(
                (
                    ticket_id,
                    0,
                    ILLEGAL_EXECUTOR,
                    "{} is neither {}'s executor cell nor its assembly cell".format(
                        executor, pack
                    ),
                )
            )
    return findings

__all__ = (
    '_pack_cells', '_lib_root', '_executor_legality',
)
