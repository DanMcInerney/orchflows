"""Cases for the visualization scripts' command-line entry points."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .support import RENDERER, ROOT, SAMPLE, VERIFIER, _no_npx_env


class TestCommandLineEntry(unittest.TestCase):
    """One subprocess per script: everything above the scripts' ``main``.

    An in-process call cannot see argv parsing, the exit code as the
    shell reads it, or the encoding of a real stdout -- and the last of
    those is a defect these scripts actually had.
    """

    def _run(self, script, path):
        return subprocess.run(
            [sys.executable, str(script), str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
            env=_no_npx_env(),
        )

    def test_non_codepage_unicode_never_crashes_the_verifier(self):
        # U+2225 and CJK are unencodable in cp1252; the verdict must ride
        # a stdout the console codepage cannot carry (friction
        # 2026-07-16), so the page sits in a directory whose name needs
        # UTF-8 and the payload names that path.
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "lanes ∥ 中文"
            directory.mkdir()
            path = directory / "diagram.md"
            path.write_text(
                "```mermaid\n"
                "flowchart TD\n"
                '    a["lanes ∥ in parallel 中文"] --> b["done"]\n'
                "```\n",
                encoding="utf-8",
            )
            result = self._run(VERIFIER, path)
        # No CLI on this PATH: no verdict, exit 2, and the tool named.
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("error", payload["status"])
        self.assertIn("Mermaid CLI", payload["message"])
        self.assertIn("∥ 中文", payload["file"])

    def test_renderer_without_the_cli_writes_no_page_and_exits_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "page.md"
            path.write_text(SAMPLE, encoding="utf-8")
            result = self._run(RENDERER, path)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("error", payload["status"])
            self.assertEqual(
                [1], [entry["graph"] for entry in payload["render_errors"]]
            )
            self.assertFalse(path.with_suffix(".html").exists())
