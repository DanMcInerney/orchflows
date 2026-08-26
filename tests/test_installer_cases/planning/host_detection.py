"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


class TestHostAutoDetection(unittest.TestCase):
    """Configure only hosts whose runnable CLI is discoverable on PATH."""

    def test_state_directories_are_not_installation_signals(self):
        with tempfile.TemporaryDirectory() as tmp, mock_host_clis():
            home = Path(tmp)
            (home / ".claude").mkdir()
            (home / ".codex").mkdir()

            self.assertEqual((False, False, False), install.detect_hosts(home))

    def test_each_cross_platform_cli_candidate_enables_its_host(self):
        cases = (
            ("claude", (True, False, False)),
            ("claude.exe", (True, False, False)),
            ("claude.cmd", (True, False, False)),
            ("codex", (False, True, False)),
            ("codex.exe", (False, True, False)),
            ("codex.cmd", (False, True, False)),
            ("grok", (False, False, True)),
            ("grok.exe", (False, False, True)),
            ("grok.cmd", (False, False, True)),
        )
        for executable, expected in cases:
            with self.subTest(executable=executable), patch.object(
                install.shutil,
                "which",
                side_effect=lambda candidate, executable=executable: (
                    str(Path("mock-bin") / candidate) if candidate == executable else None
                ),
            ):
                self.assertEqual(expected, install.detect_hosts())

    def test_both_clis_enable_both_hosts_before_state_directories_exist(self):
        with mock_host_clis("claude", "codex"):
            self.assertEqual(
                (True, True, False), install.detect_hosts(Path("missing-home"))
            )

    def test_every_cli_enables_every_host_before_state_directories_exist(self):
        with mock_host_clis("claude", "codex", "grok"):
            self.assertEqual(
                (True, True, True), install.detect_hosts(Path("missing-home"))
            )

    def test_a_grok_home_is_not_an_installation_signal_without_the_cli(self):
        """The Grok signal is the CLI, exactly as it is for the other two.

        A ``GROK_HOME`` an agent runtime left behind, or a bare ``~/.grok``,
        says nothing about whether a grok CLI is runnable here.
        """

        with tempfile.TemporaryDirectory() as tmp, mock_host_clis("claude"):
            root = Path(tmp)
            (root / ".grok").mkdir()
            with isolated_grok_home(root) as grok_home:
                (grok_home / "skills").mkdir()

                self.assertEqual(
                    (True, False, False), install.detect_hosts(root)
                )

    def test_protected_stale_codex_directory_is_ignored_without_codex_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            stale_codex = home / ".codex"
            stale_codex.mkdir()
            real_mkdir = Path.mkdir

            def reject_codex_writes(path, *args, **kwargs):
                if path == stale_codex or stale_codex in path.parents:
                    raise PermissionError(13, "Permission denied", str(path))
                return real_mkdir(path, *args, **kwargs)

            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "claude"
            ), patch.object(Path, "mkdir", autospec=True, side_effect=reject_codex_writes):
                result = install.main(["--user", "--yes"])

            self.assertEqual(0, result)
            self.assertFalse((stale_codex / "prompts").exists())
            self.assertTrue((home / ".claude" / "CLAUDE.md").is_file())

    def test_neither_host_present_returns_success_with_no_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis():
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    result = install.main(["--user", "--yes"])

            self.assertEqual(0, result)
            self.assertIn("warning:", buffer.getvalue())
            self.assertIn("nothing was installed", buffer.getvalue())
            self.assertEqual([], list(home.iterdir()))

    def test_neither_host_present_dry_run_returns_success_with_no_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis():
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    result = install.main(["--user", "--dry-run"])

            self.assertEqual(0, result)
            self.assertIn("warning:", buffer.getvalue())
            self.assertIn("nothing was installed", buffer.getvalue())
            self.assertEqual([], list(home.iterdir()))

    def test_only_claude_present_builds_claude_half_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis("claude"):
                plan = install.build_plan("user", None)

            self.assertTrue(plan.claude_enabled)
            self.assertFalse(plan.codex_enabled)
            self.assertTrue(plan.claude_adapters)
            self.assertTrue(plan.claude_agents)
            self.assertIsNotNone(plan.host_block)
            self.assertIsNotNone(plan.claude_import)
            self.assertEqual([], plan.codex_prompts)
            self.assertEqual([], plan.codex_skills)
            self.assertEqual([], plan.codex_agents)
            self.assertEqual([], plan.blocks)
            self.assertEqual([], plan.warnings)
            self.assertEqual({"claude-config"}, {config.kind for config in plan.configs})

    def test_only_codex_present_builds_codex_half_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis("codex"):
                plan = install.build_plan("user", None)

            self.assertFalse(plan.claude_enabled)
            self.assertTrue(plan.codex_enabled)
            self.assertEqual([], plan.claude_adapters)
            self.assertEqual([], plan.claude_agents)
            self.assertIsNone(plan.host_block)
            self.assertIsNone(plan.claude_import)
            self.assertTrue(plan.codex_prompts)
            self.assertTrue(plan.codex_agents)
            self.assertEqual(1, len(plan.blocks))
            self.assertEqual({"codex-config"}, {config.kind for config in plan.configs})

    def test_dry_run_prints_what_it_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis("claude"):
                plan = install.build_plan("user", None)
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    install.print_plan(plan)

            output = buffer.getvalue()
            self.assertIn("detected Claude Code CLI: yes", output)
            self.assertIn("detected Codex CLI: no", output)
