"""Mermaid source lint and rendered-SVG geometry checks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from visual_fences import Diagram, _normalize_newlines, _source_lines, make_failure

NODE_DEF_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?P<id>[A-Za-z][A-Za-z0-9_-]*)"
    r"(?:\[(?P<l1>[^\]\n]*)\]|\((?P<l2>[^)\n]*)\)|\{(?P<l3>[^}\n]*)\}|>(?P<l4>[^\]\n]*)\])"
)
ARROW_RE = re.compile(r"<?(?:-\.+-*|--+|==+)[ox>]?")
SUBGRAPH_RE = re.compile(r"^\s*subgraph\s+(?P<id>[A-Za-z0-9_-]+)")

def _frontmatter_span(lines: list[str]) -> int:
    """Number of leading lines occupied by a YAML frontmatter block
    (Mermaid per-diagram config such as `layout: elk`); 0 when absent."""

    if not lines or lines[0].strip() != "---":
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return index + 1
    return 0


def _diagram_type(diagram: Diagram) -> tuple[str, int]:
    """The diagram-type token and its line index, skipping frontmatter."""

    lines = _source_lines(diagram)
    start = _frontmatter_span(lines)
    if start:
        while start < len(lines) and not lines[start].strip():
            start += 1
    if start >= len(lines) or not lines[start].strip():
        return "", -1
    token_match = re.match(r"[A-Za-z0-9_-]+", lines[start].strip())
    return (token_match.group(0) if token_match else ""), start

def _mask_line(line: str) -> str:
    """Blank out quoted substrings and trailing %% comments, preserving length."""

    result = list(line)
    in_quote = False
    quote_char = ""
    index = 0
    length = len(line)
    while index < length:
        char = line[index]
        if in_quote:
            if char == quote_char:
                in_quote = False
            else:
                result[index] = " "
        elif char in ("\"", "'"):
            in_quote = True
            quote_char = char
        elif line[index : index + 2] == "%%":
            for j in range(index, length):
                result[j] = " "
            break
        index += 1
    return "".join(result)

# --- Legibility lint (--lint) ----------------------------------------------------

LINT_NODE_BUDGET = 31        # decompose above (Mendling 2012 error-probability threshold)
LINT_NODE_WARN = 25
LINT_OVERVIEW_BUDGET = 7     # staged pages: the first flow diagram is the overview
LINT_FAN_OUT_MAX = 4
LINT_LABEL_WORD_MAX = 5
LINT_CLASSDEF_MAX = 3
LINT_SUBGRAPH_DEPTH_MAX = 1
LINT_FORBIDDEN_TYPES = {"mindmap", "journey", "zenuml"}
FLOW_TYPES = {"flowchart", "graph"}
DIRECTION_RE = re.compile(r"^\s*direction\s+(?:TB|TD|BT|LR|RL)\b")
CLASSDEF_RE = re.compile(r"^\s*classDef\s")
NON_NODE_TOKENS = {
    "subgraph", "end", "direction", "classDef", "class", "style", "click",
    "linkStyle", "flowchart", "graph",
}


@dataclass
class FlowGraph:
    nodes: set[str] = field(default_factory=set)
    edges: list[tuple[str, str, bool, int]] = field(default_factory=list)
    decision_nodes: set[str] = field(default_factory=set)
    labels: dict[str, tuple[str, int]] = field(default_factory=dict)
    subgraphs: list[dict[str, object]] = field(default_factory=list)
    max_depth: int = 0
    classdef_count: int = 0


def _extract_flow_graph(diagram: Diagram) -> FlowGraph:
    """A best-effort node/edge model of a flowchart, from source text alone.

    Edge labels written dash-inline (`-- so -->`) are not modeled; the
    authoring contract mandates the `|so|` form this parser understands.
    """

    lines = _source_lines(diagram)
    masked = [_mask_line(line) for line in lines]
    graph = FlowGraph()
    stack: list[dict[str, object]] = []

    def note_node(node_id: str) -> None:
        if node_id in NON_NODE_TOKENS:
            return
        graph.nodes.add(node_id)
        for frame in stack:
            frame["members"].add(node_id)

    for line_index in range(_frontmatter_span(lines), len(lines)):
        raw, line = lines[line_index], masked[line_index]
        stripped = line.strip()
        if CLASSDEF_RE.match(line):
            graph.classdef_count += 1
            continue
        subgraph_match = SUBGRAPH_RE.match(line)
        if subgraph_match:
            frame: dict[str, object] = {
                "id": subgraph_match.group("id"),
                "line_index": line_index,
                "members": set(),
                "direction_line": None,
                "depth": len(stack) + 1,
            }
            stack.append(frame)
            graph.subgraphs.append(frame)
            graph.max_depth = max(graph.max_depth, len(stack))
            continue
        if stripped == "end" and stack:
            stack.pop()
            continue
        if DIRECTION_RE.match(line):
            if stack:
                stack[-1]["direction_line"] = line_index
            continue
        for match in NODE_DEF_RE.finditer(line):
            note_node(match.group("id"))
            if match.group("l3") is not None:
                graph.decision_nodes.add(match.group("id"))
        for match in NODE_DEF_RE.finditer(raw):
            node_id = match.group("id")
            label = next(
                (
                    group
                    for group in (
                        match.group("l1"),
                        match.group("l2"),
                        match.group("l3"),
                        match.group("l4"),
                    )
                    if group is not None
                ),
                "",
            ).strip().strip("\"'")
            if label and node_id not in graph.labels:
                graph.labels[node_id] = (label, line_index)
        segments = ARROW_RE.split(line)
        if len(segments) > 1:
            for segment_index in range(len(segments) - 1):
                left, right = segments[segment_index], segments[segment_index + 1]
                right_clean = re.sub(r"^\s*\|[^|\n]*\|", "", right)
                labeled = right_clean != right
                # Both sides may be `&`-lists (a & b --> c & d): every
                # combination is a real edge and counts toward fan-out.
                sources = []
                for part in left.split("&"):
                    src_match = re.search(
                        r"([A-Za-z][A-Za-z0-9_-]*)\s*"
                        r"(?:\[[^\]\n]*\]|\([^)\n]*\)|\{[^}\n]*\})?\s*$",
                        part,
                    )
                    if src_match:
                        sources.append(src_match.group(1))
                destinations = []
                for part in right_clean.split("&"):
                    dst_match = re.match(r"\s*([A-Za-z][A-Za-z0-9_-]*)", part)
                    if dst_match:
                        destinations.append(dst_match.group(1))
                for src in sources:
                    for dst in destinations:
                        if src in NON_NODE_TOKENS or dst in NON_NODE_TOKENS:
                            continue
                        note_node(src)
                        note_node(dst)
                        graph.edges.append((src, dst, labeled, line_index))
    return graph


def lint_diagram(diagram: Diagram) -> tuple[list[dict[str, object]], list[str]]:
    """Source-level legibility failures and advisory warnings for one diagram."""

    failures: list[dict[str, object]] = []
    warnings: list[str] = []
    token, token_line = _diagram_type(diagram)
    if token_line < 0:
        return failures, warnings
    if token.endswith("-beta") or token in LINT_FORBIDDEN_TYPES:
        failures.append(
            make_failure(
                diagram,
                token_line,
                f"lint: diagram type '{token}' is forbidden (beta or weak-layout); "
                "use a core type or a viz-html kit block",
                rule="lint_forbidden_type",
            )
        )
        return failures, warnings
    if token not in FLOW_TYPES:
        return failures, warnings

    graph = _extract_flow_graph(diagram)
    node_count = len(graph.nodes)
    if node_count > LINT_NODE_BUDGET:
        failures.append(
            make_failure(
                diagram,
                token_line,
                f"lint: {node_count} nodes exceed the {LINT_NODE_BUDGET}-node budget; "
                "split into an overview plus detail panels",
                rule="lint_node_budget",
            )
        )
    elif node_count > LINT_NODE_WARN:
        warnings.append(
            f"graph {diagram.index}: {node_count} nodes; target {LINT_NODE_WARN} or fewer"
        )

    out_degree: dict[str, int] = {}
    first_edge_line: dict[str, int] = {}
    for src, _dst, _labeled, line_index in graph.edges:
        out_degree[src] = out_degree.get(src, 0) + 1
        first_edge_line.setdefault(src, line_index)
    for src in sorted(out_degree):
        degree = out_degree[src]
        if degree > LINT_FAN_OUT_MAX:
            failures.append(
                make_failure(
                    diagram,
                    first_edge_line[src],
                    f"lint: node '{src}' fans out to {degree} nodes "
                    f"(max {LINT_FAN_OUT_MAX}); group targets or split",
                    rule="lint_fan_out",
                )
            )
        elif degree == LINT_FAN_OUT_MAX:
            warnings.append(f"graph {diagram.index}: node '{src}' fans out to {degree} nodes")

    if graph.max_depth > LINT_SUBGRAPH_DEPTH_MAX:
        deep = next(
            frame for frame in graph.subgraphs if frame["depth"] > LINT_SUBGRAPH_DEPTH_MAX
        )
        failures.append(
            make_failure(
                diagram,
                int(deep["line_index"]),
                f"lint: subgraph nesting depth {graph.max_depth} exceeds "
                f"{LINT_SUBGRAPH_DEPTH_MAX}; split sideways instead",
                rule="lint_subgraph_depth",
            )
        )

    for frame in graph.subgraphs:
        if frame["direction_line"] is None:
            continue
        members = frame["members"]
        if any((src in members) != (dst in members) for src, dst, _l, _i in graph.edges):
            failures.append(
                make_failure(
                    diagram,
                    int(frame["direction_line"]),
                    f"lint: 'direction' inside subgraph '{frame['id']}' is ignored "
                    "because a member links across its boundary",
                    rule="lint_direction_ignored",
                )
            )

    for src, _dst, labeled, line_index in graph.edges:
        if src in graph.decision_nodes and not labeled:
            failures.append(
                make_failure(
                    diagram,
                    line_index,
                    f"lint: unlabeled branch from decision node '{src}'; "
                    "label every decision exit with |so|",
                    rule="lint_decision_unlabeled",
                )
            )

    long_labels = [
        node_id
        for node_id, (label, _line) in sorted(graph.labels.items())
        if len(label.split()) > LINT_LABEL_WORD_MAX
    ]
    if long_labels:
        warnings.append(
            f"graph {diagram.index}: labels over {LINT_LABEL_WORD_MAX} words on: "
            + ", ".join(long_labels)
        )
    if graph.classdef_count > LINT_CLASSDEF_MAX:
        warnings.append(
            f"graph {diagram.index}: {graph.classdef_count} classDefs; "
            f"max {LINT_CLASSDEF_MAX}"
        )
    return failures, warnings


SVG_NS = "{http://www.w3.org/2000/svg}"
TRANSLATE_RE = re.compile(r"translate\(\s*(-?[\d.]+)[,\s]\s*(-?[\d.]+)\s*\)")


def geometry_failures(
    diagram: Diagram, svg_bytes: bytes, source_nodes: int = 0
) -> tuple[list[dict[str, object]], str | None]:
    """Node-overlap and viewBox-containment checks over a CLI-rendered SVG.

    Returns (failures, unchecked_reason). The reason names why the SVG
    could not be read — or, for a diagram whose source declares
    `source_nodes` nodes, why none of them was found positioned in it —
    so a page whose layout was never measured cannot be reported as one
    whose layout is clean."""

    try:
        import xml.etree.ElementTree as ElementTree

        root = ElementTree.fromstring(svg_bytes.decode("utf-8", errors="replace"))
        boxes: list[tuple[float, float, float, float]] = []
        for group in root.iter(f"{SVG_NS}g"):
            if "node" not in (group.get("class") or "").split():
                continue
            translate = TRANSLATE_RE.search(group.get("transform") or "")
            rect = group.find(f"{SVG_NS}rect")
            if translate is None or rect is None:
                continue
            boxes.append(
                (
                    float(translate.group(1)) + float(rect.get("x", "0")),
                    float(translate.group(2)) + float(rect.get("y", "0")),
                    float(rect.get("width", "0")),
                    float(rect.get("height", "0")),
                )
            )
        if source_nodes and not boxes:
            return [], (
                f"the SVG positions none of the {source_nodes} node(s) the "
                "source declares as g.node/rect boxes"
            )
        failures: list[dict[str, object]] = []
        overlaps = 0
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                ax, ay, aw, ah = boxes[i]
                bx, by, bw, bh = boxes[j]
                dx = min(ax + aw, bx + bw) - max(ax, bx)
                dy = min(ay + ah, by + bh) - max(ay, by)
                if dx > 1.0 and dy > 1.0:
                    overlaps += 1
        if overlaps:
            failures.append(
                make_failure(
                    diagram,
                    0,
                    f"lint: {overlaps} node pair(s) overlap in the rendered layout; "
                    "reduce density or split",
                    rule="lint_geometry_overlap",
                )
            )
        view_box = (root.get("viewBox") or "").replace(",", " ").split()
        if len(view_box) == 4:
            min_x, min_y, width, height = (float(part) for part in view_box)
            outside = sum(
                1
                for (x, y, w, h) in boxes
                if x < min_x - 1
                or y < min_y - 1
                or x + w > min_x + width + 1
                or y + h > min_y + height + 1
            )
            if outside:
                failures.append(
                    make_failure(
                        diagram,
                        0,
                        f"lint: {outside} node(s) fall outside the SVG viewBox",
                        rule="lint_geometry_overflow",
                    )
                )
        return failures, None
    except Exception as error:
        return [], f"{type(error).__name__}: {error}"
