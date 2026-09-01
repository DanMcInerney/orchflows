"""The durable call stack: what a frame is, and what its close refuses.

Every case fires on something the design bought and nothing else provides.
A frame is minted, sealed and journalled without ever being dispatched --
so it carries no executor and no pack, and the ordinary `result` command
is what its driver appends waves to. Its close is a recording act, and it
refuses the one thing a prose driver silently gets away with: shipping two
artifacts nobody read together. `orchflows resume` is the pull that finds
the frames again, filtered to the project the caller is standing in.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from scripts import orchflows, state_root, tickets
from scripts.tickets_mint import DO_EXECUTOR
from scripts.tickets_format import (
    _parse_frontmatter, _sections, _set_frontmatter_field, ticket_defects,
)
from scripts.tickets_store import UTC_STAMP

DOC_PACK = "orch-content-pack"
GOAL = "Deliver the migration wave.\nAnd say what it cost.\n"
FIXED_NOW = "2026-08-31T12:00:00Z"


class FrameSinkTest(unittest.TestCase):
    """A temp sink, and the workspace establishment a callable would really do."""

    RUN = "framerun"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        # ORCHFLOWS_WORKTREES_HOME rides beside the sink: unset, a derived
        # candidate would hang off the parent of a bare tempdir -- the
        # machine-shared system temp root -- instead of staying inside
        # this fixture's own tree.
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
        self.goal_file = Path(self.temporary.name) / "goal.md"
        self.goal_file.write_text(GOAL, encoding="utf-8")

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def run_dir(self, run=None) -> Path:
        return Path(self.temporary.name) / "tickets" / (run or self.RUN)

    def ticket_text(self, ticket_id: str, run=None) -> str:
        return (self.run_dir(run) / f"{ticket_id}.md").read_text(encoding="utf-8")

    def call(self, *arguments, expect_error=False) -> dict:
        """One subcommand, with a callable's workspace establishment stubbed.

        A frame establishes nothing -- that is the point of it -- but the
        `do` and `judge` children these cases open are ordinary callables, and
        stubbing the tree they would be cut into keeps the case about the
        frame rather than about git.
        """

        facade = tickets._tickets_dispatch_facade_module
        with mock.patch.object(
            facade, "_workspace_establish",
            side_effect=lambda *_: {
                "establish": {"workspace_path": self.temporary.name},
            },
        ), mock.patch.object(
            facade, "_workspace_prepare", return_value={"outcome": "skipped"},
        ):
            answer = tickets._dispatch(list(arguments))
        if expect_error:
            self.assertIn("error", answer, answer)
        else:
            self.assertNotIn("error", answer, answer)
        return answer

    def frame(self, *arguments, run=None) -> dict:
        opened = self.call(
            "frame-open", run or self.RUN, "--goal-file", str(self.goal_file),
            *arguments,
        )
        return opened["frame_open"]

    def callable(self, verb, frame_id, *arguments, run=None) -> str:
        answer = self.call(
            verb, run or self.RUN, "--pack", DOC_PACK,
            "--goal-file", str(self.goal_file), "--parent", frame_id,
            *arguments,
        )
        return answer[verb]["id"]

    def journal(self, frame: dict, text: str, record_id: str, run=None):
        return self.call(
            "result", run or self.RUN, frame["id"],
            "--assignment-seal", frame["assignment_seal"],
            "--dispatch-id", frame["dispatch_id"],
            "--record-id", record_id, "--by", frame["journal_by"],
            "--text", text,
        )


class FrameShapeTest(FrameSinkTest):
    """A frame binds no craft and dispatches nothing, and says so in bytes."""

    def test_opening_a_frame_mints_the_run_and_seals_its_goal(self):
        self.assertFalse(self.run_dir().exists())

        frame = self.frame()

        self.assertEqual("B1", frame["id"])
        self.assertIsNone(frame["parent"])
        data = _parse_frontmatter(self.ticket_text("B1"))
        self.assertEqual("true", data["frame"])
        self.assertNotIn("executor", data)
        self.assertNotIn("pack", data)
        self.assertTrue(data["root_generation"].startswith("root:B1:1:sha256:"))
        self.assertEqual(frame["assignment_seal"], data["assignment_seal"])
        self.assertEqual("claimed", data["status"])
        self.assertEqual(
            GOAL.strip(), _sections(self.ticket_text("B1"))["Goal"].strip(),
        )
        # the run the first frame-open brought into being
        identity = json.loads(
            (Path(self.temporary.name) / "runs" / self.RUN / "run.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(self.RUN, identity["run"])

    def test_a_called_frame_hangs_under_its_caller_and_seals_through_it(self):
        parent = self.frame()

        child = self.frame("--parent", parent["id"])

        self.assertEqual("B1.1", child["id"])
        outer = _parse_frontmatter(self.ticket_text("B1"))
        inner = _parse_frontmatter(self.ticket_text("B1.1"))
        self.assertEqual("B1", inner["parent"])
        for field in ("root_generation", "cut_generation"):
            self.assertEqual(outer[field], inner[field])
        self.assertNotEqual(outer["assignment_seal"], inner["assignment_seal"])
        self.assertIn("- parent: B1", _sections(self.ticket_text("B1.1"))["Context"])

    def test_a_frame_carrying_a_craft_binding_is_off_contract(self):
        for field, value, refusal in (
            ("executor", DO_EXECUTOR, "a frame binds no executor"),
            ("pack", DOC_PACK, "a frame binds no pack"),
            ("frame", "yes", "frame is the marker `true`"),
        ):
            text = _set_frontmatter_field(_ticket("frame: true\n"), field, value)
            self.assertTrue(
                any(refusal in defect for defect in ticket_defects(text)),
                (field, ticket_defects(text)),
            )

    def test_an_ordinary_ticket_still_owes_its_executor(self):
        self.assertIn(
            "frontmatter has no 'executor'", ticket_defects(_ticket("")),
        )
        self.assertNotIn(
            "frontmatter has no 'executor'",
            ticket_defects(_ticket("frame: true\n")),
        )


class FrameJournalTest(FrameSinkTest):
    """The journal is the driver's working memory, and it rides `result`."""

    def test_a_wave_appends_through_the_result_channel_under_the_frames_identity(self):
        frame = self.frame()

        self.journal(frame, "wave 1: two drafts out", "wave-1")
        self.journal(frame, "wave 2: judged, closing", "wave-2")

        journal = _sections(self.ticket_text("B1"))["Report"]
        self.assertIn("### Written by `B1`", journal)
        self.assertIn("wave 1: two drafts out", journal)
        self.assertLess(
            journal.index("wave 1: two drafts out"),
            journal.index("wave 2: judged, closing"),
        )

    def test_a_journal_append_outlives_the_frames_nominal_expiry(self):
        """A frame carries no lease to arbitrate; only its close ends it."""

        frame = self.frame("--bound", "1m")
        path = self.run_dir() / "B1.md"
        now = datetime.now(timezone.utc)
        text = self.ticket_text("B1")
        state = json.loads(_parse_frontmatter(text)["dispatch_v1"])
        state["attempts"][0].update({
            "opened_at": (now - timedelta(minutes=10)).strftime(UTC_STAMP),
            "lease_expires_at": (now - timedelta(minutes=5)).strftime(UTC_STAMP),
        })
        path.write_text(_set_frontmatter_field(
            text, "dispatch_v1",
            json.dumps(state, separators=(",", ":"), sort_keys=True),
        ), encoding="utf-8")

        self.journal(frame, "wave 9: still driving", "wave-9")

        self.assertIn(
            "wave 9: still driving", _sections(self.ticket_text("B1"))["Report"],
        )


