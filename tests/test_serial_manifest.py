"""The serial-compatibility manifest regenerates itself from live facts.

Every case but the last works on a fixture tests tree, so the generator is
proved against a suite whose discovery this file controls rather than against
the live `tests/`, whose count changes with every commit. The last case is
the exception that has to look at the committed file: it asserts the bytes on
disk are exactly what regeneration would write, which is what makes the rest
of this suite a guard over the real manifest rather than over a fixture.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools import serial_manifest
from tools.run_serial_compat import RESTORATIONS, load_manifest


from tests._repo_root import ROOT
MANIFEST = ROOT / "tests" / "serial_compat_manifest.json"
POLICY = ROOT / "tools" / "serial-compat-policy.md"
RUNNER = ROOT / "tools" / "run_serial_compat.py"

ONE_CASE = textwrap.dedent(
    """
    import unittest


    class Fixture(unittest.TestCase):
        def test_one(self):
            self.assertTrue(True)
    """
).lstrip()

# Deliberately not dedented: it is appended to the class body above, and a
# `test_two` that landed at column 0 would be a module-level function the
# loader never sees -- a grown tree that did not grow.
SECOND_CASE = "\n    def test_two(self):\n        self.assertTrue(True)\n"

# A test that borrows a process seam, so scanning it yields a mutation owner
# no prior manifest classified: the arrival this file's guard is about.
BORROWER_CASE = textwrap.dedent(
    """
    import os
    import unittest


    class Borrower(unittest.TestCase):
        def test_borrows_the_environment(self):
            os.environ["ORCHFLOWS_FIXTURE"] = "1"
            self.assertEqual(os.environ.get("ORCHFLOWS_FIXTURE"), "1")
    """
).lstrip()
BORROWER = "tests.test_borrower::Borrower.test_borrows_the_environment"

# Every scan emits the synthetic suite baseline, so a fixture manifest that
# omits its ruling has an unruled owner before the tree contributes one.
# Only the `restoration` carries: `seams` come from the scan, never the prior.
RULED_BASELINE = {
    "module": "<suite>",
    "owner": "discovery-baseline",
    "restoration": "selected-module-boundary",
    "seams": ["environment"],
}


class _Case:
    """The one thing the generator asks of a discovered case."""

    def __init__(self, identity):
        self._identity = identity

    def id(self):
        return self._identity


def fixture_manifest(identities, owners) -> dict:
    return {
        "schema": "orchflows.serial-compat.v1",
        "discovery": {"identities": list(identities)},
        "mutation_owners": list(owners),
        "sentinels": [
            {
                "categories": ["discovery", "process"],
                "id": "test_fixture.Fixture.test_one",
                "module": "test_fixture",
            },
            {
                "allowed_seams": ["cwd", "environment"],
                "categories": ["cwd"],
                "id": "test_fixture.Fixture.test_two",
                "module": "test_fixture",
            },
        ],
    }


def write_fixture_manifest(path: Path, identities, owners=(RULED_BASELINE,)) -> str:
    text = serial_manifest.render(fixture_manifest(identities, owners))
    path.write_bytes(text.encode("utf-8"))
    return text


class TestRegeneration(unittest.TestCase):
    def test_regeneration_replaces_stale_discovery_with_the_live_multiset(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp, "manifest.json")
            write_fixture_manifest(manifest, ["test_fixture.Fixture.test_one"])
            live = ["test_fixture.Fixture.test_one", "test_fixture.Fixture.test_two"]
            report = serial_manifest.regenerate(
                manifest,
                Path(tmp),
                lambda tests_dir: [_Case(identity) for identity in reversed(live)],
                lambda tests_dir: [],
            )
            written = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(written["discovery"], {"identities": live})
        self.assertEqual(report["before"], {"identities": live[:1]})
        self.assertEqual(report["after"], {"identities": live})

    def test_the_sentinels_block_survives_regeneration_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp, "manifest.json")
            before = write_fixture_manifest(manifest, ["test_fixture.Fixture.test_one"])
            serial_manifest.regenerate(
                manifest,
                Path(tmp),
                lambda tests_dir: [_Case("test_fixture.Fixture.test_one"),
                                   _Case("test_fixture.Fixture.test_two")],
                lambda tests_dir: [{"module": "m", "owner": "o", "seams": ["cwd"]}],
            )
            after = manifest.read_text(encoding="utf-8")
        self.assertIn('"sentinels": [', before)
        self.assertNotEqual(before, after)
        self.assertEqual(
            serial_manifest.sentinels_block(after),
            serial_manifest.sentinels_block(before),
        )

    def test_regeneration_drops_a_sentinel_whose_id_no_longer_discovers(self):
        """A test that no longer exists is not a judgment a reviewer has to make."""
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp, "manifest.json")
            write_fixture_manifest(manifest, ["test_fixture.Fixture.test_one"])
            serial_manifest.regenerate(
                manifest,
                Path(tmp),
                lambda tests_dir: [_Case("test_fixture.Fixture.test_one")],
                lambda tests_dir: [],
            )
            written = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(
            [entry["id"] for entry in written["sentinels"]],
            ["test_fixture.Fixture.test_one"],
        )

    def test_a_roster_regeneration_would_respell_aborts_the_write(self):
        """Dropping a vanished id is the one edit; carrying a row is byte-exact.

        Every row regeneration keeps is rendered from the committed bytes it was
        parsed from, so a roster those bytes spell any other way is a rewrite the
        write refuses rather than a reformatting it performs.
        """
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp, "manifest.json")
            text = write_fixture_manifest(manifest, ["test_fixture.Fixture.test_one"])
            block = serial_manifest.sentinels_block(text)
            respelled = block.replace('"module": "test_fixture"', '"module":  "test_fixture"')
            self.assertNotEqual(block, respelled)
            manifest.write_bytes(text.replace(block, respelled).encode("utf-8"))
            with self.assertRaisesRegex(ValueError, "rewrite the sentinel roster"):
                serial_manifest.regenerate(
                    manifest,
                    Path(tmp),
                    lambda tests_dir: [_Case("test_fixture.Fixture.test_one"),
                                       _Case("test_fixture.Fixture.test_two")],
                    lambda tests_dir: [],
                )

    def test_a_prior_owner_keeps_its_restoration_and_a_new_owner_is_marked(self):
        previous = [
            {
                "module": "tests.baseline_pin",
                "owner": "_grade",
                "restoration": "sharded-module-guard",
                "seams": ["cwd"],
            },
            {
                "module": "tests.gone",
                "owner": "retired",
                "restoration": "selected-module-boundary",
                "seams": ["cwd"],
            },
        ]
        scanned = [
            {"module": "tests.baseline_pin", "owner": "_grade", "seams": ["cwd", "monkeypatch"]},
            {"module": "tests.fresh", "owner": "arrived", "seams": ["environment"]},
        ]
        merged = serial_manifest.merge_owners(previous, scanned)
        self.assertEqual([(row["module"], row["owner"]) for row in merged],
                         [("tests.baseline_pin", "_grade"), ("tests.fresh", "arrived")])
        self.assertEqual(merged[0]["restoration"], "sharded-module-guard")
        self.assertEqual(merged[0]["seams"], ["cwd", "monkeypatch"])
        self.assertEqual(merged[1]["restoration"], serial_manifest.UNCLASSIFIED)
        self.assertEqual(
            serial_manifest.unruled(merged), ["tests.fresh::arrived [environment]"]
        )

    def test_the_marker_is_a_restoration_the_loader_can_never_accept(self):
        """The written marker and the loader's verdict cannot drift apart."""
        self.assertNotIn(serial_manifest.UNCLASSIFIED, RESTORATIONS)

    def test_the_rendered_manifest_keeps_key_order_indent_and_lf_newlines(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp, "manifest.json")
            write_fixture_manifest(manifest, ["test_fixture.Fixture.test_one"])
            serial_manifest.regenerate(
                manifest,
                Path(tmp),
                lambda tests_dir: [_Case("test_fixture.Fixture.test_one")],
                lambda tests_dir: [{"module": "m", "owner": "o", "seams": ["cwd"]}],
            )
            raw = manifest.read_bytes()
        text = raw.decode("utf-8")
        self.assertNotIn(b"\r\n", raw)
        self.assertTrue(text.endswith("}\n"))
        self.assertEqual(
            [line for line in text.splitlines() if line.startswith(' "')],
            [' "discovery": {', ' "mutation_owners": [', ' "schema": "orchflows.serial-compat.v1",',
             ' "sentinels": ['],
        )
        self.assertEqual(text, json.dumps(json.loads(text), sort_keys=True, indent=1) + "\n")


