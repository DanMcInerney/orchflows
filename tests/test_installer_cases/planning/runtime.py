"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


class TestRuntimeDirsSeedTheSink(unittest.TestCase):
    """The user install seeds the one user-scope sink."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.project = self.tmp / "project"
        (self.project / ".git").mkdir(parents=True)
        self.sink = self.home / ".orchflows" / "state"
        # The suite guard points ORCHFLOWS_STATE_HOME at a temporary sink for
        # every test in the process, and `_state_sink` honours it. These cases
        # are about the home-derived default, so they clear it for their own
        # duration — the documented single-call opt-out.
        guard = patch.dict(os.environ)
        guard.start()
        self.addCleanup(guard.stop)
        os.environ.pop(SINK_ENV_VAR, None)

    @staticmethod
    def under(root: Path, path: Path) -> bool:
        """Whole segments only: ``.orchflows`` is not under ``.orch``."""

        return path == root or root in path.parents

    def assert_under(self, root: Path, path: Path, why: str):
        self.assertTrue(self.under(root, path), f"{path}: {why}")

    def test_user_scope_seeds_the_sink(self):
        with patch.object(install.Path, "home", return_value=self.home):
            user = install._runtime_dirs("user", None)

        expected = [
            self.sink / "tickets",
            self.sink / "runs",
            self.sink / "friction",
            self.sink / "improvement" / "proposals",
        ]
        self.assertEqual(expected, list(user))
        for path in user:
            self.assert_under(self.sink, path, "seeded outside the sink")

    def test_the_override_redirects_what_an_install_seeds(self):
        """A user who redirects the sink gets the root they read seeded, and
        the suite's own redirect keeps a forgetful installer test off the real
        sink. A resolver the installer ignored would sit outside that guard."""

        elsewhere = self.tmp / "elsewhere"
        with patch.object(install.Path, "home", return_value=self.home), patch.dict(
            os.environ, {SINK_ENV_VAR: str(elsewhere)}
        ):
            seeded = install._runtime_dirs("user", None)
        # graded before anything this item introduced is named, so a can-fail
        # run reads as wrong behavior rather than as a missing attribute
        self.assertTrue(seeded)
        for path in seeded:
            self.assert_under(elsewhere, path, "the override was not honoured")

        for blank in ("", "   "):
            with patch.object(install.Path, "home", return_value=self.home), patch.dict(
                os.environ, {SINK_ENV_VAR: blank}
            ):
                self.assertEqual(self.sink, install._state_sink(), blank)
        self.assertEqual(SINK_ENV_VAR, install.STATE_HOME_ENV_VAR)

    def test_the_sink_it_seeds_is_the_one_the_scripts_resolve(self):
        """``install.py`` cannot import ``scripts/state_root.py``: it runs
        before any script is installed. That duplication is only safe while
        the two spellings agree, so they are compared against the owner
        rather than each against a literal of its own — the shape
        ``tests/test_suite_check.py`` already holds the other replica to."""

        sys.path.insert(0, str(install.REPO_ROOT / "scripts"))
        try:
            import state_root
        finally:
            sys.path.pop(0)
        self.assertEqual(state_root.ENV_VAR, install.STATE_HOME_ENV_VAR)
        self.assertEqual(
            state_root.DEFAULT_HOME_SUBPATH, install.STATE_SINK_SUBPATH
        )
        with patch.object(install.Path, "home", return_value=self.home), patch.dict(
            os.environ, {}, clear=False
        ):
            os.environ.pop(install.STATE_HOME_ENV_VAR, None)
            self.assertEqual(
                Path(state_root.state_root()), install._state_sink()
            )

    def test_the_bin_dir_is_unchanged_in_shape(self):
        """The installed entrypoint directory stays under user scope."""

        with patch.object(install.Path, "home", return_value=self.home):
            self.assertEqual(
                self.home / ".orchflows" / "bin", install._bin_dir("user", None)
            )
    def test_a_real_plan_writes_user_runtime_state_only(self):
        (self.home / ".claude").mkdir()
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("claude"):
            user_plan = install.build_plan("user", None)

        planned = set(user_plan.runtime_dirs)
        for name in ("tickets", "runs", "friction"):
            self.assertIn(self.sink / name, planned)
        self.assertIn(self.sink / "improvement" / "proposals", planned)
        self.assertNotIn(self.home / ".orchflows" / "friction", planned)

    def test_no_planned_line_names_a_dot_orch_friction_path(self):
        """Held mechanically against a temporary home, so it holds on a host
        whose real home differs from this one's."""

        (self.home / ".claude").mkdir()
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("claude"):
            plan = install.build_plan("user", None)
            printed = io.StringIO()
            with redirect_stdout(printed):
                install.print_plan(plan)
            for line in printed.getvalue().splitlines():
                self.assertNotIn(".orch/friction", line.replace(os.sep, "/"), line)
