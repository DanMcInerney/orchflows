"""The two orch-visualize scripts: the Mermaid verifier's fence rules,
exit codes and boundary inputs, and the HTML renderer's self-containment,
refusals and id salting.

Both subjects sit in skills/utilities/orch-visualize/scripts/. Neither
has a fallback tier: the verifier judges a diagram only when the pinned
Mermaid CLI read it, and the renderer produces inline SVG or nothing. So
the CLI is stubbed at the one boundary either script crosses --
`subprocess.run` -- by `_StubCli`, which chooses the exit code, the
diagnostic text and the SVG left behind; the scripts' own reading of
that output stays under test. Cases that want no CLI at all pass
`cli=None` and run with `PATH` emptied, which is a PATH `shutil.which`
resolves nothing on whatever the host really has installed; the case
that wants no vl-convert makes its import fail through `sys.modules`,
so the renderer's real import branch is what refuses. Nothing here ever
spawns npx or a Mermaid CLI process.

Each case calls the script's own `main` in-process under a redirected
stdout, the pattern tests/test_cutcheck.py:2534-2562 sets: a subprocess
per case bought an interpreter start-up and two module imports for work
that takes milliseconds, three seconds across forty-one cases. The two
smoke cases keep the command-line entry itself covered -- argv reaching
`main`, its return value arriving as a process exit code, and the UTF-8
bytes it puts on a real stdout whose console codepage cannot encode
them, which is the defect the verifier's unicode case was written for
and which no in-process call can reach.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "utilities" / "orch-visualize" / "scripts"
# The one path mutation this module makes, at import and for both
# subjects, replacing the per-test insert render_html's salting case used
# to do inside its own body.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import render_html  # noqa: E402
import verify_mermaid  # noqa: E402

VERIFIER = SCRIPTS / "verify_mermaid.py"
RENDERER = SCRIPTS / "render_html.py"

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

# One node box inside a viewBox that contains it: the geometry checks
# read this and find nothing wrong, so a case that wants a geometry
# finding says so with its own SVG rather than by accident of this one.
FAKE_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
    b'<g class="node" transform="translate(10,10)">'
    b'<rect x="0" y="0" width="40" height="20"/></g></svg>'
)

# An empty PATH is a PATH shutil.which can resolve nothing on, whatever
# the host really has installed, so the no-CLI cases refuse by decision
# rather than by accident of what is on the machine.
NO_NPX = {"PATH": ""}

Result = namedtuple("Result", "returncode stdout stderr")


def _no_npx_env():
    """`NO_NPX` over the real environment, for the two cases that still
    cross a process boundary."""
    env = dict(os.environ)
    env.update(NO_NPX)
    return env


class _StubCli:
    """The pinned Mermaid CLI, stubbed at `subprocess.run`.

    A case names the CLI's exit code, the text it writes and the bytes it
    leaves at the `-o` path (the last argument of the command both
    scripts build). Everything the scripts do with that -- locating a
    syntax error, insisting on an `<svg>` element, reading geometry --
    runs for real."""

    def __init__(self, returncode: int = 0, stderr: str = "", svg=FAKE_SVG):
        self.returncode = returncode
        self.stderr = stderr
        self.svg = svg
        self.calls = 0

    def __call__(self, command, **kwargs):
        self.calls += 1
        if self.svg is not None:
            Path(command[-1]).write_bytes(self.svg)
        return subprocess.CompletedProcess(command, self.returncode, "", self.stderr)


class _ScriptCase(unittest.TestCase):
    """A private directory per case, both entry points called in-process,
    and the Mermaid CLI stubbed unless the case asks for none."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def call(self, module, argv, cli=None):
        out, err = io.StringIO(), io.StringIO()
        patches = [mock.patch.dict(os.environ, NO_NPX)]
        if cli is not None:
            patches.append(mock.patch.object(module, "_find_npx", lambda: "npx"))
            patches.append(mock.patch.object(subprocess, "run", cli))
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(contextlib.redirect_stderr(err))
            returncode = module.main([str(argument) for argument in argv])
        return Result(returncode, out.getvalue(), err.getvalue())

    def run_verifier(self, markdown: str, *extra_args: str, cli=_StubCli()):
        path = self.directory / "diagram.md"
        path.write_text(markdown, encoding="utf-8")
        return self.call(verify_mermaid, [path, *extra_args], cli=cli)

    def run_verifier_bytes(self, raw: bytes, cli=_StubCli()):
        path = self.directory / "diagram.md"
        path.write_bytes(raw)
        return self.call(verify_mermaid, [path], cli=cli)

    def run_renderer(self, markdown: str, *extra_args: str, name: str = "page.md",
                     cli=None):
        md = self.directory / name
        md.write_text(markdown, encoding="utf-8")
        return self.call(render_html, [md, *extra_args], cli=cli)

    def run_renderer_bytes(self, raw: bytes, name: str = "page.md"):
        md = self.directory / name
        md.write_bytes(raw)
        return self.call(render_html, [md])


