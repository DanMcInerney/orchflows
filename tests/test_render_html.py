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
    instead of depending on (or spawning) a real Mermaid CLI."""
    env = dict(os.environ)
    env["PATH"] = ""
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


if __name__ == "__main__":
    unittest.main()
