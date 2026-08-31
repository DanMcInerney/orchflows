"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403
from tools import render_hosts


class HostAdapterRenderingTest(unittest.TestCase):
    def test_repository_adapters_are_a_deterministic_render_of_host_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            rendered = Path(tmp) / "adapters"

            first = render_hosts.render_all(install.HOSTS_DIR, rendered)
            first_bytes = {
                path.name: path.read_bytes() for path in sorted(rendered.glob("*.json"))
            }
            second = render_hosts.render_all(install.HOSTS_DIR, rendered)

            self.assertEqual(("claude", "codex", "grok"), tuple(first))
            self.assertEqual(first, second)
            self.assertEqual(
                first_bytes,
                {path.name: path.read_bytes() for path in sorted(rendered.glob("*.json"))},
            )
            self.assertEqual(
                first_bytes,
                {
                    path.name: path.read_bytes()
                    for path in sorted(install.HOST_ADAPTERS_DIR.glob("*.json"))
                },
            )
            render_hosts.check_all(
                install.HOSTS_DIR,
                install.HOST_ADAPTERS_DIR,
                install.HOST_BLOCK_TEMPLATE,
            )

    def test_each_host_record_carries_the_complete_binding_shape(self):
        hosts = render_hosts.load_sources(install.HOSTS_DIR)

        self.assertEqual({"claude", "codex", "grok"}, set(hosts))
        for name, host in hosts.items():
            with self.subTest(host=name):
                self.assertEqual(name, host["id"])
                self.assertTrue(host["managed_markers"])
                self.assertTrue(host["installed_items"])
                self.assertTrue(host["frontmatter"]["legal_keys"])
                self.assertTrue(host["launch"]["verb"])
                self.assertEqual({"planner", "worker"}, set(host["role_profiles"]))
                self.assertEqual(
                    {"isolation", "effort"}, set(host["capabilities"])
                )
                self.assertLessEqual(
                    set(host["capabilities"].values()), {"native", "requested"}
                )

    def test_same_target_marker_collision_is_refused_before_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "hosts"
            shutil.copytree(install.HOSTS_DIR, source)
            codex_path = source / "codex.json"
            codex = json.loads(codex_path.read_text(encoding="utf-8"))
            blocks = list(codex["managed_markers"].values())
            self.assertGreaterEqual(len(blocks), 2)
            blocks[1]["target"] = blocks[0]["target"]
            blocks[1]["start"] = blocks[0]["start"]
            codex_path.write_text(json.dumps(codex), encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError, "codex: managed marker collision"
            ):
                render_hosts.render_all(source, Path(tmp) / "adapters")

    def test_installer_profiles_and_markers_come_from_rendered_adapters(self):
        adapters = install.load_host_adapters()
        profiles = install.load_role_profiles()

        self.assertEqual(
            adapters["codex"]["role_profiles"]["planner"]["binding"],
            profiles["orch-planner"]["codex"],
        )
        self.assertEqual(
            adapters["claude"]["role_profiles"]["worker"]["binding"],
            profiles["orch-worker"]["claude"],
        )
        self.assertEqual(
            adapters["grok"]["managed_markers"]["subagent_limits"]["start"],
            install.GROK_LIMITS_START,
        )
        self.assertEqual(
            tuple(adapters["codex"]["cli_candidates"]), install.CODEX_CLI_CANDIDATES
        )
        with tempfile.TemporaryDirectory() as tmp:
            adapters = Path(tmp) / "adapters"
            render_hosts.render_all(install.HOSTS_DIR, adapters)
            rendered_profiles = install.load_role_profiles(adapters)
        expected_worker_bindings = {
            "codex": {"model": "gpt-5.6-luna", "model_reasoning_effort": "xhigh"},
            "claude": {"model": "claude-sonnet-5", "effort": "xhigh"},
            "grok": {"model": "grok-4.6", "effort": "high"},
        }
        for host, binding in expected_worker_bindings.items():
            with self.subTest(host=host):
                actual = rendered_profiles["orch-worker"][host]
                for field, value in binding.items():
                    self.assertEqual(value, actual[field])

    def test_host_profile_and_authoring_prose_point_to_the_data_owner(self):
        profiles = install.PROFILES_MD.read_text(encoding="utf-8")
        authoring = (install.REPO_ROOT / "docs" / "custom-workflow-authoring.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("host records beside this file", profiles)
        self.assertNotIn("| Profile |", profiles)
        for binding in ("gpt-5.6-sol", "claude-opus-5", "grok-4.6"):
            self.assertNotIn(binding, profiles)
        self.assertIn("../hosts/", authoring)
        self.assertNotIn("A Claude adapter keeps", authoring)

    def test_incomplete_rendered_role_binding_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapters = Path(tmp) / "adapters"
            shutil.copytree(install.HOST_ADAPTERS_DIR, adapters)
            codex_path = adapters / "codex.json"
            rendered = json.loads(codex_path.read_text(encoding="utf-8"))
            del rendered["host"]["role_profiles"]["planner"]["binding"]["model"]
            codex_path.write_text(json.dumps(rendered), encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError, "incomplete Codex binding for orch-planner"
            ):
                install.load_role_profiles(adapters)


class RoleProfileRefusalTest(unittest.TestCase):
    """Rendered host adapters bind each child role and refuse half-bindings.

    Every refusal below would otherwise ship silently and surface only at
    dispatch: a host agent for a role nothing dispatches, a role agent bound
    to no model, or two Codex agents claiming one spawn identifier. Each case
    mutates one rendered adapter in exactly one way, so nothing else can be what
    the refusal is reacting to.
    """

    def adapters(self, host: str, mutate) -> Path:
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        root = Path(tmp) / "adapters"
        shutil.copytree(install.HOST_ADAPTERS_DIR, root)
        path = root / f"{host}.json"
        rendered = json.loads(path.read_text(encoding="utf-8"))
        mutate(rendered["host"])
        path.write_text(json.dumps(rendered), encoding="utf-8")
        return root

    def test_a_missing_role_row_is_refused_and_the_role_is_named(self):
        for role in install.PROFILE_ROLES:
            with self.subTest(role=role):
                path = self.adapters(
                    "codex", lambda host, role=role: host["role_profiles"].pop(role)
                )
                with self.assertRaisesRegex(
                    ValueError, rf"missing role profile for orch-{role}"
                ):
                    install.load_role_profiles(path)

    def test_a_canonical_profile_name_must_match_its_declared_role(self):
        path = self.adapters(
            "codex",
            lambda host: host["role_profiles"]["planner"].__setitem__(
                "name", "orch-worker"
            ),
        )
        with self.assertRaisesRegex(
            ValueError, "role profile orch-planner must declare name orch-planner"
        ):
            install.load_role_profiles(path)

    def test_an_incomplete_codex_binding_is_refused_and_the_row_is_named(self):
        path = self.adapters(
            "codex",
            lambda host: host["role_profiles"]["planner"]["binding"].pop(
                "model_reasoning_effort"
            ),
        )
        with self.assertRaisesRegex(ValueError, "incomplete Codex binding for orch-planner"):
            install.load_role_profiles(path)

    def test_a_missing_codex_fork_binding_is_refused_and_the_row_is_named(self):
        path = self.adapters(
            "codex",
            lambda host: host["role_profiles"]["planner"]["binding"].pop(
                "fork_turns"
            ),
        )
        with self.assertRaisesRegex(ValueError, "incomplete Codex binding for orch-planner"):
            install.load_role_profiles(path)

    def test_none_and_a_positive_decimal_are_valid_codex_fork_bindings(self):
        self.assertEqual(
            "none", install.load_role_profiles()["orch-planner"]["codex"]["fork_turns"]
        )
        path = self.adapters(
            "codex",
            lambda host: host["role_profiles"]["planner"]["binding"].__setitem__(
                "fork_turns", "3"
            ),
        )
        self.assertEqual("3", install.load_role_profiles(path)["orch-planner"]["codex"]["fork_turns"])

    def test_other_codex_fork_bindings_are_refused_and_the_row_is_named(self):
        for value in ("all", "0", "01", "latest"):
            with self.subTest(value=value):
                path = self.adapters(
                    "codex",
                    lambda host, value=value: host["role_profiles"]["planner"][
                        "binding"
                    ].__setitem__("fork_turns", value),
                )
                with self.assertRaisesRegex(
                    ValueError, f"invalid Codex fork_turns for orch-planner: {value}"
                ):
                    install.load_role_profiles(path)

    def test_two_roles_may_not_claim_one_codex_agent_type(self):
        """The Codex agent_type is the spawn identifier and the installed
        file's name: two rows sharing one write two agents to one path, the
        second winning without a word."""

        path = self.adapters(
            "codex",
            lambda host: host["role_profiles"]["worker"]["binding"].__setitem__(
                "agent_type", "orch_planner"
            ),
        )
        with self.assertRaisesRegex(ValueError, "duplicate Codex agent_type: orch_planner"):
            install.load_role_profiles(path)

    def test_an_incomplete_claude_binding_is_refused_and_the_row_is_named(self):
        path = self.adapters(
            "claude",
            lambda host: host["role_profiles"]["planner"]["binding"].pop("model"),
        )
        with self.assertRaisesRegex(ValueError, "incomplete Claude binding for orch-planner"):
            install.load_role_profiles(path)


class TestScopedHostConfiguration(unittest.TestCase):
    def test_existing_marker_collision_is_refused_while_building_the_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            agents = home / ".codex" / "AGENTS.md"
            agents.parent.mkdir(parents=True)
            marker = install.load_host_adapters()["codex"]["managed_markers"][
                "host_instructions"
            ]["start"]
            agents.write_text(f"{marker}\nforeign\n{marker}\n", encoding="utf-8")

            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "codex"
            ):
                with self.assertRaisesRegex(
                    ValueError, "duplicate managed block markers"
                ):
                    install.build_plan("user", None)

            self.assertFalse(home.joinpath(".orchflows").exists())

    def test_invalid_codex_agent_type_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapters = Path(tmp) / "adapters"
            shutil.copytree(install.HOST_ADAPTERS_DIR, adapters)
            path = adapters / "codex.json"
            rendered = json.loads(path.read_text(encoding="utf-8"))
            rendered["host"]["role_profiles"]["planner"]["binding"][
                "agent_type"
            ] = "orch-planner"
            path.write_text(json.dumps(rendered), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "invalid Codex agent_type"):
                install.load_role_profiles(adapters)

    @requires_tomllib
    def test_codex_role_agent_names_follow_spawn_identifier_grammar(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis("codex"):
                plan = install.build_plan("user", None)

            parsed_agents = [
                (dest, install.tomllib.loads(content)) for dest, content in plan.codex_agents
            ]
            self.assertEqual(
                {"orch_planner", "orch_worker"},
                {parsed["name"] for _, parsed in parsed_agents},
            )
            for dest, parsed in parsed_agents:
                self.assertEqual(dest.stem, parsed["name"])
                self.assertIsNotNone(re.fullmatch(r"[a-z0-9_]+", parsed["name"]))

    @requires_tomllib
    def test_user_plan_merges_limits_and_writes_native_role_agents(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            claude_settings = home / ".claude" / "settings.json"
            claude_settings.parent.mkdir(parents=True)
            claude_settings.write_text(
                json.dumps({"theme": "dark", "env": {"EXISTING": "1"}}), encoding="utf-8"
            )
            codex_config = home / ".codex" / "config.toml"
            codex_config.parent.mkdir(parents=True)
            codex_config.write_text(
                "[agents]\nmax_threads = 2\ncustom = true\n\n[other]\nvalue = 1\n",
                encoding="utf-8",
            )

            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "claude", "codex"
            ):
                plan = install.build_plan("user", None)

            configs = {config.kind: config for config in plan.configs}
            claude = json.loads(configs["claude-config"].content)
            self.assertEqual("dark", claude["theme"])
            self.assertEqual("1", claude["env"]["EXISTING"])
            self.assertEqual("20", claude["env"]["CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"])
            codex = install.tomllib.loads(configs["codex-config"].content)
            self.assertEqual(20, codex["agents"]["max_threads"])
            self.assertEqual(1, codex["agents"]["max_depth"])
            self.assertTrue(codex["agents"]["custom"])
            self.assertEqual(1, codex["other"]["value"])

            self.assertEqual(2, len(plan.claude_agents))
            self.assertEqual(2, len(plan.codex_agents))
            for dest, content in plan.claude_agents:
                self.assertEqual(home / ".claude" / "agents", dest.parent)
                self.assertIn("name: orch-", content)
                if "name: orch-worker" in content:
                    self.assertIn("model: claude-sonnet-5", content)
                    self.assertIn("effort: xhigh", content)
            for dest, content in plan.codex_agents:
                self.assertEqual(home / ".codex" / "agents", dest.parent)
                parsed = install.tomllib.loads(content)
                self.assertIn(parsed["name"], {"orch_planner", "orch_worker"})
                self.assertIn("developer_instructions", parsed)
                if parsed["name"] == "orch_worker":
                    self.assertEqual("gpt-5.6-luna", parsed["model"])
                    self.assertEqual("xhigh", parsed["model_reasoning_effort"])

    def test_user_plan_writes_claude_adapters_and_codex_skill_stubs(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "claude", "codex"
            ):
                plan = install.build_plan("user", None)

            # Workflows are invocable by name and get an adapter stub like
            # skills. What differs is the body: a skill's is an `@`-include
            # of one file, and a workflow's is a pointer, because the body's
            # own relative links resolve against the library directory it
            # lives in rather than the host surface the stub is written to.
            templates = install.discover_workflow_skills()
            template_names = {directory.name for directory, _, _ in templates}
            self.assertEqual(
                len(install.discover_packages()) + len(templates),
                len(plan.claude_adapters),
            )
            role_bearing = set()
            for skill_md in install.discover_packages():
                skill_frontmatter, _ = install.split_frontmatter(
                    skill_md.read_text(encoding="utf-8")
                )
                if install.frontmatter_field(skill_frontmatter, "role") in (
                    "planner",
                    "worker",
                ):
                    role_bearing.add(skill_md.parent.name)
            expected_lib_path = (home / ".orchflows" / "lib").resolve()
            for dest, content in plan.claude_adapters:
                self.assertEqual(home / ".claude" / "skills", dest.parent.parent)
                self.assertEqual("SKILL.md", dest.name)
                frontmatter, body = install.split_frontmatter(content)
                self.assertIn("name:", frontmatter)
                self.assertIn("description:", frontmatter)
                self.assertNotIn("role:", frontmatter)
                self.assertNotIn("entry:", frontmatter)
                self.assertNotIn("placeholders:", frontmatter)
                if dest.parent.name in template_names:
                    self.assertNotIn("@", body)
                    self.assertIn("is a workflow skill", body)
                    self.assertIn("invoke the skill", body)
                    self.assertIn("disable-model-invocation: true", frontmatter)
                elif dest.parent.name in role_bearing:
                    # A role-bearing adapter forks, so its body opens with the
                    # fork-arrival clause and then the `@`-include; the clause
                    # is installer-rendered law, never a duplicated body.
                    self.assertTrue(
                        body.strip().startswith(install.FORK_ARRIVAL_CLAUSE)
                    )
                    self.assertIn("@", body)
                else:
                    self.assertTrue(body.strip().startswith("@"))
                self.assertIn(str(expected_lib_path), body)

            expected_stub_names = {
                install.frontmatter_field(install.split_frontmatter(path.read_text(encoding="utf-8"))[0], "name")
                for path in install.discover_packages()
            } | template_names
            self.assertEqual(
                expected_stub_names,
                {dest.parent.name for dest, _ in plan.codex_skills},
            )
            for dest, content in plan.codex_skills:
                self.assertEqual(home / ".codex" / "skills", dest.parent.parent)
                self.assertEqual("SKILL.md", dest.name)
                frontmatter, body = install.split_frontmatter(content)
                self.assertIn(f"name: {dest.parent.name}", frontmatter)
                self.assertIn("description:", frontmatter)
                self.assertIn(str(expected_lib_path), body)
                if dest.parent.name not in template_names:
                    self.assertIn("follow it exactly.", body)

    def test_discover_workflow_skills_requires_a_named_workflow_body(self):
        """A name surface is a workflow directory holding one `SKILL.md` that
        declares a `name`. Everything else under `example-workflows/` is
        library data: the shared `references/` tree, a directory mid-authoring,
        and — the case this replaces — any stray top-level `*.md`, which was
        the second grammar's whole surface until P4-3 deleted it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            comps = root / "example-workflows"
            (comps / "fix").mkdir(parents=True)
            (comps / "fix" / "SKILL.md").write_text(
                "---\nname: fix\ndescription: routed fix chain\n"
                "disable-model-invocation: true\n---\n\nOne frame, four calls.\n",
                encoding="utf-8",
            )
            (comps / "references").mkdir()
            (comps / "references" / "shared.md").write_text("prose\n", encoding="utf-8")
            (comps / "no-name").mkdir()
            (comps / "no-name" / "SKILL.md").write_text(
                "---\ndescription: missing name\n---\n\nbody\n",
                encoding="utf-8",
            )
            (comps / "unfrontmattered").mkdir()
            (comps / "unfrontmattered" / "SKILL.md").write_text(
                "# no frontmatter\n\nprose only\n", encoding="utf-8"
            )
            (comps / "legacy.md").write_text(
                "---\nname: legacy\ndescription: the deleted step form\n---\n\n"
                "Steps: one.\n",
                encoding="utf-8",
            )

            found = install.discover_workflow_skills(root)
            self.assertEqual(["fix"], [directory.name for directory, _, _ in found])
            directory, frontmatter, body = found[0]
            self.assertEqual("fix", install.frontmatter_field(frontmatter, "name"))
            self.assertIn("One frame, four calls.", body)

    def test_workflow_surfaces_are_manual_only_on_every_host(self):
        # Every workflow surfaces as a Claude adapter, a Codex prompt, and a
        # by-name entry -- unreachable from a host without them (SPEC §8) --
        # and the Claude adapter is manual-invocation-only whatever the body
        # declared, because a workflow's prose runs as orchestrator reasoning.
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "claude", "codex"
            ):
                plan = install.build_plan("user", None)

            templates = install.discover_workflow_skills()
            if not templates:
                self.skipTest("no invocable workflows in this tree")
            adapter_names = {dest.parent.name for dest, _ in plan.claude_adapters}
            prompt_names = {dest.stem for dest, _ in plan.codex_prompts}
            by_name_names = {dest.parent.name for dest, _ in plan.by_name}
            lib_comps = (home / ".orchflows" / "lib" / "example-workflows").resolve()
            for directory, _frontmatter, _ in templates:
                name = directory.name
                self.assertIn(name, adapter_names)
                self.assertIn(name, prompt_names)
                self.assertIn(name, by_name_names)
                # Both surfaces name the one body: the adapter to invoke it,
                # the pointer to read it.
                adapter = next(c for d, c in plan.claude_adapters if d.parent.name == name)
                self.assertIn(str(lib_comps / name / "SKILL.md"), adapter)
                self.assertIn("disable-model-invocation: true", adapter)
                self.assertNotIn("--set ", adapter)
                pointer = next(c for d, c in plan.by_name if d.parent.name == name)
                self.assertIn(str(lib_comps / name / "SKILL.md"), pointer)
                self.assertIn("invoked by name only", pointer)

    def test_user_plan_writes_flat_by_name_index_for_every_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "claude", "codex"
            ):
                plan = install.build_plan("user", None)

            by_name_root = (home / ".orchflows" / "lib" / "by-name").resolve()
            expected_lib_path = (home / ".orchflows" / "lib").resolve()
            packages = install.discover_packages()
            templates = install.discover_workflow_skills()
            # One flat entry per canonical name — skills across every tier,
            # packs, and invocable templates alike — no tier in the path.
            self.assertEqual(len(packages) + len(templates), len(plan.by_name))
            self.assertEqual(
                {p.parent.name for p in packages} | {d.name for d, _, _ in templates},
                {dest.parent.name for dest, _ in plan.by_name},
            )
            for dest, content in plan.by_name:
                self.assertEqual(by_name_root, dest.parent.parent.resolve())
                self.assertEqual("SKILL.md", dest.name)
                frontmatter, body = install.split_frontmatter(content)
                self.assertIn(f"name: {dest.parent.name}", frontmatter)
                # Pointer only — names the canonical source, never duplicates it.
                self.assertIn(str(expected_lib_path), body)
                self.assertIn("follow it exactly.", body)

    def test_by_name_index_is_host_agnostic(self):
        # The flat index lives in the shared library, so it is built whether or
        # not either host surface is present — a Codex-only install still gets it.
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis("codex"):
                plan = install.build_plan("user", None)
            self.assertEqual([], plan.claude_adapters)
            self.assertEqual(
                len(install.discover_packages()) + len(install.discover_workflow_skills()),
                len(plan.by_name),
            )

    def test_user_plan_targets_user_config_and_agent_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            (home / ".codex").mkdir(parents=True)
            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "claude", "codex"
            ):
                plan = install.build_plan("user", None)

            self.assertEqual(
                {home / ".claude" / "settings.json", home / ".codex" / "config.toml"},
                {config.dest for config in plan.configs},
            )
            self.assertEqual({home / ".claude" / "agents"}, {dest.parent for dest, _ in plan.claude_agents})
            self.assertEqual({home / ".codex" / "agents"}, {dest.parent for dest, _ in plan.codex_agents})

    @requires_tomllib
    def test_codex_limit_merge_handles_dotted_agent_keys(self):
        rendered, details = install.render_codex_agent_limits(
            "agents.max_threads = 3\nagents.max_depth = 2\n\n[other]\nvalue = true\n"
        )
        parsed = install.tomllib.loads(rendered)

        self.assertEqual(20, parsed["agents"]["max_threads"])
        self.assertEqual(1, parsed["agents"]["max_depth"])
        self.assertEqual(3, details["previous"]["agents.max_threads"])
        self.assertEqual(2, details["previous"]["agents.max_depth"])

    # --- Grok ------------------------------------------------------------
    #
    # Grok cases live on this class, not on a mixin or a new class of their
    # own. `tests/test_installer_cases/**` is not discovered: a class here
    # reaches the suite only by explicit class-name import in a shard module
    # (`tests/test_installer_hosts.py`), and `tests.test_run_tests` holds the
    # loaded class name against the one this file declares.

    def _role_bearing(self, packages) -> set:
        def role(path):
            head = install.split_frontmatter(path.read_text(encoding="utf-8"))[0]
            return install.frontmatter_field(head, "role")

        return {path.parent.name for path in packages if role(path) in ("planner", "worker")}

    def test_the_planned_grok_surface_hangs_off_grok_home(self):
        """One skill per canonical name and invocable template, both role
        agents, the whole managed rules file and the ``[subagents]`` config.

        The fake home and the fake ``GROK_HOME`` are separate roots on
        purpose: a surface that landed under ``Path.home()/.grok`` instead
        would still look right against one shared root, and ``GROK_HOME`` is
        the only relocation the grok CLI itself reads.
        """

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            home.mkdir()
            with isolated_grok_home(Path(tmp)) as grok_home, patch.object(
                install.Path, "home", return_value=home
            ), mock_host_clis("grok"):
                plan = install.build_plan("user", None)

            packages = install.discover_packages()
            bodies = {dest.parent.name: content for dest, content in plan.grok_skills}
            self.assertEqual(
                {path.parent.name for path in packages}
                | {directory.name for directory, _, _ in install.discover_workflow_skills()},
                set(bodies),
            )
            # Two spellings of one directory, because the installer writes
            # two: a skill body carries the resolved `lib_skill_md`, while the
            # host block substitutes `_lib_home`'s unresolved path. The forms
            # coincide on a box whose temp root is already canonical and
            # diverge on the CI runners -- macOS `/var` -> `/private/var`,
            # Windows `RUNNER~1` -> `runneradmin` -- so one variable for both
            # passes locally and fails there.
            lib_home = (home / ".orchflows" / "lib").resolve()
            unresolved_lib_home = home / ".orchflows" / "lib"
            for dest, content in plan.grok_skills:
                self.assertEqual(grok_home / "skills", dest.parent.parent)
                self.assertEqual("SKILL.md", dest.name)
                frontmatter, body = install.split_frontmatter(content)
                self.assertIn(f"name: {dest.parent.name}", frontmatter)
                # Grok reads neither key, so a stub carrying them would render
                # a role binding that looks present and does nothing.
                self.assertNotIn("role:", frontmatter)
                self.assertNotIn("context:", frontmatter)
                # Grok expands no ``@`` include, so a body names its source.
                self.assertFalse(body.strip().startswith("@"))
                self.assertIn(str(lib_home), body)
            gated = {name for name, body in bodies.items() if "spawn_subagent" in body}
            self.assertEqual(self._role_bearing(packages), gated)
            self.assertTrue(all(install.FORK_ARRIVAL_CLAUSE in bodies[n] for n in gated))

            self.assertEqual(
                {grok_home / "agents" / f"{n}.md" for n in ("orch-planner", "orch-worker")},
                {dest for dest, _ in plan.grok_agents},
            )
            for dest, content in plan.grok_agents:
                self.assertIn(f"name: {dest.stem}", content)
                self.assertIn("effort:", content)

            start, end = install.template_markers(
                install.HOST_BLOCK_TEMPLATE.read_text(encoding="utf-8")
            )
            self.assertEqual(grok_home / "rules" / "orchflows.md", plan.grok_rules.dest)
            rendered = plan.grok_rules.content
            self.assertTrue(rendered.startswith(start), rendered[:120])
            self.assertEqual(end, rendered.strip().splitlines()[-1])
            self.assertNotIn("{{", rendered)
            self.assertIn(str(unresolved_lib_home), rendered)

            config = {entry.kind: entry for entry in plan.configs}["grok-config"]
            self.assertEqual(grok_home / "config.toml", config.dest)
            self.assertTrue(config.content.startswith(install.GROK_LIMITS_START))
            self.assertIn(install.GROK_LIMITS_END, config.content)
            if install.tomllib is not None:
                subagents = install.tomllib.loads(config.content)["subagents"]
                self.assertEqual(install.GROK_MAX_CONCURRENT, subagents["max_concurrent"])
                self.assertEqual(install.GROK_MAX_DEPTH, subagents["max_depth"])
