"""Ticket containment, refusal, section, and elapsed-meter regressions."""

from tests.test_ui_cases._web import *  # noqa: F401,F403
from tests.test_ui_cases.projection_security import *  # noqa: F401,F403
class TestUnreadableTicketFile(unittest.TestCase):
    """`read_ticket` promises the same shape for a file it cannot read as
    for one it can. Being handed such a path is not hypothetical:
    `run_tickets` globs `*.md`, and a *directory* whose name ends in `.md`
    matches that glob, so the ordinary walk finds one."""

    RUN = "run-unreadable"

    def sink(self, tmp: str) -> Path:
        root = make_sink(
            Path(tmp), runs=("run-gamma",), friction=False, events=False
        )
        run_dir = root / "tickets" / self.RUN
        run_dir.mkdir(parents=True)
        write_raw_ticket(run_dir, "G1.md", "G1", status="ready")
        (run_dir / "oops.md").mkdir()
        return root

    def test_a_path_that_cannot_be_read_is_an_empty_ticket_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            unreadable = self.sink(tmp) / "tickets" / self.RUN / "oops.md"

            # The premise. Without it the empty values below are proved by a
            # file that read fine and merely had nothing in it.
            with self.assertRaises(OSError):
                unreadable.read_text(encoding="utf-8", errors="replace")

            ticket = ui.read_ticket(unreadable)

            self.assertEqual("oops", ticket["id"])
            self.assertEqual("oops", ticket["file_id"])
            self.assertEqual("", ticket["status"])
            self.assertEqual("", ticket["objective"])
            self.assertEqual({}, ticket["sections"])

    def test_the_read_failure_is_marked_rather_than_read_as_an_empty_ticket(self):
        # Same shape, yes -- but not the same *values* as a ticket that read
        # fine and said nothing. "unset" and "no objective recorded" are what
        # the page draws for a ticket that is there and empty.
        with tempfile.TemporaryDirectory() as tmp:
            root = self.sink(tmp)

            unread = ui.read_ticket(root / "tickets" / self.RUN / "oops.md")
            read = ui.read_ticket(root / "tickets" / self.RUN / "G1.md")

            self.assertTrue(unread["unreadable"])
            self.assertFalse(read["unreadable"])

    def test_every_page_listing_it_names_it_unread_rather_than_showing_it_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.sink(tmp)

            for url in ("/", graph_url(self.RUN)):
                page = ui.render_route(root, url)[1]
                self.assertIn(ui.DIAGNOSTIC_UNREADABLE, page, url)
                self.assertIn("oops.md", page, url)

    def test_the_ticket_page_itself_names_the_read_failure(self):
        # The index and the run page name it through `identity_diagnostics`;
        # the ticket's own page is the one a reader lands on from either,
        # and there "unset" with no sections is what an empty ticket draws.
        # A *file* that will not read, this time: the directory above never
        # reaches `render_ticket` (`find_ticket` wants `is_file()`), and the
        # page it draws instead -- "no ticket oops in run ..." -- is the
        # route-layer collapse the ticket's ## Risks 1 queues, not this.
        real = Path.read_text

        def refused_for_g1(self, *args, **kwargs):
            if self.name == "G1.md":
                raise OSError("refused")
            return real(self, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            root = self.sink(tmp)

            with patch.object(Path, "read_text", refused_for_g1):
                status, page = ui.render_route(root, detail_url(self.RUN, "G1"))

            self.assertEqual(200, status)
            self.assertIn(ui.DIAGNOSTIC_UNREADABLE, page)

    def test_a_readable_ticket_page_carries_no_such_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.sink(tmp)

            page = ui.render_route(root, detail_url(self.RUN, "G1"))[1]

            self.assertNotIn(ui.DIAGNOSTIC_UNREADABLE, page)

    def test_a_run_of_readable_tickets_carries_no_such_diagnostic(self):
        # Otherwise the assertion above is met by a page that warns always.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), friction=False, events=False)

            page = ui.render_route(root, "/")[1]

            self.assertNotIn(ui.DIAGNOSTIC_UNREADABLE, page)

    def test_the_walk_that_finds_it_still_serves_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.sink(tmp)

            listed = ui.run_tickets(root, self.RUN)

            self.assertEqual(["G1", "oops"], sorted(t["id"] for t in listed))
            for url in ("/", graph_url(self.RUN)):
                self.assertEqual(200, ui.render_route(root, url)[0], url)
            # Not by dropping the run: the readable ticket beside it still
            # reaches its own page.
            self.assertEqual(200, ui.render_route(root, detail_url(self.RUN, "G1"))[0])


class TestTicketTreeContainment(unittest.TestCase):
    """The sink's `tickets/` is the whole scope a client-supplied name may
    reach. A `..` in the query is a climb `_safe_name` sees in the string; a
    symlink under the tickets tree is one it cannot, because the name is
    ordinary and the escape happens in the path layer. `_in_tree` resolves
    before it answers, which is the only reason the second kind is refused.

    The boundary is the query, not the walk: `discover` enumerates the
    operator's own sink and takes no client input, so a link the operator
    planted there is still theirs to see on the index."""

    LEAKED = "OUTSIDE-THE-TICKETS-TREE"
    RUN = "run-leaked"

    def link_out(self, tmp: Path) -> tuple:
        """``(sink, link)`` -- a run-shaped symlink under the sink's
        `tickets/` pointing at a real ticket outside the sink."""

        main = make_sink(tmp)
        outside = tmp / "outside"
        outside.mkdir()
        (outside / "X1.md").write_text(
            "---\nid: X1\nstatus: ready\n---\n\n## Objective\n\n%s\n" % self.LEAKED,
            encoding="utf-8",
        )
        link = main / "tickets" / self.RUN
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            # Windows only permits this under Developer Mode or admin.
            self.skipTest("cannot create a directory symlink here: %s" % error)
        return main, link

    def test_the_link_is_a_run_the_lookup_would_otherwise_resolve(self):
        # The premise. Without it the refusals below are proved by a name
        # the guard rejected on sight, or by a ticket that was never there.
        with tempfile.TemporaryDirectory() as tmp:
            _main, link = self.link_out(Path(tmp))

            self.assertEqual(self.RUN, ui._safe_name(self.RUN))
            self.assertTrue(link.is_dir())
            self.assertTrue((link / "X1.md").is_file())

    def test_a_run_linked_out_of_the_sink_is_not_a_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, _link = self.link_out(Path(tmp))

            self.assertIsNone(ui.run_tickets(main, self.RUN))
            self.assertIsNone(ui.find_ticket(main, self.RUN, "X1"))
            # Not by refusing everything: the runs really in the tree still
            # resolve through the same two calls.
            self.assertTrue(ui.run_tickets(main, "run-gamma"))
            self.assertIsNotNone(ui.find_ticket(main, "run-gamma", "G1"))

    def test_no_route_that_takes_the_name_from_a_query_serves_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, _link = self.link_out(Path(tmp))

            for url in (graph_url(self.RUN), detail_url(self.RUN, "X1")):
                status, page = ui.render_route(main, url)

                self.assertEqual(404, status, url)
                self.assertNotIn(self.LEAKED, page, url)
            # And the same two routes still serve a run that really is in
            # the tree, so 404 above is containment and not a dead route.
            self.assertEqual(200, ui.render_route(main, graph_url("run-gamma"))[0])


# Names a client can send that the path layer refuses outright rather than
# answering "no such file": NUL raises `ValueError: embedded null byte` out
# of `Path.resolve`, and a component over `NAME_MAX` raises `OSError`
# ENAMETOOLONG out of the stat. Neither is caught by
# `BaseHTTPRequestHandler`, so before the guard the client got no HTTP
# response at all and `socketserver` printed the absolute tickets path.
REFUSED_NAMES = (
    "\x00",
    "lead\x00ing",
    "\x00trailing",
    "\x1f",
    "b" * 300,
    # 253 clears the ceiling on its own and fails it once `.md` is appended,
    # which is the name the lookup actually uses.
    "c" * 253,
    # 200 characters, 400 bytes: over the ceiling the filesystem enforces
    # while under every character count the ceiling could be misread as.
    "é" * 200,
)


class TestRefusedNames(unittest.TestCase):
    """The query-to-path boundary. `find_ticket` answers a ticket or
    ``None``, `run_tickets` tickets or ``None`` and `render_route` a
    ``(status, html)`` pair -- for every string a client can send, not only
    for the ones this filesystem happens to tolerate."""

    def urls(self) -> tuple:
        return tuple(
            url
            for name in REFUSED_NAMES
            for url in (
                graph_url(quote(name, safe="")),
                detail_url(quote(name, safe=""), "G1"),
                detail_url("run-gamma", quote(name, safe="")),
            )
        )

    def test_a_refused_name_is_a_named_empty_answer_never_an_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            for name in REFUSED_NAMES:
                self.assertIsNone(ui.find_ticket(main, name, "G1"), ascii(name))
                self.assertIsNone(ui.find_ticket(main, "run-gamma", name), ascii(name))
                self.assertIsNone(ui.run_tickets(main, name), ascii(name))
                self.assertIsNone(ui.read_events(main, name), ascii(name))
            # Non-vacuity: the same three calls still resolve a real name,
            # so `None` above is a rejection rather than a lookup that
            # stopped working.
            self.assertIsNotNone(ui.find_ticket(main, "run-gamma", "G1"))
            self.assertTrue(ui.run_tickets(main, "run-gamma"))

    def test_every_refused_name_renders_a_404_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            for url in self.urls():
                status, page = ui.render_route(main, url)

                self.assertEqual(404, status, url)
                self.assertIn("not found", page, url)

    def test_a_refused_name_answers_over_the_socket_rather_than_dropping_it(self):
        # The inline poll loop catches a network error and retries, so a
        # parked browser re-triggers this every second; and a traceback out
        # of `socketserver` discloses the absolute tickets path the
        # silenced `log_message` exists to withhold.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            with serving(main) as server:
                for url in self.urls():
                    status, _headers, page = fetch(server, url)

                    self.assertEqual(404, status, url)
                    self.assertTrue(page, url)

    def test_the_guard_admits_every_name_the_corpus_actually_uses(self):
        # A ceiling set too low, or a character class drawn too wide, would
        # make this suite's own fixtures unreachable.
        for name in FIXTURE_RUNS + (EMPTY_RUN, "G1", "run-gamma", "a-z_0.9"):
            self.assertEqual(name, ui._safe_name(name), name)

    def test_the_ceiling_counts_bytes_and_not_characters(self):
        # `NAME_MAX` is a byte count, and outside ASCII the two diverge: a
        # name of 200 accented characters is 400 bytes of UTF-8. Counting
        # characters here would admit a name no store can hold, and the
        # `ENAMETOOLONG` that follows is the exception this guard exists to
        # keep out of the handler.
        over, under = "é" * 200, "é" * 100

        self.assertLessEqual(len(over), ui.MAX_NAME_BYTES)
        self.assertGreater(len(over.encode("utf-8")), ui.MAX_NAME_BYTES)
        self.assertEqual("", ui._safe_name(over))
        # Non-vacuity: multibyte is not itself the refusal.
        self.assertLessEqual(len(under.encode("utf-8")), ui.MAX_NAME_BYTES)
        self.assertEqual(under, ui._safe_name(under))

    def test_the_layer_below_the_name_guard_answers_none_rather_than_raising(self):
        # `_safe_name` refuses everything above before it can reach
        # `_in_tree`, so the second layer is only ever exercised by calling
        # it directly -- which is exactly the shape a future caller that
        # forgets the first layer would produce.
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)

            # Whether a NUL reaches the path layer as an error is the
            # host's decision, so the premise is measured, not assumed:
            # POSIX and Windows through 3.12 raise out of the syscall
            # wrapper, Windows 3.13 normalises the name and answers a
            # path. `_in_tree` refuses only what it caught raising, so on
            # that last host the second layer passes this name through --
            # recorded here, not endorsed. `_safe_name` is what actually
            # stops it, one layer up, on every host.
            try:
                base.joinpath("a\x00b").resolve()
            except (OSError, ValueError):
                refused_by_the_path_layer = True
            else:
                refused_by_the_path_layer = False

            for parts in (("a\x00b",), ("run-gamma", "a\x00b.md")):
                with self.subTest(parts=parts):
                    # The contract that holds everywhere: an answer, never
                    # an exception, for any string a client can send.
                    answer = ui._in_tree(base, *parts)
                    if refused_by_the_path_layer:
                        self.assertIsNone(answer)

            # Non-vacuity: the same call still resolves a name the path
            # layer accepts, so the answers above are the guard working
            # and not a lookup that stopped working.
            self.assertEqual(
                base.resolve() / "run-gamma", ui._in_tree(base, "run-gamma")
            )


