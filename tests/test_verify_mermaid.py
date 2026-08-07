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


def run_verifier(markdown: str, *extra_args: str):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "diagram.md"
        path.write_text(markdown, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(VERIFIER), str(path), *extra_args],
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

    def test_file_without_any_fence_passes_as_prose_only(self):
        # The form ladder's first rungs (sentence, list, table) draw
        # nothing, so a fence-free prose page is a legal verified page.
        result = run_verifier("# Just a heading\n\nSome prose with no fence at all.\n")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(0, payload["graphs"])
        self.assertEqual("prose-only", payload["mode"])

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


class TestElkFrontmatter(unittest.TestCase):
    def test_elk_frontmatter_diagram_passes_structural_check(self):
        result = run_verifier(
            "```mermaid\n"
            "---\n"
            "config:\n"
            "  layout: elk\n"
            "---\n"
            "flowchart TD\n"
            '    a["start work"] --> b["done"]\n'
            "```\n"
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(1, payload["graphs"])


class TestLegibilityLint(unittest.TestCase):
    """--lint promotes legibility-contract violations to failures; without
    the flag the same inputs keep the historical pass behavior."""

    def _lint_rules(self, result):
        payload = json.loads(result.stdout)
        return payload, [failure["rule"] for failure in payload["failures"]]

    def test_forbidden_type_mindmap_fails_only_under_lint(self):
        source = "```mermaid\nmindmap\n  root\n```\n"
        self.assertEqual(0, run_verifier(source).returncode)
        result = run_verifier(source, "--lint")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload, rules = self._lint_rules(result)
        self.assertIn("lint_forbidden_type", rules)

    def test_forbidden_type_beta_suffix_fails_under_lint(self):
        result = run_verifier("```mermaid\ntreemap-beta\n```\n", "--lint")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        _payload, rules = self._lint_rules(result)
        self.assertIn("lint_forbidden_type", rules)

    def test_node_budget_exceeded_fails_under_lint(self):
        lines = ["flowchart TD"]
        for index in range(34):
            lines.append(f'    n{index}["step {index}"] --> n{index + 1}["step {index + 1}"]')
        source = "```mermaid\n" + "\n".join(lines) + "\n```\n"
        self.assertEqual(0, run_verifier(source).returncode)
        result = run_verifier(source, "--lint")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        _payload, rules = self._lint_rules(result)
        self.assertIn("lint_node_budget", rules)

    def test_fan_out_over_four_fails_under_lint(self):
        lines = ["flowchart TD"]
        for index in range(5):
            lines.append(f'    hub["dispatch work"] --> t{index}["target {index}"]')
        result = run_verifier("```mermaid\n" + "\n".join(lines) + "\n```\n", "--lint")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        _payload, rules = self._lint_rules(result)
        self.assertIn("lint_fan_out", rules)

    def test_fan_out_via_ampersand_list_fails_under_lint(self):
        result = run_verifier(
            "```mermaid\n"
            "flowchart TD\n"
            '    hub["dispatch work"] --> a["t1"] & b["t2"] & c["t3"] & d["t4"] & e["t5"]\n'
            "```\n",
            "--lint",
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        _payload, rules = self._lint_rules(result)
        self.assertIn("lint_fan_out", rules)

    def test_nested_subgraph_fails_under_lint(self):
        result = run_verifier(
            "```mermaid\n"
            "flowchart TD\n"
            "    subgraph outer\n"
            "        subgraph inner\n"
            '            z1["deep node"]\n'
            "        end\n"
            "    end\n"
            "```\n",
            "--lint",
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        _payload, rules = self._lint_rules(result)
        self.assertIn("lint_subgraph_depth", rules)

    def test_direction_in_externally_linked_subgraph_fails_under_lint(self):
        result = run_verifier(
            "```mermaid\n"
            "flowchart TD\n"
            "    subgraph s1\n"
            "        direction LR\n"
            '        x1["inside a"] --> x2["inside b"]\n'
            "    end\n"
            '    x2 --> y1["outside"]\n'
            "```\n",
            "--lint",
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        _payload, rules = self._lint_rules(result)
        self.assertIn("lint_direction_ignored", rules)

    def test_unlabeled_decision_branch_fails_under_lint(self):
        result = run_verifier(
            "```mermaid\n"
            "flowchart TD\n"
            '    a["check input"] --> d{"valid?"}\n'
            '    d --> b["accept"]\n'
            "```\n",
            "--lint",
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        _payload, rules = self._lint_rules(result)
        self.assertIn("lint_decision_unlabeled", rules)

    def test_clean_diagram_passes_lint_with_warning_channel(self):
        result = run_verifier(
            "```mermaid\n"
            "flowchart TD\n"
            '    a["check input"] --> d{"valid?"}\n'
            '    d -->|yes| b["accept"]\n'
            '    d -->|no| c["reject"]\n'
            "```\n",
            "--lint",
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual([], payload["lint"]["warnings"])
        self.assertEqual(0, payload["lint"]["geometry_checked"])


class TestStaticFences(unittest.TestCase):
    """vega-lite and viz-html fences are verified without any mermaid block."""

    def test_vega_only_page_passes_with_chart_count(self):
        result = run_verifier(
            "```vega-lite\n"
            '{"mark": "bar", "data": {"values": []}}\n'
            "```\n"
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(0, payload["graphs"])
        self.assertEqual(1, payload["charts"])
        self.assertEqual("static-only", payload["mode"])

    def test_invalid_vega_json_fails(self):
        result = run_verifier("```vega-lite\n{not json}\n```\n")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            ["invalid_vega_json"], [failure["rule"] for failure in payload["failures"]]
        )

    def test_unbalanced_viz_html_fails(self):
        result = run_verifier(
            "```viz-html\n"
            '<div class="viz-steps"><ol><li>one</li></ol>\n'
            "```\n"
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            ["unbalanced_html"], [failure["rule"] for failure in payload["failures"]]
        )

    def test_script_in_viz_html_fails(self):
        result = run_verifier(
            "```viz-html\n"
            "<div><script>alert(1)</script></div>\n"
            "```\n"
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        rules = [failure["rule"] for failure in payload["failures"]]
        self.assertIn("viz_html_script", rules)

    def test_inline_style_in_viz_html_fails(self):
        result = run_verifier(
            "```viz-html\n"
            '<div style="color: red">styled</div>\n'
            "```\n"
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        rules = [failure["rule"] for failure in payload["failures"]]
        self.assertIn("viz_html_inline_style", rules)

    def test_external_reference_in_viz_html_fails(self):
        result = run_verifier(
            "```viz-html\n"
            '<div><img src="https://example.com/x.png"></div>\n'
            "```\n"
        )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        rules = [failure["rule"] for failure in payload["failures"]]
        self.assertIn("viz_html_external", rules)

    def test_balanced_viz_html_passes(self):
        result = run_verifier(
            "```viz-html\n"
            '<table class="viz-compare"><tr><th>axis</th><td>value</td></tr></table>\n'
            "```\n"
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(1, payload["components"])


if __name__ == "__main__":
    unittest.main()
