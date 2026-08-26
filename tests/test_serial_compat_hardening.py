"""Adversarial regressions for serial-compatibility boundaries."""

from __future__ import annotations

import io
import json
import tempfile
import time
import unittest
from pathlib import Path

from tools import run_serial_compat


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tests" / "serial_compat_manifest.json"


class TestStateBoundaryDiscrimination(unittest.TestCase):
    LEAKS = {
        "environment": "import os; os.environ['SERIAL_COMPAT_LEAK'] = '1'",
        "cwd": "import os; from pathlib import Path; os.chdir(str(Path(__file__).parent))",
        "import-path": "import sys; sys.path.append('serial-compat-leak')",
        "warnings": "import warnings; warnings.formatwarning = lambda *args: 'leak'",
        "logging": (
            "import logging; "
            "logging.getLogger('serial-compat-leak').setLevel(logging.CRITICAL); "
            "logging.getLogger().addFilter(logging.Filter('serial-compat-leak'))"
        ),
        "event-loop": "import asyncio; asyncio.set_event_loop(asyncio.new_event_loop())",
        "module-cache": (
            "import sys, types; "
            "sys.modules['serial_compat_leak'] = types.ModuleType('serial_compat_leak')"
        ),
        "monkeypatch": "from pathlib import Path; Path.exists = lambda self: True",
        "threads": (
            "import threading, time; "
            "threading.Thread(target=lambda: time.sleep(.25), daemon=True).start()"
        ),
    }

    def test_each_process_seam_is_detected_and_restorable_seams_are_restored(self):
        for seam, statement in self.LEAKS.items():
            with self.subTest(seam=seam), tempfile.TemporaryDirectory() as tmp:
                tests_dir = Path(tmp)
                tests_dir.joinpath("test_fixture.py").write_text(
                    "import unittest\nclass Fixture(unittest.TestCase):\n"
                    " def test_leak(self):\n  " + statement + "\n",
                    encoding="utf-8",
                )
                manifest = {"sentinels": [{
                    "id": "test_fixture.Fixture.test_leak", "module": "test_fixture",
                }], "mutation_owners": []}
                record = run_serial_compat.run_selected(
                    tests_dir, manifest, stream=io.StringIO()
                )
            self.assertFalse(record["ok"], "%s: %s" % (seam, record))
            self.assertIn(seam, record["boundaries"][0]["unexpected"])
            if seam in run_serial_compat.RESTORABLE_SEAMS:
                self.assertIn(seam, record["boundaries"][0]["restored"])
                self.assertNotIn(seam, record["boundaries"][0]["remaining"])
        time.sleep(.3)


class TestManifestHardening(unittest.TestCase):
    def test_an_aliased_environment_write_is_owned(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = Path(tmp)
            tests_dir.joinpath("test_alias.py").write_text(
                "import os as operating\n"
                "from pathlib import Path as FilePath\n"
                "def test_it():\n operating.environ['X'] = '1'\n"
                " FilePath.exists = lambda self: True\n",
                encoding="utf-8",
            )
            owners = run_serial_compat.scan_mutation_owners(tests_dir)
        owner = next(item for item in owners if item["owner"] == "test_it")
        self.assertIn("environment", owner["seams"])
        self.assertIn("monkeypatch", owner["seams"])

    def test_required_fidelity_category_cannot_be_silently_removed(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        data["sentinels"] = [
            entry for entry in data["sentinels"]
            if "real-hashed-runtime" not in entry["categories"]
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "categories are incomplete"):
                run_serial_compat.load_manifest(path)
            data = json.loads(MANIFEST.read_text(encoding="utf-8"))
            data["sentinels"] = [
                entry for entry in data["sentinels"]
                if entry["id"] != (
                    "tests.test_state_root_cases.environment.TestNoTestReachesTheRealSink."
                    "test_the_redirect_is_in_force_in_this_process"
                )
            ]
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly 14 sentinels"):
                run_serial_compat.load_manifest(path)

    def test_only_observed_intentional_residue_is_allowlisted(self):
        entries = run_serial_compat.load_manifest(MANIFEST)["sentinels"]
        allowed = {
            entry["module"]: entry.get("allowed_seams", [])
            for entry in entries if entry.get("allowed_seams")
        }
        self.assertEqual({
            "tests.test_tickets_issue_cases.new_cases": ["environment"],
            "tests.test_workspace_cases.start_cases": ["environment"],
            "tests.test_ui_cases.http_server": ["module-cache"],
        }, allowed)


if __name__ == "__main__":
    unittest.main()
