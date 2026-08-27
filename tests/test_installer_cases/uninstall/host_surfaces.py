"""Uninstall cases that grade the three hosts against each other."""

from __future__ import annotations

from ..support import *  # noqa: F403

from installer import uninstall


class TestHostSurfaceUninstall(unittest.TestCase):
    """The surfaces every host has, removed on terms that must not differ.

    ``TestConservativeUninstall`` grades one receipt entry at a time against
    the hash and boundary gates. What it cannot see is a gate that admits one
    host's copy of a surface and refuses another's for no reason but which
    run wrote it -- so each case here is written once and run per host.
    """

    # --- role agents ------------------------------------------------------

    _ROLE_AGENTS = (
        ("claude-agent", "CLAUDE_CONFIG_DIR", "orch-planner.md", "Claude role agent"),
        ("codex-agent", "CODEX_HOME", "orch-worker.toml", "Codex role agent"),
        ("grok-agent", "GROK_HOME", "orch-worker.md", "Grok role agent"),
    )

    def _seeded_role_agents(self, root: Path):
        """One installer-written role agent per host, and the env that finds it.

        Each host's agents directory is reached through the variable that
        relocates that host's home, so all three land inside ``root`` and the
        boundary check sees the same directory the installer would have
        written to. Returns the paths by kind and the environment to patch.
        """

        agents, environment = {}, {}
        for kind, env_var, filename, _noun in self._ROLE_AGENTS:
            host_home = root / kind
            environment[env_var] = str(host_home)
            agent = host_home / "agents" / filename
            agent.parent.mkdir(parents=True)
            agent.write_text(f"{kind} binding\n", encoding="utf-8")
            agents[kind] = agent
        return agents, environment

    def test_every_hosts_role_agent_is_removed_on_the_same_terms(self):
        """Grok's role agents were auto-removable from the day they landed and
        Claude's and Codex's were not.

        That gap was one run's write exclusion, not a property of the files:
        all three are whole files this installer creates under a directory it
        owns, and all three stay gated on the receipt's recorded hash. The
        case runs the three together, so widening one host and forgetting
        another fails here.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents, environment = self._seeded_role_agents(root)
            receipt_path = root / ".orchflows" / "receipt.json"
            receipt_path.parent.mkdir(parents=True)
            receipt_path.write_text(
                json.dumps(
                    {
                        "files": [
                            {
                                "path": str(path),
                                "kind": kind,
                                "install_action": "created",
                                "sha256": digest(path),
                            }
                            for kind, path in agents.items()
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict(os.environ, environment), patch.object(
                install.Path, "home", return_value=root
            ):
                report = install.run_uninstall("user", None, dry_run=False)

            removed = {entry["path"]: entry["action"] for entry in report["skill_actions"]}
            for kind, _env_var, _filename, noun in self._ROLE_AGENTS:
                with self.subTest(kind=kind):
                    self.assertFalse(agents[kind].exists())
                    self.assertEqual(f"removed unchanged {noun}", removed[str(agents[kind])])
            self.assertEqual(
                [str(receipt_path)], [entry["path"] for entry in report["manual_actions"]]
            )

    def test_a_role_agent_edited_since_the_install_is_left_for_review(self):
        """The hash gate is what makes the widening safe, on every host.

        A machine running a deliberately different binding is the ordinary
        reason a role agent differs, and the install flow already asks before
        replacing one. The uninstall never asks, so it must not guess.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents, environment = self._seeded_role_agents(root)
            files = [
                {
                    "path": str(path),
                    "kind": kind,
                    "install_action": "created",
                    "sha256": digest(path),
                }
                for kind, path in agents.items()
            ]
            for path in agents.values():
                path.write_text("hand-tuned binding\n", encoding="utf-8")
            receipt_path = root / ".orchflows" / "receipt.json"
            receipt_path.parent.mkdir(parents=True)
            receipt_path.write_text(json.dumps({"files": files}), encoding="utf-8")

            with patch.dict(os.environ, environment), patch.object(
                install.Path, "home", return_value=root
            ):
                report = install.run_uninstall("user", None, dry_run=False)

            manual = {entry["path"]: entry["action"] for entry in report["manual_actions"]}
            for kind, _env_var, _filename, noun in self._ROLE_AGENTS:
                with self.subTest(kind=kind):
                    self.assertTrue(agents[kind].is_file())
                    self.assertEqual(
                        f"review {noun} file; modified since install; not removed",
                        manual[str(agents[kind])],
                    )
            self.assertEqual([], report["skill_actions"])

    # --- the set and its boundaries ---------------------------------------

    def test_every_auto_removable_kind_names_the_directory_it_may_be_removed_from(self):
        """The kind set and the boundary table are one fact in two files.

        A kind widened onto ``AUTO_REMOVE_KINDS`` with no boundary of its own
        used to fall through to the Codex prompts directory -- which refuses
        it, silently and for the wrong reason. Equality here is what says so.
        """

        self.assertEqual(
            set(install.AUTO_REMOVE_KINDS), set(uninstall._AUTO_REMOVE_BOUNDARIES)
        )

    def test_every_auto_removable_host_config_comes_back_out_by_key(self):
        """A config the uninstall removes automatically is never deleted.

        Both are files the host's own CLI writes as well, so both have to be
        lifted key by key. This is the check that was missing when only Grok's
        removal existed: Codex's block rode along on the shared render and
        nothing said its removal had to.
        """

        self.assertEqual(
            {kind for kind in install.AUTO_REMOVE_KINDS if kind.endswith("-config")},
            set(uninstall._LIMIT_REMOVALS),
        )

    # --- host TOML configs -----------------------------------------------

    def _config_hosts(self):
        """The two hosts whose config the installer merges a block into.

        Each is one row: the receipt kind, the environment variable that
        relocates that host's home, the markers, the keys the installer's own
        render writes, and what the report calls the block. The Grok cases
        further down grade one real install end to end; these grade the two
        hosts against each other, which is the thing no single-host case can
        see.
        """

        return (
            (
                "codex-config",
                "CODEX_HOME",
                install.CODEX_LIMITS_START,
                install.CODEX_LIMITS_END,
                "agents.max_threads = 20\nagents.max_depth = 1\n",
                "Codex config",
                "managed agent limits block",
            ),
            (
                "grok-config",
                "GROK_HOME",
                install.GROK_LIMITS_START,
                install.GROK_LIMITS_END,
                "subagents.max_concurrent = 20\nsubagents.max_depth = 1\n",
                "Grok config",
                "managed subagent limits block",
            ),
        )

    def _config_receipt(self, root: Path, config: Path, kind: str) -> Path:
        receipt_path = root / ".orchflows" / "receipt.json"
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(
            json.dumps(
                {
                    "files": [
                        {
                            "path": str(config),
                            "kind": kind,
                            "install_action": "created",
                            "sha256": digest(config),
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return receipt_path

    def test_a_managed_config_block_comes_out_and_the_hosts_own_table_stays(self):
        """Neither host's config is the installer's file to delete.

        Both merge into a file the host's own CLI writes, and a TOML editor
        appending a table at the end of the document body lands it *inside*
        the trailing END comment. So both removals take back their own keys
        and leave the rest of the document standing.
        """

        for kind, env_var, start, end, keys, _noun, block in self._config_hosts():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                host_home = root / kind
                host_home.mkdir()
                config = host_home / "config.toml"
                config.write_text(
                    '[permission]\nmode = "ask"\n'
                    f"{start}\n{keys}[marketplace]\nappended = true\n{end}\n",
                    encoding="utf-8",
                )
                receipt_path = self._config_receipt(root, config, kind)

                with patch.dict(os.environ, {env_var: str(host_home)}), patch.object(
                    install.Path, "home", return_value=root
                ):
                    report = install.run_uninstall("user", None, dry_run=False)

                self.assertTrue(config.is_file())
                remaining = config.read_text(encoding="utf-8")
                for gone in (start, end) + tuple(keys.splitlines()):
                    self.assertNotIn(gone, remaining)
                self.assertIn('mode = "ask"', remaining)
                self.assertIn("appended = true", remaining)
                self.assertEqual(
                    [{"path": str(config), "action": f"removed the {block} from {_noun}"}],
                    report["skill_actions"],
                )
                self.assertEqual(
                    [str(receipt_path)], [entry["path"] for entry in report["manual_actions"]]
                )

    def test_a_managed_config_holding_nothing_else_goes_with_its_block(self):
        for kind, env_var, start, end, keys, noun, _block in self._config_hosts():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                host_home = root / kind
                host_home.mkdir()
                config = host_home / "config.toml"
                config.write_text(f"{start}\n{keys}{end}\n", encoding="utf-8")
                self._config_receipt(root, config, kind)

                with patch.dict(os.environ, {env_var: str(host_home)}), patch.object(
                    install.Path, "home", return_value=root
                ):
                    dry = install.run_uninstall("user", None, dry_run=True)
                    self.assertTrue(config.is_file())
                    report = install.run_uninstall("user", None, dry_run=False)

                self.assertFalse(config.exists())
                self.assertEqual(
                    f"would remove {noun} written by the installer", dry["skill_actions"][0]["action"]
                )
                self.assertEqual(
                    f"removed {noun} written by the installer", report["skill_actions"][0]["action"]
                )

    def test_a_managed_config_without_its_block_is_left_for_review(self):
        for kind, env_var, _start, _end, _keys, noun, block in self._config_hosts():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                host_home = root / kind
                host_home.mkdir()
                config = host_home / "config.toml"
                config.write_text('[permission]\nmode = "ask"\n', encoding="utf-8")
                self._config_receipt(root, config, kind)

                with patch.dict(os.environ, {env_var: str(host_home)}), patch.object(
                    install.Path, "home", return_value=root
                ):
                    report = install.run_uninstall("user", None, dry_run=False)

                self.assertTrue(config.is_file())
                self.assertEqual([], report["skill_actions"])
                self.assertIn(
                    f"review {noun}; the {block} is not in it; not changed",
                    [entry["action"] for entry in report["manual_actions"]],
                )

