"""Layout-cache, active-band, and polling regressions."""

from tests.test_ui_cases._web import *  # noqa: F401,F403

import scripts.ui_experience as experience


class ActivePollingTest(unittest.TestCase):
    def test_active_polling_preserves_current_next_and_pause_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=(), friction=False, events=False)
            run_dir = root / "tickets" / "polling-run"
            current = write_ticket(
                run_dir, "A", status="claimed", executor="orch-tdd", depends_on="[]"
            )
            upcoming = write_ticket(
                run_dir, "B", status="pending", executor="orch-tdd", depends_on="[A]"
            )
            write_ticket(
                run_dir, "C", status="pending", executor="orch-verify", depends_on="[B]"
            )

            paused = experience.project_view(root, None, "now")
            current.write_text(
                current.read_text(encoding="utf-8").replace(
                    "status: claimed", "status: complete"
                ),
                encoding="utf-8",
            )
            upcoming.write_text(
                upcoming.read_text(encoding="utf-8").replace(
                    "status: pending", "status: claimed"
                ),
                encoding="utf-8",
            )
            refreshed = experience.project_view(root, None, "now")

        paused_run = paused["runs"][0]
        refreshed_run = refreshed["runs"][0]
        self.assertEqual("polling-run", paused_run["id"])
        self.assertEqual("polling-run", refreshed_run["id"])
        self.assertEqual(
            {
                "current": [{"id": "A", "status": "claimed", "state": "running"}],
                "next": [{"id": "B", "status": "pending", "state": "waiting"}],
            },
            paused_run["execution"],
        )
        self.assertEqual(
            {
                "current": [{"id": "B", "status": "claimed", "state": "running"}],
                "next": [{"id": "C", "status": "pending", "state": "waiting"}],
            },
            refreshed_run["execution"],
        )


class TestLayoutCache(unittest.TestCase):
    """`lane-ui-patterns.md` §6(3): re-laying out a graph on a refresh that
    moved no node is a live defect in a shipped orchestrator, whose own fix
    sits in the source commented out. At a one-second poll the cost is paid
    once per second forever, so the guard is the feature."""

    def setUp(self):
        ui.LAYOUT_CACHE.clear()
        self.addCleanup(ui.LAYOUT_CACHE.clear)

    @contextlib.contextmanager
    def counting(self):
        with patch.object(ui, "graph_layout", side_effect=ui.graph_layout) as computed:
            yield computed

    def test_two_requests_over_an_unchanged_ticket_set_lay_out_exactly_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            with self.counting() as computed:
                first = ui.render_route(main, graph_url(SETTLED_RUN))[1]
                second = ui.render_route(main, graph_url(SETTLED_RUN))[1]

            self.assertEqual(1, computed.call_count)
            self.assertEqual(first, second)
            # The counter can reach two, so one is a measurement rather than
            # a mock that was never wired to anything.
            with self.counting() as recomputed:
                ui.LAYOUT_CACHE.clear()
                ui.render_route(main, graph_url(SETTLED_RUN))
                ui.LAYOUT_CACHE.clear()
                ui.render_route(main, graph_url(SETTLED_RUN))
            self.assertEqual(2, recomputed.call_count)

    def test_a_status_change_repaints_without_laying_the_graph_out_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            ticket = main / "tickets" / SETTLED_RUN / "D3.md"

            with self.counting() as computed:
                before = ui.render_route(main, graph_url(SETTLED_RUN))[1]
                ticket.write_text(
                    ticket.read_text(encoding="utf-8").replace(
                        "status: failed", "status: complete"
                    ),
                    encoding="utf-8",
                )
                after = ui.render_route(main, graph_url(SETTLED_RUN))[1]

            self.assertEqual(1, computed.call_count)
            self.assertEqual("nd-failed", node_for(before, "D3"))
            self.assertEqual("nd-complete", node_for(after, "D3"))

    def test_a_node_or_an_edge_appearing_does_lay_the_graph_out_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            run_dir = main / "tickets" / SETTLED_RUN

            with self.counting() as computed:
                ui.render_route(main, graph_url(SETTLED_RUN))
                (run_dir / "D6.md").write_text(
                    "---\nid: D6\nstatus: ready\ndepends_on: [D5]\n---\n", encoding="utf-8"
                )
                ui.render_route(main, graph_url(SETTLED_RUN))
                edged = run_dir / "D2.md"
                edged.write_text(
                    edged.read_text(encoding="utf-8").replace("  - D1", "  - D3"),
                    encoding="utf-8",
                )
                page = ui.render_route(main, graph_url(SETTLED_RUN))[1]

            self.assertEqual(3, computed.call_count)
            self.assertIn(">D6<", page)

    def test_two_runs_never_serve_each_other_a_cached_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            delta = ui.render_route(main, graph_url(SETTLED_RUN))[1]
            epsilon = ui.render_route(main, graph_url(CYCLIC_RUN))[1]

            self.assertIn(">D5<", delta)
            self.assertNotIn(">D5<", epsilon)
            self.assertIn(">E4<", epsilon)
            self.assertEqual(2, len(ui.LAYOUT_CACHE))

    def test_the_cache_is_bounded_so_a_long_lived_viewer_cannot_grow_forever(self):
        for index in range(ui.LAYOUT_CACHE_LIMIT * 2):
            ui.cached_layout(("N{0}".format(index),), ())

        self.assertEqual(ui.LAYOUT_CACHE_LIMIT, len(ui.LAYOUT_CACHE))

    def test_a_cache_hit_returns_the_layout_that_was_computed_for_that_key(self):
        ids, edges = fan_graph(5)

        computed = ui.graph_layout(ids, edges)
        first = ui.cached_layout(ids, edges)
        second = ui.cached_layout(tuple(reversed(ids)), tuple(reversed(edges)))

        self.assertEqual(coordinates(computed), coordinates(first))
        self.assertIs(first, second)


