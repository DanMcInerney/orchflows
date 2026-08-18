"""Session escaping, cache, empty-state, timestamp, content-wall, and read-only regressions."""

from tests.test_ui_cases._transcript_support import *  # noqa: F401,F403
from tests.test_ui_cases.transcript_containment import SessionCase
class TestSessionEscaping(SessionCase):
    """`S2` completion test 6, spec criterion 15. Every value on this page
    is another program's undocumented JSON, and it reaches three contexts:
    a table cell, an SVG text node, and an attribute."""

    def markup(self) -> str:
        return self.flowchart(MARKUP_SESSION)

    def test_the_fixture_really_carries_markup_in_all_three_fields(self):
        # Without this the assertions below sweep a page that never had
        # anything on it to escape.
        source = self.subagents(MARKUP_SESSION) / (MARKUP_AGENT + ".meta.json")
        recorded = json.loads(source.read_text(encoding="utf-8"))
        transcript = self.transcripts / BETA_PROJECT / (MARKUP_SESSION + ".jsonl")

        self.assertEqual(MARKUP_AGENT_TYPE, recorded["agentType"])
        self.assertEqual(MARKUP_AGENT_DESCRIPTION, recorded["description"])
        self.assertIn(PAYLOAD, transcript.read_text(encoding="utf-8"))

    def test_none_of_the_three_reaches_the_page_as_markup(self):
        page = self.markup()

        self.assertNotIn(PAYLOAD, page)
        self.assertNotIn('onerror="alert(1)"', page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)

    def test_the_agent_type_is_escaped_in_the_cell_and_in_the_svg_text_node(self):
        page = self.markup()
        node = session_node(page, MARKUP_AGENT)

        self.assertIn("&lt;script&gt;", session_cell(page, MARKUP_AGENT, "type"))
        self.assertIn("&lt;", node["body"])
        self.assertNotIn("<script", node["body"])

    def test_the_description_is_escaped_in_the_attribute_it_is_carried_in(self):
        # An unescaped quote here closes `aria-label` early and everything
        # after it becomes attributes of the anchor.
        node = session_node(self.markup(), MARKUP_AGENT)

        self.assertIn("&quot;", node["label"])
        self.assertNotIn("onerror", node["label"].split("&quot;")[0])
        self.assertIn(
            "&lt;img src=&quot;x&quot;",
            session_cell(self.markup(), MARKUP_AGENT, "description"),
        )

    def test_the_session_title_is_escaped_in_the_heading_and_in_the_svg_label(self):
        page = self.markup()

        self.assertIn("&lt;script&gt;", block_for(page, "title", "</p>"))
        self.assertIn("&lt;script&gt;", session_node(page, ui.ORCHESTRATOR_ANCHOR)["label"])

    def test_removing_the_escaping_breaks_every_assertion_above(self):
        # The guards are only worth what their mutation says they are: with
        # `html.escape` neutered the same page carries the live payload in
        # all three contexts.
        with patch.object(ui.html, "escape", lambda value, quote=True: value):
            page = self.markup()

        self.assertIn(PAYLOAD, page)
        self.assertIn('onerror="alert(1)"', page)
        self.assertIn("<script>alert(1)</script>", block_for(page, "title", "</p>"))