class DryRunOracleTest(unittest.TestCase):
    """``python install.py --dry-run`` is one of the four required checks.

    It used to return a bare 0 whether it had planned the entire install or
    nothing at all: with no host CLI on PATH -- the state of every CI runner
    -- ``main`` returned before printing any plan, so a green run claimed
    only that argv parsed and the module imported. These oracles pin what a
    green dry run now asserts about the plan it printed.
    """

    _COUNT = re.compile(r"^planned entries: (\d+)$", re.MULTILINE)

    def _dry_run(self, home: Path, *hosts: str) -> tuple[int, str]:
        with patch.object(install.Path, "home", return_value=home), mock_host_clis(*hosts):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = install.main(["--user", "--dry-run"])
        return code, buffer.getvalue()

    def _planned_entries(self, output: str) -> int:
        found = self._COUNT.search(output)
        self.assertIsNotNone(found, "dry run printed no planned-entry count:\n" + output)
        return int(found.group(1))

    def test_a_dry_run_with_no_host_enabled_is_distinguishable(self):
        with tempfile.TemporaryDirectory() as tmp:
            no_host_home = Path(tmp) / "no-host"
            claude_home = Path(tmp) / "claude"
            no_host_home.mkdir()
            claude_home.mkdir()

            no_host_code, no_host_output = self._dry_run(no_host_home)
            claude_code, claude_output = self._dry_run(claude_home, "claude")

        # Both exit 0 on purpose: CI runners carry neither CLI, and this
        # repository's own required check has to stay green. What separates
        # the two runs is what each says about its plan, not its status.
        self.assertEqual(0, no_host_code)
        self.assertEqual(0, claude_code)

        self.assertEqual(0, self._planned_entries(no_host_output))
        self.assertGreater(self._planned_entries(claude_output), 0)
        self.assertIn("detected Claude Code CLI: no", no_host_output)
        self.assertIn("detected Claude Code CLI: yes", claude_output)

    def test_the_printed_plan_is_non_empty_when_a_host_is_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._dry_run(Path(tmp), "claude", "codex")

        self.assertEqual(0, code)
        self.assertGreater(self._planned_entries(output), 0)
        for heading in ("library files (", "scripts (", "Claude Code role agents ("):
            self.assertIn(heading, output)

        # Can-fail, built beside the tree: a planner that detected a host and
        # planned nothing is exactly the silence this criterion exists to
        # break. The wrong result is a stub Plan, never a mutation of the
        # tree under test.
        empty = install.Plan(
            scope="user",
            project_root=None,
            lib_home=Path("unused") / "lib",
            scope_home=Path("unused") / "scope",
            bin_dir=Path("unused") / "bin",
            receipt_path=Path("unused") / "receipt.json",
            claude_enabled=True,
            codex_enabled=False,
        )
        with patch.object(install, "build_plan", return_value=empty):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                empty_code = install.main(["--user", "--dry-run"])

        self.assertNotEqual(0, empty_code)
        self.assertEqual(0, self._planned_entries(buffer.getvalue()))

    def test_dry_run_writes_nothing(self):
        def snapshot(root: Path) -> dict:
            return {
                str(path.relative_to(root)): digest(path) if path.is_file() else "<dir>"
                for path in sorted(root.rglob("*"))
            }

        with tempfile.TemporaryDirectory() as tmp:
            # A sandboxed destination, populated so there is something a
            # write could disturb. The tree under test is never the target.
            home = Path(tmp) / "home"
            (home / ".claude").mkdir(parents=True)
            (home / ".codex").mkdir(parents=True)
            (home / ".claude" / "CLAUDE.md").write_text("# mine\n", encoding="utf-8")
            before = snapshot(home)

            code, _ = self._dry_run(home, "claude", "codex")

            self.assertEqual(0, code)
            self.assertEqual(before, snapshot(home))

            # Can-fail: the same comparison against a real install into the
            # same sandboxed home must differ, or the equality above would
            # hold just as well for a dry run that wrote the lot.
            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "claude", "codex"
            ):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    install.main(["--user", "--yes"])

            self.assertNotEqual(before, snapshot(home))
