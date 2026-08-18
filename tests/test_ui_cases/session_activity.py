"""Session activity and polling regressions."""

from tests.test_ui_cases._transcript_support import *  # noqa: F401,F403
from tests.test_ui_cases.transcript_containment import SessionCase
class TestActivityState(SessionCase):
    """`S2` completion test 4, spec criterion 9. `running` is a claim about
    a process this reader cannot see, and the only evidence of one anywhere
    in the tree is the call and the return in the parent's own transcript."""

    def states(self, session=TITLED_SESSION) -> dict:
        return dict((agent["id"], agent["state"]) for agent in self.read(session)["agents"])

    def test_a_call_whose_result_came_back_is_the_only_thing_read_as_finished(self):
        page = self.flowchart()

        self.assertEqual(ui.ACTIVITY_FINISHED, self.states()[RETURNED_AGENT])
        self.assertIn(ui.ACTIVITY_FINISHED, session_cell(page, RETURNED_AGENT, "state"))
        self.assertIn(ui.EVIDENCE_RETURNED, session_cell(page, RETURNED_AGENT, "state"))

    def test_a_call_with_no_result_yet_is_read_as_running(self):
        page = self.flowchart()

        self.assertEqual(ui.ACTIVITY_RUNNING, self.states()[CALLED_AGENT])
        self.assertIn(ui.ACTIVITY_RUNNING, session_cell(page, CALLED_AGENT, "state"))
        self.assertIn(ui.EVIDENCE_CALLED, session_cell(page, CALLED_AGENT, "state"))

    def test_an_agent_the_transcript_never_calls_is_unknown_with_its_last_time(self):
        page = self.flowchart()

        self.assertEqual(ui.ACTIVITY_UNKNOWN, self.states()[UNEVIDENCED_AGENT])
        self.assertIn(ui.EVIDENCE_NONE, session_cell(page, UNEVIDENCED_AGENT, "state"))
        self.assertIn(
            agent_stamp(UNEVIDENCED_AGENT), session_cell(page, UNEVIDENCED_AGENT, "when")
        )

    def test_a_subagent_whose_files_will_not_stat_is_not_dated_at_the_epoch(self):
        # `read_agents` takes a subagent's last activity off its files' mtimes;
        # a file the path layer will not describe used to leave that at 0,
        # which `_stamp` draws as 1970-01-01 -- a real-looking time for a
        # read that failed. The listing above already names a *session* file
        # that will not stat; this is the same failure one level down.
        real = ui._stat_identity

        def refused_under_subagents(path):
            return None if "subagents" in path.parts else real(path)

        with patch.object(ui, "_stat_identity", refused_under_subagents):
            page = self.flowchart()

        cell = session_cell(page, UNEVIDENCED_AGENT, "when")
        self.assertIn(ui.DIAGNOSTIC_UNREADABLE, cell)
        self.assertNotIn("1970-01-01", cell)

    def test_a_tool_call_that_is_not_an_agent_call_is_evidence_of_nothing(self):
        # `toolu_alpha_03` is `agent-aa13`'s id, and the transcript carries a
        # `Bash` call and a `Bash` result under it. A reader matching on the
        # id alone reads a finished shell command as a finished subagent.
        found = ui.find_session(self.transcripts, TITLED_SESSION)
        summary = ui.cached_transcript(found["path"], found["identity"])

        self.assertIn("toolu_alpha_03", found["path"].read_text(encoding="utf-8"))
        self.assertEqual({"toolu_alpha_01", "toolu_alpha_02"}, set(summary["agent_calls"]))
        self.assertEqual({"toolu_alpha_01"}, set(summary["agent_returns"]))

    def test_no_agent_in_the_corpus_is_running_without_a_call_behind_it(self):
        running = 0
        for session in SESSIONS_NEWEST_FIRST:
            found = self.read(session)
            calls = ui.cached_transcript(found["path"], found["identity"])["agent_calls"]
            for agent in found["agents"]:
                if agent["state"] != ui.ACTIVITY_UNKNOWN:
                    running += 1
                    self.assertIn(agent["tool_use_id"], calls, agent["id"])
        # Six sessions of `unknown` would satisfy the sweep above and prove
        # nothing at all.
        self.assertEqual(2, running)

    def test_no_agent_defaults_to_finished_when_no_result_was_recorded(self):
        # Every `tool_result` gone, and the calls left standing: nothing on
        # the page may still read as done.
        self.own_fixture()
        path = self.transcripts / ALPHA_PROJECT / (TITLED_SESSION + ".jsonl")
        path.write_text(
            "".join(
                line
                for line in path.read_text(encoding="utf-8").splitlines(True)
                if "tool_result" not in line
            ),
            encoding="utf-8",
        )
        states = self.states()

        self.assertNotIn(ui.ACTIVITY_FINISHED, states.values())
        self.assertEqual(ui.ACTIVITY_RUNNING, states[RETURNED_AGENT])
        self.assertEqual(ui.ACTIVITY_UNKNOWN, states[UNEVIDENCED_AGENT])

    def test_a_result_for_a_call_that_never_happened_is_not_a_finished_agent(self):
        self.own_fixture()
        path = self.transcripts / ALPHA_PROJECT / (TITLED_SESSION + ".jsonl")
        path.write_text(
            "".join(
                line
                for line in path.read_text(encoding="utf-8").splitlines(True)
                if '"name":"Agent"' not in line
            ),
            encoding="utf-8",
        )
        found = ui.find_session(self.transcripts, TITLED_SESSION)
        summary = ui.cached_transcript(found["path"], found["identity"])

        self.assertEqual(set(), set(summary["agent_returns"]))
        self.assertEqual({ui.ACTIVITY_UNKNOWN}, set(self.states().values()))

    def test_the_node_is_drawn_in_the_state_its_row_reports(self):
        page = self.flowchart()

        self.assertEqual("nd-running", session_node(page, CALLED_AGENT)["state"])
        self.assertIn(ui.ACTIVITY_RUNNING, session_node(page, CALLED_AGENT)["body"])
        self.assertIn(ui.ACTIVITY_FINISHED, session_node(page, RETURNED_AGENT)["body"])
        self.assertIn(ui.ACTIVITY_UNKNOWN, session_node(page, UNEVIDENCED_AGENT)["body"])

    def test_every_state_the_view_can_draw_has_a_declared_presentation(self):
        # `U2`'s hue tokens are a closed set, so a state drawn in a colour
        # family the stylesheet does not declare renders as nothing at all.
        for state in ui.ACTIVITY_STATES:
            seen = ui.activity_presentation(state)

            self.assertIn(seen.hue, ui.HUE_TOKENS, state)
            self.assertTrue(seen.glyph, state)
            self.assertEqual(state, seen.word)
            self.assertIn(".st-{0} {{".format(state), ui.PAGE_CSS)
            self.assertIn(".nd-{0} rect {{".format(state), ui.PAGE_CSS)


