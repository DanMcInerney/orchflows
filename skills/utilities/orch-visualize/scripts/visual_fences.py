"""Extract and validate non-executable visual fences."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser

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

def _source_lines(diagram: Diagram) -> list[str]:
    return _normalize_newlines(diagram.source).splitlines()

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
