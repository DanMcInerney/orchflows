#!/usr/bin/env python3
"""Render a verified Mermaid Markdown page to one self-contained HTML file.

Primary path: every ```mermaid fence is rendered to inline SVG with the
pinned Mermaid CLI, so the page needs no network and no JavaScript.
When the CLI is unavailable or fails, the page carries the fence source
in ``<pre class="mermaid">`` and loads Mermaid from the CDN at view
time; the JSON result reports mode "cdn" so the caller can say so.
All file and subprocess boundaries are explicit UTF-8 — never the
console codepage. Always exits 0 except on unreadable input (2).

Usage:
    render_html.py <page.md> [--out <page.html>]   -> result JSON on stdout
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_mermaid import (  # noqa: E402
    FENCE_RE,
    MERMAID_PACKAGE,
    TIMEOUT_SECONDS,
    _find_npx,
    _normalize_newlines,
)

CDN_SCRIPT = (
    '<script type="module">import mermaid from '
    '"https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";'
    "mermaid.initialize({startOnLoad:true});</script>"
)

PAGE_CSS = """
  body { margin: 0; background: #f7f6f2; color: #1d2229;
         font: 16px/1.6 system-ui, sans-serif; }
  main { max-width: 900px; margin: 0 auto; padding: 40px 20px 80px; }
  h1 { font-size: 1.4rem; } h2 { font-size: 1.05rem; margin-top: 40px; }
  p { max-width: 65ch; }
  code { font-family: ui-monospace, Consolas, monospace; font-size: .9em; }
  figure.diagram { margin: 16px 0; padding: 16px; background: #fdfdfb;
                   border: 1px solid #d8d9d2; border-radius: 4px;
                   overflow-x: auto; }
  figure.diagram svg { max-width: none; }
  @media (prefers-color-scheme: dark) {
    body { background: #12161a; color: #e6e4dd; }
    figure.diagram { background: #f4f3ee; border-color: #2a3138; }
  }
"""


def render_svg(source: str, npx: str, temporary_directory: Path, index: int):
    output_path = temporary_directory / f"render-{index}.svg"
    command = [npx, "--yes", MERMAID_PACKAGE, "-i", "-", "-o", str(output_path)]
    try:
        result = subprocess.run(
            command,
            input=source,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return None
    if result.returncode != 0:
        return None
    try:
        svg = output_path.read_text(encoding="utf-8")
    except OSError:
        return None
    return svg if "<svg" in svg else None


def _inline_md(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def _prose_to_html(prose: str) -> str:
    parts: list[str] = []
    for block in re.split(r"\n\s*\n", _normalize_newlines(prose)):
        block = block.strip()
        if not block:
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)$", block.splitlines()[0])
        if heading and len(block.splitlines()) == 1:
            level = min(len(heading.group(1)), 6)
            parts.append(f"<h{level}>{_inline_md(heading.group(2))}</h{level}>")
        else:
            parts.append(f"<p>{_inline_md(' '.join(block.splitlines()))}</p>")
    return "\n".join(parts)


def build_page(markdown: str, title: str, npx):
    """Returns (html_text, mode, graph_count)."""
    text = _normalize_newlines(markdown)
    pieces: list[str] = []
    mode = "svg"
    graphs = 0
    cursor = 0
    with tempfile.TemporaryDirectory(prefix="orch-render-") as temporary:
        temporary_directory = Path(temporary)
        for match in FENCE_RE.finditer(text):
            pieces.append(_prose_to_html(text[cursor : match.start()]))
            graphs += 1
            source = match.group("body")
            svg = (
                render_svg(source, npx, temporary_directory, graphs)
                if npx is not None
                else None
            )
            if svg is not None:
                pieces.append(f'<figure class="diagram">{svg}</figure>')
            else:
                mode = "cdn"
                pieces.append(
                    '<figure class="diagram"><pre class="mermaid">'
                    f"{html.escape(source)}</pre></figure>"
                )
            cursor = match.end()
        pieces.append(_prose_to_html(text[cursor:]))
    body = "\n".join(piece for piece in pieces if piece)
    script = CDN_SCRIPT if mode == "cdn" else ""
    page = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{html.escape(title)}</title>\n<style>{PAGE_CSS}</style>\n</head>\n"
        f"<body>\n<main>\n{body}\n</main>\n{script}\n</body>\n</html>\n"
    )
    return page, mode, graphs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="verified Markdown page")
    parser.add_argument("--out", type=Path, default=None, help="output HTML path")
    arguments = parser.parse_args(argv)
    try:
        path = arguments.path.expanduser().resolve(strict=True)
        markdown = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        print(json.dumps({"status": "error", "message": f"cannot read input: {error}"},
                         ensure_ascii=True))
        return 2

    out = arguments.out or path.with_suffix(".html")
    title = path.stem.replace("-", " ")
    for line in markdown.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break

    page, mode, graphs = build_page(markdown, title, _find_npx())
    try:
        out.write_text(page, encoding="utf-8")
    except OSError as error:
        print(json.dumps({"status": "error", "message": f"cannot write output: {error}"},
                         ensure_ascii=True))
        return 2
    print(json.dumps({"status": "rendered", "page": str(out), "mode": mode,
                      "graphs": graphs}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
