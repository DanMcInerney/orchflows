"""Ticket script: pending promotion, status enum, and adversarial coverage
(claim races, malformed input, repo-boundary errors)."""

import ast
import inspect
import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402

TICKETS_PY = ROOT / "scripts" / "tickets.py"
STATE_ROOT_PY = ROOT / "scripts" / "state_root.py"
WORKSPACE_PY = ROOT / "scripts" / "workspace.py"
STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"

TICKET = """---
id: {tid}
run: testrun
status: {status}
executor: orch-tdd
depends_on: {deps}
write_scope: scratch/{tid}.txt
bound: 30m
---

## Objective

Test ticket.
"""


def use_sink(tmp: Path) -> Path:
    """Point ``ORCHFLOWS_STATE_HOME`` at a sink under this test's tempdir.

    Sets the variable for the rest of the process rather than restoring
    it: every fixture below calls this before writing, and
    ``tests/__init__.py`` holds the floor at a temporary directory
    regardless, so the worst a stale value can do is fail a test, never
    reach the real sink. ``run_full`` passes no ``env``, so each child
    inherits whatever is in force when it is launched.
    """

    # resolved: a macOS tempdir is reached through a /var symlink, and a
    # payload that prints the sink path must match the path a test opens
    sink = (tmp / "state-sink").resolve()
    os.environ[STATE_HOME_ENV_VAR] = str(sink)
    return sink


def sink_root() -> Path:
    """Wherever ``use_sink`` last pointed. Never the real sink."""

    return Path(os.environ[STATE_HOME_ENV_VAR])


def make_tickets(run_dir: Path, tickets: dict) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    for tid, (status, deps) in tickets.items():
        (run_dir / f"{tid}.md").write_text(
            TICKET.format(tid=tid, status=status, deps=deps), encoding="utf-8"
        )
    return run_dir


def make_repo(tmp: Path, tickets: dict, *, sink: Path = None) -> Path:
    """A repository at ``tmp``, and its run of tickets in the sink.

    Tickets are user-scope state, so they land outside the checkout. Pass
    ``sink`` when the caller has already placed one — a worktree fixture
    puts it beside both trees rather than inside either.
    """

    (tmp / ".git").mkdir()
    if sink is None:
        sink = use_sink(tmp)
    return make_tickets(sink / "tickets" / "testrun", tickets)


def run_full(cwd: Path, *args):
    return subprocess.run(
        [sys.executable, str(TICKETS_PY), *args],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd),
    )


def run_cmd(cwd: Path, *args):
    return json.loads(run_full(cwd, *args).stdout)


class TestPendingPromotion(unittest.TestCase):
    def test_pending_with_complete_deps_is_promoted_and_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {
                "T1": ("complete", "[]"),
                "T2": ("pending", "[T1]"),
            })
            payload = run_cmd(tmp, "ready", "--run", "testrun")
            ids = [t["id"] for t in payload["ready"]]
            self.assertEqual(["T2"], ids)
            self.assertEqual("ready", payload["ready"][0]["status"])
            self.assertIn("status: ready", (run_dir / "T2.md").read_text(encoding="utf-8"))

    def test_pending_with_incomplete_deps_stays_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {
                "T1": ("ready", "[]"),
                "T2": ("pending", "[T1]"),
            })
            payload = run_cmd(tmp, "ready", "--run", "testrun")
            ids = sorted(t["id"] for t in payload["ready"])
            self.assertEqual(["T1"], ids)
            self.assertIn("status: pending", (run_dir / "T2.md").read_text(encoding="utf-8"))

    def test_set_status_accepts_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            payload = run_cmd(tmp, "set-status", "testrun", "T1", "pending")
            self.assertEqual("pending", payload["set_status"]["status"])
            self.assertIn("status: pending", (run_dir / "T1.md").read_text(encoding="utf-8"))


class TestClaim(unittest.TestCase):
    def test_claim_happy_path_transitions_ready_to_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual("agent-a", payload["claimed"]["claimed_by"])
            self.assertEqual("T1", payload["claimed"]["id"])
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertIn("status: claimed", text)
            self.assertIn("claimed_by: agent-a", text)
            self.assertRegex(text, r"claimed_at: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

    def test_claim_on_fresh_claim_is_rejected_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            first = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertIn("claimed", first)
            second = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertIn("error", second)

    def test_stale_claim_is_reclaimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            ticket_path = run_dir / "T1.md"
            first = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertIn("claimed", first)
            # backdate the claim well past the ticket's 30m bound so it reads stale
            text = ticket_path.read_text(encoding="utf-8")
            text = tickets_mod._set_frontmatter_field(text, "claimed_at", "2020-01-01T00:00:00Z")
            ticket_path.write_text(text, encoding="utf-8")
            second = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertEqual("agent-b", second["claimed"]["claimed_by"])
            self.assertIn("claimed_by: agent-b", ticket_path.read_text(encoding="utf-8"))

    def test_two_writer_claim_race_yields_exactly_one_winner(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            ticket_path = run_dir / "T1.md"
            # Both writers "read" the identical pre-claim snapshot before either
            # writes, modelling two processes racing to claim the same ticket.
            prior_text = ticket_path.read_text(encoding="utf-8")
            now = datetime.now(timezone.utc)

            result_a = tickets_mod._do_claim(ticket_path, prior_text, "writer-a", now)
            result_b = tickets_mod._do_claim(ticket_path, prior_text, "writer-b", now)

            outcomes = [result_a, result_b]
            winners = [r for r in outcomes if "claimed" in r]
            losers = [r for r in outcomes if "error" in r]
            self.assertEqual(1, len(winners), outcomes)
            self.assertEqual(1, len(losers), outcomes)

            final_text = ticket_path.read_text(encoding="utf-8")
            winner_name = winners[0]["claimed"]["claimed_by"]
            self.assertIn(f"claimed_by: {winner_name}", final_text)
            loser_name = "writer-b" if winner_name == "writer-a" else "writer-a"
            self.assertNotIn(f"claimed_by: {loser_name}", final_text)


class TestInvalidStatus(unittest.TestCase):
    def test_set_status_rejects_invalid_status_as_error_json_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            result = run_full(tmp, "set-status", "testrun", "T1", "bogus-status")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)
            self.assertIn("status: ready", (run_dir / "T1.md").read_text(encoding="utf-8"))


class TestMalformedFrontmatter(unittest.TestCase):
    def test_list_handles_ticket_with_no_frontmatter_delimiters(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            run_dir = use_sink(tmp) / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            (run_dir / "T1.md").write_text(
                "# Not a ticket\n\nNo frontmatter delimiters at all.\n", encoding="utf-8"
            )
            result = run_full(tmp, "list", "--run", "testrun")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual(1, len(payload["tickets"]))
            self.assertIsNone(payload["tickets"][0]["status"])

    def test_set_status_on_unterminated_frontmatter_returns_error_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            run_dir = use_sink(tmp) / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            (run_dir / "T1.md").write_text("---\nid: T1\nstatus: ready\n", encoding="utf-8")
            result = run_full(tmp, "set-status", "testrun", "T1", "complete")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)

    def test_claim_on_unterminated_frontmatter_returns_error_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            run_dir = use_sink(tmp) / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            (run_dir / "T1.md").write_text("---\nid: T1\nstatus: ready\n", encoding="utf-8")
            result = run_full(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)


class TestRunFilter(unittest.TestCase):
    def test_run_filter_scopes_list_to_named_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"A1": ("ready", "[]")})
            other_dir = sink_root() / "tickets" / "otherrun"
            other_dir.mkdir(parents=True)
            (other_dir / "B1.md").write_text(
                "---\nid: B1\nrun: otherrun\nstatus: ready\ndepends_on: []\n"
                "write_scope: scratch/B1.txt\nbound: 30m\n---\n\n## Objective\n\nTest ticket.\n",
                encoding="utf-8",
            )

            payload_testrun = run_cmd(tmp, "list", "--run", "testrun")
            self.assertEqual(["A1"], [t["id"] for t in payload_testrun["tickets"]])

            payload_otherrun = run_cmd(tmp, "list", "--run", "otherrun")
            self.assertEqual(["B1"], [t["id"] for t in payload_otherrun["tickets"]])

            payload_all = run_cmd(tmp, "list")
            self.assertEqual(["A1", "B1"], sorted(t["id"] for t in payload_all["tickets"]))

    def test_run_filter_on_unknown_run_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"A1": ("ready", "[]")})
            payload = run_cmd(tmp, "list", "--run", "nonexistent-run")
            self.assertEqual([], payload["tickets"])


