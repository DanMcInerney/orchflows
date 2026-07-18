#!/usr/bin/env python3
"""Verify ```mermaid fenced diagrams embedded in a Markdown file.

Primary path: render each diagram with the pinned Mermaid CLI and locate
syntax errors from its diagnostics. When the CLI is unavailable (npx not
found) or fails to run for reasons other than a diagram syntax error, this
degrades gracefully to a built-in structural parse that catches unbalanced
brackets, an unknown diagram type on line 1, duplicate node redefinition
with conflicting labels, and dangling edge references. Results produced by
the fallback are marked "structural-only" in the output JSON.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


MERMAID_VERSION = "11.16.0"
MERMAID_PACKAGE = f"@mermaid-js/mermaid-cli@{MERMAID_VERSION}"
TIMEOUT_SECONDS = 120

ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
FENCE_RE = re.compile(
    r"^```mermaid[ \t]*\r?\n(?P<body>.*?)^```[ \t]*$",
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

KNOWN_DIAGRAM_TYPES = {
    "flowchart", "graph", "sequenceDiagram", "classDiagram", "classDiagram-v2",
    "stateDiagram", "stateDiagram-v2", "erDiagram", "journey", "gantt", "pie",
    "quadrantChart", "requirementDiagram", "gitGraph", "mindmap", "timeline",
    "sankey-beta", "sankey", "block-beta", "C4Context", "C4Container",
    "C4Component", "C4Dynamic", "C4Deployment", "xychart-beta", "packet-beta",
    "kanban", "architecture-beta", "zenuml", "radar-beta", "info",
}

NODE_DEF_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?P<id>[A-Za-z][A-Za-z0-9_-]*)"
    r"(?:\[(?P<l1>[^\]\n]*)\]|\((?P<l2>[^)\n]*)\)|\{(?P<l3>[^}\n]*)\}|>(?P<l4>[^\]\n]*)\])"
)
ARROW_RE = re.compile(r"<?(?:-\.+-*|--+|==+)[ox>]?")
CLICK_RE = re.compile(r"^\s*click\s+(?P<id>[A-Za-z][A-Za-z0-9_-]*)\b")
STYLE_RE = re.compile(r"^\s*style\s+(?P<id>[A-Za-z][A-Za-z0-9_-]*)\b")
CLASS_ASSIGN_RE = re.compile(
    r"^\s*class\s+(?P<ids>[A-Za-z0-9_,\-\s]+?)\s+[A-Za-z][A-Za-z0-9_-]*\s*;?\s*$"
)
SUBGRAPH_RE = re.compile(r"^\s*subgraph\s+(?P<id>[A-Za-z0-9_-]+)")

BRACKET_PAIRS = {")": "(", "]": "[", "}": "{"}
BRACKET_OPENS = set(BRACKET_PAIRS.values())
BRACKET_CLOSES = set(BRACKET_PAIRS.keys())


@dataclass(frozen=True)
class Diagram:
    index: int
    source: str
    source_start_line: int


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def extract_diagrams(text: str) -> list[Diagram]:
    """Extract every ```mermaid fenced block, retaining its source-file line."""

    text = _normalize_newlines(text)
    diagrams: list[Diagram] = []
    for match in FENCE_RE.finditer(text):
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


# --- Structural fallback checks -------------------------------------------------


def check_diagram_type(diagram: Diagram) -> dict[str, object] | None:
    lines = _source_lines(diagram)
    if not lines or not lines[0].strip():
        return make_failure(diagram, 0, "diagram is empty on line 1", rule="empty_diagram")
    first = lines[0].strip()
    token_match = re.match(r"[A-Za-z0-9_-]+", first)
    token = token_match.group(0) if token_match else ""
    if token not in KNOWN_DIAGRAM_TYPES:
        return make_failure(
            diagram,
            0,
            f"unknown diagram type '{token or first[:20]}' on line 1",
            rule="unknown_diagram_type",
        )
    return None


def check_bracket_balance(diagram: Diagram) -> list[dict[str, object]]:
    lines = _source_lines(diagram)
    masked = [_mask_line(line) for line in lines]
    stack: list[tuple[str, int]] = []
    for line_index, line in enumerate(masked):
        for char in line:
            if char in BRACKET_OPENS:
                stack.append((char, line_index))
            elif char in BRACKET_CLOSES:
                if not stack or stack[-1][0] != BRACKET_PAIRS[char]:
                    return [
                        make_failure(
                            diagram,
                            line_index,
                            f"unbalanced brackets: unexpected '{char}'",
                            rule="unbalanced_brackets",
                        )
                    ]
                stack.pop()
    if stack:
        char, line_index = stack[-1]
        return [
            make_failure(
                diagram,
                line_index,
                f"unbalanced brackets: unclosed '{char}'",
                rule="unbalanced_brackets",
            )
        ]
    return []


def check_node_and_edges(diagram: Diagram) -> list[dict[str, object]]:
    lines = _source_lines(diagram)
    masked = [_mask_line(line) for line in lines]
    node_labels: dict[str, tuple[str, int]] = {}
    known_ids: set[str] = set()
    failures: list[dict[str, object]] = []

    for line_index, line in enumerate(masked):
        for match in NODE_DEF_RE.finditer(line):
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
            ).strip()
            known_ids.add(node_id)
            if not label:
                continue
            if node_id in node_labels:
                prior_label, prior_line = node_labels[node_id]
                if prior_label and prior_label != label:
                    failures.append(
                        make_failure(
                            diagram,
                            line_index,
                            f"node '{node_id}' redefined with conflicting label: "
                            f"'{prior_label}' (line "
                            f"{diagram.source_start_line + prior_line}) vs '{label}'",
                            rule="duplicate_node_label",
                        )
                    )
            else:
                node_labels[node_id] = (label, line_index)

        subgraph_match = SUBGRAPH_RE.match(line)
        if subgraph_match:
            known_ids.add(subgraph_match.group("id"))

        segments = ARROW_RE.split(line)
        if len(segments) > 1:
            for segment_index in range(len(segments) - 1):
                left, right = segments[segment_index], segments[segment_index + 1]
                right_clean = re.sub(r"^\s*\|[^|\n]*\|", "", right)
                src_match = re.search(
                    r"([A-Za-z0-9_-]+)\s*(?:\[[^\]\n]*\]|\([^)\n]*\)|\{[^}\n]*\})?\s*$",
                    left,
                )
                dst_match = re.match(r"\s*([A-Za-z0-9_-]+)", right_clean)
                if src_match:
                    known_ids.add(src_match.group(1))
                if dst_match:
                    known_ids.add(dst_match.group(1))

    for line_index, line in enumerate(masked):
        click_match = CLICK_RE.match(line)
        if click_match:
            node_id = click_match.group("id")
            if node_id not in known_ids:
                failures.append(
                    make_failure(
                        diagram,
                        line_index,
                        f"dangling reference: '{node_id}' used in 'click' but "
                        "never defined as a node",
                        rule="dangling_reference",
                    )
                )
            continue
        style_match = STYLE_RE.match(line)
        if style_match:
            node_id = style_match.group("id")
            if node_id not in known_ids:
                failures.append(
                    make_failure(
                        diagram,
                        line_index,
                        f"dangling reference: '{node_id}' used in 'style' but "
                        "never defined as a node",
                        rule="dangling_reference",
                    )
                )
            continue
        class_match = CLASS_ASSIGN_RE.match(line)
        if class_match:
            for node_id in (part.strip() for part in class_match.group("ids").split(",")):
                if node_id and node_id not in known_ids:
                    failures.append(
                        make_failure(
                            diagram,
                            line_index,
                            f"dangling reference: '{node_id}' used in 'class' but "
                            "never defined as a node",
                            rule="dangling_reference",
                        )
                    )

    return failures


def structural_check(diagram: Diagram) -> list[dict[str, object]]:
    failures: list[dict[str, object]] = []
    type_failure = check_diagram_type(diagram)
    if type_failure is not None:
        failures.append(type_failure)
    failures.extend(check_bracket_balance(diagram))
    failures.extend(check_node_and_edges(diagram))
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

    Returns None when an exact source location cannot be recovered, signaling
    the caller to fall back to a tool_error (and, ultimately, structural check).
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
) -> tuple[str, list[dict[str, object]]]:
    """Returns (status, failures) with status in {"ok", "syntax_error", "tool_error"}."""

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
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return "tool_error", []

    combined_output = "\n".join(
        part for part in (result.stderr, result.stdout) if part
    )
    if result.returncode != 0:
        if MERMAID_SYNTAX_ERROR.search(combined_output):
            failure = _diagnose_cli_syntax_error(diagram, combined_output)
            if failure is None:
                return "tool_error", []
            return "syntax_error", [failure]
        return "tool_error", []

    try:
        rendered = output_path.read_bytes()
    except OSError:
        return "tool_error", []
    if b"<svg" not in rendered:
        return "tool_error", []
    return "ok", []


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
    parser.add_argument("path", type=Path, help="Markdown file containing mermaid fences")
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
    if not diagrams:
        payload = {
            "status": "error",
            "graphs": 0,
            "failures": [],
            "file": str(path),
            "message": "No ```mermaid fenced block was found.",
        }
        _emit(payload)
        _write(sys.stderr, f"{path}: {payload['message']}\n")
        return 2

    npx = _find_npx()
    failures: list[dict[str, object]] = []
    modes_used: set[str] = set()

    with tempfile.TemporaryDirectory(prefix="orch-mermaid-") as temporary:
        temporary_directory = Path(temporary)
        for diagram in diagrams:
            used_cli = False
            if npx is not None:
                status, diagram_failures = verify_diagram_cli(diagram, npx, temporary_directory)
                if status == "ok":
                    modes_used.add("cli")
                    used_cli = True
                elif status == "syntax_error":
                    modes_used.add("cli")
                    failures.extend(diagram_failures)
                    used_cli = True
                # status == "tool_error" falls through to the structural fallback
            if not used_cli:
                modes_used.add("structural")
                structural_failures = structural_check(diagram)
                for failure in structural_failures:
                    failure["structural_only"] = True
                failures.extend(structural_failures)

    if modes_used == {"cli"}:
        mode = "cli"
    elif modes_used == {"structural"}:
        mode = "structural-only"
    else:
        mode = "mixed"

    status = "pass" if not failures else "fail"
    payload: dict[str, object] = {
        "status": status,
        "graphs": len(diagrams),
        "mode": mode,
        "failures": failures,
        "file": str(path),
    }
    if "cli" in modes_used:
        payload["mermaid_version"] = MERMAID_VERSION
    for failure in failures:
        _write(
            sys.stderr,
            f"{path}:{failure['source_line']}: {failure['message']}\n",
        )
    _emit(payload)
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
