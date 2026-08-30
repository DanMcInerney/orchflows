"""Writer relocation and no-fallback cases."""

import json

from tests.test_state_root_cases.support import (
    FRICTION_PY,
    SCRIPTS_DIR,
    TICKET,
    TICKETS_PY,
    SinkFixture,
    listing,
    run_script,
)


class TestEveryWriterLandsInTheSink(SinkFixture):
    """Writer relocation proved at the file and subprocess seams."""

    def assert_repo_untouched(self):
        self.assertFalse((self.repo / ".orch").exists(), "a writer created .orch/")

    def test_a_run_state_note_appends_under_the_sink(self):
        done = run_script(
            TICKETS_PY,
            "run-state",
            "testrun",
            "--note",
            "slice one landed",
            cwd=self.repo,
            sink=self.sink,
        )
        payload = json.loads(done.stdout)
        worklog = self.sink / "runs" / "testrun" / "notes.md"
        self.assertEqual(str(worklog.resolve()), payload["run_state"]["path"])
        self.assertEqual("slice one landed\n", worklog.read_text(encoding="utf-8"))
        self.assert_repo_untouched()

    def test_a_run_state_artifact_lands_under_the_run_partition(self):
        run_script(
            TICKETS_PY,
            "run-state",
            "testrun",
            "--artifact",
            "evidence.md",
            "--text",
            "the bytes in the sink\n",
            cwd=self.repo,
            sink=self.sink,
        )
        artifact = self.sink / "runs" / "testrun" / "evidence.md"
        self.assertEqual("the bytes in the sink\n", artifact.read_text(encoding="utf-8"))
        self.assert_repo_untouched()

    def test_a_ticket_is_read_out_of_the_sink_from_a_repository_with_none(self):
        run_dir = self.sink / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        (run_dir / "T1.md").write_text(TICKET, encoding="utf-8")
        done = run_script(
            TICKETS_PY, "list", "--run", "testrun", cwd=self.repo, sink=self.sink
        )
        payload = json.loads(done.stdout)
        self.assertEqual(["T1"], [ticket["id"] for ticket in payload["tickets"]])
        self.assert_repo_untouched()

    def test_a_friction_entry_lands_in_the_sink(self):
        done = run_script(
            FRICTION_PY, "observed thing", "expected thing", cwd=self.repo, sink=self.sink
        )
        self.assertEqual(0, done.returncode)
        self.assertEqual("friction logged", done.stdout.strip())
        log = self.sink / "friction" / f"{self.stamp()}.jsonl"
        entry = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual("observed thing", entry["observed"])
        self.assert_repo_untouched()

    def test_two_workspaces_of_one_project_write_one_sink(self):
        origin = "https://example.invalid/acme/alpha.git"
        self.give_origin(self.repo, origin)
        second = self.tmp / "other-clone"
        (second / ".git").mkdir(parents=True)
        self.give_origin(second, origin)
        run_script(
            TICKETS_PY,
            "run-state",
            "testrun",
            "--note",
            "from clone one",
            cwd=self.repo,
            sink=self.sink,
        )
        run_script(
            TICKETS_PY,
            "run-state",
            "testrun",
            "--note",
            "from clone two",
            cwd=second,
            sink=self.sink,
        )
        worklog = self.sink / "runs" / "testrun" / "notes.md"
        self.assertEqual(
            ["from clone one", "from clone two"],
            worklog.read_text(encoding="utf-8").splitlines(),
        )
        self.assertFalse((second / ".orch").exists())
        self.assert_repo_untouched()

    def test_two_unrelated_projects_write_one_sink(self):
        second = self.tmp / "other-repo"
        (second / ".git").mkdir(parents=True)
        run_script(
            TICKETS_PY,
            "run-state",
            "run-one",
            "--note",
            "from repo one",
            cwd=self.repo,
            sink=self.sink,
        )
        run_script(
            TICKETS_PY,
            "run-state",
            "run-two",
            "--note",
            "from repo two",
            cwd=second,
            sink=self.sink,
        )
        runs = self.sink / "runs"
        self.assertEqual(
            "from repo one\n", (runs / "run-one" / "notes.md").read_text(encoding="utf-8")
        )
        self.assertEqual(
            "from repo two\n", (runs / "run-two" / "notes.md").read_text(encoding="utf-8")
        )
        self.assertFalse((second / ".orch").exists())
        self.assert_repo_untouched()

    def test_outside_any_repository_the_sink_still_resolves(self):
        bare = self.tmp / "no-repo-here"
        bare.mkdir()
        done = run_script(
            TICKETS_PY,
            "run-state",
            "testrun",
            "--note",
            "no git in sight",
            cwd=bare,
            sink=self.sink,
        )
        payload = json.loads(done.stdout)
        self.assertNotIn("error", payload)
        self.assertEqual(
            "no git in sight\n",
            (self.sink / "runs" / "testrun" / "notes.md").read_text(encoding="utf-8"),
        )
        self.assertFalse((bare / ".orch").exists())


