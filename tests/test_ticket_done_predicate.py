"""Done is a checked condition, and `land` is what checks it.

Every case here fires on the mechanism the last dogfooded gate lacked. A
child spent 14.1M tokens wrapping an exit code; the run had no lawful
round-two slot when that code was non-zero; and the tree that shipped never
had a gate run against it. So: the predicate is evaluated by `land` in the
integrated tree, its exit is the verdict, a refusal arms a repair round
instead of wedging, and the candidate is merged before any of it.
`LandRoundAdmissionTest` then drives the armed round through `ready` and
the dispatch admission door, where the loop lane's rounds had already
refused once and the landing lane's reproduced both refusals verbatim.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests._candidate_checkout import git_checkout, record_established_workspace
from scripts import state_root
from scripts import tickets
from scripts import tickets_done
from scripts import tickets_loop
from scripts.tickets_context import graded_admission, run_snapshot
from scripts.tickets_dispatch_guards import admission_failure
from scripts.tickets_format import _sections, parse_canonical_json

# The interpreter every predicate below is run through: a bare `python` is a
# Windows Store stub, and a fixture that shipped one would be testing the
# stub's exit code.
INTERPRETER = sys.executable


def _command(code: int) -> str:
    return f'"{INTERPRETER}" -c "raise SystemExit({code})"'


def _done(form: str, value: str) -> str:
    return json.dumps({"form": form, "value": value}, sort_keys=True)


# An author-written child of the landed ticket: it is an id-descendant like
# a round is, and it is not a round, so it is what tells the shape exemption
# from a hole in the shape check.
AUTHORED_CHILD = """---
id: T.extra
run: run
status: pending
executor: orch-execute
pack: orch-code-pack
depends_on: []
bound: 30m
independence: checker
isolation: none
---

## Goal

A hand-authored child of a landed ticket, which is not one of its rounds.

## Context

- input: written straight into the run directory.

