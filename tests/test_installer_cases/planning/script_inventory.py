"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


class TestScriptNames(unittest.TestCase):
    """Behavioral replacement: SCRIPT_NAMES only matters if every named
    script actually reaches the installed bin dir with matching content --
    checking membership in the tuple two lines from its own declaration
    proved nothing about install.py's behavior."""

    def test_build_plan_installs_every_managed_script_with_matching_content(self):
        plan = relocated_user_install()[0]
        expected = install.discover_script_names(install.REPO_ROOT / "scripts")
        self.assertEqual(set(expected), {path.name for _, path in plan.scripts})
        for name in expected:
            installed = plan.bin_dir / name
            self.assertTrue(installed.is_file(), f"{name} was not installed to {plan.bin_dir}")
            source = install.REPO_ROOT / "scripts" / name
            self.assertEqual(source.read_bytes(), installed.read_bytes())

    def test_build_plan_ships_doclint_the_documentation_oracle(self):
        """The test above grades ``SCRIPT_NAMES`` against itself: drop a name
        and both sides of its assertion shrink together, so it stays green on
        a script the installer silently stopped shipping. ``doclint.py`` is
        the documentation factory's oracle and the bodies that invoke it name
        it by bare filename, which resolves only from the installed bin dir --
        so the name is pinned here, from outside the tuple."""

        plan = relocated_user_install()[0]
        installed = plan.bin_dir / "doclint.py"
        self.assertIn(
            installed,
            [destination for _, destination in plan.scripts],
            "the plan never carries doclint.py to the bin dir",
        )
        self.assertTrue(installed.is_file(), f"doclint.py never reached {plan.bin_dir}")
        source = install.REPO_ROOT / "scripts" / "doclint.py"
        self.assertEqual(source.read_bytes(), installed.read_bytes())

    def test_every_bare_script_a_template_stub_names_is_shipped(self):
        """A stub that says `python search_plan.py advance` is telling an
        executor to run a file the installed tree has to carry. The template
        names it by bare filename on purpose -- the path is the installer's
        business, not the stub's -- so the only thing standing between the
        instruction and a `No such file` is this list. `search_plan.py`
        crossed from a canonical skills/ directory to scripts/ and stopped
        shipping without a single check going red."""

        named = set()
        for path in sorted((install.REPO_ROOT / "compositions").rglob("*.md")):
            named.update(BARE_SCRIPT_RE.findall(path.read_text(encoding="utf-8")))
        self.assertTrue(named, "no template stub names a bare script; the grep is wrong")
        missing = sorted(name for name in named if name not in install.SCRIPT_NAMES)
        self.assertEqual(
            [],
            missing,
            f"template stubs name scripts the installer never ships: {missing}",
        )

    def test_the_installed_writers_resolve_their_sink_from_the_flat_layout(self):
        """The scripts land flat in one bin dir, with no ``scripts`` package
        above them. Copying the files is not enough: the two-arm import in
        ``tickets.py`` and ``friction.py`` has to find ``state_root.py``
        beside it, which only the installed layout proves."""

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            (home / ".claude").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis("claude"):
                plan = install.build_plan("user", None)
                install.apply_plan(plan)

            sink = home / "sink"
            elsewhere = home / "not-a-repo"
            elsewhere.mkdir()
            env = dict(os.environ, ORCHFLOWS_STATE_HOME=str(sink))

            def run(name, *args):
                return subprocess.run(
                    [sys.executable, str(plan.bin_dir / name), *args],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="replace", cwd=str(elsewhere), env=env,
                )

            noted = run("tickets.py", "run-state", "testrun", "--note", "installed")
            self.assertEqual(0, noted.returncode, noted.stderr)
            payload = json.loads(noted.stdout)
            self.assertNotIn("error", payload)
            worklog = sink / "runs" / "testrun" / "notes.md"
            self.assertEqual(str(worklog), payload["run_state"]["path"])
            self.assertEqual("installed\n", worklog.read_text(encoding="utf-8"))

            logged = run("friction.py", "observed", "expected")
            self.assertEqual(0, logged.returncode, logged.stderr)
            self.assertEqual("friction logged", logged.stdout.strip())
            self.assertEqual(1, len(list((sink / "friction").glob("*.jsonl"))))

            self.assertFalse((elsewhere / ".orch").exists())
            self.assertFalse((plan.bin_dir / ".orch").exists())
