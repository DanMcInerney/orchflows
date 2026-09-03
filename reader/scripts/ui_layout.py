"""Dependency and session graph layout."""

from __future__ import annotations

from reader.scripts.ui_model import *
from reader.scripts.ui_discovery import discover_sessions
from reader.scripts.ui_sessions import *


# What the layout cannot honour it names. Both shapes occur on real data:
# nothing on the write path proves a `depends_on` set is acyclic, and a
# ticket copied between runs keeps a `depends_on` its new run cannot
# resolve.
DIAGNOSTIC_CYCLE = "dependency cycle"
DIAGNOSTIC_DANGLING = "depends_on names no ticket in this run"


def layout_key(node_ids, edges) -> tuple:
    """The node-and-edge set, normalized, and nothing else.

    Nothing derived from a ticket's *state* may reach this key: re-laying
    out a graph on a refresh that moved no node is the live defect
    `lane-ui-patterns.md` §6(3) records in Argo, whose own fix sits in the
    source commented out. Sorting here is also what makes the layout
    independent of the order the tickets happened to be read in.
    """

    return (tuple(sorted(set(node_ids))), tuple(sorted(set(edges))))


def _rotated(cycle) -> list:
    """A reported cycle restated from its lexicographically smallest node,
    so the diagnostic reads the same however the detector entered it."""

    ring = list(cycle[:-1]) if len(cycle) > 1 and cycle[0] == cycle[-1] else list(cycle)
    if not ring:
        return []
    start = ring.index(min(ring))
    ring = ring[start:] + ring[:start]
    return ring + [ring[0]]


def _break_cycles(node_ids, edges) -> tuple:
    """``(edges with every back arc withheld, one diagnostic per cycle)``.

    ``graphlib.TopologicalSorter`` exists at the 3.9 floor and reports the
    offending nodes rather than leaving them to be guessed. Only an arc the
    detector itself named is withheld, so each pass makes progress; the
    loop is bounded by the edge count, so the pathological set costs time
    and never the process.
    """

    kept = list(edges)
    diagnostics = []
    for _ in range(len(edges) + 1):
        sorter = graphlib.TopologicalSorter()
        for node in node_ids:
            sorter.add(node)
        for source, target in kept:
            sorter.add(target, source)
        try:
            sorter.prepare()
            return kept, diagnostics
        except graphlib.CycleError as error:
            ring = _rotated(list(error.args[1]))
            arcs = set()
            for index in range(len(ring) - 1):
                arcs.add((ring[index], ring[index + 1]))
                arcs.add((ring[index + 1], ring[index]))
            droppable = sorted(arc for arc in arcs if arc in kept)
            if not droppable:
                break
            kept.remove(droppable[0])
            diagnostics.append(
                "{0}: {1}; edge {2} -> {3} not drawn".format(
                    DIAGNOSTIC_CYCLE,
                    " -> ".join(ring),
                    droppable[0][0],
                    droppable[0][1],
                )
            )
    return kept, diagnostics


def graph_layout(node_ids, edges) -> dict:
    """The edges actually drawn and any diagnostics, for one run's
    dependency graph.

    ``edges`` run from a dependency to the ticket that declares it. Node
    position is a browser-side concern (``layout.worker.ts``,
    ``elk.worker.ts``): this seam states which edges survive cycle- and
    dangling-breaking and why, and nothing about where a node sits.
    """

    ids, given = layout_key(node_ids, edges)
    known = set(ids)
    diagnostics = []
    missing = sorted({end for edge in given for end in edge} - known)
    if missing:
        diagnostics.append("{0}: {1}".format(DIAGNOSTIC_DANGLING, ", ".join(missing)))
    kept, cycles = _break_cycles(
        ids, [edge for edge in given if edge[0] in known and edge[1] in known]
    )
    diagnostics.extend(cycles)
    return {"edges": list(kept), "diagnostics": diagnostics}


# --- Claude Code sessions -----------------------------------------------------

