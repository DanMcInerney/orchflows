"""Transcript parse-cache and validator-basis regressions."""

from tests.test_ui_cases._transcript_support import *  # noqa: F401,F403
class TestTranscriptParseCache(TranscriptCase):
    """`S1` completion test 8, spec criterion 13. A transcript is megabytes
    of conversation and the poll asks for the page every second."""

    def counted(self):
        seen = []
        real = ui._transcript_summary

        def counting(path):
            seen.append(str(path))
            return real(path)

        return seen, counting

    def test_two_requests_over_an_unchanged_root_parse_each_session_once(self):
        seen, counting = self.counted()

        with patch.object(ui, "_transcript_summary", counting):
            first = self.sessions()
            second = self.sessions()

        self.assertEqual(first, second)
        self.assertEqual(sorted(set(seen)), sorted(seen))
        self.assertEqual(len(SESSIONS_NEWEST_FIRST), len(seen))

    def test_a_changed_transcript_is_parsed_again(self):
        # A cache with no invalidation would satisfy the count above and
        # serve a label the transcript no longer carries.
        self.own_fixture()
        path = self.transcripts / ALPHA_PROJECT / (TITLED_SESSION + ".jsonl")
        self.sessions()
        path.write_text(
            '{"type":"ai-title","aiTitle":"Alpha, renamed"}\n', encoding="utf-8"
        )
        seen, counting = self.counted()

        with patch.object(ui, "_transcript_summary", counting):
            page = self.sessions()

        self.assertEqual([str(path)], seen)
        self.assertIn("Alpha, renamed", session_cell(page, TITLED_SESSION, "title"))

    def test_the_cache_is_bounded_so_a_long_lived_viewer_cannot_grow_forever(self):
        for index in range(ui.TRANSCRIPT_CACHE_LIMIT + 10):
            ui.cached_transcript(Path("/nowhere"), ("/nowhere", index, index))

        self.assertLessEqual(len(ui.TRANSCRIPT_CACHE), ui.TRANSCRIPT_CACHE_LIMIT)


class TestTranscriptValidatorBasis(TranscriptCase):
    """`U3`'s lesson, applied to the tree this ticket adds. A validator whose
    basis is narrower than the route's read set answers 304 to a page that
    has already moved, and a 304 is indistinguishable from nothing having
    happened. `S2` owns the `/session` tag end to end; what is held here is
    the narrower claim that the transcript root is inside the basis at all."""

    def digest(self, transcripts=True) -> str:
        root = self.transcripts if transcripts is True else transcripts
        with frozen_clock():
            return ui.state_digest(self.main, None, root)

    def test_a_transcript_that_changes_moves_the_validator(self):
        self.own_fixture()
        before = self.digest()
        (self.transcripts / ALPHA_PROJECT / (TITLED_SESSION + ".jsonl")).write_text(
            '{"type":"ai-title","aiTitle":"Alpha, renamed"}\n', encoding="utf-8"
        )

        self.assertNotEqual(before, self.digest())

    def test_a_session_appearing_moves_the_validator(self):
        self.own_fixture()
        before = self.digest()
        (self.transcripts / ALPHA_PROJECT / "77777777-7777-4777-8777-777777777777.jsonl").write_text(
            '{"type":"ai-title","aiTitle":"newly opened"}\n', encoding="utf-8"
        )

        self.assertNotEqual(before, self.digest())

    def test_a_subagent_appearing_moves_the_validator(self):
        # The count is on the page, so the metadata beside the transcript is
        # part of the read set even though no line of it is ever rendered.
        self.own_fixture()
        before = self.digest()
        (self.transcripts / ALPHA_PROJECT / TITLED_SESSION / "subagents" / "agent-aa14.meta.json").write_text(
            '{"agentType":"orch-worker","spawnDepth":1}\n', encoding="utf-8"
        )

        self.assertNotEqual(before, self.digest())

    def test_an_unchanged_root_holds_the_validator_still(self):
        # Otherwise the 304 is unreachable and the poll re-renders forever.
        self.assertEqual(self.digest(), self.digest())

    def test_the_orch_root_alone_no_longer_determines_the_tag(self):
        self.own_fixture()
        bare = self.tmp / "bare"
        bare.mkdir()

        self.assertNotEqual(self.digest(), self.digest(bare))
        self.assertNotEqual(self.digest(bare), self.digest(None))

    def test_a_root_that_appears_moves_the_validator(self):
        # Three pages with no file between them: no root configured, a root
        # that is not there yet, and a root holding nothing. A viewer opened
        # before Claude Code first ran sits on the middle one.
        self.own_fixture()
        absent = self.tmp / "not-yet"
        before = self.digest(absent)
        absent.mkdir()

        self.assertNotEqual(before, self.digest(absent))

    def test_a_reader_with_no_transcript_root_reads_no_tree_for_its_tag(self):
        # The unconfigured case contributes that it is unconfigured and
        # nothing else -- there is no path it could have walked.
        self.assertEqual((("transcripts", 0, ""),), ui.transcript_state(None))

    # Every route that renders no transcript at all. On a host with a live
    # Claude Code session -- the normal case, and the case this viewer is
    # opened for -- the transcript root is rewritten every second.
    ORCH_ONLY = ("/", ui.FRICTION_ROUTE, graph_url("run-gamma"), detail_url("run-gamma", "G1"))

    def rename_a_transcript(self):
        (self.transcripts / ALPHA_PROJECT / (TITLED_SESSION + ".jsonl")).write_text(
            '{"type":"ai-title","aiTitle":"Alpha, renamed"}\n', encoding="utf-8"
        )

    def tags(self, routes) -> dict:
        return dict(
            (route, ui.entity_tag(self.main, route, None, self.transcripts))
            for route in routes
        )

    def bodies(self, routes) -> dict:
        return dict(
            (route, ui.render_route(self.main, route, self.transcripts)[1])
            for route in routes
        )

    def test_a_route_that_renders_no_transcript_holds_its_tag_across_a_write(self):
        # The basis is the route's read set, which is `U3`'s lesson in both
        # directions: too narrow serves a 304 to a page that moved, and too
        # wide denies the 304 to a page that did not. Too wide is what a
        # live session makes permanent -- the poll then swaps `main` once a
        # second over a byte-identical body, churning scroll and focus.
        self.own_fixture()
        with frozen_clock():
            before, drawn = self.tags(self.ORCH_ONLY), self.bodies(self.ORCH_ONLY)
            self.rename_a_transcript()

            self.assertEqual(before, self.tags(self.ORCH_ONLY))
            self.assertEqual(drawn, self.bodies(self.ORCH_ONLY))

    def test_the_session_routes_still_see_the_write_the_others_ignore(self):
        # Otherwise the narrowing above is satisfied by a validator that
        # observes the transcript tree nowhere at all.
        self.own_fixture()
        polled = (ui.SESSIONS_ROUTE, session_url(TITLED_SESSION))
        with frozen_clock():
            before = self.tags(polled)
            self.rename_a_transcript()
            after = self.tags(polled)

        for route in polled:
            self.assertNotEqual(before[route], after[route], route)

    def test_an_orch_page_is_answered_304_while_a_session_writes(self):
        self.own_fixture()
        with frozen_clock():
            with serving(self.main, self.transcripts) as server:
                status, headers, _body = fetch(server, ui.FRICTION_ROUTE)
                self.assertEqual(200, status)
                held = {"If-None-Match": headers["ETag"]}
                self.rename_a_transcript()
                status, _headers, body = fetch(server, ui.FRICTION_ROUTE, held)

        self.assertEqual(304, status)
        self.assertEqual("", body)

    def test_the_poll_is_not_answered_304_after_a_transcript_moves(self):
        self.own_fixture()
        with serving(self.main, self.transcripts) as server:
            status, headers, _body = fetch(server, ui.SESSIONS_ROUTE)
            self.assertEqual(200, status)
            tag = headers["ETag"]
            held = {"If-None-Match": tag}
            self.assertEqual(304, fetch(server, ui.SESSIONS_ROUTE, held)[0])

            (self.transcripts / ALPHA_PROJECT / (TITLED_SESSION + ".jsonl")).write_text(
                '{"type":"ai-title","aiTitle":"Alpha, renamed"}\n', encoding="utf-8"
            )

            status, _headers, body = fetch(server, ui.SESSIONS_ROUTE, held)

        self.assertEqual(200, status)
        self.assertIn("Alpha, renamed", session_cell(body, TITLED_SESSION, "title"))


