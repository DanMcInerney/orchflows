"""Adversarial regressions for serial-compatibility evidence and boundaries."""

from __future__ import annotations

import hashlib
import io
import json
import math
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

from tools import run_serial_compat
from tools import serial_gate
from tools import serial_pair
from tools import serial_trials


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tests" / "serial_compat_manifest.json"


def observation(mode, *, ok=True, identity="identity", manifest="manifest"):
    tests = 14 if mode == "selected" else 42
    record = {
        "schema": "orchflows.serial-compat-observation.v1",
        "mode": mode,
        "revision": "candidate",
        "worktree_clean": True,
        "recorded_at_utc": "2026-08-21T01:00:00Z",
        "interpreter": {"pid": 1, "version": "3.13", "executable": "python"},
        "manifest": {"sha256": hashlib.sha256(manifest.encode()).hexdigest()},
        "discovery": {"count": 42, "sha256": hashlib.sha256(identity.encode()).hexdigest()},
        "outcomes": {"tests": tests, "failures": 0, "errors": 0, "skipped": 0,
                     "expected_failures": 0, "unexpected_successes": 0},
        "wall_time_seconds": 1.0,
        "ok": ok,
    }
    if mode == "selected":
        record.update(sentinels={"count": 14}, boundaries=[])
    return record


def pair(pair_id, hour=1, *, identity="identity", manifest="manifest", exhaustive_ok=True):
    return serial_pair.make_pair(
        observation("selected", identity=identity, manifest=manifest),
        observation("exhaustive", ok=exhaustive_ok, identity=identity, manifest=manifest),
        pair_id,
        "2026-08-21T%02d:00:00Z" % hour,
    )


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

    def test_only_observed_intentional_residue_is_allowlisted(self):
        entries = run_serial_compat.load_manifest(MANIFEST)["sentinels"]
        allowed = {
            entry["module"]: entry.get("allowed_seams", [])
            for entry in entries if entry.get("allowed_seams")
        }
        self.assertEqual({
            "tests.test_tickets_cases.run_state_artifacts": ["environment"],
            "tests.test_tickets_cases.identity_core": ["environment"],
            "tests.test_ui_cases.http_server": ["module-cache"],
        }, allowed)


class TestEvidenceGateHardening(unittest.TestCase):
    def test_nonfinite_or_wrong_sentinel_timing_records_fail_closed(self):
        bad = observation("selected")
        bad["wall_time_seconds"] = math.nan
        bad["sentinels"]["count"] = 0
        bad["worktree_clean"] = False
        gate = serial_trials.evaluate([bad, dict(bad)])
        self.assertFalse(gate["target_met"])
        self.assertFalse(gate["fallback_met"])
        self.assertIn("trial-1-duration", gate["reasons"])
        self.assertIn("trial-1-sentinel-count", gate["reasons"])
        self.assertIn("trial-1-worktree-dirty", gate["reasons"])

    def test_duplicate_or_forged_pairs_cannot_open_promotion(self):
        clean = pair("same")
        duplicate = serial_pair.evaluate_pairs([clean] * 20)
        self.assertFalse(duplicate["promotion_ready"])
        self.assertTrue(duplicate["defects"])
        forged = dict(clean, pair_id="forged", clean=True, reasons=[])
        forged["exhaustive"] = observation("exhaustive", ok=False)
        evaluated = serial_pair.evaluate_pairs([forged] * 20)
        self.assertFalse(evaluated["promotion_ready"])

    def test_discovery_or_manifest_change_restarts_the_streak(self):
        initial = [pair("p-%02d" % index, index, manifest="one") for index in range(1, 20)]
        changed = pair("p-20", 20, manifest="two")
        gate = serial_pair.evaluate_pairs(initial + [changed])
        self.assertEqual(1, gate["clean_streak"])
        self.assertFalse(gate["promotion_ready"])
        self.assertEqual("contract-identity-change", gate["resets"][-1]["reason"])

    def test_accumulator_carries_prior_pairs_and_fails_closed_on_history_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = root / "history" / "gate.json"
            previous.parent.mkdir()
            prior_gate = serial_pair.evaluate_pairs([
                pair("p-%02d" % index, index) for index in range(1, 19)
            ])
            previous.write_text(json.dumps(prior_gate), encoding="utf-8")
            current = root / "current"
            for index in (19, 20):
                directory = current / ("host-%d" % index)
                directory.mkdir(parents=True)
                directory.joinpath("pair.json").write_text(
                    json.dumps(pair("p-%02d" % index, index)), encoding="utf-8"
                )
            gate = serial_gate.accumulate(previous, current)
            self.assertEqual(20, gate["clean_streak"])
            self.assertTrue(gate["promotion_ready"])
            previous.write_text("not-json", encoding="utf-8")
            failed = serial_gate.accumulate(previous, current)
            self.assertFalse(failed["promotion_ready"])
            self.assertTrue(failed["source_errors"])

    def test_a_partial_host_run_records_a_durable_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "current" / "one-host"
            current.mkdir(parents=True)
            current.joinpath("pair.json").write_text(
                json.dumps(pair("only-host")), encoding="utf-8"
            )
            gate = serial_gate.accumulate(root / "missing.json", root / "current")
        self.assertFalse(gate["promotion_ready"])
        self.assertTrue(gate["source_errors"])
        self.assertTrue(any(not item["clean"] for item in gate["pairs"]))


if __name__ == "__main__":
    unittest.main()
