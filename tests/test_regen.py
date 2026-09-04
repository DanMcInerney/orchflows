"""Every derived artifact has one regeneration owner, and drift fails the gate.

`tools/regen.py` declares which artifact belongs to which generator; this file
proves the declaration is complete, that a hand-edited artifact is named along
with the exact command that repairs it, and that `tools/validate.py` -- one of
the five required checks -- refuses the tree while any of them is stale.

Every case works on a fixture tree. The live tree's verdict belongs to the
gate, not to a test that would fail for the whole repository whenever a
generator input legitimately moves mid-change.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import regen, serial_manifest
from tools import validate


from tests._repo_root import ROOT
RUNNER = ROOT / "tools" / "run_serial_compat.py"

ONE_CASE = (
    "import unittest\n\n\nclass Fixture(unittest.TestCase):\n"
    "    def test_one(self):\n        self.assertTrue(True)\n"
)
SECOND_CASE = "\n    def test_two(self):\n        self.assertTrue(True)\n"
# Every scan emits this synthetic owner, so a fixture manifest that omits its
# ruling is refused before the fixture tree contributes anything of its own.
RULED_BASELINE = {
    "module": "<suite>",
    "owner": "discovery-baseline",
    "restoration": "selected-module-boundary",
    "seams": ["environment"],
}


def _cli(root: Path, *extra) -> dict:
    """Drive the tool the way a gate drives it, and read its one report line."""

    done = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "regen.py"), "--check", "--json",
         "--only", "serial-compat-manifest", "--root", str(root), "--no-cache", *extra],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    assert done.returncode in (0, 1), done.stdout + done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def _seed_manifest(path: Path, identities) -> None:
    document = {
        "schema": "orchflows.serial-compat.v1",
        "discovery": {"identities": list(identities)},
        "mutation_owners": [dict(RULED_BASELINE)],
        "sentinels": [
            {"categories": ["discovery"], "id": "test_fixture.Fixture.test_one",
             "module": "test_fixture"},
        ],
    }
    path.write_bytes(serial_manifest.render(document).encode("utf-8"))


class ManifestFixture:
    """A tree carrying only the serial-compat artifact and its inputs."""

    def __init__(self, case: unittest.TestCase, *, fresh: bool):
        directory = tempfile.TemporaryDirectory(prefix="regen-manifest-")
        case.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.tests = self.root / "tests"
        self.tests.mkdir()
        self.module = self.tests / "test_fixture.py"
        self.module.write_text(ONE_CASE, encoding="utf-8")
        self.manifest = self.tests / "serial_compat_manifest.json"
        _seed_manifest(self.manifest, ["test_fixture.Fixture.test_stale"])
        if fresh:
            self.reconcile(case)

    def reconcile(self, case: unittest.TestCase) -> None:
        """Regenerate through the owner itself, in its own interpreter."""

        done = subprocess.run(
            [sys.executable, str(RUNNER), "--write-manifest",
             "--manifest", str(self.manifest), "--tests-dir", str(self.tests)],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
        )
        case.assertEqual(0, done.returncode, done.stdout + done.stderr)


class TestDeclaration(unittest.TestCase):
    def test_the_manifest_covers_every_artifact_the_spec_names(self):
        self.assertEqual(
            {
                "t0-shapes", "lifecycle", "ci-topology", "host-adapters",
                "serial-compat-manifest",
            },
            set(regen.NAMES),
        )
        self.assertEqual(len(regen.NAMES), len(set(regen.NAMES)))

    def test_every_declared_command_names_a_tool_that_exists(self):
        for record in regen.ARTIFACTS:
            parts = record.command.split()
            script = next(part for part in parts if part.endswith(".py"))
            self.assertTrue((ROOT / script).is_file(), record.command)
            self.assertTrue(callable(record.stale), record.name)
            self.assertTrue(callable(record.write), record.name)
            self.assertTrue(record.drift, record.name)

    def test_the_costly_artifact_declares_its_whole_input_closure(self):
        """A memo over a partial closure is a gate that stops biting."""

        record = regen.artifact("serial-compat-manifest")
        self.assertTrue(record.costly)
        self.assertEqual(
            {"tests/**/*.py", "tests/serial_compat_manifest.json",
             "tools/run_serial_compat.py", "tools/serial_manifest.py"},
            set(record.inputs),
        )
        for other in regen.ARTIFACTS:
            if not other.costly:
                self.assertEqual((), other.inputs, other.name)


class TestAbsentOwners(unittest.TestCase):
    def test_a_tree_without_the_owners_is_skipped_and_says_so(self):
        with tempfile.TemporaryDirectory() as directory:
            findings = regen.check(Path(directory), cache=False)
        self.assertEqual([], [item for item in findings if item.level == "error"])
        skipped = {item.artifact for item in findings if item.level == "warn"}
        self.assertIn("serial-compat-manifest", skipped)
        self.assertIn("t0-shapes", skipped)


class TestHostAdapters(unittest.TestCase):
    def _tree(self) -> Path:
        directory = tempfile.TemporaryDirectory(prefix="regen-hosts-")
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        shutil.copytree(ROOT / "hosts", root / "hosts")
        shutil.copytree(ROOT / "installer" / "host_adapters", root / "installer" / "host_adapters")
        (root / "templates").mkdir()
        shutil.copyfile(ROOT / "templates" / "host-block.md", root / "templates" / "host-block.md")
        return root

    def test_a_faithful_copy_of_the_rendered_adapters_is_current(self):
        self.assertEqual([], regen.check(self._tree(), ("host-adapters",), cache=False))

    def test_a_hand_edited_adapter_is_named_beside_its_regeneration_command(self):
        root = self._tree()
        target = root / "installer" / "host_adapters" / "claude.json"
        document = json.loads(target.read_text(encoding="utf-8"))
        document["source_sha256"] = "0" * 64
        target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        findings = regen.check(root, ("host-adapters",), cache=False)

        self.assertEqual(1, len(findings), findings)
        self.assertEqual("error", findings[0].level)
        self.assertEqual(("installer/host_adapters/claude.json",), findings[0].paths)
        self.assertIn("tools/render_hosts.py --write", findings[0].message)


class TestGeneratedShapes(unittest.TestCase):
    def _tree(self) -> Path:
        directory = tempfile.TemporaryDirectory(prefix="regen-shapes-")
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        shutil.copytree(ROOT / "contracts", root / "contracts")
        (root / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts" / "tickets_shapes.py", root / "scripts" / "tickets_shapes.py")
        return root

    def test_a_hand_edited_generated_validator_is_named(self):
        root = self._tree()
        target = root / "scripts" / "tickets_shapes.py"
        target.write_text(target.read_text(encoding="utf-8") + "HAND = 1\n", encoding="utf-8")

        findings = regen.check(root, ("t0-shapes",), cache=False)

        self.assertEqual(("scripts/tickets_shapes.py",), findings[0].paths)
        self.assertIn("tools/render_shapes.py --write", findings[0].message)

    def test_an_unreadable_declaration_fails_closed_rather_than_passing(self):
        root = self._tree()
        (root / "contracts" / "shapes.json").write_text("{ not json", encoding="utf-8")

        findings = regen.check(root, ("t0-shapes",), cache=False)

        self.assertEqual(1, len(findings), findings)
        self.assertEqual("error", findings[0].level)
        self.assertIn("could not be regenerated", findings[0].message)
        self.assertIn("tools/render_shapes.py --write", findings[0].message)


class TestSerialCompatManifest(unittest.TestCase):
    def test_a_manifest_the_tree_outgrew_is_named_with_its_command(self):
        fixture = ManifestFixture(self, fresh=False)

        findings = regen.check(fixture.root, ("serial-compat-manifest",), cache=False)

        self.assertEqual(1, len(findings), findings)
        self.assertEqual(("tests/serial_compat_manifest.json",), findings[0].paths)
        self.assertIn("tools/run_serial_compat.py --write-manifest", findings[0].message)

    def test_the_child_interpreter_and_this_one_return_the_same_verdict(self):
        """The spawn exists to keep a fixture test tree out of the caller."""

        fixture = ManifestFixture(self, fresh=False)
        spawned = regen.check(fixture.root, ("serial-compat-manifest",), cache=False)

        self.assertEqual(("tests/serial_compat_manifest.json",), spawned[0].paths)
        # Read-only: the spawned check must not have imported the fixture suite
        # into this interpreter, which is the whole reason it is spawned.
        self.assertNotIn("test_fixture", sys.modules)
        self.assertEqual(
            {"serial-compat-manifest": ["tests/serial_compat_manifest.json"]},
            _cli(fixture.root, "--no-spawn")["stale"],
        )

    def test_a_reconciled_manifest_is_current(self):
        fixture = ManifestFixture(self, fresh=True)
        self.assertEqual(
            [], regen.check(fixture.root, ("serial-compat-manifest",), cache=False)
        )


class TestInputClosureMemo(unittest.TestCase):
    def test_a_verified_artifact_is_not_re_run_until_an_input_byte_moves(self):
        fixture = ManifestFixture(self, fresh=True)
        calls = []
        real = regen._spawned_stale

        def counted(root, name):
            calls.append(name)
            return real(root, name)

        regen._spawned_stale = counted
        try:
            self.assertEqual([], regen.check(fixture.root, ("serial-compat-manifest",)))
            self.assertEqual(1, len(calls))
            self.assertEqual([], regen.check(fixture.root, ("serial-compat-manifest",)))
            self.assertEqual(1, len(calls), "a memo hit must not re-run the generator")

            fixture.module.write_text(ONE_CASE + SECOND_CASE, encoding="utf-8")
            findings = regen.check(fixture.root, ("serial-compat-manifest",))
            self.assertEqual(2, len(calls), "an input edit must miss the memo")
        finally:
            regen._spawned_stale = real
        self.assertEqual(("tests/serial_compat_manifest.json",), findings[0].paths)
        self.assertTrue(regen._cache_path(fixture.root).is_file())

    def test_the_fingerprint_covers_the_generator_source_not_only_its_inputs(self):
        record = regen.artifact("serial-compat-manifest")
        first = regen._fingerprint(ROOT, record.inputs)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "tests").mkdir()
            (root / "tools" / "serial_manifest.py").write_text("x\n", encoding="utf-8")
            second = regen._fingerprint(root, record.inputs)
        self.assertNotEqual(first, second)


class TestValidateGate(unittest.TestCase):
    """The acceptance: a stale derived artifact fails one of the five checks."""

    def _findings(self, root: Path, names=None) -> list:
        prior = validate.ROOT
        try:
            validate.ROOT = root
            diag = validate.Diagnostics()
            if names is None:
                validate.validate_regenerated_artifacts(diag)
            else:
                validate.validate_regenerated_artifacts(diag, names)
        finally:
            validate.ROOT = prior
        return diag, diag.lines()

    def _shapes_tree(self, declare_a_field: bool) -> Path:
        """contracts/ plus the generated validator, optionally with one
        field added to the declaration and nothing re-rendered."""

        directory = tempfile.TemporaryDirectory(prefix="regen-shapes-gate-")
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        shutil.copytree(ROOT / "contracts", root / "contracts")
        (root / "scripts").mkdir()
        shutil.copyfile(
            ROOT / "scripts" / "tickets_shapes.py", root / "scripts" / "tickets_shapes.py"
        )
        if declare_a_field:
            source = root / "contracts" / "shapes.json"
            document = json.loads(source.read_text(encoding="utf-8"))
            declaration = document["shapes"][0]
            declaration["fields"].append("an_undeclared_field")
            source.write_text(
                json.dumps(document, indent=2, sort_keys=True) + chr(10),
                encoding="utf-8",
            )
        return root

    def test_a_stale_serial_manifest_fails_validate_and_names_the_command(self):
        fixture = ManifestFixture(self, fresh=False)

        diag, lines = self._findings(fixture.root)

        self.assertTrue(diag.has_errors)
        stale = [line for line in lines if line.startswith("ERROR")]
        self.assertEqual(1, len(stale), lines)
        self.assertIn("tests/serial_compat_manifest.json", stale[0])
        self.assertIn("tools/run_serial_compat.py --write-manifest", stale[0])

    def test_a_reconciled_tree_draws_no_error_from_the_same_gate(self):
        fixture = ManifestFixture(self, fresh=True)

        diag, lines = self._findings(fixture.root)

        self.assertFalse(diag.has_errors, lines)

    def test_a_field_added_to_shapes_json_without_re_rendering_fails_validate(self):
        """The one structural check the T0 pin apparatus left behind: the
        declaration is the source, every contract table and the generated
        validator are rendered from it, and an unrendered edit is refused
        by name with the command that repairs it."""

        root = self._shapes_tree(declare_a_field=True)

        diag, lines = self._findings(root, ("t0-shapes",))

        self.assertTrue(diag.has_errors, lines)
        stale = [line for line in lines if line.startswith("ERROR")]
        self.assertTrue(stale, lines)
        self.assertIn("tools/render_shapes.py --write", stale[0])

    def test_the_same_tree_re_rendered_draws_no_error(self):
        """Can-fail reading for the case above: the gate answers to the
        unrendered edit, not to the fixture tree's own shape."""

        root = self._shapes_tree(declare_a_field=False)

        diag, lines = self._findings(root, ("t0-shapes",))

        self.assertFalse(diag.has_errors, lines)


class TestCommandSurface(unittest.TestCase):
    def test_writing_refuses_to_be_pointed_at_another_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            done = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "regen.py"), "--root", directory],
                cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
            )
        self.assertEqual(2, done.returncode, done.stdout + done.stderr)
        self.assertIn("never writes", done.stdout + done.stderr)

    def test_the_check_reports_one_machine_readable_line(self):
        fixture = ManifestFixture(self, fresh=False)
        report = _cli(fixture.root)
        self.assertEqual(
            {"serial-compat-manifest": ["tests/serial_compat_manifest.json"]},
            report["stale"],
        )
        self.assertEqual({}, report["failed"])


if __name__ == "__main__":
    unittest.main()
