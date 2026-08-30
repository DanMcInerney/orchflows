"""Every mutating ticket write is refused, then locked, then surfaced.

The holes were one shape: a command graded half of its identity, skipped
the lock when that grade failed, then ran its handler anyway; a stamp
compared one read and wrote from another; a standalone projection read
outside the lock it committed inside; any ticket of a run could take the
run's one terminal-timing slot. Each case fires on the mechanism, not on a
message: a rewrite keeps the message and drops the mechanism.
"""

from __future__ import annotations

import ast
import inspect
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent

from scripts import tickets as tickets_mod  # noqa: E402
from scripts import tickets_attempts  # noqa: E402
from scripts import tickets_dispatch_facade  # noqa: E402
from scripts import tickets_dispatch_packet  # noqa: E402
from scripts import tickets_dispatch_gate  # noqa: E402
from scripts import tickets_join  # noqa: E402
from scripts import tickets_result  # noqa: E402
from scripts import tickets_lifecycle  # noqa: E402
from scripts import tickets_store  # noqa: E402
from scripts import workspace_git  # noqa: E402
from tests.test_tickets_cases.common import (  # noqa: E402
    TICKETS_PY, make_repo, run_cmd, sink_root, use_sink,
)

SCRIPTS = ROOT / "scripts"
WORKSPACE_PY = SCRIPTS / "workspace.py"
UTC_STAMP = "%Y-%m-%dT%H:%M:%SZ"
# Long enough that a child which was going to run has run. What is graded is
# that it has NOT finished, and a held lock is held until its holder lets go.
WAIT = 2.0


def ticket_at(run_dir: Path, tid: str, *, executor="orch-execute", deps="[]",
              status="ready", extra=()) -> Path:
    """One fixture work item, written straight into the sink's run."""

    run_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "---", f"id: {tid}", f"run: {run_dir.name}", f"status: {status}",
        f"executor: {executor}", f"depends_on: {deps}",
    ]
    lines += [f"{key}: {value}" for key, value in extra]
    lines += ["---", "", "## Objective", "", "Fixture work item.", ""]
    path = run_dir / f"{tid}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def sink_listing() -> list:
    """Every path under the sink, so a refusal that wrote can be named."""

    root = sink_root()
    return sorted(str(path.relative_to(root)) for path in root.rglob("*"))


class TestMalformedIdentityRefusesBeforeTheLock(unittest.TestCase):
    """Both halves of a ticket's identity are graded before anything opens.

    `tickets.py check ".." X --stage X.check` used to skip the lock *because*
    the run id was malformed, then run the unlocked handler with it. The grade
    is now the primitive's first act, and it raises rather than returning.
    """

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        tmp = Path(self.temporary.name)
        self.repo = tmp / "repo"
        self.repo.mkdir()
        make_repo(self.repo, {"T1": ("ready", "[]")})

    def tearDown(self):
        self.temporary.cleanup()

    def commands(self, run: str, tid: str):
        """Every mutating route the public facade dispatches on a ticket.

        `claim` is not among them: the dispatch-v1 cutover left its plumbing
        reachable only as an import, and it has since been deleted with the
        rest of the unreachable claim path.
        """

        return (
            ("check", run, tid, "--stage", f"{tid}.check"),
            ("set-status", run, tid, "complete"),
            ("join-noop-repair", run, tid, "--by", "gate-join"),
            ("dispatch-packet", run, tid, "--dispatch-id", "D1",
             "--reply-to", "root"),
            ("gate", run, tid),
            ("checker-stage", run, tid),
        )

    def assert_refused_without_writing(self, argv, expected: str):
        before = sink_listing()
        payload = run_cmd(self.repo, *argv)
        self.assertIn("error", payload, argv)
        self.assertIn(expected, payload["error"], argv)
        self.assertEqual(before, sink_listing(), argv)
        self.assertFalse(
            (sink_root() / "locks").exists(),
            f"{argv[0]} opened a run lock for a malformed identity",
        )

    def test_a_malformed_run_id_refuses_every_mutating_command(self):
        for run, expected in ((
            "..", "unsafe run id '..'"), (".", "unsafe run id '.'"),
            ("a/b", "unsafe run id 'a/b'"), ("", "run id is empty"),
        ):
            for argv in self.commands(run, "T1"):
                with self.subTest(run=run, command=argv[0]):
                    self.assert_refused_without_writing(argv, expected)

    def test_a_malformed_ticket_id_refuses_every_mutating_command(self):
        """The half that was never graded at all: the run id was checked and
        the ticket id went straight into the path the handler opened."""

        for tid, expected in (
            ("../x", "unsafe ticket id '../x'"), ("", "ticket id is empty"),
        ):
            for argv in self.commands("testrun", tid):
                with self.subTest(ticket=tid, command=argv[0]):
                    self.assert_refused_without_writing(argv, expected)

    def test_a_malformed_run_id_refuses_the_run_only_command(self):
        """`run-state` names no ticket, so the run half is all it has to
        grade -- and it graded it, then ran the handler anyway."""

        for run, expected in (
            ("..", "unsafe run id '..'"), ("a/b", "unsafe run id 'a/b'"),
        ):
            with self.subTest(run=run):
                self.assert_refused_without_writing(
                    ("run-state", run, "--note", "x"), expected
                )


