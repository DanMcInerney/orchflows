"""Conditional HTTP, loopback, route, read-only, and asset regressions."""

import socket

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


class TestCompiledApplicationServer(unittest.TestCase):
    """The installed reader is the immutable application plus frozen JSON."""

    def test_the_application_and_every_manifest_asset_are_served_with_validators(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            manifest = json.loads(
                (ROOT / "web" / "dist" / ".vite" / "manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            assets = [manifest["index.html"]["file"]]
            assets.extend(manifest["index.html"].get("css", ()))
            with serving(main) as server:
                status, headers, page = fetch(server, "/observe")
                self.assertEqual(200, status)
                self.assertIn('id="root"', page)
                self.assertEqual("text/html; charset=utf-8", headers.get("Content-Type"))
                self.assertTrue(headers.get("ETag"))
                self.assertEqual("no-cache", headers.get("Cache-Control"))
                for asset in assets:
                    status, seen, body = fetch(server, "/" + asset)
                    self.assertEqual(200, status, asset)
                    self.assertTrue(body, asset)
                    self.assertTrue(seen.get("ETag"), asset)
                    self.assertIn("immutable", seen.get("Cache-Control", ""), asset)
                    repeated = fetch(
                        server, "/" + asset, {"If-None-Match": seen.get("ETag")}
                    )
                    self.assertEqual(304, repeated[0], asset)
                    self.assertEqual("", repeated[2], asset)
                    head = request(server, "/" + asset, method="HEAD")
                    self.assertEqual(200, head[0], asset)
                    self.assertEqual("", head[2], asset)
                    self.assertEqual(seen.get("Content-Type"), head[1].get("Content-Type"))
                    self.assertEqual(seen.get("Content-Length"), head[1].get("Content-Length"))

    def test_the_v1_projection_surface_is_json_only_and_conditional(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            transcripts = make_transcripts(Path(tmp))
            routes = (
                "/api/v1/runs",
                "/api/v1/runs/run-gamma",
                "/api/v1/runs/run-gamma/tickets/G1",
                "/api/v1/friction",
                "/api/v1/sessions",
                "/api/v1/sessions/{0}".format(TITLED_SESSION),
                "/api/observe?run=run-gamma",
            )
            with serving(main, transcripts) as server:
                for route in routes:
                    status, headers, body = fetch(server, route)
                    self.assertEqual(200, status, route)
                    self.assertEqual(
                        "application/json; charset=utf-8",
                        headers.get("Content-Type"),
                        route,
                    )
                    self.assertIsInstance(json.loads(body), dict, route)
                    tag = headers.get("ETag")
                    self.assertTrue(tag, route)
                    unchanged = fetch(server, route, {"If-None-Match": tag})
                    self.assertEqual(304, unchanged[0], route)
                    self.assertEqual("", unchanged[2], route)

    def test_feature_views_are_closed_json_slices_with_shared_validators(self):
        cases = {
            "/api/v1/views/now": ("orchflows.now.v1", {"schema", "runs"}),
            "/api/v1/views/run-map?run=run-gamma": (
                "orchflows.run-map.v1",
                {"schema", "runs", "run"},
            ),
            "/api/v1/views/inspector?run=run-gamma&ticket=G1": (
                "orchflows.inspector.v1",
                {"schema", "run", "ticket"},
            ),
            "/api/v1/views/sessions": (
                "orchflows.sessions.v1",
                {"schema", "sessions"},
            ),
            "/api/v1/views/session-graph?session={0}".format(TITLED_SESSION): (
                "orchflows.session-graph.v1",
                {"schema", "session"},
            ),
            "/api/v1/views/friction": (
                "orchflows.friction.v1",
                {"schema", "friction"},
            ),
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with serving(make_sink(tmp), make_transcripts(tmp)) as server:
                for route, (schema, keys) in cases.items():
                    with self.subTest(route=route):
                        status, headers, body = fetch(server, route)
                        self.assertEqual(200, status)
                        self.assertEqual(
                            "application/json; charset=utf-8",
                            headers.get("Content-Type"),
                        )
                        payload = json.loads(body)
                        self.assertEqual(keys, set(payload))
                        self.assertEqual(schema, payload["schema"])
                        tag = headers.get("ETag")
                        self.assertTrue(tag)
                        repeated = fetch(server, route, {"If-None-Match": tag})
                        self.assertEqual((304, ""), (repeated[0], repeated[2]))
                        self.assertEqual(tag, repeated[1].get("ETag"))

    def test_ticket_projection_names_source_and_partial_friction_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            log = ui.read_friction(main)
            with serving(main) as server:
                status, _headers, body = fetch(server, "/api/v1/runs/run-gamma/tickets/G1")
        payload = json.loads(body)
        self.assertEqual(200, status)
        self.assertEqual({"file_id": "G1", "unreadable": False}, payload["ticket"]["source"])
        self.assertEqual({"skipped": log["skipped"], "unreadable": log["unreadable"]}, payload["friction_health"])

    def test_observe_compatibility_has_the_browser_contract_and_one_run_graph(self):
        with tempfile.TemporaryDirectory() as tmp:
            with serving(make_sink(Path(tmp))) as server:
                status, _headers, body = fetch(server, "/api/observe?run=run-gamma")

            payload = json.loads(body)
            self.assertEqual(200, status)
            self.assertEqual(
                {"revision", "active", "nodes", "edges"}, set(payload)
            )
            self.assertTrue(payload["revision"])
            self.assertEqual(
                ["G1", "G2", "G3", "G4", "G5", "G6", "G7"],
                sorted(node["id"] for node in payload["nodes"]),
            )
            self.assertEqual(
                {"id", "label", "status"}, set(payload["nodes"][0])
            )
            self.assertEqual(
                {"id", "source", "target"}, set(payload["edges"][0])
            )

    def test_legacy_deep_links_keep_their_rendered_identity(self):
        routes = {
            "/ticket?run=run-gamma&id=G1": "G1",
            "/graph?run=run-gamma": "run-gamma",
            "/session?id={0}".format(TITLED_SESSION): TITLED_SESSION,
            "/sessions": "sessions",
            "/friction": "friction",
        }
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with serving(make_sink(tmp), make_transcripts(tmp)) as server:
                for route, identity in routes.items():
                    status, headers, body = fetch(server, route)
                    self.assertEqual(200, status, route)
                    self.assertIn(identity, body, route)
                    self.assertTrue(headers.get("ETag"), route)

    def test_host_methods_cors_headers_and_binding_fail_closed(self):
        required = {
            "Content-Security-Policy",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "Cross-Origin-Resource-Policy",
        }
        with tempfile.TemporaryDirectory() as tmp:
            with serving(make_sink(Path(tmp))) as server:
                self.assertEqual("127.0.0.1", server.server_address[0])
                for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
                    status, headers, _body = request(server, "/api/v1/runs", method)
                    self.assertEqual(405, status, method)
                    self.assertEqual(
                        {"GET", "HEAD"},
                        set(headers.get("Allow", "").replace(" ", "").split(",")),
                        method,
                    )
                    self.assertIsNone(headers.get("Access-Control-Allow-Origin"), method)
                trace = request(server, "/api/v1/runs", "TRACE")
                self.assertEqual(405, trace[0])
                self.assertEqual("GET, HEAD", trace[1].get("Allow"))
                refused = fetch(server, "/", {"Host": "reader.example"})
                self.assertEqual(400, refused[0])
                self.assertIsNone(refused[1].get("Access-Control-Allow-Origin"))
                for route in ("/observe", "/api/v1/runs", "/not-found"):
                    status, headers, _body = fetch(server, route)
                    self.assertIn(status, (200, 404), route)
                    self.assertTrue({name.lower() for name in required}.issubset({name.lower() for name in headers}), route)

                raw = socket.create_connection(server.server_address, timeout=5)
                with raw:
                    raw.sendall(b"GET /api/v1/runs HTTP/1.1\r\nHost: 127.0.0.1\r\nHost: reader.example\r\nConnection: close\r\n\r\n")
                    response = raw.recv(4096)
                self.assertIn(b" 400 ", response.split(b"\r\n", 1)[0])