class TestEngineExecutorIsRejected(unittest.TestCase):
    """A ticket naming an engine as its executor is a call cycle.

    rules/composition.md §3: an engine dispatches a ticket's executor, so
    an engine cannot be one. Seventeen such tickets were cut in a real run
    and nothing caught them; these prove the reader now does.
    """

    def make(self, tmp: Path, executor: str) -> Path:
        run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
        path = run_dir / "T1.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "executor: orch-tdd", f"executor: {executor}"
            ),
            encoding="utf-8",
        )
        return run_dir

    def test_engine_list_matches_the_library(self):
        engines = {
            path.name
            for path in (ROOT / "skills" / "engines").iterdir()
            if path.is_dir()
        }
        self.assertEqual(engines, set(tickets_mod.ENGINE_EXECUTORS))

    def test_every_engine_is_refused(self):
        for engine in sorted(tickets_mod.ENGINE_EXECUTORS):
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                self.make(tmp, engine)
                summary = run_cmd(tmp, "list")["tickets"][0]
                self.assertIn("error", summary, engine)
                self.assertIn("is an engine", summary["error"])

    def test_an_engine_executor_is_never_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, "orch-task")
            self.assertEqual([], run_cmd(tmp, "ready")["ready"])

    def test_an_engine_executor_cannot_be_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = self.make(tmp, "orch-task")
            payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertIn("is an engine", payload.get("error", ""))
            self.assertNotIn(
                "claimed_by", (run_dir / "T1.md").read_text(encoding="utf-8")
            )

    def test_backticks_and_spacing_do_not_evade_the_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, "`orch-frontier`")
            self.assertIn("error", run_cmd(tmp, "list")["tickets"][0])

    def test_a_lawful_executor_still_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, "orch-verify")
            summary = run_cmd(tmp, "list")["tickets"][0]
            self.assertNotIn("error", summary)
            self.assertEqual(["T1"], [t["id"] for t in run_cmd(tmp, "ready")["ready"]])


