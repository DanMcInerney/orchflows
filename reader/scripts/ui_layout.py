"""Dependency and session graph layout."""

from __future__ import annotations

from reader.scripts.ui_model import *
from reader.scripts.ui_model import _facade_value
from reader.scripts.ui_discovery import discover_sessions
from reader.scripts.ui_sessions import *
from reader.scripts.ui_sessions import _make_room

LAYER_WIDTH = 4
NODE_WIDTH = 132
NODE_HEIGHT = 44
GAP_X = 24
GAP_Y = 52
MARGIN = 16

# Coordinates are integers, so "two calls return byte-equal coordinates" is
# a fact about the layout rather than about float formatting.
LayoutNode = namedtuple("LayoutNode", ("id", "layer", "order", "x", "y"))

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


def _predecessors(node_ids, edges) -> dict:
    """``{node: sorted dependencies}``, every node present."""

    preds = dict((node, set()) for node in node_ids)
    for source, target in edges:
        preds[target].add(source)
    return dict((node, sorted(values)) for node, values in preds.items())


def _coffman_graham_order(node_ids, preds) -> list:
    """Coffman-Graham phase 1: label each node only once every predecessor
    carries a label, taking the candidate whose predecessor labels are
    lexicographically smallest. The tie-break on the id is load-bearing --
    without it the whole layout depends on iteration order."""

    labels = {}
    order = []
    remaining = list(node_ids)
    while remaining:
        best = None
        for node in remaining:
            if any(p not in labels for p in preds[node]):
                continue
            key = (sorted((labels[p] for p in preds[node]), reverse=True), node)
            if best is None or key < best:
                best = key
        if best is None:
            # No candidate means a cycle reached this far. Unreachable once
            # `_break_cycles` has run; kept so a caller that skipped it
            # degrades to input order rather than looping forever.
            order.extend(remaining)
            break
        labels[best[1]] = len(labels)
        order.append(best[1])
        remaining.remove(best[1])
    return order


def _layer_assignment(order, preds, width) -> dict:
    """Coffman-Graham phase 2: each node lands on the lowest layer that is
    strictly above every predecessor's and is not already full. Every edge
    is therefore upward by construction, not by a later repair pass."""

    layers = {}
    occupancy = {}
    for node in order:
        layer = max((layers[p] + 1 for p in preds[node] if p in layers), default=0)
        while occupancy.get(layer, 0) >= width:
            layer += 1
        layers[node] = layer
        occupancy[layer] = occupancy.get(layer, 0) + 1
    return layers


def _barycenter(node, preds, placed) -> Fraction:
    """The mean position of a node's already-placed predecessors, exactly.
    A float mean sorts the same today and is one rounding change away from
    not doing so. A node with no placed predecessor floats left."""

    positions = [placed[p] for p in preds[node] if p in placed]
    if not positions:
        return Fraction(-1)
    return Fraction(sum(positions), len(positions))


def _within_layer_order(node_ids, layers, preds) -> dict:
    """One barycenter sweep down the layers. Crossing reduction is one of
    the two things dagre buys over Argo's hand-rolled layout, and one sweep
    is most of it at this size; ties break on the id."""

    members = {}
    for node in node_ids:
        members.setdefault(layers[node], []).append(node)
    placed = {}
    for layer in sorted(members):
        ordered = sorted(
            members[layer], key=lambda node: (_barycenter(node, preds, placed), node)
        )
        for index, node in enumerate(ordered):
            placed[node] = index
    return placed