class TestWriteManifestFlag(unittest.TestCase):
    """The flag the runner grew, driven the way a unit drives it."""

    def _run(self, *argv):
        return subprocess.run(
            [sys.executable, str(RUNNER), *argv],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
        )

    def _require_discovery(self, tests_dir: Path, manifest: Path):
        return subprocess.run(
            [
                sys.executable, "-c",
                "import json, sys\n"
                "from tools.run_serial_compat import discover_cases, _require_discovery\n"
                "manifest = json.loads(open(sys.argv[2], encoding='utf-8').read())\n"
                "_require_discovery(discover_cases(sys.argv[1]), manifest)\n"
                "print('discovery agrees')\n",
                str(tests_dir), str(manifest),
            ],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
        )

    def test_the_flag_reconciles_a_tree_that_grew_one_test_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = Path(tmp, "tests")
            tests_dir.mkdir()
            module = tests_dir / "test_fixture.py"
            module.write_text(ONE_CASE, encoding="utf-8")
            manifest = Path(tmp, "manifest.json")
            one = ["test_fixture.Fixture.test_one"]
            before_text = write_fixture_manifest(manifest, one)
            self.assertEqual(self._require_discovery(tests_dir, manifest).returncode, 0)

            module.write_text(ONE_CASE + SECOND_CASE, encoding="utf-8")
            stale = self._require_discovery(tests_dir, manifest)
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("discovery identity drift", stale.stderr)

            written = self._run(
                "--write-manifest", "--manifest", str(manifest), "--tests-dir", str(tests_dir)
            )
            self.assertEqual(written.returncode, 0, written.stderr)
            after_text = manifest.read_text(encoding="utf-8")

        both = one + ["test_fixture.Fixture.test_two"]
        self.assertIn("discovery before: 1 identities", written.stdout)
        self.assertIn("discovery after: 2 identities", written.stdout)
        self.assertEqual(json.loads(after_text)["discovery"]["identities"], both)
        self.assertEqual(
            serial_manifest.sentinels_block(after_text),
            serial_manifest.sentinels_block(before_text),
        )

    def test_the_flag_reconciles_a_tree_that_grew_one_test_for_the_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = Path(tmp, "tests")
            tests_dir.mkdir()
            (tests_dir / "test_fixture.py").write_text(ONE_CASE + SECOND_CASE, encoding="utf-8")
            manifest = Path(tmp, "manifest.json")
            write_fixture_manifest(manifest, ["test_fixture.Fixture.test_one"])
            self._run(
                "--write-manifest", "--manifest", str(manifest), "--tests-dir", str(tests_dir)
            )
            agreed = self._require_discovery(tests_dir, manifest)
        self.assertEqual(agreed.returncode, 0, agreed.stderr)
        self.assertIn("discovery agrees", agreed.stdout)


