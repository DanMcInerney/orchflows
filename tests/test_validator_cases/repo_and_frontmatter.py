"""Repository and frontmatter validator regression cases."""
import subprocess
import sys
import unittest

from .support import VALIDATE, validate

class TestValidatorAgainstRepo(unittest.TestCase):
    def test_repo_passes_clean(self):
        result = subprocess.run(
            [sys.executable, str(VALIDATE)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            0,
            result.returncode,
            f"validate.py exited {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )


class TestFrontmatterBoundaryInputs(unittest.TestCase):
    """parse_frontmatter is the seam every discovered package's SKILL.md
    passes through; these exercise it directly at boundary inputs without
    needing a full synthetic repo tree."""

    def test_empty_file_produces_error_not_traceback(self):
        diag = validate.Diagnostics()
        fm, body = validate.parse_frontmatter("", "empty.md", diag)
        self.assertIsNone(fm)
        self.assertIsNone(body)
        self.assertTrue(diag.has_errors)
        self.assertIn("missing opening frontmatter fence", diag.lines()[0])

    def test_missing_closing_fence_produces_error_not_traceback(self):
        diag = validate.Diagnostics()
        fm, body = validate.parse_frontmatter(
            "---\nname: foo\ndescription: bar\n", "noclose.md", diag
        )
        self.assertIsNone(fm)
        self.assertIsNone(body)
        self.assertTrue(diag.has_errors)
        self.assertIn("missing closing frontmatter fence", diag.lines()[0])

    def test_malformed_line_without_colon_is_an_error_and_parsing_continues(self):
        diag = validate.Diagnostics()
        fm, body = validate.parse_frontmatter(
            "---\nname: foo\nnot-a-kv-line\ndescription: bar\n---\nbody\n",
            "malformed.md", diag,
        )
        self.assertEqual({"name": "foo", "description": "bar"}, fm)
        self.assertEqual("body\n", body)
        self.assertTrue(diag.has_errors)
        self.assertIn("malformed frontmatter line", diag.lines()[0])

    def test_oversized_single_line_body_does_not_crash(self):
        huge_line = "x" * (2 * 1024 * 1024)
        text = f"---\nname: foo\ndescription: bar\n---\n{huge_line}\n"
        diag = validate.Diagnostics()
        fm, body = validate.parse_frontmatter(text, "huge.md", diag)
        self.assertEqual({"name": "foo", "description": "bar"}, fm)
        self.assertEqual(huge_line, body.strip())
        self.assertFalse(diag.has_errors)
