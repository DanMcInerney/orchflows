"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

import ast

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
        # The suite guard points the sink env var at a temporary sink for
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
            user = install._runtime_dirs()

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
            seeded = install._runtime_dirs()
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
        """``install.STATE_HOME_ENV_VAR`` and ``install.STATE_SINK_SUBPATH``
        are ``scripts.state_root``'s own constants, imported rather than
        restated (spec unit U4) — this proves the seeded sink is the one
        the installed scripts resolve, not merely that two independent
        spellings happen to agree."""

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
                self.home / ".orchflows" / "bin", install._bin_dir()
            )
    def test_a_real_plan_writes_user_runtime_state_only(self):
        (self.home / ".claude").mkdir()
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis("claude"):
            user_plan = install.build_plan()

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
            plan = install.build_plan()
            printed = io.StringIO()
            with redirect_stdout(printed):
                install.print_plan(plan)
            for line in printed.getvalue().splitlines():
                self.assertNotIn(".orch/friction", line.replace(os.sep, "/"), line)
class TestClaudeAdapters(unittest.TestCase):
    """Claude gets one skill adapter per canonical name: every package and
    every workflow, with no selector to mint fewer."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name)
        (self.home / ".claude").mkdir(parents=True)
        (self.home / ".codex").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _plan(self):
        with patch.object(install.Path, "home", return_value=self.home), mock_host_clis(
            "claude", "codex"
        ):
            return install.build_plan()

    def test_every_package_and_workflow_gets_one_claude_adapter(self):
        plan = self._plan()
        expected = len(install.discover_packages()) + len(install.discover_workflow_skills())
        self.assertEqual(expected, len(plan.claude_adapters))
        printed = io.StringIO()
        with redirect_stdout(printed):
            install.print_plan(plan)
        self.assertIn(f"Claude Code skill adapters ({expected})", printed.getvalue())

    def test_no_flag_selects_a_smaller_adapter_set(self):
        """One adapter per canonical name is the whole rule: the parser
        offers no selector for a smaller set and refuses one."""

        parser = install.build_arg_parser()
        rendered = parser.format_help()
        self.assertNotIn("claude-adapters", rendered)
        self.assertNotIn("orch-do", rendered)
        with self.assertRaises(SystemExit) as raised, redirect_stderr(io.StringIO()):
            parser.parse_args(["--user", "--claude-adapters", "four"])
        self.assertEqual(2, raised.exception.code)

    def test_installer_description_says_codex_redirects_every_canonical_name(self):
        codex_description = doc_bullet(install.__doc__, "- Codex ")
        self.assertTrue(codex_description, "Codex description bullet is missing")
        self.assertIn("one exact redirect skill", codex_description)
        self.assertIn("per discovered canonical skill or composition", codex_description)
        names = {path.parent.name for path in install.discover_packages()}
        self.assertNotIn("orch-build", names)

    @staticmethod
    def _hosts_named(sentence):
        """The hosts one surface's opening sentence lists, in order."""

        listed = sentence.partition("orchflows for ")[2].partition(" from ")[0].rstrip(".")
        return tuple(part.strip() for part in re.split(r",| and ", listed) if part.strip())

    def test_help_names_the_hosts_the_module_docstring_names(self):
        """``--help`` is a host-facing surface the docstring guards never read.

        The two are compared as lists rather than as one string: each keeps
        its own sentence, and only the host list is shared. The literal
        triple anchors the comparison -- without it a parser extractor that
        returned nothing would pass against a docstring it never parsed.
        """

        docstring_hosts = self._hosts_named(doc_sentence(install.__doc__))
        self.assertEqual(("Claude Code", "Codex", "Grok Build"), docstring_hosts)
        parser = install.build_arg_parser()
        self.assertEqual(docstring_hosts, self._hosts_named(parser.description or ""))
        rendered = " ".join(parser.format_help().split())
        for host in docstring_hosts:
            self.assertIn(host, rendered)

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
                without = install.build_plan()
            with mock_host_clis("claude", "codex", "grok"):
                with_grok = install.build_plan()

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


