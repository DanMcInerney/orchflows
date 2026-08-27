"""Claude and Codex profile probe regression cases."""

from ._support import *
from installer import packages as installer_packages


class GrokRoleProfileCases:
    """`load_role_profiles` refuses half a host binding rather than ship
    one. These cases hold the Grok column to the standard the Codex and
    Claude columns already meet, hold those two to what they parsed to
    before it existed, and keep `isolation` the ticket's field. Each
    refusal mutates the shipped table in exactly one way, so nothing
    else can be what it reacts to.

    A mixin, not a `TestCase`: a case here reaches the suite only by
    being named in the import block at `tests/test_live_harnesses.py:16`,
    so a new top-level class would be collected by nothing and report
    green without ever running, which costs Grok its own class name.
    """

    packages = installer_packages
    PLANNER = "model `grok-4.6`, effort `xhigh`, subagent_type `orch-planner`"
    REFUSED = (
        ("model `grok-4.6`", "incomplete Grok binding for orch-planner"),
        ("effort `xhigh`, subagent_type `orch-planner`", "incomplete Grok binding"),
        (PLANNER.replace("grok-4.6", "grok-4"),
         "Grok model outside the recorded census for orch-planner: grok-4"),
        (PLANNER.replace("grok-4.6", "claude-opus-5"), "Grok model outside the"
         " recorded census for orch-planner: claude-opus-5"),
        (PLANNER.replace("xhigh", "ultra"), "invalid Grok effort for orch-planner: ultra"),
        (PLANNER.replace("xhigh", "XHIGH"), "invalid Grok effort for orch-planner: XHIGH"),
    )

    def setUp(self):
        self._scratch = contextlib.ExitStack()
        self.addCleanup(self._scratch.close)

    def table(self, *replacements) -> Path:
        """The shipped table with substrings replaced, on disk."""
        text = self.packages.PROFILES_MD.read_text(encoding="utf-8")
        for old, new in replacements:
            self.assertIn(old, text, old)
            text = text.replace(old, new, 1)
        path = Path(self._scratch.enter_context(tempfile.TemporaryDirectory()))
        (path / "profiles.md").write_text(text, encoding="utf-8")
        return path / "profiles.md"

    def test_every_column_parses_and_grok_is_bound_for_both_roles(self):
        profiles = self.packages.load_role_profiles()
        self.assertEqual(
            {"orch-planner": {"model": "grok-4.6", "effort": "xhigh",
                              "subagent_type": "orch-planner"},
             "orch-worker": {"model": "grok-4.6", "effort": "high",
                             "subagent_type": "orch-worker"}},
            {n: p["grok"] for n, p in profiles.items()})
        self.assertEqual(
            {"orch-planner": ("gpt-5.6-sol", "ultra", "claude-opus-5", "max"),
             "orch-worker": ("gpt-5.6-sol", "high", "claude-opus-5", "high")},
            {n: (p["codex"]["model"], p["codex"]["model_reasoning_effort"],
                 p["claude"]["model"], p["claude"]["effort"])
             for n, p in profiles.items()})

    def test_every_way_a_grok_row_can_fail_is_refused_naming_the_host(self):
        for cell, message in self.REFUSED:
            with self.subTest(cell=cell):
                with self.assertRaisesRegex(ValueError, re.escape(message)):
                    self.packages.load_role_profiles(self.table((self.PLANNER, cell)))

    def test_every_recorded_model_and_effort_is_admitted(self):
        """The census is what `grok models` returned on this host. A
        refusal that rejected what the table records refuses everything."""

        for model in self.packages.GROK_MODEL_CENSUS:
            for effort in self.packages.GROK_EFFORTS:
                with self.subTest(model=model, effort=effort):
                    cell = self.PLANNER.replace("grok-4.6", model).replace("xhigh", effort)
                    grok = self.packages.load_role_profiles(
                        self.table((self.PLANNER, cell)))["orch-planner"]["grok"]
                    self.assertEqual((model, effort), (grok["model"], grok["effort"]))

    def test_a_row_that_lost_its_grok_cell_is_not_read_as_a_row(self):
        """A four-column row is not a row with an empty Grok cell: read
        as one it yields a host binding carrying no model at all."""

        row = next(line for line in self.packages.PROFILES_MD.read_text(
            encoding="utf-8").splitlines() if line.startswith("| `orch-planner` |"))
        with self.assertRaisesRegex(
                ValueError, r"missing role profile row\(s\) for orch-planner"):
            self.packages.load_role_profiles(self.table(
                (row, row[: row.rindex("|", 0, row.rindex("|"))] + " |")))

    def test_isolation_stays_the_tickets_field_on_every_host(self):
        """Grok's `spawn_subagent` takes a native isolation argument, so
        the paragraph records it; no row and no rendered definition binds
        it, which would isolate every child of a role whatever its
        ticket said."""

        paragraph = "\n\n".join(
            block for block in self.packages.PROFILES_MD.read_text(
                encoding="utf-8").split("\n\n")
            if "isolation" in block and not block.lstrip().startswith("|"))
        for recorded in ("spawn_subagent", "Grok", "established at dispatch"):
            self.assertIn(recorded, paragraph)
        for name, profile in self.packages.load_role_profiles().items():
            with self.subTest(name=name):
                for host in ("codex", "claude", "grok"):
                    self.assertNotIn("isolation", profile[host])
                self.assertNotIn("isolation", self.packages.render_codex_agent(name, profile))
                self.assertNotIn("isolation", self.packages.render_claude_agent(name, profile))


