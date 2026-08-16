#!/usr/bin/env python3
"""Verify the visual fences embedded in a Markdown page.

```mermaid fences are rendered by the pinned Mermaid CLI, which locates
syntax errors from its diagnostics. That CLI is the only judge of a
diagram: when npx is not found, or when the CLI runs and cannot judge
(timeout, spawn failure, no SVG written, a parse error it will not
locate), this exits 2 naming the cause in "message" or "tool_errors".
No diagram is ever reported as passing that a Mermaid parser did not
read.

```vega-lite fences are checked for valid JSON; ```viz-html fences for
balanced tags and absence of scripts.

--lint additionally enforces the legibility contract: a type gate on
every diagram (no `-beta`, mindmap, journey, zenuml), then flowchart
rules — node budget, fan-out, subgraph depth, `direction` in
externally-linked subgraphs, labeled decision branches — and
node-overlap and viewBox-containment geometry checks over the rendered
SVG, whose failure to run is a `lint.warnings` entry, never a silent
skip. On a staged page (two or more flow diagrams) the first flow
diagram is advised against the overview budget. A page with prose but
no visual fence passes as prose-only; an empty page is an error.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path


MERMAID_VERSION = "11.16.0"
MERMAID_PACKAGE = f"@mermaid-js/mermaid-cli@{MERMAID_VERSION}"
TIMEOUT_SECONDS = 120

ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
FENCE_RE = re.compile(
    r"^```mermaid[ \t]*\r?\n(?P<body>.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
VEGA_FENCE_RE = re.compile(
    r"^```vega-lite[ \t]*\r?\n(?P<body>.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
VIZ_HTML_FENCE_RE = re.compile(
    r"^```viz-html[ \t]*\r?\n(?P<body>.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
ERROR_LOCATION = re.compile(
    r"(?P<kind>Parse|Lexical|Lexer|Syntax) error on line\s+"
    r"(?P<line>\d+)(?:,\s*column\s+(?P<column>\d+))?",
    re.IGNORECASE,
)
EXPECTATION = re.compile(
    r"Expecting\s+(?P<expected>.+?),\s*got\s+['\"](?P<got>[^'\"]+)['\"]",
    re.IGNORECASE,
)
MERMAID_SYNTAX_ERROR = re.compile(
    r"(?:Parse|Lexical|Lexer|Syntax) error", re.IGNORECASE
)

NODE_DEF_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?P<id>[A-Za-z][A-Za-z0-9_-]*)"
    r"(?:\[(?P<l1>[^\]\n]*)\]|\((?P<l2>[^)\n]*)\)|\{(?P<l3>[^}\n]*)\}|>(?P<l4>[^\]\n]*)\])"
)
ARROW_RE = re.compile(r"<?(?:-\.+-*|--+|==+)[ox>]?")
SUBGRAPH_RE = re.compile(r"^\s*subgraph\s+(?P<id>[A-Za-z0-9_-]+)")


@dataclass(frozen=True)
class Diagram:
    index: int
    source: str
    source_start_line: int


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def extract_diagrams(text: str, fence_re: re.Pattern[str] = FENCE_RE) -> list[Diagram]:
    """Extract every matching fenced block, retaining its source-file line."""

    text = _normalize_newlines(text)
    diagrams: list[Diagram] = []
    for match in fence_re.finditer(text):
        source = match.group("body")
        source_start_line = text.count("\n", 0, match.start("body")) + 1
        diagrams.append(
            Diagram(
                index=len(diagrams) + 1,
                source=source,
                source_start_line=source_start_line,
            )
        )
    return diagrams


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


def _source_lines(diagram: Diagram) -> list[str]:
    return _normalize_newlines(diagram.source).splitlines()


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


def make_failure(
    diagram: Diagram,
    relative_line_index: int,
    message: str,
    *,
    rule: str | None = None,
    context_radius: int = 1,
) -> dict[str, object]:
    lines = _source_lines(diagram)
    context: list[dict[str, object]] = []
    for offset in range(
        max(0, relative_line_index - context_radius),
        min(len(lines), relative_line_index + context_radius + 1),
    ):
        context.append(
            {"line": diagram.source_start_line + offset, "text": lines[offset]}
        )
    failure: dict[str, object] = {
        "graph_index": diagram.index,
        "source_line": diagram.source_start_line + relative_line_index,
        "message": message,
        "context": context,
    }
    if rule is not None:
        failure["rule"] = rule
    return failure


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
    diagram: Diagram, svg_bytes: bytes
) -> tuple[list[dict[str, object]], str | None]:
    """Node-overlap and viewBox-containment checks over a CLI-rendered SVG.

    Returns (failures, unchecked_reason). The reason names why the SVG
    could not be read, so a page whose layout was never measured cannot
    be reported as one whose layout is clean."""

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


# --- Non-mermaid fences -----------------------------------------------------------

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "source", "track", "wbr",
}
SCRIPT_TAG_RE = re.compile(r"<\s*script\b", re.IGNORECASE)
INLINE_STYLE_RE = re.compile(r"\bstyle\s*=\s*[\"']", re.IGNORECASE)
EXTERNAL_REF_RE = re.compile(r"\b(?:src|href)\s*=\s*[\"'](?:https?:)?//", re.IGNORECASE)


class _TagBalance(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.problem: tuple[str, int] | None = None

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag not in VOID_TAGS:
            self.stack.append((tag, self.getpos()[0]))

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS or self.problem is not None:
            return
        if not self.stack or self.stack[-1][0] != tag:
            self.problem = (tag, self.getpos()[0])
        else:
            self.stack.pop()


def check_vega_fence(block: Diagram) -> dict[str, object] | None:
    try:
        json.loads(block.source)
    except json.JSONDecodeError as error:
        return {
            "fence": "vega-lite",
            "chart_index": block.index,
            "source_line": block.source_start_line + max(error.lineno - 1, 0),
            "message": f"vega-lite spec is not valid JSON: {error.msg}",
            "rule": "invalid_vega_json",
        }
    return None


def check_viz_html_fence(block: Diagram) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []

    def forbid(pattern: re.Pattern[str], message: str, rule: str) -> None:
        found = pattern.search(block.source)
        if found is not None:
            failures.append(
                {
                    "fence": "viz-html",
                    "component_index": block.index,
                    "source_line": block.source_start_line
                    + block.source[: found.start()].count("\n"),
                    "message": message,
                    "rule": rule,
                }
            )

    forbid(SCRIPT_TAG_RE, "viz-html fences never carry scripts", "viz_html_script")
    forbid(
        INLINE_STYLE_RE,
        "viz-html fences never carry inline styles; use the kit classes",
        "viz_html_inline_style",
    )
    forbid(
        EXTERNAL_REF_RE,
        "viz-html fences never reference external resources",
        "viz_html_external",
    )
    parser = _TagBalance()
    try:
        parser.feed(_normalize_newlines(block.source))
        parser.close()
    except Exception:
        pass  # html.parser is lenient; the stack below is the verdict
    if parser.problem is not None:
        tag, line = parser.problem
        failures.append(
            {
                "fence": "viz-html",
                "component_index": block.index,
                "source_line": block.source_start_line + line - 1,
                "message": f"viz-html markup unbalanced: unexpected </{tag}>",
                "rule": "unbalanced_html",
            }
        )
    elif parser.stack:
        tag, line = parser.stack[-1]
        failures.append(
            {
                "fence": "viz-html",
                "component_index": block.index,
                "source_line": block.source_start_line + line - 1,
                "message": f"viz-html markup unbalanced: unclosed <{tag}>",
                "rule": "unbalanced_html",
            }
        )
    return failures


# --- Mermaid CLI path ------------------------------------------------------------


def _jison_column(diagram: Diagram, diagram_line: int, past_display: str) -> int | None:
    """Map Jison's truncated pre-token display back to a source column."""

    source = _normalize_newlines(diagram.source)
    lines = source.splitlines()
    if not 1 <= diagram_line <= len(lines):
        return None

    line_start = 0
    for _ in range(1, diagram_line):
        newline = source.find("\n", line_start)
        if newline < 0:
            return None
        line_start = newline + 1

    candidates: list[int] = []
    truncated = past_display.startswith("...")
    displayed_tail = past_display[3:] if truncated else past_display
    for offset in range(len(lines[diagram_line - 1]) + 1):
        before = source[: line_start + offset]
        flattened = before.replace("\n", "")
        matches = (
            flattened.endswith(displayed_tail)
            if truncated
            else flattened == displayed_tail
        )
        if matches:
            candidates.append(offset + 1)
    return candidates[0] if len(candidates) == 1 else None


