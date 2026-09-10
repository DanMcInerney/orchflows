"""Sync fixtures must never prepare dependencies in the shared source tree."""

from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import orchflows_node, rings
from tests._repo_root import ROOT
from tests import test_orchflows_cli, test_orchflows_envs, test_orchflows_tooling


class SyncDependencyIsolationTests(unittest.TestCase):
    def test_sync_fixtures_do_not_prepare_source_dependencies(self):
        cases = (
            test_orchflows_cli.SyncTests("test_sync_makes_a_fresh_home_ring_whole"),
            test_orchflows_envs.EnvCommandTests(
                "test_env_prints_the_items_own_interpreter_once_sync_built_it"),
            test_orchflows_tooling.SyncReportTests(
                "test_sync_reports_each_missing_tool_with_its_line_and_prunes_the_orphan"),
        )
        ensure = orchflows_node.ensure
        inventory = rings.inventory

        def prepare(kind, name, item_dir, **kwargs):
            # Intercept before the stamp check: a warm developer cache must not
            # hide a source install that cold, raw npm-ci dependencies trigger.
            self.assertFalse(Path(item_dir).resolve().is_relative_to(ROOT), item_dir)
            return ensure(kind, name, item_dir, **kwargs)

        for case in cases:
            with self.subTest(case=case.id()), \
                    patch.object(orchflows_node, "ensure", side_effect=prepare):
                result = unittest.TestResult()
                case.run(result)
                self.assertEqual([], result.errors + result.failures)
                self.assertEqual([], result.skipped)
                self.assertEqual(1, result.testsRun)
                self.assertIs(inventory, rings.inventory)


if __name__ == "__main__":
    unittest.main()
