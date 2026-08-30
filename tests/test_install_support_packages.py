"""Distribution regressions for flat installer support modules."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install


FACADE_PREFIXES = (
    "tickets",
    "ui",
    "cutcheck",
    "packs",
    "search_plan",
    "trace",
    "workspace",
    "migrate_state",
)


class ScriptSupportDistributionTest(unittest.TestCase):
    def test_inventory_adds_only_flat_support_modules_for_cut_facades(self):
        with tempfile.TemporaryDirectory() as raw:
            scripts_dir = Path(raw)
            for name in install.SCRIPT_NAMES:
                (scripts_dir / name).write_text("", encoding="utf-8")
            support_names = [f"{prefix}_support.py" for prefix in FACADE_PREFIXES]
            for name in reversed(support_names):
                (scripts_dir / name).write_text("", encoding="utf-8")
            (scripts_dir / "unrelated_support.py").write_text("", encoding="utf-8")
            nested = scripts_dir / "nested"
            nested.mkdir()
            (nested / "tickets_nested.py").write_text("", encoding="utf-8")

            inventory = install.discover_script_names(scripts_dir)

        self.assertEqual(inventory[: len(install.SCRIPT_NAMES)], install.SCRIPT_NAMES)
        self.assertEqual(inventory[len(install.SCRIPT_NAMES) :], tuple(sorted(support_names)))

    def test_user_plan_uses_discovered_inventory_at_bin_root(self):
        expected_names = install.discover_script_names(install.REPO_ROOT / "scripts")
        with patch.object(install.Path, "home", return_value=Path(tempfile.gettempdir())), patch.object(
            install.shutil, "which", return_value="mock-host"
        ):
            plan = install.build_plan("user", None)

        self.assertEqual(tuple(src.name for src, _ in plan.scripts), expected_names)
        self.assertEqual(tuple(dest.name for _, dest in plan.scripts), expected_names)
        self.assertTrue(all(dest.parent == plan.bin_dir for _, dest in plan.scripts))

    def test_project_plan_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            project_root = Path(raw)
            with self.assertRaisesRegex(ValueError, "user scope only"):
                install.build_plan("project", project_root)


if __name__ == "__main__":
    unittest.main()
