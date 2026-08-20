"""JSON projection content-wall and containment regressions."""

from tests.test_ui_cases._web import *  # noqa: F401,F403

import scripts.ui_api as api


INVALID_REQUEST = {
    "error": {"code": "invalid_request", "message": "request could not be served"}
}
NOT_FOUND = {"error": {"code": "not_found", "message": "resource not found"}}
INTERNAL_ERROR = {
    "error": {"code": "internal_error", "message": "projection failed"}
}


class TestProjectionContentWall(unittest.TestCase):
    def assert_projection_is_closed(self, body: str, *host_paths):
        self.assertNotIn(TRANSCRIPT_SENTINEL, body)
        for path in host_paths:
            self.assertNotIn(str(path), body)

    def test_the_content_wall_detector_rejects_a_wrong_projection(self):
        wrong = json.dumps(
            {"transcript": TRANSCRIPT_SENTINEL, "path": str(Path.cwd())}
        )

        with self.assertRaises(AssertionError):
            self.assert_projection_is_closed(wrong, Path.cwd())

    def test_json_routes_expose_neither_host_paths_nor_ticket_bodies(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main = make_sink(tmp)
            ticket = main / "tickets" / "run-gamma" / "G1.md"
            with ticket.open("a", encoding="utf-8") as handle:
                handle.write(
                    "\n## Private transcript copy\n\n{0}\n{1}\n".format(
                        TRANSCRIPT_SENTINEL, ticket.resolve()
                    )
                )
            before = snapshot(main)

            with serving(main) as server:
                for route in (
                    "/observe",
                    "/api/v1/runs",
                    "/api/v1/runs/run-gamma",
                    "/api/v1/runs/run-gamma/tickets/G1",
                    "/api/v1/friction",
                    "/api/observe?run=run-gamma",
                ):
                    status, _headers, body = fetch(server, route)
                    self.assertEqual(200, status, route)
                    self.assert_projection_is_closed(body, main, ticket)

            self.assertEqual(before, snapshot(main))

    def test_api_path_parameters_are_containment_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            main = make_sink(Path(tmp))
            outside = main / "secret.md"
            outside.write_text("outside-content-wall", encoding="utf-8")
            routes = (
                "/api/v1/runs/..",
                "/api/v1/runs/%2e%2e",
                "/api/v1/runs/run-gamma/tickets/%2e%2e%2f%2e%2e%2fsecret",
                "/api/v1/sessions/%2e%2e",
            )
            with serving(main) as server:
                for route in routes:
                    status, _headers, body = fetch(server, route)
                    self.assertEqual(404, status, route)
                    self.assertNotIn("outside-content-wall", body, route)
                    self.assertNotIn(str(outside), body, route)


class TestProjectionFailureBoundary(unittest.TestCase):
    def test_unsupported_views_and_query_shapes_are_the_same_generic_typed_422(self):
        routes = (
            "/api/v1/views/private-view?secret=do-not-reflect",
            "/api/v1/views/now?run=run-gamma",
            "/api/v1/views/run-map?ticket=G1",
            "/api/v1/views/inspector?run=run-gamma",
            "/api/v1/views/inspector?run=run-gamma&ticket=G1&extra=secret",
            "/api/v1/views/inspector?run=run-gamma&run=other&ticket=G1",
            "/api/v1/views/session-graph",
            "/api/v1/views/friction?path=C%3A%5Csecret",
        )
        with tempfile.TemporaryDirectory() as tmp:
            with serving(make_sink(Path(tmp))) as server:
                for route in routes:
                    with self.subTest(route=route):
                        status, headers, body = fetch(server, route)
                        self.assertEqual(422, status)
                        self.assertEqual(INVALID_REQUEST, json.loads(body))
                        self.assertIsNone(headers.get("ETag"))
                        self.assertNotIn("secret", body)
                        self.assertNotIn("private-view", body)

    def test_missing_selected_resources_are_domain_local_404s(self):
        routes = (
            "/api/v1/views/run-map?run=no-such-run",
            "/api/v1/views/inspector?run=run-gamma&ticket=no-such-ticket",
            "/api/v1/views/session-graph?session=no-such-session",
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            with serving(make_sink(tmp), make_transcripts(tmp)) as server:
                for route in routes:
                    with self.subTest(route=route):
                        status, headers, body = fetch(server, route)
                        self.assertEqual(404, status)
                        self.assertEqual(NOT_FOUND, json.loads(body))
                        self.assertIsNone(headers.get("ETag"))
                        self.assertNotIn("no-such", body)

    def test_malformed_topology_is_typed_and_never_names_the_host_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp))
            with serving(root) as server:
                status, _headers, body = fetch(
                    server, "/api/v1/views/run-map?run={0}".format(CYCLIC_RUN)
                )

        payload = json.loads(body)
        self.assertEqual(200, status)
        self.assertTrue(payload["run"]["diagnostics"])
        for diagnostic in payload["run"]["diagnostics"]:
            self.assertEqual({"kind", "ticket_ids", "message"}, set(diagnostic))
            self.assertIn(
                diagnostic["kind"],
                {"cycle", "dangling", "duplicate", "unreadable"},
            )
        self.assertNotIn(str(root), body)

    def test_unexpected_new_and_legacy_projection_faults_are_generic_500s(self):
        with tempfile.TemporaryDirectory() as tmp:
            with serving(make_sink(Path(tmp))) as server:
                with patch.object(
                    api,
                    "project_view",
                    side_effect=RuntimeError("private C:\\host\\secret"),
                ):
                    view_failure = fetch(server, "/api/v1/views/now")
                with patch.object(
                    api,
                    "project_runs",
                    side_effect=RuntimeError("private C:\\host\\secret"),
                ):
                    legacy_failure = fetch(server, "/api/v1/runs")

        for status, headers, body in (view_failure, legacy_failure):
            self.assertEqual(500, status)
            self.assertEqual(INTERNAL_ERROR, json.loads(body))
            self.assertIsNone(headers.get("ETag"))
            self.assertNotIn("private", body)
            self.assertNotIn("host", body)
