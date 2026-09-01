"""Behavioral ticket regression cases."""

from .run_state_artifacts import *  # noqa: F401,F403

class TerminalNoteTest(unittest.TestCase):
    """contracts/worklog.md: "Notes append in occurrence order, and no note
    is written past a terminal section: a worklog carries no terminal
    placeholder until it closes."

    Both halves are one law. A placeholder written at creation would make
    every note a note past a terminal section; a terminal section written
    at the close makes the notes after it the error they are.
    """

    def test_creation_writes_no_terminal_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--note", "the first line")
            text = notes_of().read_text(encoding="utf-8")
            self.assertEqual("the first line\n", text)
            self.assertNotIn(tickets_mod.TERMINAL_HEADING, text)
            for state in tickets_mod.TERMINAL_STATES:
                self.assertNotIn(state, text, state)

    def test_note_note_terminal_note_refuses_the_fourth_in_occurrence_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for line in ("note one", "note two"):
                self.assertIn(
                    "run_state", run_cmd(worktree, "run-state", "testrun", "--note", line)
                )
            closed = run_cmd(worktree, "run-state", "testrun", "--terminal", "complete",
                             "--text", "every criterion passed")
            self.assertEqual("terminal", closed["run_state"]["mode"])
            self.assertEqual("complete", closed["run_state"]["terminal"])

            result = run_main(worktree, "run-state", "testrun", "--note", "note four")
            self.assertEqual(1, result.returncode, result.stdout)
            error = json.loads(result.stdout)["error"]
            self.assertIn("terminal", error)
            self.assertIn("complete", error)
            self.assertIn(str(notes_of().resolve()), error)

            lines = notes_of().read_text(encoding="utf-8").splitlines()
            # the notes are in occurrence order, the close is after them, and
            # the fourth note is nowhere in the file
            self.assertEqual(["note one", "note two"], lines[:2])
            self.assertLess(lines.index("note two"), lines.index("## terminal: complete"))
            self.assertNotIn("note four", lines)
            self.assertIn("every criterion passed", lines)

    def test_a_second_close_is_refused_and_the_first_stands(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--terminal", "complete",
                    "--text", "the deciding evidence")
            before = notes_of().read_text(encoding="utf-8")
            result = run_main(worktree, "run-state", "testrun", "--terminal", "failed",
                              "--text", "a second close")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("complete", json.loads(result.stdout)["error"])
            self.assertEqual(before, notes_of().read_text(encoding="utf-8"))

    # Both halves of what stood here are graded by TestRunStateWorklog, each
    # asserting more: the interleave by
    # test_a_prior_line_and_an_outside_writer_both_survive, and the eight
    # concurrent writers by test_concurrent_notes_all_land_whole, which also
    # grades the payloads (a writer that reported an error and a writer whose
    # line was lost are two defects, and the file check alone shows only the
    # second). The mechanism is graded below off the AST, which is the only
    # place it can be: the writes above land between complete invocations, so
    # a read-modify-write reproduces both expectations exactly.

    def test_the_append_is_one_open_in_append_mode_with_no_read(self):
        """The mechanism assertion, read off the AST: one open, append mode,
        nothing read.

        Replaces the source-text grep this class carried at 6c3b7aa:907,
        which fell to a spelling change and to the call moving one function
        away -- each a false failure, neither a change in mechanism."""

        assert_one_append_open_and_no_read(
            self, inspect.getsource(tickets_mod._append_one_line), "_append_one_line"
        )

    def test_the_assertion_survives_alternate_open_spellings(self):
        """The spellings the grep could not read. Each is the same mechanism
        written another way, so the assertion has to pass every one of them
        while the string the grep looked for appears in none."""

        for label, source in APPEND_SPELLINGS.items():
            with self.subTest(label):
                self.assertNotIn('open(path, "a"', source)
                assert_one_append_open_and_no_read(self, source, "_append_one_line")

    def test_a_read_modify_write_implementation_fails_the_assertion(self):
        """The can-fail direction, without which the assertion grades nothing.

        Each wrong implementation is imported beside the tree and run for
        real: first against the interleaved write, where it reproduces the
        behavioural expectation exactly and so goes uncaught, and then
        against the assertion, which is the one check here that can see it."""

        for label, source in WRONG_APPENDS.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                wrong = load_beside_the_tree(tmp, "wrong_append", source)
                path = tmp / "worklog.md"
                path.write_text("", encoding="utf-8")
                wrong._append_one_line(path, "from the channel\n")
                with open(path, "a", encoding="utf-8", newline="\n") as handle:
                    handle.write("from another worktree\n")
                wrong._append_one_line(path, "from the channel again\n")
                self.assertEqual(
                    ["from the channel", "from another worktree",
                     "from the channel again"],
                    path.read_text(encoding="utf-8").splitlines(),
                    "the behavioural test cannot tell this from the real one",
                )
                with self.assertRaises(AssertionError):
                    assert_one_append_open_and_no_read(
                        self,
                        inspect.getsource(wrong._append_one_line),
                        "_append_one_line",
                    )

    def test_the_write_call_count_is_not_asserted(self):
        """Bodies that differ only in how many times they write get one
        verdict. The real function is already on two writes and a flush, so a
        count here would fail the next branch added to it -- the grep's
        mistake in another instrument."""

        for label, source in (
            ("one write", APPEND_SPELLINGS["single quotes"]),
            ("a write on every branch", BRANCHED_APPEND),
        ):
            with self.subTest(label):
                assert_one_append_open_and_no_read(self, source, "_append_one_line")

    def test_the_close_requires_a_known_state_and_its_deciding_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            # a ticket-level status is not a run-level terminal state
            for bad in ("suspended", "ready", "done", ""):
                result = run_main(worktree, "run-state", "testrun", "--terminal", bad,
                                  "--text", "x")
                self.assertEqual(1, result.returncode, f"{bad!r}: {result.stdout}")
                error = json.loads(result.stdout)["error"]
                for state in tickets_mod.TERMINAL_STATES:
                    self.assertIn(state, error, f"{bad!r}: {state}")
            # the deciding evidence is not optional
            result = run_main(worktree, "run-state", "testrun", "--terminal", "complete")
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("--text", json.loads(result.stdout)["error"])
            self.assertFalse(notes_of().exists())

    def test_every_run_level_terminal_state_closes_and_the_states_are_the_contract(self):
        for state in tickets_mod.TERMINAL_STATES:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
                run_cmd(worktree, "run-state", "testrun", "--terminal", state,
                        "--text", "the deciding evidence")
                self.assertIn(
                    f"## terminal: {state}",
                    notes_of().read_text(encoding="utf-8"),
                )
                result = run_main(worktree, "run-state", "testrun", "--note", "past it")
                self.assertEqual(1, result.returncode, f"{state}: {result.stdout}")
        self.assertEqual(
            ("complete", "blocked", "stalled", "limited", "failed"),
            tickets_mod.TERMINAL_STATES,
        )

    def test_a_note_may_not_forge_the_terminal_heading(self):
        """The marker is only trustworthy if a note cannot write one. A note
        that would read as a close is refused, so the guard can never be
        walked past by a line that merely looks like the close."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for forged in ("## terminal: complete", "  ## terminal", "## Terminal: failed"):
                result = run_main(worktree, "run-state", "testrun", "--note", forged)
                self.assertEqual(1, result.returncode, f"{forged!r}: {result.stdout}")
                self.assertIn("--terminal", json.loads(result.stdout)["error"])
            self.assertFalse(notes_of().exists())

    def test_the_close_is_per_run_and_per_tree(self):
        """A closed run does not close another run, and a closed research
        worklog does not close the run's own."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--terminal", "complete",
                    "--text", "closed")
            self.assertIn(
                "run_state", run_cmd(worktree, "run-state", "otherrun", "--note", "still open")
            )
            self.assertIn(
                "run_state",
                run_cmd(worktree, "run-state", "testrun", "--tree", "research",
                        "--note", "a research lane's own log"),
            )
            self.assertEqual(
                "a research lane's own log\n",
                (tree_dir_of("research") / "notes.md").read_text(
                    encoding="utf-8"
                ),
            )

    def test_an_artifact_is_not_a_note_and_survives_the_close(self):
        """The law is about notes past a terminal section. Evidence written
        under a name is not a note and stays writable after the close."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--terminal", "complete",
                    "--text", "closed")
            payload = run_cmd(worktree, "run-state", "testrun", "--artifact",
                              "post-close.md", "--text", "the join's own record\n")
            self.assertEqual("artifact", payload["run_state"]["mode"])
            self.assertEqual(
                "the join's own record\n",
                (run_dir_of() / "post-close.md").read_text(encoding="utf-8"),
            )


class ArtifactOverwriteTest(unittest.TestCase):
    """contracts/worklog.md: "Writing an artifact that already exists is
    refused by default, the refusal naming the existing path."

    `--artifact` is the one whole-file write on this channel, and two
    workspaces write one repository's `.orch/` at once. Truncating an
    existing artifact is how a sibling lane's evidence leaves no trace of
    having existed.
    """

    def test_an_existing_artifact_is_refused_and_the_refusal_names_the_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--artifact", "evidence.md",
                    "--text", "the first lane's evidence\n")
            artifact = run_dir_of() / "evidence.md"
            result = run_main(worktree, "run-state", "testrun", "--artifact",
                              "evidence.md", "--text", "a silent truncation\n")
            self.assertEqual(1, result.returncode, result.stdout)
            error = json.loads(result.stdout)["error"]
            self.assertIn(str(artifact.resolve()), error)
            self.assertIn("--replace", error)
            # the first content stays intact
            self.assertEqual(
                "the first lane's evidence\n", artifact.read_text(encoding="utf-8")
            )

    def test_replace_is_what_carries_the_overwrite_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "run-state", "testrun", "--artifact", "evidence.md",
                    "--text", "first\n")
            payload = run_cmd(worktree, "run-state", "testrun", "--artifact",
                              "evidence.md", "--text", "second\n", "--replace")
            self.assertEqual("artifact", payload["run_state"]["mode"])
            self.assertTrue(payload["run_state"]["replaced"])
            self.assertEqual(
                "second\n",
                (run_dir_of() / "evidence.md").read_text(encoding="utf-8"),
            )

    def test_a_first_write_needs_no_flag_and_reports_it_replaced_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(worktree, "run-state", "testrun", "--artifact",
                              "evidence.md", "--text", "only\n")
            self.assertFalse(payload["run_state"]["replaced"])
            self.assertEqual(
                "only\n", (run_dir_of() / "evidence.md").read_text(encoding="utf-8")
            )

    def test_replace_on_an_absent_artifact_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(worktree, "run-state", "testrun", "--artifact",
                              "fresh.md", "--text", "only\n", "--replace")
            self.assertEqual("artifact", payload["run_state"]["mode"])
            self.assertEqual(
                "only\n", (run_dir_of() / "fresh.md").read_text(encoding="utf-8")
            )

    def test_the_guard_is_the_run_partitioned_path_not_the_bare_name(self):
        """The same artifact name under two run ids is two paths, and neither
        refuses the other: the run id partitioning the path is what makes a
        whole-file write safe here at all."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for run in ("testrun", "otherrun"):
                payload = run_cmd(worktree, "run-state", run, "--artifact",
                                  "evidence.md", "--text", f"{run}\n")
                self.assertIn("run_state", payload, run)
            for run in ("testrun", "otherrun"):
                self.assertEqual(
                    f"{run}\n",
                    (run_dir_of(run) / "evidence.md").read_text(encoding="utf-8"),
                )

    def test_a_note_is_an_append_and_never_trips_the_artifact_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for line in ("one", "two", "three"):
                payload = run_cmd(worktree, "run-state", "testrun", "--note", line)
                self.assertIn("run_state", payload, line)
            self.assertEqual(
                ["one", "two", "three"],
                notes_of().read_text(encoding="utf-8").splitlines(),
            )