# --- tools/live_claude_profiles.py and tools/live_codex_profiles.py ----


class TestClaudeLiveProfiles(unittest.TestCase):
    def test_role_skill_topology_is_enforced(self):
        agent_type = "orch-worker"
        skill_name = "orch-profile-probe-worker-42"
        sentinel = "ORCH_SKILL_EXECUTED:orch-repair"
        matching = [
            {"type": "system", "subtype": "init", "agents": [agent_type]},
            _skill_use(skill_name, "skill-1"),
            _reply("skill-1", sentinel),
        ]

        result = claude_live._analyze_run(
            _stream(matching), returncode=0, expected={agent_type: sentinel},
            expected_skills={skill_name: agent_type},
        )
        self.assertTrue(result["passed"])
        self.assertEqual("enforced", result["role_skill_topology"]["mode"])
        self.assertEqual("verified", result["role_skill_topology"]["profile_selection"])

        parent_only = matching[:2] + [_parent_text(sentinel)]
        result = claude_live._analyze_run(
            _stream(parent_only), returncode=0, expected={agent_type: sentinel},
            expected_skills={skill_name: agent_type},
        )
        self.assertFalse(result["passed"])
        self.assertEqual("failed", result["role_skill_topology"]["profile_selection"])

    def test_builds_all_production_derived_probe_agents(self):
        agents, expected, configured = claude_live._build_probe_agents(
            claude_live.PROFILE_NAMES, pid=42
        )

        self.assertEqual(2, len(agents))
        self.assertEqual(set(agents), set(expected))
        self.assertEqual(set(agents), set(configured))
        for agent_type, definition in agents.items():
            self.assertIsNotNone(re.fullmatch(r"[a-z0-9-]+", agent_type))
            self.assertEqual([], definition["tools"])
            self.assertIn(expected[agent_type], definition["prompt"])
            self.assertEqual(configured[agent_type]["model"], definition["model"])
            self.assertEqual(configured[agent_type].get("effort"), definition.get("effort"))

    def test_builds_generated_role_bound_skill_adapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            mapping = claude_live._build_probe_adapters(
                claude_live.PROFILE_NAMES, Path(tmp), pid=42
            )

            self.assertEqual(
                {
                    "orch-profile-probe-planner-42": "orch-planner",
                    "orch-profile-probe-worker-42": "orch-worker",
                },
                mapping,
            )
            for skill_name, agent_type in mapping.items():
                content = (
                    Path(tmp) / "skills" / skill_name / "SKILL.md"
                ).read_text(encoding="utf-8")
                frontmatter, body = claude_live.install.split_frontmatter(content)
                self.assertEqual(
                    "fork", claude_live.install.frontmatter_field(frontmatter, "context")
                )
                self.assertEqual(
                    agent_type,
                    claude_live.install.frontmatter_field(frontmatter, "agent"),
                )
                self.assertNotIn("ORCH_PROFILE_LOADED:", body)

    def test_accepts_exact_registered_launches_and_forwarded_sentinels(self):
        expected = {
            "orch-planner": "SENTINEL:planner",
            "orch-worker": "SENTINEL:worker",
        }
        expected_skills = {
            "orch-profile-probe-planner-42": "orch-planner",
            "orch-profile-probe-worker-42": "orch-worker",
        }
        events = [
            {
                "type": "system",
                "subtype": "init",
                "agents": list(expected),
            }
        ]
        for index, (skill_name, agent_type) in enumerate(expected_skills.items()):
            tool_id = f"tool-{index}"
            sentinel = expected[agent_type]
            events.extend(
                [
                    _skill_use(skill_name, tool_id),
                    {
                        "type": "assistant",
                        "parent_tool_use_id": tool_id,
                        "message": {
                            "model": f"reported-{index}",
                            "content": [{"type": "text", "text": sentinel}],
                        },
                    },
                ]
            )

        result = claude_live._analyze_run(
            _stream(events),
            returncode=0,
            expected=expected,
            expected_skills=expected_skills,
        )

        self.assertTrue(result["passed"])
        self.assertEqual([], result["missing_registrations"])
        self.assertEqual([], result["invalid_launches"])
        self.assertEqual([], result["missing_sentinels"])
        self.assertEqual(0, result["unexpected_child_tools"])
        self.assertEqual(
            {agent_type: [f"reported-{index}"] for index, agent_type in enumerate(expected)},
            result["reported_models"],
        )

    def test_rejects_duplicate_launches(self):
        agent_type = "orch-worker"
        skill_name = "orch-profile-probe-worker-42"
        sentinel = "SENTINEL:worker"
        events = [
            {"type": "system", "subtype": "init", "agents": [agent_type]},
            {
                "type": "assistant",
                "parent_tool_use_id": None,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": "Skill",
                            "input": {"skill": skill_name},
                        }
                        for tool_id in ("tool-1", "tool-2")
                    ]
                },
            },
            _reply("tool-1", sentinel),
        ]

        result = claude_live._analyze_run(
            _stream(events),
            returncode=0,
            expected={agent_type: sentinel},
            expected_skills={skill_name: agent_type},
        )

        self.assertFalse(result["passed"])
        self.assertEqual([skill_name], result["invalid_launches"])

    def test_explicit_agent_launch_cannot_substitute_for_generated_adapter(self):
        agent_type = "orch-worker"
        skill_name = "orch-profile-probe-worker-42"
        sentinel = "SENTINEL:worker"
        events = [
            {"type": "system", "subtype": "init", "agents": [agent_type]},
            _launch("worker-1", agent_type),
            _reply("worker-1", sentinel),
        ]

        result = claude_live._analyze_run(
            _stream(events), 0, {agent_type: sentinel}, {skill_name: agent_type}
        )

        self.assertFalse(result["passed"])
        self.assertEqual(1, result["manual_root_launches"])

    def test_timeout_returns_structured_failure(self):
        expected = {"orch-worker": "SENTINEL:worker"}
        expected_skills = {"orch-profile-probe-worker-42": "orch-worker"}
        expired = subprocess.TimeoutExpired(
            ["claude"], 1, output="not-json", stderr="probe timed out"
        )

        with mock.patch.object(claude_live.subprocess, "run", side_effect=expired):
            result, stderr = claude_live._run_probe(
                ["claude"], 1, expected, expected_skills
            )

        self.assertFalse(result["passed"])
        self.assertTrue(result["timed_out"])
        self.assertEqual(124, result["returncode"])
        self.assertEqual("probe timed out", stderr)