BAND_ID_RE = re.compile(r'<li class="claim">.*?<a [^>]*>([^<]+)</a>')


def band_ids(page: str) -> list:
    return BAND_ID_RE.findall(block_for(page, "band", "</ul>"))


def band_entry(page: str, ticket_id: str) -> str:
    """The band entry for ``ticket_id``, so a field is proved to sit with
    its own claim rather than with some other executor's."""

    for fragment in block_for(page, "band", "</ul>").split('<li class="claim">')[1:]:
        entry = fragment.split("</li>")[0]
        if ">{0}</a>".format(ticket_id) in entry:
            return entry
    return ""


class TestActiveBand(unittest.TestCase):
    """`U3` completion test 6, for the band the spec's view scope names.
    Which executors are at work right now is the question an orchestrator
    asks between polls, and reading it off the run tables costs a scan of
    every ticket in every run."""

    def index(self, tmp: str, runs=FIXTURE_RUNS) -> str:
        return ui.render_route(make_sink(Path(tmp), runs=runs), "/")[1]

    def test_the_band_lists_exactly_the_tickets_whose_status_is_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.index(tmp)

            self.assertEqual(["A2", "G3", "G4", "G5"], band_ids(page))
            # G7 is suspended and retains claimant observations; its joined
            # attempt is retired. G2 is blocked. Neither is at work.
            self.assertNotIn("G7", band_ids(page))
            self.assertNotIn("G2", band_ids(page))

    def test_the_band_is_absent_when_nothing_is_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.index(tmp, runs=(SETTLED_RUN,))

            self.assertEqual("", block_for(page, "band", "</ul>"))
            self.assertNotIn('<ul class="band"', page)
            # The page itself still rendered, so the band's absence is not
            # the absence of the index.
            self.assertIn(">D1<", page)

    def test_each_entry_names_its_run_ticket_executor_and_claimant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=())
            write_ticket(
                root / "tickets" / "run-one",
                "K1",
                status="claimed",
                executor="orch-tdd",
                claimed_by="agent-one",
            )
            write_ticket(
                root / "tickets" / "run-two",
                "K2",
                status="claimed",
                executor="orch-verify",
                claimed_by="agent-two",
            )
            page = ui.render_route(root, "/")[1]

            self.assertEqual(["K1", "K2"], band_ids(page))
            for wanted in ("run-one", "K1", "orch-tdd", "agent-one"):
                self.assertIn(wanted, band_entry(page, "K1"), wanted)
            for wanted in ("run-two", "K2", "orch-verify", "agent-two"):
                self.assertIn(wanted, band_entry(page, "K2"), wanted)
            # Each claimant sits with its own claim rather than anywhere.
            self.assertNotIn("agent-two", band_entry(page, "K1"))

    def test_an_entry_links_to_the_ticket_it_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = band_entry(self.index(tmp), "G3")

            self.assertIn('href="/ticket?run=run-gamma&amp;id=G3"', entry)

    def test_a_claim_that_can_be_measured_carries_its_meter(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("<progress", band_entry(self.index(tmp), "G4"))

    def test_a_claim_with_nothing_to_measure_is_listed_without_a_meter(self):
        # G5 is claimed and carries no `claimed_at`; G3's bound is not a
        # duration. Both are real shapes, and a band that dropped either
        # would hide a working executor.
        with tempfile.TemporaryDirectory() as tmp:
            page = self.index(tmp)

            for ticket_id in ("G3", "G5"):
                entry = band_entry(page, ticket_id)
                self.assertNotIn("<progress", entry, ticket_id)
                self.assertIn(ui.EMPTY_NO_METER, entry, ticket_id)

    def test_an_unset_executor_or_claimant_is_named_rather_than_left_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=())
            write_ticket(root / "tickets" / "run-one", "K1", status="claimed")
            entry = band_entry(ui.render_route(root, "/")[1], "K1")

            self.assertEqual(2, entry.count(ui.EMPTY_UNSET), entry)

    def test_an_untrusted_claimant_reaches_the_band_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), runs=())
            write_ticket(
                root / "tickets" / "run-one",
                "K1",
                status="claimed",
                claimed_by="<b>agent</b>",
            )
            page = ui.render_route(root, "/")[1]

            self.assertIn("&lt;b&gt;agent&lt;/b&gt;", page)
            self.assertNotIn("<b>agent</b>", page)

    def test_the_band_sits_above_the_runs_it_summarises(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.index(tmp)

            self.assertLess(page.index('class="band"'), page.index('class="run"'))


SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.S)
LIVE_RE = re.compile(r'<main data-live="([a-z]+)">')


