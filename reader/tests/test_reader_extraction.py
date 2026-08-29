"""Structural contract for the reader's isolation from the library tree."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
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
    """The public facade is v1 and does not carry legacy dispatch paths."""

    facade = (READER / "scripts" / "ui_api.py").read_text(encoding="utf-8")
    self.assertIn("PUBLIC_API_VERSION = \"v1\"", facade)
    self.assertIn("/api/v1/", facade)
    self.assertNotIn("/api/observe", facade)
    self.assertNotIn("FallbackReaderServer", facade)


  def test_frontend_ci_runs_from_the_reader_root(self):
    """The extracted frontend's CI commands resolve only inside reader/."""

    workflow = (ROOT / ".github" / "workflows" / "checks.yml").read_text(
        encoding="utf-8"
    )
    frontend_job = workflow.split("  frontend:\n", 1)[1].split("\n  checks:", 1)[0]

    self.assertIn("working-directory: reader", frontend_job)
    self.assertIn("hashFiles('reader/pnpm-lock.yaml')", frontend_job)
    self.assertNotIn("hashFiles('pnpm-lock.yaml')", frontend_job)
