"""Conditional HTTP, loopback, route, read-only, and asset regressions."""

from tests.test_ui_cases._web import *  # noqa: F401,F403
class TestConditionalRequests(unittest.TestCase):
    """Spec criterion 10. A one-second poll that re-renders every page every
    second is the cost this view refuses to pay; the 304 is what makes the
    interval affordable."""

    def setUp(self):
        # These are tests about a directory that did or did not change. The
        # fixtures also carry a live meter, which honestly moves the tag at
        # each minute boundary, so an unpinned clock would make a handful of
        # them fail on the minute rather than never.
        freeze(self)

    def touch(self, path: Path):
        """A rewrite inside the same wall-clock second that leaves the size
        alone -- the case a mtime-only tag misses."""

        before = path.stat()
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1000))
        after = path.stat()
        if after.st_mtime_ns == before.st_mtime_ns:
            self.skipTest("filesystem does not record sub-second mtime")
        self.assertEqual(before.st_size, after.st_size)
        self.assertEqual(int(before.st_mtime), int(after.st_mtime))

    def test_an_unchanged_ticket_directory_answers_304_to_every_data_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            with serving(main) as server:
                for route in every_route():
                    status, headers, body = fetch(server, route)
                    if status != 200:
                        continue
                    etag = headers.get("ETag")
                    self.assertTrue(etag, route)
                    again = fetch(server, route, {"If-None-Match": etag})
                    self.assertEqual(304, again[0], route)
                    self.assertEqual("", again[2], route)
                    self.assertEqual(etag, again[1].get("ETag"), route)
                    self.assertNotEqual("", body, route)

    def test_a_ticket_changing_size_answers_200_with_a_different_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            ticket = main / "tickets" / SETTLED_RUN / "D1.md"
            with serving(main) as server:
                first = fetch(server, graph_url(SETTLED_RUN))[1].get("ETag")
                with ticket.open("a", encoding="utf-8") as handle:
                    handle.write("\nanother line\n")
                status, headers, _ = fetch(
                    server, graph_url(SETTLED_RUN), {"If-None-Match": first}
                )

            self.assertEqual(200, status)
            self.assertNotEqual(first, headers.get("ETag"))

    def test_a_same_second_rewrite_of_the_same_size_answers_200_with_a_new_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            ticket = main / "tickets" / SETTLED_RUN / "D1.md"
            with serving(main) as server:
                first = fetch(server, "/")[1].get("ETag")
                self.touch(ticket)
                status, headers, body = fetch(server, "/", {"If-None-Match": first})

            self.assertEqual(200, status)
            self.assertNotEqual(first, headers.get("ETag"))
            self.assertNotEqual("", body)

    def test_a_tag_from_another_page_never_satisfies_this_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            with serving(main) as server:
                index = fetch(server, "/")[1].get("ETag")
                graph = fetch(server, graph_url(SETTLED_RUN))[1].get("ETag")
                status, _, _ = fetch(server, "/", {"If-None-Match": graph})

            self.assertNotEqual(index, graph)
            self.assertEqual(200, status)

    def test_a_stale_or_absent_validator_answers_the_whole_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            with serving(main) as server:
                for header in ({}, {"If-None-Match": '"not-a-real-tag"'}):
                    status, _, body = fetch(server, "/", header)
                    self.assertEqual(200, status)
                    self.assertIn("<main", body)

    def test_a_wildcard_or_weak_validator_is_honoured_as_rfc7232_requires(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            with serving(main) as server:
                etag = fetch(server, "/")[1].get("ETag")
                for sent in (
                    "*",
                    "W/{0}".format(etag),
                    '"other", {0}'.format(etag),
                ):
                    status, _, _ = fetch(server, "/", {"If-None-Match": sent})
                    self.assertEqual(304, status, sent)

    def test_a_404_carries_no_entity_tag_to_be_cached_against(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            with serving(main) as server:
                for route in ("/nope", detail_url(SETTLED_RUN, "ZZ9"), graph_url("nope")):
                    status, headers, _ = fetch(server, route)
                    self.assertEqual(404, status, route)
                    self.assertIsNone(headers.get("ETag"), route)

    def test_the_page_is_offered_for_revalidation_rather_than_not_stored(self):
        # `no-store` forbids keeping the response at all, so the browser has
        # nothing to revalidate and never sends `If-None-Match`: the 304 above
        # would be unreachable from a real client.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            with serving(main) as server:
                headers = fetch(server, "/")[1]

            self.assertEqual("no-cache", headers.get("Cache-Control"))

    def test_a_304_renders_nothing_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            etag = ui.respond(main, graph_url(SETTLED_RUN))[1]

            with patch.object(ui, "render_route") as rendered:
                status, echoed, body = ui.respond(main, graph_url(SETTLED_RUN), etag)

            self.assertEqual((304, etag, ""), (status, echoed, body))
            rendered.assert_not_called()


class TestLoopbackOnly(unittest.TestCase):
    """Spec `binding_constraints`: bind loopback only, never 0.0.0.0."""

    def test_server_binds_a_loopback_address_and_serves_there(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            with serving(main) as server:
                host = server.server_address[0]

                self.assertTrue(ipaddress.ip_address(host).is_loopback, host)
                self.assertNotEqual("0.0.0.0", host)
                status, page = get(server, "/")
                self.assertEqual(200, status)
                self.assertIn("orchflows runs", page)

    def test_an_unavailable_port_exits_2_with_a_message_not_a_traceback(self):
        # The bind failure is injected rather than provoked by holding the
        # port: Windows honours SO_REUSEADDR on a live listener, so a real
        # collision would bind there and serve_forever would hang CI.
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            argv = ["--root", str(main), "--port", "8787"]
            stderr = io.StringIO()
            with patch.object(ui, "create_server", side_effect=OSError("in use")):
                with contextlib.redirect_stderr(stderr):
                    code = ui.main(argv)

            self.assertEqual(2, code)
            self.assertIn("8787", stderr.getvalue())
            self.assertIn("in use", stderr.getvalue())


class TestRouteCoverage(unittest.TestCase):
    """A guard that iterates the routes proves nothing about a route it
    never visits. U1 registered `/` alone; a route added later and left out
    of the examples silently shrinks both guards below, so the coverage is
    asserted rather than assumed."""

    def test_every_served_route_is_reached_by_a_concrete_example(self):
        for route in ui.ROUTES:
            self.assertIn(route, ROUTE_EXAMPLES, route)
            self.assertTrue(ROUTE_EXAMPLES[route], route)

    def test_the_examples_reach_a_rendered_ticket_not_only_its_error_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            transcripts = make_transcripts(Path(tmp))

            served = [
                ui.render_route(main, url, transcripts)[0] for url in every_route()
            ]

            self.assertIn(200, served)
            self.assertIn(404, served)


class TestReadOnly(unittest.TestCase):
    """Spec criterion 11."""

    def test_exercising_every_route_writes_nothing_under_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            transcripts = make_transcripts(Path(tmp))
            before = snapshot(main)
            self.assertTrue(before)

            with serving(main, transcripts) as server:
                for route in every_route():
                    status, page = get(server, route)
                    self.assertIn(status, (200, 404))
                    self.assertTrue(page)

            self.assertEqual(before, snapshot(main))

    def test_revalidating_every_route_writes_nothing_either(self):
        # A 304 short-circuits before `render_route`, so the guard above
        # never walks that path -- and it is the path a poll takes almost
        # every second the viewer is open.
        freeze(self)
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            transcripts = make_transcripts(Path(tmp))
            before = snapshot(main)
            revalidated = 0

            with serving(main, transcripts) as server:
                for route in every_route():
                    etag = fetch(server, route)[1].get("ETag")
                    if etag is None:
                        continue
                    again = fetch(server, route, {"If-None-Match": etag})
                    self.assertEqual(304, again[0], route)
                    revalidated += 1

            self.assertEqual(before, snapshot(main))
            self.assertGreaterEqual(revalidated, len(ui.ROUTES))


class TestNoNetworkAssets(unittest.TestCase):
    """Spec criterion 12."""

    def test_the_detector_catches_a_remote_asset(self):
        for markup in (
            '<script src="https://cdn.example/x.js"></script>',
            "<link rel=stylesheet href='//cdn.example/x.css'>",
            '<img src="http://cdn.example/x.png">',
        ):
            self.assertIsNotNone(REMOTE_ASSET_RE.search(markup), markup)

    def test_no_route_emits_a_remote_src_or_href(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            transcripts = make_transcripts(Path(tmp))
            with serving(main, transcripts) as server:
                for route in every_route():
                    _, page = get(server, route)
                    self.assertIsNone(REMOTE_ASSET_RE.search(page), route)
