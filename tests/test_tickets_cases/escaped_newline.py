"""A literal backslash-n in a semantic section: one owner, two doors.

friction/2026-08.jsonl, 2026-08-30T21:02:18Z: `tickets.py new --context`
accepted a shell string carrying an escaped newline and collapsed three
intake bullets onto one stored line; lint and admission both passed it, and
only a checker reading stored bytes saw the collapse. `format_policy_defects`
is the one shape-defect owner both `new` (refusal) and `lint` (finding)
already read through `ticket_defects` -> `_issue_defects`, so a fix there
reaches both doors without a second reader.
"""

import unittest

from .common import *  # noqa: F401,F403


class EscapedNewlineShapeTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.sink = use_sink(Path(self.temporary.name))

    def tearDown(self):
        self.temporary.cleanup()

    def dispatch(self, *arguments):
        return tickets_mod._dispatch(list(arguments))

    def test_new_refuses_the_exact_collapsed_bullet_shape(self):
        """The friction repro, verbatim: three bullets joined by `\\n`."""
        refused = self.dispatch(
            "new", "testrun", "T1", "--executor", "orch-do",
            "--goal", "Deliver the artifact.",
            "--context", "- one\\n- two\\n- three",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.assertIn("error", refused)
        self.assertIn("backslash-n", refused["error"])
        self.assertIn("Context", refused["error"])
        self.assertFalse((self.sink / "tickets" / "testrun" / "T1.md").exists())

    def test_new_accepts_a_real_multiline_context(self):
        """An actual line break is invisible to the check -- it is one byte,
        not the two-character escape."""
        accepted = self.dispatch(
            "new", "testrun", "T2", "--executor", "orch-do",
            "--goal", "Deliver the artifact.",
            "--context", "line one\nline two\nline three",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.assertNotIn("error", accepted)

    def test_new_accepts_a_windows_path_segment_beginning_with_n(self):
        """A rooted Windows path is read as the path it is, not the escape."""
        accepted = self.dispatch(
            "new", "testrun", "T3", "--executor", "orch-do",
            "--goal", "Deliver the artifact.",
            "--context",
            "Evidence: C:\\Users\\danhm\\.orchflows\\state\\notes\\thing.md.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.assertNotIn("error", accepted)

    def test_new_accepts_the_escape_inside_a_fenced_code_block(self):
        """A fenced code block is read as code, not prose."""
        fenced_goal = (
            "Deliver the parser.\n\n```\nassert body.split('\\n') == parts\n```"
        )
        accepted = self.dispatch(
            "new", "testrun", "T4", "--executor", "orch-do",
            "--goal", fenced_goal, "--context", "[]",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.assertNotIn("error", accepted)

    def test_new_accepts_the_escape_inside_an_inline_code_span(self):
        """The repository's own idiom for naming a newline in prose -- a
        backticked fragment such as `newline=` or "rstrip of a newline" --
        is not the collapsed-bullet defect. Only fenced code was exempt
        before; this is the same exemption for one unfenced line.

        Regression for state sink run 20260831T001500Z-friction-fixes,
        finding F3: measured on the live state sink, 41 of 67 tickets the
        prior discriminator newly flagged were flagged only because they
        named the escape inside an inline backtick span like this one.
        """
        accepted = self.dispatch(
            "new", "testrun", "T4b", "--executor", "orch-do",
            "--goal", "Deliver the artifact.",
            "--context", "Pass `newline=\\n` to open() and rstrip a newline.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.assertNotIn("error", accepted)

    def test_new_still_refuses_the_collapsed_shape_beside_an_inline_span(self):
        """The inline-code exemption protects only its own span: a real
        collapsed bullet elsewhere on the same line still refuses, so the
        exemption cannot be used to smuggle the defect past the check."""
        refused = self.dispatch(
            "new", "testrun", "T4c", "--executor", "orch-do",
            "--goal", "Deliver the artifact.",
            "--context", "See `newline=\\n` for context. - one\\n- two\\n- three",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.assertIn("error", refused)
        self.assertIn("backslash-n", refused["error"])
        self.assertIn("Context", refused["error"])

    def test_lint_reports_the_same_defect_on_an_issued_ticket(self):
        """The corruption the friction entry describes: a checker reading
        stored bytes, after the shell has already done the collapsing --
        here simulated by a direct write past the CLI, since a fixed `new`
        can no longer produce this ticket itself."""
        accepted = self.dispatch(
            "new", "testrun", "T5", "--executor", "orch-do",
            "--goal", "Deliver the artifact.", "--context", "[]",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.assertNotIn("error", accepted)
        path = Path(accepted["new"]["path"])
        corrupted = path.read_text(encoding="utf-8").replace(
            "## Report\n", "## Report\n\nfirst\\nsecond\n", 1,
        )
        path.write_text(corrupted, encoding="utf-8")

        linted = self.dispatch("lint", "testrun", "T5")
        messages = [item["message"] for item in linted["lint"]["findings"]]
        self.assertTrue(
            any("backslash-n" in message and "Report" in message for message in messages),
            messages,
        )
        self.assertEqual(1, linted["exit_code"])

    def test_new_refusal_and_lint_finding_share_one_message(self):
        """One shape-defect owner: `new`'s refusal and `lint`'s finding on
        the same broken text read identically, because both call
        `ticket_defects` through `_issue_defects`."""
        from scripts.tickets_format import ticket_defects
        from scripts.tickets_issue_render import _render_ticket

        fields = {
            "id": "T6", "run": "testrun", "status": "pending",
            "admission": "pending", "executor": "orch-do",
            "pack": "orch-code-pack", "independence": "gate",
            "depends_on": [], "isolation": "required", "bound": "30m",
        }
        sections = [
            ("Goal", "Deliver the artifact."),
            ("Context", "note one\\nnote two"),
            ("Report", ""),
        ]
        text = _render_ticket(fields, sections)
        defects = ticket_defects(text)
        matches = [d for d in defects if "backslash-n" in d]
        self.assertEqual(1, len(matches), defects)

        refused = self.dispatch(
            "new", "testrun", "T7", "--executor", "orch-do",
            "--goal", "Deliver the artifact.",
            "--context", "note one\\nnote two",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.assertIn(matches[0], refused["error"])


if __name__ == "__main__":
    unittest.main()
