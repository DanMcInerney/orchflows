"""Selected serial compatibility-lane and proving-policy regressions."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import tempfile
import textwrap
import threading
import unittest
import warnings
from pathlib import Path

from tools import run_serial_compat
from tools import run_tests
from tools import serial_pair
from tools import serial_trials


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "tests" / "serial_compat_manifest.json"
CHECKS = ROOT / ".github" / "workflows" / "checks.yml"
PAIRED = ROOT / ".github" / "workflows" / "serial-compat.yml"
GUIDANCE = ROOT / "AGENTS.md"
POLICY = ROOT / "tools" / "serial-compat-policy.md"


class TestSelectedDiscovery(unittest.TestCase):
    def test_discovery_preserves_preloaded_test_module_identities(self):
        tests_dir = (ROOT / "tests").resolve()
        before = {}
        for name, module in list(__import__("sys").modules.items()):
            module_file = getattr(module, "__file__", None)
            if module_file is None:
                continue
            try:
                Path(module_file).resolve().relative_to(tests_dir)
            except (OSError, ValueError):
                continue
            before[name] = module

        self.assertTrue(before)
        run_serial_compat.discover_cases(tests_dir)

        for name, module in before.items():
            self.assertIs(module, __import__("sys").modules.get(name), name)

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

    def test_discovery_manifest_drift_is_refused_before_any_case_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = Path(tmp)
            marker = tests_dir / "ran"
            tests_dir.joinpath("test_drift.py").write_text(
                "import pathlib, unittest\nclass Drift(unittest.TestCase):\n"
                f" def test_one(self): pathlib.Path({str(marker)!r}).touch()\n",
                encoding="utf-8",
            )
            manifest = {
                "discovery": {"count": 2, "sha256": "wrong"},
                "sentinels": [{"id": "test_drift.Drift.test_one", "module": "test_drift"}],
                "mutation_owners": [],
            }
            with self.assertRaisesRegex(ValueError, "discovery identity"):
                run_serial_compat.run_selected(tests_dir, manifest, stream=io.StringIO())
            self.assertFalse(marker.exists())


class TestBoundaryRestoration(unittest.TestCase):
    def test_selected_module_boundaries_restore_classified_process_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = Path(tmp)
            original_cwd = os.getcwd()
            changed_cwd = tests_dir / "changed"
            changed_cwd.mkdir()
            tests_dir.joinpath("test_first.py").write_text(
                textwrap.dedent(
                    f"""\
                    import logging, os, sys, unittest, warnings
                    def tearDownModule():
                        warnings.filters.append(('serial-compat-unique',))
                    class First(unittest.TestCase):
                        def test_mutates(self):
                            os.environ['SERIAL_COMPAT_LEAK'] = 'changed'
                            os.chdir({str(changed_cwd)!r})
                            sys.path.append({str(changed_cwd)!r})
                            logging.getLogger().setLevel(logging.CRITICAL)
                    """
                ),
                encoding="utf-8",
            )
            tests_dir.joinpath("test_second.py").write_text(
                textwrap.dedent(
                    f"""\
                    import logging, os, sys, unittest
                    class Second(unittest.TestCase):
                        def test_observes_baseline(self):
                            self.assertNotIn('SERIAL_COMPAT_LEAK', os.environ)
                            self.assertEqual({original_cwd!r}, os.getcwd())
                            self.assertNotIn({str(changed_cwd)!r}, sys.path)
                            self.assertNotEqual(logging.CRITICAL, logging.getLogger().level)
                    """
                ),
                encoding="utf-8",
            )
            manifest = {
                "sentinels": [
                    {"id": "test_first.First.test_mutates", "module": "test_first"},
                    {"id": "test_second.Second.test_observes_baseline", "module": "test_second"},
                ],
                "mutation_owners": [{
                    "module": "test_first",
                    "seams": ["environment", "cwd", "import-path", "warnings", "logging"],
                    "restoration": "selected-module-boundary",
                }],
            }
            record = run_serial_compat.run_selected(tests_dir, manifest, stream=io.StringIO())
        self.assertTrue(record["ok"], record)
        self.assertEqual(
            {"cwd", "environment", "import-path", "logging"},
            set(record["boundaries"][0]["restored"]),
        )

    def test_warning_filters_are_restored_when_a_module_leaves_them_dirty(self):
        before = run_serial_compat.capture_state()
        warnings.filters.append(("serial-compat-unique",))
        try:
            self.assertIn("warnings", run_serial_compat.changed_state(before))
            self.assertIn("warnings", run_serial_compat.restore_state(before))
            self.assertNotIn("warnings", run_serial_compat.changed_state(before))
        finally:
            run_serial_compat.restore_state(before)

    def test_an_unclassified_boundary_change_fails_the_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = Path(tmp)
            tests_dir.joinpath("test_leak.py").write_text(
                "import os, unittest\nclass Leak(unittest.TestCase):\n"
                " def test_it(self): os.environ['SERIAL_COMPAT_UNCLASSIFIED'] = '1'\n",
                encoding="utf-8",
            )
            manifest = {
                "sentinels": [{"id": "test_leak.Leak.test_it", "module": "test_leak"}],
                "mutation_owners": [],
            }
            record = run_serial_compat.run_selected(tests_dir, manifest, stream=io.StringIO())
        self.assertFalse(record["ok"])
        self.assertEqual(["environment"], record["boundaries"][0]["unexpected"])

    def test_a_live_thread_is_detected_and_cannot_be_classified_as_restorable(self):
        release = threading.Event()
        thread = threading.Thread(target=release.wait, name="serial-compat-leak", daemon=True)
        before = run_serial_compat.capture_state()
        thread.start()
        try:
            changed = run_serial_compat.changed_state(before)
            self.assertIn("threads", changed)
            self.assertNotIn("threads", run_serial_compat.RESTORABLE_SEAMS)
        finally:
            release.set()
            thread.join(timeout=5)

    def test_sharded_guard_restores_the_complete_environment(self):
        before = run_tests.guarded_state()
        original = dict(os.environ)
        os.environ["SERIAL_COMPAT_SHARDED"] = "changed"
        try:
            restored = run_tests.restore_guarded_state(before)
            self.assertIn("os.environ", restored)
            self.assertEqual(original, dict(os.environ))
        finally:
            os.environ.clear()
            os.environ.update(original)


class TestMutationOwnerManifest(unittest.TestCase):
    def test_manifest_classifies_every_detected_mutation_owner(self):
        manifest = run_serial_compat.load_manifest(MANIFEST)
        expected = run_serial_compat.scan_mutation_owners(ROOT / "tests")
        actual = [
            {"module": owner["module"], "owner": owner["owner"], "seams": owner["seams"]}
            for owner in manifest["mutation_owners"]
        ]
        self.assertEqual(expected, actual)
        for owner in manifest["mutation_owners"]:
            self.assertIn(
                owner["restoration"],
                {"sharded-module-guard", "selected-module-boundary"},
            )
        covered = {seam for owner in actual for seam in owner["seams"]}
        self.assertTrue(
            {"cwd", "environment", "event-loop", "import-path", "logging",
             "module-cache", "monkeypatch", "threads", "warnings"}.issubset(covered),
            covered,
        )


class TestExhaustiveObservation(unittest.TestCase):
    def test_exhaustive_mode_runs_every_discovered_case_in_this_interpreter(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = Path(tmp)
            tests_dir.joinpath("test_all.py").write_text(
                "import unittest\nclass All(unittest.TestCase):\n"
                " def test_one(self): pass\n def test_two(self): pass\n",
                encoding="utf-8",
            )
            cases = run_serial_compat.discover_cases(tests_dir)
            identities = sorted(case.id() for case in cases)
            manifest = {"discovery": {
                "count": len(identities),
                "sha256": hashlib.sha256("\n".join(identities).encode()).hexdigest(),
                "identities": identities,
            }}
            record = run_serial_compat.run_exhaustive(
                tests_dir, manifest, stream=io.StringIO()
            )
        self.assertTrue(record["ok"])
        self.assertEqual("exhaustive", record["mode"])
        self.assertEqual(2, record["outcomes"]["tests"])
        self.assertEqual(os.getpid(), record["interpreter"]["pid"])


class TestPairedProvingGate(unittest.TestCase):
    @staticmethod
    def observation(mode, *, ok=True, revision="abc", identity="ids"):
        return {
            "schema": "orchflows.serial-compat-observation.v1",
            "mode": mode,
            "revision": revision,
            "recorded_at_utc": "2026-08-21T01:00:00Z",
            "discovery": {"count": 2357, "sha256": identity},
            "ok": ok,
        }

    def test_a_pair_requires_matching_revision_and_discovery_identity(self):
        selected = self.observation("selected")
        exhaustive = self.observation("exhaustive", identity="different")
        pair = serial_pair.make_pair(selected, exhaustive, pair_id="pair-1")
        self.assertFalse(pair["clean"])
        self.assertIn("discovery-identity-mismatch", pair["reasons"])

    def test_selected_green_exhaustive_red_is_an_explicit_discrepancy(self):
        pair = serial_pair.make_pair(
            self.observation("selected"),
            self.observation("exhaustive", ok=False),
            pair_id="pair-1",
        )
        self.assertFalse(pair["clean"])
        self.assertTrue(pair["selected_green_exhaustive_red"])

    def test_only_twenty_consecutive_clean_pairs_open_the_promotion_gate(self):
        clean = serial_pair.make_pair(
            self.observation("selected"), self.observation("exhaustive"), pair_id="pair"
        )
        first = serial_pair.evaluate_pairs([
            dict(clean, pair_id="pair-%02d" % index, recorded_at_utc="2026-08-21T%02d:00:00Z" % index)
            for index in range(19)
        ])
        self.assertEqual(19, first["clean_streak"])
        self.assertFalse(first["promotion_ready"])
        twentieth = dict(clean, pair_id="pair-19", recorded_at_utc="2026-08-21T19:00:00Z")
        passed = serial_pair.evaluate_pairs(first["pairs"] + [twentieth])
        self.assertEqual(20, passed["clean_streak"])
        self.assertTrue(passed["promotion_ready"])
        discrepancy = dict(
            clean,
            pair_id="pair-20",
            recorded_at_utc="2026-08-21T20:00:00Z",
            clean=False,
            selected_green_exhaustive_red=True,
        )
        reset = serial_pair.evaluate_pairs(passed["pairs"] + [discrepancy])
        self.assertEqual(0, reset["clean_streak"])
        self.assertFalse(reset["promotion_ready"])


class TestPairedWorkflowAndPolicy(unittest.TestCase):
    def test_proving_workflow_is_separate_scheduled_manual_and_paired(self):
        checks = CHECKS.read_text(encoding="utf-8")
        paired = PAIRED.read_text(encoding="utf-8")
        self.assertNotIn("schedule:", checks)
        self.assertNotIn("workflow_dispatch:", checks)
        self.assertEqual(1, checks.count("run: python tools/run_tests.py"))
        self.assertIn("schedule:", paired)
        self.assertIn("workflow_dispatch:", paired)
        self.assertIn("os: [ubuntu-latest, windows-latest]", paired)
        self.assertIn("--mode selected", paired)
        self.assertIn("--mode exhaustive", paired)
        self.assertGreaterEqual(paired.count("continue-on-error: true"), 2)
        self.assertIn("python tools/serial_pair.py", paired)
        self.assertIn("if: ${{ always() }}", paired)
        self.assertIn("uses: actions/upload-artifact@v4", paired)

    def test_policy_keeps_exhaustive_required_while_selected_is_experimental(self):
        guidance = GUIDANCE.read_text(encoding="utf-8")
        policy = POLICY.read_text(encoding="utf-8")
        self.assertIn("## Experimental serial lane", guidance)
        self.assertIn("python -m unittest discover -s tests -v", guidance)
        self.assertIn("`tools/serial-compat-policy.md`", guidance)
        self.assertIn("`experimental`", policy)
        self.assertIn("`20`", policy)
        self.assertIn("`selected-green/exhaustive-red`", policy)
        self.assertIn("`90s`", policy)
        self.assertIn("`100s`", policy)
        self.assertIn("`120s`", policy)


class TestColdTrialGate(unittest.TestCase):
    @staticmethod
    def trial(seconds, revision="candidate", identity="ids"):
        return {
            "mode": "selected",
            "revision": revision,
            "discovery": {"count": 2363, "sha256": identity},
            "sentinels": {"count": 14},
            "wall_time_seconds": seconds,
            "ok": True,
        }

    def test_two_green_fixed_revision_trials_decide_the_target(self):
        gate = serial_trials.evaluate([self.trial(89.0), self.trial(90.0)])
        self.assertEqual(89.5, gate["median_seconds"])
        self.assertEqual(90.0, gate["max_seconds"])
        self.assertTrue(gate["target_met"])
        self.assertTrue(gate["fallback_met"])

    def test_revision_identity_or_time_drift_refuses_the_target(self):
        gate = serial_trials.evaluate([
            self.trial(80.0), self.trial(101.0, revision="other", identity="other")
        ])
        self.assertFalse(gate["target_met"])
        self.assertFalse(gate["fallback_met"])
        self.assertIn("revision-mismatch", gate["reasons"])
        self.assertIn("discovery-identity-mismatch", gate["reasons"])
        self.assertIn("trial-over-100s", gate["reasons"])
        fallback = serial_trials.evaluate([self.trial(100.0), self.trial(101.0)])
        self.assertFalse(fallback["target_met"])
        self.assertTrue(fallback["fallback_met"])


if __name__ == "__main__":
    unittest.main()