def _compact_message(output: str, location_index: int | None) -> str:
    raw_lines = output.splitlines()
    lines = [line.strip() for line in raw_lines if line.strip()]
    if not lines:
        return "Mermaid rejected the diagram without a diagnostic."
    if location_index is not None and location_index < len(raw_lines):
        line = raw_lines[location_index].strip()
    else:
        line = next(
            (candidate for candidate in lines if "error" in candidate.lower()),
            lines[0],
        )
    return re.sub(r"^Error:\s*", "", line, flags=re.IGNORECASE)


def _diagnose_cli_syntax_error(diagram: Diagram, output: str) -> dict[str, object] | None:
    """Normalize Mermaid's parser error into an exact, source-oriented record.

    Returns None when an exact source location cannot be recovered; the
    caller then reports a tool_error carrying the CLI's own text.
    """

    clean = _normalize_newlines(ANSI_ESCAPE.sub("", output))
    output_lines = clean.splitlines()
    location_match: re.Match[str] | None = None
    location_index: int | None = None
    for index, line in enumerate(output_lines):
        match = ERROR_LOCATION.search(line)
        if match is not None:
            location_match = match
            location_index = index
            break
    if location_match is None:
        return None

    lines = _source_lines(diagram)
    source = _normalize_newlines(diagram.source)
    mermaid_line = int(location_match.group("line"))
    diagram_line = mermaid_line
    synthetic_trailing_line = False
    if mermaid_line == len(lines) + 1:
        if source.endswith("\n"):
            lines.append("")
            synthetic_trailing_line = True
        elif lines:
            diagram_line -= 1

    column: int | None = None
    if location_match.group("column") is not None:
        column = int(location_match.group("column"))
    elif synthetic_trailing_line:
        column = 1
    elif (
        location_index is not None
        and location_index + 2 < len(output_lines)
        and "^" in output_lines[location_index + 2]
    ):
        caret_index = output_lines[location_index + 2].index("^")
        past_display = output_lines[location_index + 1][:caret_index]
        column = _jison_column(diagram, diagram_line, past_display)

    if diagram_line is None or not (1 <= diagram_line <= len(lines)) or column is None:
        return None

    source_line = lines[diagram_line - 1]
    file_line = diagram.source_start_line + diagram_line - 1

    expectation = EXPECTATION.search(clean)
    expected = expectation.group("expected") if expectation is not None else None
    got = expectation.group("got") if expectation is not None else None
    message = _compact_message(clean, location_index)
    if expected is not None and got is not None:
        message = f"{message.rstrip(':')}: got '{got}'; expected {expected}."

    context: list[dict[str, object]] = []
    for relative_line in range(
        max(1, diagram_line - 1), min(len(lines), diagram_line + 1) + 1
    ):
        context.append(
            {
                "line": diagram.source_start_line + relative_line - 1,
                "text": lines[relative_line - 1],
            }
        )

    return {
        "graph_index": diagram.index,
        "source_line": file_line,
        "message": message,
        "context": context,
        "rule": "cli_syntax_error",
    }


