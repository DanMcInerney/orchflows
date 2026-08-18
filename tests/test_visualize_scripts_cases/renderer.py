"""Behavioral cases for ``render_html.py``."""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

from .support import SAMPLE, _ScriptCase, _StubCli, render_html


class TestRendererHasNoCdnMode(_ScriptCase):
    """The page carries inline SVG or is not written."""

    def test_a_rendered_page_is_inline_svg_and_loads_nothing(self):
        result = self.run_renderer(SAMPLE, cli=_StubCli())
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("rendered", payload["status"])
        self.assertNotIn("mode", payload)
        self.assertEqual(1, payload["graphs"])
        page = Path(payload["page"]).read_text(encoding="utf-8")
        self.assertIn("<svg", page)
        self.assertIn("unicode", page)
        self.assertIn("<code>code</code>", page)
        self.assertIn("<strong>bold</strong>", page)
        self.assertNotIn("cdn.jsdelivr.net", page)
        self.assertNotIn("<script", page)
        self.assertNotIn('class="mermaid"', page)

    def test_each_unrendered_fence_is_an_error_and_no_page_is_written(self):
        cases = (
            ("mermaid, no CLI", SAMPLE, None, "npx"),
            (
                "mermaid, a CLI whose output is not an SVG",
                SAMPLE,
                _StubCli(svg=b"<html>an error page</html>"),
                "no SVG element",
            ),
            (
                "vega-lite, no vl-convert",
                '```vega-lite\n{"mark": "bar", "data": {"values": [{"x": 1}]}}\n```\n',
                None,
                "vl-convert",
            ),
        )
        for label, markdown, cli, named in cases:
            # ``vl_convert`` mapped to None makes its import raise on any
            # host, so the renderer's own import branch is what refuses.
            with self.subTest(case=label), mock.patch.dict(
                sys.modules, {"vl_convert": None}
            ):
                result = self.run_renderer(markdown, cli=cli)
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual("error", payload["status"])
                self.assertIsNone(payload["page"])
                self.assertEqual(1, len(payload["render_errors"]))
                self.assertIn(named, payload["render_errors"][0]["text"])
                self.assertFalse((self.directory / "page.html").exists())

    def test_oversized_fence_body_still_renders_without_crashing(self):
        lines = ["flowchart TD"]
        for index in range(2000):
            lines.append(f'    n{index}["label {index}"] --> n{index + 1}["label {index + 1}"]')
        markdown = "# Big\n\n```mermaid\n" + "\n".join(lines) + "\n```\n"
        result = self.run_renderer(markdown, cli=_StubCli())
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("rendered", payload["status"])
        self.assertEqual(1, payload["graphs"])


class TestRenderHtml(_ScriptCase):
    def test_unreadable_input_exits_two(self):
        result = self.call(render_html, [self.directory / "no-such-page.md"])
        self.assertEqual(2, result.returncode)
        self.assertEqual("error", json.loads(result.stdout)["status"])

    def test_non_utf8_bytes_report_unreadable_and_exit_two(self):
        result = self.run_renderer_bytes(b"\xff\xfe\x00\x01garbage, not valid utf-8")
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("error", payload["status"])
        self.assertIn("cannot read input", payload["message"])

    def test_an_unwritable_output_path_exits_two_and_says_so(self):
        """The renderer's exit-2 branch after the page has been built."""
        md = self.directory / "page.md"
        md.write_text(SAMPLE, encoding="utf-8")
        # A directory that does not exist: OSError on every platform,
        # needing no permission the test runner might have.
        out = self.directory / "no-such-directory" / "page.html"
        result = self.call(render_html, [md, "--out", out], cli=_StubCli())
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("error", payload["status"])
        self.assertIn("cannot write output", payload["message"])
        self.assertFalse(out.exists())


class TestRenderHtmlBoundaryInputs(_ScriptCase):
    """The renderer accepts prose-only input the verifier would refuse."""

    def test_empty_file_renders_empty_page_successfully(self):
        result = self.run_renderer("")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("rendered", payload["status"])
        self.assertEqual(0, payload["graphs"])

    def test_bom_only_file_renders_empty_page_successfully(self):
        result = self.run_renderer_bytes("﻿".encode("utf-8"))
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("rendered", payload["status"])
        self.assertEqual(0, payload["graphs"])

    def test_file_without_mermaid_fence_renders_prose_only(self):
        result = self.run_renderer("# Just a heading\n\nSome prose with no fence at all.\n")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("rendered", payload["status"])
        self.assertEqual(0, payload["graphs"])
        page = Path(payload["page"]).read_text(encoding="utf-8")
        self.assertNotIn('class="mermaid"', page)
        self.assertNotIn("<svg", page)


class TestKitAndChartFences(_ScriptCase):
    def test_viz_html_fence_passes_markup_through(self):
        result = self.run_renderer(
            "# Kit\n\n"
            "```viz-html\n"
            '<div class="viz-steps"><ol><li>step one</li><li>step two</li></ol></div>\n'
            "```\n"
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("rendered", payload["status"])
        self.assertEqual(0, payload["graphs"])
        self.assertEqual(1, payload["components"])
        page = Path(payload["page"]).read_text(encoding="utf-8")
        self.assertIn('<section class="viz">', page)
        self.assertIn("<li>step one</li>", page)
        self.assertIn(".viz-steps", page)


class TestSvgIdSalting(unittest.TestCase):
    def test_ids_and_references_are_prefixed_per_visual(self):
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
