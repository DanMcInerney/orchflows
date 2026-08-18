"""Behavioral cases for ``verify_mermaid.py``."""

import json

from .support import _ScriptCase, _StubCli, verify_mermaid


class TestVerifierRequiresTheMermaidCli(_ScriptCase):
    """No CLI is not a verdict; the verifier refuses and names the cause."""

    DIAGRAM = "```mermaid\nflowchart TD\n    a[\"start\"] --> b[\"done\"]\n```\n"

    def test_missing_cli_exits_two_and_names_the_tool(self):
        result = self.run_verifier(self.DIAGRAM, cli=None)
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("error", payload["status"])
        self.assertIn("Mermaid CLI", payload["message"])
        self.assertIn("npx", payload["message"])
        self.assertNotIn("structural", result.stdout)

    def test_a_cli_that_cannot_judge_exits_two_carrying_its_own_text(self):
        for label, cli in (
            ("the CLI left no file", _StubCli(svg=None)),
            ("the CLI wrote something other than an SVG", _StubCli(svg=b"<html/>")),
            ("a non-zero exit with no parse error", _StubCli(1, "ENOENT: chrome")),
            (
                "a parse error with no location",
                _StubCli(1, "Error: Parse error somewhere in there"),
            ),
        ):
            with self.subTest(cause=label):
                result = self.run_verifier(self.DIAGRAM, cli=cli)
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual("error", payload["status"])
                self.assertEqual(
                    [1], [entry["graph"] for entry in payload["tool_errors"]]
                )
                self.assertTrue(payload["tool_errors"][0]["text"])

    def test_a_located_parse_error_is_a_failure_at_its_source_line(self):
        cli = _StubCli(1, "Parse error on line 2, column 5:\nExpecting 'SQE', got 'x'")
        result = self.run_verifier("# Page\n\n" + self.DIAGRAM, cli=cli)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("fail", payload["status"])
        failure = payload["failures"][0]
        self.assertEqual("cli_syntax_error", failure["rule"])
        # Fence body opens on file line 4; the CLI's line 2 is file line 5.
        self.assertEqual(5, failure["source_line"])

    def test_a_diagram_the_cli_read_passes_and_records_the_version(self):
        result = self.run_verifier(self.DIAGRAM)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual("cli", payload["mode"])
        self.assertEqual(verify_mermaid.MERMAID_VERSION, payload["mermaid_version"])

    def test_geometry_that_cannot_run_is_warned_not_counted_as_checked(self):
        result = self.run_verifier(
            self.DIAGRAM, "--lint", cli=_StubCli(svg=b"<svg not really xml at all")
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(0, payload["lint"]["geometry_checked"])
        self.assertTrue(
            any("geometry" in warning for warning in payload["lint"]["warnings"]),
            payload["lint"]["warnings"],
        )

    def test_geometry_that_positions_no_declared_node_is_warned_not_counted(self):
        result = self.run_verifier(
            self.DIAGRAM,
            "--lint",
            cli=_StubCli(svg=b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 9 9"/>'),
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(0, payload["lint"]["geometry_checked"])
        self.assertTrue(
            any("positions none" in warning for warning in payload["lint"]["warnings"]),
            payload["lint"]["warnings"],
        )

    def test_overlapping_nodes_in_the_rendered_layout_fail_the_lint(self):
        overlapping = (
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
            b'<g class="node" transform="translate(10,10)">'
            b'<rect x="0" y="0" width="40" height="40"/></g>'
            b'<g class="node" transform="translate(20,20)">'
            b'<rect x="0" y="0" width="40" height="40"/></g></svg>'
        )
        result = self.run_verifier(self.DIAGRAM, "--lint", cli=_StubCli(svg=overlapping))
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn(
            "lint_geometry_overlap",
            [failure["rule"] for failure in payload["failures"]],
        )


class TestBoundaryInputs(_ScriptCase):
    def test_empty_file_reports_no_fence_and_exits_two(self):
        result = self.run_verifier("")
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("error", payload["status"])
        self.assertIn("No ```mermaid fenced block", payload["message"])

    def test_bom_only_file_reports_no_fence_and_exits_two(self):
        result = self.run_verifier_bytes("﻿".encode("utf-8"))
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("error", payload["status"])
        self.assertIn("No ```mermaid fenced block", payload["message"])

    def test_file_without_any_fence_passes_as_prose_only(self):
        result = self.run_verifier(
            "# Just a heading\n\nSome prose with no fence at all.\n", cli=None
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(0, payload["graphs"])
        self.assertEqual("prose-only", payload["mode"])

    def test_non_utf8_bytes_report_unreadable_and_exit_two(self):
        result = self.run_verifier_bytes(b"\xff\xfe\x00\x01garbage, not valid utf-8")
        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("error", payload["status"])
        self.assertIn("Could not read UTF-8 input", payload["message"])

    def test_bom_prefixed_fence_on_first_line_is_detected(self):
        raw = ("﻿```mermaid\nflowchart TD\n    a[\"x\"] --> b[\"y\"]\n```\n").encode("utf-8")
        result = self.run_verifier_bytes(raw)
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
        result = self.run_verifier(markdown)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(1, payload["graphs"])


class TestElkFrontmatter(_ScriptCase):
    def test_elk_frontmatter_diagram_passes_the_lint(self):
        result = self.run_verifier(
            "```mermaid\n"
            "---\n"
            "config:\n"
            "  layout: elk\n"
            "---\n"
            "flowchart TD\n"
            '    a["start work"] --> b["done"]\n'
            "```\n",
            "--lint",
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(1, payload["graphs"])


class TestLegibilityLint(_ScriptCase):
    """``--lint`` promotes legibility-contract violations to failures."""

    def _lint_rules(self, result):
        payload = json.loads(result.stdout)
        return payload, [failure["rule"] for failure in payload["failures"]]

    def _fan_out_source(self):
        lines = ["flowchart TD"]
        for index in range(5):
            lines.append(f'    hub["dispatch work"] --> t{index}["target {index}"]')
        return "\n".join(lines) + "\n"

    def test_each_legibility_rule_fails_under_lint(self):
        cases = (
            ("lint_forbidden_type", "beta suffix", "treemap-beta\n"),
            ("lint_fan_out", "five edges from one hub", self._fan_out_source()),
            (
                "lint_fan_out",
                "one ampersand list",
                "flowchart TD\n"
                '    hub["dispatch work"] --> a["t1"] & b["t2"] & c["t3"] & d["t4"] & e["t5"]\n',
            ),
            (
                "lint_subgraph_depth",
                "a subgraph inside a subgraph",
                "flowchart TD\n"
                "    subgraph outer\n"
                "        subgraph inner\n"
                '            z1["deep node"]\n'
                "        end\n"
                "    end\n",
            ),
            (
                "lint_direction_ignored",
                "direction inside an externally linked subgraph",
                "flowchart TD\n"
                "    subgraph s1\n"
                "        direction LR\n"
                '        x1["inside a"] --> x2["inside b"]\n'
                "    end\n"
                '    x2 --> y1["outside"]\n',
            ),
            (
                "lint_decision_unlabeled",
                "an unlabeled branch out of a decision",
                "flowchart TD\n"
                '    a["check input"] --> d{"valid?"}\n'
                '    d --> b["accept"]\n',
            ),
        )
        for rule, label, source in cases:
            with self.subTest(rule=rule, case=label):
                result = self.run_verifier("```mermaid\n%s```\n" % source, "--lint")
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                _payload, rules = self._lint_rules(result)
                self.assertIn(rule, rules)

    def test_forbidden_type_mindmap_fails_only_under_lint(self):
        source = "```mermaid\nmindmap\n  root\n```\n"
        self.assertEqual(0, self.run_verifier(source).returncode)
        result = self.run_verifier(source, "--lint")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        payload, rules = self._lint_rules(result)
        self.assertIn("lint_forbidden_type", rules)

    def test_node_budget_exceeded_fails_only_under_lint(self):
        lines = ["flowchart TD"]
        for index in range(34):
            lines.append(f'    n{index}["step {index}"] --> n{index + 1}["step {index + 1}"]')
        source = "```mermaid\n" + "\n".join(lines) + "\n```\n"
        self.assertEqual(0, self.run_verifier(source).returncode)
        result = self.run_verifier(source, "--lint")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        _payload, rules = self._lint_rules(result)
        self.assertIn("lint_node_budget", rules)

    def test_oversized_overview_on_staged_page_warns_but_passes(self):
        overview_lines = ["flowchart LR"]
        for index in range(8):
            overview_lines.append(f'    o{index}["phase {index}"] --> o{index + 1}["phase {index + 1}"]')
        source = (
            "```mermaid\n" + "\n".join(overview_lines) + "\n```\n\n"
            "```mermaid\nflowchart TD\n    a[\"detail a\"] --> b[\"detail b\"]\n```\n"
        )
        result = self.run_verifier(source, "--lint")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertTrue(
            any("overview budget" in warning for warning in payload["lint"]["warnings"]),
            payload["lint"]["warnings"],
        )

    def test_clean_diagram_passes_lint_with_warning_channel(self):
        result = self.run_verifier(
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
        self.assertEqual(1, payload["lint"]["geometry_checked"])


class TestStaticFences(_ScriptCase):
    """Static fences are verified without any Mermaid block or CLI."""

    def test_each_static_fence_rule_is_detected(self):
        cases = (
            ("invalid_vega_json", "```vega-lite\n{not json}\n```\n"),
            (
                "unbalanced_html",
                "```viz-html\n"
                '<div class="viz-steps"><ol><li>one</li></ol>\n'
                "```\n",
            ),
            ("viz_html_script", "```viz-html\n<div><script>alert(1)</script></div>\n```\n"),
            ("viz_html_inline_style", '```viz-html\n<div style="color: red">styled</div>\n```\n'),
            ("viz_html_external", '```viz-html\n<div><img src="https://example.com/x.png"></div>\n```\n'),
        )
        for rule, source in cases:
            with self.subTest(rule=rule):
                result = self.run_verifier(source, cli=None)
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertIn(rule, [failure["rule"] for failure in payload["failures"]])

    def test_vega_only_page_passes_with_chart_count(self):
        result = self.run_verifier(
            "```vega-lite\n"
            '{"mark": "bar", "data": {"values": []}}\n'
            "```\n",
            cli=None,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(0, payload["graphs"])
        self.assertEqual(1, payload["charts"])
        self.assertEqual("static-only", payload["mode"])

    def test_balanced_viz_html_passes(self):
        result = self.run_verifier(
            "```viz-html\n"
            '<table class="viz-compare"><tr><th>axis</th><td>value</td></tr></table>\n'
            "```\n",
            cli=None,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(1, payload["components"])