class TestOutsideARepoTheSinkStillResolves(unittest.TestCase):
    """The sink is user-scope, so being outside a checkout is no longer an
    error: the tickets are found anyway, and only a genuinely absent one is
    reported missing."""

    def test_list_outside_a_repo_reads_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # deliberately no .git anywhere under this tempdir
            make_tickets(use_sink(tmp) / "tickets" / "testrun", {"T1": ("ready", "[]")})
            bare = tmp / "no-repo-here"
            bare.mkdir()
            result = run_full(bare, "list", "--run", "testrun")
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertEqual(["T1"], [t["id"] for t in payload["tickets"]])

    def test_claim_outside_a_repo_claims_the_ticket_in_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_tickets(
                use_sink(tmp) / "tickets" / "testrun", {"T1": ("ready", "[]")}
            )
            bare = tmp / "no-repo-here"
            bare.mkdir()
            result = run_full(bare, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual(0, result.returncode)
            self.assertNotIn("error", json.loads(result.stdout))
            self.assertIn(
                "status: claimed", (run_dir / "T1.md").read_text(encoding="utf-8")
            )

    def test_an_absent_ticket_is_still_reported_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            bare = tmp / "no-repo-here"
            bare.mkdir()
            payload = json.loads(
                run_full(bare, "claim", "testrun", "T1", "--by", "agent-a").stdout
            )
            self.assertIn("ticket not found", payload["error"])

    def test_a_sink_that_cannot_be_resolved_is_the_one_remaining_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            with mock.patch.object(
                tickets_mod.state_root, "tickets_root", side_effect=RuntimeError("no home")
            ):
                payload = tickets_mod._cmd_list([])
            self.assertEqual({"error": tickets_mod.NO_SINK_ERROR}, payload)


FULL_TICKET = """---
id: T1
run: testrun
status: ready
executor: orch-tdd
pack: orch-code-pack
depends_on: []
write_scope: scratch/t1.txt
bound: 30m
---

## Objective

Add `double(n)`.

## Fixed inputs

None.

## Completion test

1. `python -m unittest` exits 0. Oracle: that command. oracle_class: deterministic.

## Return fields

status, changed_artifacts, verification.
"""


class TestPacket(unittest.TestCase):
    """`packet` is the by-reference dispatch of contracts/delegation.md: the
    dispatcher gets a path and a refusal check, never the ticket body."""

    def make(self, tmp: Path, body: str = FULL_TICKET) -> Path:
        (tmp / ".git").mkdir()
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        path = run_dir / "T1.md"
        path.write_text(body, encoding="utf-8")
        return path

    def test_complete_ticket_yields_an_absolute_path_and_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ticket_path = self.make(tmp)
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            self.assertEqual(str(ticket_path.resolve()), packet["path"])
            self.assertTrue(Path(packet["path"]).is_absolute())
            self.assertEqual("orch-tdd", packet["executor"])
            self.assertEqual("orch-code-pack", packet["pack"])
            # contracts/work-item.md: absent `independence` reads `checker`.
            self.assertEqual("checker", packet["independence"])
            self.assertIn(packet["path"], packet["prompt"])
            self.assertIn("orch-tdd", packet["prompt"])
            self.assertIn("reply_to: main", packet["prompt"])

    def test_workspace_rides_the_prompt_only_when_supplied(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            bare = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            self.assertIsNone(bare["workspace"])
            self.assertNotIn("Workspace:", bare["prompt"])
            with_ws = run_cmd(
                tmp, "packet", "testrun", "T1", "--reply-to", "main", "--workspace", "/wt/a"
            )["packet"]
            self.assertEqual("/wt/a", with_ws["workspace"])
            self.assertIn("Workspace: /wt/a", with_ws["prompt"])

    def test_missing_body_section_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            trimmed = FULL_TICKET.split("## Return fields")[0]
            self.make(tmp, trimmed)
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("return_contract (## Return fields)", payload["error"])
            self.assertNotIn("packet", payload)

    def test_missing_frontmatter_part_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace("bound: 30m\n", ""))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("bounds (bound)", payload["error"])

    def test_reply_to_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            payload = run_cmd(tmp, "packet", "testrun", "T1")
            self.assertIn("reply_to (--reply-to)", payload["error"])

    def test_criterion_without_oracle_class_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace(" oracle_class: deterministic.", ""))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("oracle_class", payload["error"])

    def test_engine_executor_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace("executor: orch-tdd", "executor: orch-task"))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("is an engine", payload["error"])

    def test_unknown_ticket_and_an_empty_sink_are_errors_not_crashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            self.assertIn("ticket not found", run_cmd(tmp, "packet", "testrun", "T9", "--reply-to", "main")["error"])
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            result = run_full(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertEqual(0, result.returncode)
            self.assertIn("ticket not found", json.loads(result.stdout)["error"])


def make_worktree(tmp: Path, tickets: dict):
    """A main checkout plus a linked worktree whose ``.git`` is a pointer file.

    The shape `make_repo` cannot produce: `.git` as a file holding a
    `gitdir:` line, which is what an executor's isolated workspace has and
    what the result channel must dereference to the main checkout.
    """

    sink = use_sink(tmp)
    main = tmp / "main"
    main.mkdir()
    run_dir = make_repo(main, tickets, sink=sink)
    (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
    worktree = tmp / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text(
        f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
    )
    return main, worktree, run_dir


class TestResultWorktreeCrossing(unittest.TestCase):
    """contracts/work-item.md: one run's tickets have one path, identical
    from every executor workspace. The executor files its result there from
    inside its own worktree, reading its body from that worktree."""

    def test_result_from_a_worktree_lands_in_the_main_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            body = worktree / "result-body.md"
            body.write_text("Landed at the main root.\n", encoding="utf-8")
            payload = run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "Result", "--file", str(body),
            )
            self.assertEqual("Result", payload["result"]["section"])
            self.assertEqual(
                str((run_dir / "T1.md").resolve()), payload["result"]["path"]
            )
            self.assertIn(
                "## Result\n\nLanded at the main root.\n",
                (run_dir / "T1.md").read_text(encoding="utf-8"),
            )
            # nothing was created in the worktree: the ticket tree is the
            # main checkout's alone
            self.assertFalse((worktree / ".orch").exists())

    def test_text_form_writes_the_same_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "verification", "--text", "1. PASS.",
            )
            self.assertEqual("Verification", payload["result"]["section"])
            self.assertIn(
                "## Verification\n\n1. PASS.\n",
                (run_dir / "T1.md").read_text(encoding="utf-8"),
            )


def frontmatter_of(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("---\n", 2)[1]


class TestResultClosedSet(unittest.TestCase):
    """contracts/work-item.md:56-57 names exactly what an executor writes."""

    def test_the_writable_set_is_the_contracts_five(self):
        self.assertEqual(
            ("Result", "Verification", "Feedback", "Risks", "Handoff"),
            tickets_mod.EXECUTOR_SECTIONS,
        )

    def test_every_reserved_section_round_trips(self):
        for name in tickets_mod.EXECUTOR_SECTIONS:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
                payload = run_cmd(
                    worktree, "result", "testrun", "T1",
                    "--section", name, "--text", f"body for {name}",
                )
                self.assertEqual(name, payload["result"]["section"], name)
                text = (run_dir / "T1.md").read_text(encoding="utf-8")
                self.assertEqual(f"body for {name}", tickets_mod._sections(text)[name])

    def test_a_cut_time_section_is_refused_and_the_set_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            payload = run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "Objective", "--text", "hijacked",
            )
            self.assertIn("Objective", payload["error"])
            for name in tickets_mod.EXECUTOR_SECTIONS:
                self.assertIn(name, payload["error"])
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))


class TestResultBodySource(unittest.TestCase):
    def test_both_file_and_text_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            body = worktree / "body.md"
            body.write_text("from a file\n", encoding="utf-8")
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            result = run_full(
                worktree, "result", "testrun", "T1", "--section", "Result",
                "--file", str(body), "--text", "from a string",
            )
            self.assertEqual(0, result.returncode)
            self.assertIn("error", json.loads(result.stdout))
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_neither_file_nor_text_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            result = run_full(worktree, "result", "testrun", "T1", "--section", "Result")
            self.assertEqual(0, result.returncode)
            self.assertIn("error", json.loads(result.stdout))
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_an_unreadable_body_file_is_an_error_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            result = run_full(
                worktree, "result", "testrun", "T1", "--section", "Result",
                "--file", str(worktree / "absent.md"),
            )
            self.assertEqual(0, result.returncode)
            self.assertIn("error", json.loads(result.stdout))