class TestSessionLayoutCache(SessionCase):
    """`S2` completion test 7. `U3`'s cache, and `U3`'s reason: at a
    one-second poll a layout recomputed for a picture that did not move is
    paid for once a second forever. A second layout algorithm in this module
    would be the same defect wearing a different name."""

    def setUp(self):
        super(TestSessionLayoutCache, self).setUp()
        ui.LAYOUT_CACHE.clear()
        self.addCleanup(ui.LAYOUT_CACHE.clear)

    @contextlib.contextmanager
    def counting(self):
        with patch.object(ui, "graph_layout", side_effect=ui.graph_layout) as computed:
            yield computed

    def test_two_requests_over_an_unchanged_subagent_set_lay_out_exactly_once(self):
        with self.counting() as computed:
            first = self.flowchart()
            second = self.flowchart()

        self.assertEqual(1, computed.call_count)
        self.assertEqual(first, second)
        # The counter can reach two, so one is a measurement rather than a
        # mock that was never wired to anything.
        with self.counting() as recomputed:
            ui.LAYOUT_CACHE.clear()
            self.flowchart()
            ui.LAYOUT_CACHE.clear()
            self.flowchart()

        self.assertEqual(2, recomputed.call_count)

    def test_an_activity_change_repaints_without_laying_the_graph_out_again(self):
        self.own_fixture()
        path = self.transcripts / ALPHA_PROJECT / (TITLED_SESSION + ".jsonl")
        with self.counting() as computed:
            before = self.flowchart()
            with path.open("a", encoding="utf-8") as handle:
                handle.write(
                    '{"type":"user","message":{"role":"user","content":'
                    '[{"type":"tool_result","tool_use_id":"toolu_alpha_02",'
                    '"content":"%s"}]}}\n' % TRANSCRIPT_SENTINEL
                )
            after = self.flowchart()

        self.assertEqual(1, computed.call_count)
        self.assertEqual("nd-running", session_node(before, CALLED_AGENT)["state"])
        self.assertEqual("nd-finished", session_node(after, CALLED_AGENT)["state"])

    def test_a_subagent_appearing_does_lay_the_graph_out_again(self):
        self.own_fixture()
        with self.counting() as computed:
            self.flowchart()
            (self.subagents(TITLED_SESSION) / "agent-aa14.meta.json").write_text(
                '{"agentType":"Plan","spawnDepth":1}', encoding="utf-8"
            )
            page = self.flowchart()

        self.assertEqual(2, computed.call_count)
        self.assertIn("agent-aa14", session_anchors(page))

    def test_the_run_graph_and_the_flowchart_share_the_one_cache(self):
        self.flowchart()
        ui.render_route(self.main, graph_url(SETTLED_RUN))

        self.assertEqual(2, len(ui.LAYOUT_CACHE))

    def test_one_layout_function_serves_both_views(self):
        # The structural half of the claim above: a private copy of the
        # algorithm would pass every count in this class.
        calls = set()
        for node in ast.walk(ast.parse(UI_PY.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.FunctionDef):
                continue
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                    if inner.func.id in ("graph_layout", "cached_layout"):
                        calls.add((node.name, inner.func.id))

        self.assertEqual(
            {("cached_layout", "graph_layout")},
            set(call for call in calls if call[1] == "graph_layout"),
        )
        self.assertEqual(
            {"render_graph", "render_session"},
            set(call[0] for call in calls if call[1] == "cached_layout"),
        )


class TestSessionEmptyStates(SessionCase):
    """`S2` completion test 8. A session that spawned nothing is the common
    case on a real host, and an id that names no session is one keystroke
    away from every id that does."""

    def test_a_session_that_spawned_nothing_draws_the_orchestrator_alone(self):
        page = self.flowchart(UNTITLED_SESSION)

        self.assertEqual([ui.ORCHESTRATOR_ANCHOR], session_anchors(page))
        self.assertEqual([], EDGE_RE.findall(page))
        self.assertIn(ui.EMPTY_NO_AGENTS, block_for(page, "agents empty", "</p>"))

    def test_an_unknown_session_id_is_a_named_404_rather_than_a_traceback(self):
        status, page = ui.render_route(
            self.main, session_url("no-such-session"), self.transcripts
        )

        self.assertEqual(404, status)
        self.assertIn(ui.EMPTY_NO_SESSION, page)
        self.assertIn("no-such-session", page)

    def test_an_id_that_is_not_a_name_at_all_is_refused_the_same_way(self):
        for identifier in ("", "..", "../" + TITLED_SESSION, "a/b", PAYLOAD):
            status, page = ui.render_route(
                self.main, "/session?id=" + identifier, self.transcripts
            )

            self.assertEqual(404, status, identifier)
            self.assertNotIn(PAYLOAD, page, identifier)

    def test_a_traversal_shaped_id_is_refused_before_any_directory_is_read(self):
        # The listing would refuse it too, by never matching -- so without
        # this the guard is untested and its removal changes no page. It is
        # here to keep a query-string value from reaching the filesystem at
        # all, and that is a claim about what was read, not what was drawn.
        with patch.object(ui, "discover_sessions") as listed:
            found = ui.find_session(self.transcripts, "../" + TITLED_SESSION)

        self.assertIsNone(found)
        listed.assert_not_called()

    def test_no_transcript_root_configured_reads_nothing_and_says_so(self):
        with patch.object(ui, "_transcript_summary") as parsed:
            status, page = ui.render_route(self.main, session_url(TITLED_SESSION), None)

        parsed.assert_not_called()
        self.assertEqual(404, status)
        self.assertIn(ui.EMPTY_NO_SESSION, page)

    def test_metadata_that_cannot_be_read_still_draws_its_node_and_says_so(self):
        page = self.flowchart(MARKUP_SESSION)

        self.assertIn(UNREADABLE_AGENT, session_anchors(page))
        self.assertIn(
            ui.DIAGNOSTIC_UNREADABLE_AGENT, block_for(page, "diagnostics", "</ul>")
        )

    def test_a_field_of_the_wrong_type_is_a_named_absence_rather_than_a_value(self):
        page = self.flowchart(MARKUP_SESSION)

        self.assertIn(ui.EMPTY_NO_TYPE, session_cell(page, BAD_FIELDS_AGENT, "type"))
        self.assertIn(
            ui.EMPTY_NO_DESCRIPTION, session_cell(page, BAD_FIELDS_AGENT, "description")
        )
        self.assertIn(ui.EMPTY_NO_DEPTH, session_cell(page, BAD_FIELDS_AGENT, "depth"))
        self.assertEqual(
            "nd-" + ui.ACTIVITY_UNKNOWN, session_node(page, BAD_FIELDS_AGENT)["state"]
        )


class TestUnrenderableTimestamps(SessionCase):
    """Spec criterion 12 over the one field that comes from the filesystem
    rather than from a transcript. `U3` shipped a traceback in the handler
    once already: the client gets no HTTP response at all and the absolute
    module path goes to stderr. A stamp is the remaining door."""

    def test_a_time_beyond_the_calendar_is_a_named_diagnostic_not_a_raise(self):
        # APFS clamps at 2262 and cannot reach this; an NTFS FILETIME
        # reaches the year 30828, so the Windows leg can.
        self.assertEqual(
            ui.DIAGNOSTIC_UNRENDERABLE_STAMP, ui._stamp(FAR_FUTURE_MTIME_NS)
        )

    def test_an_ordinary_time_is_untouched_by_the_guard(self):
        # Otherwise the assertion above is satisfied by a stamp that never
        # renders anything.
        self.assertEqual(utc_stamp(SESSION_EPOCH), ui._stamp(SESSION_EPOCH * 1000000000))

    def test_both_session_routes_still_answer_over_such_a_file(self):
        with far_future_mtimes():
            with serving(self.main, self.transcripts) as server:
                index = get(server, ui.SESSIONS_ROUTE)
                detail = get(server, session_url(TITLED_SESSION))

        self.assertEqual(200, index[0])
        self.assertEqual(200, detail[0])
        self.assertIn(
            ui.DIAGNOSTIC_UNRENDERABLE_STAMP,
            session_cell(index[1], TITLED_SESSION, "when"),
        )
        self.assertIn(
            ui.DIAGNOSTIC_UNRENDERABLE_STAMP,
            session_cell(detail[1], RETURNED_AGENT, "when"),
        )


class TestSubagentContentWall(SessionCase):
    """`S2`'s half of spec criterion 10. The flowchart reads the one file
    the index does not, and the evidence it reads the activity off is a
    prompt -- the single most sensitive thing in the tree."""

    def test_the_flowchart_emits_only_the_fields_the_spec_admits(self):
        # Named here so widening the row is a decision rather than a slip.
        self.assertEqual(
            ("agent", "type", "description", "depth", "state", "attached", "when"),
            ui.AGENT_COLUMNS,
        )
        self.assertEqual(len(ui.AGENT_COLUMNS), len(ui.AGENT_HEADINGS))

    def test_the_rendered_row_carries_exactly_the_closed_set(self):
        # `agentType`, `description`, `toolUseId` and `spawnDepth` are the
        # whole of what a subagent's metadata may render. An eighth cell is
        # a field off a transcript, and the tuple above would not see it.
        page = self.flowchart()

        for agent in ALPHA_AGENTS:
            self.assertEqual(list(ui.AGENT_COLUMNS), row_columns(page, agent), agent)

    def test_narrowing_the_closed_set_narrows_the_row_it_renders(self):
        with patch.object(ui, "AGENT_COLUMNS", ("agent", "type")):
            page = self.flowchart()

        self.assertEqual(["agent", "type"], row_columns(page, RETURNED_AGENT))

    def test_no_flowchart_in_the_corpus_leaks_a_line_of_any_transcript(self):
        for session in SESSIONS_NEWEST_FIRST:
            status, page = ui.render_route(
                self.main, session_url(session), self.transcripts
            )

            self.assertEqual(200, status, session)
            self.assertNotIn(TRANSCRIPT_SENTINEL, page, session)

    def test_the_state_is_read_off_a_prompt_the_page_never_shows(self):
        # The `Agent` call carrying `toolu_alpha_01` holds the subagent's
        # whole prompt. What comes off it is one word.
        page = self.flowchart()

        self.assertIn(ui.ACTIVITY_FINISHED, session_cell(page, RETURNED_AGENT, "state"))
        self.assertIn(TRANSCRIPT_SENTINEL, (self.transcripts / ALPHA_PROJECT / (
            TITLED_SESSION + ".jsonl")).read_text(encoding="utf-8"))
        self.assertNotIn(TRANSCRIPT_SENTINEL, page)

    def test_the_sweep_still_renders_what_it_is_allowed_to(self):
        # The sweep above would also pass on a page that rendered nothing.
        page = self.flowchart()

        self.assertIn("orch-worker", session_cell(page, RETURNED_AGENT, "type"))
        self.assertEqual(1 + len(ALPHA_AGENTS), len(session_anchors(page)))

    def test_a_subagents_own_transcript_is_listed_and_never_opened(self):
        opened = []
        real = Path.open

        def watching(self, *args, **kwargs):
            opened.append(self.name)
            return real(self, *args, **kwargs)

        with patch.object(Path, "open", watching):
            self.flowchart()

        self.assertNotIn(RETURNED_AGENT + ".jsonl", opened)
        self.assertIn(TITLED_SESSION + ".jsonl", opened)


class TestSessionRouteIsReadOnly(SessionCase):
    """`S2` completion test 10, spec criterion 11 over the routes this
    ticket adds."""

    def test_drawing_every_flowchart_writes_nothing_under_the_transcript_root(self):
        before = snapshot(self.transcripts)
        self.assertTrue(before)

        with serving(self.main, self.transcripts) as server:
            for session in SESSIONS_NEWEST_FIRST:
                status, _headers, body = fetch(server, session_url(session))

                self.assertEqual(200, status, session)
                self.assertTrue(body, session)

        self.assertEqual(before, snapshot(self.transcripts))


if __name__ == "__main__":
    unittest.main()
