"""Transcript labels, content wall, read-only, and degradation regressions."""

from reader.tests.test_ui_cases._transcript_support import *  # noqa: F401,F403
class TestSessionLabel(TranscriptCase):
    """`S1` completion test 4, spec criterion 7."""

    def test_the_label_is_the_last_ai_title_record(self):
        page = self.sessions()

        self.assertIn(LAST_AI_TITLE, session_cell(page, TITLED_SESSION, "title"))
        self.assertNotIn(SUPERSEDED_AI_TITLE, page)

    def test_a_session_with_no_ai_title_renders_a_named_fallback(self):
        cell = session_cell(self.sessions(), UNTITLED_SESSION, "title")

        self.assertIn(ui.EMPTY_NO_TITLE, cell)

    def test_a_title_carrying_markup_reaches_the_page_escaped(self):
        cell = session_cell(self.sessions(), MARKUP_SESSION, "title")

        self.assertIn(html.escape(PAYLOAD), cell)
        self.assertNotIn(PAYLOAD, cell)


class TestContentWall(TranscriptCase):
    """`S1` completion test 5, spec criterion 10. A transcript holds the
    operator's prompts, file contents and command output for every project
    on the machine. The renderable set is closed and this is its guard."""

    def carriers(self) -> list:
        return [
            path
            for path in sorted(self.transcripts.rglob("*"))
            if path.is_file()
            and TRANSCRIPT_SENTINEL in path.read_text(encoding="utf-8", errors="replace")
        ]

    def test_the_fixture_really_carries_the_sentinel(self):
        # Without this the sweep below passes over a corpus that never had
        # anything to leak.
        carriers = self.carriers()

        self.assertGreaterEqual(len(carriers), 6)
        self.assertIn(
            "agent-aa11.jsonl", [path.name for path in carriers]
        )

    def test_the_sentinel_reaches_no_route(self):
        with serving(self.main, self.transcripts) as server:
            for route in every_route():
                status, page = get(server, route)

                self.assertIn(status, (200, 404), route)
                self.assertNotIn(TRANSCRIPT_SENTINEL, page, route)

    def test_the_sweep_still_renders_what_it_is_allowed_to(self):
        # The sweep above would also pass on a page that rendered nothing.
        page = self.sessions()

        self.assertIn(LAST_AI_TITLE, session_cell(page, TITLED_SESSION, "title"))
        self.assertEqual(len(SESSIONS_NEWEST_FIRST), len(session_ids(page)))

    def test_the_index_emits_only_the_fields_the_spec_admits(self):
        # Named here so widening the row is a decision rather than a slip.
        self.assertEqual(
            ("sid", "title", "cwd", "when", "size", "agents", "notes"),
            ui.SESSION_COLUMNS,
        )
        self.assertEqual(len(ui.SESSION_COLUMNS), len(ui.SESSION_HEADINGS))

    def test_the_rendered_row_carries_exactly_the_closed_set(self):
        # The tuple above is only a wall if the page is built from it. An
        # eighth cell written beside it renders a transcript field the spec
        # does not admit, and the tuple still reads as correct.
        page = self.sessions()

        for session in SESSIONS_NEWEST_FIRST:
            self.assertEqual(
                list(ui.SESSION_COLUMNS), row_columns(page, session), session
            )

    def test_narrowing_the_closed_set_narrows_the_row_it_renders(self):
        # Proves the row derives from the tuple rather than merely agreeing
        # with it: a row spelled out in a format string is unmoved by this.
        with patch.object(ui, "SESSION_COLUMNS", ("sid", "title")):
            page = self.sessions()

        self.assertEqual(["sid", "title"], row_columns(page, TITLED_SESSION))


class TestTranscriptsAreReadOnly(TranscriptCase):
    """`S1` completion test 6, spec criterion 11."""

    def test_exercising_every_route_writes_nothing_under_the_transcript_root(self):
        before = snapshot(self.transcripts)
        self.assertTrue(before)

        with serving(self.main, self.transcripts) as server:
            for route in every_route():
                status, page = get(server, route)
                self.assertIn(status, (200, 404), route)
                self.assertTrue(page, route)

        self.assertEqual(before, snapshot(self.transcripts))

    def test_the_snapshot_would_notice_a_write(self):
        self.own_fixture()
        before = snapshot(self.transcripts)
        (self.transcripts / ALPHA_PROJECT / "intruder.jsonl").write_text(
            "{}\n", encoding="utf-8"
        )

        self.assertNotEqual(before, snapshot(self.transcripts))