class TestResultRefusesTerminalStatus(unittest.TestCase):
    """Criterion 4's refusal half: terminal status is the join's alone
    (contracts/work-item.md:31-33), so `result` writes no frontmatter."""

    def test_a_status_flag_is_refused_and_names_set_status_and_the_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            result = run_full(
                worktree, "result", "testrun", "T1", "--section", "Result",
                "--text", "done", "--status", "complete",
            )
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("--status", payload["error"])
            self.assertIn("set-status", payload["error"])
            self.assertIn("orch-integrate", payload["error"])
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_any_unrecognized_flag_is_refused_the_same_way(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(
                worktree, "result", "testrun", "T1", "--section", "Result",
                "--text", "done", "--claimed-by", "someone",
            )
            self.assertIn("--claimed-by", payload["error"])
            self.assertIn("set-status", payload["error"])

    def test_frontmatter_is_byte_unchanged_after_writing_every_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            before = frontmatter_of(ticket)
            for name in tickets_mod.EXECUTOR_SECTIONS:
                run_cmd(
                    worktree, "result", "testrun", "T1",
                    "--section", name, "--text", f"body for {name}",
                )
            self.assertEqual(before, frontmatter_of(ticket))
            self.assertIn("status: claimed", ticket.read_text(encoding="utf-8"))

    def test_a_heading_shaped_frontmatter_line_is_not_a_section_boundary(self):
        # A wrapped frontmatter value can begin a line with "## ". Treating it
        # as a heading would put the writer inside frontmatter the join owns.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8").replace(
                    "bound: 30m\n", "bound: 30m\nnote:\n  - suspend through\n## Risks\n"
                ),
                encoding="utf-8",
            )
            before = frontmatter_of(ticket)
            run_cmd(
                worktree, "result", "testrun", "T1", "--section", "Risks", "--text", "[]",
            )
            self.assertEqual(before, frontmatter_of(ticket))
            self.assertEqual("[]", tickets_mod._sections(
                ticket.read_text(encoding="utf-8").split("---\n", 2)[2]
            )["Risks"])

    def test_a_fenced_heading_is_not_a_section_boundary(self):
        # Every deliverable in this repository is markdown with "## "
        # headings, and executors quote them at length. A heading inside a
        # fence is quoted content: ending the replaced span there deletes
        # the opening fence, orphans the closing one, and promotes the
        # quotation to a second heading that `_sections` then resolves
        # last-writer-wins -- silently reshaping sections the write never
        # named. Both fence characters, and an info string on the opener.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8")
                + "\n## Result\n\nOLD BODY\n\n"
                + "```markdown\n## Objective\nquoted heading\n```\n\n"
                + "tail prose\n\n"
                + "## Feedback\n\n~~~\n## Handoff\nfenced handoff\n~~~\n\n"
                + "## Risks\n\n[]\n",
                encoding="utf-8",
            )
            run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "Result", "--text", "REPLACED",
            )
            text = ticket.read_text(encoding="utf-8")
            sections = tickets_mod._sections(text.split("---\n", 2)[2])
            # The quotation stayed quoted: no second Objective, no orphan.
            self.assertEqual("Test ticket.", sections["Objective"])
            self.assertNotIn("quoted heading", text)
            self.assertNotIn("```", text)
            # The replaced span ran to the next real heading, and stopped.
            self.assertEqual("REPLACED", sections["Result"])
            self.assertIn("fenced handoff", sections["Feedback"])
            self.assertNotIn("Handoff", sections)
            self.assertEqual("[]", sections["Risks"])


class TestResultScriptContract(unittest.TestCase):
    def test_success_and_failure_both_exit_zero_with_one_json_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ok = run_full(
                worktree, "result", "testrun", "T1", "--section", "Result", "--text", "ok",
            )
            self.assertEqual(0, ok.returncode)
            self.assertIn("result", json.loads(ok.stdout))
            self.assertEqual(1, len(ok.stdout.strip().splitlines()))
            bad = run_full(
                worktree, "result", "testrun", "T9", "--section", "Result", "--text", "ok",
            )
            self.assertEqual(0, bad.returncode)
            self.assertIn("ticket not found", json.loads(bad.stdout)["error"])
            self.assertEqual(1, len(bad.stdout.strip().splitlines()))

    def test_result_outside_a_repo_still_reaches_the_sink(self):
        """A result is user-scope state, so the cwd being outside a checkout
        no longer decides anything: the ticket is found and written."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_tickets(
                use_sink(tmp) / "tickets" / "testrun", {"T1": ("claimed", "[]")}
            )
            bare = tmp / "no-repo-here"
            bare.mkdir()
            result = run_full(
                bare, "result", "testrun", "T1", "--section", "Result", "--text", "x"
            )
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertNotIn("error", payload)
            self.assertIn(
                "## Result\n\nx\n", (run_dir / "T1.md").read_text(encoding="utf-8")
            )


def headings_of(text: str) -> list:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


class TestResultSectionOrder(unittest.TestCase):
    """A created section takes its place in the order contracts/work-item.md
    states. The sparse `TICKET` fixture is the one that can tell the
    difference: on a fuller ticket, blind appending is right by accident."""

    def test_a_created_section_lands_in_contract_order_not_append_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Feedback", "--text", "[]")
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Result", "--text", "did it")
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertEqual(["Objective", "Result", "Feedback"], headings_of(text))
            self.assertEqual("did it", tickets_mod._sections(text)["Result"])
            self.assertEqual("[]", tickets_mod._sections(text)["Feedback"])

    def test_handoff_lands_last_however_the_sections_arrive(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for name in ("Handoff", "Risks", "Verification"):
                run_cmd(worktree, "result", "testrun", "T1", "--section", name, "--text", name)
            self.assertEqual(
                ["Objective", "Verification", "Risks", "Handoff"],
                headings_of((run_dir / "T1.md").read_text(encoding="utf-8")),
            )


class TestResultAppend(unittest.TestCase):
    """contracts/work-item.md:91-93: a rules/verification.md §10 checker
    appends its own pass and never rewrites the executor's."""

    def test_append_keeps_the_prior_body_and_adds_after_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                    "--text", "executor pass")
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Feedback", "--text", "[]")
            before = ticket.read_text(encoding="utf-8")
            payload = run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                              "--text", "checker pass", "--append")
            self.assertEqual("append", payload["result"]["mode"])
            text = ticket.read_text(encoding="utf-8")
            self.assertEqual("executor pass\n\nchecker pass", tickets_mod._sections(text)["Result"])
            self.assertLess(text.index("executor pass"), text.index("checker pass"))
            # every other section is byte-unchanged
            self.assertEqual(headings_of(before), headings_of(text))
            for name in ("Objective", "Feedback"):
                self.assertEqual(
                    tickets_mod._sections(before)[name], tickets_mod._sections(text)[name]
                )
            self.assertEqual(frontmatter_of(ticket), frontmatter_of(ticket))

    def test_append_to_an_absent_section_creates_it_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Risks",
                    "--text", "[]", "--append")
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertEqual(["Objective", "Risks"], headings_of(text))
            self.assertEqual("[]", tickets_mod._sections(text)["Risks"])

    def test_default_replaces_rather_than_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Result", "--text", "first")
            payload = run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                              "--text", "second")
            self.assertEqual("replace", payload["result"]["mode"])
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertEqual("second", tickets_mod._sections(text)["Result"])
            self.assertNotIn("first", text)


# --- the run-state channel ---------------------------------------------------


def worklog_of(run: str = "testrun") -> Path:
    return sink_root() / "runs" / run / "worklog.md"


def run_dir_of(run: str = "testrun") -> Path:
    return sink_root() / "runs" / run


def run_state_lines(prompt: str) -> list:
    return [line for line in prompt.splitlines() if " run-state " in line]


