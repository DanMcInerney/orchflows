"""Mermaid verifier: unicode robustness, structural-fallback rules, and the
exit-code / boundary-input contract.

Every subprocess call below runs the verifier with npx made unresolvable
(``PATH`` stripped), so the structural fallback fires deterministically
regardless of whether the host has Node/npx installed. This never spawns
npx or any Mermaid CLI process.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFIER = ROOT / "skills" / "utilities" / "orch-visualize" / "scripts" / "verify_mermaid.py"


def _no_npx_env():
    """An environment where shutil.which can never resolve npx, whatever the
    real host PATH contains — forces the structural fallback deterministically
    instead of depending on (or spawning) a real Mermaid CLI."""
    env = dict(os.environ)
    env["PATH"] = ""
    return env


def run_verifier(markdown: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "diagram.md"
        path.write_text(markdown, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(VERIFIER), str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
            env=_no_npx_env(),
        )


def run_verifier_bytes(raw: bytes):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "diagram.md"
        path.write_bytes(raw)
        return subprocess.run(
            [sys.executable, str(VERIFIER), str(path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(ROOT),
            env=_no_npx_env(),
        )


class TestVerifierRobustness(unittest.TestCase):
    def test_non_codepage_unicode_never_crashes_the_verifier(self):
        # U+2225 and CJK are unencodable in cp1252; the verifier must judge
        # the diagram, not the console codepage (friction 2026-07-16).
        result = run_verifier(
            "```mermaid\n"
            "flowchart TD\n"
            '    a["lanes ∥ in parallel 中文"] --> b["done"]\n'
            "```\n"
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(1, payload["graphs"])
        self.assertEqual("structural-only", payload["mode"])

    def test_broken_diagram_still_fails_cleanly(self):
        result = run_verifier(
            "```mermaid\n"
            "flowchart TD\n"
            "    a[unclosed --> b\n"
            "```\n"
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("fail", payload["status"])
        self.assertTrue(payload["failures"])
        self.assertEqual("unbalanced_brackets", payload["failures"][0]["rule"])
        self.assertTrue(payload["failures"][0]["structural_only"])


class TestStructuralFallbackRules(unittest.TestCase):
    """Each structural-fallback rule pinned by one dedicated input that
    triggers exactly that rule and no other, with the failure carrying
    both the rule name and the structural_only marker."""

    def test_unknown_diagram_type_rule_detected(self):
        result = run_verifier(
            "```mermaid\n"
            "notARealDiagramType\n"
            "    a --> b\n"
            "```\n"
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("fail", payload["status"])
        rules = [failure["rule"] for failure in payload["failures"]]
        self.assertEqual(["unknown_diagram_type"], rules)
        self.assertTrue(payload["failures"][0]["structural_only"])

    def test_duplicate_node_label_rule_detected(self):
        result = run_verifier(
            "```mermaid\n"
            "flowchart TD\n"
            '    a["first label"] --> b["second"]\n'
            '    a["different label"] --> c["third"]\n'
            "```\n"
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("fail", payload["status"])
        rules = [failure["rule"] for failure in payload["failures"]]
        self.assertEqual(["duplicate_node_label"], rules)
        self.assertTrue(payload["failures"][0]["structural_only"])

    def test_dangling_click_reference_rule_detected(self):
        result = run_verifier(
            "```mermaid\n"
            "flowchart TD\n"
            '    a["start"] --> b["end"]\n'
            '    click missingNode "https://example.com"\n'
            "```\n"
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("fail", payload["status"])
        rules = [failure["rule"] for failure in payload["failures"]]
        self.assertEqual(["dangling_reference"], rules)
        self.assertIn("missingNode", payload["failures"][0]["message"])
        self.assertTrue(payload["failures"][0]["structural_only"])

    def test_dangling_style_reference_rule_detected(self):
        result = run_verifier(
            "```mermaid\n"
            "flowchart TD\n"
            '    a["start"] --> b["end"]\n'
            "    style missingNode fill:#f00\n"
            "```\n"
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("fail", payload["status"])
        rules = [failure["rule"] for failure in payload["failures"]]
        self.assertEqual(["dangling_reference"], rules)
        self.assertIn("missingNode", payload["failures"][0]["message"])
        self.assertTrue(payload["failures"][0]["structural_only"])

    def test_dangling_class_reference_rule_detected(self):
        result = run_verifier(
            "```mermaid\n"
            "flowchart TD\n"
            '    a["start"] --> b["end"]\n'
            "    class missingNode someClass\n"
            "```\n"
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("fail", payload["status"])
        rules = [failure["rule"] for failure in payload["failures"]]
        self.assertEqual(["dangling_reference"], rules)
        self.assertIn("missingNode", payload["failures"][0]["message"])
        self.assertTrue(payload["failures"][0]["structural_only"])


class TestBoundaryInputs(unittest.TestCase):
    def test_empty_file_reports_no_fence_and_exits_two(self):
        result = run_verifier("")
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("error", payload["status"])
        self.assertIn("No ```mermaid fenced block", payload["message"])

    def test_bom_only_file_reports_no_fence_and_exits_two(self):
        result = run_verifier_bytes("﻿".encode("utf-8"))
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("error", payload["status"])
        self.assertIn("No ```mermaid fenced block", payload["message"])

    def test_file_without_mermaid_fence_reports_no_fence_and_exits_two(self):
        result = run_verifier("# Just a heading\n\nSome prose with no fence at all.\n")
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("error", payload["status"])
        self.assertIn("No ```mermaid fenced block", payload["message"])

    def test_non_utf8_bytes_report_unreadable_and_exit_two(self):
        result = run_verifier_bytes(b"\xff\xfe\x00\x01garbage, not valid utf-8")
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("error", payload["status"])
        self.assertIn("Could not read UTF-8 input", payload["message"])

    def test_bom_prefixed_fence_on_first_line_is_detected(self):
        # Regression: the verifier read input as plain "utf-8", leaving a
        # leading BOM as a literal U+FEFF character. That defeated the
        # fence regex's `^` anchor for a fence starting on line 1, so a
        # valid BOM-prefixed diagram was reported as "no fence" (exit 2)
        # even though render_html.py (which reads "utf-8-sig") renders the
        # same file correctly.
        raw = ("﻿```mermaid\nflowchart TD\n    a[\"x\"] --> b[\"y\"]\n```\n").encode("utf-8")
        result = run_verifier_bytes(raw)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(1, payload["graphs"])

    def test_oversized_fence_body_still_processes_without_crashing(self):
        lines = ["flowchart TD"]
        node_count = 3000
        for index in range(node_count):
            lines.append(f'    n{index}["label {index}"] --> n{index + 1}["label {index + 1}"]')
        source = "\n".join(lines) + "\n"
        markdown = f"```mermaid\n{source}```\n"
        result = run_verifier(markdown)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(1, payload["graphs"])
        self.assertEqual("structural-only", payload["mode"])


if __name__ == "__main__":
    unittest.main()
