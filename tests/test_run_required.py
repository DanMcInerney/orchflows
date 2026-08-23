"""The required-check runner: order, exit mapping, payload, and its cache."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from tests.test_run_required_cases.harness import (
    REPO_ROOT,
    RunRequiredCase,
    git,
    moment,
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SURFACE_ORDER = (
    ["tools/validate.py"],
    ["tools/run_tests.py"],
    ["tools/run_serial_compat.py"],
    ["install.py", "--dry-run"],
)
WHITESPACE_CHECK = ["git", "diff", "--check"]
CHEAP = ("validate.py", "install.py", "diff")
COMMAND_KEYS = {
    "argv", "started_at", "ended_at", "exit_status",
    "stdout_sha256", "stderr_sha256", "cached",
}
RECORD_KEYS = {
    "kind", "repository_identity", "tree_identity", "dirty", "commands", "exit",
}


class TestRefusal(RunRequiredCase):
    """Exit 2 is reserved for what the runner cannot honestly attempt."""

    def test_a_directory_that_is_not_a_checkout_is_refused(self):
        outside = Path(self.repo).parent / "not-a-checkout"
        outside.mkdir()
        status, _, _, err = self.invoke("--repo", str(outside))
        self.assertEqual(2, status)
        self.assertIn("git", err)
        self.assertEqual([], self.stub.calls())

    def test_a_missing_interpreter_is_refused(self):
        missing = Path(self.repo).parent / "stub" / "absent-python"
        status, _, _, err = self.invoke("--python", str(missing))
        self.assertEqual(2, status)
        self.assertIn("interpreter", err)
        self.assertEqual([], self.stub.calls())

    def test_a_refusal_names_itself_in_the_json_stream(self):
        outside = Path(self.repo).parent / "also-not-a-checkout"
        outside.mkdir()
        _, payload, _, _ = self.invoke("--repo", str(outside))
        self.assertIsNotNone(payload)
        self.assertEqual("required-check-refusal/v1", payload["kind"])
        self.assertTrue(payload["reason"])


class TestOrderAndPhases(RunRequiredCase):
    """The surface's order is what the record says; the phases are timing."""

    def test_the_record_lists_the_five_in_the_surface_order(self):
        status, payload, _, _ = self.invoke()
        self.assertEqual(0, status)
        stub = str(self.stub.path.resolve())
        expected = [[stub] + list(args) for args in SURFACE_ORDER]
        expected.append(WHITESPACE_CHECK)
        self.assertEqual(expected, [r["argv"] for r in payload["commands"]])

    def test_the_interpreter_is_asked_for_itself_exactly_once(self):
        _, payload, _, _ = self.invoke()
        self.assertEqual(1, len(self.stub.probes()))
        self.assertEqual(
            [["install.py", "--dry-run"], ["tools/run_serial_compat.py"],
             ["tools/run_tests.py"], ["tools/validate.py"]],
            sorted(self.stub.calls()),
        )

    def test_the_cheap_three_share_one_window(self):
        self.stub.plan({
            "validate.py": {"sleep": 0.5},
            "install.py": {"sleep": 0.5},
        })
        _, payload, _, _ = self.invoke()
        cheap = [self.named(payload, needle) for needle in CHEAP]
        latest_start = max(moment(record["started_at"]) for record in cheap)
        earliest_end = min(moment(record["ended_at"]) for record in cheap)
        self.assertLess(latest_start, earliest_end, cheap)

    def test_each_long_check_starts_after_everything_before_it_ended(self):
        self.stub.plan({
            "validate.py": {"sleep": 0.2},
            "run_tests.py": {"sleep": 0.2},
        })
        _, payload, _, _ = self.invoke()
        cheap = [self.named(payload, needle) for needle in CHEAP]
        tests = self.named(payload, "run_tests.py")
        serial = self.named(payload, "run_serial_compat.py")
        self.assertGreaterEqual(
            moment(tests["started_at"]),
            max(moment(record["ended_at"]) for record in cheap),
        )
        self.assertGreaterEqual(
            moment(serial["started_at"]), moment(tests["ended_at"])
        )


class TestExitMapping(RunRequiredCase):
    """0 for all five green, 1 for any red; 2 stays refusal's alone."""

    def test_all_five_green_is_zero(self):
        status, payload, _, _ = self.invoke()
        self.assertEqual(0, status)
        self.assertEqual(0, payload["exit"])
        self.assertEqual([0] * 5, [r["exit_status"] for r in payload["commands"]])

    def test_one_red_check_is_one(self):
        self.stub.plan({"run_serial_compat.py": {"exit": 7}})
        status, payload, _, _ = self.invoke()
        self.assertEqual(1, status)
        self.assertEqual(1, payload["exit"])
        self.assertEqual(7, self.named(payload, "run_serial_compat.py")["exit_status"])

    def test_a_red_cheap_check_does_not_cancel_the_long_ones(self):
        self.stub.plan({"validate.py": {"exit": 1}})
        status, payload, _, _ = self.invoke()
        self.assertEqual(1, status)
        self.assertEqual(5, len(payload["commands"]))
        self.assertEqual(0, self.named(payload, "run_tests.py")["exit_status"])


class TestRecordShape(RunRequiredCase):
    """The payload is the evidence; its keys are the contract."""

    def test_the_record_carries_exactly_the_stated_keys(self):
        _, payload, _, _ = self.invoke()
        self.assertEqual("required-check-run/v1", payload["kind"])
        self.assertEqual(RECORD_KEYS, set(payload))
        for record in payload["commands"]:
            self.assertEqual(COMMAND_KEYS, set(record))

    def test_the_record_names_the_commit_and_the_tree_it_judged(self):
        _, payload, _, _ = self.invoke()
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"),
                         payload["repository_identity"])
        self.assertEqual(git(self.repo, "rev-parse", "HEAD^{tree}"),
                         payload["tree_identity"])
        self.assertFalse(payload["dirty"])

    def test_a_working_change_is_reported_dirty(self):
        self.touch_tracked()
        _, payload, _, _ = self.invoke()
        self.assertTrue(payload["dirty"])

    def test_an_untracked_file_is_dirt_but_an_ignored_one_is_not(self):
        (self.repo / "ignored").mkdir()
        (self.repo / "ignored" / "junk.txt").write_text("x", encoding="utf-8")
        _, payload, _, _ = self.invoke()
        self.assertFalse(payload["dirty"])
        (self.repo / "loose.txt").write_text("x", encoding="utf-8")
        _, payload, _, _ = self.invoke("--no-cache")
        self.assertTrue(payload["dirty"])

    def test_each_command_digests_its_own_two_streams(self):
        _, payload, _, _ = self.invoke()
        digests = set()
        for record in payload["commands"]:
            for key in ("stdout_sha256", "stderr_sha256"):
                self.assertRegex(record[key], r"\A[0-9a-f]{64}\Z")
            digests.add(record["stdout_sha256"])
        self.assertEqual(5, len(digests))

    def test_a_freshly_run_command_is_not_marked_cached(self):
        _, payload, _, _ = self.invoke()
        self.assertEqual([False] * 5, [r["cached"] for r in payload["commands"]])


if __name__ == "__main__":
    unittest.main()