def git_available() -> bool:
    try:
        return subprocess.run(
            ["git", "--version"], capture_output=True, text=True
        ).returncode == 0
    except OSError:
        return False


def make_real_worktree(tmp: Path):
    """A main checkout and a linked worktree that `git worktree add` made.

    `make_worktree` hand-writes the pointer file; this one lets git write it,
    so the resolver is proved against the shape git actually produces.
    """

    env = dict(
        os.environ,
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
    )

    def git(*args):
        completed = subprocess.run(
            ["git", "-c", "commit.gpgsign=false", *args],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", cwd=str(main), env=env,
        )
        if completed.returncode != 0:
            raise unittest.SkipTest(f"git {args[0]} failed: {completed.stderr.strip()}")

    use_sink(tmp)
    main = tmp / "main"
    main.mkdir()
    git("init", "--quiet")
    (main / "README.md").write_text("baseline\n", encoding="utf-8")
    git("add", "README.md")
    git("commit", "--quiet", "-m", "init")
    worktree = tmp / "wt"
    git("worktree", "add", "--quiet", "-b", "wt-branch", str(worktree))
    return main, worktree


class TestRunStateWorklog(unittest.TestCase):
    """rules/visibility.md §6: run state reaches the one user-scope sink
    from any workspace in any repository, or it fails loudly."""

    def test_a_note_from_a_worktree_appends_in_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(worktree, "run-state", "testrun", "--note", "slice one landed")
            self.assertEqual("note", payload["run_state"]["mode"])
            self.assertEqual(
                str(worklog_of().resolve()), payload["run_state"]["path"]
            )
            self.assertEqual(
                "slice one landed\n", worklog_of().read_text(encoding="utf-8")
            )
            # the run tree is the sink's alone
            self.assertFalse((worktree / ".orch").exists())
            self.assertFalse((main / ".orch").exists())

    def test_a_prior_line_and_an_outside_writer_both_survive(self):
        """Append mode, never read-modify-write: scripts/friction.py opens the
        shared log with ``"a"`` and an explicit ``newline`` for exactly this."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--note", "first from the channel")
            with open(worklog_of(), "a", encoding="utf-8", newline="\n") as handle:
                handle.write("second from another worktree\n")
            run_cmd(worktree, "run-state", "testrun", "--note", "third from the channel")
            self.assertEqual(
                [
                    "first from the channel",
                    "second from another worktree",
                    "third from the channel",
                ],
                worklog_of().read_text(encoding="utf-8").splitlines(),
            )

    def test_concurrent_notes_all_land_whole(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            notes = [f"writer-{i} " + "x" * 2000 for i in range(8)]
            with ThreadPoolExecutor(max_workers=8) as pool:
                list(
                    pool.map(
                        lambda note: run_cmd(worktree, "run-state", "testrun", "--note", note),
                        notes,
                    )
                )
            self.assertEqual(
                sorted(notes),
                sorted(worklog_of().read_text(encoding="utf-8").splitlines()),
            )


class TestRunStateArtifact(unittest.TestCase):
    """Anything not append-only is partitioned by run id, so two runs in two
    workspaces never write one file."""

    def test_a_named_artifact_lands_under_the_run_partition(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(
                worktree, "run-state", "testrun", "--artifact", "evidence.md",
                "--text", "the bytes at the main root\n",
            )
            artifact = run_dir_of() / "evidence.md"
            self.assertEqual("artifact", payload["run_state"]["mode"])
            self.assertEqual(str(artifact.resolve()), payload["run_state"]["path"])
            self.assertEqual(
                "the bytes at the main root\n", artifact.read_text(encoding="utf-8")
            )
            self.assertFalse((worktree / ".orch").exists())

    def test_the_body_can_come_from_a_file_inside_the_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            body = worktree / "evidence-body.md"
            body.write_text("read inside, written outside\n", encoding="utf-8")
            run_cmd(
                worktree, "run-state", "testrun", "--artifact", "checks.md",
                "--file", str(body),
            )
            self.assertEqual(
                "read inside, written outside\n",
                (run_dir_of() / "checks.md").read_text(encoding="utf-8"),
            )


class TestRunStateRootResolution(unittest.TestCase):
    def test_the_root_comes_from_the_one_resolver_with_no_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            calls = []
            original = tickets_mod.state_root.runs_root

            def spy():
                calls.append(True)
                return original()

            cwd = os.getcwd()
            tickets_mod.state_root.runs_root = spy
            try:
                os.chdir(worktree)
                payload = tickets_mod._dispatch(
                    ["run-state", "testrun", "--note", "resolved in process"]
                )
            finally:
                os.chdir(cwd)
                tickets_mod.state_root.runs_root = original
            self.assertIn("run_state", payload)
            self.assertEqual(1, len(calls))
            self.assertEqual(
                "resolved in process\n", worklog_of().read_text(encoding="utf-8")
            )
            # nothing can shell out to git that never imports a way to:
            # the whole script's import set, not a word match on its prose
            imported = set()
            for node in ast.walk(ast.parse(TICKETS_PY.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    imported.add((node.module or "").split(".")[0])
            self.assertNotIn("subprocess", imported)
            self.assertEqual(
                {"__future__", "datetime", "json", "pathlib", "re", "scripts",
                 "state_root", "sys"},
                imported,
            )

    @unittest.skipUnless(git_available(), "git is not on PATH")
    def test_inside_a_real_git_worktree_the_bytes_land_in_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree = make_real_worktree(Path(tmp))
            payload = run_cmd(worktree, "run-state", "testrun", "--note", "from a real worktree")
            self.assertEqual(
                str(worklog_of().resolve()), payload["run_state"]["path"]
            )
            self.assertEqual(
                "from a real worktree\n", worklog_of().read_text(encoding="utf-8")
            )
            self.assertFalse((worktree / ".orch").exists())
            self.assertFalse((main / ".orch").exists())


class TestRunStateRefusesUnsafeNames(unittest.TestCase):
    """A run id or artifact name is one path segment. Anything that could
    climb out of the sink's `runs/` is refused by name, never sanitized
    silently."""

    def test_an_unsafe_run_id_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for bad in ("../escape", "a/b", "a\\b", ".."):
                payload = run_cmd(worktree, "run-state", bad, "--note", "x")
                self.assertIn(bad, payload.get("error", ""), bad)
                self.assertNotIn("run_state", payload)
            self.assertFalse((sink_root() / "runs").exists())

    def test_an_unsafe_artifact_name_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for bad in ("../escape.md", "a/b.md", "a\\b.md", ".."):
                payload = run_cmd(
                    worktree, "run-state", "testrun", "--artifact", bad, "--text", "x"
                )
                self.assertIn(bad, payload.get("error", ""), bad)
                self.assertNotIn("run_state", payload)
            self.assertFalse((sink_root() / "runs").exists())


class TestPacketCarriesTheRunStateCommand(unittest.TestCase):
    """Every dispatched child gets the channel in its own packet: no sibling
    reads another ticket to learn how to write run state."""

    def make(self, tmp: Path) -> Path:
        (tmp / ".git").mkdir()
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        path = run_dir / "T1.md"
        path.write_text(FULL_TICKET, encoding="utf-8")
        return path

    def test_every_packet_carries_it_workspace_or_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            bare = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            with_ws = run_cmd(
                tmp, "packet", "testrun", "T1", "--reply-to", "main", "--workspace", "/wt/a"
            )["packet"]
            for packet in (bare, with_ws):
                lines = run_state_lines(packet["prompt"])
                self.assertEqual(2, len(lines), packet["prompt"])
                for line in lines:
                    # `run` is interpolated from the ticket, not left a placeholder
                    self.assertIn(" run-state testrun ", line)

    def test_the_line_is_absolute_one_token_per_argument_and_shell_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            note_line, artifact_line = run_state_lines(packet["prompt"])
            for line in (note_line, artifact_line):
                for forbidden in ("|", ">", "<", "&&", "$("):
                    self.assertNotIn(forbidden, line, line)
                tokens = line.split()
                self.assertEqual(sys.executable, tokens[0])
                self.assertTrue(Path(tokens[0]).is_absolute(), tokens[0])
                self.assertEqual(str(TICKETS_PY.resolve()), tokens[1])
                self.assertTrue(Path(tokens[1]).is_absolute(), tokens[1])
                self.assertEqual("tickets.py", Path(tokens[1]).name)
                self.assertEqual(["run-state", "testrun"], tokens[2:4])
            self.assertEqual(["--note", "TEXT"], note_line.split()[4:])
            self.assertEqual(
                ["--artifact", "NAME", "--text", "TEXT"], artifact_line.split()[4:]
            )

    def test_the_interpreter_and_script_path_are_derived_not_literal(self):
        """Run a copy of the script from somewhere else entirely: a literal
        `python3 scripts/tickets.py` would emit the same line from both."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            elsewhere = tmp / "elsewhere"
            elsewhere.mkdir()
            copy = elsewhere / "tickets.py"
            copy.write_text(TICKETS_PY.read_text(encoding="utf-8"), encoding="utf-8")
            # the installed layout: the resolver sits flat beside it, and the
            # copy reaches it by the second arm of its two-arm import
            (elsewhere / "state_root.py").write_text(
                STATE_ROOT_PY.read_text(encoding="utf-8"), encoding="utf-8"
            )
            completed = subprocess.run(
                [sys.executable, str(copy), "packet", "testrun", "T1", "--reply-to", "main"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", cwd=str(tmp),
            )
            packet = json.loads(completed.stdout)["packet"]
            lines = run_state_lines(packet["prompt"])
            self.assertEqual(2, len(lines))
            for line in lines:
                self.assertEqual(str(copy.resolve()), line.split()[1])
                self.assertNotIn(str(TICKETS_PY.resolve()), line)


class TestRelativeGitdirPointer(unittest.TestCase):
    """`make_worktree` writes an absolute pointer; git writes a relative one
    whenever the worktree was added with a relative path.

    The bodies moved to `scripts/state_root.py`; these two names survive
    here as re-exports, because `scripts/cutcheck.py` and `scripts/ui.py`
    still import them from this module. What is graded is that the
    re-export is the owner's function and not a second copy of it.
    """

    def test_a_relative_pointer_resolves_against_the_pointer_files_own_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main = tmp / "main"
            (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
            worktree = tmp / "wt"
            worktree.mkdir()
            pointer = worktree / ".git"
            pointer.write_text("gitdir: ../main/.git/worktrees/wt\n", encoding="utf-8")
            self.assertEqual(main.resolve(), tickets_mod._main_checkout_root(pointer))
            self.assertEqual(main.resolve(), tickets_mod._find_repo_root(worktree))

    def test_the_two_names_are_the_resolvers_own_functions(self):
        self.assertIs(
            tickets_mod.state_root.main_checkout_root, tickets_mod._main_checkout_root
        )
        self.assertIs(
            tickets_mod.state_root.find_repo_root, tickets_mod._find_repo_root
        )


FENCE_TICKET_TAIL = (
    "\n## Result\n\nOLD BODY\n\n"
    "```markdown\n## Objective\nquoted heading\n```\n\n"
    "## Feedback\n\n[]\n"
)


def fence_broken(worktree_pair, tail: str) -> Path:
    """Append `tail` to the fixture ticket and hand back its path."""

    _main, _worktree, run_dir = worktree_pair
    ticket = run_dir / "T1.md"
    ticket.write_text(ticket.read_text(encoding="utf-8") + tail, encoding="utf-8")
    return ticket


class TestUnterminatedFenceIsReported(unittest.TestCase):
    """A fence that never closes hides every heading below it from
    `_heading_lines`, so the writer used to conclude the section was absent
    and create a second one -- leaving two `## Result` headings that
    `_sections` resolves to neither, since the fence swallows both. The file
    is corrupt input at that point: the only safe write is none, reported."""

    def test_an_unterminated_fence_in_an_earlier_section_is_reported_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(
                pair,
                "\n## Verification\n\n```text\nRan 1 test\nOK\n\n"  # never closed
                "## Result\n\nOLD BODY\n",
            )
            before = ticket.read_text(encoding="utf-8")
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED",
            )
            self.assertIn("unterminated fence", payload.get("error", ""), payload)
            self.assertNotIn("result", payload)
            after = ticket.read_text(encoding="utf-8")
            self.assertEqual(before, after)
            self.assertEqual(1, after.count("\n## Result"), after)
            self.assertNotIn("REPLACED", after)

    def test_the_refusal_covers_append_a_tilde_fence_and_a_fence_below_the_target(self):
        tails = {
            "tilde opener": "\n## Verification\n\n~~~\nRan 1 test\n\n## Result\n\nOLD\n",
            "opened below the target": "\n## Result\n\nOLD\n\n## Feedback\n\n```\nopen\n",
        }
        for name, tail in tails.items():
            for mode in ([], ["--append"]):
                with self.subTest(tail=name, mode=mode or ["replace"]):
                    with tempfile.TemporaryDirectory() as tmp:
                        pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
                        ticket = fence_broken(pair, tail)
                        before = ticket.read_text(encoding="utf-8")
                        payload = run_cmd(
                            pair[1], "result", "testrun", "T1", "--section", "Result",
                            "--text", "REPLACED", *mode,
                        )
                        self.assertIn("unterminated fence", payload.get("error", ""), payload)
                        self.assertEqual(before, ticket.read_text(encoding="utf-8"))


class TestIndentedFenceIsNotAFence(unittest.TestCase):
    """CommonMark 4.4-4.5: at four columns of indentation a ``` line is
    indented-code content, not a fence. Opening a block there is how a
    ticket that merely quotes an indented snippet became unwritable."""

    def test_a_four_space_indented_fence_is_not_a_fence(self):
        self.assertEqual(
            [0, 5],
            tickets_mod._heading_lines([
                "## Objective",
                "",
                "    ```",
                "    ## quoted inside an indented block",
                "",
                "## Result",
            ]),
        )
        # up to three columns it is still a fence, and so is an unindented one
        self.assertEqual([0], tickets_mod._heading_lines(["## A", "   ```", "## B", "```"]))
        self.assertEqual([0], tickets_mod._heading_lines(["## A", "```", "## B", "```"]))

    def test_a_section_below_an_indented_fence_is_replaced_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(
                pair,
                "\n## Verification\n\n    ```\n    ## quoted\n\n## Result\n\nOLD BODY\n",
            )
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED",
            )
            self.assertIn("result", payload)
            text = ticket.read_text(encoding="utf-8")
            self.assertEqual(1, text.count("\n## Result"), text)
            sections = tickets_mod._sections(text)
            self.assertEqual("REPLACED", sections["Result"])
            self.assertIn("## quoted", sections["Verification"])


