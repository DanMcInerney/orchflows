"""HTML renderer for verified Mermaid pages: self-containment, cdn fallback,
and the exit-code / boundary-input contract.

Every subprocess call below runs the renderer with npx made unresolvable
(``PATH`` stripped), so the cdn fallback fires deterministically regardless
of whether the host has Node/npx installed. This never spawns npx or any
Mermaid CLI process.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RENDERER = ROOT / "skills" / "utilities" / "orch-visualize" / "scripts" / "render_html.py"

SAMPLE = (
    "# Sample viz — unicode ∥ 中文\n"
    "\n"
    "One terse paragraph with `code` and **bold**.\n"
    "\n"
    "```mermaid\n"
    "flowchart TD\n"
    '    a["start"] --> b["done"]\n'
    "```\n"
)


def _no_npx_env():
    """An environment where shutil.which can never resolve npx, whatever the
    real host PATH contains — forces the cdn fallback deterministically
    instead of depending on (or spawning) a real Mermaid CLI. The vl-convert
    knob likewise forces the vega cdn fallback regardless of what the host
    happens to have installed."""
    env = dict(os.environ)
    env["PATH"] = ""
    env["ORCH_VIZ_NO_VLCONVERT"] = "1"
    return env


def run_renderer(directory: Path, markdown: str, name: str = "page.md"):
    md = directory / name
    md.write_text(markdown, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(RENDERER), str(md)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        env=_no_npx_env(),
    )
    return result


def run_renderer_bytes(directory: Path, raw: bytes, name: str = "page.md"):
    md = directory / name
    md.write_bytes(raw)
    result = subprocess.run(
        [sys.executable, str(RENDERER), str(md)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        env=_no_npx_env(),
    )
    return result


class TestRenderHtml(unittest.TestCase):
    def test_cdn_fallback_html_shape_when_npx_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            result = run_renderer(directory, SAMPLE)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("rendered", payload["status"])
            self.assertEqual(1, payload["graphs"])
            self.assertEqual("cdn", payload["mode"])
            page = Path(payload["page"]).read_text(encoding="utf-8")
            self.assertIn("<title>", page)
            self.assertIn("unicode", page)
            self.assertIn('<pre class="mermaid">', page)
            self.assertIn("a[&quot;start&quot;] --&gt; b[&quot;done&quot;]", page)
            self.assertIn("cdn.jsdelivr.net", page)
            self.assertNotIn("<svg", page)
            self.assertIn("<code>code</code>", page)
            self.assertIn("<strong>bold</strong>", page)

    def test_unreadable_input_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [sys.executable, str(RENDERER), str(Path(tmp) / "no-such-page.md")],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", cwd=str(ROOT), env=_no_npx_env(),
            )
            self.assertEqual(2, result.returncode)
            self.assertEqual("error", json.loads(result.stdout)["status"])

    def test_non_utf8_bytes_report_unreadable_and_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_renderer_bytes(Path(tmp), b"\xff\xfe\x00\x01garbage, not valid utf-8")
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("error", payload["status"])
            self.assertIn("cannot read input", payload["message"])


class TestRenderHtmlBoundaryInputs(unittest.TestCase):
    """render_html tolerates inputs verify_mermaid would reject: a page
    with no mermaid fence at all is still valid prose to render."""

    def test_empty_file_renders_empty_page_successfully(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_renderer(Path(tmp), "")
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("rendered", payload["status"])
            self.assertEqual(0, payload["graphs"])

    def test_bom_only_file_renders_empty_page_successfully(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_renderer_bytes(Path(tmp), "﻿".encode("utf-8"))
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("rendered", payload["status"])
            self.assertEqual(0, payload["graphs"])

    def test_file_without_mermaid_fence_renders_prose_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_renderer(
                Path(tmp), "# Just a heading\n\nSome prose with no fence at all.\n"
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("rendered", payload["status"])
            self.assertEqual(0, payload["graphs"])
            page = Path(payload["page"]).read_text(encoding="utf-8")
            self.assertNotIn('class="mermaid"', page)
            self.assertNotIn("<svg", page)

    def test_oversized_fence_body_still_renders_without_crashing(self):
        lines = ["flowchart TD"]
        node_count = 2000
        for index in range(node_count):
            lines.append(f'    n{index}["label {index}"] --> n{index + 1}["label {index + 1}"]')
        source = "\n".join(lines) + "\n"
        markdown = f"# Big\n\n```mermaid\n{source}```\n"
        with tempfile.TemporaryDirectory() as tmp:
            result = run_renderer(Path(tmp), markdown)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("rendered", payload["status"])
            self.assertEqual(1, payload["graphs"])
            self.assertEqual("cdn", payload["mode"])
            page = Path(payload["page"]).read_text(encoding="utf-8")
            self.assertIn('<pre class="mermaid">', page)
            self.assertIn("label 1999", page)


class TestKitAndChartFences(unittest.TestCase):
    def test_viz_html_fence_passes_markup_through(self):
        page_md = (
            "# Kit\n\n"
            "```viz-html\n"
            '<div class="viz-steps"><ol><li>step one</li><li>step two</li></ol></div>\n'
            "```\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = run_renderer(Path(tmp), page_md)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("rendered", payload["status"])
            self.assertEqual(0, payload["graphs"])
            self.assertEqual(1, payload["components"])
            page = Path(payload["page"]).read_text(encoding="utf-8")
            self.assertIn('<section class="viz">', page)
            self.assertIn("<li>step one</li>", page)
            self.assertIn(".viz-steps", page)

    def test_vega_lite_fence_falls_back_to_cdn(self):
        page_md = (
            "```vega-lite\n"
            '{"mark": "bar", "data": {"values": [{"x": 1}]}}\n'
            "```\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = run_renderer(Path(tmp), page_md)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("cdn", payload["mode"])
            self.assertEqual(1, payload["charts"])
            page = Path(payload["page"]).read_text(encoding="utf-8")
            self.assertIn('<pre class="vega-lite">', page)
            self.assertIn("vega-embed", page)
            self.assertNotIn("mermaid.esm", page)


class TestSvgIdSalting(unittest.TestCase):
    def test_ids_and_references_are_prefixed_per_visual(self):
        sys.path.insert(
            0, str(ROOT / "skills" / "utilities" / "orch-visualize" / "scripts")
        )
        import render_html

        svg = (
            '<svg id="my-svg" aria-labelledby="my-title" role="img">'
            "<style>#my-svg .node rect{fill:red}#other{}</style>"
            '<title id="my-title">t</title>'
            '<defs><clipPath id="a"><rect/></clipPath></defs>'
            '<g clip-path="url(#a)"></g><use href="#a"/>'
            '<g clip-path="url(#external)"></g></svg>'
        )
        salted = render_html._salt_svg(svg, 3)
        self.assertIn('id="v3-a"', salted)
        self.assertIn("url(#v3-a)", salted)
        self.assertIn('href="#v3-a"', salted)
        self.assertIn("url(#external)", salted)
        # Mermaid CLI SVGs scope their stylesheet by root id; the selector
        # and the aria idref must be rewritten with the id or the diagram
        # detaches from its own styles.
        self.assertIn("#v3-my-svg .node rect", salted)
        self.assertIn("#other{}", salted)
        self.assertIn('aria-labelledby="v3-my-title"', salted)


if __name__ == "__main__":
    unittest.main()
