"""Observed public commands preserve one review allowance across wrappers."""
from __future__ import annotations

import json
import subprocess
import sys
from unittest import mock

from scripts import tickets, tickets_done, tickets_review
from scripts.tickets_context import graded_admission
from scripts.tickets_format import _parse_frontmatter, _set_frontmatter_field
from tests.test_ticket_callables import CallableSinkTest, CODE_STANDARD
from tests._repo_root import ROOT


class ReviewPolicyTest(CallableSinkTest):
    def frame(self, *args, error=False):
        return self.callable("frame-open", "--shape", "do > judge", *args,
                             expect_error=error)

    def owner(self, *args):
        return self.frame(*args)["frame_open"]["id"]

    def judge(self, parent=None, *args, error=False):
        return self.callable("judge", "--standard", CODE_STANDARD,
                             "--artifacts", "git:" + "a" * 40,
                             *(("--parent", parent) if parent else ()), *args,
                             expect_error=error)

    def finish_fixture(self, ticket_id):
        # Lifecycle is outside these policy cases. Preserve sealed semantics;
        # set only the mutable lifecycle field before the next real command.
        path = self.run_dir() / (ticket_id + ".md")
        path.write_text(_set_frontmatter_field(self.ticket_text(ticket_id),
                                              "status", "complete"), encoding="utf-8")

    def test_default_exhaustion_nested_wrapper_and_resume_admission(self):
        owner = self.owner()
        first = self.judge(owner)["judge"]["id"]
        self.finish_fixture(first)
        wrapper = self.owner("--parent", owner)
        self.assertEqual("review-policy", self.judge(wrapper, error=True)["code"])
        data = _parse_frontmatter(self.ticket_text(first))
        self.assertEqual((owner, "1", "critique"),
                         (data["review_owner"], str(data["review_rounds"]), data["review_phase"]))
        # The shared grader is used by dispatch-open/replace on resume, too.
        siblings = {p.stem: p.read_text(encoding="utf-8") for p in self.run_dir().glob("*.md")}
        bad = _set_frontmatter_field(self.ticket_text(first), "review_round", "2")
        grade = graded_admission(first, bad, siblings, self.RUN)
        self.assertIn("review-policy", {row["code"] for row in grade["findings"]})

    def test_finite_and_until_pass_count_critiques_and_keep_criteria(self):
        for setting in ("2", "until_pass"):
            with self.subTest(setting=setting):
                owner = self.owner("--review-rounds", setting)
                first = self.judge(owner)["judge"]["id"]
                self.assertEqual("review-policy", self.judge(owner, error=True)["code"])
                self.finish_fixture(first)
                second = self.judge(owner)["judge"]["id"]
                self.finish_fixture(second)
                if setting == "2":
                    self.assertEqual("review-policy", self.judge(owner, error=True)["code"])
                else:
                    self.assertIn("judge", self.judge(owner))

    def test_parallel_repairs_then_scoped_verification_and_no_second_wave(self):
        owner = self.owner()
        critique = self.judge(owner)["judge"]["id"]
        self.finish_fixture(critique)
        repairs = [self.callable("do", "--parent", owner, "--standard", CODE_STANDARD,
                                 "--review-of", critique)["do"]["id"] for _ in range(2)]
        helper = self.owner("--parent", repairs[0])
        self.assertEqual("review-policy", self.judge(owner, "--review-of", critique, error=True)["code"])
        for repair in repairs:
            self.finish_fixture(repair)
        self.finish_fixture(helper)
        verification = self.judge(owner, "--review-of", critique)["judge"]["id"]
        self.assertEqual("verify", _parse_frontmatter(self.ticket_text(verification))["review_phase"])
        self.assertEqual("review-policy", self.callable(
            "do", "--parent", owner, "--standard", CODE_STANDARD,
            "--review-of", critique, expect_error=True)["code"])
        self.assertEqual("review-policy", self.callable(
            "do", "--parent", helper, "--standard", CODE_STANDARD, expect_error=True)["code"])
        self.assertEqual("review-policy", self.judge(owner, error=True)["code"])

    def test_repair_subtree_cannot_reset_or_review(self):
        owner = self.owner()
        critique = self.judge(owner)["judge"]["id"]
        self.finish_fixture(critique)
        repair = self.callable("do", "--parent", owner, "--standard", CODE_STANDARD,
                               "--review-of", critique)["do"]["id"]
        nested = self.owner("--parent", repair)
        self.assertEqual("review-policy", self.frame("--parent", nested,
                         "--review-new-work", "retry", error=True)["code"])
        self.assertEqual("review-policy", self.judge(nested, error=True)["code"])
        self.assertEqual("review-policy", self.judge(nested, "--review-independent",
                                                    "retry", error=True)["code"])

    def test_explicit_stages_and_independent_research(self):
        owner = self.owner()
        self.judge(owner, "--review-independent", "standalone research coverage")
        self.judge(owner)
        for stage in ("game core acceptance", "game final acceptance"):
            child = self.owner("--parent", owner, "--review-new-work", stage)
            self.judge(child)
        self.judge()
        self.judge()
        self.assertEqual("review-policy", self.frame("--parent", owner,
                         "--review-rounds", "5", error=True)["code"])

    def test_invalid_rounds_cross_owner_reference_and_changed_criteria(self):
        for setting in ("0", "-1", "1.5", "forever", "01"):
            self.assertEqual("review-policy", self.frame("--review-rounds", setting,
                                                         error=True)["code"])
        owner = self.owner("--review-rounds", "2")
        critique = self.judge(owner)["judge"]["id"]
        self.finish_fixture(critique)
        other = self.owner()
        self.assertEqual("review-policy", self.judge(other, "--review-of", critique, error=True)["code"])
        failure = self.callable("judge", "--parent", owner, "--standard", "orch-content",
                                "--artifacts", "git:" + "a" * 40, expect_error=True)
        self.assertEqual("review-policy", failure["code"])

    def test_policy_negative_oracle_can_fail(self):
        owner = self.owner()
        first = self.judge(owner)["judge"]["id"]
        self.finish_fixture(first)
        # With the policy removed, the same actual command wrongly admits a
        # second critique. This mutation proves the refusal oracle can fail.
        with mock.patch.object(tickets_review, "validate", return_value=None):
            admitted = self.judge(owner)
        self.assertIn("judge", admitted)

    def test_cli_refuses_invalid_policy_without_issuing_a_ticket(self):
        observed = subprocess.run([
            sys.executable, str(ROOT / "scripts/tickets.py"), "frame-open", self.RUN,
            "--goal-file", str(self.goal_file), "--shape", "do > judge",
            "--review-rounds", "0",
        ], cwd=self.candidate, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(1, observed.returncode, observed.stderr)
        self.assertEqual("review-policy", json.loads(observed.stdout)["code"])
        self.assertEqual([], list(self.run_dir().glob("*.md")))

    def test_failed_repair_predicate_closes_blocked_without_auto_successor(self):
        owner = self.owner()
        critique = self.judge(owner)["judge"]["id"]
        self.finish_fixture(critique)
        predicate = json.dumps({"form": "command", "value":
                                f'"{sys.executable}" -c "raise SystemExit(7)"'}, sort_keys=True)
        repair = self.callable("do", "--parent", owner, "--standard", CODE_STANDARD,
                               "--review-of", critique, "--done", predicate)["do"]["id"]
        path = self.run_dir() / (repair + ".md")
        decision, failure = tickets_done.resolve(
            self.RUN, repair, self.run_dir(), path, _parse_frontmatter(self.ticket_text(repair)),
            self.candidate, None, repair)
        self.assertIsNone(failure)
        self.assertEqual(("blocked", "close", 7),
                         (decision["status"], decision["action"], decision["reading"]["exit"]))
        self.assertEqual([], list(self.run_dir().glob(repair + ".repair.*.md")))

    def test_dispatch_replay_keeps_the_reserved_review_round(self):
        owner = self.owner()
        critique = self.judge(owner)["judge"]["id"]
        before = _parse_frontmatter(self.ticket_text(critique))
        attempt = json.loads(before["dispatch_v1"])["attempts"][0]
        with self._stubbed_establishment():
            replay = tickets._dispatch([
                "dispatch", self.RUN, critique, "--by", critique,
                "--dispatch-id", attempt["dispatch_id"], "--lease-expires-at", attempt["lease_expires_at"],
                "--workspace", str(self.candidate),
            ])
        self.assertNotIn("error", replay, replay)
        self.assertEqual(before["review_round"], _parse_frontmatter(self.ticket_text(critique))["review_round"])
        self.assertEqual(2, len(list(self.run_dir().glob("*.md"))))