# --- the command line itself ------------------------------------------


class TestCommandLineEntry(unittest.TestCase):
    """One subprocess per script: everything above the scripts' `main`.

    An in-process call cannot see argv parsing, the exit code as the
    shell reads it, or the encoding of a real stdout -- and the last of
    those is a defect these scripts actually had."""

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


# --- verify_mermaid ----------------------------------------------------


class TestVerifierRequiresTheMermaidCli(_ScriptCase):
    """No CLI is not a verdict. With npx unresolvable, or with a CLI that
    ran but could not judge, the verifier refuses (exit 2) and names the
    cause -- it never reports a pass the Mermaid parser never confirmed."""

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
        # A well-formed SVG carrying none of the source's nodes as
        # positioned boxes measured nothing; that is not a clean layout.
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
        # The form ladder's first rungs (sentence, list, table) draw
        # nothing, so a fence-free prose page is a legal verified page --
        # and one no CLI is needed for.
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
        # Regression: the verifier read input as plain "utf-8", leaving a
        # leading BOM as a literal U+FEFF character. That defeated the
        # fence regex's `^` anchor for a fence starting on line 1, so a
        # valid BOM-prefixed diagram was reported as "no fence" (exit 2)
        # even though render_html.py (which reads "utf-8-sig") renders the
        # same file correctly.
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
    """--lint promotes legibility-contract violations to failures; without
    the flag the same inputs keep the historical pass behavior."""

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
    """vega-lite and viz-html fences are verified without any mermaid
    block -- and so without any CLI."""

    def test_each_static_fence_rule_is_detected(self):
        cases = (
            ("invalid_vega_json", "```vega-lite\n{not json}\n```\n"),
            (
                "unbalanced_html",
                "```viz-html\n"
                '<div class="viz-steps"><ol><li>one</li></ol>\n'
                "```\n",
            ),
            (
                "viz_html_script",
                "```viz-html\n<div><script>alert(1)</script></div>\n```\n",
            ),
            (
                "viz_html_inline_style",
                "```viz-html\n<div style=\"color: red\">styled</div>\n```\n",
            ),
            (
                "viz_html_external",
                "```viz-html\n<div><img src=\"https://example.com/x.png\"></div>\n```\n",
            ),
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


# --- render_html -------------------------------------------------------


class TestRendererHasNoCdnMode(_ScriptCase):
    """The page carries its diagrams as inline SVG or it is not written.

    There is no `<pre class="mermaid">` tier loading Mermaid from a CDN at
    view time, and so no "cdn" mode for a caller to have to refuse: an
    unrendered fence is an error naming its cause."""

    def test_a_rendered_page_is_inline_svg_and_loads_nothing(self):
        result = self.run_renderer(SAMPLE, cli=_StubCli())
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("rendered", payload["status"])
        self.assertNotIn("mode", payload)  # one way to render leaves no mode to report
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
            # `vl_convert` mapped to None makes its import raise on any
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
        """The renderer's other exit-2 branch, and the only one that fires
        after the page has been built: a readable input whose `--out` can
        not be written. Untested until the two scripts' cases sat side by
        side -- the read branch had a case on both scripts and the write
        branch had none, and an unhandled OSError here would surface as a
        traceback with a half-rendered page and no JSON verdict."""

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
    """render_html tolerates inputs verify_mermaid would reject: a page
    with no mermaid fence at all is still valid prose to render."""

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


if __name__ == "__main__":
    unittest.main()
