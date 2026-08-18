"""Transcript-root and session-index regressions."""

from tests.test_ui_cases._transcript_support import *  # noqa: F401,F403
class TestTranscriptRoot(TranscriptCase):
    """`S1` completion test 2, spec criterion 5."""

    def test_the_flag_selects_the_root_the_index_reads(self):
        page = self.sessions()

        self.assertEqual(list(SESSIONS_NEWEST_FIRST), session_ids(page))
        self.assertIn(str(self.transcripts), block_for(page, "root", "</p>"))

    def test_the_default_is_the_operators_projects_directory(self):
        self.assertEqual(
            Path.home() / ".claude" / "projects", ui.transcript_root(None)
        )
        # Derived from the running user's home rather than a literal, and
        # by arithmetic alone: the directory patched in here does not exist,
        # and resolving the default must not care.
        with patch.object(Path, "home", return_value=self.tmp / "elsewhere"):
            self.assertEqual(
                self.tmp / "elsewhere" / ".claude" / "projects", ui.transcript_root(None)
            )
        self.assertFalse((self.tmp / "elsewhere").exists())

    def test_the_entry_point_hands_the_resolved_root_to_the_server(self):
        seen = {}

        def capture(root, port, transcripts=None):
            seen["transcripts"] = transcripts
            raise OSError("stopped before serving")

        with patch.object(ui, "create_server", capture):
            with contextlib.redirect_stderr(io.StringIO()):
                flagged = ui.main(
                    ["--root", str(self.main), "--transcripts", str(self.transcripts)]
                )
                self.assertEqual(2, flagged)
                self.assertEqual(self.transcripts, seen["transcripts"])

                self.assertEqual(2, ui.main(["--root", str(self.main)]))

        self.assertEqual(Path.home() / ".claude" / "projects", seen["transcripts"])

    def test_no_root_configured_reads_nothing_at_all(self):
        # The guarantee that keeps this suite off the operator's machine: a
        # caller that supplies no root gets the named empty state, so a test
        # that forgets one cannot fall back to `~/.claude/projects`.
        with patch.object(ui, "_transcript_summary") as parsed:
            page = self.sessions(None)

        parsed.assert_not_called()
        self.assertIn(ui.EMPTY_NO_TRANSCRIPTS, block_for(page, "empty", "</p>"))

    def test_only_the_entry_point_resolves_the_default(self):
        callers = set()
        for node in ast.walk(ast.parse(UI_PY.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.FunctionDef):
                continue
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id == "transcript_root"
                ):
                    callers.add(node.name)

        self.assertEqual({"main"}, callers)


class TestSessionIndex(TranscriptCase):
    """`S1` completion test 3, spec criterion 6."""

    def test_every_project_directory_contributes_to_one_index(self):
        page = self.sessions()

        self.assertEqual(sorted(SESSIONS_NEWEST_FIRST), sorted(session_ids(page)))
        self.assertEqual(4, len(set(SESSION_PROJECT.values())))

    def test_sessions_are_ordered_by_last_activity_newest_first(self):
        page = self.sessions()

        self.assertEqual(list(SESSIONS_NEWEST_FIRST), session_ids(page))

    def test_the_ordering_is_the_activity_time_and_not_the_directory_walk(self):
        # Two directories interleave in the expected order, so an index that
        # grouped by directory could not produce it.
        drawn = session_ids(self.sessions())
        projects = [SESSION_PROJECT[session] for session in drawn]

        self.assertNotEqual(sorted(projects), projects)

    def test_each_row_carries_its_last_activity_stamp(self):
        page = self.sessions()

        for session in SESSIONS_NEWEST_FIRST:
            self.assertIn(session_stamp(session), session_cell(page, session, "when"))

    def test_a_worktree_state_record_supplies_the_working_directory(self):
        page = self.sessions()

        self.assertIn(
            "/Users/dmcinerney/tools/alpha", session_cell(page, TITLED_SESSION, "cwd")
        )
        self.assertIn(ui.CWD_FROM_RECORD, session_cell(page, TITLED_SESSION, "cwd"))

    def test_the_worktree_path_wins_over_the_directory_it_was_opened_from(self):
        self.assertIn(
            "/Users/dmcinerney/tools/beta-repo/.claude/worktrees/wt-one",
            session_cell(self.sessions(), TRUNCATED_SESSION, "cwd"),
        )

    def test_a_session_with_no_record_decodes_the_directory_name(self):
        cell = session_cell(self.sessions(), UNTITLED_SESSION, "cwd")

        self.assertIn("/Users/dmcinerney/tools/alpha", cell)
        self.assertIn(ui.CWD_FROM_NAME, cell)

    def test_the_decode_is_named_as_a_guess_where_it_provably_is_one(self):
        # Both sessions sit in `-Users-dmcinerney-tools-beta-repo`. The
        # record says `/Users/dmcinerney/tools/beta-repo`; the name decodes
        # to `/Users/dmcinerney/tools/beta/repo`, because a `-` already in a
        # directory name is indistinguishable from an encoded separator.
        page = self.sessions()
        recorded = session_cell(page, MARKUP_SESSION, "cwd")
        guessed = session_cell(page, MALFORMED_SESSION, "cwd")

        self.assertIn("/Users/dmcinerney/tools/beta-repo", recorded)
        self.assertIn(ui.CWD_FROM_RECORD, recorded)
        self.assertIn("/Users/dmcinerney/tools/beta/repo", guessed)
        self.assertIn(ui.CWD_FROM_NAME, guessed)

    def test_a_directory_name_that_is_not_a_path_is_a_named_diagnostic(self):
        page = self.sessions()

        self.assertIn(ui.DIAGNOSTIC_UNDECODABLE_SLUG, block_for(page, "diagnostics", "</ul>"))
        self.assertIn(UNDECODABLE_PROJECT, block_for(page, "diagnostics", "</ul>"))
        self.assertIn(ui.EMPTY_NO_CWD, session_cell(page, EMPTY_SESSION, "cwd"))

    def test_each_row_carries_its_subagent_count(self):
        page = self.sessions()

        self.assertIn("3", session_cell(page, TITLED_SESSION, "agents"))
        self.assertIn("0", session_cell(page, UNTITLED_SESSION, "agents"))

    def test_a_subagent_transcript_is_not_itself_a_session(self):
        self.assertNotIn("agent-aa11", session_ids(self.sessions()))

    def test_the_run_index_offers_the_session_index(self):
        page = ui.render_route(self.main, "/")[1]

        self.assertIn('href="{0}"'.format(ui.SESSIONS_ROUTE), page)


