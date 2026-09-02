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
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tests._repo_root import ROOT
from scripts import orchflows, orchflows_scaffold, state_root, tickets
from scripts.tickets_mint import DO_EXECUTOR
from scripts.tickets_format import (
    _parse_frontmatter, _sections, _set_frontmatter_field, ticket_defects,
)
from scripts.tickets_store import UTC_STAMP
from scripts.tickets_shape_line import (
    GRAMMAR_TOKENS, RESERVED_NAMES, SHAPE_GRAMMAR,
)

DOC_PACK = "orch-content-pack"
GOAL = "Deliver the migration wave.\nAnd say what it cost.\n"
FIXED_NOW = "2026-08-31T12:00:00Z"
# Every root frame states its wave plan at open, so every fixture that opens
# one carries a lawful line.
SHAPE = "outline > [do, do] > judge"


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
        if not {"--shape", "--workflow", "--parent"} & set(arguments):
            arguments = ("--shape", SHAPE, *arguments)
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


class FrameShapeLineTest(FrameSinkTest):
    """The wave plan a root frame states before its first dispatch.

    A shape is worth a command's refusal only where writing none is the
    cheap path: an unplanned root is exactly the frame nobody can audit
    later, so it never gets minted. Everything after the open is printed,
    not enforced -- the plan is intent, and work that outgrows it is the
    ordinary case, not a defect.
    """

    def open_shapeless(self, *arguments, run=None):
        """`frame-open` with no default line injected, for the refusals."""

        return self.call(
            "frame-open", run or self.RUN, "--goal-file", str(self.goal_file),
            *arguments, expect_error=True,
        )

    def test_a_root_frame_with_no_plan_is_refused_before_anything_is_minted(self):
        refused = self.open_shapeless()

        self.assertIn('--shape "<line>"', refused["error"])
        self.assertIn("--workflow NAME", refused["error"])
        # The grammar, in the one line the refusal prints.
        for notation in ("`a > b`", "`[a, b]`", "`a[*]`", "`do`, `outline`, `judge`"):
            self.assertIn(notation, refused["error"])
        self.assertFalse(self.run_dir().exists())

    def test_one_ticket_is_the_worker_lane_and_the_refusal_says_which_command(self):
        refused = self.open_shapeless("--shape", "do")

        self.assertEqual(
            "one ticket is the worker lane: run tickets.py do", refused["error"],
        )
        self.assertFalse(self.run_dir().exists())

    def test_the_direct_lane_opens_no_frame_at_all(self):
        refused = self.open_shapeless("--shape", "direct")

        self.assertIn("direct opens no frame", refused["error"])
        self.assertFalse(self.run_dir().exists())

    def test_an_unparseable_line_names_the_first_token_that_does_not_belong(self):
        """Where, not merely that: a hand-written line's author cannot
        derive the position of the mistake from a bare rejection."""

        for line, token in (
            ("draft judge", "judge"),
            ("draft > > judge", ">"),
            ("draft >", ">"),
            ("draft, judge", ","),
            ("draft[3]", "3"),
            ("[draft, [judge]]", "["),
            ("draft > judge!", "!"),
        ):
            with self.subTest(shape=line):
                refused = self.open_shapeless("--shape", line)
                self.assertIn(f"does not parse at `{token}`", refused["error"])
                self.assertFalse(self.run_dir().exists())

    def test_a_lawful_line_of_every_construct_opens_the_frame(self):
        """Waves, a parallel wave, an outline-decided count, and a free name
        -- `do` is lawful inside a line and refused only as the whole of it."""

        for index, line in enumerate((
            "outline > [do, do] > judge",
            "draft[*] > judge",
            "[draft, review] > assemble",
            "one-off_pass.2",
            "do > judge",
        )):
            with self.subTest(shape=line):
                frame = self.frame("--shape", line, run=f"shaperun{index}")
                self.assertEqual(line, frame["shape"])

    def test_a_saved_workflows_name_stands_in_for_the_line(self):
        frame = self.frame("--workflow", "self-improve")

        self.assertEqual("workflow:self-improve", frame["shape"])
        self.assertIn(
            "shape: workflow:self-improve",
            _sections(self.ticket_text("B1"))["Report"],
        )

    def test_an_explicit_line_outranks_the_workflow_it_was_written_beside(self):
        frame = self.frame("--shape", SHAPE, "--workflow", "self-improve")

        self.assertEqual(SHAPE, frame["shape"])

    def test_a_called_frame_is_already_a_wave_of_its_callers_plan(self):
        parent = self.frame()

        child = self.frame("--parent", parent["id"])

        self.assertIsNone(child["shape"])
        self.assertEqual("", _sections(self.ticket_text("B1.1"))["Report"].strip())

    def test_the_shape_is_the_frames_first_record_on_the_result_channel(self):
        frame = self.frame()

        self.journal(frame, "wave 1: two drafts out", "wave-1")

        journal = _sections(self.ticket_text("B1"))["Report"]
        # Written through `result`, so it carries that channel's attribution
        # rather than a hand-placed line, and it is there before wave one.
        self.assertIn("### Written by `B1`", journal)
        self.assertIn(f"shape: {SHAPE}", journal)
        self.assertLess(
            journal.index(f"shape: {SHAPE}"),
            journal.index("wave 1: two drafts out"),
        )

    def test_a_second_record_may_not_reuse_the_shape_record_id(self):
        """The record id is `shape`, and `result` fences one per id."""

        frame = self.frame()

        answer = self.call(
            "result", self.RUN, frame["id"],
            "--assignment-seal", frame["assignment_seal"],
            "--dispatch-id", frame["dispatch_id"],
            "--record-id", "shape", "--by", frame["journal_by"],
            "--text", "shape: something else", expect_error=True,
        )
        self.assertIn("error", answer)

    def test_the_close_prints_the_plan_beside_what_was_actually_minted(self):
        frame = self.frame()
        self.callable("do", frame["id"])

        closed = self.call(
            "frame-close", self.RUN, frame["id"], "--status", "complete",
        )["frame_close"]

        self.assertEqual(SHAPE, closed["shape"])
        self.assertIn(
            f"shape {SHAPE}; frame closed complete over 1 do and 0 judge "
            "children;",
            _sections(self.ticket_text("B1"))["Report"],
        )

    def test_a_plan_the_work_outgrew_prints_and_never_refuses(self):
        """Drift is reported to the person holding both, not blocked."""

        frame = self.frame("--shape", "draft > judge")
        self.journal(frame, "unjudged: the user reads the draft", "wave-1")

        closed = self.call(
            "frame-close", self.RUN, frame["id"], "--status", "limited",
        )["frame_close"]

        self.assertEqual("limited", closed["status"])
        self.assertEqual("draft > judge", closed["shape"])
        self.assertIn(
            "shape draft > judge; frame closed limited over 0 do and 0 judge",
            _sections(self.ticket_text("B1"))["Report"],
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
        self.assertEqual(SHAPE, closed["shape"])
        self.assertIn(
            f"shape {SHAPE}; frame closed complete over 2 do and 1 judge "
            "children; judged by B1.3.",
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

    def test_the_shape_record_alone_is_not_a_wave_anybody_wrote(self):
        """`resume`'s journal column answers "has this driver written a wave
        down". `frame-open` files the shape before any wave exists, so a
        column that counted it would read `yes` for every open frame."""

        frame = self.frame()
        self._hold_open_at("B1", "2026-08-31T11:30:00Z")
        self.assertIn("no ", self._resume("--now", FIXED_NOW).splitlines()[1])

        self.journal(frame, "wave 1: one draft out", "wave-1")

        self.assertIn("yes ", self._resume("--now", FIXED_NOW).splitlines()[1])

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


class SavedWorkflowShapeTest(unittest.TestCase):
    """Every shipped workflow's root `frame-open` states a plan.

    These bodies are the worked examples a driver copies, so one that
    opened a planless root would be a refusal in the wild the first time
    anybody ran it -- and worse, a reader would learn the wrong command.
    A saved workflow names `--workflow`: its body *is* the plan.
    """

    def setUp(self):
        self.bodies = {
            path.parent.name: path.read_text(encoding="utf-8")
            for path in sorted(
                (ROOT / "example-workflows").glob("*/SKILL.md")
            )
        }
        self.assertTrue(self.bodies)

    def test_every_root_frame_open_line_states_a_plan(self):
        self.assertEqual([], sorted(_planless(self.bodies)))

    def test_dropping_the_flag_from_a_copy_fails_the_check(self):
        """The can-fail direction (rules/verification.md §8) on copies built
        beside the tree: one workflow's text at a time, mutated in memory."""

        for name, body in self.bodies.items():
            if name not in _planless({name: body}, flag=""):
                continue  # this body opens no root frame to strip
            with self.subTest(workflow=name):
                stripped = dict(self.bodies)
                stripped[name] = body.replace(" --workflow " + name, "")
                self.assertIn(name, _planless(stripped))

    def test_the_scaffolded_workflow_states_a_plan(self):
        """`orchflows new workflow` writes a body the door would accept.

        The skeleton is the first `frame-open` line most authors ever run,
        and it is generated, not shipped -- so the glob above cannot see
        it. Same check, same set: a scaffold that regressed to a planless
        line would hand every new author a command this tree refuses.
        """

        name = "scaffolded-flow"
        body = dict(orchflows_scaffold.files_for("workflow", name))["SKILL.md"]
        self.assertEqual(set(), _planless({name: body}))
        self.assertEqual(
            {name},
            _planless({name: body.replace(" --workflow " + name, "")}),
        )


class ShapeGrammarOwnerTest(unittest.TestCase):
    """One grammar, stated as prose and echoed as notation.

    `docs/vocabulary.md`'s shape-line paragraph defines it; `SHAPE_GRAMMAR`
    is the line a refusal prints, and it points at that owner rather than
    redefining it. Nothing but agreement holds the two together, so this
    reads the anchors each must carry -- the parser's own tokens and its
    reserved names, backticked, never a sentence -- and a construct one
    side grows or loses alone lands here.
    """

    def test_the_prose_and_the_printed_notation_carry_the_same_anchors(self):
        self.assertEqual([], _adrift(_shape_line_prose(), SHAPE_GRAMMAR))

    def test_a_construct_dropped_from_either_side_is_caught(self):
        """The can-fail direction, on copies: neither file is touched."""

        prose = _shape_line_prose()
        self.assertEqual(
            ["notation:*"],
            _adrift(prose, SHAPE_GRAMMAR.replace("`a[*]`", "`a`")),
        )
        self.assertEqual(
            ["prose:judge"],
            _adrift(prose.replace("`judge` are", "judge are"), SHAPE_GRAMMAR),
        )


def _planless(bodies: dict, flag: str = "--workflow") -> set:
    """The workflows whose root `frame-open` line names no plan.

    A `--parent` frame is a wave of its caller's shape and owes none, so it
    is not one of these; `flag=""` asks the weaker question "does this body
    open a root frame at all", which is what the can-fail case needs to
    know before it strips anything.
    """

    named = set()
    for name, body in bodies.items():
        for line in body.splitlines():
            if "tickets.py frame-open" not in line or "--parent" in line:
                continue
            if not flag or (flag not in line and "--shape" not in line):
                named.add(name)
    return named


def _shape_line_prose() -> str:
    """The vocabulary's shape-line paragraph: the grammar's owner.

    Sliced on the bolded term and the next term's bullet, so the anchor
    the check leans on is a heading-grade one; a paragraph that moved
    reddens here rather than quietly matching nothing.
    """

    text = (ROOT / "docs" / "vocabulary.md").read_text(encoding="utf-8")
    start = text.index("A **shape line**")
    return text[start:text.index("\n- **", start)]


def _adrift(prose: str, notation: str) -> list:
    """`['<side>:<anchor>']` for every anchor a side fails to carry.

    Tokens are looked for inside the backticked spans, names as whole
    spans: `> judge` carries the token but is not the reserved name.
    """

    missing = []
    for side, text in (("prose", prose), ("notation", notation)):
        spans = re.findall(r"`([^`]+)`", " ".join(text.split()))
        joined = " ".join(spans)
        missing.extend(f"{side}:{t}" for t in GRAMMAR_TOKENS if t not in joined)
        missing.extend(f"{side}:{n}" for n in RESERVED_NAMES if n not in spans)
    return sorted(missing)


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
