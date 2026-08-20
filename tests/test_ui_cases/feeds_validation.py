"""Friction, event, and whole-page validation regressions."""

from tests.test_ui_cases._web import *  # noqa: F401,F403

TS_RE = re.compile(r'<span class="ts">([^<]*)</span>')


class TestFrictionFeed(unittest.TestCase):
    """`U3` completion test 7. The friction law says a session that hit
    friction and logged nothing failed silently; a feed that dies on one
    half-written line is the same failure one layer up."""

    def feed(self, tmp: str, friction=True) -> str:
        root = make_sink(Path(tmp), friction=friction)
        status, page = ui.render_route(root, ui.FRICTION_ROUTE)
        self.assertEqual(200, status)
        return page

    def test_every_well_formed_entry_from_every_log_is_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.feed(tmp)

            self.assertEqual(5, len(TS_RE.findall(page)))
            self.assertIn("tools/validate.py discovered no file under scripts/", page)
            self.assertIn("a route added by branching inside the dispatcher", page)

    def test_entries_are_newest_first_across_the_log_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            stamps = TS_RE.findall(self.feed(tmp))

            self.assertEqual(sorted(stamps, reverse=True), stamps)
            self.assertEqual("2026-08-03T11:00:00Z", stamps[0])
            self.assertEqual("2026-07-30T09:15:00Z", stamps[-1])

    def test_a_malformed_line_is_skipped_and_counted_rather_than_failing(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.feed(tmp)

            # Two: a line that is not JSON, and an array that is JSON and
            # still not an entry.
            self.assertIn("2 unreadable", page)
            self.assertNotIn("an array is valid JSON", page)

    def test_a_blank_line_is_not_a_malformed_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), friction=False)
            log = root / "friction" / "2026-09.jsonl"
            log.parent.mkdir(parents=True)
            log.write_text(
                '\n{"ts": "2026-09-01T00:00:00Z", "observed": "a", "expected": "b"}\n\n\n',
                encoding="utf-8",
            )
            read = ui.read_friction(root)

            self.assertEqual(0, read["skipped"])
            self.assertEqual(1, len(read["entries"]))

    def test_a_clean_log_carries_no_skip_note_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), friction=False)
            log = root / "friction" / "2026-09.jsonl"
            log.parent.mkdir(parents=True)
            log.write_text(
                '{"ts": "2026-09-01T00:00:00Z", "observed": "a", "expected": "b"}\n',
                encoding="utf-8",
            )
            page = ui.render_route(root, ui.FRICTION_ROUTE)[1]

            self.assertNotIn("unreadable", page)
            self.assertIn("1 entry", page)

    def test_an_entry_missing_a_host_is_shown_rather_than_dropped(self):
        # An older logger wrote an entry without one. Dropping the entry would
        # lose the observation the law exists to keep.
        with tempfile.TemporaryDirectory() as tmp:
            page = self.feed(tmp)

            self.assertIn("an entry written by an older logger", page)
            self.assertEqual(1, page.count(ui.EMPTY_UNSET))

    def test_historical_categories_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.feed(tmp)

            for historical_value in ("missing-doc", "workaround", "surprising-output", "contract-gap"):
                self.assertNotIn(historical_value, page)

    def test_an_untrusted_entry_reaches_the_feed_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.feed(tmp)

            self.assertIn("&lt;b&gt;markup&lt;/b&gt;", page)
            self.assertNotIn("<b>markup</b>", page)

    def test_an_absent_friction_log_is_named_rather_than_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.feed(tmp, friction=False)

            self.assertIn(ui.EMPTY_NO_FRICTION, page)
            self.assertEqual([], TS_RE.findall(page))

    def test_the_index_links_to_the_feed(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = ui.render_route(make_sink(Path(tmp)), "/")[1]

            self.assertIn('href="{0}"'.format(ui.FRICTION_ROUTE), page)

    def test_an_entry_that_is_json_but_not_an_object_never_reaches_a_key_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), friction=False)
            log = root / "friction" / "2026-09.jsonl"
            log.parent.mkdir(parents=True)
            log.write_text('"a bare string"\n42\nnull\n[]\n', encoding="utf-8")
            read = ui.read_friction(root)

            self.assertEqual({"entries": [], "skipped": 4, "unreadable": []}, read)

    def test_a_month_file_that_cannot_be_read_is_named_rather_than_dropped(self):
        # A *directory* named like a month file matches the glob, which is
        # how this path is reachable without a chmod Windows ignores. The
        # month vanishing from the feed with no count and no note is the
        # friction law's own evidence going missing quietly.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), friction=False)
            (root / "friction" / "2026-09.jsonl").mkdir(parents=True)

            read = ui.read_friction(root)
            page = ui.render_route(root, ui.FRICTION_ROUTE)[1]

            self.assertEqual(["2026-09.jsonl"], read["unreadable"])
            self.assertIn(ui.DIAGNOSTIC_UNREADABLE, page)
            self.assertIn("2026-09.jsonl", page)
            # "no friction log under this root" would be the wrong story: one
            # was found and could not be read.
            self.assertNotIn(ui.EMPTY_NO_FRICTION, page)


