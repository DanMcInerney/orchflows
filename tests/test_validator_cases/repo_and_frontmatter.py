"""Repository, pin, and frontmatter validator regression cases."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .support import CONTRACTS, PINS, ROOT, VALIDATE, validate

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


class TestPinFlagRoundTrip(unittest.TestCase):
    """--pin runs against an isolated temp copy so it never mutates the
    real tests/pins.json while the suite runs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        shutil.copytree(CONTRACTS, self.tmp_path / "contracts")
        (self.tmp_path / "tools").mkdir()
        shutil.copy(VALIDATE, self.tmp_path / "tools" / "validate.py")
        shutil.copytree(ROOT / "tools" / "validate_support", self.tmp_path / "tools" / "validate_support")
        (self.tmp_path / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "doclint.py", self.tmp_path / "scripts" / "doclint.py")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(self.tmp_path / "tools" / "validate.py"), *args],
            capture_output=True,
            text=True,
        )

    def test_pin_creates_pins_matching_contracts(self):
        result = self._run("--pin")
        self.assertEqual(0, result.returncode, result.stderr)

        pins_path = self.tmp_path / "tests" / "pins.json"
        self.assertTrue(pins_path.is_file())
        pins = json.loads(pins_path.read_text(encoding="utf-8"))

        expected_names = {f.name for f in CONTRACTS.glob("*.md")}
        self.assertEqual(expected_names, set(pins))
        for name in expected_names:
            self.assertRegex(pins[name], r"^[0-9a-f]{64}$")

    def test_pin_is_idempotent(self):
        first = self._run("--pin")
        before = (self.tmp_path / "tests" / "pins.json").read_text(encoding="utf-8")
        second = self._run("--pin")
        after = (self.tmp_path / "tests" / "pins.json").read_text(encoding="utf-8")
        self.assertEqual(0, first.returncode)
        self.assertEqual(0, second.returncode)
        self.assertEqual(before, after)

    def test_pin_matches_committed_pins_json(self):
        self._run("--pin")
        generated = json.loads((self.tmp_path / "tests" / "pins.json").read_text(encoding="utf-8"))
        committed = json.loads(PINS.read_text(encoding="utf-8"))
        self.assertEqual(committed, generated)

    def test_missing_or_stale_pin_fails_validation(self):
        (self.tmp_path / "tests").mkdir()
        (self.tmp_path / "tests" / "pins.json").write_text(
            json.dumps({"verdict.md": "0" * 64}), encoding="utf-8"
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("T0 contract changed", result.stdout)


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
