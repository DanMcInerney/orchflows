"""Graph layout, diagnostics, view, and ticket-identity regressions."""

from reader.tests.test_ui_cases._web import *  # noqa: F401,F403


class TestGraphLayout(unittest.TestCase):
    """Spec criterion 6. A layered layout with a Coffman-Graham sorter, the
    shape Argo Workflows ships hand-rolled in 56 + 48 lines with zero
    dependencies (`lane-ui-patterns.md` §3), computed in Python so a layout
    bug is a failing unit test rather than a visual regression."""

    IDS = ("D1", "D2", "D3", "D4", "D5")
    EDGES = (("D1", "D2"), ("D1", "D3"), ("D2", "D4"), ("D3", "D4"), ("D4", "D5"))

    def test_two_calls_on_equal_input_return_byte_equal_coordinates(self):
        first = ui.graph_layout(self.IDS, self.EDGES)
        second = ui.graph_layout(self.IDS, self.EDGES)

        self.assertTrue(coordinates(first))
        self.assertEqual(coordinates(first), coordinates(second))
        # Byte equality is only meaningful because every coordinate is an
        # integer: a float would make it a fact about repr, not about layout.
        for node in first["nodes"]:
            for value in (node.layer, node.order, node.x, node.y):
                self.assertIsInstance(value, int, node)

    def test_input_order_does_not_move_a_single_node(self):
        # Set and dict iteration is where a layout loses determinism, and it
        # loses it silently: the same call in one process keeps agreeing.
        forward = ui.graph_layout(self.IDS, self.EDGES)
        reversed_input = ui.graph_layout(
            tuple(reversed(self.IDS)), tuple(reversed(self.EDGES))
        )

        self.assertEqual(coordinates(forward), coordinates(reversed_input))

    def test_a_wide_graph_with_every_tie_still_lays_out_identically_twice(self):
        ids, edges = fan_graph(9)

        first = ui.graph_layout(ids, edges)
        second = ui.graph_layout(tuple(reversed(ids)), tuple(reversed(edges)))

        self.assertEqual(coordinates(first), coordinates(second))
        self.assertEqual(len(ids), len(first["nodes"]))

    def test_every_edge_runs_from_a_strictly_lower_layer_to_a_strictly_higher_one(self):
        layout = ui.graph_layout(self.IDS, self.EDGES)
        layer = {node.id: node.layer for node in layout["nodes"]}

        self.assertEqual([], layout["diagnostics"])
        for source, target in layout["edges"]:
            self.assertLess(layer[source], layer[target], (source, target))
        # Non-vacuity: a layout that dropped every edge, or collapsed the
        # graph onto one layer, would satisfy the loop above and nothing else.
        self.assertEqual(len(self.EDGES), len(layout["edges"]))
        self.assertEqual(4, len(set(layer.values())))
        self.assertEqual(0, layer["D1"])

    def test_the_layer_law_survives_a_graph_wider_than_the_layer_bound(self):
        ids, edges = fan_graph(9)

        layout = ui.graph_layout(ids, edges)
        layer = {node.id: node.layer for node in layout["nodes"]}

        self.assertGreater(9, ui.LAYER_WIDTH)
        for source, target in layout["edges"]:
            self.assertLess(layer[source], layer[target], (source, target))
        counts = {}
        for value in layer.values():
            counts[value] = counts.get(value, 0) + 1
        self.assertTrue(counts)
        for value, count in counts.items():
            self.assertLessEqual(count, ui.LAYER_WIDTH, (value, count))

    def test_no_two_nodes_share_a_coordinate(self):
        ids, edges = fan_graph(9)

        for layout in (ui.graph_layout(*fan_graph(9)), ui.graph_layout(self.IDS, self.EDGES)):
            points = [(node.x, node.y) for node in layout["nodes"]]
            self.assertEqual(len(points), len(set(points)), points)

    def test_an_empty_graph_lays_out_to_nothing_rather_than_raising(self):
        layout = ui.graph_layout((), ())

        self.assertEqual([], layout["nodes"])
        self.assertEqual([], layout["edges"])
        self.assertEqual([], layout["diagnostics"])