def graph_layout(node_ids, edges) -> dict:
    """Coordinates for one run's dependency graph.

    ``edges`` run from a dependency to the ticket that declares it, so an
    edge always points up the layers. Returns ``nodes``, the ``edges``
    actually drawn, any ``diagnostics``, and the canvas size.

    O(V^2 log V + E) -- the Coffman-Graham labelling is the quadratic term,
    which at 3-12 tickets is a few hundred comparisons.
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
    preds = _predecessors(ids, kept)
    order = _coffman_graham_order(ids, preds)
    layers = _layer_assignment(order, preds, LAYER_WIDTH)
    placed = _within_layer_order(ids, layers, preds)
    nodes = [
        LayoutNode(
            node,
            layers[node],
            placed[node],
            MARGIN + placed[node] * (NODE_WIDTH + GAP_X),
            MARGIN + layers[node] * (NODE_HEIGHT + GAP_Y),
        )
        for node in ids
    ]
    columns = max((node.order for node in nodes), default=-1) + 1
    rows = max((node.layer for node in nodes), default=-1) + 1
    return {
        "nodes": nodes,
        "edges": list(kept),
        "diagnostics": diagnostics,
        "width": MARGIN * 2 + columns * NODE_WIDTH + max(columns - 1, 0) * GAP_X,
        "height": MARGIN * 2 + rows * NODE_HEIGHT + max(rows - 1, 0) * GAP_Y,
    }


LAYOUT_CACHE = {}
LAYOUT_CACHE_LIMIT = 32


def cached_layout(node_ids, edges) -> dict:
    """``graph_layout`` memoized on the node-and-edge set alone.

    Status is deliberately absent from the key: a poll that repaints a
    ticket from claimed to complete moved no node, so it must not pay for
    a layout.
    """

    key = layout_key(node_ids, edges)
    layout = LAYOUT_CACHE.get(key)
    if layout is None:
        layout = _facade_value("graph_layout", graph_layout)(node_ids, edges)
        _make_room(LAYOUT_CACHE, LAYOUT_CACHE_LIMIT)
        LAYOUT_CACHE[key] = layout
    return layout


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


def transcript_state(transcripts=None) -> tuple:
    """The stat identity of everything the session views read.

    The same three facts per file the sink walk contributes, over the
    set this reader actually opens -- and the project directory names, so a
    directory appearing empty is a change too. Naming the validator's basis
    as the route's whole read set, rather than one directory, is `U3`'s
    lesson from the friction feed.
    """

    found = _facade_value("discover_sessions", discover_sessions)(transcripts)
    # Configured or not, and present or not, before any file: three pages
    # differ here -- no root configured, a root that is not there yet, and a
    # root holding nothing -- and none of the three has a file to stat, so a
    # walk alone cannot tell them apart. The middle-to-last transition is the
    # ordinary one: a viewer left open from before Claude Code first ran.
    root = found["root"]
    state = [("transcripts", int(found["present"]), "" if root is None else str(root))]
    state.extend(("projects", 0, name) for name in found["projects"])
    for session in found["sessions"]:
        state.append(session["identity"])
        state.extend(session["subagents"])
    # A file that is not a session still renders: it renders a diagnostic.
    # No directory is stat'd on this walk, so without these the row-shaped
    # hole in the page appears and disappears under an unchanged tag.
    state.extend(found["unaddressable"])
    return tuple(state)


# --- rendering ---------------------------------------------------------------


def render_graph_svg(run: str, tickets, layout: dict) -> str:
    """The dependency graph as inline SVG at natural size inside a
    scrollable box. No canvas and no pan/zoom: at 3-12 nodes both are
    machinery with no keyboard path (`lane-ui-patterns.md` §3.2)."""

    at = dict((node.id, node) for node in layout["nodes"])
    state = dict((ticket["id"], ticket["status"]) for ticket in tickets)
    parts = [
        '<div class="canvas">\n<svg class="graph" viewBox="0 0 {width} {height}" '
        'width="{width}" height="{height}" role="img" '
        'aria-label="dependency graph for {run}">\n'.format(
            width=layout["width"], height=layout["height"], run=html.escape(run)
        ),
        '<defs><marker id="dep-arrow" viewBox="0 0 8 8" refX="8" refY="4" '
        'markerWidth="6" markerHeight="6" orient="auto">'
        '<path class="arrow" d="M0 0 L8 4 L0 8 z" /></marker></defs>\n',
    ]
    for source, target in layout["edges"]:
        tail, head = at[source], at[target]
        parts.append(
            '<line class="edge" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            'marker-end="url(#dep-arrow)" />\n'.format(
                x1=tail.x + NODE_WIDTH // 2,
                y1=tail.y + NODE_HEIGHT,
                x2=head.x + NODE_WIDTH // 2,
                y2=head.y,
            )
        )
    for node in layout["nodes"]:
        seen = status_presentation(state.get(node.id, ""))
        parts.append(
            '<a href="{href}"><g class="nd nd-{word}" transform="translate({x},{y})">'
            '<rect width="{w}" height="{h}" rx="5" />'
            '<text class="nd-id" x="10" y="19">{id}</text>'
            '<text class="nd-state" x="10" y="35">{glyph} {word}</text>'
            "</g></a>\n".format(
                href=_facade_value("ticket_href", None)(run, node.id),
                word=seen.word,
                glyph=seen.glyph,
                x=node.x,
                y=node.y,
                w=NODE_WIDTH,
                h=NODE_HEIGHT,
                id=html.escape(node.id),
            )
        )
    parts.append("</svg>\n</div>\n")
    return "".join(parts)