class TestAbsentTranscriptRoot(TranscriptCase):
    """`S1` completion test 9, spec criterion 16."""

    def missing(self) -> Path:
        absent = self.tmp / "no-transcripts-here"
        self.assertFalse(absent.exists())
        return absent

    def test_every_pre_existing_route_still_answers(self):
        with serving(self.main, self.missing()) as server:
            served = {}
            for route in every_route():
                served[route] = get(server, route)

        self.assertEqual({200, 404}, set(status for status, _ in served.values()))
        self.assertIn(SETTLED_RUN, served["/"][1])

    def test_the_session_index_names_an_empty_state(self):
        page = self.sessions(self.missing())

        self.assertIn(ui.EMPTY_NO_TRANSCRIPTS, block_for(page, "empty", "</p>"))
        self.assertEqual([], session_ids(page))

    def test_a_present_but_sessionless_root_is_a_different_empty_state(self):
        self.own_fixture()
        bare = self.tmp / "bare"
        bare.mkdir()

        page = self.sessions(bare)

        self.assertIn(ui.EMPTY_NO_SESSIONS, block_for(page, "empty", "</p>"))

    def test_a_root_the_host_will_not_answer_for_is_not_an_absent_root(self):
        # "no transcript root at this path" is a fact about the path. A
        # listing the host refused is a fact about this poll, and the
        # operator can act on exactly one of them.
        with patch.object(Path, "is_dir", side_effect=OSError("gone")):
            found = ui.discover_sessions(self.transcripts)

        self.assertIn(ui.DIAGNOSTIC_UNREADABLE, " ".join(found["diagnostics"]))
        self.assertIn(ui.DIAGNOSTIC_UNREADABLE, ui.render_sessions(found))

    def test_a_session_file_that_will_not_stat_is_named_rather_than_dropped(self):
        with patch.object(ui, "_stat_identity", return_value=None):
            found = ui.discover_sessions(self.transcripts)

        self.assertEqual([], found["sessions"])
        self.assertIn(ui.DIAGNOSTIC_UNREADABLE, " ".join(found["diagnostics"]))

    def test_a_healthy_root_carries_no_such_diagnostic(self):
        found = ui.discover_sessions(self.transcripts)

        self.assertNotIn(ui.DIAGNOSTIC_UNREADABLE, " ".join(found["diagnostics"]))
