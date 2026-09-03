"""Structural contract for the reader's isolation from the library tree."""

import tempfile
import unittest
from pathlib import Path

import reader.scripts.ui_api as ui_api

from reader.tests._repo_root import ROOT
READER = ROOT / "reader"


class ReaderExtractionTest(unittest.TestCase):
  def test_reader_owns_browser_toolchain_and_projection_family(self):
    """The browser reader is an in-repository sibling, not library content."""

    self.assertTrue(READER.is_dir())
    for name in (
        "package.json",
        "pnpm-lock.yaml",
        "vite.config.ts",
        "tsconfig.json",
        "eslint.config.js",
    ):
        self.assertTrue((READER / name).is_file(), name)
    self.assertTrue((READER / "web").is_dir())
    self.assertTrue((READER / "scripts" / "ui_api.py").is_file())
    self.assertTrue((READER / "tools" / "ui_frontend.py").is_file())
    for name in ("view-manifest.json", "workflow-summary-manifest.json"):
        self.assertTrue((READER / "docs" / name).is_file(), name)
    self.assertFalse((ROOT / "docs" / "ui").exists())

    for path in (
        "package.json",
        "pnpm-lock.yaml",
        "vite.config.ts",
        "tsconfig.json",
        "eslint.config.js",
        "web",
        "scripts/ui.py",
        "scripts/ui_api.py",
        "tools/ui_frontend.py",
    ):
        self.assertFalse((ROOT / path).exists(), path)


  def test_reader_exposes_one_versioned_public_api_without_compatibility_fallbacks(self):
    """The public facade is v1 and does not carry legacy dispatch paths.

    Read off the built application rather than off the module's source: the
    version is the facade's own constant, the routes are the ones the
    application actually mounts, and a fallback server class would be a
    name in the module. A source-text form could only prove the grep.
    """

    self.assertEqual("v1", ui_api.PUBLIC_API_VERSION)
    self.assertNotIn("FallbackReaderServer", dir(ui_api))
    with tempfile.TemporaryDirectory() as tmp:
      mounted = {
          route.path for route in ui_api.create_application(Path(tmp)).routes
          if getattr(route, "path", "").startswith("/api")
      }
    self.assertTrue(mounted, "the application mounts no API routes")
    self.assertEqual(
        set(),
        {path for path in mounted if not path.startswith("/api/v1/")},
    )


  def test_frontend_ci_runs_from_the_reader_root(self):
    """The extracted frontend's CI commands resolve only inside reader/."""

    workflow = (ROOT / ".github" / "workflows" / "checks.yml").read_text(
        encoding="utf-8"
    )
    frontend_job = workflow.split("  frontend:\n", 1)[1].split("\n  checks:", 1)[0]

    self.assertEqual(frontend_job.count("working-directory: reader"), 4)
    self.assertIn("-r requirements-runtime.txt", frontend_job)
    self.assertIn("hashFiles('reader/pnpm-lock.yaml')", frontend_job)
    self.assertNotIn("hashFiles('pnpm-lock.yaml')", frontend_job)

    smoke = (READER / "web" / "src" / "smoke.spec.ts").read_text(encoding="utf-8")
    self.assertIn('const fixtureRoot = resolve("..", "tests", "fixtures")', smoke)
    self.assertNotIn('resolve("tests", "fixtures"', smoke)
