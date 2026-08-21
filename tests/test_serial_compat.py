"""Selected serial compatibility-lane and proving-policy regressions."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools import run_serial_compat


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tests" / "serial_compat_manifest.json"
CHECKS = ROOT / ".github" / "workflows" / "checks.yml"
PAIRED = ROOT / ".github" / "workflows" / "serial-compat.yml"
GUIDANCE = ROOT / "AGENTS.md"


class TestSelectedDiscovery(unittest.TestCase):
    def test_manifest_is_the_exact_discovered_identity_multiset(self):
        manifest = run_serial_compat.load_manifest(MANIFEST)
        cases = run_serial_compat.discover_cases(ROOT / "tests")
        identities = sorted(case.id() for case in cases)
        encoded = "\n".join(identities).encode("utf-8")
        self.assertEqual(len(identities), manifest["discovery"]["count"])
        self.assertEqual(hashlib.sha256(encoded).hexdigest(), manifest["discovery"]["sha256"])
        self.assertEqual(identities, manifest["discovery"]["identities"])

    def test_every_selected_identity_exists_exactly_once(self):
        manifest = run_serial_compat.load_manifest(MANIFEST)
        identities = [case.id() for case in run_serial_compat.discover_cases(ROOT / "tests")]
        selected = [entry["id"] for entry in manifest["sentinels"]]
        self.assertEqual(len(selected), len(set(selected)))
        self.assertTrue(selected)
        for identity in selected:
            self.assertEqual(1, identities.count(identity), identity)

    def test_selected_cases_execute_once_in_the_calling_interpreter(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = Path(tmp)
            seen = tests_dir / "seen.jsonl"
            tests_dir.joinpath("test_fixture.py").write_text(
                textwrap.dedent(
                    f"""\
                    import json, os, unittest
                    SEEN = {str(seen)!r}
                    class Fixture(unittest.TestCase):
                        def test_one(self):
                            with open(SEEN, 'a', encoding='utf-8') as stream:
                                stream.write(json.dumps({{'pid': os.getpid(), 'case': 'one'}}) + '\\n')
                        def test_two(self):
                            with open(SEEN, 'a', encoding='utf-8') as stream:
                                stream.write(json.dumps({{'pid': os.getpid(), 'case': 'two'}}) + '\\n')
                    """
                ),
                encoding="utf-8",
            )
            manifest = {
                "sentinels": [
                    {"id": "test_fixture.Fixture.test_one", "module": "test_fixture"},
                    {"id": "test_fixture.Fixture.test_two", "module": "test_fixture"},
                ],
                "mutation_owners": [],
            }
            record = run_serial_compat.run_selected(
                tests_dir, manifest, stream=io.StringIO()
            )
            events = [json.loads(line) for line in seen.read_text(encoding="utf-8").splitlines()]
        self.assertTrue(record["ok"])
        self.assertEqual(["one", "two"], [event["case"] for event in events])
        self.assertEqual({os.getpid()}, {event["pid"] for event in events})
        self.assertEqual(os.getpid(), record["interpreter"]["pid"])

    def test_a_missing_selected_identity_is_refused_before_any_case_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = Path(tmp)
            marker = tests_dir / "ran"
            tests_dir.joinpath("test_fixture.py").write_text(
                "import pathlib, unittest\n"
                "class Fixture(unittest.TestCase):\n"
                f" def test_one(self): pathlib.Path({str(marker)!r}).touch()\n",
                encoding="utf-8",
            )
            manifest = {
                "sentinels": [{"id": "test_fixture.Fixture.test_missing", "module": "test_fixture"}],
                "mutation_owners": [],
            }
            with self.assertRaisesRegex(ValueError, "selected identity"):
                run_serial_compat.run_selected(tests_dir, manifest, stream=io.StringIO())
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