class TestGraphDiagnostics(unittest.TestCase):
    """Spec criterion 7. Nothing on the write path proves a `depends_on` set
    is a DAG, and the sink is untrusted data, so the layout is total over
    every edge set: it terminates, it never raises, and what it cannot
    honour it names."""

    CYCLE = (("E3", "E1"), ("E1", "E2"), ("E2", "E3"))
    IDS = ("E1", "E2", "E3")

    def layer_law_holds(self, layout: dict):
        layer = {node.id: node.layer for node in layout["nodes"]}
        for source, target in layout["edges"]:
            self.assertLess(layer[source], layer[target], (source, target))

    def test_a_cycle_is_reported_as_a_named_diagnostic_and_never_raised(self):
        layout = ui.graph_layout(self.IDS, self.CYCLE)

        self.assertEqual(3, len(layout["nodes"]))
        self.assertEqual(1, len(layout["diagnostics"]), layout["diagnostics"])
        diagnostic = layout["diagnostics"][0]
        self.assertTrue(diagnostic.startswith(ui.DIAGNOSTIC_CYCLE), diagnostic)
        for node_id in self.IDS:
            self.assertIn(node_id, diagnostic, diagnostic)

    def test_breaking_the_cycle_leaves_every_remaining_edge_obeying_the_layer_law(self):
        layout = ui.graph_layout(self.IDS, self.CYCLE)

        self.layer_law_holds(layout)
        # Exactly one arc is withheld: dropping the whole cycle would lose
        # two true dependencies to report one false one.
        self.assertEqual(len(self.CYCLE) - 1, len(layout["edges"]))

    def test_the_diagnostic_does_not_depend_on_the_order_the_edges_arrive_in(self):
        first = ui.graph_layout(self.IDS, self.CYCLE)
        shuffled = ui.graph_layout(
            tuple(reversed(self.IDS)), (self.CYCLE[1], self.CYCLE[2], self.CYCLE[0])
        )

        self.assertEqual(first["diagnostics"], shuffled["diagnostics"])
        self.assertEqual(coordinates(first), coordinates(shuffled))

    def test_a_ticket_depending_on_itself_is_named_rather_than_drawn(self):
        layout = ui.graph_layout(("X", "Y"), (("X", "X"), ("X", "Y")))

        self.assertEqual([("X", "Y")], layout["edges"])
        self.assertEqual(1, len(layout["diagnostics"]))
        self.assertIn(ui.DIAGNOSTIC_CYCLE, layout["diagnostics"][0])

    def test_a_dependency_on_a_ticket_outside_the_run_is_named_and_dropped(self):
        layout = ui.graph_layout(("E1", "E4"), (("ZZ9", "E4"), ("E1", "E4")))

        self.assertEqual(["E1", "E4"], [node.id for node in layout["nodes"]])
        self.assertEqual([("E1", "E4")], layout["edges"])
        self.assertEqual(1, len(layout["diagnostics"]), layout["diagnostics"])
        self.assertTrue(layout["diagnostics"][0].startswith(ui.DIAGNOSTIC_DANGLING))
        self.assertIn("ZZ9", layout["diagnostics"][0])

    def test_a_graph_that_is_nothing_but_cycles_still_terminates(self):
        # Every ordered pair of eight nodes, so every edge sits on a cycle
        # and a naive "drop one edge and retry" that picked a chord would
        # never converge. The suite's own runtime is the timeout.
        ids = tuple("N{0}".format(i) for i in range(8))
        edges = tuple((a, b) for a in ids for b in ids if a != b)

        layout = ui.graph_layout(ids, edges)

        self.assertEqual(8, len(layout["nodes"]))
        self.assertTrue(layout["diagnostics"])
        self.layer_law_holds(layout)

    def test_both_diagnostics_can_be_reported_at_once(self):
        layout = ui.graph_layout(("A", "B"), (("A", "B"), ("B", "A"), ("GONE", "A")))

        named = " ".join(layout["diagnostics"])
        self.assertIn(ui.DIAGNOSTIC_CYCLE, named)
        self.assertIn(ui.DIAGNOSTIC_DANGLING, named)

    def test_api_graphs_use_the_same_normalized_structural_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = ui.project_run(make_sink(Path(tmp)), CYCLIC_RUN)
        node_ids = {node["id"] for node in graph["nodes"]}
        edge_ids = [edge["id"] for edge in graph["edges"]]
        self.assertEqual(len(edge_ids), len(set(edge_ids)))
        self.assertTrue(all(edge["source"] in node_ids and edge["target"] in node_ids for edge in graph["edges"]))
        named = " ".join(graph["diagnostics"])
        self.assertIn(ui.DIAGNOSTIC_CYCLE, named)
        self.assertIn(ui.DIAGNOSTIC_DANGLING, named)