class TestInstallerDescriptionSurvivesRewrap(unittest.TestCase):
    """Every assertion over ``install.__doc__`` reads words, not wrap.

    Three facts are pinned off that docstring: the Codex redirect claim
    asserted above, the absence of the killed stdlib-only claim asserted in
    ``planning/private_runtime.py``, and the host list its opening sentence
    names. All three are prose pinned by substring, and where a line break
    falls in prose is a fact about the source column limit rather than
    about the installer -- so each is held here to the same docstring
    reflowed at five column limits, and to the mutant that must still fail
    it. 60 earns its place among those limits: it is the one that puts a
    line break inside the summary's host list.

    The negatives are anchored on something the docstring really says. A
    normaliser that stripped its input to nothing would leave every
    ``assertNotIn`` reading it green, which is the one way this whole class
    could pass while checking nothing.
    """

    WIDTHS = (60, 66, 72, 78, 88)

    def codex_bullet(self, docstring, width):
        """What ``TestClaudeAdapterSet``'s Codex assertion reads, rewrapped."""

        return doc_bullet(rewrapped_doc(docstring, width), "- Codex ")

    def stdlib_claims(self, docstring, width):
        """What ``RuntimeVenvTests``' stdlib assertion reads, rewrapped."""

        return doc_claim(rewrapped_doc(docstring, width))

    def test_the_codex_claims_survive_every_lawful_rewrap(self):
        for width in self.WIDTHS:
            with self.subTest(width=width):
                codex = self.codex_bullet(install.__doc__, width)
                self.assertIn("one exact redirect skill", codex)
                self.assertIn("per discovered canonical skill or composition", codex)

    def test_a_changed_codex_claim_still_fails_at_every_rewrap(self):
        mutant = install.__doc__.replace(
            "one exact redirect skill", "one shared redirect skill", 1
        )
        self.assertNotEqual(normalised_doc(install.__doc__), normalised_doc(mutant))
        for width in self.WIDTHS:
            with self.subTest(width=width):
                self.assertNotIn(
                    "one exact redirect skill", self.codex_bullet(mutant, width)
                )

    def test_the_stdlib_claim_stays_absent_at_every_rewrap(self):
        """Anchored, because a negative assertion passes over empty text.

        `doc_claim` could strip its input to nothing and every ``assertNotIn``
        reading it would still report green. So each width is asked for a
        phrase the docstring really carries before it is asked what it does
        not carry.
        """

        for width in self.WIDTHS:
            with self.subTest(width=width):
                claims = self.stdlib_claims(install.__doc__, width)
                self.assertIn("pathlib throughout, never symlinks", claims)
                self.assertNotIn("stdlib only", claims)

    def test_a_restated_stdlib_claim_still_fails_however_it_is_spelled(self):
        for spelling in ("Stdlib-only", "stdlib-only", "Stdlib only"):
            mutant = install.__doc__.replace(
                "Cross-platform", spelling + ", cross-platform", 1
            )
            self.assertNotEqual(normalised_doc(install.__doc__), normalised_doc(mutant))
            for width in self.WIDTHS:
                with self.subTest(spelling=spelling, width=width):
                    self.assertIn("stdlib only", self.stdlib_claims(mutant, width))

    def test_a_true_sentence_about_the_stdlib_is_not_the_killed_claim(self):
        """The negative discriminates, rather than refusing a word.

        ``install.py`` really does import nothing outside the stdlib -- it
        is the runtime it builds that carries pinned dependencies -- so a
        docstring saying so must pass. An assertion that refused ``stdlib``
        outright would be a wall around a true sentence.
        """

        true_sentence = install.__doc__.replace(
            "Cross-platform",
            "It imports only the stdlib and builds a runtime that does not."
            " Cross-platform",
            1,
        )
        for width in self.WIDTHS:
            with self.subTest(width=width):
                self.assertNotIn(
                    "stdlib only", self.stdlib_claims(true_sentence, width)
                )

    def test_the_opening_sentence_keeps_every_host_at_every_rewrap(self):
        """The summary's host list, which ``splitlines()[0]`` breaks on reflow.

        Read as a line, the sentence is whole only while the wrap agrees.
        At 60 columns the real docstring's summary breaks after ``from``,
        so a reader that stops at the line keeps all three hosts but loses
        the clause that ends them -- and an extractor delimiting on ``
        from `` then hands back ``Grok Build from``. The literal triple
        anchors this, so a `doc_sentence` that parsed nothing cannot pass
        on empty text.
        """

        for width in self.WIDTHS:
            with self.subTest(width=width):
                sentence = doc_sentence(rewrapped_doc(install.__doc__, width))
                for host in ("Claude Code", "Codex", "Grok Build"):
                    self.assertIn(host, sentence)
                self.assertTrue(sentence.endswith("from a git clone."), sentence)
                self.assertNotIn("Cross-platform", sentence)

    def test_reading_the_opening_sentence_as_a_line_loses_its_tail(self):
        """The can-fail direction: what a reflow does to ``splitlines()[0]``.

        Spelled as a literal rather than read off ``install.__doc__``,
        because this is the one test whose subject is raw text -- reading
        the real docstring here would be the very shape the guard below
        refuses, and rightly so.
        """

        summary = (
            "Install orchflows for Claude Code, Codex and Grok Build"
            " from a git clone.\n\nA second paragraph, so the summary ends.\n"
        )
        first_line = rewrapped_doc(summary, 40).splitlines()[0]
        self.assertIn("Claude Code", first_line)
        self.assertNotIn("Grok Build", first_line)
        self.assertEqual(summary.partition("\n")[0], doc_sentence(summary))
        self.assertIn("Grok Build", doc_sentence(rewrapped_doc(summary, 40)))

    def test_no_test_in_the_tree_asserts_over_the_raw_installer_docstring(self):
        """Read off the tree, so a later assertion cannot reopen the hazard."""

        offenders = [
            f"{path.relative_to(install.REPO_ROOT).as_posix()}:{line} ({name})"
            for path in sorted((install.REPO_ROOT / "tests").rglob("*.py"))
            for name, line in raw_doc_assertions(
                ast.parse(path.read_text(encoding="utf-8"))
            )
        ]
        self.assertEqual([], offenders, "assert over normalised text instead")

    def test_the_enumeration_names_both_shapes_the_two_broken_sessions_had(self):
        """Inline, and reached through a local -- the shape that got missed."""

        inline = 'self.assertNotIn("Stdlib-only", install.__doc__ or "")\n'
        self.assertEqual([("assertNotIn", 1)], raw_doc_assertions(ast.parse(inline)))
        through_a_local = (
            'description = install.__doc__ or ""\n'
            '_, separator, codex = description.partition("- Codex ")\n'
            'self.assertTrue(separator, "missing")\n'
            'codex = codex.partition("\\n\\n")[0]\n'
            'self.assertIn("one exact redirect skill", codex)\n'
        )
        self.assertEqual(
            [("assertTrue", 3), ("assertIn", 5)],
            raw_doc_assertions(ast.parse(through_a_local)),
        )
        normalised = (
            'codex = doc_bullet(install.__doc__, "- Codex ")\n'
            'self.assertIn("one exact redirect skill", codex)\n'
            'self.assertNotIn("stdlib only", doc_claim(install.__doc__))\n'
        )
        self.assertEqual([], raw_doc_assertions(ast.parse(normalised)))
