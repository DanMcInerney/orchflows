"""The two orch-visualize scripts: the Mermaid verifier's fence rules,
exit codes and boundary inputs, and the HTML renderer's self-containment,
cdn fallback and id salting.

Both subjects sit in skills/utilities/orch-visualize/scripts/, both are
driven with npx made unresolvable so the verifier's structural fallback
and the renderer's cdn fallback fire deterministically on any host, and
both once carried their own copy of that environment. Nothing here ever
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

# An empty PATH is a PATH shutil.which can resolve nothing on, whatever
# the host really has installed, so both fallbacks are taken by decision
# rather than by accident of what is on the machine. The vl-convert knob
# is the renderer's equivalent switch for the vega path.
NO_NPX = {"PATH": "", "ORCH_VIZ_NO_VLCONVERT": "1"}

Result = namedtuple("Result", "returncode stdout stderr")


def _no_npx_env():
    """`NO_NPX` over the real environment, for the two cases that still
    cross a process boundary."""
    env = dict(os.environ)
    env.update(NO_NPX)
    return env


class _ScriptCase(unittest.TestCase):
    """A private directory per case, and both entry points called
    in-process with npx unresolvable."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def call(self, module, argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, NO_NPX), contextlib.redirect_stdout(
            out
        ), contextlib.redirect_stderr(err):
            returncode = module.main([str(argument) for argument in argv])
        return Result(returncode, out.getvalue(), err.getvalue())

    def run_verifier(self, markdown: str, *extra_args: str):
        path = self.directory / "diagram.md"
        path.write_text(markdown, encoding="utf-8")
        return self.call(verify_mermaid, [path, *extra_args])

    def run_verifier_bytes(self, raw: bytes):
        path = self.directory / "diagram.md"
        path.write_bytes(raw)
        return self.call(verify_mermaid, [path])

    def run_renderer(self, markdown: str, name: str = "page.md", *extra_args: str):
        md = self.directory / name
        md.write_text(markdown, encoding="utf-8")
        return self.call(render_html, [md, *extra_args])

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
        # U+2225 and CJK are unencodable in cp1252; the verifier must judge
        # the diagram, not the console codepage (friction 2026-07-16).
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "diagram.md"
            path.write_text(
                "```mermaid\n"
                "flowchart TD\n"
                '    a["lanes ∥ in parallel 中文"] --> b["done"]\n'
                "```\n",
                encoding="utf-8",
            )
            result = self._run(VERIFIER, path)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(1, payload["graphs"])
        self.assertEqual("structural-only", payload["mode"])

    def test_cdn_fallback_html_shape_when_npx_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "page.md"
            path.write_text(SAMPLE, encoding="utf-8")
            result = self._run(RENDERER, path)
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


# --- verify_mermaid ----------------------------------------------------


class TestVerifierRobustness(_ScriptCase):
    def test_broken_diagram_still_fails_cleanly(self):
        result = self.run_verifier(
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


class TestStructuralFallbackRules(_ScriptCase):
    """Each structural-fallback rule pinned by one dedicated input that
    triggers exactly that rule and no other, with the failure carrying
    both the rule name and the structural_only marker. The three dangling
    forms differ only in the line that names the missing node, so they
    are rows here rather than three copies of one assertion."""

    CASES = (
        (
            "unknown_diagram_type",
            "notARealDiagramType\n    a --> b\n",
            None,
        ),
        (
            "duplicate_node_label",
            'flowchart TD\n    a["first label"] --> b["second"]\n'
            '    a["different label"] --> c["third"]\n',
            None,
        ),
        (
            "dangling_reference",
            'flowchart TD\n    a["start"] --> b["end"]\n'
            '    click missingNode "https://example.com"\n',
            "missingNode",
        ),
        (
            "dangling_reference",
            'flowchart TD\n    a["start"] --> b["end"]\n'
            "    style missingNode fill:#f00\n",
            "missingNode",
        ),
        (
            "dangling_reference",
            'flowchart TD\n    a["start"] --> b["end"]\n'
            "    class missingNode someClass\n",
            "missingNode",
        ),
    )

    def test_each_structural_rule_is_detected_alone_and_marked(self):
        for rule, source, named in self.CASES:
            with self.subTest(rule=rule, source=source):
                result = self.run_verifier("```mermaid\n%s```\n" % source)
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual("fail", payload["status"])
                self.assertEqual(
                    [rule], [failure["rule"] for failure in payload["failures"]]
                )
                self.assertTrue(payload["failures"][0]["structural_only"])
                if named is not None:
                    self.assertIn(named, payload["failures"][0]["message"])


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
        # nothing, so a fence-free prose page is a legal verified page.
        result = self.run_verifier("# Just a heading\n\nSome prose with no fence at all.\n")
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
        self.assertEqual("structural-only", payload["mode"])


class TestElkFrontmatter(_ScriptCase):
    def test_elk_frontmatter_diagram_passes_structural_check(self):
        result = self.run_verifier(
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
        self.assertEqual(0, payload["lint"]["geometry_checked"])


class TestStaticFences(_ScriptCase):
    """vega-lite and viz-html fences are verified without any mermaid block."""

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
                result = self.run_verifier(source)
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertIn(rule, [failure["rule"] for failure in payload["failures"]])

    def test_vega_only_page_passes_with_chart_count(self):
        result = self.run_verifier(
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

    def test_balanced_viz_html_passes(self):
        result = self.run_verifier(
            "```viz-html\n"
            '<table class="viz-compare"><tr><th>axis</th><td>value</td></tr></table>\n'
            "```\n"
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("pass", payload["status"])
        self.assertEqual(1, payload["components"])


# --- render_html -------------------------------------------------------


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
        result = self.call(render_html, [md, "--out", out])
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

    def test_oversized_fence_body_still_renders_without_crashing(self):
        lines = ["flowchart TD"]
        node_count = 2000
        for index in range(node_count):
            lines.append(f'    n{index}["label {index}"] --> n{index + 1}["label {index + 1}"]')
        source = "\n".join(lines) + "\n"
        markdown = f"# Big\n\n```mermaid\n{source}```\n"
        result = self.run_renderer(markdown)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("rendered", payload["status"])
        self.assertEqual(1, payload["graphs"])
        self.assertEqual("cdn", payload["mode"])
        page = Path(payload["page"]).read_text(encoding="utf-8")
        self.assertIn('<pre class="mermaid">', page)
        self.assertIn("label 1999", page)


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

    def test_vega_lite_fence_falls_back_to_cdn(self):
        result = self.run_renderer(
            "```vega-lite\n"
            '{"mark": "bar", "data": {"values": [{"x": 1}]}}\n'
            "```\n"
        )
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
