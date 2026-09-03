"""Dependency and session graph layout."""

from __future__ import annotations

from reader.scripts.ui_model import *
from reader.scripts.ui_discovery import discover_sessions
from reader.scripts.ui_sessions import *


# What the layout cannot honour it names. Both shapes occur on real data:
# nothing on the write path proves a `depends_on` set is acyclic, and a
# ticket copied between runs keeps a `depends_on` its new run cannot resolve.
DIAGNOSTIC_CYCLE = "dependency cycle"
DIAGNOSTIC_DANGLING = "depends_on names no ticket in this run"


def layout_key(node_ids, edges) -> tuple:
    """The node-and-edge set, normalized, and nothing else."""

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
    """``(edges with every back arc withheld, one diagnostic per cycle)``."""

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
    dependency graph."""

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



# A second data source, and a far more dangerous one than the sink: a
# transcript holds the operator's prompts, the contents of the files they
# opened and the output of the commands they ran, for every project on the
# machine. The spec's `binding_constraints` close the renderable set to
# labels and structure, so the reader below parses *for* the two record types
# it renders and drops every other line before anything is taken from it --
# there is no render-time filter to get wrong.
#
# The layout is an undocumented implementation detail of another program,
# not a contract, so every field access degrades to a named diagnostic.

def agent_ids(agents) -> frozenset:
    """The nodes a recorded parent is allowed to resolve to: the session's
    own subagents, and not the orchestrator, which no metadata names."""

    return frozenset(agent["id"] for agent in agents)


def _recorded_parent(agent: dict, known: frozenset) -> str:
    """The node one subagent's own ``parentAgentId`` resolves to, or ``""``."""

    for candidate in (agent["parent"], "agent-" + agent["parent"]):
        if agent["parent"] and candidate in known and candidate != agent["id"]:
            return candidate
    return ""


def _agent_parent(agent: dict, known: frozenset) -> str:
    """The node one subagent hangs off, or ``""`` when nothing says."""

    if agent["depth"] == 1:
        return ORCHESTRATOR_NODE
    return _recorded_parent(agent, known)


def session_graph(agents) -> tuple:
    """``(node ids, edges, the subset of edges that is inferred)``."""

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
    """What one subagent's edge was read off, said on its own row."""

    parent = _agent_parent(agent, known)
    if parent == ORCHESTRATOR_NODE:
        return EDGE_FROM_DEPTH
    if parent:
        return EDGE_FROM_PARENT
    return EDGE_PARENT_UNRESOLVED if agent["parent"] else EDGE_INFERRED