EVENT_RUN = "run-gamma"


class TestEventsSeam(unittest.TestCase):
    """The deferred hooks seam the spec's `binding_constraints` fix so v2 is
    additive: `<sink>/events/<run>.jsonl`, one JSON object per line. No hook
    writes it in this version, so the reader has to hold both halves --
    render the file where it exists, say nothing at all where it does
    not."""

    def graph(self, root: Path, run: str) -> str:
        status, page = ui.render_route(root, graph_url(run))
        self.assertEqual(200, status, run)
        return page

    def test_a_run_with_an_event_log_renders_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.graph(make_sink(Path(tmp)), EVENT_RUN)

            self.assertIn("<h2>events</h2>", page)
            block = block_for(page, "events")
            self.assertEqual(3, len(block.split('<li class="event">')) - 1, block)
            for kind in ("tool_pre", "tool_post", "subagent_stop"):
                self.assertIn(kind, block, kind)

    def test_a_run_with_no_event_log_says_nothing_at_all(self):
        # The silent half. A heading over an empty feed would promise a
        # stream nothing in this version produces.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            for run in (SETTLED_RUN, CYCLIC_RUN, EMPTY_RUN):
                page = self.graph(main, run)
                self.assertNotIn("<h2>events</h2>", page, run)
                self.assertEqual("", block_for(page, "events"), run)
            self.assertIsNone(ui.read_events(main, SETTLED_RUN))

    def test_an_absent_events_directory_is_the_same_silence(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp), events=False)

            self.assertIsNone(ui.read_events(main, EVENT_RUN))
            self.assertNotIn("<h2>events</h2>", self.graph(main, EVENT_RUN))

    def test_every_key_the_seam_fixes_reaches_the_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            block = block_for(self.graph(make_sink(Path(tmp)), EVENT_RUN), "events")

            for value in (
                "2026-01-01T00:20:00Z",
                "run-gamma",
                "G4",
                "fixture-agent",
                "tool_pre",
                "Read",
                "scripts/ui.py",
            ):
                self.assertIn(value, block, value)

    def test_a_nullable_key_left_null_is_named_rather_than_blank(self):
        with tempfile.TemporaryDirectory() as tmp:
            block = block_for(self.graph(make_sink(Path(tmp)), EVENT_RUN), "events")
            stop = block.split('<li class="event">')[1].split("</li>")[0]

            self.assertIn("subagent_stop", stop)
            # `ticket`, `tool` and `detail` are all null on that line.
            self.assertEqual(3, stop.count(ui.EMPTY_UNSET), stop)

    def test_events_are_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            block = block_for(self.graph(main, EVENT_RUN), "events")

            stamps = TS_RE.findall(block)
            self.assertEqual(3, len(stamps))
            self.assertEqual(sorted(stamps, reverse=True), stamps)
            self.assertEqual("2026-01-01T00:21:00Z", stamps[0])

    def test_a_malformed_line_is_skipped_and_counted_as_the_friction_feed_does(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            read = ui.read_events(main, EVENT_RUN)

            # Two: a half-written line, and an array that is JSON and still
            # not an event. The blank line is neither.
            self.assertEqual(2, read["skipped"])
            self.assertEqual(3, len(read["entries"]))
            self.assertIn("2 unreadable lines", block_for(self.graph(main, EVENT_RUN), "events"))
            self.assertNotIn("a half-written line", self.graph(main, EVENT_RUN))

    def test_a_log_that_is_there_and_cannot_be_read_is_not_zero_events(self):
        # `None` is the seam's "no file" half and renders as silence. A file
        # found and not read is the other half: "0 events" claims a stream
        # nothing was read from.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            with patch.object(Path, "read_text", side_effect=OSError("gone")):
                read = ui.read_events(main, EVENT_RUN)

            self.assertTrue(read["unreadable"])
            self.assertIn(ui.DIAGNOSTIC_UNREADABLE, ui.render_events(read))

    def test_a_readable_log_is_marked_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))

            read = ui.read_events(main, EVENT_RUN)

            self.assertFalse(read["unreadable"])
            self.assertNotIn(ui.DIAGNOSTIC_UNREADABLE, ui.render_events(read))

    def test_an_untrusted_event_reaches_the_page_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            page = self.graph(make_sink(Path(tmp)), EVENT_RUN)

            self.assertIn("&lt;b&gt;markup&lt;/b&gt;", page)
            self.assertNotIn("<b>markup</b>", page)

    def test_the_log_is_read_from_the_run_it_is_named_for_and_no_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), events=False)
            logs = root / "events"
            logs.mkdir(parents=True)
            (logs / "{0}.jsonl".format(SETTLED_RUN)).write_text(
                '{"ts": "2026-01-01T00:00:00Z", "event": "tool_pre", "detail": "OWN-RUN"}\n',
                encoding="utf-8",
            )

            self.assertIn("OWN-RUN", self.graph(root, SETTLED_RUN))
            self.assertNotIn("OWN-RUN", self.graph(root, EVENT_RUN))

    def test_an_event_log_appearing_moves_the_validator(self):
        # `STATE_DIRS` omitted the directory, so a log written while a
        # viewer was open would never have been noticed.
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp), events=False)
            with frozen_clock():
                before = ui.state_digest(root)
                logs = root / "events"
                logs.mkdir(parents=True)
                (logs / "{0}.jsonl".format(SETTLED_RUN)).write_text(
                    '{"ts": "2026-01-01T00:00:00Z", "event": "tool_pre"}\n', encoding="utf-8"
                )
                after = ui.state_digest(root)

            self.assertNotEqual(before, after)
            self.assertIn(ui.EVENTS_DIR, ui.STATE_DIRS)


