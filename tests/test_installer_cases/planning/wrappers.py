"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


class TestBootstrapWrappers(unittest.TestCase):
    """Criterion 7: install.sh / install.cmd resolve uv -> python3 -> python
    and forward every argument to install.py; never a bare hardcoded
    interpreter. Strengthened over a plain "does this substring appear
    anywhere in the file" check: each resolution branch is asserted to pair
    its own interpreter invocation with the target script and full argument
    forwarding, on the same branch -- a branch that resolved an interpreter
    but forgot to forward arguments would pass the old check and fail this
    one."""

    def test_install_sh_is_posix_wrapper_resolving_interpreters(self):
        path = install.REPO_ROOT / "install.sh"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/bin/sh"))
        self.assertRegex(
            text,
            r'command -v uv[^\n]*\n(?:.*\n)*?\s*exec uv run --no-project python "\$target" "\$@"',
        )
        self.assertRegex(
            text,
            r'command -v python3[^\n]*\n(?:.*\n)*?\s*exec python3 "\$target" "\$@"',
        )
        self.assertRegex(
            text,
            r'command -v python[^\n]*\n(?:.*\n)*?\s*exec python "\$target" "\$@"',
        )

    def test_install_cmd_is_windows_wrapper_resolving_interpreters(self):
        path = install.REPO_ROOT / "install.cmd"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertRegex(
            text,
            r'where uv[^\n]*\n(?:.*\n)*?\s*uv run --no-project python "%target%" %\*',
        )
        self.assertRegex(
            text,
            r'where python3[^\n]*\n(?:.*\n)*?\s*python3 "%target%" %\*',
        )
        self.assertRegex(
            text,
            r'where python[^\n]*\n(?:.*\n)*?\s*python "%target%" %\*',
        )

    def test_wrapper_comments_credit_the_uv_first_order_not_a_path_check(self):
        # A PATH check does not avoid the Store stub: on Windows `where
        # python3` resolves the stub itself. What avoids it is trying uv
        # first, which is what both wrappers do -- so that is what they say
        # (F Q7).
        for name in ("install.sh", "install.cmd"):
            text = (install.REPO_ROOT / name).read_text(encoding="utf-8")
            comments = "\n".join(
                line for line in text.splitlines() if line.startswith(("#", "rem "))
            )
            with self.subTest(wrapper=name):
                self.assertNotIn("PATH check", comments)
                self.assertIn("uv", comments)
                self.assertIn("stub", comments)
class TestDeclaredPythonFloor(unittest.TestCase):
    """The supported floor lives in two places that have to agree:
    `install.MIN_PYTHON`, which enforces it at the one file a user runs
    directly, and AGENTS.md, which is what a contributor reads before
    running the checks. When they disagree a result gets recorded on an
    interpreter nobody supports and read as if it meant something, so the
    agreement is pinned rather than trusted."""

    def test_agents_md_states_the_floor_install_py_enforces(self):
        text = (install.REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        # Whitespace-normalized on purpose: AGENTS.md hard-wraps near 70
        # columns, so a line-anchored match reports failure on correct text
        # the moment someone rewraps the paragraph.
        flat = " ".join(text.split())
        stated = re.search(r"Python (\d+)\.(\d+) or newer", flat)
        self.assertIsNotNone(stated, "AGENTS.md names no minimum Python version")
        self.assertEqual(
            install.MIN_PYTHON,
            (int(stated.group(1)), int(stated.group(2))),
            "AGENTS.md and install.MIN_PYTHON disagree about the floor",
        )

    def test_floor_turns_an_unsupported_interpreter_away(self):
        # The guard runs at import time, so the only way to watch it fire is
        # a copy of the script whose floor sits above whatever is running
        # this test. Without this the constant is never demonstrated to stop
        # anything -- it is just a tuple nobody reads.
        source = (install.REPO_ROOT / "install.py").read_text(encoding="utf-8")
        unreachable = (sys.version_info[0], sys.version_info[1] + 1)
        mutated = source.replace(
            "MIN_PYTHON = %r" % (install.MIN_PYTHON,),
            "MIN_PYTHON = %r" % (unreachable,),
            1,
        )
        self.assertNotEqual(source, mutated, "no MIN_PYTHON literal to raise")
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "install.py"
            script.write_text(mutated, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(script), "--dry-run"],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(0, proc.returncode)
        message = proc.stdout + proc.stderr
        self.assertIn(f"{unreachable[0]}.{unreachable[1]} or newer", message)
        # Naming what is actually running is the difference between a
        # message someone can act on and one they have to investigate.
        self.assertIn(".".join(str(p) for p in sys.version_info[:3]), message)
class TestPluginSubsystemRemoved(unittest.TestCase):
    """Criterion 1: the Claude plugin distribution is dropped from the tree
    (preserved in git history). Kept as a structure guard (binding
    constraints keep structure guards; this asserts real repo/file state,
    not a module constant against itself) and strengthened to also check
    install.py's own source carries no reference back to the removed
    subsystem."""

    def test_plugin_subsystem_paths_are_absent(self):
        self.assertFalse((install.REPO_ROOT / "tools" / "build_plugin.py").exists())
        self.assertFalse((install.REPO_ROOT / "plugin").exists())
        self.assertFalse((install.REPO_ROOT / ".claude-plugin").exists())
        self.assertFalse((install.REPO_ROOT / "tests" / "test_plugin_build.py").exists())

    def test_install_py_source_has_no_plugin_subsystem_reference(self):
        source = (install.REPO_ROOT / "install.py").read_text(encoding="utf-8")
        self.assertNotIn("build_plugin", source)
        self.assertNotIn(".claude-plugin", source)
