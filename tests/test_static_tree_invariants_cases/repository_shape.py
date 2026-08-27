"""Static invariants owned by repository and test-process shape."""
import ast
import subprocess
import unittest
from pathlib import Path

from . import _registration
from ._support import ROOT, called_name, calls_named


class TestRootShellEntryPointsAreExecutable(unittest.TestCase):
    """Root shell entry points documented as ``./name.sh`` are executable."""

    def test_every_root_shell_script_is_committed_executable(self):
        try:
            listing = subprocess.run(
                ["git", "ls-files", "-s"],
                cwd=ROOT, capture_output=True, text=True, check=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            self.skipTest(f"not a git checkout, so no index mode to read: {exc}")

        checked = []
        for line in listing.splitlines():
            meta, _, path = line.partition("\t")
            if "/" in path or not path.endswith(".sh"):
                continue
            checked.append(path)
            self.assertEqual(
                "100755", meta.split()[0],
                f"{path} is committed {meta.split()[0]}; README documents "
                f"./{path}, which needs the execute bit to run as written",
            )

        # Without this the test passes when the parse or filter breaks.
        self.assertTrue(checked, "found no root-level *.sh to check")


class TestNoTempTreeIsDeletedWhileItIsTheCwd(unittest.TestCase):
    """A TemporaryDirectory block restores cwd before deleting its tree."""

    def test_no_chdir_inside_a_temporary_directory_block_defers_its_restore(self):
        offenders = []
        for path in sorted(Path(__file__).resolve().parent.parent.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.With):
                    continue
                opens_temp_tree = any(
                    isinstance(item.context_expr, ast.Call)
                    and called_name(item.context_expr) == "TemporaryDirectory"
                    for item in node.items
                )
                if not opens_temp_tree or not calls_named(node, "chdir"):
                    continue
                restored = any(
                    isinstance(child, ast.Try)
                    and any(calls_named(stmt, "chdir") for stmt in child.finalbody)
                    for child in ast.walk(node)
                )
                if not restored:
                    offenders.append(f"{path.name}:{node.lineno}")
        self.assertEqual([], offenders, "chdir inside a self-deleting temp tree")
class TestEveryCaseClassIsRegistered(unittest.TestCase):
    """No active case-family TestCase is dropped by its own shard family."""

    @classmethod
    def setUpClass(cls):
        cls.survey = _registration.survey_in_a_fresh_process()

    def test_every_case_class_its_package_defines_is_collected_by_its_family(self):
        unreachable = self.survey["unreachable"]
        self.assertEqual(
            [], self.survey["errors"],
            "the survey could not read every case package: {}".format(
                self.survey["errors"]),
        )
        self.assertEqual(
            [], unreachable,
            "case classes no shard collects, so none of their tests run:\n"
            + "\n".join(
                "  {case} ({tests} test(s)) -- import it in {aggregator}".format(
                    **record)
                for record in unreachable
            ),
        )
        # Without this the test passes when the walk finds nothing to walk.
        # Do not pin an observed corpus size: removing an obsolete family is
        # legitimate, while an empty survey is always a broken survey.
        self.assertTrue(self.survey["scanned"], "the survey found no case classes")

    def test_every_exemption_still_names_a_live_base_with_no_test_of_its_own(self):
        """Both halves, so an exemption cannot outlive what justified it.

        A dropped class appears here only because the walk found it dropped,
        so a complete list is also the proof that the walk still fires.
        """

        dropped = {record["case"]: record["tests"] for record in self.survey["exempt"]}
        for name in sorted(_registration.BASE_ONLY):
            with self.subTest(exemption=name):
                self.assertIn(
                    name, dropped,
                    "{} is gone or is now collected; drop the exemption".format(name),
                )
                self.assertEqual(
                    0, dropped[name],
                    "{} carries tests of its own now, so exempting it hides "
                    "them; register it instead".format(name),
                )