class TestFenceRepairHoldsBothDirections(unittest.TestCase):
    """The repair `d8af1c4` made -- a balanced fenced heading is quoted
    content, not a boundary -- and the refusal this item adds are one
    behavior read two ways. Pinning them in one case is what keeps a later
    change from buying either direction with the other."""

    def test_the_repair_holds_in_both_directions(self):
        # balanced: the quotation stays quoted and the span is replaced
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(pair, FENCE_TICKET_TAIL)
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED",
            )
            self.assertIn("result", payload)
            text = ticket.read_text(encoding="utf-8")
            sections = tickets_mod._sections(text)
            self.assertEqual("REPLACED", sections["Result"])
            self.assertEqual("Test ticket.", sections["Objective"])
            self.assertEqual("[]", sections["Feedback"])
            self.assertNotIn("quoted heading", text)

        # the same ticket with the closing fence gone: refused, bytes intact
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(
                pair, FENCE_TICKET_TAIL.replace("quoted heading\n```\n", "quoted heading\n")
            )
            before = ticket.read_text(encoding="utf-8")
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED",
            )
            self.assertIn("unterminated fence", payload.get("error", ""), payload)
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))


ISOLATED_TICKET = FULL_TICKET.replace(
    "write_scope:", "isolation: required\nwrite_scope:"
)
UNISOLATED_TICKET = FULL_TICKET.replace(
    "write_scope:", "isolation: none\nwrite_scope:"
)