class TestSessionPolling(SessionCase):
    """`S2` completion test 5, spec criterion 14. The flowchart is the page
    an orchestrator leaves open while the work it is watching runs."""

    def setUp(self):
        super(TestSessionPolling, self).setUp()
        # The fixtures also carry a live elapsed meter, which honestly moves
        # the tag on each minute boundary.
        freeze(self)

    def polled(self) -> tuple:
        return (ui.SESSIONS_ROUTE, session_url(TITLED_SESSION))

    def test_both_session_routes_answer_304_over_an_unchanged_root(self):
        with serving(self.main, self.transcripts) as server:
            for route in self.polled():
                status, headers, body = fetch(server, route)
                self.assertEqual(200, status, route)
                self.assertTrue(body, route)

                again = fetch(server, route, {"If-None-Match": headers["ETag"]})

                self.assertEqual((304, ""), (again[0], again[2]), route)

    def test_a_subagent_appearing_answers_200_with_a_new_tag_on_both(self):
        self.own_fixture()
        with serving(self.main, self.transcripts) as server:
            held = dict(
                (route, fetch(server, route)[1]["ETag"]) for route in self.polled()
            )
            (self.subagents(TITLED_SESSION) / "agent-aa14.meta.json").write_text(
                '{"agentType":"Plan","description":"just spawned",'
                '"toolUseId":"toolu_alpha_04","spawnDepth":1}',
                encoding="utf-8",
            )
            served = dict(
                (route, fetch(server, route, {"If-None-Match": held[route]}))
                for route in self.polled()
            )

        for route in self.polled():
            status, headers, _body = served[route]
            self.assertEqual(200, status, route)
            self.assertNotEqual(held[route], headers["ETag"], route)
        self.assertIn("agent-aa14", session_anchors(served[self.polled()[1]][2]))

    def test_a_subagent_returning_answers_200_with_a_new_tag(self):
        # The node set has not moved and the picture has: an ETag over the
        # listing alone would sit on a page that says `running` forever.
        self.own_fixture()
        path = self.transcripts / ALPHA_PROJECT / (TITLED_SESSION + ".jsonl")
        route = session_url(TITLED_SESSION)
        with serving(self.main, self.transcripts) as server:
            held = {"If-None-Match": fetch(server, route)[1]["ETag"]}
            with path.open("a", encoding="utf-8") as handle:
                handle.write(
                    '{"type":"user","message":{"role":"user","content":'
                    '[{"type":"tool_result","tool_use_id":"toolu_alpha_02",'
                    '"content":"%s"}]}}\n' % TRANSCRIPT_SENTINEL
                )
            status, _headers, body = fetch(server, route, held)

        self.assertEqual(200, status)
        self.assertEqual("nd-finished", session_node(body, CALLED_AGENT)["state"])

    def test_one_session_never_answers_another_sessions_tag(self):
        with serving(self.main, self.transcripts) as server:
            first = fetch(server, session_url(TITLED_SESSION))[1]["ETag"]
            other = fetch(server, session_url(MARKUP_SESSION))
            status, _headers, body = fetch(
                server, session_url(MARKUP_SESSION), {"If-None-Match": first}
            )

        self.assertNotEqual(first, other[1]["ETag"])
        self.assertEqual(200, status)
        self.assertIn(MARKUP_SESSION, body)

    def test_a_missing_session_offers_no_tag_to_be_cached_against(self):
        with serving(self.main, self.transcripts) as server:
            status, headers, _body = fetch(server, session_url("no-such-session"))

        self.assertEqual(404, status)
        self.assertIsNone(headers.get("ETag"))


