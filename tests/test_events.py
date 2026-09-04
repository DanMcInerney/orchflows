"""M2: the sink event stream.

One line per terminal machine event, appended to
``<sink>/events/<yyyy-mm>.jsonl`` by `tickets_frame.py`'s open and close and
by `tickets_land.py`'s land -- through `tickets_result._append_event`, the
one shared emitter, which reuses `_append_one_line`'s locked-append idiom
and `tickets_project.recorded_project`'s identity plumbing rather than a
second copy of either. Every line opens with the provenance head
`friction.py` entries carry, and a write that cannot reach the sink costs
the event, never the transition that produced it.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tests._candidate_checkout import git_checkout, record_established_workspace
from tests import _retired_commands as retired_commands
from scripts import state_root
from scripts import tickets
from scripts import tickets_result
from scripts.tickets_format import parse_canonical_json

from tests._repo_root import ROOT
INTERPRETER = sys.executable
PROVENANCE_KEYS = {"sink_convention", "ts", "project", "run", "ticket", "host", "session"}


def _command(code: int) -> str:
    return f'"{INTERPRETER}" -c "raise SystemExit({code})"'


def _done(form: str, value: str) -> str:
    return json.dumps({"form": form, "value": value}, sort_keys=True)


class _EventSinkTestCase(unittest.TestCase):
    """A temp sink, and the events stream read back off it."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
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
        self.addCleanup(self.environment.stop)

    def events_path(self) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m")
        return Path(self.temporary.name) / "events" / f"{stamp}.jsonl"

    def events(self) -> list:
        path = self.events_path()
        if not path.is_file():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]

    def assertProvenance(self, entry: dict, *, run: str, ticket: str):
        self.assertEqual(set(), PROVENANCE_KEYS - set(entry), entry)
        self.assertEqual(tickets.SINK_CONVENTION, entry["sink_convention"])
        self.assertRegex(entry["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertIsInstance(entry["project"], dict)
        self.assertEqual(run, entry["run"])
        self.assertEqual(ticket, entry["ticket"])
        self.assertIn(entry["host"], {"claude-code", "codex", "unknown"})


class _FrameEventTestCase(_EventSinkTestCase):
    """The frame world: a goal file and the two callable verbs a close reads."""

    RUN = "eventrun"

    def setUp(self):
        super().setUp()
        self.goal_file = Path(self.temporary.name) / "goal.md"
        self.goal_file.write_text(
            "Deliver the migration wave.\nand say what it cost.\n", encoding="utf-8",
        )

    def call(self, *arguments, expect_error=False) -> dict:
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

    def frame(self, *arguments) -> dict:
        # A root frame states its wave plan at open; a case about `--workflow`
        # supplies its own, so only the shapeless ones get the default.
        if not {"--shape", "--workflow"} & set(arguments):
            arguments = ("--shape", "outline > [do, do] > judge", *arguments)
        opened = self.call(
            "frame-open", self.RUN, "--goal-file", str(self.goal_file), *arguments,
        )
        return opened["frame_open"]

    def callable(self, verb, frame_id, *arguments) -> str:
        answer = self.call(
            verb, self.RUN, "--standard", "orch-content",
            "--goal-file", str(self.goal_file), "--parent", frame_id, *arguments,
        )
        return answer[verb]["id"]

    def journal(self, frame: dict, text: str, record_id: str):
        return self.call(
            "result", self.RUN, frame["id"],
            "--assignment-seal", frame["assignment_seal"],
            "--dispatch-id", frame["dispatch_id"],
            "--record-id", record_id, "--by", frame["journal_by"], "--text", text,
        )


class FrameOpenEventTest(_FrameEventTestCase):
    """`workflow` and `goal_head`, the two fields open adds to the head."""

    def test_frame_open_names_its_workflow_and_goal_head(self):
        frame = self.frame("--workflow", "self-improve")

        events = self.events()
        self.assertEqual(1, len(events))
        entry = events[0]
        self.assertEqual("frame-open", entry["event"])
        self.assertEqual("self-improve", entry["workflow"])
        self.assertEqual("Deliver the migration wave.", entry["goal_head"])
        self.assertProvenance(entry, run=self.RUN, ticket=frame["id"])

    def test_frame_open_without_workflow_names_none(self):
        frame = self.frame()

        entry = self.events()[0]
        self.assertIsNone(entry["workflow"])
        self.assertProvenance(entry, run=self.RUN, ticket=frame["id"])

    def test_frame_open_carries_the_shape_it_opened_under(self):
        """The wave plan is on the event, not only in the ticket: a harvest
        reading one run's stream can say what it set out to do without
        opening the sink's tickets."""

        self.frame("--shape", "outline > [do, do] > judge")

        self.assertEqual(
            "outline > [do, do] > judge", self.events()[0]["shape"],
        )

    def test_a_workflow_frames_shape_names_the_body_that_is_its_plan(self):
        self.frame("--workflow", "self-improve")

        self.assertEqual("workflow:self-improve", self.events()[0]["shape"])

    def test_a_long_goal_first_line_is_truncated_to_200_chars(self):
        self.goal_file.write_text("x" * 260 + "\nsecond line\n", encoding="utf-8")

        self.frame()

        entry = self.events()[0]
        self.assertEqual("x" * 200, entry["goal_head"])


class FrameCloseEventTest(_FrameEventTestCase):
    """`children`, `judged`, `unjudged_reason`, `done_exit` and `status`."""

    def _frame_close_entry(self) -> dict:
        closes = [event for event in self.events() if event["event"] == "frame-close"]
        self.assertEqual(1, len(closes), self.events())
        return closes[0]

    def test_a_judged_close_names_its_children_and_no_reason(self):
        frame = self.frame()
        do_children = [self.callable("do", frame["id"]) for _ in range(2)]
        self.callable(
            "judge", frame["id"], "--artifacts", "doc:draft.md@sha256:" + "e" * 64,
        )

        self.call("frame-close", self.RUN, frame["id"], "--status", "complete")

        entry = self._frame_close_entry()
        self.assertEqual("frame-close", entry["event"])
        self.assertEqual(len(do_children) + 1, entry["children"])
        self.assertTrue(entry["judged"])
        self.assertIsNone(entry["unjudged_reason"])
        self.assertIsNone(entry["done_exit"])
        self.assertEqual("complete", entry["status"])
        self.assertProvenance(entry, run=self.RUN, ticket=frame["id"])

    def test_an_unjudged_close_names_the_journals_reason(self):
        frame = self.frame()
        for _ in range(2):
            self.callable("do", frame["id"])
        self.journal(
            frame, "unjudged: both drafts go straight to the user", "wave-1",
        )

        self.call("frame-close", self.RUN, frame["id"], "--status", "limited")

        entry = self._frame_close_entry()
        self.assertEqual(2, entry["children"])
        self.assertFalse(entry["judged"])
        self.assertEqual(
            "both drafts go straight to the user", entry["unjudged_reason"],
        )
        self.assertEqual("limited", entry["status"])

    def test_a_refused_close_writes_no_event(self):
        frame = self.frame()
        for _ in range(2):
            self.callable("do", frame["id"])

        self.call(
            "frame-close", self.RUN, frame["id"], "--status", "complete",
            expect_error=True,
        )

        self.assertEqual(
            [], [event for event in self.events() if event["event"] == "frame-close"],
        )


class EventFailureIsSwallowedTest(_FrameEventTestCase):
    """The reliability bar: a broken append costs the event, not the close."""

    def test_a_broken_append_does_not_fail_the_frame_close(self):
        frame = self.frame()
        stderr = io.StringIO()

        # Patched at the facade, not at `tickets_result` directly: `_dispatch`
        # runs `_sync_seams()` on every call, which re-injects
        # `tickets._append_one_line` into `tickets_result` and would stomp a
        # patch made at the lower module before this call ever reached it.
        with mock.patch(
            "scripts.tickets._append_one_line", side_effect=OSError("disk full"),
        ), mock.patch("sys.stderr", stderr):
            closed = self.call(
                "frame-close", self.RUN, frame["id"], "--status", "complete",
            )

        self.assertEqual("complete", closed["frame_close"]["status"])
        self.assertIn("events: not logged", stderr.getvalue())
        self.assertEqual(
            ["frame-open"], [event["event"] for event in self.events()],
        )


class _LandEventTestCase(_EventSinkTestCase):
    """The land world: a sealed, dispatched, closed item ready for one land."""

    RUN = "run"

    def setUp(self):
        super().setUp()
        self.candidate = git_checkout(Path(self.temporary.name) / "candidate")

    def run_command(self, *arguments):
        result = retired_commands.run(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def ticket_path(self, ticket_id="T") -> Path:
        return Path(self.temporary.name) / "tickets" / self.RUN / f"{ticket_id}.md"

    def stand_up(self, done=None):
        self.run_command(
            "new", self.RUN, "T", "--executor", "orch-do",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--standard", "orch-code", "--isolation", "none",
        )
        if done is not None:
            path = self.ticket_path()
            path.write_text(
                tickets._set_frontmatter_field(
                    path.read_text(encoding="utf-8"), "done", done,
                ),
                encoding="utf-8",
            )
        self.run_command("stamp-generation", self.RUN, "T")
        validated = self.run_command("draft-validate", self.RUN, "T")
        self.run_command(
            "seal", self.RUN, "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        self.run_command("ready", "--run", self.RUN)
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
                "dispatch", self.RUN, "T", "--by", "worker", "--dispatch-id", "D1",
                "--lease-expires-at", lease, "--workspace", str(self.candidate),
            )
        self.seal = parse_canonical_json(tickets._parse_frontmatter(
            self.ticket_path().read_text(encoding="utf-8")
        )["dispatch_v1"])["attempts"][0]["assignment_seal"]
        self.run_command(
            "dispatch-outcome", self.RUN, "T", "--note", "delivered and verified",
        )

    def land(self, *extra):
        return retired_commands.run([
            "land", self.RUN, "T", "--assignment-seal", self.seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome",
            "--by", "root-join", *extra,
        ])

    def _land_entries(self) -> list:
        return [event for event in self.events() if event["event"] == "land"]


class LandEventTest(_LandEventTestCase):
    """`status`, `done_exit`, `attempts` and `elapsed_s`, with and without
    a done predicate."""

    def test_a_completed_predicate_names_its_exit_and_dispatch_cost(self):
        self.stand_up(_done("command", _command(0)))

        landed = self.land()

        self.assertEqual("complete", landed["land"]["status"])
        entries = self._land_entries()
        self.assertEqual(1, len(entries))
        entry = entries[0]
        self.assertEqual("land", entry["event"])
        self.assertEqual("complete", entry["status"])
        self.assertEqual(0, entry["done_exit"])
        self.assertEqual(1, entry["attempts"])
        self.assertIsInstance(entry["elapsed_s"], float)
        self.assertGreaterEqual(entry["elapsed_s"], 0.0)
        self.assertProvenance(entry, run=self.RUN, ticket="T")

    def test_a_driver_graded_land_carries_no_done_exit(self):
        self.stand_up()

        landed = self.land("--status", "limited")

        self.assertEqual("limited", landed["land"]["status"])
        entry = self._land_entries()[0]
        self.assertEqual("limited", entry["status"])
        self.assertIsNone(entry["done_exit"])
        self.assertEqual(1, entry["attempts"])


class LandEventFailureIsSwallowedTest(_LandEventTestCase):
    """The same reliability bar, at the command that never backgrounds a gate."""

    def test_a_broken_append_does_not_fail_the_land(self):
        self.stand_up(_done("command", _command(0)))
        stderr = io.StringIO()

        with mock.patch(
            "scripts.tickets._append_one_line", side_effect=OSError("disk full"),
        ), mock.patch("sys.stderr", stderr):
            landed = self.land()

        self.assertEqual("complete", landed["land"]["status"])
        self.assertIn("events: not logged", stderr.getvalue())
        self.assertEqual([], self.events())


class AppendEventUsesTheLockedIdiomTest(_EventSinkTestCase):
    """`_append_event` writes through `_append_one_line`, never a second open.

    Graded by running it rather than by reading its source. The shared
    locked writer is replaced by a recorder that writes nothing, so an
    emitter that opened the events file itself would leave a line on disk
    and no recording behind it -- and the three readings below name that
    exact swap, in both directions.
    """

    def test_append_event_calls_the_shared_locked_writer(self):
        recorded = []
        stderr = io.StringIO()
        with mock.patch.object(
            tickets_result, "_append_one_line",
            side_effect=lambda path, block: recorded.append((Path(path), block)),
        ), mock.patch("sys.stderr", stderr):
            tickets_result._append_event("r-1", "T-1", "probe", {"status": "complete"})

        self.assertEqual("", stderr.getvalue())
        self.assertEqual(1, len(recorded), recorded)
        path, block = recorded[0]
        self.assertEqual(self.events_path(), path)
        self.assertEqual("probe", json.loads(block)["event"])
        self.assertEqual([], self.events())


if __name__ == "__main__":
    unittest.main()
