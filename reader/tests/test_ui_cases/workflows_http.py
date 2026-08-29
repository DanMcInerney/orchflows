"""Reader-facade contracts for Workflows list, detail, and source routes."""

from __future__ import annotations

from reader.tests.test_ui_cases._web import *  # noqa: F401,F403

import reader.scripts.ui_api as api


NOT_FOUND = {"error": {"code": "not_found", "message": "resource not found"}}
UNREADABLE = {
    "error": {
        "code": "unreadable_source",
        "message": "workflow source is unavailable",
    }
}
INTERNAL_ERROR = {"error": {"code": "internal_error", "message": "projection failed"}}


class WorkflowHttpTests(unittest.TestCase):
    def test_list_detail_and_source_routes_share_json_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            with serving(make_sink(Path(directory))) as server:
                catalog_response = fetch(server, "/api/v1/workflows")
                catalog = json.loads(catalog_response[2])
                detail_response = fetch(server, "/api/v1/workflows/evolve")
                detail = json.loads(detail_response[2])
                source_id = next(
                    node["source_id"] for node in detail["nodes"]
                    if node["id"] == "work:evolve/02-campaign"
                )
                source_response = fetch(
                    server, f"/api/v1/workflows/evolve/sources/{source_id}"
                )

                for route, response in (
                    ("/api/v1/workflows", catalog_response),
                    ("/api/v1/workflows/evolve", detail_response),
                    (f"/api/v1/workflows/evolve/sources/{source_id}", source_response),
                ):
                    status, headers, body = response
                    self.assertEqual(200, status, route)
                    self.assertEqual("application/json; charset=utf-8", headers.get("Content-Type"))
                    etag = headers.get("ETag")
                    self.assertTrue(etag, route)
                    repeated = fetch(server, route, {"If-None-Match": etag})
                    self.assertEqual((304, ""), (repeated[0], repeated[2]))
                    self.assertEqual(etag, repeated[1].get("ETag"))
                    self.assertNotIn(str(api.ui_workflows_projection.ROOT), body)

        self.assertEqual("orchflows.workflow-catalog.v1", catalog["schema"])
        self.assertEqual("orchflows.workflow-detail.v1", detail["schema"])
        self.assertEqual("orchflows.workflow-source.v1", json.loads(source_response[2])["schema"])

    def test_unknown_workflows_and_sources_share_route_local_generic_404(self):
        routes = (
            "/api/v1/workflows/no-such-workflow",
            "/api/v1/workflows/evolve/sources/src_bad",
            "/api/v1/workflows/..",
            "/api/v1/workflows/evolve/sources/../../private",
        )
        with tempfile.TemporaryDirectory() as directory:
            with serving(make_sink(Path(directory))) as server:
                responses = [(route, fetch(server, route)) for route in routes]

        for route, (status, headers, body) in responses:
            self.assertEqual(404, status, route)
            self.assertEqual(NOT_FOUND, json.loads(body), route)
            self.assertIsNone(headers.get("ETag"), route)
            self.assertNotIn("no-such", body)
            self.assertNotIn("private", body)

    def test_unknown_nested_workflow_path_stays_in_json_api(self):
        route = "/api/v1/workflows/evolve/private"
        with tempfile.TemporaryDirectory() as directory:
            with serving(make_sink(Path(directory))) as server:
                status, headers, body = fetch(server, route)

        self.assertEqual(404, status)
        self.assertEqual(NOT_FOUND, json.loads(body))
        self.assertIsNone(headers.get("ETag"))

    def test_unreadable_source_and_unexpected_faults_are_closed_and_uncached(self):
        private = RuntimeError(r"private C:\host\secret")
        with tempfile.TemporaryDirectory() as directory:
            with serving(make_sink(Path(directory))) as server:
                with patch.object(api, "project_workflow_source", return_value=(422, UNREADABLE)):
                    unreadable = fetch(server, "/api/v1/workflows/evolve/sources/src_" + "a" * 43)
                failures = []
                for name, route in (
                    ("project_workflow_catalog", "/api/v1/workflows"),
                    ("project_workflow", "/api/v1/workflows/evolve"),
                    ("project_workflow_source", "/api/v1/workflows/evolve/sources/src_" + "a" * 43),
                ):
                    with patch.object(api, name, side_effect=private):
                        failures.append(fetch(server, route))

        self.assertEqual((422, UNREADABLE), (unreadable[0], json.loads(unreadable[2])))
        self.assertIsNone(unreadable[1].get("ETag"))
        for status, headers, body in failures:
            self.assertEqual(500, status)
            self.assertEqual(INTERNAL_ERROR, json.loads(body))
            self.assertIsNone(headers.get("ETag"))
            self.assertNotIn("private", body)
            self.assertNotIn("host", body)

    def test_startup_refuses_a_public_route_that_duplicates_an_existing_owner(self):
        duplicate = (
            ("GET", "/api/v1/runs", "project_workflow_catalog"),
        )
        with patch.object(api.ui_workflows_projection, "PUBLIC_ROUTE_SPECS", duplicate):
            with self.assertRaisesRegex(ValueError, "duplicate.*GET.*/api/v1/runs"):
                api.create_server(Path.cwd(), 0)


if __name__ == "__main__":
    unittest.main()
