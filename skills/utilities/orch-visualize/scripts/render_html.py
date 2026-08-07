#!/usr/bin/env python3
"""Render a verified visual Markdown page to one self-contained HTML file.

Three fence kinds are rendered:
  ```mermaid    -> inline SVG via the pinned Mermaid CLI; when the CLI is
                   unavailable or fails, the fence source is carried in
                   ``<pre class="mermaid">`` and Mermaid loads from the CDN
                   at view time (mode "cdn").
  ```vega-lite  -> inline SVG via vl-convert when importable; otherwise the
                   spec is carried in ``<pre class="vega-lite">`` and
                   vega-embed loads from the CDN at view time (mode "cdn").
                   ORCH_VIZ_NO_VLCONVERT=1 forces that fallback (tests).
  ```viz-html   -> passed through inside ``<section class="viz">``; the kit
                   classes (viz-steps, viz-timeline, viz-compare, viz-boxes,
                   viz-callout) are styled by the page stylesheet.

Every inline SVG gets its ids salted per visual so clip paths, markers,
and gradients cannot cross-contaminate on one page. Page colors ride CSS
custom properties with a prefers-color-scheme default and [data-theme]
overrides. All file and subprocess boundaries are explicit UTF-8 — never
the console codepage. Always exits 0 except on unreadable input or
unwritable output (2).

Usage:
    render_html.py <page.md> [--out <page.html>]   -> result JSON on stdout
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_mermaid import (  # noqa: E402
    MERMAID_PACKAGE,
    TIMEOUT_SECONDS,
    _find_npx,
    _normalize_newlines,
)

ANY_FENCE_RE = re.compile(
    r"^```(?P<kind>mermaid|vega-lite|viz-html)[ \t]*\r?\n(?P<body>.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)

CDN_SCRIPT = (
    '<script type="module">import mermaid from '
    '"https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";'
    "mermaid.initialize({startOnLoad:true});</script>"
)

VEGA_CDN_SCRIPT = (
    '<script src="https://cdn.jsdelivr.net/npm/vega@6"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/vega-lite@6"></script>\n'
    '<script src="https://cdn.jsdelivr.net/npm/vega-embed@7"></script>\n'
    "<script>document.querySelectorAll('pre.vega-lite').forEach(function (pre) {"
    "var spec = JSON.parse(pre.textContent);"
    "var holder = document.createElement('div');"
    "pre.replaceWith(holder);"
    "vegaEmbed(holder, spec, {actions: false});"
    "});</script>"
)

# Panels stay light in dark mode on purpose: CLI-rendered SVGs assume a
# light canvas, and recoloring them is not this renderer's job.
PAGE_CSS = """
  :root { --bg: #f7f6f2; --fg: #1d2229; --panel: #fdfdfb;
          --line: #d8d9d2; --accent: #4a6b8a; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #12161a; --fg: #e6e4dd; --line: #2a3138; }
  }
  :root[data-theme="dark"] { --bg: #12161a; --fg: #e6e4dd; --line: #2a3138; }
  :root[data-theme="light"] { --bg: #f7f6f2; --fg: #1d2229; --line: #d8d9d2; }
  body { margin: 0; background: var(--bg); color: var(--fg);
         font: 16px/1.6 system-ui, sans-serif; }
  main { max-width: 900px; margin: 0 auto; padding: 40px 20px 80px; }
  h1 { font-size: 1.4rem; } h2 { font-size: 1.05rem; margin-top: 40px; }
  p { max-width: 65ch; }
  code { font-family: ui-monospace, Consolas, monospace; font-size: .9em; }
  figure.diagram { margin: 16px 0; padding: 16px; background: var(--panel);
                   border: 1px solid var(--line); border-radius: 4px;
                   overflow-x: auto; }
  figure.diagram svg { max-width: none; }
  figure.diagram pre { color: #1d2229; }
  section.viz { margin: 16px 0; padding: 16px; background: var(--panel);
                border: 1px solid var(--line); border-radius: 4px;
                overflow-x: auto; color: #1d2229; }
  .viz-steps ol { margin: 0; padding-left: 1.4em; }
  .viz-steps li { margin: 8px 0; padding: 8px 12px; background: #f7f6f2;
                  border: 1px solid #d8d9d2; border-radius: 4px;
                  max-width: 60ch; }
  .viz-timeline { list-style: none; margin: 0; padding: 0;
                  border-left: 2px solid var(--accent); }
  .viz-timeline > * { margin: 0 0 12px 0; padding: 0 0 0 16px;
                  position: relative; }
  .viz-timeline > *::before { content: ""; position: absolute; left: -5px;
                  top: .5em; width: 8px; height: 8px; border-radius: 50%;
                  background: var(--accent); }
  table.viz-compare { border-collapse: collapse; }
  table.viz-compare th, table.viz-compare td { border: 1px solid #d8d9d2;
                  padding: 6px 10px; text-align: left; vertical-align: top; }
  table.viz-compare th { background: #f7f6f2; }
  .viz-boxes { border: 1px solid #d8d9d2; border-radius: 4px;
               padding: 10px 12px; margin: 8px 0; }
  .viz-boxes .viz-boxes { background: #f7f6f2; }
  .viz-callout { border-left: 3px solid var(--accent); padding: 4px 12px;
                 margin: 12px 0; font-size: .95em; }
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


def render_vega_svg(spec_source: str):
    """Vega-Lite spec -> SVG via vl-convert when importable; None otherwise."""

    if os.environ.get("ORCH_VIZ_NO_VLCONVERT"):
        return None
    try:
        import vl_convert
    except Exception:
        return None
    try:
        svg = vl_convert.vegalite_to_svg(vl_spec=json.loads(spec_source))
    except Exception:
        return None
    return svg if "<svg" in svg else None


def _salt_svg(svg: str, index: int) -> str:
    """Prefix ids and every internal reference to them — url(#...), href,
    aria idrefs, and `#id` selectors inside <style> blocks — so multiple
    inline SVGs on one page cannot cross-contaminate clip paths, markers,
    gradients, or each other's scoped stylesheets."""

    ids = set(re.findall(r'\bid="([^"]+)"', svg))
    if not ids:
        return svg
    prefix = f"v{index}-"
    svg = re.sub(r'\bid="([^"]+)"', lambda m: f'id="{prefix}{m.group(1)}"', svg)
    svg = re.sub(
        r"url\(#([^)]+)\)",
        lambda m: f"url(#{prefix}{m.group(1)})" if m.group(1) in ids else m.group(0),
        svg,
    )
    svg = re.sub(
        r'\b(href|xlink:href)="#([^"]+)"',
        lambda m: f'{m.group(1)}="#{prefix}{m.group(2)}"'
        if m.group(2) in ids
        else m.group(0),
        svg,
    )
    svg = re.sub(
        r'\b(aria-labelledby|aria-describedby)="([^"]+)"',
        lambda m: '{}="{}"'.format(
            m.group(1),
            " ".join(
                (prefix + token) if token in ids else token
                for token in m.group(2).split()
            ),
        ),
        svg,
    )
    id_alternation = "|".join(
        re.escape(known) for known in sorted(ids, key=len, reverse=True)
    )
    selector_re = re.compile(rf"#({id_alternation})(?![A-Za-z0-9_-])")

    def _fix_style(match: re.Match[str]) -> str:
        rewritten = selector_re.sub(
            lambda m: f"#{prefix}{m.group(1)}", match.group(2)
        )
        return match.group(1) + rewritten + match.group(3)

    return re.sub(
        r"(<style[^>]*>)(.*?)(</style>)", _fix_style, svg, flags=re.DOTALL
    )


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
    """Returns (html_text, mode, graph_count, chart_count, component_count)."""

    text = _normalize_newlines(markdown)
    pieces: list[str] = []
    graphs = charts = components = salt = 0
    mermaid_fallback = vega_fallback = False
    cursor = 0
    with tempfile.TemporaryDirectory(prefix="orch-render-") as temporary:
        temporary_directory = Path(temporary)
        for match in ANY_FENCE_RE.finditer(text):
            pieces.append(_prose_to_html(text[cursor : match.start()]))
            kind = match.group("kind")
            source = match.group("body")
            if kind == "mermaid":
                graphs += 1
                salt += 1
                svg = (
                    render_svg(source, npx, temporary_directory, salt)
                    if npx is not None
                    else None
                )
                if svg is not None:
                    pieces.append(
                        f'<figure class="diagram">{_salt_svg(svg, salt)}</figure>'
                    )
                else:
                    mermaid_fallback = True
                    pieces.append(
                        '<figure class="diagram"><pre class="mermaid">'
                        f"{html.escape(source)}</pre></figure>"
                    )
            elif kind == "vega-lite":
                charts += 1
                salt += 1
                svg = render_vega_svg(source)
                if svg is not None:
                    pieces.append(
                        f'<figure class="diagram">{_salt_svg(svg, salt)}</figure>'
                    )
                else:
                    vega_fallback = True
                    pieces.append(
                        '<figure class="diagram"><pre class="vega-lite">'
                        f"{html.escape(source)}</pre></figure>"
                    )
            else:  # viz-html: verified kit markup passes through untouched
                components += 1
                pieces.append(f'<section class="viz">\n{source.strip()}\n</section>')
            cursor = match.end()
        pieces.append(_prose_to_html(text[cursor:]))
    body = "\n".join(piece for piece in pieces if piece)
    scripts: list[str] = []
    if mermaid_fallback:
        scripts.append(CDN_SCRIPT)
    if vega_fallback:
        scripts.append(VEGA_CDN_SCRIPT)
    mode = "cdn" if scripts else "svg"
    script = "\n".join(scripts)
    page = (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{html.escape(title)}</title>\n<style>{PAGE_CSS}</style>\n</head>\n"
        f"<body>\n<main>\n{body}\n</main>\n{script}\n</body>\n</html>\n"
    )
    return page, mode, graphs, charts, components


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

    page, mode, graphs, charts, components = build_page(markdown, title, _find_npx())
    try:
        out.write_text(page, encoding="utf-8")
    except OSError as error:
        print(json.dumps({"status": "error", "message": f"cannot write output: {error}"},
                         ensure_ascii=True))
        return 2
    print(json.dumps({"status": "rendered", "page": str(out), "mode": mode,
                      "graphs": graphs, "charts": charts,
                      "components": components}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
