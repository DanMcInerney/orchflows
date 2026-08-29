"""Pure projection contracts for each reader domain owner."""

import json
import tempfile
import unittest
from pathlib import Path

from reader.scripts import (
    ui_api,
    ui_artifacts_projection,
    ui_friction_projection,
    ui_runs_projection,
    ui_sessions_projection,
    ui_workflows_projection,
)
from reader.tests.test_ui_cases import _base as fixture


class DomainProjectionBoundaryTests(unittest.TestCase):
    def test_route_specs_are_versioned_and_owned_by_domain_modules(self):
        modules = (
            ui_artifacts_projection,
            ui_runs_projection,
            ui_sessions_projection,
            ui_friction_projection,
        )
        for module in modules:
            for method, path, function_name in module.ROUTE_SPECS:
                self.assertEqual("GET", method)
                self.assertTrue(path.startswith("/api/v1/"), path)
                self.assertTrue(callable(getattr(module, function_name)))
        routes = {path for _method, path, _module, _name in ui_api._projector_route_specs()}
        self.assertTrue(routes)
        self.assertTrue(all(path.startswith("/api/v1/") for path in routes))

    def test_api_facade_does_not_reexport_projection_functions(self):
        for name in (
            "project_runs",
            "project_run",
            "project_ticket",
            "project_sessions",
            "project_session",
            "project_friction",
            "project_workflow",
            "project_artifact",
        ):
            self.assertFalse(hasattr(ui_api, name), name)


class ProjectionPayloadTests(unittest.TestCase):
    def setUp(self):
        self.stack = tempfile.TemporaryDirectory()
        self.root = fixture.make_sink(Path(self.stack.name))
        self.transcripts = fixture.make_transcripts(Path(self.stack.name))
        self.addCleanup(self.stack.cleanup)

    def test_run_projection_is_closed_and_contains_graph_diagnostics(self):
        payload = ui_runs_projection.project_run(self.root, fixture.CYCLIC_RUN)
        self.assertEqual({"api_version", "run", "active", "nodes", "edges", "diagnostics", "events"}, set(payload))
        self.assertTrue(payload["diagnostics"])
        self.assertNotIn(str(self.root), json.dumps(payload))

    def test_now_and_friction_projections_are_closed_metadata(self):
        now = ui_runs_projection.project_runs(self.root)
        friction = ui_friction_projection.project_friction(self.root)
        self.assertEqual({"api_version", "runs", "empty"}, set(now))
        self.assertEqual({"api_version", "entries", "skipped", "unreadable"}, set(friction))
        encoded = json.dumps((now, friction))
        self.assertNotIn(str(self.root), encoded)

    def test_sessions_projection_exposes_metadata_without_transcript_content(self):
        payload = ui_sessions_projection.project_sessions(self.transcripts)
        self.assertEqual({"api_version", "sessions", "diagnostics", "empty"}, set(payload))
        encoded = json.dumps(payload)
        self.assertNotIn(fixture.TRANSCRIPT_SENTINEL, encoded)
        self.assertNotIn(str(self.transcripts), encoded)

    def test_workflows_projection_has_its_versioned_catalog(self):
        payload = ui_workflows_projection.project_workflow_catalog()
        self.assertEqual("orchflows.workflow-catalog.v1", payload["schema"])
        self.assertTrue(payload["workflows"])