# A second data source, and a far more dangerous one than the sink. A
# transcript holds the operator's prompts, the contents of the files they
# opened and the output of the commands they ran, for every project on the
# machine. The spec's `binding_constraints` close the renderable set to
# labels and structure: ``sessionId``, ``aiTitle``, the ``worktree-state``
# fields, timestamps, sizes, counts, and a subagent's own metadata. So the
# reader below parses *for* the two record types it renders and drops every
# other line before anything is taken from it -- there is no render-time
# filter to get wrong, because nothing else is ever held.
#
# The layout is an undocumented implementation detail of another program,
# not a contract. Every field access degrades to a named diagnostic, so a
# Claude Code release that moves a key produces a visibly degraded page
# rather than a traceback or a silently empty one that looks correct.

def agent_ids(agents) -> frozenset:
    """The nodes a recorded parent is allowed to resolve to: the session's
    own subagents, and not the orchestrator, which no metadata names."""

    return frozenset(agent["id"] for agent in agents)


def _recorded_parent(agent: dict, known: frozenset) -> str:
    """The node one subagent's own ``parentAgentId`` resolves to, or ``""``.

    ``parentAgentId`` was observed on every depth-2 record and no depth-1
    one, holding the bare id whose file is ``agent-<id>``; both spellings
    are accepted because neither is anybody's contract. A pointer to an
    agent this session does not have, or to the agent itself, resolves to
    nothing rather than to a node that is not there or an edge nobody can
    lay out.
    """

    for candidate in (agent["parent"], "agent-" + agent["parent"]):
        if agent["parent"] and candidate in known and candidate != agent["id"]:
            return candidate
    return ""


def _agent_parent(agent: dict, known: frozenset) -> str:
    """The node one subagent hangs off, or ``""`` when nothing says.

    Depth 1 is read before the pointer and outranks it: the session spawned
    it and nothing else could have, so spec criterion 8's edge from the
    orchestrator to *every* depth-1 agent holds even where the metadata also
    names a sibling. Ordering the two the other way makes that criterion
    hold only for the records that happen to omit the key.
    """

    if agent["depth"] == 1:
        return ORCHESTRATOR_NODE
    return _recorded_parent(agent, known)


def session_graph(agents) -> tuple:
    """``(node ids, edges, the subset of edges that is inferred)``.

    The orchestrator is the session itself. A subagent at depth 1 was
    spawned by it and nothing else could have been; a recorded parent that
    resolves to a node on this page is a fact. Everything left over -- a
    subagent that names no parent, and one whose named parent is not on this
    page -- hangs off the orchestrator too, and that edge is returned as a
    guess so the page can draw it as one. Inventing a parent for it would be
    the one lie a flowchart of another program's tree must not tell. Which
    of the two guesses was made is `edge_source`'s to say; the shape here is
    the same either way.
    """

    nodes = (ORCHESTRATOR_NODE,) + tuple(agent["id"] for agent in agents)
    known = agent_ids(agents)
    edges, inferred = [], []
    for agent in agents:
        parent = _agent_parent(agent, known)
        edges.append((parent or ORCHESTRATOR_NODE, agent["id"]))
        if not parent:
            inferred.append(edges[-1])
    return nodes, tuple(edges), tuple(inferred)


def edge_source(agent: dict, known: frozenset) -> str:
    """What one subagent's edge was read off, said on its own row.

    Two of the four are guesses and they are not the same guess. A record
    that never named a parent and a record whose named parent is on no other
    row here both land on the orchestrator; calling the second the first is
    a false statement about another program's data, and the reader it
    misleads goes looking for a pointer that was written down all along.
    """

    parent = _agent_parent(agent, known)
    if parent == ORCHESTRATOR_NODE:
        return EDGE_FROM_DEPTH
    if parent:
        return EDGE_FROM_PARENT
    return EDGE_PARENT_UNRESOLVED if agent["parent"] else EDGE_INFERRED
