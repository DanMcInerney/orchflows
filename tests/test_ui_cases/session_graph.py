"""Session route, flowchart, and subagent-edge regressions."""

from tests.test_ui_cases._transcript_support import *  # noqa: F401,F403
from tests.test_ui_cases.transcript_containment import SessionCase
class TestSessionRoute(SessionCase):
    """`S2` completion test 9. `U1`'s tuple is what makes the read-only,
    no-network, escaping and conditional-request guards sweep a route."""

    def test_the_route_is_declared_and_carries_concrete_examples(self):
        self.assertIn(ui.SESSION_ROUTE, ui.ROUTES)
        self.assertTrue(ROUTE_EXAMPLES[ui.SESSION_ROUTE])
        for url in ROUTE_EXAMPLES[ui.SESSION_ROUTE]:
            self.assertIn(url, every_route(), url)

    def test_the_examples_reach_a_drawn_flowchart_and_not_only_its_errors(self):
        served = [
            ui.render_route(self.main, url, self.transcripts)[0]
            for url in ROUTE_EXAMPLES[ui.SESSION_ROUTE]
        ]

        self.assertIn(200, served)
        self.assertIn(404, served)

    def test_the_session_index_links_each_row_to_its_own_flowchart(self):
        # `S1` left the id unlinked deliberately: there was nowhere to go.
        page = self.sessions()

        self.assertIn('href="/session?id={0}"'.format(TITLED_SESSION), page)
        self.assertEqual(list(SESSIONS_NEWEST_FIRST), session_ids(page))


class TestSessionFlowchart(SessionCase):
    """`S2` completion test 2, spec criterion 8."""

    def test_one_node_for_the_orchestrator_and_one_for_each_subagent(self):
        drawn = session_anchors(self.flowchart())

        self.assertEqual(
            sorted(ALPHA_AGENTS + (ui.ORCHESTRATOR_ANCHOR,)), sorted(drawn)
        )

    def test_the_node_set_is_the_metadata_files_and_not_the_agent_transcripts(self):
        # `agent-aa11.jsonl` sits beside `agent-aa11.meta.json`; two files
        # about one subagent must not draw two nodes.
        subagents = self.transcripts / ALPHA_PROJECT / TITLED_SESSION / "subagents"
        drawn = session_anchors(self.flowchart())

        self.assertEqual(4, len(list(subagents.glob("agent-*"))))
        self.assertEqual(len(set(drawn)), len(drawn))
        self.assertEqual(1 + len(ALPHA_AGENTS), len(drawn))

    def test_each_node_carries_its_type_description_and_depth(self):
        page = self.flowchart()

        self.assertIn("orch-worker", session_cell(page, RETURNED_AGENT, "type"))
        self.assertIn(
            "Implement the session index",
            session_cell(page, RETURNED_AGENT, "description"),
        )
        self.assertIn("1", session_cell(page, RETURNED_AGENT, "depth"))
        self.assertIn("2", session_cell(page, UNEVIDENCED_AGENT, "depth"))
        self.assertIn("Explore", session_cell(page, UNEVIDENCED_AGENT, "type"))

    def test_the_drawn_node_names_the_agent_rather_than_only_its_row(self):
        # A table under an anonymous picture is not a flowchart of anything.
        node = session_node(self.flowchart(), RETURNED_AGENT)

        self.assertIn("orch-worker", node["body"])
        self.assertIn("orch-worker", node["label"])
        self.assertIn("Implement the session index", node["label"])

    def test_the_orchestrator_node_names_itself_and_what_it_spawned(self):
        node = session_node(self.flowchart(), ui.ORCHESTRATOR_ANCHOR)

        self.assertIn("orchestrator", node["body"])
        self.assertIn("3", node["body"])
        self.assertIn(LAST_AI_TITLE, node["label"])

    def test_every_depth_one_agent_is_drawn_from_the_orchestrator(self):
        nodes, edges, _inferred = self.graph()

        self.assertIn(ui.ORCHESTRATOR_NODE, nodes)
        self.assertIn((ui.ORCHESTRATOR_NODE, RETURNED_AGENT), edges)
        self.assertIn((ui.ORCHESTRATOR_NODE, CALLED_AGENT), edges)
        self.assertEqual(len(nodes) - 1, len(edges))

    def test_the_page_names_the_session_it_drew(self):
        page = self.flowchart()

        self.assertIn(TITLED_SESSION, page)
        self.assertIn(LAST_AI_TITLE, page)
        self.assertIn("/Users/dmcinerney/tools/alpha", page)