class TestValidatorObservesTheWholePage(unittest.TestCase):
    """The validator's whole job is to be a faithful function of the body it
    is served with. A tag that observes less than the page does turns the
    poll into a machine for showing a reader something that is no longer
    true, and does it silently: the response is a 304, which looks exactly
    like nothing having happened."""

    def live_root(self, tmp: str) -> Path:
        """One claim, 90m bound, claimed at `CLAIMED_AT` -- the shape whose
        rendering moves with the clock and nothing else."""

        root = make_sink(Path(tmp), runs=(), friction=False, events=False)
        write_ticket(
            root / "tickets" / "run-live",
            "L1",
            status="claimed",
            bound="90m",
            claimed_at="2026-01-01T00:20:00Z",
        )
        return root

    def at(self, server, minutes: int, etag=None) -> tuple:
        headers = {"If-None-Match": etag} if etag else {}
        with frozen_clock(CLAIMED_AT + timedelta(minutes=minutes)):
            return fetch(server, "/", headers)

    def test_a_live_meter_advances_under_polling(self):
        with tempfile.TemporaryDirectory() as tmp:
            seen = []
            with serving(self.live_root(tmp)) as server:
                for minutes in (1, 75, 100):
                    status, headers, body = self.at(server, minutes)
                    self.assertEqual(200, status, minutes)
                    seen.append((headers.get("ETag"), body))

            for (tag, body), wanted in zip(
                seen, ("1m of 90m", "75m of 90m", "100m of 90m, over bound")
            ):
                self.assertIn(wanted, body, wanted)
                self.assertTrue(tag, wanted)
            # Three different pages, so three different validators.
            self.assertEqual(3, len({tag for tag, _ in seen}))

    def test_a_client_holding_last_minutes_tag_is_answered_rather_than_left(self):
        with tempfile.TemporaryDirectory() as tmp:
            with serving(self.live_root(tmp)) as server:
                stale = self.at(server, 1)[1].get("ETag")
                status, headers, body = self.at(server, 75, stale)

            self.assertEqual(200, status)
            self.assertNotEqual(stale, headers.get("ETag"))
            self.assertIn("75m of 90m", body)

    def test_a_bound_is_crossed_under_polling_rather_than_at_the_next_write(self):
        # Nothing writes to a ticket when its bound expires, so an overrun is
        # visible only if the clock alone can move the page.
        with tempfile.TemporaryDirectory() as tmp:
            with serving(self.live_root(tmp)) as server:
                inside = self.at(server, 89)
                status, _, body = self.at(server, 91, inside[1].get("ETag"))

            self.assertNotIn("over bound", inside[2])
            self.assertEqual(200, status)
            self.assertIn("over bound", body)

    def test_a_meter_that_has_not_moved_still_answers_304(self):
        # The 304 is not defeated: within one minute the page is identical
        # and the poll must stay cheap.
        with tempfile.TemporaryDirectory() as tmp:
            with serving(self.live_root(tmp)) as server:
                first = self.at(server, 30)[1].get("ETag")
                with frozen_clock(CLAIMED_AT + timedelta(minutes=30, seconds=59)):
                    status, headers, body = fetch(
                        server, "/", {"If-None-Match": first}
                    )

            self.assertEqual(304, status)
            self.assertEqual("", body)
            self.assertEqual(first, headers.get("ETag"))

    def test_a_settled_run_answers_304_across_an_hour_of_clock(self):
        # Criterion 10's own case, kept: where nothing is claimed there is
        # nothing for the clock to move, so the tag must not move either.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp), runs=(SETTLED_RUN,))
            with serving(main) as server:
                first = self.at(server, 0)[1].get("ETag")
                status, headers, _ = self.at(server, 74, first)

            self.assertEqual(304, status)
            self.assertEqual(first, headers.get("ETag"))

    def test_a_meter_the_page_draws_is_a_digest_input(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            live = self.live_root(tmp)
            settled = make_sink(Path(other), runs=(SETTLED_RUN,))
            clock = [CLAIMED_AT + timedelta(minutes=minutes) for minutes in (1, 2, 3)]

            self.assertEqual(3, len({ui.state_digest(live, now) for now in clock}))
            # The clock is an input only where the page reads one.
            self.assertEqual(1, len({ui.state_digest(settled, now) for now in clock}))

    def test_the_two_empty_states_of_the_sink_never_share_one_digest(self):
        # A sink that is absent and one that is present-but-bare are two
        # different named pages, so they are two different validators.
        with tempfile.TemporaryDirectory() as tmp:
            absent = Path(tmp) / "absent"
            hollow = Path(tmp) / "hollow"
            hollow.mkdir()
            tickets = Path(tmp) / "with-tickets"
            (tickets / "tickets").mkdir(parents=True)

            digests = [ui.state_digest(root) for root in (absent, hollow, tickets)]
            pages = [ui.render_route(root, "/")[1] for root in (absent, hollow, tickets)]

            self.assertEqual(3, len(set(digests)), digests)
            self.assertIn(ui.EMPTY_NO_SINK, pages[0])
            self.assertIn(ui.EMPTY_NO_RUNS, pages[1])
            self.assertIn(ui.EMPTY_NO_RUNS, pages[2])

    def test_a_sink_appearing_repaints_the_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "absent"
            with serving(root) as server:
                first = fetch(server, "/")
                (root / "tickets").mkdir(parents=True)
                status, headers, body = fetch(
                    server, "/", {"If-None-Match": first[1].get("ETag")}
                )

            self.assertIn(ui.EMPTY_NO_SINK, first[2])
            self.assertEqual(200, status)
            self.assertNotEqual(first[1].get("ETag"), headers.get("ETag"))
            self.assertIn(ui.EMPTY_NO_RUNS, body)
            self.assertNotIn(ui.EMPTY_NO_SINK, body)