class TestTranscriptDegradation(TranscriptCase):
    """`S1` completion test 7, spec criterion 12. The layout is another
    program's undocumented implementation detail: it must degrade visibly,
    never silently and never by raising."""

    def notes(self, session: str) -> str:
        return session_cell(self.sessions(), session, "notes")

    def test_a_malformed_transcript_names_its_unreadable_lines_and_still_lists(self):
        notes = self.notes(MALFORMED_SESSION)

        self.assertIn(ui.DIAGNOSTIC_UNREADABLE_LINES, notes)
        self.assertIn(MALFORMED_SESSION, session_ids(self.sessions()))

    def test_a_truncated_transcript_names_its_unreadable_line(self):
        self.assertIn(ui.DIAGNOSTIC_UNREADABLE_LINES, self.notes(TRUNCATED_SESSION))

    def test_a_truncated_transcript_still_yields_the_records_before_the_cut(self):
        page = self.sessions()

        self.assertIn(
            "Worktree session, cut short", session_cell(page, TRUNCATED_SESSION, "title")
        )

    def test_an_empty_transcript_names_a_diagnostic_rather_than_looking_healthy(self):
        notes = self.notes(EMPTY_SESSION)

        self.assertIn(ui.DIAGNOSTIC_NO_RECORDS, notes)

    def test_a_healthy_transcript_carries_no_diagnostic_at_all(self):
        # Otherwise every assertion above is satisfied by a page that warns
        # about everything.
        self.assertEqual("", self.notes(TITLED_SESSION).strip())

    def test_a_session_with_no_subagents_directory_still_lists(self):
        page = self.sessions()

        self.assertFalse((self.transcripts / ALPHA_PROJECT / UNTITLED_SESSION).exists())
        self.assertIn(UNTITLED_SESSION, session_ids(page))
        self.assertIn("0", session_cell(page, UNTITLED_SESSION, "agents"))

    def test_a_transcript_that_cannot_be_opened_is_named_rather_than_raised(self):
        with patch.object(Path, "open", side_effect=OSError("gone")):
            page = self.sessions()

        self.assertEqual(len(SESSIONS_NEWEST_FIRST), len(session_ids(page)))
        self.assertIn(
            ui.DIAGNOSTIC_UNREADABLE_TRANSCRIPT, session_cell(page, TITLED_SESSION, "notes")
        )

    def test_a_record_of_the_wrong_shape_is_dropped_rather_than_believed(self):
        self.own_fixture()
        path = self.transcripts / ALPHA_PROJECT / (TITLED_SESSION + ".jsonl")
        path.write_text(
            '{"type":"ai-title","aiTitle":["not","a","string"]}\n'
            '{"type":"worktree-state","worktreeSession":"not an object"}\n',
            encoding="utf-8",
        )
        cell = session_cell(self.sessions(), TITLED_SESSION, "title")

        self.assertIn(ui.EMPTY_NO_TITLE, cell)


class TestSessionProjectionContentWall(TranscriptCase):
    def test_session_json_is_metadata_and_structure_never_transcript_content(self):
        before = snapshot(self.transcripts)
        routes = (
            "/api/v1/sessions",
            "/api/v1/sessions/{0}".format(TITLED_SESSION),
            "/api/v1/sessions/{0}".format(MARKUP_SESSION),
        )

        with serving(self.main, self.transcripts) as server:
            for route in routes:
                status, _headers, body = fetch(server, route)
                self.assertEqual(200, status, route)
                self.assertNotIn(TRANSCRIPT_SENTINEL, body, route)
                self.assertNotIn(str(self.transcripts), body, route)
                self.assertNotIn("tool_use", body, route)
                self.assertNotIn("tool_result", body, route)
                self.assertNotIn("last-prompt", body, route)
                if MARKUP_SESSION in route:
                    self.assertNotIn(PAYLOAD, body)
                    self.assertIn(PAYLOAD, json.loads(body)["session"]["title"])

        self.assertEqual(before, snapshot(self.transcripts))