class TestPolling(unittest.TestCase):
    """`U3` completion test 8. `lane-ui-patterns.md` §4: stdlib
    `http.server` never speaks HTTP/2, so the browser's six-connection cap
    applies in full and one held stream would deadlock a serial server.
    Interval polling is the transport, and the interval is the whole
    design."""

    def script(self, page: str) -> str:
        found = SCRIPT_RE.findall(page)
        self.assertEqual(1, len(found), "expected exactly one inline script")
        return found[0]

    def live(self, root: Path, route: str) -> str:
        return LIVE_RE.search(ui.render_route(root, route)[1]).group(1)

    def test_every_polling_constant_the_spec_names_is_bound_in_the_emitted_js(self):
        # Each interval is bound to its own name. A bare substring search
        # cannot tell these three apart -- "1000" is inside "15000" and
        # "5000" is inside "15000" too -- so a page that emitted only the
        # hidden interval would satisfy all three.
        with tempfile.TemporaryDirectory() as tmp:
            source = self.script(ui.render_route(make_sink(Path(tmp)), "/")[1])

            for name, milliseconds in (
                ("LIVE_MS", ui.POLL_LIVE_MS),
                ("IDLE_MS", ui.POLL_IDLE_MS),
                ("HIDDEN_MS", ui.POLL_HIDDEN_MS),
            ):
                bound = re.compile(
                    r"\b{0}\s*=\s*{1}\b".format(name, milliseconds)
                )
                self.assertRegex(source, bound, name)
            self.assertIn("document.hidden", source)

    def test_the_binding_test_can_tell_the_three_intervals_apart(self):
        # The discrimination the assertion above rests on, made explicit:
        # against a page emitting one interval under all three names, two of
        # the three patterns must fail.
        source = "  var LIVE_MS = 15000, IDLE_MS = 15000, HIDDEN_MS = 15000;\n"

        matched = [
            re.search(r"\b{0}\s*=\s*{1}\b".format(name, milliseconds), source)
            for name, milliseconds in (
                ("LIVE_MS", ui.POLL_LIVE_MS),
                ("IDLE_MS", ui.POLL_IDLE_MS),
                ("HIDDEN_MS", ui.POLL_HIDDEN_MS),
            )
        ]

        self.assertEqual([None, None], matched[:2])
        self.assertIsNotNone(matched[2])

    def test_no_route_emits_setinterval(self):
        # `setInterval` queues a second request behind a slow first one; on a
        # serial stdlib server that is how a poll becomes a pile-up.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            for route in every_route():
                page = ui.render_route(main, route)[1]
                self.assertNotIn("setInterval", page, route)
                self.assertIn("setTimeout", page, route)

    def test_the_poll_revalidates_with_the_tag_it_was_given(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self.script(ui.render_route(make_sink(Path(tmp)), "/")[1])

            self.assertIn("If-None-Match", source)
            self.assertIn("304", source)

    def test_the_script_is_inline_and_names_no_remote_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            for route in every_route():
                page = ui.render_route(main, route)[1]
                self.assertNotIn("<script src", page, route)
                self.assertNotIn("<script ", page, route)

    def test_a_run_with_work_under_way_polls_at_the_live_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            # run-gamma holds claimed tickets; run-epsilon holds a ready one.
            self.assertEqual("yes", self.live(main, graph_url("run-gamma")))
            self.assertEqual("yes", self.live(main, graph_url(CYCLIC_RUN)))

    def test_a_run_whose_every_ticket_is_terminal_polls_at_the_idle_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            self.assertEqual("no", self.live(main, graph_url(SETTLED_RUN)))
            self.assertEqual("no", self.live(main, graph_url(EMPTY_RUN)))

    def test_the_index_is_live_while_any_run_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual("yes", self.live(make_sink(Path(tmp)), "/"))
        with tempfile.TemporaryDirectory() as tmp:
            settled = make_sink(Path(tmp), runs=(SETTLED_RUN,))
            self.assertEqual("no", self.live(settled, "/"))

    def test_a_ticket_page_is_live_only_while_its_own_ticket_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            self.assertEqual("yes", self.live(main, detail_url("run-gamma", "G3")))
            self.assertEqual("no", self.live(main, detail_url("run-gamma", "G1")))
            # `suspended` retains Handoff observations but has no live attempt,
            # so the page has nothing to wait for.
            self.assertEqual("no", self.live(main, detail_url("run-gamma", "G7")))

    def test_a_page_with_no_ticket_in_view_polls_at_the_idle_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            self.assertEqual("no", self.live(main, ui.FRICTION_ROUTE))
            self.assertEqual("no", self.live(main, "/no-such-route"))