GIT_ENV = dict(
    os.environ,
    GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
    GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
)


def git_run(cwd: Path, *args) -> str:
    completed = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd), env=GIT_ENV,
    )
    if completed.returncode != 0:
        raise unittest.SkipTest(f"git {args[0]} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def establishment_lines(prompt: str) -> list:
    """Every emitted establishment line, found the way a child finds it: by
    the tokens themselves, never by position and never by a literal path."""

    found = []
    for line in prompt.splitlines():
        tokens = line.split()
        if (
            len(tokens) > 2
            and Path(tokens[1]).name == "workspace.py"
            and tokens[2] == "start"
        ):
            found.append(line)
    return found


def make_packet_repo(tmp: Path, body: str, run: str = "testrun", tid: str = "T1") -> Path:
    (tmp / ".git").mkdir()
    run_dir = use_sink(tmp) / "tickets" / run
    run_dir.mkdir(parents=True)
    path = run_dir / f"{tid}.md"
    path.write_text(body, encoding="utf-8")
    return path


def make_isolated_fixture(tmp: Path, body: str = None):
    """A real `git init` main checkout, a ticket at its root, and a linked
    `git worktree add` tree on its own branch — the shape the emitted line is
    meant to be run in."""

    use_sink(tmp)
    main = tmp / "main"
    main.mkdir()
    git_run(main, "init", "--quiet")
    (main / "README.md").write_text("baseline\n", encoding="utf-8")
    git_run(main, "add", "README.md")
    git_run(main, "commit", "--quiet", "-m", "init")
    base = git_run(main, "rev-parse", "HEAD")
    run_dir = sink_root() / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    ticket = run_dir / "T1.md"
    ticket.write_text(ISOLATED_TICKET if body is None else body, encoding="utf-8")
    worktree = tmp / "wt"
    git_run(main, "worktree", "add", "--quiet", "-b", "item-branch", str(worktree))
    return main, worktree, ticket, base


def run_argv(argv: list, cwd: Path):
    return subprocess.run(
        argv, capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd),
    )


