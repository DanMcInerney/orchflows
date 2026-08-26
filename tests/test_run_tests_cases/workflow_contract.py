"""What CI must invoke, and what it must not invoke twice.

The matrix, the one sharded suite command, the per-leg timing artifact and
the per-leg timing cache are all asserted against the workflow file itself.
"""

from __future__ import annotations
import importlib
import re
import unittest
from pathlib import Path

# No sys.path guard: this module is reached only through
# ``tests.test_run_tests``, so the repository root is already importable,
# and mutating the path here would make the module an import-path seam owner.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CHECKS_YML = REPO_ROOT / ".github" / "workflows" / "checks.yml"
AGENTS_MD = REPO_ROOT / "AGENTS.md"


class TestWorkflowContract(unittest.TestCase):
    def test_star_imported_facades_do_not_export_test_cases(self):
        facade_pattern = re.compile(
            r"^from (tests\.test_[^. ]+) import \*", re.MULTILINE
        )
        facades = {
            match.group(1)
            for path in (REPO_ROOT / "tests").rglob("*.py")
            for match in facade_pattern.finditer(path.read_text(encoding="utf-8"))
        }
        offenders = []
        for module_name in sorted(facades):
            module = importlib.import_module(module_name)
            exported = getattr(
                module,
                "__all__",
                tuple(name for name in vars(module) if not name.startswith("_")),
            )
            offenders.extend(
                "{}.{}".format(module_name, name)
                for name in exported
                if isinstance(getattr(module, name), type)
                and issubclass(getattr(module, name), unittest.TestCase)
            )
        self.assertEqual([], offenders)

    def test_ci_has_exactly_the_four_supported_boundary_legs(self):
        workflow = CHECKS_YML.read_text(encoding="utf-8")
        matrix = workflow.split("      matrix:\n", 1)[1].split("\n    steps:", 1)[0]
        os_axis = re.search(r"^        os: \[([^]]+)\]$", matrix, re.MULTILINE)
        python_axis = re.search(
            r"^        python-version: \[([^]]+)\]$", matrix, re.MULTILINE
        )
        self.assertIsNotNone(os_axis)
        self.assertIsNotNone(python_axis)
        self.assertNotRegex(matrix, re.compile(r"^        include:", re.MULTILINE))
        self.assertEqual(
            {"os", "python-version", "exclude"},
            set(re.findall(r"^        ([a-z][a-z0-9-]*):", matrix, re.MULTILINE)),
        )
        self.assertEqual(
            1,
            len(re.findall(
                r"^    runs-on: \$\{\{ matrix\.os \}\}$", workflow, re.MULTILINE
            )),
        )
        self.assertEqual(
            1,
            len(re.findall(
                r"^          python-version: \$\{\{ matrix\.python-version \}\}$",
                workflow,
                re.MULTILINE,
            )),
        )

        def values(match):
            return [value.strip(" '\"") for value in match.group(1).split(",")]

        excluded = set(re.findall(
            r"- os: ([a-z-]+)\s+python-version: ['\"]([0-9.]+)['\"]",
            matrix,
        ))
        legs = [
            (os_name, python_version)
            for os_name in values(os_axis)
            for python_version in values(python_axis)
            if (os_name, python_version) not in excluded
        ]
        self.assertEqual(
            [
                ("ubuntu-latest", "3.9"),
                ("ubuntu-latest", "3.13"),
                ("macos-latest", "3.13"),
                ("windows-latest", "3.13"),
            ],
            legs,
        )
        # Both sides of the one version-gated import, and no third copy of
        # either side: 3.9 has no `tomllib`, every other supported version
        # has it, and which side a leg is on is all this axis can grade.
        self.assertEqual({"3.9", "3.13"}, set(values(python_axis)))

    def test_ci_runs_the_regression_suite_once_through_the_parallel_runner(self):
        workflow = CHECKS_YML.read_text(encoding="utf-8")
        self.assertEqual(1, workflow.count("run: python tools/run_tests.py"))
        self.assertNotIn("run: python -m unittest discover", workflow)

    def test_ci_uploads_each_python_legs_timing_even_after_failure(self):
        workflow = CHECKS_YML.read_text(encoding="utf-8")
        self.assertIn("--timing-file .orch/run-tests.json", workflow)
        self.assertIn("uses: actions/upload-artifact@v4", workflow)
        self.assertIn("if: ${{ always() }}", workflow)
        self.assertIn("path: .orch/run-tests.json", workflow)
        self.assertIn("include-hidden-files: true", workflow)

    def test_ci_restores_a_timing_cache_scoped_to_the_leg_that_wrote_it(self):
        """A shared or fixed key is worse than none: it would schedule every
        leg by another leg's long pole, or freeze the first run's timings."""
        workflow = CHECKS_YML.read_text(encoding="utf-8")
        self.assertIn("uses: actions/cache@v4", workflow)
        self.assertIn("path: .orch/run_tests_times.json", workflow)
        leg = "${{ matrix.os }}-py${{ matrix.python-version }}"
        self.assertIn("key: run-tests-times-" + leg + "-${{ github.run_id }}", workflow)
        self.assertIn("restore-keys: |", workflow)
        # Twelve spaces of indent: the key line above already holds the
        # bare prefix, so only the restore-keys entry can satisfy this.
        self.assertIn("            run-tests-times-" + leg + "-", workflow)

    def test_ci_does_not_repeat_oracles_already_in_the_sharded_suite(self):
        workflow = CHECKS_YML.read_text(encoding="utf-8")
        # TestValidatorAgainstRepo and DryRunOracleTest cover these commands
        # inside the one sharded suite invocation above.
        self.assertNotIn("run: python tools/validate.py", workflow)
        self.assertNotIn("run: python install.py --dry-run", workflow)

    def test_selected_serial_is_routine_and_exhaustive_is_the_fallback(self):
        guidance = AGENTS_MD.read_text(encoding="utf-8")
        self.assertIn("python tools/run_serial_compat.py", guidance)
        self.assertIn("python -m unittest discover -s tests -v", guidance)
        self.assertIn("routinely", guidance)
        self.assertIn("scheduled/manual", guidance)
        self.assertIn("pre-release", guidance)