class TestSectionRendering(unittest.TestCase):
    """A ticket body is whatever its author wrote: `contracts/work-item.md`
    fixes eight section names, requires only some of them, and lets a domain
    add its own. The reader shows what is there and invents nothing."""

    def detail(self, main: Path, run: str, ticket_id: str) -> str:
        status, page = ui.render_route(main, detail_url(run, ticket_id))
        self.assertEqual(200, status, ticket_id)
        return page

    def test_a_heading_inside_a_fenced_block_is_content_not_a_section(self):
        text = (FIXTURES / "run-gamma" / "G7.md").read_text(encoding="utf-8")

        sections = ui.split_sections(text)

        # The fenced line names a section the contract does fix, so nothing
        # about the name itself can rescue this: only the fence can.
        self.assertIn("Handoff", contract_sections())
        self.assertNotIn("Handoff", sections)
        # The line is not lost -- it belongs to the section it sits in.
        self.assertIn("## Handoff", sections["Notes on the wire"])

    def test_only_the_sections_the_ticket_carries_are_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            page = self.detail(main, "run-gamma", "G5")

            self.assertIn("<h2>Objective</h2>", page)
            for absent in ("Verification", "Result", "Risks", "Feedback"):
                self.assertNotIn("<h2>{0}</h2>".format(absent), page, absent)

    def test_a_section_name_outside_the_contract_set_is_still_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            page = self.detail(main, "run-gamma", "G7")

            self.assertNotIn("Notes on the wire", contract_sections())
            self.assertIn("<h2>Notes on the wire</h2>", page)
            self.assertIn("fixes eight section names", page)

    def test_a_present_but_empty_section_is_named_rather_than_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            page = self.detail(main, "run-gamma", "G7")
            after = page.split("<h2>Result</h2>")[1].split("</section>")[0]

            self.assertIn(ui.EMPTY_SECTION, after)

    def test_sections_render_in_the_order_the_ticket_carries_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            page = self.detail(main, "run-gamma", "G7")

            self.assertEqual(
                ["Objective", "Notes on the wire", "Result", "Risks"],
                re.findall(r"<h2>(.*?)</h2>", page),
            )


