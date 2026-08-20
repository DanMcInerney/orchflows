"""Facade assembly contracts for the isolated UI projection modules."""

from tests.test_ui_cases._web import *  # noqa: F401,F403

import importlib
import subprocess
from types import SimpleNamespace

import scripts.ui_api as api
import scripts.ui_friction_projection as friction
import scripts.ui_experience as experience
import scripts.ui_now_projection as now
import scripts.ui_runs_projection as runs
import scripts.ui_sessions_projection as sessions
import scripts.ui_workflows_projection as workflows


DOMAIN_MODULES = (now, runs, workflows, sessions, friction)


class FacadeRouteAssemblyTests(unittest.TestCase):
    def test_facade_assembles_every_domain_route_spec_exactly_once(self):
        expected = tuple(
            (method, path, module, function_name)
            for module in DOMAIN_MODULES
            for method, path, function_name in module.ROUTE_SPECS
        )
        assembled = api._projector_route_specs(DOMAIN_MODULES)

        self.assertEqual(expected, assembled)
        self.assertEqual(DOMAIN_MODULES, api.PROJECTOR_MODULES)

    def test_duplicate_domain_method_and_path_is_rejected_at_startup(self):
        duplicate = SimpleNamespace(
            __name__="duplicate_projection",
            ROUTE_SPECS=(("GET", "/api/observe", "project_duplicate"),),
        )

        with self.assertRaisesRegex(ValueError, "duplicate.*GET.*/api/observe"):
            api._projector_route_specs(DOMAIN_MODULES + (duplicate,))

    def test_facade_imports_in_package_and_flat_installed_layouts(self):
        self.assertIs(api, importlib.import_module("scripts.ui_api"))
        completed = subprocess.run(
            [sys.executable, "-c", "import ui_api"],
            cwd=str(ROOT),
            env=dict(os.environ, PYTHONPATH=str(ROOT / "scripts")),
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)


class FacadeProjectionDelegationTests(unittest.TestCase):
    def test_public_projection_compatibility_names_delegate_to_domain_owners(self):
        expected = {
            "project_observe": now.project_observe,
            "project_runs": runs.project_runs,
            "project_run": runs.project_run,
            "project_ticket": runs.project_ticket,
            "project_sessions": sessions.project_sessions,
            "project_session": sessions.project_session,
            "project_friction": friction.project_friction,
        }

        for name, owner in expected.items():
            with self.subTest(name=name):
                self.assertIs(owner, getattr(api, name))


class ClosedViewProjectionTests(unittest.TestCase):
    def test_each_view_is_a_closed_slice_of_the_compatibility_projection(self):
        cases = (
            ("now", {}, "orchflows.now.v1", ("runs",)),
            ("run-map", {"run": "run-gamma"}, "orchflows.run-map.v1", ("runs", "run")),
            (
                "inspector",
                {"run": "run-gamma", "ticket": "G1"},
                "orchflows.inspector.v1",
                ("run", "ticket"),
            ),
            ("sessions", {}, "orchflows.sessions.v1", ("sessions",)),
            (
                "session-graph",
                {"session": TITLED_SESSION},
                "orchflows.session-graph.v1",
                ("session",),
            ),
            ("friction", {}, "orchflows.friction.v1", ("friction",)),
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            root = make_sink(tmp)
            transcripts = make_transcripts(tmp)
            for view, query, schema, fields in cases:
                with self.subTest(view=view):
                    legacy = experience.project_experience(root, transcripts, query)
                    projected = experience.project_view(root, transcripts, view, query)
                    self.assertEqual({"schema", *fields}, set(projected))
                    self.assertEqual(schema, projected["schema"])
                    for field in fields:
                        self.assertEqual(legacy[field], projected[field])

    def test_phase_a_workflows_slice_adds_no_catalog_or_authoring_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_sink(Path(tmp))
            projected = experience.project_view(root, None, "run-map", {})

        encoded = json.dumps(projected, sort_keys=True)
        self.assertNotIn("workflow-catalog", encoded)
        self.assertNotIn("create", encoded)
        self.assertEqual((), workflows.ROUTE_SPECS)


class ProjectionOwnershipTests(unittest.TestCase):
    def test_aggregate_discovers_every_projection_contract_module(self):
        tree = ast.parse((ROOT / "tests" / "test_ui.py").read_text(encoding="utf-8"))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        expected = {
            "tests.test_ui_cases.domain_projections",
            "tests.test_ui_cases.experience_projection",
            "tests.test_ui_cases.projection_modules",
            "tests.test_ui_cases.projection_security",
        }

        self.assertTrue(expected.issubset(imported), expected - imported)

    def test_architecture_names_the_facade_domains_and_compatibility_owner(self):
        architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
        owners = {
            "scripts/ui_api.py",
            "scripts/ui_experience.py",
            "scripts/ui_now_projection.py",
            "scripts/ui_runs_projection.py",
            "scripts/ui_workflows_projection.py",
            "scripts/ui_sessions_projection.py",
            "scripts/ui_friction_projection.py",
        }

        for owner in owners:
            with self.subTest(owner=owner):
                self.assertIn("`{0}`".format(owner), architecture)


if __name__ == "__main__":
    unittest.main()
