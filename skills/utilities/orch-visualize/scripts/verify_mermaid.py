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
from pathlib import Path

from mermaid_lint import (
    ARROW_RE,
    CLASSDEF_RE,
    DIRECTION_RE,
    FLOW_TYPES,
    LINT_CLASSDEF_MAX,
    LINT_FAN_OUT_MAX,
    LINT_FORBIDDEN_TYPES,
    LINT_LABEL_WORD_MAX,
    LINT_NODE_BUDGET,
    LINT_NODE_WARN,
    LINT_OVERVIEW_BUDGET,
    LINT_SUBGRAPH_DEPTH_MAX,
    NODE_DEF_RE,
    NON_NODE_TOKENS,
    SUBGRAPH_RE,
    SVG_NS,
    TRANSLATE_RE,
    FlowGraph,
    _diagram_type,
    _extract_flow_graph,
    _frontmatter_span,
    _mask_line,
    geometry_failures,
    lint_diagram,
)
from visual_fences import (
    EXTERNAL_REF_RE,
    FENCE_RE,
    INLINE_STYLE_RE,
    SCRIPT_TAG_RE,
    VEGA_FENCE_RE,
    VIZ_HTML_FENCE_RE,
    VOID_TAGS,
    Diagram,
    _TagBalance,
    _normalize_newlines,
    _source_lines,
    check_vega_fence,
    check_viz_html_fence,
    extract_diagrams,
    make_failure,
)


MERMAID_VERSION = "11.16.0"
MERMAID_PACKAGE = f"@mermaid-js/mermaid-cli@{MERMAID_VERSION}"
TIMEOUT_SECONDS = 120

ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
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
                source_nodes = 0
                if token in FLOW_TYPES:
                    source_nodes = len(_extract_flow_graph(diagram).nodes)
                    flow_node_counts.append((diagram.index, source_nodes))
                if rendered_svg is not None:
                    geometry, unchecked = geometry_failures(
                        diagram, rendered_svg, source_nodes
                    )
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