class TestThereIsNoFallback(SinkFixture):
    """A blocked sink reports loss and never writes under the cwd."""

    def setUp(self):
        super().setUp()
        self.blocked = self.tmp / "blocked-sink"
        self.blocked.write_text("not a directory\n", encoding="utf-8")

    def test_run_state_reports_the_failure_and_writes_nothing_under_cwd(self):
        before = listing(self.repo)
        done = run_script(
            TICKETS_PY,
            "run-state",
            "testrun",
            "--note",
            "x",
            cwd=self.repo,
            sink=self.blocked,
        )
        self.assertEqual(1, done.returncode)
        payload = json.loads(done.stdout)
        self.assertIn("error", payload)
        self.assertNotIn("run_state", payload)
        self.assertEqual(before, listing(self.repo))

    def test_the_logger_names_the_loss_exits_zero_and_writes_nothing_under_cwd(self):
        before = listing(self.repo)
        done = run_script(FRICTION_PY, "o", "e", cwd=self.repo, sink=self.blocked)
        self.assertEqual(0, done.returncode)
        self.assertEqual("", done.stdout)
        self.assertIn("not logged", done.stderr)
        self.assertNotIn("Traceback", done.stderr)
        self.assertEqual(before, listing(self.repo))

    def test_the_logger_survives_a_missing_resolver_beside_it(self):
        flat = self.tmp / "bin"
        flat.mkdir()
        (flat / "friction.py").write_text(
            FRICTION_PY.read_text(encoding="utf-8"), encoding="utf-8"
        )
        done = run_script(flat / "friction.py", "o", "e", cwd=self.repo, sink=self.sink)
        self.assertEqual(0, done.returncode)
        self.assertEqual("", done.stdout)
        self.assertNotIn("Traceback", done.stderr)
        self.assertIn("not logged", done.stderr)
        self.assertFalse((self.sink / "friction").exists())

    def test_the_flat_installed_layout_resolves_when_the_resolver_is_beside_it(self):
        flat = self.tmp / "bin"
        flat.mkdir()
        names = ["friction.py", "packs.py", "packs_support.py", "state_root.py"] + [
            path.name for path in SCRIPTS_DIR.glob("tickets*.py")
        ]
        for name in names:
            (flat / name).write_text(
                (SCRIPTS_DIR / name).read_text(encoding="utf-8"), encoding="utf-8"
            )
        logged = run_script(flat / "friction.py", "o", "e", cwd=self.repo, sink=self.sink)
        self.assertEqual("friction logged", logged.stdout.strip())
        noted = run_script(
            flat / "tickets.py",
            "run-state",
            "testrun",
            "--note",
            "flat",
            cwd=self.repo,
            sink=self.sink,
        )
        self.assertNotIn("error", json.loads(noted.stdout))
        self.assertEqual(
            "flat\n",
            (self.sink / "runs" / "testrun" / "notes.md").read_text(encoding="utf-8"),
        )