## Report
"""


class DonePredicateGrammarTest(unittest.TestCase):
    """One parser owns `{form, value}` for both of its homes."""

    def test_the_loops_done_and_a_tickets_done_are_graded_by_one_owner(self):
        from scripts import tickets_format

        for value, expected in (
            ('{"form": "command", "value": "ok"}', []),
            ('{"form": "check", "value": "the criterion"}', []),
            ('{"form": "guess", "value": "x"}', ["done form must be one of"]),
            ('{"form": "command"}', ["done is missing required field 'value'"]),
            ('{"form": "command", "value": ""}', ["done value is empty"]),
            ('{"form": "command", "value": "x", "extra": 1}',
             ["done carries unknown field 'extra'"]),
            ("not json", ["done is not canonical JSON"]),
        ):
            with self.subTest(value=value):
                defects = tickets_format.done_defects(value)
                self.assertEqual(len(expected), len(defects), defects)
                for fragment, defect in zip(expected, defects):
                    self.assertIn(fragment, defect)
        # The loop has no second home for it: the marker moves who reads the
        # one `done`, and a marker with nothing to read is refused.
        self.assertEqual(
            [], tickets_format.loop_defects("true", "orch-execute", _done("command", "ok")),
        )
        marked = tickets_format.loop_defects("true", "orch-execute", "")
        self.assertTrue(any("carries the `done` predicate" in item for item in marked))
        valued = tickets_format.loop_defects(
            '{"done": {"form": "command", "value": "ok"}}', "orch-execute",
            _done("command", "ok"),
        )
        self.assertTrue(any("takes no other value" in item for item in valued))

    def test_the_predicate_is_part_of_the_sealed_assignment(self):
        """`done` says what completion means, so a changed one is a changed
        assignment -- the rule `loop` already answers to."""

        from scripts import tickets_generations

        self.assertIn("done", tickets_generations.ASSIGNMENT_SYSTEM_FIELDS)


class LandTrunkTest(unittest.TestCase):
    """The temp sink, candidate checkout, and one landing every case runs on.

    `stand_up` walks the whole trunk short of `land`: new, done binding,
    stamp, validate, seal, ready, dispatch, outcome.
    """

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(
            os.environ, {"ORCHFLOWS_STATE_HOME": self.temporary.name}
        )
        self.environment.start()
        self.candidate = git_checkout(Path(self.temporary.name) / "candidate")

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def run_command(self, *arguments):
        result = tickets._dispatch(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def ticket_path(self, ticket_id="T") -> Path:
        return Path(self.temporary.name) / "tickets" / "run" / f"{ticket_id}.md"

    def stand_up(self, done=None):
        """A sealed, dispatched, closed item ready for one `land`."""

        self.run_command(
            "new", "run", "T", "--executor", "orch-execute",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--pack", "orch-code-pack", "--isolation", "none",
        )
        if done is not None:
            path = self.ticket_path()
            path.write_text(
                tickets._set_frontmatter_field(
                    path.read_text(encoding="utf-8"), "done", done,
                ),
                encoding="utf-8",
            )
        self.run_command("stamp-generation", "run", "T")
        validated = self.run_command("draft-validate", "run", "T")
        self.run_command(
            "seal", "run", "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        self.run_command("ready", "--run", "run")
        lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")

        def establish(run, ticket_id, _workspace):
            record_established_workspace(
                self.ticket_path(ticket_id), self.candidate, strict=False,
            )
            return {"establish": {"workspace_path": str(self.candidate)}}

        with mock.patch.object(
            tickets._tickets_dispatch_facade_module, "_workspace_establish",
            side_effect=establish,
        ):
            self.run_command(
                "dispatch", "run", "T", "--by", "worker", "--dispatch-id", "D1",
                "--lease-expires-at", lease, "--workspace", str(self.candidate),
            )
        self.seal = parse_canonical_json(tickets._parse_frontmatter(
            self.ticket_path().read_text(encoding="utf-8")
        )["dispatch_v1"])["attempts"][0]["assignment_seal"]
        self.run_command(
            "dispatch-outcome", "run", "T", "--note", "delivered and verified",
        )

    def land(self, *extra):
        return tickets._dispatch([
            "land", "run", "T", "--assignment-seal", self.seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome",
            "--by", "root-join", *extra,
        ])

    def steps(self, landed) -> dict:
        return {step["step"]: step for step in landed["land"]["steps"]}

    def _codes(self, ticket_id):
        """The admission finding codes one ticket carries right now."""

        snapshot, failures = run_snapshot(self.ticket_path().parent)
        self.assertEqual([], failures, failures)
        grade = graded_admission(ticket_id, snapshot[ticket_id], snapshot, "run")
        return {str(item["code"]) for item in grade["findings"]}


class LandDonePredicateTest(LandTrunkTest):
    """The predicate, in the composition that owns it."""

    def test_a_passing_command_is_the_verdict_and_land_files_its_evidence(self):
        command = _command(0)
        self.stand_up(_done("command", command))

        landed = self.land()

        self.assertNotIn("error", landed, landed)
        self.assertEqual("complete", landed["land"]["status"])
        self.assertEqual(0, landed["land"]["done"]["exit"])
        self.assertEqual("checked", self.steps(landed)["done"]["outcome"])
        verification = _sections(
            self.ticket_path().read_text(encoding="utf-8")
        )["Report"]
        self.assertIn("### Written by `root-join`", verification)
        self.assertIn(f"done command `{command}` exited 0 in ", verification)

    def test_a_refused_command_arms_a_repair_round_instead_of_wedging(self):
        """The round-two slot the composite gate never had.

        The last real run stopped here: a failing final check with nothing
        lawful to dispatch next, so the remedy went in by hand outside the
        protocol. Now the refusal arms `T.repair.1`, the ticket stays open,
        and landing again re-runs the predicate.
        """

        command = _command(3)
        self.stand_up(_done("command", command))

        landed = self.land()

        self.assertNotIn("error", landed, landed)
        self.assertIsNone(landed["land"]["status"])
        self.assertEqual(3, landed["land"]["done"]["exit"])
        step = self.steps(landed)["done"]
        self.assertEqual("arm", step["outcome"])
        self.assertEqual("T.repair.1", step["repair"])
        armed = self.ticket_path("T.repair.1").read_text(encoding="utf-8")
        self.assertIn("executor: orch-execute", armed)
        self.assertIn("exits 3 there now", armed)
        # the ticket is not closed: nothing joined, so nothing is terminal
        self.assertIn(
            "status: claimed", self.ticket_path().read_text(encoding="utf-8"),
        )
        # and landing again is lawful, and finds the round it already armed
        again = self.land()
        self.assertEqual("T.repair.1", self.steps(again)["done"]["repair"])
        self.assertEqual("replayed", self.steps(again)["done"]["outcome_detail"])

    def test_two_rounds_with_no_delta_close_the_ticket_stalled(self):
        """`tickets_loop`'s own rule, reached through the second marker."""

        run_dir = self.ticket_path().parent
        self.assertEqual(
            {"action": "arm", "next": 1},
            tickets_loop.advance_action(run_dir, "T", tickets_loop.REPAIR_MARKER, False),
        )
        self.assertEqual(
            {"action": "close", "status": "complete"},
            tickets_loop.advance_action(run_dir, "T", tickets_loop.REPAIR_MARKER, True),
        )

    def test_the_check_form_mints_one_orch_check_and_reads_its_joined_status(self):
        self.stand_up(_done("check", "the Goal clause no oracle covers"))

        landed = self.land()

        self.assertNotIn("error", landed, landed)
        self.assertIsNone(landed["land"]["status"])
        self.assertEqual("await-done-check", self.steps(landed)["done"]["outcome"])
        minted = self.ticket_path("T.done").read_text(encoding="utf-8")
        self.assertIn("executor: orch-check", minted)
        self.assertIn("the Goal clause no oracle covers", minted)
        # no lane, no verdict token: the check files findings and the
        # authority that joins it records the disposition
        self.assertNotIn("review_kind:", minted)
        for token in ("PASS:", "FAIL:", "UNVERIFIED:"):
            self.assertNotIn(token, minted)

    def test_a_ticket_with_no_predicate_still_takes_the_drivers_grade(self):
        self.stand_up()

        landed = self.land("--status", "limited")

        self.assertNotIn("error", landed, landed)
        self.assertEqual("limited", landed["land"]["status"])
        self.assertEqual("graded", self.steps(landed)["done"]["outcome"])

    def test_the_two_grade_paths_refuse_to_be_used_together_or_neither(self):
        self.stand_up()
        missing = self.land()
        self.assertIn("--status", missing["error"])

        self.tearDown()
        self.setUp()
        self.stand_up(_done("command", _command(0)))
        both = self.land("--status", "complete")
        self.assertIn("land evaluates", both["error"])


