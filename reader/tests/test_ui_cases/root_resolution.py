"""State-root resolution and reader discovery regressions."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import state_root
from reader.scripts import ui, ui_assets, ui_discovery
from reader.tests.test_ui_cases import _base as fixture


ROOT = Path(__file__).resolve().parents[3]
SINK_ENV_VAR = state_root.ENV_VAR
UI_PY = ROOT / "reader" / "scripts" / "ui.py"


class TestRootResolution(unittest.TestCase):
    def test_default_root_is_the_state_resolver_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = fixture.make_sink(Path(tmp))
            with mock.patch.dict(os.environ, {SINK_ENV_VAR: str(sink)}):
                self.assertEqual(state_root.state_root(), ui.default_root())
                self.assertEqual(sink, ui.default_root())

    def test_discovery_is_independent_of_launch_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = fixture.make_sink(tmp)
            main = tmp / "main"
            (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
            worktree = tmp / "wt"
            worktree.mkdir()
            (worktree / ".git").write_text(
                "gitdir: {0}\n".format(main / ".git" / "worktrees" / "wt"),
                encoding="utf-8",
            )
            nowhere = tmp / "nowhere"
            nowhere.mkdir()
            expected = fixture.relative_ticket_paths(ui_discovery.discover(sink))
            with mock.patch.dict(os.environ, {SINK_ENV_VAR: str(sink)}):
                for launched_from in (main, worktree, nowhere):
                    old = Path.cwd()
                    os.chdir(str(launched_from))
                    try:
                        self.assertEqual(sink, ui.default_root())
                    finally:
                        os.chdir(str(old))
                    self.assertEqual(expected, fixture.relative_ticket_paths(ui_discovery.discover(ui.default_root())))

    def test_all_run_directories_are_discovered_including_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = ui_discovery.discover(fixture.make_sink(Path(tmp)))
        self.assertEqual(
            sorted(fixture.FIXTURE_RUNS + (fixture.EMPTY_RUN,)),
            [run["run"] for run in found["runs"]],
        )
        self.assertEqual([], next(run for run in found["runs"] if run["run"] == fixture.EMPTY_RUN)["tickets"])

    def test_reader_launcher_defers_sink_resolution_to_owner(self):
        source = UI_PY.read_text(encoding="utf-8")
        self.assertNotIn('".orch"', source)
        self.assertNotIn("'.orch'", source)
        self.assertIn("state_root()", source)


class TestInstalledAssetResolution(unittest.TestCase):
    def test_installed_script_resolves_sibling_distribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / ".orchflows"
            script = home / "bin" / "ui_assets.py"
            distribution = home / "ui"
            script.parent.mkdir(parents=True)
            distribution.mkdir()
            script.write_text("# installed seam\n", encoding="utf-8")
            (distribution / "index.html").write_text("installed", encoding="utf-8")
            self.assertEqual(distribution.resolve(), ui_assets.resolve_asset_root(script))

    def test_checkout_script_resolves_reader_distribution(self):
        self.assertEqual(
            (ROOT / "reader" / "web" / "dist").resolve(),
            ui_assets.resolve_asset_root(ROOT / "reader" / "scripts" / "ui_assets.py"),
        )
