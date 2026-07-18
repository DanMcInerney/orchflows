"""Runs tools/validate.py as a subprocess against the live repo, and
exercises the --pin flag against an isolated copy of contracts/."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.validate as validate  # noqa: E402

VALIDATE = ROOT / "tools" / "validate.py"
CONTRACTS = ROOT / "contracts"
PINS = ROOT / "tests" / "pins.json"


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


class TestSyntheticPackageBoundaryInputs(unittest.TestCase):
    """Full CLI runs (via the isolated tmp-copy pattern already used for
    --pin) against a synthetic skills/ tree, so the ERROR/exit-code contract
    is checked at the actual ROOT-relative seam, not just parse_frontmatter."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        shutil.copytree(CONTRACTS, self.tmp_path / "contracts")
        (self.tmp_path / "tools").mkdir()
        shutil.copy(VALIDATE, self.tmp_path / "tools" / "validate.py")
        self._run("--pin")  # matching pins so only the synthetic package can fail

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(self.tmp_path / "tools" / "validate.py"), *args],
            capture_output=True,
            text=True,
        )

    def _write_skill(self, name: str, content: bytes, tier: str = "instances"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_bytes(content)

    def _write_pack(self, name: str, content: bytes):
        pack_dir = self.tmp_path / "packs" / name
        pack_dir.mkdir(parents=True)
        (pack_dir / "SKILL.md").write_bytes(content)

    def test_missing_closing_fence_is_error_line_and_exit_1_no_traceback(self):
        self._write_skill(
            "badpkg",
            b"---\nname: badpkg\ndescription: missing closing fence\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing closing frontmatter fence", result.stdout)
        self.assertEqual("", result.stderr.strip())

    def test_bom_prefixed_valid_skill_md_is_not_falsely_flagged(self):
        body = (
            "---\nname: bompkg\ndescription: a bom-prefixed valid skill\nrole: worker\n---\n"
            "Require: one thing.\nNever: another thing.\nReturn: a result.\n"
        )
        self._write_skill("bompkg", b"\xef\xbb\xbf" + body.encode("utf-8"))
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn("missing opening frontmatter fence", result.stdout)

    def test_empty_skill_md_is_error_line_and_exit_1_no_traceback(self):
        self._write_skill("emptypkg", b"")
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing opening frontmatter fence", result.stdout)
        self.assertEqual("", result.stderr.strip())

    def test_skill_missing_role_is_error(self):
        self._write_skill(
            "norolepkg",
            b"---\nname: norolepkg\ndescription: a skill without a role\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing required key 'role'", result.stdout)

    def test_role_value_outside_allowed_set_is_error(self):
        self._write_skill(
            "badrolepkg",
            b"---\nname: badrolepkg\ndescription: a skill with a bad role\nrole: judge\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("role", result.stdout)
        self.assertIn("badrolepkg", result.stdout)

    def test_engine_declaring_role_other_than_none_is_error(self):
        self._write_skill(
            "someenginepkg",
            b"---\nname: someenginepkg\ndescription: an engine with a non-none role\nrole: worker\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
            tier="engines",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("engines skill must declare role: none", result.stdout)

    def test_workflow_declaring_role_other_than_none_is_error(self):
        self._write_skill(
            "someworkflowpkg",
            b"---\nname: someworkflowpkg\ndescription: a workflow with a non-none role\nrole: planner\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
            tier="workflows",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("workflows skill must declare role: none", result.stdout)

    def test_pack_declaring_role_at_all_is_error(self):
        self._write_pack(
            "somepack",
            b"---\nname: somepack\ndescription: a pack that wrongly declares a role\nrole: worker\n---\n"
            b"| slicing | x |\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("pack frontmatter must not declare 'role'", result.stdout)


if __name__ == "__main__":
    unittest.main()
