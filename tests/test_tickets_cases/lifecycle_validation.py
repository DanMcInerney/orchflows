"""Behavioral ticket regression cases."""

from .lifecycle_lease import *  # noqa: F401,F403

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
            result = run_main(tmp, "list", "--run", "testrun")
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
            result = run_main(tmp, "set-status", "testrun", "T1", "complete")
            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)

    def test_claim_on_unterminated_frontmatter_returns_error_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            run_dir = use_sink(tmp) / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            (run_dir / "T1.md").write_text("---\nid: T1\nstatus: ready\n", encoding="utf-8")
            result = run_main(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual(1, result.returncode)
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
        """Every engine is a lawful ticket executor — orch-loop for a loop
        ticket, orch-frontier for a nested template (contracts/work-item.md, Executor form).

        This was a partition until P4-3: the other half was the engines
        refused as an executor, orch-compose and orch-panel, both deleted
        there. A refusal set with no members refuses nothing, so the concept
        went with them and this is the whole of the pin — an engine added to
        the library without a decision about it fails right here."""
        engines = {
            path.name
            for path in (ROOT / "skills" / "engines").iterdir()
            if path.is_dir()
        }
        self.assertEqual({"orch-frontier", "orch-loop"}, engines)
        self.assertFalse(hasattr(tickets_mod, "ENGINE_EXECUTORS"))
        # The script no longer names the set at all: nothing in it branched
        # on membership once the refusal half went, and a constant only a
        # test reads is a fact with no consumer. The tree above is the pin.
        self.assertFalse(hasattr(tickets_mod, "TICKET_EXECUTOR_ENGINES"))

    def test_a_loop_or_frontier_executor_is_lawful(self):
        for engine in ("orch-frontier", "orch-loop"):
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                self.make(tmp, engine)
                summary = run_cmd(tmp, "list")["tickets"][0]
                self.assertNotIn("error", summary, engine)
                self.assertEqual(["T1"], [t["id"] for t in run_cmd(tmp, "ready")["ready"]])
                payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
                self.assertIn("recut", payload.get("error", ""), engine)

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

    def test_claim_outside_a_repo_still_enforces_v0_recut(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_tickets(
                use_sink(tmp) / "tickets" / "testrun", {"T1": ("ready", "[]")}
            )
            bare = tmp / "no-repo-here"
            bare.mkdir()
            result = run_full(bare, "claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual(1, result.returncode)
            self.assertIn("requires `recut`", json.loads(result.stdout)["error"])
            self.assertIn(
                "status: ready", (run_dir / "T1.md").read_text(encoding="utf-8")
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
status: claimed
executor: orch-tdd
pack: orch-code-pack
depends_on: []
write_scope: scratch/t1.txt
bound: 30m
claimed_by: legacy-agent
claimed_at: 2099-01-01T00:00:00Z
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
