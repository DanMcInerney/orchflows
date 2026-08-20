"""Facade assembly contracts for the isolated UI projection modules."""

from tests.test_ui_cases._web import *  # noqa: F401,F403

import importlib
import subprocess
from types import SimpleNamespace

import scripts.ui_api as api
import scripts.ui_friction_projection as friction
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


if __name__ == "__main__":
    unittest.main()
