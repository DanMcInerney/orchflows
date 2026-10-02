"""The harness selfcheck: every check passes here within its time budget, and a failure is reported, not hidden."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from benchkit import identity, selfcheck  # noqa: E402
from benchkit.launch import Outcome  # noqa: E402

NAMES = ["overlap", "timeout-reaps-process-tree", "transient-retry", "verifier-crash-unscored", "interrupt-and-resume",
         "changed-bytes-detected", "staging-leak-refused"]


class SelfcheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(identity.discard, self.tmp)

    def test_every_check_passes_within_ten_seconds(self):
        began = time.monotonic()
        report = selfcheck.run(self.tmp)
        self.assertLess(time.monotonic() - began, 10)
        self.assertEqual([check["name"] for check in report["checks"]], NAMES)
        for check in report["checks"]:
            self.assertTrue(check["passed"], check)
            self.assertTrue(check["detail"])
        self.assertEqual(set(report), {"platform", "python", "checks"})
        self.assertTrue(report["platform"] and report["python"])
        json.dumps(report)

    def test_a_check_that_fails_is_reported_with_its_reason(self):
        def broken(folder):
            raise selfcheck.Failed("the harness is broken")

        def crashing(folder):
            raise RuntimeError("unexpected")

        with mock.patch.object(selfcheck, "CHECKS", (("fine", lambda folder: "ok"), ("broken", broken), ("crashing", crashing))):
            report = selfcheck.run(self.tmp)
        self.assertEqual([(c["name"], c["passed"]) for c in report["checks"]], [("fine", True), ("broken", False), ("crashing", False)])
        self.assertEqual(report["checks"][1]["detail"], "the harness is broken")
        self.assertEqual(report["checks"][2]["detail"], "RuntimeError: unexpected")

    def failing(self, name, **patches):
        """The detail of the named check, which must fail while the given kit functions are replaced."""
        only = tuple(item for item in selfcheck.CHECKS if item[0] == name)
        with mock.patch.multiple(selfcheck, CHECKS=only, **patches):
            report = selfcheck.run(self.tmp / name)
        check = next(c for c in report["checks"] if c["name"] == name)
        self.assertFalse(check["passed"], check)
        return check["detail"]

    def test_the_checks_detect_the_failures_they_exist_for(self):
        real = selfcheck.run_units

        def serial(units, attempt, **options):
            return real(units, attempt, **{**options, "jobs": 1})

        def unreaped(command, *, cwd, stdout, stderr, timeout, **_):
            with open(stdout, "wb") as out, open(stderr, "wb") as err:
                proc = subprocess.Popen(command, cwd=cwd, stdout=out, stderr=err)
                try:
                    proc.wait(timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                    return Outcome("timeout", None, timeout, 0.0, 0.0, False, "capped")
            return Outcome("completed", 0, 0.0, 0.0, 0.0, False, "")

        self.assertIn("overlapped only", self.failing("overlap", run_units=serial))
        self.assertIn("outlived the cap", self.failing("timeout-reaps-process-tree", run_capped=unreaped))
        self.assertIn("one changed byte was reported as []", self.failing("changed-bytes-detected", identity=mock.Mock(
            retain=mock.Mock(), compare=mock.Mock(return_value=[]), discard=identity.discard)))
        self.assertIn("was staged", self.failing("staging-leak-refused", stage=mock.Mock(
            stage_public=mock.Mock(return_value=None), StagingError=selfcheck.stage.StagingError)))

    def test_it_works_without_a_given_folder_and_leaves_nothing_behind(self):
        before = set(Path(tempfile.gettempdir()).glob("benchkit-selfcheck-*"))
        with mock.patch.object(selfcheck, "CHECKS", (("fine", lambda folder: "ok"),)):
            report = selfcheck.run()
        self.assertTrue(report["checks"][0]["passed"])
        self.assertEqual(set(Path(tempfile.gettempdir()).glob("benchkit-selfcheck-*")), before)


if __name__ == "__main__":
    unittest.main()