def _find_npx() -> str | None:
    return shutil.which("npx.cmd") or shutil.which("npx")


def verify_diagram_cli(
    diagram: Diagram, npx: str, temporary_directory: Path
) -> tuple[str, list, bytes | None]:
    """Returns (status, detail, rendered_svg) with status in
    {"ok", "syntax_error", "tool_error"}; rendered_svg only on "ok".

    `detail` is the failure list on "syntax_error" and, on "tool_error",
    one string carrying the CLI's own text — the cause the caller reports
    rather than a verdict it cannot reach."""

    output_path = temporary_directory / f"diagram-{diagram.index}.svg"
    command = [npx, "--yes", MERMAID_PACKAGE, "-i", "-", "-o", str(output_path)]
    try:
        # Explicit UTF-8: text=True alone encodes stdin with the locale
        # codepage (cp1252 on Windows), which cannot carry arbitrary
        # diagram text and raises UnicodeEncodeError before the CLI runs.
        result = subprocess.run(
            command,
            input=diagram.source,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError) as error:
        return "tool_error", [f"{MERMAID_PACKAGE} did not run: {error}"], None

    combined_output = "\n".join(
        part for part in (result.stderr, result.stdout) if part
    )
    clean_output = _normalize_newlines(ANSI_ESCAPE.sub("", combined_output))
    if result.returncode != 0:
        if MERMAID_SYNTAX_ERROR.search(combined_output):
            failure = _diagnose_cli_syntax_error(diagram, combined_output)
            if failure is None:
                return (
                    "tool_error",
                    [
                        "the CLI reported a syntax error this verifier could "
                        f"not locate: {_compact_message(clean_output, None)}"
                    ],
                    None,
                )
            return "syntax_error", [failure], None
        return (
            "tool_error",
            [
                f"{MERMAID_PACKAGE} exited {result.returncode}: "
                f"{_compact_message(clean_output, None)}"
            ],
            None,
        )

    try:
        rendered = output_path.read_bytes()
    except OSError as error:
        return "tool_error", [f"the rendered SVG was unreadable: {error}"], None
    if b"<svg" not in rendered:
        return "tool_error", ["the CLI wrote no SVG element"], None
    return "ok", [], rendered


