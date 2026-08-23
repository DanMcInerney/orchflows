"""Every edge kind the resolver claims, proved over one synthetic tree."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.test_affected_tests_cases.common import build_tree, run_cli

from tools import affected_tests  # noqa: E402


class FixtureTreeCase(unittest.TestCase):
    """Resolve scope paths against a repository built for this test alone."""

    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self._scratch.cleanup)
        self.root = build_tree(self._scratch.name)

    def resolve(self, *scope):
        return affected_tests.affected(scope, root=self.root)

    def modules(self, *scope):
        return self.resolve(*scope)["modules"]


class TestImportEdges(FixtureTreeCase):
    def test_a_dotted_import_and_a_from_import_both_reach_their_module(self):
        self.assertEqual(
            ["tests.test_from_edge", "tests.test_import_edge"],
            self.modules("scripts/mod_alpha.py"),
        )

    def test_a_spec_from_file_location_path_reaches_its_module(self):
        self.assertEqual(["tests.test_spec_edge"], self.modules("scripts/mod_beta.py"))

    def test_a_whole_string_literal_path_reaches_its_module(self):
        self.assertEqual(["tests.test_literal_edge"], self.modules("tools/mod_gamma.py"))

    def test_a_case_package_edge_is_attributed_to_its_shard_module(self):
        self.assertEqual(["tests.test_cases_edge"], self.modules("scripts/mod_delta.py"))

    def test_several_scope_paths_resolve_to_the_union_of_their_modules(self):
        self.assertEqual(
            ["tests.test_from_edge", "tests.test_import_edge", "tests.test_spec_edge"],
            self.modules("scripts/mod_alpha.py", "scripts/mod_beta.py"),
        )


class TestDirectoryAndTestScopes(FixtureTreeCase):
    def test_a_directory_scope_reaches_every_module_reading_under_it(self):
        self.assertEqual(["tests.test_dir_edge"], self.modules("pkgdir"))

    def test_a_scope_path_already_under_tests_is_its_own_module(self):
        self.assertEqual(
            ["tests.test_literal_edge"], self.modules("tests/test_literal_edge.py")
        )

    def test_a_case_package_scope_path_is_its_shard_module(self):
        self.assertEqual(
            ["tests.test_cases_edge"],
            self.modules("tests/test_cases_edge_cases/inner.py"),
        )


class TestRefusalsAndResidue(FixtureTreeCase):
    def test_a_scope_path_matching_no_module_is_named_and_yields_nothing(self):
        resolved = self.resolve("scripts/mod_orphan.py")
        self.assertEqual([], resolved["modules"])
        self.assertEqual(["scripts/mod_orphan.py"], resolved["no_tests"])

    def test_an_unreadable_test_file_is_reported_and_skipped(self):
        resolved = self.resolve("scripts/mod_alpha.py")
        reported = [entry["path"] for entry in resolved["unreadable"]]
        self.assertEqual(["tests/test_broken.py"], reported)
        self.assertEqual(
            ["tests.test_from_edge", "tests.test_import_edge"], resolved["modules"]
        )

    def test_nothing_under_the_scanned_tree_is_imported(self):
        # The fixture tree holds a module that cannot be parsed, let alone
        # imported; a resolver that imported the tree would raise here.
        self.assertTrue((self.root / "tests" / "test_broken.py").is_file())
        self.assertEqual(["tests.test_dir_edge"], self.modules("pkgdir"))


class TestCommandLineFormats(FixtureTreeCase):
    def run_cli(self, *arguments):
        return run_cli("--root", str(self.root), *arguments)

    def test_the_default_format_prints_one_module_per_line(self):
        completed = self.run_cli("scripts/mod_alpha.py")
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(
            ["tests.test_from_edge", "tests.test_import_edge"],
            completed.stdout.split(),
        )
        self.assertEqual(2, len(completed.stdout.strip().splitlines()))

    def test_the_argv_format_prints_the_runner_module_list_on_one_line(self):
        completed = self.run_cli("--format", "argv", "scripts/mod_alpha.py")
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual(
            "tests.test_from_edge tests.test_import_edge", completed.stdout.strip()
        )
        self.assertEqual(1, len(completed.stdout.strip().splitlines()))

    def test_the_json_format_carries_the_modules_scope_and_residue(self):
        completed = self.run_cli("--format", "json", "scripts/mod_alpha.py")
        self.assertEqual(0, completed.returncode, completed.stderr)
        record = json.loads(completed.stdout)
        self.assertEqual(
            ["tests.test_from_edge", "tests.test_import_edge"], record["modules"]
        )
        self.assertEqual(["scripts/mod_alpha.py"], record["scope"])
        self.assertEqual([], record["no_tests"])
        self.assertEqual(
            ["tests/test_broken.py"], [e["path"] for e in record["unreadable"]]
        )

    def test_a_no_match_scope_prints_a_no_tests_line_and_exits_zero(self):
        completed = self.run_cli("scripts/mod_orphan.py")
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertEqual("", completed.stdout.strip())
        self.assertIn("no-tests: scripts/mod_orphan.py", completed.stderr)

    def test_an_unreadable_test_file_is_named_on_the_error_stream(self):
        completed = self.run_cli("scripts/mod_alpha.py")
        self.assertIn("tests/test_broken.py", completed.stderr)
        self.assertIn("unreadable", completed.stderr)


class TestPathAcceptance(FixtureTreeCase):
    def test_an_absolute_scope_path_resolves_as_its_repository_relative_one(self):
        absolute = Path(self.root) / "scripts" / "mod_alpha.py"
        self.assertEqual(
            ["tests.test_from_edge", "tests.test_import_edge"],
            self.modules(str(absolute)),
        )

    def test_a_windows_separated_scope_path_resolves_the_same_way(self):
        self.assertEqual(
            ["tests.test_from_edge", "tests.test_import_edge"],
            self.modules("scripts\\mod_alpha.py"),
        )


if __name__ == "__main__":
    unittest.main()