class LandRoundAdmissionTest(LandTrunkTest):
    """A landing's armed round crosses `ready` and the dispatch admission door.

    The loop lane refused `sealed-assignment-mismatch` and
    `graph-direct-members` the first time it was driven through the trunk,
    and the landing lane reproduced both verbatim: `land` mints its
    `<id>.repair.NN` round and `<id>.done` judge through the same machinery
    past the same seal, under a parent whose licence is the `done` predicate
    rather than the loop marker.
    """

    def _arm_repair_round(self):
        """One failing command-form landing, and the round it armed."""

        self.stand_up(_done("command", _command(3)))
        landed = self.land()
        self.assertNotIn("error", landed, landed)
        self.assertEqual("T.repair.1", self.steps(landed)["done"]["repair"])

    def test_ready_promotes_the_armed_round_and_the_landing_owns_no_members(self):
        self._arm_repair_round()
        self.assertNotIn("graph-direct-members", self._codes("T"))
        promoted = self.run_command("ready", "--run", "run")
        self.assertIn(
            "T.repair.1", {item["id"] for item in promoted["ready"]}, promoted,
        )
        path = self.ticket_path("T.repair.1")
        text = path.read_text(encoding="utf-8")
        self.assertIsNone(admission_failure(
            path, text, tickets._parse_frontmatter(text), "run", "T.repair.1",
        ))

    def test_a_round_edited_after_it_was_armed_is_bound_by_nothing(self):
        self._arm_repair_round()
        self.assertEqual(set(), self._codes("T.repair.1"))
        path = self.ticket_path("T.repair.1")
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "done predicate pass", "done predicate sing", 1,
            ),
            encoding="utf-8",
        )
        self.assertIn("sealed-assignment-mismatch", self._codes("T.repair.1"))

    def test_a_hand_authored_child_of_a_landed_ticket_is_still_refused(self):
        self._arm_repair_round()
        self.assertNotIn("graph-direct-members", self._codes("T"))
        (self.ticket_path().parent / "T.extra.md").write_text(
            AUTHORED_CHILD, encoding="utf-8",
        )
        self.assertIn("graph-direct-members", self._codes("T"))

    def test_a_round_whose_landing_the_seal_does_not_name_is_refused(self):
        self._arm_repair_round()
        self.assertEqual(set(), self._codes("T.repair.1"))
        parent = self.ticket_path()
        parent.write_text(tickets._set_frontmatter_field(
            parent.read_text(encoding="utf-8"), "assignment_seal",
            "sha256:" + "0" * 64,
        ), encoding="utf-8")
        self.assertIn("sealed-landing-mismatch", self._codes("T.repair.1"))

    def test_the_minted_done_judge_binds_through_the_landed_ticket(self):
        self.stand_up(_done("check", "the Goal clause no oracle covers"))
        landed = self.land()
        self.assertEqual("await-done-check", self.steps(landed)["done"]["outcome"])
        self.assertNotIn("graph-direct-members", self._codes("T"))
        # The two lane refusals are gone; what stands is the judge's own
        # dependency on the still-claimed ticket it judges, a readiness
        # wedge the admission door does not own. Pinned exactly so the fix
        # that clears it retires this line too.
        self.assertEqual({"dependency-incomplete"}, self._codes("T.done"))


