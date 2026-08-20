"""Behavioral ticket regression cases."""

from .packet_close import *  # noqa: F401,F403

class TestReadyReportsWhatItCouldNotGrade(unittest.TestCase):
    """`ready` used to answer a read failure with silence: an unloadable
    ticket was dropped, a failed promotion write was `continue`, and a
    claimed ticket that had stopped being readable was counted as the
    holder still moving. A frontier reading an empty list cannot tell "no
    ticket is ready" from "four could not be looked at" (F F4), so every
    ticket this command could not read or grade comes back under `skipped`.
    """

    def ready(self, tmp: Path):
        return run_cmd(tmp, "ready", "--run", "testrun")

    def test_the_flat_ticket_family_needs_no_ui_reader_module(self):
        """The installed ticket command is copied as its closed ticket family.

        Reader modules are not part of that portable packet. Readiness must
        therefore remain executable when only the established ``tickets_*``
        support set and state-root resolver sit beside the facade.
        """
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            flat = tmp / "bin"
            flat.mkdir()
            for source in (*TICKETS_MODULES, STATE_ROOT_PY):
                (flat / source.name).write_text(
                    source.read_text(encoding="utf-8"), encoding="utf-8"
                )
            repo = tmp / "repo"
            (repo / ".git").mkdir(parents=True)
            sink = tmp / "sink"
            make_tickets(sink / "tickets" / "testrun", {"T1": ("ready", "[]")})
            environment = os.environ.copy()
            environment[STATE_HOME_ENV_VAR] = str(sink)
            completed = subprocess.run(
                [sys.executable, str(flat / "tickets.py"), "ready", "--run", "testrun"],
                cwd=str(repo), env=environment, capture_output=True, text=True,
                encoding="utf-8", errors="replace",
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(["T1"], [item["id"] for item in payload["ready"]])

    def test_a_readable_run_reports_an_empty_skipped_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            payload = self.ready(tmp)
            self.assertEqual(["T1"], [item["id"] for item in payload["ready"]])
            self.assertEqual([], payload["skipped"])

    def test_an_unreadable_ticket_is_named_with_its_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("ready", "[]")})
            (run_dir / "T2.md").write_text("no frontmatter here\n", encoding="utf-8")
            payload = self.ready(tmp)
            self.assertEqual(["T1"], [item["id"] for item in payload["ready"]])
            self.assertEqual(["T2"], [item["id"] for item in payload["skipped"]])
            self.assertTrue(payload["skipped"][0]["reason"])

    def test_a_dependency_naming_no_ticket_in_the_run_is_named(self):
        """A dangling edge never completes, so the dependent sat in the
        listing's silence forever -- and a `depends_on` written as a bare
        scalar is iterated by character into the same silence."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("pending", "[T0]"), "T2": ("pending", "T0")})
            payload = self.ready(tmp)
            self.assertEqual([], payload["ready"])
            self.assertEqual(
                {"T1", "T2"}, {item["id"] for item in payload["skipped"]}
            )
            for item in payload["skipped"]:
                self.assertIn("depends_on", item["reason"])

    def test_a_promotion_that_could_not_be_written_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("pending", "[]")})
            path = run_dir / "T1.md"
            text = path.read_text(encoding="utf-8")
            text = tickets_mod._set_frontmatter_field(text, "admission", "v1:pending")
            text = tickets_mod._set_frontmatter_field(text, "cohort", "v1:ticket:T1")
            text = tickets_mod._set_frontmatter_field(text, "pack", "orch-code-pack")
            text = tickets_mod._set_frontmatter_field(text, "isolation", "required")
            text = tickets_mod._set_frontmatter_field(text, "mutations", "[change:scratch/T1.txt]")
            subprocess.run(["git", "init", "-q", str(tmp)], check=True)
            subprocess.run(["git", "-C", str(tmp), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(tmp), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(tmp), "commit", "--allow-empty", "-qm", "baseline"], check=True)
            revision = subprocess.check_output(
                ["git", "-C", str(tmp), "rev-parse", "HEAD"], text=True
            ).strip()
            baseline = {"identity": {"kind": "git-tree", "repo": "run-project", "revision": revision}, "name": "baseline", "type": "identity"}
            text = tickets_mod._write_section(
                text, "Fixed inputs", "- input: " + json.dumps(baseline, separators=(",", ":"), sort_keys=True)
            )
            path.write_text(text, encoding="utf-8")
            with refusing_to_write(run_dir / "T1.md"):
                payload = self.ready(tmp)
            self.assertEqual([], payload["ready"])
            self.assertEqual(["T1"], [item["id"] for item in payload["skipped"]])
            self.assertIn("promote", payload["skipped"][0]["reason"])

    def test_a_claim_that_stopped_being_readable_is_named_not_read_as_motion(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, {"T1": ("claimed", "[]")})
            with refusing_to_read(run_dir / "T1.md", OSError, after=1):
                payload = self.ready(tmp)
            self.assertEqual([], payload["ready"])
            self.assertEqual(["T1"], [item["id"] for item in payload["skipped"]])
            self.assertIn("claimed", payload["skipped"][0]["reason"])


class TestClaimGradesStalenessAsReadyDoes(unittest.TestCase):
    """`_claim_is_stale`'s docstring says the two paths "cannot answer
    differently about one claim". They could: `ready` graded the
    grant-merged, list-normalised ticket while `claim` graded raw
    frontmatter, so a `write_scope` written as a bare scalar -- the shape
    half the sink carries -- was iterated by character on the claim path,
    every cited artifact fell outside the scope of letters, and a lane
    still writing was handed to a second executor (F F4)."""

    def fixture(self, tmp: Path):
        (tmp / ".git").mkdir()
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        scratch = tmp / "scratch"
        scratch.mkdir()
        artifact = scratch / "t1.txt"
        artifact.write_text("live\n", encoding="utf-8")
        long_ago = (datetime.now(timezone.utc) - timedelta(hours=4)).strftime(
            tickets_mod.UTC_STAMP
        )
        path = run_dir / "T1.md"
        path.write_text(
            "---\nid: T1\nrun: testrun\nstatus: claimed\nexecutor: orch-tdd\n"
            f"depends_on: []\nwrite_scope: {scratch.name}/t1.txt\nbound: 30m\n"
            f"claimed_by: agent-a\nclaimed_at: {long_ago}\n---\n\n"
            f"## Objective\n\nWork.\n\n## Result\n\nWrote {artifact}\n",
            encoding="utf-8",
        )
        # the ticket itself is old; only the cited artifact is moving
        old = (datetime.now(timezone.utc) - timedelta(hours=4)).timestamp()
        os.utime(path, (old, old))
        return path

    def test_a_bare_scalar_scope_holds_the_claim_on_both_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.fixture(tmp)
            self.assertEqual([], run_cmd(tmp, "ready", "--run", "testrun")["ready"])
            payload = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertIn("error", payload)
            self.assertIn("requires `recut`", payload["error"])


class TestAppendLockDocstringIsTrue(unittest.TestCase):
    """`_append_one_line` takes a mandatory range lock on byte zero, which
    on Windows fails a concurrent *reader* of that byte too -- so the
    docstring's "an append blocks only another append" told a reader it was
    safe when `_notes_terminal` and every other reader can be refused
    (F F4)."""

    def test_the_docstring_does_not_promise_readers_are_unaffected(self):
        doc = " ".join((tickets_mod._append_one_line.__doc__ or "").split())
        self.assertNotIn("blocks only another append", doc)
        self.assertIn("reader", doc)

    def test_the_terminal_reader_refuses_when_it_cannot_read_rather_than_calling_the_run_open(self):
        """The docstring now says a refused reader retries and has not found
        the file unreadable; `_notes_terminal` was the reader F F4 named, and
        it answered every failure with "open" -- so a note landed on a closed
        run whenever the read was refused. A missing notes.md is still open
        (the first note creates it); an unreadable one is an error, and the
        note is not written."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            self.assertIn(
                "run_state", run_cmd(worktree, "run-state", "testrun", "--note", "one")
            )
            with refusing_to_read(notes_of(), OSError):
                payload = run_cmd(worktree, "run-state", "testrun", "--note", "two")
            self.assertIn("error", payload)
            self.assertIn("unreadable", payload["error"])
            self.assertEqual(["one"], notes_of().read_text(encoding="utf-8").splitlines())