class OrchTreesTest(unittest.TestCase):
    """`.orch/research/`, `.orch/improvement/` and `.orch/handoffs/` had no
    writer: named in the library, reachable by no subcommand, so anything
    meant for them was written by hand or not at all. `--tree` addresses
    them beside `runs/`, and the run id keeps partitioning the path."""

    OWNERLESS = ("research", "improvement", "handoffs")

    def test_one_file_is_written_and_read_back_in_each_ownerless_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for tree in self.OWNERLESS:
                payload = run_cmd(worktree, "run-state", "testrun", "--tree", tree,
                                  "--artifact", "evidence.md", "--text", f"{tree} bytes\n")
                self.assertEqual(tree, payload["run_state"]["tree"], tree)
                landed = tree_dir_of(tree) / "evidence.md"
                self.assertEqual(str(landed.resolve()), payload["run_state"]["path"], tree)
                self.assertEqual(f"{tree} bytes\n", landed.read_text(encoding="utf-8"), tree)
            # written from the worktree, landed at the main root, every time
            self.assertFalse((worktree / ".orch").exists())

    def test_the_run_id_still_partitions_the_artifact_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for run in ("testrun", "otherrun"):
                run_cmd(worktree, "run-state", run, "--tree", "research",
                        "--artifact", "evidence.md", "--text", f"{run}\n")
            for run in ("testrun", "otherrun"):
                self.assertEqual(
                    f"{run}\n",
                    (tree_dir_of("research", run) / "evidence.md").read_text(
                        encoding="utf-8"
                    ),
                )

    def test_runs_stays_the_default_and_nothing_is_retired(self):
        """Every pre-existing call site passes no `--tree` and must land
        exactly where it always did."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            note = run_cmd(worktree, "run-state", "testrun", "--note", "a line")
            self.assertEqual("runs", note["run_state"]["tree"])
            self.assertEqual(str(notes_of().resolve()), note["run_state"]["path"])
            artifact = run_cmd(worktree, "run-state", "testrun", "--artifact",
                               "evidence.md", "--text", "bytes\n")
            self.assertEqual("runs", artifact["run_state"]["tree"])
            self.assertEqual(
                str((run_dir_of() / "evidence.md").resolve()),
                artifact["run_state"]["path"],
            )
            self.assertEqual("runs", tickets_mod.DEFAULT_RUN_STATE_TREE)
            self.assertIn("runs", tickets_mod.RUN_STATE_TREES)

    def test_an_explicit_runs_tree_is_the_same_path_as_the_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            explicit = run_cmd(worktree, "run-state", "testrun", "--tree", "runs",
                               "--artifact", "evidence.md", "--text", "bytes\n")
            self.assertEqual(
                str((run_dir_of() / "evidence.md").resolve()),
                explicit["run_state"]["path"],
            )

    def test_the_overwrite_guard_holds_in_every_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for tree in self.OWNERLESS:
                run_cmd(worktree, "run-state", "testrun", "--tree", tree,
                        "--artifact", "evidence.md", "--text", "first\n")
                result = run_main(worktree, "run-state", "testrun", "--tree", tree,
                                  "--artifact", "evidence.md", "--text", "clobber\n")
                self.assertEqual(1, result.returncode, f"{tree}: {result.stdout}")
                landed = tree_dir_of(tree) / "evidence.md"
                self.assertIn(str(landed.resolve()), json.loads(result.stdout)["error"], tree)
                self.assertEqual("first\n", landed.read_text(encoding="utf-8"), tree)

    def test_an_unknown_tree_is_refused_and_the_closed_set_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for bad in ("tickets", "friction", "../escape", "a/b", "", "canary"):
                result = run_main(worktree, "run-state", "testrun", "--tree", bad,
                                  "--artifact", "evidence.md", "--text", "x")
                self.assertEqual(1, result.returncode, f"{bad!r}: {result.stdout}")
                error = json.loads(result.stdout)["error"]
                for tree in tickets_mod.RUN_STATE_TREES:
                    self.assertIn(tree, error, f"{bad!r}: {tree}")
            # a refused tree creates nothing: the sink still holds only what
            # the fixture put there, and no run-state tree was opened
            self.assertEqual(
                ["tickets"], sorted(p.name for p in sink_root().iterdir())
            )
            self.assertFalse((main / ".orch").exists())

    def test_every_addressed_tree_is_gitignored_runtime_state(self):
        """`.gitignore` ignores `.orch/` whole: every tree this subcommand
        writes is runtime state, never tracked content. A tree added to the
        closed set that escaped that line would commit run output. The line
        was `.orch/*` while the canary fixture was re-admitted beneath it;
        with the fixture deleted there is nothing to re-admit."""

        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".orch/", ignore)
        for tree in tickets_mod.RUN_STATE_TREES:
            self.assertNotIn(f"!.orch/{tree}/", ignore, tree)