class TestGraphView(unittest.TestCase):
    """The graph route: coordinates from the server, rendered as inline SVG.
    No canvas and no external asset -- `install.py`'s `SCRIPT_NAMES` ships
    flat filenames, so a sidecar asset would never reach `~/.orchflows/bin`
    even if the no-network law allowed one."""

    def graph(self, main: Path, run: str) -> str:
        status, page = ui.render_route(main, graph_url(run))
        self.assertEqual(200, status, run)
        return page

    def test_a_ticket_carries_its_dependencies_and_its_claimant(self):
        ticket = ui.read_ticket(FIXTURES / SETTLED_RUN / "D4.md")

        self.assertEqual(("D2", "D3"), ticket["depends_on"])
        self.assertEqual("fixture-agent", ticket["claimed_by"])
        # Both `depends_on` spellings the frontmatter parser accepts reach
        # the graph identically; only the fixtures know which is which.
        self.assertEqual(
            ("D1",), ui.read_ticket(FIXTURES / SETTLED_RUN / "D2.md")["depends_on"]
        )
        self.assertEqual((), ui.read_ticket(FIXTURES / SETTLED_RUN / "D1.md")["depends_on"])

    def test_the_graph_draws_one_node_per_ticket_and_one_edge_per_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            page = self.graph(main, SETTLED_RUN)

            self.assertIn("<svg", page)
            self.assertNotIn("<canvas", page)
            self.assertEqual(5, len(re.findall(r'<g class="nd', page)), page)
            self.assertEqual(5, len(re.findall(r'<line class="edge"', page)))
            for ticket_id in ("D1", "D2", "D3", "D4", "D5"):
                self.assertIn(">{0}<".format(ticket_id), page, ticket_id)

    def test_every_drawn_edge_points_downward_on_the_canvas(self):
        # The layer law is a fact about integers; this is the fact about the
        # picture, and one sign error separates them.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            page = self.graph(main, SETTLED_RUN)

            drawn = re.findall(r'<line class="edge" x1="\d+" y1="(\d+)" x2="\d+" y2="(\d+)"', page)
            self.assertEqual(5, len(drawn))
            for y1, y2 in drawn:
                self.assertLess(int(y1), int(y2), (y1, y2))

    def test_each_node_carries_its_status_and_links_to_its_ticket(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            page = self.graph(main, SETTLED_RUN)

            self.assertIn('href="/ticket?run=run-delta&amp;id=D3"', page)
            self.assertIn("nd-failed", page)
            self.assertIn(ui.status_presentation("failed").glyph, page)

    def test_a_cyclic_run_displays_the_named_diagnostic_and_still_draws(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            page = self.graph(main, CYCLIC_RUN)

            diagnostics = block_for(page, "diagnostics", "</ul>")
            self.assertIn(ui.DIAGNOSTIC_CYCLE, diagnostics)
            self.assertIn(ui.DIAGNOSTIC_DANGLING, diagnostics)
            self.assertIn("ZZ9", diagnostics)
            # Named, not fatal: the four nodes are still on the page.
            self.assertEqual(4, len(re.findall(r'<g class="nd', page)))

    def test_a_run_with_no_dependencies_draws_nodes_and_no_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            page = self.graph(main, "run-beta")

            self.assertIn("<svg", page)
            self.assertIn('<g class="nd', page)
            self.assertNotIn('<line class="edge"', page)
            self.assertEqual("", block_for(page, "diagnostics", "</ul>"))

    def test_a_run_with_no_tickets_names_the_empty_state_instead_of_drawing(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            page = self.graph(main, EMPTY_RUN)

            self.assertIn(ui.EMPTY_NO_TICKETS, page)
            self.assertNotIn("<svg", page)

    def test_an_unresolvable_run_is_404_with_the_value_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            for url in ("/graph", graph_url("no-such-run"), graph_url("..")):
                status, page = ui.render_route(main, url)
                self.assertEqual(404, status, url)

            status, page = ui.render_route(main, graph_url("%3Cscript%3Ex"))
            self.assertEqual(404, status)
            self.assertIn("&lt;script&gt;x", page)
            self.assertNotIn("<script>x", page)

    def test_an_out_of_contract_status_is_drawn_from_the_closed_set(self):
        # G6's `status` carries markup. The graph never interpolates a raw
        # status at all -- it draws the presentation the closed set maps to
        # -- so the fact worth holding is that the fallback was drawn, on
        # G6's own node, rather than that markup is missing from the page.
        with tempfile.TemporaryDirectory() as tmp:
            page = self.graph(make_sink(Path(tmp)), "run-gamma")

            self.assertEqual(
                "nd-{0}".format(ui.STATUS_FALLBACK.word), node_for(page, "G6")
            )
            self.assertIn(ui.STATUS_FALLBACK.glyph, page)
            self.assertNotIn("side<b>ways", page)

    def test_every_untrusted_value_the_graph_interpolates_reaches_it_escaped(self):
        # A run name and a ticket id are directory and file names, so the
        # payload has to be one a filesystem will accept: `&` is legal on
        # every platform this runs on, and is exactly the character that
        # ends an href's query parameter early if it is not escaped.
        run = "run&sub"
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=())
            run_dir = root / "tickets" / run
            write_ticket(run_dir, "T&1", status="done")
            write_ticket(run_dir, "T&2", status="ready", depends_on="T&1")

            status, page = ui.render_route(
                root, "/graph?run={0}".format(quote(run, safe=""))
            )
            self.assertEqual(200, status)

            self.assertIn('aria-label="dependency graph for run&amp;sub"', page)
            self.assertIn('href="/ticket?run=run%26sub&amp;id=T%261"', page)
            self.assertIn('<text class="nd-id" x="10" y="19">T&amp;1</text>', page)
            self.assertNotIn("run&sub", page)
            self.assertNotIn(">T&1<", page)

    def test_a_dependency_naming_markup_reaches_the_diagnostic_escaped(self):
        # `depends_on` is the one untrusted value that reaches the page as
        # free text rather than as a name the corpus vouches for: a dangling
        # target is reported verbatim and need never have been a filename.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=())
            write_ticket(
                root / "tickets" / "run-ghost",
                "H1",
                status="ready",
                depends_on="<b>ghost</b>",
            )

            page = self.graph(root, "run-ghost")

            diagnostics = block_for(page, "diagnostics", "</ul>")
            self.assertIn(ui.DIAGNOSTIC_DANGLING, diagnostics)
            self.assertIn("&lt;b&gt;ghost&lt;/b&gt;", diagnostics)
            self.assertNotIn("<b>ghost</b>", page)

    def test_the_index_offers_a_graph_for_every_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            _, index = ui.render_route(main, "/")

            for run in FIXTURE_RUNS + (EMPTY_RUN,):
                self.assertIn('href="/graph?run={0}"'.format(run), index, run)


class TestTicketIdentity(unittest.TestCase):
    """A ticket carries two identities: the frontmatter `id:` the page
    displays and links, and the file name every lookup resolves. Nothing on
    the write path keeps them equal -- a ticket copied or renamed between
    runs keeps the id it was written with -- and where they differ every
    link the page emits for that ticket is dead. The reader names what it
    cannot honour everywhere else; this is the last place it went silent."""

    RUN = "run-identity"

    def checkout(self, tmp: str, tickets) -> Path:
        root = make_sink(Path(tmp), runs=(), friction=False, events=False)
        for file_name, declared_id in tickets:
            write_raw_ticket(
                root / "tickets" / self.RUN,
                file_name,
                declared_id,
                status="ready",
            )
        return root

    def diagnostics(self, page: str) -> str:
        return block_for(page, "diagnostics", "</ul>")

    def test_a_declared_id_that_is_not_its_file_name_is_named_on_the_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.checkout(tmp, (("C1.md", "renamed"),))

            page = ui.render_route(root, "/")[1]

            named = self.diagnostics(section_for(page, self.RUN))
            self.assertNotEqual("", named)
            self.assertIn(ui.DIAGNOSTIC_ID_MISMATCH, named)
            self.assertIn("renamed", named)
            self.assertIn("C1.md", named)

    def test_the_same_mismatch_is_named_on_the_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.checkout(tmp, (("C1.md", "renamed"),))

            page = ui.render_route(root, graph_url(self.RUN))[1]

            self.assertIn(ui.DIAGNOSTIC_ID_MISMATCH, self.diagnostics(page))
            # Named, not fatal: the node is still drawn.
            self.assertIn(">renamed<", page)

    def test_the_diagnostic_names_a_link_that_really_is_dead(self):
        # Without this the diagnostic could be true of nothing: the row,
        # the node and the band all link the declared id, and that is the
        # id no lookup resolves.
        with tempfile.TemporaryDirectory() as tmp:
            root = self.checkout(tmp, (("C1.md", "renamed"),))

            page = ui.render_route(root, "/")[1]

            self.assertIn('href="/ticket?run=run-identity&amp;id=renamed"', page)
            self.assertEqual(404, ui.render_route(root, detail_url(self.RUN, "renamed"))[0])
            self.assertEqual(200, ui.render_route(root, detail_url(self.RUN, "C1"))[0])

    def test_two_files_declaring_one_id_are_named_and_one_node_is_drawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.checkout(tmp, (("C1.md", "dup"), ("C2.md", "dup")))

            page = ui.render_route(root, graph_url(self.RUN))[1]

            named = self.diagnostics(page)
            self.assertIn(ui.DIAGNOSTIC_ID_COLLISION, named)
            self.assertIn("C1.md", named)
            self.assertIn("C2.md", named)
            # The collapse the diagnostic exists for: two tickets, one node.
            self.assertEqual(2, len(ui.run_tickets(root, self.RUN)))
            self.assertEqual(1, len(re.findall(r'<g class="nd', page)))

    def test_a_declared_id_carrying_markup_reaches_the_diagnostic_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.checkout(tmp, (("C1.md", "<b>x</b>"),))

            page = ui.render_route(root, graph_url(self.RUN))[1]

            self.assertIn("&lt;b&gt;x&lt;/b&gt;", self.diagnostics(page))
            self.assertNotIn("<b>x</b>", page)

    def test_a_run_whose_ids_all_match_their_files_says_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            self.assertEqual([], ui.identity_diagnostics(ui.run_tickets(main, "run-gamma")))
            index = ui.render_route(main, "/")[1]
            for run in FIXTURE_RUNS:
                self.assertNotIn(
                    ui.DIAGNOSTIC_ID_MISMATCH, self.diagnostics(section_for(index, run)), run
                )

    def test_an_unreadable_frontmatter_falls_back_to_the_file_name_silently(self):
        # A ticket with no `id:` at all already resolves both ways, so it
        # must not be reported as a disagreement.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=(), friction=False, events=False)
            run_dir = root / "tickets" / self.RUN
            run_dir.mkdir(parents=True)
            (run_dir / "C9.md").write_text("no frontmatter at all\n", encoding="utf-8")

            tickets = ui.run_tickets(root, self.RUN)

            self.assertEqual(["C9"], [ticket["id"] for ticket in tickets])
            self.assertEqual([], ui.identity_diagnostics(tickets))
