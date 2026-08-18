"""Static invariants owned by repository and test-process shape."""
import ast
import subprocess
import unittest
from pathlib import Path

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
