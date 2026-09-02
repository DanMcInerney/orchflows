"""Executable contract for the reader API from outside its implementation tree."""

from pathlib import Path
import tempfile
import unittest

from reader.scripts.ui_api import PUBLIC_API_SCHEMA, PUBLIC_API_VERSION, create_application


from reader.tests._repo_root import ROOT


class ReaderApiContractTest(unittest.TestCase):
    def test_application_exposes_only_versioned_json_routes(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = create_application(
                Path(temporary), assets=ROOT / "reader" / "web" / "dist"
            )
        routes = {getattr(route, "path", "") for route in app.routes}
        api_routes = {route for route in routes if route.startswith("/api/")}
        self.assertTrue(api_routes)
        self.assertTrue(all(route.startswith("/api/v1/") for route in api_routes))
        self.assertNotIn("/api/observe", routes)

    def test_public_identity_is_explicitly_versioned(self):
        self.assertEqual("v1", PUBLIC_API_VERSION)
        self.assertEqual("orchflows.reader.v1", PUBLIC_API_SCHEMA)


if __name__ == "__main__":
    unittest.main()