class TestClaudeAdapterSet(unittest.TestCase):
    """``--claude-adapters {all,four}``: the switch SPEC §7.2's routing
    benchmark measures. The compatibility selector ``four`` mints Claude
    skill adapters only for the shared bounded set; every other surface -- the flat by-name index,
    the Codex prompts and redirect skills, the role agents, the host block --
    is the same plan either way. ``all`` is the default and is what HEAD
    already planned."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / ".claude").mkdir(parents=True)
        (self.home / ".codex").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _plan(self, adapter_set=None):
        args = ("user", None) if adapter_set is None else ("user", None, adapter_set)
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis(
            "claude", "codex"
        ):
            return install.build_plan(*args)

    @staticmethod
    def _names(pairs):
        return {dest.parent.name for dest, _ in pairs}

    def test_the_shared_names_remain_the_reduced_claude_set(self):
        self.assertEqual(
            ("orch-spec", "orch-frontier", "fix"),
            install.SHARED_ADAPTER_NAMES,
        )

    def test_installer_description_says_codex_redirects_every_canonical_name(self):
        description = install.__doc__ or ""
        _, separator, codex_description = description.partition("- Codex ")
        self.assertTrue(separator, "Codex description paragraph is missing")
        codex_description = codex_description.partition("\n\n")[0]
        self.assertIn("one exact redirect skill", codex_description)
        self.assertIn("per discovered canonical skill or composition", codex_description)
        names = {path.parent.name for path in install.discover_packages()}
        self.assertNotIn("orch-build", names)

    def test_four_mints_exactly_the_shared_adapters(self):
        plan = self._plan("four")
        self.assertEqual(set(install.SHARED_ADAPTER_NAMES), self._names(plan.claude_adapters))
        self.assertEqual(3, len(plan.claude_adapters))

    def test_all_is_the_default_and_mints_every_package_and_template(self):
        default = self._plan()
        explicit = self._plan("all")
        expected = len(install.discover_packages()) + len(install.discover_templates())
        self.assertEqual(expected, len(default.claude_adapters))
        self.assertEqual(
            [(dest, content) for dest, content in default.claude_adapters],
            [(dest, content) for dest, content in explicit.claude_adapters],
        )
        self.assertLess(len(install.SHARED_ADAPTER_NAMES), expected)

    def test_four_changes_nothing_but_the_claude_adapter_list(self):
        every = self._plan("all")
        four = self._plan("four")
        self.assertEqual(every.by_name, four.by_name)
        self.assertEqual(every.codex_prompts, four.codex_prompts)
        self.assertEqual(every.codex_skills, four.codex_skills)
        self.assertEqual(every.claude_agents, four.claude_agents)
        self.assertEqual(every.codex_agents, four.codex_agents)
        self.assertEqual(every.lib_copies, four.lib_copies)
        self.assertEqual(every.scripts, four.scripts)
        self.assertEqual(every.blocks, four.blocks)
        self.assertEqual(every.host_block.content, four.host_block.content)

    def test_the_four_adapters_carry_the_same_content_they_carry_under_all(self):
        every = dict(self._plan("all").claude_adapters)
        for dest, content in self._plan("four").claude_adapters:
            self.assertEqual(every[dest], content)

    def test_the_plan_count_and_printout_follow_the_adapter_set(self):
        every = self._plan("all")
        four = self._plan("four")
        dropped = len(every.claude_adapters) - len(four.claude_adapters)
        self.assertEqual(
            install.plan_entry_count(every) - dropped, install.plan_entry_count(four)
        )
        printed = io.StringIO()
        with redirect_stdout(printed):
            install.print_plan(four)
        self.assertIn("Claude Code skill adapters (3)", printed.getvalue())

    def test_the_receipt_records_only_the_minted_adapters(self):
        plan = self._plan("four")
        # The library copy is the whole cost of an apply and nothing here
        # reads it; the adapter writes and the receipt are what is graded.
        plan.lib_copies = []
        with patch.object(install.Path, "home", return_value=self.home):
            receipt = install.apply_plan(plan, keep_role_agents=True)
        adapters = [
            entry for entry in receipt["files"] if entry["kind"] == "adapter"
        ]
        self.assertEqual(3, len(adapters))
        self.assertEqual(
            set(install.SHARED_ADAPTER_NAMES),
            {Path(entry["path"]).parent.name for entry in adapters},
        )

    def test_the_cli_defaults_to_all_and_carries_four_into_the_plan(self):
        def _dry_run(argv):
            with patch.object(install.Path, "home", return_value=self.home), mock_host_clis(
                "claude", "codex"
            ):
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    code = install.main(argv)
            self.assertEqual(0, code)
            return buffer.getvalue()

        every = len(install.discover_packages()) + len(install.discover_templates())
        self.assertIn(
            f"Claude Code skill adapters ({every})", _dry_run(["--user", "--dry-run"])
        )
        self.assertIn(
            f"Claude Code skill adapters ({every})",
            _dry_run(["--user", "--dry-run", "--claude-adapters", "all"]),
        )
        self.assertIn(
            "Claude Code skill adapters (3)",
            _dry_run(["--user", "--dry-run", "--claude-adapters", "four"]),
        )

    def test_the_parser_accepts_the_two_sets_and_refuses_any_other(self):
        parser = install.build_arg_parser()
        self.assertEqual("all", parser.parse_args(["--user"]).claude_adapters)
        for adapter_set in ("all", "four"):
            self.assertEqual(
                adapter_set,
                parser.parse_args(["--user", "--claude-adapters", adapter_set]).claude_adapters,
            )
        with self.assertRaises(SystemExit) as raised, redirect_stderr(io.StringIO()):
            parser.parse_args(["--user", "--claude-adapters", "some"])
        self.assertEqual(2, raised.exception.code)

    def test_without_a_grok_cli_no_grok_entry_is_planned_and_nothing_else_moves(self):
        """Detecting Grok adds Grok entries and moves nothing else.

        On this class because its subject is already the same one: which
        surfaces are the same plan either way. Its home is this suite's, not
        a mixin's -- see the collection note in ``scoped_hosts.py``.
        """

        with isolated_grok_home(self.home) as grok_home, patch.object(
            install.Path, "home", return_value=self.home
        ):
            with mock_host_clis("claude", "codex"):
                without = install.build_plan("user", None)
            with mock_host_clis("claude", "codex", "grok"):
                with_grok = install.build_plan("user", None)

        self.assertEqual((False, True), (without.grok_enabled, with_grok.grok_enabled))
        self.assertEqual(
            ([], [], None, []),
            (
                without.grok_skills,
                without.grok_agents,
                without.grok_rules,
                [entry for entry in without.configs if entry.kind == "grok-config"],
            ),
        )
        # Planning writes nothing, on either side of the detection.
        self.assertFalse((grok_home / "skills").exists())

        for name in (
            "claude_adapters", "codex_prompts", "codex_skills", "by_name",
            "claude_agents", "codex_agents", "blocks", "host_block", "claude_import",
        ):
            self.assertEqual(getattr(without, name), getattr(with_grok, name), name)
        self.assertEqual(
            [(entry.dest, entry.content) for entry in without.configs],
            [(e.dest, e.content) for e in with_grok.configs if e.kind != "grok-config"],
        )
        # The Grok half is counted, so a dry run states what it would write.
        self.assertEqual(
            install.plan_entry_count(without)
            + len(with_grok.grok_skills)
            + len(with_grok.grok_agents)
            + 2,
            install.plan_entry_count(with_grok),
        )