class TestTheOneLockedWritePrimitive(unittest.TestCase):
    """One primitive holds refusal, lock, and path; nothing holds two of them."""

    SUBJECTS = (
        tickets_lifecycle._cmd_check,
        tickets_lifecycle._cmd_set_status,
        tickets_lifecycle._cmd_join_noop_repair,
        tickets_dispatch_gate._cmd_gate,
        tickets_dispatch_gate._cmd_checker_stage,
    )
    RUN_ONLY_SUBJECTS = (tickets_result._cmd_run_state,)

    def test_every_mutating_command_enters_through_the_primitive(self):
        for subject in self.SUBJECTS:
            with self.subTest(subject.__name__):
                self.assertIn("locked_ticket_write(", inspect.getsource(subject))

    def test_no_command_reaches_its_handler_outside_that_primitive(self):
        """The skip-lock-on-bad-id shape, named structurally: the handler is
        reached once, and only after the primitive has opened."""

        for subject in self.SUBJECTS:
            with self.subTest(subject.__name__):
                source = inspect.getsource(subject)
                self.assertEqual(1, source.count("_under_run_lock("))
                self.assertLess(
                    source.index("locked_ticket_write("),
                    source.index("_under_run_lock("),
                )

    def test_the_run_only_command_enters_through_its_own_primitive(self):
        """`run-state` grades one segment because it names one. The sibling
        primitive exists so that half cannot be graded inline and skipped."""

        for subject in self.RUN_ONLY_SUBJECTS:
            with self.subTest(subject.__name__):
                source = inspect.getsource(subject)
                self.assertIn("locked_run_write(", source)
                self.assertNotIn("_segment_error(", source)

    def test_the_primitive_refuses_by_raising_not_by_returning(self):
        with self.assertRaises(tickets_store.TicketWriteRefused) as refused:
            with tickets_store.locked_ticket_write("..", "T1"):
                self.fail("a malformed identity opened the lock")
        self.assertIn("unsafe run id", refused.exception.payload["error"])

    def test_the_primitive_yields_the_canonical_ticket_path(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            use_sink(tmp)
            with tickets_store.locked_ticket_write("testrun", "T1") as path:
                self.assertEqual(
                    sink_root() / "tickets" / "testrun" / "T1.md", path
                )


class TestWorkspaceStampsUnderTheRunLock(unittest.TestCase):
    """`workspace.py start` stamps a ticket other commands are moving. Its
    read and its write are now one critical section, and the dispatch facade
    -- already holding that lock, running this as its child -- says so."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        tmp = Path(self.temporary.name)
        use_sink(tmp)
        self.ticket = ticket_at(
            sink_root() / "tickets" / "testrun", "T1", status="claimed",
            extra=(("pack", "orch-research-pack"),),
        )
        self.here = tmp

    def tearDown(self):
        self.temporary.cleanup()

    def start(self, *extra):
        return [sys.executable, str(WORKSPACE_PY), "start", "testrun", "T1", *extra]

    def test_the_stamp_derives_from_the_text_read_under_the_lock(self):
        source = inspect.getsource(workspace_git._stamped)
        self.assertIn("updated = current_text", source)
        self.assertNotIn("updated = prior_text", source)

    def test_start_waits_for_a_run_lock_another_writer_holds(self):
        with tickets_store._run_lock("testrun"):
            child = subprocess.Popen(
                self.start(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", cwd=str(self.here),
            )
            time.sleep(WAIT)
            early = child.poll()
        out, err = child.communicate(timeout=60)
        self.assertIsNone(early, f"start stamped inside another writer's lock: {out or err}")
        self.assertEqual(0, child.returncode, out or err)
        self.assertIn("workspace_path", self.ticket.read_text(encoding="utf-8"))

    def test_lock_held_stamps_inside_the_callers_critical_section(self):
        with tickets_store._run_lock("testrun"):
            done = subprocess.run(
                self.start(workspace_git.LOCK_HELD), capture_output=True,
                text=True, encoding="utf-8", errors="replace",
                cwd=str(self.here), timeout=60,
            )
        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertIn("workspace_path", self.ticket.read_text(encoding="utf-8"))

    def test_the_dispatch_facade_tells_its_child_the_lock_is_held(self):
        """Two processes, one flag: without this the facade's own lock and the
        child's request for it are a deadlock, each waiting on the other."""

        source = inspect.getsource(tickets_dispatch_facade._workspace_establish)
        self.assertIn(workspace_git.LOCK_HELD, source)

    def test_the_facade_really_starts_a_workspace_inside_its_own_run_lock(self):
        """The composition, not its source: every other facade case stubs
        this call out, so the one arrangement that can deadlock -- parent
        holding the lock, child asking for it -- was never run. In a thread,
        so a deadlock is a failed join rather than a hung suite."""

        outcome = {}

        def start():
            outcome["response"] = tickets_dispatch_facade._workspace_establish(
                "testrun", "T1", str(self.here)
            )

        worker = threading.Thread(target=start, daemon=True)
        with tickets_store._run_lock("testrun"):
            worker.start()
            worker.join(timeout=60)
            finished = not worker.is_alive()
        worker.join(timeout=60)
        self.assertTrue(finished, "start waited for its own caller's lock")
        self.assertNotIn("error", outcome["response"])
        self.assertIn("workspace_path", self.ticket.read_text(encoding="utf-8"))


class TestStandaloneDispatchPacketIsLocked(unittest.TestCase):
    """`dispatch-packet` read the attempt, the review state and the seal
    unlocked, then committed under a lock it opened at the end."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        tmp = Path(self.temporary.name)
        use_sink(tmp)
        self.here = tmp
        ticket_at(sink_root() / "tickets" / "testrun", "T1", status="claimed")

    def tearDown(self):
        self.temporary.cleanup()

    def test_the_whole_projection_waits_for_the_run_lock(self):
        command = [
            sys.executable, str(TICKETS_PY), "dispatch-packet", "testrun", "T1",
            "--dispatch-id", "D1", "--reply-to", "root",
        ]
        with tickets_store._run_lock("testrun"):
            child = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace", cwd=str(self.here),
            )
            time.sleep(WAIT)
            early = child.poll()
        out, err = child.communicate(timeout=60)
        self.assertIsNone(early, f"dispatch-packet read outside the lock: {out or err}")
        self.assertIn("error", json.loads(out))

    def test_the_commit_is_told_the_lock_is_already_held(self):
        source = inspect.getsource(tickets_dispatch_packet._packet_transaction)
        self.assertIn("_lock_held=True", source)


class TestOneOwnerForTheEndedAttemptRule(unittest.TestCase):
    """`_commit_record` refuses an unseen record on an ended attempt before
    any mutation runs, so the copy of that rule inside `dispatch-retire` could
    never fire -- and could only ever disagree with the one that decides."""

    def test_retirement_carries_no_second_ended_attempt_guard(self):
        self.assertNotIn(
            'attempt.get("state") != "live"',
            inspect.getsource(tickets_attempts._cmd_dispatch_retire),
        )
        self.assertIn(
            'attempt.get("state") != "live"',
            inspect.getsource(tickets_attempts._commit_record),
        )


class TestOnlyTheRunsOwnRootClosesIt(unittest.TestCase):
    """The run identity's terminal timing is written once and never rewritten,
    so whichever ticket reached it first froze the run's elapsed time there.
    The predicate is the worklog's own goal reader: one owner."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        use_sink(Path(self.temporary.name))
        self.run_dir = sink_root() / "tickets" / "testrun"

    def tearDown(self):
        self.temporary.cleanup()

    def test_a_cut_runs_root_closes_it_and_its_members_do_not(self):
        ticket_at(self.run_dir, "R", executor="orch-decompose")
        ticket_at(self.run_dir, "R.01", deps="[R]")
        self.assertTrue(tickets_join._closes_the_run("testrun", "R"))
        self.assertFalse(tickets_join._closes_the_run("testrun", "R.01"))

    def test_the_root_decides_whichever_member_joins_first(self):
        for label, member in (("root joins last", "complete"),
                              ("root joins first", "pending")):
            with self.subTest(label):
                ticket_at(self.run_dir, "R", executor="orch-decompose")
                ticket_at(self.run_dir, "R.01", deps="[R]", status=member)
                self.assertTrue(tickets_join._closes_the_run("testrun", "R"))
                self.assertFalse(tickets_join._closes_the_run("testrun", "R.01"))

    def test_an_ad_hoc_runs_single_ticket_is_its_own_root(self):
        ticket_at(self.run_dir, "T1")
        self.assertTrue(tickets_join._closes_the_run("testrun", "T1"))

    def test_a_loop_runs_single_ticket_is_its_own_root(self):
        ticket_at(self.run_dir, "L", executor="orch-execute")
        self.assertTrue(tickets_join._closes_the_run("testrun", "L"))

    def test_an_unreadable_or_absent_run_closes_nothing(self):
        self.assertFalse(tickets_join._closes_the_run("testrun", "T1"))

    def test_the_join_asks_before_it_stamps(self):
        self.assertIn(
            "_closes_the_run(run, ticket_id)",
            inspect.getsource(tickets_join._cmd_dispatch_join),
        )


class TestSplitTerminalWriteIsSurfaced(unittest.TestCase):
    """Ticket first, identity second, and a failed identity write rolls the
    ticket back. When the rollback fails too the pair is genuinely split, and
    neither error may be swallowed: both are named, with the one command that
    lands the pair from either half's state."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        tmp = Path(self.temporary.name)
        self.repo = tmp / "repo"
        self.repo.mkdir()
        make_repo(self.repo, {"R": ("pending", "[]")})
        self.identity = sink_root() / "runs" / "testrun" / "run.json"
        self.identity.parent.mkdir(parents=True, exist_ok=True)
        self.identity.write_text(json.dumps({
            "run": "testrun",
            "sink_convention": 2,
            "opened_at": datetime.now(timezone.utc).strftime(UTC_STAMP),
            "project": {
                "root": str(self.repo.resolve()), "origin": None,
                "name": self.repo.name,
            },
            "workspaces": [],
        }) + "\n", encoding="utf-8")
        self.ticket = sink_root() / "tickets" / "testrun" / "R.md"

    def tearDown(self):
        self.temporary.cleanup()

    def status(self) -> str:
        return tickets_mod._parse_frontmatter(
            self.ticket.read_text(encoding="utf-8")
        )["status"]

    def test_a_failed_identity_write_alone_still_rolls_the_ticket_back(self):
        with mock.patch.object(
            tickets_mod, "_write_identity", side_effect=OSError("timing failed")
        ):
            payload = run_cmd(self.repo, "set-status", "testrun", "R", "complete")
        self.assertIn("timing failed", payload["error"])
        self.assertNotIn("could not be rolled back", payload["error"])
        self.assertEqual("pending", self.status())

    def test_a_failed_rollback_names_both_errors_and_the_retry_that_replays(self):
        real = tickets_mod._write_text_atomically
        calls = {"count": 0}

        def refuse_the_rollback(path, text):
            calls["count"] += 1
            if calls["count"] == 1:
                return real(path, text)
            raise OSError("rollback refused")

        with mock.patch.object(
            tickets_mod, "_write_text_atomically", refuse_the_rollback
        ), mock.patch.object(
            tickets_mod, "_write_identity", side_effect=OSError("timing failed")
        ):
            payload = run_cmd(self.repo, "set-status", "testrun", "R", "complete")

        self.assertIn("timing failed", payload["error"])
        self.assertIn("rollback refused", payload["error"])
        self.assertIn("tickets.py set-status testrun R complete", payload["error"])
        # the split the caller was told about: the ticket moved, the timing
        # did not, and nothing pretended otherwise
        self.assertEqual("complete", self.status())
        self.assertNotIn("terminal_at", json.loads(self.identity.read_text(encoding="utf-8")))

        retried = run_cmd(self.repo, "set-status", "testrun", "R", "complete")
        self.assertNotIn("error", retried)
        identity = json.loads(self.identity.read_text(encoding="utf-8"))
        self.assertEqual("complete", identity["terminal_status"])
        self.assertEqual("R", identity["terminal_ticket_id"])


class TestNoHelperImportsItsFacade(unittest.TestCase):
    """A facade exists so its callers need not know its parts, and a part
    that imports it back closes the cycle it was drawn to open --
    `tickets_store` paid that import per atomic write. `tickets.py` and
    `workspace.py` are the facades; their prefixes name the helpers."""

    FACADES = frozenset({"tickets.py", "workspace.py"})

    def helpers(self):
        found = sorted(SCRIPTS.glob("tickets_*.py")) + sorted(SCRIPTS.glob("workspace*.py"))
        return [path for path in found if path.name not in self.FACADES]

    @staticmethod
    def imported_names(node) -> set:
        if isinstance(node, ast.Import):
            return {alias.name.split(".")[-1] for alias in node.names}
        if isinstance(node, ast.ImportFrom):
            if node.module:
                return {node.module.split(".")[-1]}
            return {alias.name for alias in node.names}
        return set()

    def test_no_family_helper_imports_the_tickets_facade(self):
        offenders = []
        for path in self.helpers():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if "tickets" in self.imported_names(node):
                    offenders.append(f"{path.name}:{node.lineno}")
        self.assertEqual([], offenders)

    def test_no_family_helper_reaches_the_facade_by_name_either(self):
        """`__import__` and `importlib` are the same import with the AST
        looking the other way."""

        for path in self.helpers():
            source = path.read_text(encoding="utf-8")
            with self.subTest(path.name):
                self.assertNotIn('__import__("tickets")', source)
                self.assertNotIn("__import__('tickets')", source)
                self.assertNotIn('import_module("tickets")', source)

    def test_the_atomic_write_no_longer_syncs_the_facades_seams(self):
        source = inspect.getsource(tickets_store._waiting_out_windows)
        self.assertNotIn("_sync_seams", source)

    def test_the_facade_installs_its_seam_sync_on_the_dispatcher(self):
        """The sync survives, handed down instead of fetched up: the facade
        assigns it, and a dispatcher loaded without a facade has none."""

        dispatcher = tickets_mod._tickets_dispatch_module
        self.assertIs(tickets_mod._sync_seams, dispatcher._sync_seams)


if __name__ == "__main__":
    unittest.main()