# --- Entry point -------------------------------------------------------------------


def _write(stream: object, text: str) -> None:
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        buffer.write(text.encode("utf-8"))
        buffer.flush()
    else:
        stream.write(text)


def _emit(payload: dict[str, object]) -> None:
    _write(sys.stdout, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Markdown file containing visual fences")
    parser.add_argument(
        "--lint",
        action="store_true",
        help="also enforce the legibility contract: type gate, node budget, "
        "fan-out, subgraph depth, decision labels, rendered geometry",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    try:
        path = arguments.path.expanduser().resolve(strict=True)
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        payload = {
            "status": "error",
            "graphs": 0,
            "failures": [],
            "message": f"Could not read UTF-8 input: {error}",
        }
        _emit(payload)
        _write(sys.stderr, f"error: {payload['message']}\n")
        return 2

    diagrams = extract_diagrams(text)
    charts = extract_diagrams(text, VEGA_FENCE_RE)
    components = extract_diagrams(text, VIZ_HTML_FENCE_RE)
    if not diagrams and not charts and not components:
        if not text.strip():
            payload = {
                "status": "error",
                "graphs": 0,
                "failures": [],
                "file": str(path),
                "message": "No ```mermaid fenced block was found "
                "(nor ```vega-lite or ```viz-html) and the page is empty.",
            }
            _emit(payload)
            _write(sys.stderr, f"{path}: {payload['message']}\n")
            return 2
        # Prose with no visual fence is a legal page: the form ladder's
        # first rungs (sentence, list, table) draw nothing.
        payload = {
            "status": "pass",
            "graphs": 0,
            "charts": 0,
            "components": 0,
            "mode": "prose-only",
            "failures": [],
            "file": str(path),
        }
        _emit(payload)
        return 0

    npx = _find_npx()
    if diagrams and npx is None:
        payload = {
            "status": "error",
            "graphs": len(diagrams),
            "failures": [],
            "file": str(path),
            "message": "The Mermaid CLI is unavailable: npx was not found on "
            f"PATH, so {MERMAID_PACKAGE} cannot read the "
            f"{len(diagrams)} diagram(s) on this page. Install Node.js and "
            "rerun; this verifier judges no diagram it did not render.",
        }
        _emit(payload)
        _write(sys.stderr, f"error: {payload['message']}\n")
        return 2

    failures: list[dict[str, object]] = []
    tool_errors: list[dict[str, object]] = []
    lint_warnings: list[str] = []
    geometry_checked = 0
    flow_node_counts: list[tuple[int, int]] = []

    with tempfile.TemporaryDirectory(prefix="orch-mermaid-") as temporary:
        temporary_directory = Path(temporary)
        for diagram in diagrams:
            status, detail, rendered_svg = verify_diagram_cli(
                diagram, npx, temporary_directory
            )
            if status == "syntax_error":
                failures.extend(detail)
            elif status == "tool_error":
                tool_errors.append(
                    {"graph": diagram.index, "text": detail[0] if detail else ""}
                )
            if arguments.lint:
                lint_fails, lint_warns = lint_diagram(diagram)
                failures.extend(lint_fails)
                lint_warnings.extend(lint_warns)
                token, _line = _diagram_type(diagram)
                if token in FLOW_TYPES:
                    flow_node_counts.append(
                        (diagram.index, len(_extract_flow_graph(diagram).nodes))
                    )
                if rendered_svg is not None:
                    geometry, unchecked = geometry_failures(diagram, rendered_svg)
                    if unchecked is None:
                        geometry_checked += 1
                        failures.extend(geometry)
                    else:
                        lint_warnings.append(
                            f"graph {diagram.index}: geometry checks could not "
                            f"read the rendered SVG ({unchecked}); its layout "
                            "is unmeasured"
                        )

    # On a staged page the first flow diagram is the overview; advisory
    # because a multi-relationship page legitimately has no overview.
    if arguments.lint and len(flow_node_counts) >= 2:
        first_index, first_nodes = flow_node_counts[0]
        if first_nodes > LINT_OVERVIEW_BUDGET:
            lint_warnings.append(
                f"graph {first_index}: leads a staged page with {first_nodes} "
                f"nodes; the overview budget is {LINT_OVERVIEW_BUDGET}"
            )

    for block in charts:
        chart_failure = check_vega_fence(block)
        if chart_failure is not None:
            failures.append(chart_failure)
    for block in components:
        failures.extend(check_viz_html_fence(block))

    if tool_errors:
        status = "error"
    elif failures:
        status = "fail"
    else:
        status = "pass"
    payload: dict[str, object] = {
        "status": status,
        "graphs": len(diagrams),
        "charts": len(charts),
        "components": len(components),
        "mode": "cli" if diagrams else "static-only",
        "failures": failures,
        "file": str(path),
    }
    if tool_errors:
        payload["tool_errors"] = tool_errors
    if arguments.lint:
        payload["lint"] = {
            "warnings": lint_warnings,
            "geometry_checked": geometry_checked,
        }
    if diagrams:
        payload["mermaid_version"] = MERMAID_VERSION
    for failure in failures:
        _write(
            sys.stderr,
            f"{path}:{failure['source_line']}: {failure['message']}\n",
        )
    for tool_error in tool_errors:
        _write(
            sys.stderr,
            f"{path}: graph {tool_error['graph']} was not judged: "
            f"{tool_error['text']}\n",
        )
    _emit(payload)
    if status == "error":
        return 2
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as error:  # defensive: never crash without JSON + exit 2
        _emit(
            {
                "status": "error",
                "graphs": 0,
                "failures": [],
                "message": f"internal error: {error}",
            }
        )
        raise SystemExit(2)