class FrameCloseTest(FrameSinkTest):
    """The close records, and refuses the composition nobody read."""

    def _two_do_children(self, frame: dict) -> list:
        return [self.callable("do", frame["id"]) for _ in range(2)]

    def test_a_close_over_two_unjudged_do_children_is_refused_by_name(self):
        frame = self.frame()
        self._two_do_children(frame)

        refused = self.call(
            "frame-close", self.RUN, frame["id"], "--status", "complete",
            expect_error=True,
        )

        self.assertEqual(
            "frame framerun/B1 closes over 2 do-children (B1.1, B1.2) and its "
            "subtree holds no judge: nobody has read those artifacts together, "
            "and this close would record that silently. Open one "
            "`tickets.py judge` under this frame, or write one "
            "`unjudged: <reason>` line into its journal (## Report) and close "
            "again. Nothing was recorded.",
            refused["error"],
        )
        self.assertEqual("claimed", _parse_frontmatter(self.ticket_text("B1"))["status"])

    def test_a_judge_under_the_frame_lets_the_same_close_land(self):
        frame = self.frame()
        self._two_do_children(frame)
        judge = self.callable(
            "judge", frame["id"], "--artifacts", "doc:draft.md@sha256:" + "e" * 64,
        )

        closed = self.call(
            "frame-close", self.RUN, frame["id"], "--status", "complete",
        )["frame_close"]

        self.assertEqual("complete", closed["status"])
        self.assertEqual(["B1.1", "B1.2"], closed["do_children"])
        self.assertEqual([judge], closed["judges"])
        self.assertEqual(
            "complete", _parse_frontmatter(self.ticket_text("B1"))["status"],
        )
        self.assertIn(
            "frame closed complete over 2 do-children; judged by B1.3.",
            _sections(self.ticket_text("B1"))["Report"],
        )

    def test_a_stated_reason_in_the_journal_is_the_other_lawful_close(self):
        frame = self.frame()
        self._two_do_children(frame)
        self.journal(
            frame, "unjudged: both drafts go straight to the user, who reads them",
            "wave-1",
        )

        closed = self.call(
            "frame-close", self.RUN, frame["id"], "--status", "limited",
        )["frame_close"]

        self.assertEqual("limited", closed["status"])
        self.assertEqual(
            "both drafts go straight to the user, who reads them",
            closed["unjudged"],
        )

    def test_an_unjudged_line_with_no_reason_buys_nothing(self):
        frame = self.frame()
        self._two_do_children(frame)
        self.journal(frame, "unjudged:", "wave-1")

        refused = self.call(
            "frame-close", self.RUN, frame["id"], "--status", "complete",
            expect_error=True,
        )

        self.assertIn("holds no judge", refused["error"])

    def test_a_refused_done_command_leaves_the_frame_open_and_unwritten(self):
        frame = self.frame()
        before = self.ticket_text("B1")

        refused = self.call(
            "frame-close", self.RUN, frame["id"], "--done", _exit_command(3),
            expect_error=True,
        )

        self.assertIn("exited 3", refused["error"])
        self.assertIn("the frame stays open", refused["error"])
        self.assertEqual(before, self.ticket_text("B1"))

    def test_a_passing_done_command_is_what_closes_the_frame_complete(self):
        frame = self.frame()

        closed = self.call(
            "frame-close", self.RUN, frame["id"], "--done", _exit_command(0),
        )["frame_close"]

        self.assertEqual("complete", closed["status"])
        self.assertEqual(0, closed["done"]["exit"])
        self.assertIn("done command", _sections(self.ticket_text("B1"))["Report"])

    def test_a_frame_that_sealed_its_gate_at_open_evaluates_that_one(self):
        frame = self.frame("--done", _exit_command(0))

        refused = self.call(
            "frame-close", self.RUN, frame["id"], "--status", "complete",
            expect_error=True,
        )
        self.assertIn("sealed its own done at open", refused["error"])

        self.assertEqual("complete", self.call(
            "frame-close", self.RUN, frame["id"],
        )["frame_close"]["status"])

    def test_a_judged_criterion_is_a_judge_callable_rather_than_a_frame_gate(self):
        refused = self.call(
            "frame-open", self.RUN, "--goal-file", str(self.goal_file),
            "--done", json.dumps(
                {"form": "check", "value": "the thesis holds"}, sort_keys=True,
            ),
            expect_error=True,
        )

        self.assertIn("a frame's done is a command", refused["error"])
        self.assertFalse(self.run_dir().exists())

    def test_land_stays_the_callable_command_and_frame_close_says_so(self):
        frame = self.frame()
        callable_ticket = self.callable("do", frame["id"])

        refused = self.call(
            "frame-close", self.RUN, callable_ticket, "--status", "complete",
            expect_error=True,
        )

        self.assertIn("is not a frame", refused["error"])
        self.assertIn("tickets.py land", refused["error"])


