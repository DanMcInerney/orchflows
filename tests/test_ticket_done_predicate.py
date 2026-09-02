"""Done is a checked condition, and `land` is what checks it.

Every case here fires on the mechanism the last dogfooded gate lacked. A
child spent 14.1M tokens wrapping an exit code; the run had no lawful
round-two slot when that code was non-zero; and the tree that shipped never
had a gate run against it. So: the predicate is evaluated by `land` in the
integrated tree, its exit is the verdict, a refusal arms a repair round
instead of wedging, and the candidate is merged before any of it.
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
from tests import _retired_commands as retired_commands
from scripts import tickets
from scripts import tickets_done
from scripts.tickets_format import _sections, parse_canonical_json

# The interpreter every predicate below is run through: a bare `python` is a
# Windows Store stub, and a fixture that shipped one would be testing the
# stub's exit code.
INTERPRETER = sys.executable


def _command(code: int) -> str:
    return f'"{INTERPRETER}" -c "raise SystemExit({code})"'


def _done(form: str, value: str) -> str:
    return json.dumps({"form": form, "value": value}, sort_keys=True)


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
        # `done` has one home and one grader. The `loop` marker was the
        # second reader of this field and it is gone, so a ticket carrying
        # the marker is now refused for the unknown field it is.
        self.assertFalse(hasattr(tickets_format, "loop_defects"))
        self.assertNotIn("loop", tickets_format.ALLOWED_TICKET_KEYS)

    def test_the_predicate_is_part_of_the_sealed_assignment(self):
        """`done` says what completion means, so a changed one is a changed
        assignment."""

        from scripts import tickets_generations

        self.assertIn("done", tickets_generations.ASSIGNMENT_SYSTEM_FIELDS)


class LandDonePredicateTest(unittest.TestCase):
    """The predicate, in the composition that owns it."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        # ORCHFLOWS_WORKTREES_HOME rides beside the sink: unset, a derived
        # candidate would hang off the parent of a bare tempdir -- the
        # machine-shared system temp root -- instead of staying inside
        # this fixture's own tree (the sibling class below,
        # LandIntegratesTheCandidateTest, already carried this fix).
        self.environment = mock.patch.dict(
            os.environ,
            {
                state_root.ENV_VAR: self.temporary.name,
                "ORCHFLOWS_WORKTREES_HOME": str(
                    Path(self.temporary.name) / "worktrees"
                ),
            },
        )
        self.environment.start()
        self.candidate = git_checkout(Path(self.temporary.name) / "candidate")

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def run_command(self, *arguments):
        result = retired_commands.run(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def ticket_path(self, ticket_id="T") -> Path:
        return Path(self.temporary.name) / "tickets" / "run" / f"{ticket_id}.md"

    def stand_up(self, done=None):
        """A sealed, dispatched, closed item ready for one `land`."""

        self.run_command(
            "new", "run", "T", "--executor", "orch-do",
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
        return retired_commands.run([
            "land", "run", "T", "--assignment-seal", self.seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome",
            "--by", "root-join", *extra,
        ])

    def steps(self, landed) -> dict:
        return {step["step"]: step for step in landed["land"]["steps"]}

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

    def test_land_still_joins_after_the_workers_lease_expires(self):
        """The 2026-09-01 wedge, at the command a driver actually calls.

        `stand_up` already commits the outcome inside the worker's lease.
        The driver calling `land` days later is not the worker's overrun to
        answer for: the join is the driver's own act, and it names no
        lease of its own to have missed.
        """

        self.stand_up(_done("command", _command(0)))

        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                value = datetime(2100, 1, 1, tzinfo=timezone.utc)
                return value if tz is None else value.astimezone(tz)

        with mock.patch("scripts.tickets_attempts.datetime", Later):
            landed = self.land()

        self.assertNotIn("error", landed, landed)
        self.assertEqual("complete", landed["land"]["status"])
        self.assertEqual("checked", self.steps(landed)["done"]["outcome"])

    def test_a_refused_join_flag_leaves_everything_unmoved(self):
        """The 2026-09-01 landing defect, in its general form.

        `land --artifact` on an ordinary ticket used to merge the candidate
        before `dispatch-join` refused "review flags apply only to
        gate-stage joins" -- a refusal that had already mutated the tree it
        was refusing over. The gate-stage flags are retired now, so the
        concrete trigger is gone, but the law it exposed is general: every
        argument-shape refusal `dispatch-join` itself would raise has to run
        before `land` touches anything. A stray `--artifact` and a malformed
        `--dispatch-id` both prove it here: the predicate marker this
        Goal's own `done` command would leave behind never appears, and the
        ticket is byte-identical to before either call.
        """

        marker = Path(self.temporary.name) / "predicate-ran.txt"
        command = f'"{INTERPRETER}" -c "open(r\'{marker}\', \'w\').close()"'
        self.stand_up(_done("command", command))
        before = self.ticket_path().read_bytes()

        stray = retired_commands.run([
            "land", "run", "T", "--assignment-seal", self.seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome",
            "--by", "root-join", "--artifact", "git:" + "a" * 40,
        ])
        self.assertIn("usage: land", stray.get("error", ""), stray)
        self.assertFalse(marker.exists())
        self.assertEqual(before, self.ticket_path().read_bytes())

        malformed = retired_commands.run([
            "land", "run", "T", "--assignment-seal", self.seal,
            "--dispatch-id", "bad id", "--outcome-record-id", "outcome",
            "--by", "root-join",
        ])
        self.assertEqual("dispatch-id-invalid", malformed.get("code"), malformed)
        self.assertFalse(marker.exists())
        self.assertEqual(before, self.ticket_path().read_bytes())

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
        self.assertIn("executor: orch-do", armed)
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
        """The advance rule, now in the module that is its one reader."""

        run_dir = self.ticket_path().parent
        self.assertEqual(
            {"action": "arm", "next": 1},
            tickets_done.advance_action(run_dir, "T", tickets_done.REPAIR_MARKER, False),
        )
        self.assertEqual(
            {"action": "close", "status": "complete"},
            tickets_done.advance_action(run_dir, "T", tickets_done.REPAIR_MARKER, True),
        )

    def test_the_check_form_mints_one_orch_check_and_reads_its_joined_status(self):
        self.stand_up(_done("check", "the Goal clause no oracle covers"))

        landed = self.land()

        self.assertNotIn("error", landed, landed)
        self.assertIsNone(landed["land"]["status"])
        self.assertEqual("await-done-check", self.steps(landed)["done"]["outcome"])
        minted = self.ticket_path("T.done").read_text(encoding="utf-8")
        self.assertIn("executor: orch-judge", minted)
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


class LandIntegratesTheCandidateTest(unittest.TestCase):
    """Land merges the candidate; hand git was the step that got skipped."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(os.environ, {
            state_root.ENV_VAR: self.temporary.name,
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
        result = retired_commands.run([
            "new", "run", "T", "--executor", "orch-do",
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
        self.assertNotIn("error", retired_commands.run(["stamp-generation", "run", "T"]))
        validated = retired_commands.run(["draft-validate", "run", "T"])
        retired_commands.run([
            "seal", "run", "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        ])
        retired_commands.run(["ready", "--run", "run"])
        lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")
        # the real establishment, not a stub: this case is about the tree
        # git actually made and the branch it actually stands on
        launched = retired_commands.run([
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
        closed = retired_commands.run([
            "dispatch-outcome", "run", "T", "--note", "delivered and verified",
        ])
        self.assertNotIn("error", closed, closed)

    def land(self, *extra):
        return retired_commands.run([
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

    def test_a_land_refused_for_want_of_a_grade_leaves_no_merge_commit(self):
        """The seam the ordering is about: a refused call must not have
        moved the checkout the run is driven from."""

        self.stand_up()
        (self.candidate / "delivered.txt").write_text("done\n", encoding="utf-8")
        for arguments in (
            ("config", "user.email", "fixture@example.invalid"),
            ("config", "user.name", "fixture"),
            ("add", "delivered.txt"), ("commit", "--quiet", "-m", "deliver"),
        ):
            self.git(*arguments, cwd=self.candidate)
        self.close()
        before = self.git("rev-list", "--count", "HEAD")

        refusal = self.land()

        self.assertIn("carries no done predicate", refusal["error"])
        self.assertEqual(before, self.git("rev-list", "--count", "HEAD"))
        self.assertFalse((self.main / "delivered.txt").is_file())

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
