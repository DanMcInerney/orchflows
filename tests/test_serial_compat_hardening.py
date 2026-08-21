"""Adversarial regressions for serial-compatibility evidence and boundaries."""

from __future__ import annotations

import datetime
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


def observation(
        mode, *, ok=True, identity="identity", manifest="manifest",
        recorded_at="2026-08-21T01:00:00Z", pid=1):
    tests = 14 if mode == "selected" else 42
    record = {
        "schema": "orchflows.serial-compat-observation.v1",
        "mode": mode,
        "revision": "candidate",
        "worktree_clean": True,
        "recorded_at_utc": recorded_at,
        "interpreter": {"pid": pid, "version": "3.13", "executable": "python"},
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


def pair(
        pair_id, hour=1, *, identity="identity", manifest="manifest",
        exhaustive_ok=True, recorded_at=None):
    recorded_at = recorded_at or "2026-08-21T%02d:00:00Z" % hour
    evidence_pid = int(hashlib.sha256(pair_id.encode()).hexdigest()[:7], 16) + 1
    return serial_pair.make_pair(
        observation(
            "selected", identity=identity, manifest=manifest,
            recorded_at=recorded_at, pid=evidence_pid,
        ),
        observation(
            "exhaustive", ok=exhaustive_ok, identity=identity, manifest=manifest,
            recorded_at=recorded_at, pid=evidence_pid + 1,
        ),
        pair_id,
        recorded_at,
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
    def _write_current_pairs(self, root, pairs):
        current = root / "current"
        for index, current_pair in enumerate(pairs, 1):
            directory = current / ("host-%d" % index)
            directory.mkdir(parents=True)
            directory.joinpath("pair.json").write_text(
                json.dumps(current_pair), encoding="utf-8"
            )
        return current

    def _pairs_after(self, gate, prefix, count=2, **kwargs):
        latest = max(
            datetime.datetime.strptime(item["recorded_at_utc"], "%Y-%m-%dT%H:%M:%SZ")
            for item in gate["pairs"]
        )
        return [
            pair(
                "%s-%d" % (prefix, index),
                recorded_at=(latest + datetime.timedelta(seconds=index)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                **kwargs,
            )
            for index in range(1, count + 1)
        ]

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
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = root / "gate.json"
            previous.write_text(json.dumps(duplicate), encoding="utf-8")
            current = self._write_current_pairs(
                root, [
                    pair("new-1", recorded_at="2026-08-22T01:00:00Z"),
                    pair("new-2", recorded_at="2026-08-22T02:00:00Z"),
                ]
            )
            accumulated = serial_gate.accumulate(previous, current)
        self.assertEqual(0, accumulated["clean_streak"])
        self.assertFalse(accumulated["promotion_ready"])
        self.assertTrue(accumulated["source_errors"])

        original = pair("clone", 1)
        renamed_clones = []
        for index in range(1, 21):
            clone = json.loads(json.dumps(original))
            clone["pair_id"] = "clone-%02d" % index
            clone["recorded_at_utc"] = "2026-08-21T%02d:00:00Z" % index
            renamed_clones.append(clone)
        cloned_gate = serial_pair.evaluate_pairs(renamed_clones)
        self.assertTrue(cloned_gate["promotion_ready"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = root / "gate.json"
            previous.write_text(json.dumps(cloned_gate), encoding="utf-8")
            current = self._write_current_pairs(
                root, [
                    pair("fresh-1", recorded_at="2026-08-22T01:00:00Z"),
                    pair("fresh-2", recorded_at="2026-08-22T02:00:00Z"),
                ]
            )
            accumulated = serial_gate.accumulate(previous, current)
        self.assertFalse(accumulated["promotion_ready"])
        self.assertTrue(accumulated["rollback_required"])
        self.assertTrue(accumulated["source_errors"])

    def test_discovery_or_manifest_change_restarts_the_streak(self):
        for field, changed_kwargs in (
                ("manifest", {"manifest": "two"}),
                ("discovery", {"identity": "two"})):
            with self.subTest(field=field):
                initial = [
                    pair("%s-%02d" % (field, index), index)
                    for index in range(1, 20)
                ]
                changed = pair("%s-20" % field, 20, **changed_kwargs)
                gate = serial_pair.evaluate_pairs(initial + [changed])
                self.assertEqual(1, gate["clean_streak"])
                self.assertFalse(gate["promotion_ready"])
                self.assertEqual(
                    "contract-identity-change", gate["resets"][-1]["reason"]
                )

        promoted = serial_pair.evaluate_pairs([
            pair("promoted-%02d" % index, index) for index in range(1, 21)
        ])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = root / "gate.json"
            previous.write_text(json.dumps(promoted), encoding="utf-8")
            current = self._write_current_pairs(root, [
                pair("backdated-red", 0, exhaustive_ok=False),
                pair("after-red", 21),
            ])
            gate = serial_gate.accumulate(previous, current)
        self.assertTrue(gate["source_errors"])
        self.assertFalse(gate["promotion_ready"])
        self.assertTrue(gate["rollback_required"])
        self.assertEqual("unclean-pair", gate["resets"][-1]["reason"])

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

        valid_history = serial_pair.evaluate_pairs([
            pair("old-%02d" % index, index) for index in range(1, 19)
        ])
        promoted_history = serial_pair.evaluate_pairs([
            pair("promoted-%02d" % index, index) for index in range(1, 21)
        ])
        duplicate_history = serial_pair.evaluate_pairs([pair("duplicate")] * 2)
        nested_timestamp = json.loads(json.dumps(valid_history))
        nested_timestamp["pairs"][0]["recorded_at_utc"] = 1
        nested_observation = json.loads(json.dumps(valid_history))
        nested_observation["pairs"][0]["selected"] = []
        numeric_state = dict(valid_history, required_clean_pairs=20.0)
        forged_promotion = dict(valid_history, clean_streak=20, promotion_ready=True)
        contradictory_promoted = dict(promoted_history, rollback_required=True)
        corrupt_promoted = dict(valid_history, promotion_ready=True, pairs="corrupt")
        invalid_cases = {
            "wrong-top-level": json.dumps([]),
            "malformed-schema": json.dumps(dict(valid_history, schema="unknown")),
            "truncated": '{"schema":',
            "duplicate": json.dumps(duplicate_history),
            "nested-timestamp": json.dumps(nested_timestamp),
            "nested-observation": json.dumps(nested_observation),
            "numeric-state": json.dumps(numeric_state),
            "forged-promotion": json.dumps(forged_promotion),
            "contradictory-promoted": json.dumps(contradictory_promoted),
            "corrupt-promoted": json.dumps(corrupt_promoted),
        }
        for name, history_text in invalid_cases.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    previous = root / "gate.json"
                    previous.write_text(history_text, encoding="utf-8")
                    current = self._write_current_pairs(root, [
                        pair("%s-new-1" % name, recorded_at="2026-08-22T01:00:00Z"),
                        pair("%s-new-2" % name, recorded_at="2026-08-22T02:00:00Z"),
                    ])
                    gate = serial_gate.accumulate(previous, current)

                    reset_id = gate["pairs"][-1]["pair_id"]
                    continued_history = root / "continued-gate.json"
                    continued_history.write_text(json.dumps(gate), encoding="utf-8")
                    continued_current = self._write_current_pairs(
                        root / "continued",
                        self._pairs_after(gate, name + "-continued"),
                    )
                    continued = serial_gate.accumulate(
                        continued_history, continued_current
                    )

                self.assertFalse(gate["promotion_ready"])
                self.assertEqual(0, gate["clean_streak"])
                self.assertEqual([], gate["defects"])
                self.assertTrue(gate["source_errors"])
                self.assertTrue(gate["rollback_required"])
                self.assertTrue(reset_id.startswith("source-error-"))
                self.assertFalse(continued["source_errors"])
                self.assertEqual(2, continued["clean_streak"])
                self.assertFalse(continued["promotion_ready"])
                self.assertTrue(continued["rollback_required"])
                self.assertIn(
                    reset_id, [item["pair_id"] for item in continued["pairs"]]
                )

        stale_history = serial_pair.evaluate_pairs([
            pair("stale-%02d" % index, index, manifest="old-contract")
            for index in range(1, 19)
        ])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = root / "gate.json"
            previous.write_text(json.dumps(stale_history), encoding="utf-8")
            current = self._write_current_pairs(root, [
                pair(
                    "new-contract-1", manifest="new-contract",
                    recorded_at="2026-08-22T01:00:00Z",
                ),
                pair(
                    "new-contract-2", manifest="new-contract",
                    recorded_at="2026-08-22T02:00:00Z",
                ),
            ])
            gate = serial_gate.accumulate(previous, current)
            continued_history = root / "continued-gate.json"
            continued_history.write_text(json.dumps(gate), encoding="utf-8")
            continued_current = self._write_current_pairs(
                root / "continued",
                self._pairs_after(gate, "new-contract-continued", manifest="new-contract"),
            )
            continued = serial_gate.accumulate(continued_history, continued_current)
        self.assertFalse(gate["source_errors"])
        self.assertEqual(2, gate["clean_streak"])
        self.assertIn(
            "contract-identity-change",
            [reset["reason"] for reset in gate["resets"]],
        )
        self.assertEqual(4, continued["clean_streak"])
        self.assertFalse(continued["rollback_required"])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = root / "gate.json"
            previous.write_text(json.dumps(corrupt_promoted), encoding="utf-8")
            current = self._write_current_pairs(root, [
                pair("reset-seed-1", recorded_at="2026-08-22T01:00:00Z"),
                pair("reset-seed-2", recorded_at="2026-08-22T02:00:00Z"),
            ])
            gate = serial_gate.accumulate(previous, current)
            for hop in range(1, 11):
                history = root / ("hop-%02d-gate.json" % hop)
                history.write_text(json.dumps(gate), encoding="utf-8")
                hop_current = self._write_current_pairs(
                    root / ("hop-%02d" % hop), self._pairs_after(gate, "hop-%02d" % hop)
                )
                gate = serial_gate.accumulate(history, hop_current)
                self.assertFalse(gate["source_errors"], hop)
                self.assertEqual(2 * hop, gate["clean_streak"], hop)
                if hop < 10:
                    self.assertFalse(gate["promotion_ready"], hop)
                    self.assertTrue(gate["rollback_required"], hop)
            self.assertTrue(gate["promotion_ready"])
            self.assertFalse(gate["rollback_required"])

    def test_a_partial_host_run_records_a_durable_reset(self):
        promoted = serial_pair.evaluate_pairs([
            pair("promoted-host-%02d" % index, index) for index in range(1, 21)
        ])
        for shape in ("missing", "one-max", "extra", "same-host", "malformed"):
            with self.subTest(shape=shape):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    previous = root / "gate.json"
                    previous.write_text(json.dumps(promoted), encoding="utf-8")
                    current = root / "current"
                    if shape == "one-max":
                        directory = current / "one-host"
                        directory.mkdir(parents=True)
                        directory.joinpath("pair.json").write_text(
                            json.dumps(pair(
                                "only-host", recorded_at="9999-12-31T23:59:59Z"
                            )),
                            encoding="utf-8",
                        )
                    elif shape == "extra":
                        current = self._write_current_pairs(root, [
                            pair("extra-1", recorded_at="2026-08-22T01:00:00Z"),
                            pair("extra-2", recorded_at="2026-08-22T02:00:00Z"),
                            pair("extra-3", recorded_at="2026-08-22T03:00:00Z"),
                        ])
                    elif shape == "same-host":
                        for index in (1, 2):
                            directory = current / "one-host" / str(index)
                            directory.mkdir(parents=True)
                            directory.joinpath("pair.json").write_text(
                                json.dumps(pair(
                                    "same-host-%d" % index,
                                    recorded_at="2026-08-22T0%d:00:00Z" % index,
                                )),
                                encoding="utf-8",
                            )
                    elif shape == "malformed":
                        malformed = pair(
                            "malformed-1", recorded_at="2026-08-22T01:00:00Z"
                        )
                        malformed["selected"] = []
                        current = self._write_current_pairs(root, [
                            malformed,
                            pair("malformed-2", recorded_at="2026-08-22T02:00:00Z"),
                        ])

                    gate = serial_gate.accumulate(previous, current)
                    reset_id = gate["pairs"][-1]["pair_id"]
                    continued_history = root / "continued-gate.json"
                    continued_history.write_text(json.dumps(gate), encoding="utf-8")
                    continued_current = self._write_current_pairs(
                        root / "continued",
                        self._pairs_after(gate, shape + "-continued"),
                    )
                    continued = serial_gate.accumulate(
                        continued_history, continued_current
                    )

                self.assertFalse(gate["promotion_ready"])
                self.assertTrue(gate["rollback_required"])
                self.assertTrue(gate["source_errors"])
                self.assertEqual([], gate["defects"])
                self.assertEqual("unclean-pair", gate["resets"][-1]["reason"])
                self.assertTrue(reset_id.startswith("source-error-"))
                self.assertFalse(continued["source_errors"])
                self.assertEqual(2, continued["clean_streak"])
                self.assertTrue(continued["rollback_required"])
                self.assertIn(
                    reset_id, [item["pair_id"] for item in continued["pairs"]]
                )

if __name__ == "__main__":
    unittest.main()