class LandIntegratesTheCandidateTest(unittest.TestCase):
    """Land merges the candidate; hand git was the step that got skipped."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(os.environ, {
            "ORCHFLOWS_STATE_HOME": self.temporary.name,
            # the derived candidate lives beside the sink, never in the
            # host's own worktree root, or this fixture would meet a tree
            # some other run left there
            "ORCHFLOWS_WORKTREES_HOME": str(
                Path(self.temporary.name) / "worktrees"
            ),
        })
        self.environment.start()
        self.main = self.repository(Path(self.temporary.name) / "main")

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def git(self, *arguments, cwd=None):
        completed = subprocess.run(
            ["git", *arguments], cwd=str(cwd or self.main), text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise unittest.SkipTest(f"git {' '.join(arguments)}: {completed.stderr}")
        return completed.stdout.strip()

    def repository(self, path: Path) -> Path:
        checkout = git_checkout(path)
        (checkout / "seed.txt").write_text("seed\n", encoding="utf-8")
        for arguments in (
            ("config", "user.email", "fixture@example.invalid"),
            ("config", "user.name", "fixture"),
            ("add", "seed.txt"),
            ("commit", "--quiet", "-m", "seed"),
        ):
            self.git(*arguments, cwd=checkout)
        return checkout

    def stand_up(self, done=None):
        result = tickets._dispatch([
            "new", "run", "T", "--executor", "orch-execute",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--pack", "orch-code-pack", "--isolation", "required",
        ])
        self.assertNotIn("error", result, result)
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        if done is not None:
            path.write_text(
                tickets._set_frontmatter_field(
                    path.read_text(encoding="utf-8"), "done", done,
                ),
                encoding="utf-8",
            )
        self.assertNotIn("error", tickets._dispatch(["stamp-generation", "run", "T"]))
        validated = tickets._dispatch(["draft-validate", "run", "T"])
        tickets._dispatch([
            "seal", "run", "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        ])
        tickets._dispatch(["ready", "--run", "run"])
        lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")
        # the real establishment, not a stub: this case is about the tree
        # git actually made and the branch it actually stands on
        launched = tickets._dispatch([
            "dispatch", "run", "T", "--by", "worker", "--dispatch-id", "D1",
            "--lease-expires-at", lease, "--workspace", str(self.main),
        ])
        self.assertNotIn("error", launched, launched)
        self.seal = parse_canonical_json(tickets._parse_frontmatter(
            path.read_text(encoding="utf-8")
        )["dispatch_v1"])["attempts"][0]["assignment_seal"]
        self.candidate = state_root.candidate_paths("run", "T")["path"]
        return path

    def close(self):
        closed = tickets._dispatch([
            "dispatch-outcome", "run", "T", "--note", "delivered and verified",
        ])
        self.assertNotIn("error", closed, closed)

    def land(self, *extra):
        return tickets._dispatch([
            "land", "run", "T", "--assignment-seal", self.seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome",
            "--by", "root-join", *extra,
        ])

    def test_the_candidates_commits_reach_the_tree_the_run_stands_in(self):
        self.stand_up()
        (self.candidate / "delivered.txt").write_text("done\n", encoding="utf-8")
        for arguments in (
            ("config", "user.email", "fixture@example.invalid"),
            ("config", "user.name", "fixture"),
            ("add", "delivered.txt"), ("commit", "--quiet", "-m", "deliver"),
        ):
            self.git(*arguments, cwd=self.candidate)
        self.close()

        landed = self.land("--status", "complete")

        self.assertNotIn("error", landed, landed)
        step = next(
            item for item in landed["land"]["steps"]
            if item["step"] == "workspace-integrate"
        )
        self.assertEqual("merged", step["outcome"])
        self.assertTrue((self.main / "delivered.txt").is_file())

    def test_a_conflicted_merge_refuses_naming_the_files_and_the_remedy(self):
        self.stand_up()
        (self.candidate / "seed.txt").write_text("candidate\n", encoding="utf-8")
        for arguments in (
            ("config", "user.email", "fixture@example.invalid"),
            ("config", "user.name", "fixture"),
            ("add", "seed.txt"), ("commit", "--quiet", "-m", "candidate"),
        ):
            self.git(*arguments, cwd=self.candidate)
        (self.main / "seed.txt").write_text("main\n", encoding="utf-8")
        self.git("commit", "--quiet", "-am", "main")
        self.close()

        refusal = self.land("--status", "complete")

        self.assertIn("seed.txt", refusal["error"])
        self.assertIn("land run/T again", refusal["error"])
        # aborted, never handed back mid-merge
        self.assertEqual("", self.git("ls-files", "--unmerged"))
        self.assertIn(
            "status: claimed",
            (Path(self.temporary.name) / "tickets" / "run" / "T.md").read_text(
                encoding="utf-8"
            ),
        )


if __name__ == "__main__":
    unittest.main()