class ResumeTest(FrameSinkTest):
    """The pull that finds a project's open frames again."""

    def _resume(self, *arguments) -> str:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = orchflows.main(["resume", *arguments])
        self.assertEqual(0, code)
        return stdout.getvalue()

    def _hold_open_at(self, ticket_id: str, opened: str):
        """Freeze one frame's opening instant so an age is assertable."""

        path = self.run_dir() / f"{ticket_id}.md"
        text = path.read_text(encoding="utf-8")
        state = json.loads(_parse_frontmatter(text)["dispatch_v1"])
        state["attempts"][0]["opened_at"] = opened
        path.write_text(_set_frontmatter_field(
            text, "dispatch_v1",
            json.dumps(state, separators=(",", ":"), sort_keys=True),
        ), encoding="utf-8")

    def test_an_empty_sink_says_so_rather_than_printing_a_header(self):
        self.assertEqual(
            "no open frames for this project\n", self._resume(),
        )

    def test_one_open_frame_is_listed_with_its_goal_age_and_children(self):
        frame = self.frame()
        self.journal(frame, "wave 1: one draft out", "wave-1")
        self.callable("do", frame["id"])
        self._hold_open_at("B1", "2026-08-31T10:30:00Z")

        listing = self._resume("--now", FIXED_NOW)

        self.assertEqual(
            "frame  run       age  journal  children  leases  goal\n"
            "B1     framerun  1h   yes      1         1       "
            "Deliver the migration wave.\n",
            listing,
        )

    def test_a_closed_frame_leaves_the_listing_and_a_nested_one_joins_it(self):
        frame = self.frame()
        self.frame("--parent", frame["id"])

        self.assertEqual(2, len(self._resume().splitlines()) - 1)
        self.call("frame-close", self.RUN, "B1.1", "--status", "complete")
        remaining = self._resume().splitlines()[1:]
        self.assertEqual(1, len(remaining))
        self.assertTrue(remaining[0].startswith("B1 "), remaining)

    def test_another_projects_run_is_not_this_projects_to_resume(self):
        self.frame()
        identity = Path(self.temporary.name) / "runs" / self.RUN / "run.json"
        document = json.loads(identity.read_text(encoding="utf-8"))
        document["project"] = {
            "root": "/somewhere/else", "origin": "https://example.invalid/other",
            "name": "other",
        }
        identity.write_text(json.dumps(document), encoding="utf-8")

        self.assertEqual(
            "no open frames for this project\n", self._resume(),
        )


def _ticket(extra: str) -> str:
    """The smallest whole ticket, plus whatever frontmatter a case is about."""

    return (
        f"---\nid: F\nrun: r\nstatus: pending\nbound: 60m\n{extra}---\n\n"
        "## Goal\n\nOne end.\n\n## Context\n\n[]\n\n## Report\n"
    )


def _exit_command(code: int) -> str:
    """One frozen done predicate whose command exits ``code``."""

    return json.dumps(
        {"form": "command", "value": f'"{sys.executable}" -c "raise SystemExit({code})"'},
        sort_keys=True,
    )


if __name__ == "__main__":
    unittest.main()
