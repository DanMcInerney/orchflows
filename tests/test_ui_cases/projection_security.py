"""JSON projection content-wall and containment regressions."""

from tests.test_ui_cases._web import *  # noqa: F401,F403


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