class TestElapsedMeter(unittest.TestCase):
    """Spec criterion 9: `bound` is prose on real data, and a meter drawn
    from a substituted default would be a fiction."""

    NOW = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

    def test_only_the_ticket_duration_grammar_yields_minutes(self):
        self.assertEqual(90, ui.bound_minutes("90m"))
        self.assertEqual(120, ui.bound_minutes("2h"))
        for value in ("one session", "", "90", "90 m", "1d", "m90", "-5m", None):
            self.assertIsNone(ui.bound_minutes(value), value)

    def test_this_module_refuses_the_default_bound_its_sibling_substitutes(self):
        # Non-vacuity: the sibling really does default, so `None` here is a
        # decision rather than an accident of the same code path.
        self.assertEqual(
            tickets_mod.DEFAULT_BOUND_MINUTES,
            tickets_mod._parse_bound_minutes("one session"),
        )
        self.assertIsNone(ui.bound_minutes("one session"))

    def test_a_live_claim_with_both_operands_measures_elapsed_against_bound(self):
        meter = ui.claim_meter(
            {"status": "claimed", "bound": "90m", "claimed_at": "2026-01-01T00:00:00Z"},
            self.NOW,
        )

        self.assertEqual(60, meter["elapsed_minutes"])
        self.assertEqual(90, meter["bound_minutes"])
        self.assertEqual(67, meter["percent"])
        self.assertFalse(meter["over"])

    def test_a_claim_past_its_bound_caps_at_full_and_says_so(self):
        meter = ui.claim_meter(
            {"status": "suspended", "bound": "30m", "claimed_at": "2026-01-01T00:00:00Z"},
            self.NOW,
        )

        self.assertEqual(100, meter["percent"])
        self.assertTrue(meter["over"])

    def test_nothing_is_measured_without_two_operands_and_a_live_claim(self):
        for front in (
            {"status": "claimed", "bound": "one session", "claimed_at": "2026-01-01T00:00:00Z"},
            {"status": "claimed", "bound": "90m"},
            {"status": "claimed", "bound": "90m", "claimed_at": "yesterday"},
            {"status": "complete", "bound": "90m", "claimed_at": "2026-01-01T00:00:00Z"},
            {"status": "pending", "bound": "90m", "claimed_at": "2026-01-01T00:00:00Z"},
            {},
        ):
            self.assertIsNone(ui.claim_meter(front, self.NOW), front)

    def claim_line(self, ticket_id: str) -> tuple:
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            status, page = ui.render_route(main, detail_url("run-gamma", ticket_id))
            self.assertEqual(200, status, ticket_id)
            return block_for(page, "claim", "</p>"), page

    def test_a_non_duration_bound_renders_no_meter_and_no_default(self):
        claim, page = self.claim_line("G3")

        self.assertIn("one session", claim)
        self.assertIn(ui.EMPTY_NO_METER, claim)
        self.assertNotIn("<progress", page)
        self.assertNotIn("%", claim)
        # The sibling's 60-minute lease default must not appear as a bound.
        self.assertNotIn("60", claim)

    def test_a_duration_bound_with_a_claim_time_renders_a_meter(self):
        claim, _ = self.claim_line("G4")

        self.assertIn("<progress", claim)
        self.assertIn("%", claim)
        self.assertIn("90m", claim)
        self.assertNotIn(ui.EMPTY_NO_METER, claim)

    def test_claimed_with_no_claim_time_renders_no_meter_and_does_not_raise(self):
        claim, page = self.claim_line("G5")

        self.assertIn(ui.EMPTY_UNSET, claim)
        self.assertIn(ui.EMPTY_NO_METER, claim)
        self.assertNotIn("<progress", page)
        self.assertNotIn("%", claim)

