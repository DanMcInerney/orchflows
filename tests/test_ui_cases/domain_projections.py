"""Focused contracts for the flat, read-only UI domain projectors."""

from tests.test_ui_cases._web import *  # noqa: F401,F403

import ast
import importlib
import subprocess


PROJECTORS = (
    "ui_now_projection",
    "ui_runs_projection",
    "ui_workflows_projection",
    "ui_sessions_projection",
    "ui_friction_projection",
)
ROUTES = {
    "ui_now_projection": (("GET", "/api/observe", "project_observe"),),
    "ui_runs_projection": (
        ("GET", "/api/v1/runs", "project_runs"),
        ("GET", "/api/v1/runs/{run}", "project_run"),
        ("GET", "/api/v1/runs/{run}/tickets/{ticket}", "project_ticket"),
    ),
    "ui_workflows_projection": (),
    "ui_sessions_projection": (
        ("GET", "/api/v1/sessions", "project_sessions"),
        ("GET", "/api/v1/sessions/{session}", "project_session"),
    ),
    "ui_friction_projection": (("GET", "/api/v1/friction", "project_friction"),),
}


class DomainProjectionBoundaryTests(unittest.TestCase):
    def test_projectors_are_package_and_flat_import_safe_without_cross_imports(self):
        for name in PROJECTORS:
            with self.subTest(name=name, mode="package"):
                module = importlib.import_module("scripts." + name)
                self.assertEqual(ROUTES[name], module.ROUTE_SPECS)
            with self.subTest(name=name, mode="flat"):
                completed = subprocess.run(
                    [sys.executable, "-c", "import " + name],
                    cwd=str(ROOT),
                    env=dict(os.environ, PYTHONPATH=str(ROOT / "scripts")),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)

            tree = ast.parse((ROOT / "scripts" / (name + ".py")).read_text(encoding="utf-8"))
            imported = {
                alias.name.rsplit(".", 1)[-1]
                for node in ast.walk(tree)
                if isinstance(node, ast.Import)
                for alias in node.names
            }
            imported.update(
                (node.module or "").rsplit(".", 1)[-1]
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            )
            self.assertFalse((set(PROJECTORS) - {name}) & imported)


if __name__ == "__main__":
    unittest.main()