class TestSubagentEdges(SessionCase):
    """`S2` completion test 3. Most subagent metadata records no parent at
    all, so most of this tree is a guess -- and a guess drawn like a fact is
    the one failure a flowchart of somebody else's process can commit."""

    def test_a_depth_two_agent_with_no_recorded_parent_hangs_off_the_root(self):
        # There is nowhere else to hang it: depth says a parent exists and
        # nothing says which agent it is.
        _nodes, edges, inferred = self.graph()

        self.assertIn((ui.ORCHESTRATOR_NODE, UNEVIDENCED_AGENT), edges)
        self.assertEqual(((ui.ORCHESTRATOR_NODE, UNEVIDENCED_AGENT),), tuple(inferred))

    def test_that_edge_is_dashed_and_the_page_says_what_a_dashed_edge_means(self):
        page = self.flowchart()

        self.assertEqual(1, len(INFERRED_EDGE_RE.findall(page)))
        self.assertEqual(len(ALPHA_AGENTS), len(EDGE_RE.findall(page)))
        self.assertIn(
            ui.DIAGNOSTIC_INFERRED_EDGE, block_for(page, "diagnostics", "</ul>")
        )

    def test_each_row_names_what_its_agent_hangs_off_and_how_that_was_known(self):
        page = self.flowchart()
        proven = session_cell(page, RETURNED_AGENT, "attached")
        guessed = session_cell(page, UNEVIDENCED_AGENT, "attached")

        self.assertIn(ui.EDGE_FROM_DEPTH, proven)
        self.assertNotIn(ui.EDGE_INFERRED, proven)
        self.assertIn(ui.EDGE_INFERRED, guessed)

    def test_an_unprovable_depth_two_agent_still_says_it_is_at_depth_two(self):
        # It cannot be nested under anything: nothing records what. Its
        # depth is on the node's own face as well as on its row, so the
        # picture does not read as three siblings of equal standing.
        page = self.flowchart()

        self.assertIn("d2", session_node(page, UNEVIDENCED_AGENT)["body"])
        self.assertIn("depth 2", session_node(page, UNEVIDENCED_AGENT)["label"])
        self.assertIn("2", session_cell(page, UNEVIDENCED_AGENT, "depth"))

    def test_a_recorded_parent_attaches_the_child_to_that_agent_as_a_fact(self):
        _nodes, edges, inferred = self.graph(TRUNCATED_SESSION)

        self.assertIn((ui.ORCHESTRATOR_NODE, PARENT_AGENT), edges)
        self.assertIn((PARENT_AGENT, CHILD_AGENT), edges)
        self.assertNotIn((ui.ORCHESTRATOR_NODE, CHILD_AGENT), edges)
        self.assertEqual((), tuple(inferred))

    def test_the_recorded_child_is_drawn_a_layer_below_its_own_parent(self):
        # Nesting is the picture, not the prose: a child drawn beside its
        # parent is not nested however its row reads.
        nodes, edges, _inferred = self.graph(TRUNCATED_SESSION)
        layers = dict(
            (node.id, node.layer) for node in ui.cached_layout(nodes, edges)["nodes"]
        )

        self.assertEqual(0, layers[ui.ORCHESTRATOR_NODE])
        self.assertEqual(1, layers[PARENT_AGENT])
        self.assertEqual(2, layers[CHILD_AGENT])

    def test_a_parent_pointer_naming_nobody_falls_back_to_an_inferred_edge(self):
        # The pointer's spelling is undocumented and observed, never
        # promised: one that resolves to no sibling is not a node.
        self.own_fixture()
        meta = self.subagents(TRUNCATED_SESSION) / (CHILD_AGENT + ".meta.json")
        meta.write_text(
            '{"agentType":"Explore","spawnDepth":2,"parentAgentId":"nobody"}',
            encoding="utf-8",
        )
        _nodes, edges, inferred = self.graph(TRUNCATED_SESSION)

        self.assertIn((ui.ORCHESTRATOR_NODE, CHILD_AGENT), edges)
        self.assertEqual(((ui.ORCHESTRATOR_NODE, CHILD_AGENT),), tuple(inferred))

    # The three shapes a recorded `parentAgentId` takes that resolve to no
    # node on the page: a stranger, the agent itself, and the orchestrator,
    # which no subagent's metadata is allowed to name.
    UNRESOLVED_PARENTS = (
        ("a stranger", "nobody"),
        ("its own agent", "cc32"),
        ("the orchestrator", ui.ORCHESTRATOR_NODE),
    )

    def unresolved(self, recorded: str, depth: int = 2) -> str:
        """`TRUNCATED_SESSION`'s child, rewritten to record a parent that
        resolves to nothing, and its flowchart."""

        meta = self.subagents(TRUNCATED_SESSION) / (CHILD_AGENT + ".meta.json")
        meta.write_text(
            json.dumps(
                {"agentType": "Explore", "spawnDepth": depth, "parentAgentId": recorded}
            ),
            encoding="utf-8",
        )
        return self.flowchart(TRUNCATED_SESSION)

    def test_a_recorded_parent_that_did_not_resolve_is_not_called_an_absent_one(self):
        # `inferred: no parent recorded` states two things about another
        # program's data and both are false here: a parent *was* recorded,
        # and it failed to resolve. The edge shape is the same for either;
        # the sentence is not, and the sentence is what a reader acts on.
        self.own_fixture()
        for shape, recorded in self.UNRESOLVED_PARENTS:
            cell = session_cell(self.unresolved(recorded), CHILD_AGENT, "attached")

            self.assertIn(ui.EDGE_PARENT_UNRESOLVED, cell, shape)
            self.assertNotIn(ui.EDGE_INFERRED, cell, shape)

    def test_the_page_names_which_of_the_two_guesses_it_made(self):
        self.own_fixture()
        for shape, recorded in self.UNRESOLVED_PARENTS:
            notes = block_for(self.unresolved(recorded), "diagnostics", "</ul>")

            self.assertIn(ui.DIAGNOSTIC_UNRESOLVED_PARENT, notes, shape)
            self.assertNotIn(ui.DIAGNOSTIC_INFERRED_EDGE, notes, shape)

    def test_the_sentence_does_not_contradict_the_depth_it_is_drawn_at(self):
        # A depth-3 record drawn on the orchestrator is not drawn "by its
        # spawn depth alone": its own depth says two agents stand between
        # the two, and the page must not say otherwise in the same breath.
        self.own_fixture()
        page = self.unresolved("nobody", depth=3)

        self.assertNotIn("spawn depth alone", page)
        self.assertIn("3", session_cell(page, CHILD_AGENT, "depth"))
        self.assertIn(
            ui.DIAGNOSTIC_UNRESOLVED_PARENT, block_for(page, "diagnostics", "</ul>")
        )

    def test_a_record_that_truly_names_no_parent_still_says_exactly_that(self):
        # Otherwise the distinction above is bought by renaming the honest
        # case rather than by naming the case that was missing.
        page = self.flowchart()
        cell = session_cell(page, UNEVIDENCED_AGENT, "attached")
        notes = block_for(page, "diagnostics", "</ul>")

        self.assertIn(ui.EDGE_INFERRED, cell)
        self.assertNotIn(ui.EDGE_PARENT_UNRESOLVED, cell)
        self.assertIn(ui.DIAGNOSTIC_INFERRED_EDGE, notes)
        self.assertNotIn(ui.DIAGNOSTIC_UNRESOLVED_PARENT, notes)

    def test_a_depth_one_agent_hangs_off_the_orchestrator_whatever_it_records(self):
        # Spec criterion 8 is unconditional. Depth 1 means the session
        # spawned it and nothing else could have, so a pointer at a sibling
        # is a contradiction the depth wins; without this the criterion
        # holds only for the records that happen to omit the key.
        self.own_fixture()
        meta = self.subagents(TRUNCATED_SESSION) / (CHILD_AGENT + ".meta.json")
        meta.write_text(
            '{"agentType":"Explore","spawnDepth":1,"parentAgentId":"cc31"}',
            encoding="utf-8",
        )
        _nodes, edges, inferred = self.graph(TRUNCATED_SESSION)
        cell = session_cell(self.flowchart(TRUNCATED_SESSION), CHILD_AGENT, "attached")

        self.assertIn((ui.ORCHESTRATOR_NODE, CHILD_AGENT), edges)
        self.assertNotIn((PARENT_AGENT, CHILD_AGENT), edges)
        self.assertEqual((), tuple(inferred))
        self.assertIn(ui.EDGE_FROM_DEPTH, cell)

    def test_a_parent_pointer_naming_its_own_agent_still_draws_a_graph(self):
        # `graph_layout` breaks cycles, but a self-edge is not a dependency
        # anybody can lay out, and the metadata is another program's.
        self.own_fixture()
        meta = self.subagents(TRUNCATED_SESSION) / (CHILD_AGENT + ".meta.json")
        meta.write_text(
            '{"agentType":"Explore","spawnDepth":2,"parentAgentId":"cc32"}',
            encoding="utf-8",
        )
        nodes, edges, _inferred = self.graph(TRUNCATED_SESSION)

        self.assertNotIn((CHILD_AGENT, CHILD_AGENT), edges)
        self.assertEqual(sorted(set(nodes)), sorted(nodes))
        self.assertEqual(
            sorted((ui.ORCHESTRATOR_NODE, PARENT_AGENT, CHILD_AGENT)), sorted(nodes)
        )