class TestPacketEmitsTheEstablishmentCommand(unittest.TestCase):
    """contracts/work-item.md's `isolation` is what `packet` conditions on:
    an isolated item is told how to establish its workspace, and a read-only
    lane is told nothing it must not run."""

    def packet_for(self, tmp: Path, body: str, run: str = "testrun", tid: str = "T1"):
        make_packet_repo(tmp, body, run, tid)
        return run_cmd(tmp, "packet", run, tid, "--reply-to", "main")["packet"]

    def test_required_emits_the_line_and_none_or_absent_omit_it(self):
        for body, expected in (
            (ISOLATED_TICKET, 1), (UNISOLATED_TICKET, 0), (FULL_TICKET, 0)
        ):
            with tempfile.TemporaryDirectory() as tmp:
                packet = self.packet_for(Path(tmp), body)
                prompt = packet["prompt"]
                self.assertEqual(expected, len(establishment_lines(prompt)), prompt)
                if not expected:
                    # omitted entirely: not the command, not a mention of it
                    self.assertNotIn("workspace.py", prompt)

    def test_run_and_id_are_interpolated_from_the_ticket(self):
        for run, tid in (("testrun", "T1"), ("otherrun", "Z9")):
            body = ISOLATED_TICKET.replace("id: T1", f"id: {tid}").replace(
                "run: testrun", f"run: {run}"
            )
            with tempfile.TemporaryDirectory() as tmp:
                packet = self.packet_for(Path(tmp), body, run, tid)
                (line,) = establishment_lines(packet["prompt"])
                self.assertEqual([run, tid], line.split()[3:5], line)

    def test_isolation_rides_the_packet_dict_beside_pack_and_independence(self):
        for body, expected in (
            (ISOLATED_TICKET, "required"),
            (UNISOLATED_TICKET, "none"),
            (FULL_TICKET, "none"),  # contracts/work-item.md: absent reads `none`
        ):
            with tempfile.TemporaryDirectory() as tmp:
                packet = self.packet_for(Path(tmp), body)
                self.assertLessEqual(
                    {"pack", "independence", "isolation"}, set(packet), sorted(packet)
                )
                self.assertEqual(expected, packet["isolation"])
                self.assertEqual("orch-code-pack", packet["pack"])

    def test_the_line_is_absolute_one_token_per_argument_and_shell_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.packet_for(Path(tmp), ISOLATED_TICKET)
            (line,) = establishment_lines(packet["prompt"])
            for forbidden in ("|", ">", "<", "&&", "$(", '"', "'"):
                self.assertNotIn(forbidden, line, line)
            tokens = line.split()
            self.assertEqual(5, len(tokens), line)
            self.assertEqual(sys.executable, tokens[0])
            self.assertTrue(Path(tokens[0]).is_absolute(), tokens[0])
            self.assertEqual(str((TICKETS_PY.parent / "workspace.py").resolve()), tokens[1])
            self.assertTrue(Path(tokens[1]).is_absolute(), tokens[1])
            self.assertEqual(["start", "testrun", "T1"], tokens[2:])

    def test_the_interpreter_and_script_path_are_derived_not_literal(self):
        """Run a copy of both scripts from somewhere else entirely: a
        hardcoded interpreter or a literal script path emits the same line
        from either layout, and installed scripts do not sit in `scripts/`."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, ISOLATED_TICKET)
            elsewhere = tmp / "elsewhere"
            elsewhere.mkdir()
            for name in ("state_root.py", "tickets.py", "workspace.py"):
                (elsewhere / name).write_text(
                    (TICKETS_PY.parent / name).read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            completed = run_argv(
                [sys.executable, str(elsewhere / "tickets.py"), "packet",
                 "testrun", "T1", "--reply-to", "main"],
                tmp,
            )
            packet = json.loads(completed.stdout)["packet"]
            (line,) = establishment_lines(packet["prompt"])
            self.assertEqual(str((elsewhere / "workspace.py").resolve()), line.split()[1])
            self.assertNotIn(str(TICKETS_PY.parent.resolve()), line)

    def test_the_emitting_code_holds_no_literal_interpreter_or_script_path(self):
        source = " ".join(inspect.getsource(tickets_mod._cmd_packet).split())
        self.assertNotIn("python3", source)
        self.assertNotIn("scripts/workspace.py", source)
        self.assertIn("sys.executable", source)
        self.assertIn("with_name", source)


@unittest.skipUnless(git_available(), "git is not on PATH")
class TestExecutedPacketSeam(unittest.TestCase):
    """The establishment line is not read, it is run: lifted verbatim out of
    the rendered packet, split to argv, executed against the shipped scripts
    in a real linked worktree, and graded by what it did to the repository."""

    def test_the_emitted_line_runs_from_inside_and_check_grades_the_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree, ticket, base = make_isolated_fixture(Path(tmp))
            packet = run_cmd(worktree, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            (line,) = establishment_lines(packet["prompt"])
            argv = line.split()

            started = run_argv(argv, worktree)
            self.assertEqual(0, started.returncode, started.stderr)
            recorded = json.loads(started.stdout)["start"]
            self.assertEqual(str(main.resolve()), str(Path(recorded["main_root"]).resolve()))
            self.assertTrue(recorded["isolated"])

            front = tickets_mod._parse_frontmatter(ticket.read_text(encoding="utf-8"))
            self.assertEqual("item-branch", front.get("workspace_branch"))
            self.assertEqual(f"{base} clean", front.get("workspace_baseline"))
            # the run tree is the sink's alone
            self.assertFalse((worktree / ".orch").exists())
            self.assertFalse((main / ".orch").exists())

            # `check` reuses every token the packet supplied but the subcommand
            check_argv = [*argv[:2], "check", *argv[3:], "--base", base]
            (worktree / "scratch").mkdir()
            (worktree / "scratch" / "t1.txt").write_text("in scope\n", encoding="utf-8")
            git_run(worktree, "add", "scratch/t1.txt")
            git_run(worktree, "commit", "--quiet", "-m", "in scope")
            clean = run_argv(check_argv, main)
            self.assertEqual(0, clean.returncode, clean.stdout + clean.stderr)
            graded = json.loads(clean.stdout)["check"]
            self.assertEqual("pass", graded["verdict"])
            self.assertEqual("item-branch", graded["workspace_branch"])

            # a deliberate scope breach, committed in the fixture
            (worktree / "secrets.txt").write_text("out of scope\n", encoding="utf-8")
            git_run(worktree, "add", "secrets.txt")
            git_run(worktree, "commit", "--quiet", "-m", "breach")
            breached = run_argv(check_argv, main)
            self.assertEqual(4, breached.returncode, breached.stdout + breached.stderr)
            payload = json.loads(breached.stdout)
            self.assertEqual("scope-breach", payload["verdict"])
            self.assertEqual(["secrets.txt"], payload["breaches"])


@unittest.skipUnless(git_available(), "git is not on PATH")
class TestExecutedRunStateSeam(unittest.TestCase):
    """The same execution against the run-state line every packet carries:
    run from inside the linked tree, the bytes land at the main root."""

    def test_the_emitted_run_state_lines_run_from_inside_the_linked_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree, _, _ = make_isolated_fixture(Path(tmp))
            packet = run_cmd(worktree, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            note_line, artifact_line = run_state_lines(packet["prompt"])

            note_argv = note_line.split()
            self.assertEqual("TEXT", note_argv[-1])  # the one placeholder
            note_argv[-1] = "seam-note-from-the-linked-tree"
            noted = run_argv(note_argv, worktree)
            self.assertEqual(0, noted.returncode, noted.stderr)
            payload = json.loads(noted.stdout)
            # `tickets.py` exits 0 on error: the payload decides, not the code
            self.assertNotIn("error", payload)
            self.assertEqual(str(worklog_of().resolve()), payload["run_state"]["path"])
            self.assertEqual(
                "seam-note-from-the-linked-tree\n",
                worklog_of().read_text(encoding="utf-8"),
            )

            artifact_argv = artifact_line.split()
            self.assertEqual(["NAME", "--text", "TEXT"], artifact_argv[-3:])
            artifact_argv[-3] = "seam-evidence.md"
            artifact_argv[-1] = "seam-bytes-at-the-main-root"
            wrote = run_argv(artifact_argv, worktree)
            self.assertEqual(0, wrote.returncode, wrote.stderr)
            artifact = json.loads(wrote.stdout)
            self.assertNotIn("error", artifact)
            landed = run_dir_of() / "seam-evidence.md"
            self.assertEqual(str(landed.resolve()), artifact["run_state"]["path"])
            self.assertEqual("seam-bytes-at-the-main-root", landed.read_text(encoding="utf-8"))
            self.assertFalse((worktree / ".orch").exists())


if __name__ == "__main__":
    unittest.main()