class TestUnruledOwners(unittest.TestCase):
    """A ruling the scan cannot recover stops the flag rather than shipping."""

    def _write(self, tmp, owners):
        tests_dir = Path(tmp, "tests")
        tests_dir.mkdir()
        (tests_dir / "test_borrower.py").write_text(BORROWER_CASE, encoding="utf-8")
        manifest = Path(tmp, "manifest.json")
        write_fixture_manifest(manifest, ["stale.identity"], owners)
        written = subprocess.run(
            [sys.executable, str(RUNNER), "--write-manifest", "--manifest", str(manifest),
             "--tests-dir", str(tests_dir)],
            cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
        )
        return written, json.loads(manifest.read_text(encoding="utf-8"))

    def test_an_owner_needing_a_ruling_fails_the_flag_and_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            written, after = self._write(tmp, [RULED_BASELINE])
        self.assertNotEqual(written.returncode, 0, written.stdout)
        self.assertIn(BORROWER, written.stdout + written.stderr)
        self.assertIn("serial-compat-policy.md", written.stdout + written.stderr)
        rows = {(row["module"], row["owner"]): row for row in after["mutation_owners"]}
        # The regeneration is still on disk: the reviewer rules the marked row
        # in place instead of hand-writing derived facts nobody recomputed.
        self.assertEqual(
            rows[("tests.test_borrower", "Borrower.test_borrows_the_environment")],
            {"module": "tests.test_borrower",
             "owner": "Borrower.test_borrows_the_environment",
             "restoration": serial_manifest.UNCLASSIFIED, "seams": ["environment"]},
        )
        self.assertEqual(
            after["discovery"]["identities"], ["test_borrower.Borrower.test_borrows_the_environment"]
        )

    def test_the_flag_exits_zero_once_every_scanned_owner_carries_a_ruling(self):
        ruled = [RULED_BASELINE, {
            "module": "tests.test_borrower",
            "owner": "Borrower.test_borrows_the_environment",
            "restoration": "sharded-module-guard",
            "seams": ["environment"],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            written, after = self._write(tmp, ruled)
        self.assertEqual(written.returncode, 0, written.stdout + written.stderr)
        self.assertNotIn("ruling", written.stdout)
        self.assertEqual(
            sorted({row["restoration"] for row in after["mutation_owners"]}),
            ["selected-module-boundary", "sharded-module-guard"],
        )


class TestCommittedManifest(unittest.TestCase):
    def test_the_committed_bytes_are_exactly_what_regeneration_would_write(self):
        raw = MANIFEST.read_bytes()
        text = raw.decode("utf-8")
        self.assertNotIn(b"\r\n", raw)
        self.assertEqual(serial_manifest.render(json.loads(text)), text)

    def test_every_committed_owner_still_carries_its_restoration(self):
        owners = json.loads(MANIFEST.read_text(encoding="utf-8"))["mutation_owners"]
        self.assertTrue(owners)
        self.assertEqual(
            [row for row in owners if "restoration" not in row],
            [],
            "regeneration must not drop a classification the scan cannot recover",
        )
        self.assertEqual([row for row in owners if row["restoration"] not in RESTORATIONS], [])

    def test_the_loader_accepts_the_committed_file_and_names_what_it_refuses(self):
        """The refusal a marked row earns has to say which row earned it."""
        committed = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(load_manifest(MANIFEST)["schema"], "orchflows.serial-compat.v1")
        marked = dict(committed["mutation_owners"][-1], restoration=serial_manifest.UNCLASSIFIED)
        committed["mutation_owners"] = committed["mutation_owners"][:-1] + [marked]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "manifest.json")
            path.write_bytes(serial_manifest.render(committed).encode("utf-8"))
            with self.assertRaises(ValueError) as refusal:
                load_manifest(path)
        self.assertIn("%s::%s" % (marked["module"], marked["owner"]), str(refusal.exception))

    def test_the_policy_names_every_ruling_the_loader_accepts(self):
        """Reviewers rule from the policy, so it owns the ruling vocabulary."""
        policy = POLICY.read_text(encoding="utf-8")
        for ruling in sorted(RESTORATIONS):
            self.assertIn(ruling, policy)


if __name__ == "__main__":
    unittest.main()