class TestCodexLiveProfiles(GrokRoleProfileCases, unittest.TestCase):
    def test_role_skill_topology_reports_advisory_when_unsupported(self):
        stdout = json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "agent_message",
                    "text": codex_live.V2_UNSUPPORTED_MARKER,
                },
            }
        )

        result = codex_live._classify_surface(
            "v2", stdout, 0, {"orch_worker_e2e_42": "SENTINEL:worker"}
        )

        self.assertEqual("unsupported", result["status"])
        self.assertEqual("advisory", result["role_skill_topology"]["mode"])
        self.assertEqual("unsupported", result["role_skill_topology"]["profile_selection"])
        self.assertFalse(result["role_skill_topology"]["automatic_binding_claimed"])
        self.assertFalse(result["role_skill_topology"]["hard_root_guard_claimed"])

    def test_stable_surface_accepts_all_sentinels(self):
        expected = {
            "orch_planner_e2e_42": "SENTINEL:planner",
            "orch_worker_e2e_42": "SENTINEL:worker",
        }
        stdout = "\n".join(
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": sentinel},
                }
            )
            for sentinel in expected.values()
        )

        result = codex_live._classify_surface("stable", stdout, 0, expected)

        self.assertEqual("passed", result["status"])
        self.assertTrue(result["passed"])
        self.assertEqual([], result["missing_sentinels"])

    def test_v2_surface_reports_explicit_unavailable_marker(self):
        stdout = json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "agent_message",
                    "text": codex_live.V2_UNSUPPORTED_MARKER,
                },
            }
        )

        result = codex_live._classify_surface(
            "v2", stdout, 0, {"orch_planner_e2e_42": "SENTINEL:planner"}
        )

        self.assertEqual("unsupported", result["status"])
        self.assertFalse(result["passed"])
        self.assertFalse(result["supported"])

    def test_v2_surface_accepts_all_sentinels(self):
        expected = {"orch_planner_e2e_42": "SENTINEL:planner"}
        stdout = json.dumps(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "SENTINEL:planner"},
            }
        )

        result = codex_live._classify_surface("v2", stdout, 0, expected)

        self.assertEqual("passed", result["status"])
        self.assertTrue(result["passed"])
        self.assertTrue(result["supported"])

    def test_v2_surface_does_not_mask_missing_sentinel(self):
        stdout = json.dumps(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "could not launch"},
            }
        )

        result = codex_live._classify_surface(
            "v2", stdout, 0, {"orch_planner_e2e_42": "SENTINEL:planner"}
        )

        self.assertEqual("failed", result["status"])
        self.assertEqual(["SENTINEL:planner"], result["missing_sentinels"])

    def test_v2_unavailable_marker_with_command_use_fails(self):
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "agent_message",
                            "text": codex_live.V2_UNSUPPORTED_MARKER,
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "command_execution", "command": "echo nope"},
                    }
                ),
            ]
        )

        result = codex_live._classify_surface(
            "v2", stdout, 0, {"orch_planner_e2e_42": "SENTINEL:planner"}
        )

        self.assertEqual("failed", result["status"])
        self.assertEqual(1, result["unexpected_tool_actions"])

    def test_file_tool_activity_fails_the_surface(self):
        expected = {"orch_planner_e2e_42": "SENTINEL:planner"}
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "SENTINEL:planner"},
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "file_change", "path": "unexpected.txt"},
                    }
                ),
            ]
        )

        result = codex_live._classify_surface("stable", stdout, 0, expected)

        self.assertEqual("failed", result["status"])
        self.assertEqual(1, result["unexpected_tool_actions"])

    def _capture_surface_command(self, surface):
        captured = {}

        def _fake_run(command, **kwargs):
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        expected = {"orch_planner_e2e_42": "SENTINEL:planner"}
        with mock.patch.object(codex_live.subprocess, "run", side_effect=_fake_run):
            codex_live._run_surface(surface, ["codex"], expected, 5)
        return captured["command"]

    def test_stable_surface_command_uses_native_fork_field_and_default_config(self):
        # Exercise the public _run_surface seam so the config-args/prompt
        # wiring is proven on the actual argv, not just each helper in
        # isolation echoing its own literal.
        command = self._capture_surface_command("stable")
        self.assertNotIn("--ignore-user-config", command)
        self.assertIn("fork_context=false", command[-1])

    def test_v2_surface_command_ignores_stable_user_config_and_uses_native_fork_field(self):
        command = self._capture_surface_command("v2")
        self.assertIn("--ignore-user-config", command)
        self.assertIn('fork_turns="none"', command[-1])
        self.assertIn(codex_live.V2_UNSUPPORTED_MARKER, command[-1])

    def test_timeout_returns_structured_surface_failure(self):
        expected = {"orch_planner_e2e_42": "SENTINEL:planner"}
        expired = subprocess.TimeoutExpired(
            ["codex"], 1, output="not-json", stderr="probe timed out"
        )

        with mock.patch.object(codex_live.subprocess, "run", side_effect=expired):
            result, stderr = codex_live._run_surface("v2", ["codex"], expected, 1)

        self.assertEqual("failed", result["status"])
        self.assertTrue(result["timed_out"])
        self.assertEqual(124, result["returncode"])
        self.assertEqual("probe timed out", stderr)

    def test_exception_during_surface_run_still_cleans_up_temp_agent_file(self):
        # The rendered probe .toml is written before any CLI call; if the
        # subprocess call blows up, the finally block in main() must still
        # unlink it rather than leaking a live agent file into ~/.codex.
        with tempfile.TemporaryDirectory() as codex_home:
            agents_dir = Path(codex_home) / "agents"
            with mock.patch.dict(os.environ, {"CODEX_HOME": codex_home}), \
                    mock.patch.object(codex_live, "_codex_command", return_value=["codex"]), \
                    mock.patch.object(
                        codex_live.subprocess, "run", side_effect=RuntimeError("boom")
                    ):
                with self.assertRaises(RuntimeError):
                    codex_live.main(["--profile", "orch-worker"])

            self.assertEqual([], list(agents_dir.glob("*.toml")))

    def test_probe_sentinel_injection_does_not_require_tomllib(self):
        profile = codex_live.install.load_role_profiles()["orch-planner"]
        rendered = codex_live.install.render_codex_agent("orch-planner", profile)

        with mock.patch.object(codex_live.install, "tomllib", None):
            injected = codex_live._with_probe_sentinel(rendered, "SENTINEL:planner")

        self.assertIn("SENTINEL:planner", injected)
