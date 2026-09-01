"""Routing benchmark execution regression cases."""

from ._support import *

class TestRoutingBenchRun(unittest.TestCase):
    """The whole benchmark with the CLI seam mocked: two isolated installs,
    one plain repository each, one graded launch per case per repeat."""

    CASES = [
        {"id": "a1", "prompt": "what does write_scope mean?", "expected": "answer", "note": ""},
        {"id": "t1", "prompt": "add a --json flag", "expected": "ticket", "note": ""},
        {"id": "n1", "prompt": "run evolve on orch-tdd", "expected": "named:evolve", "note": ""},
    ]
    # Keyed by prompt so the fake CLI answers each case differently: one
    # right, one misrouted, one unrouted.
    TRANSCRIPTS = {
        "what does write_scope mean?": [_parent_text("the paths a ticket may write")],
        "add a --json flag": [_skill_use("evolve")],
        "run evolve on orch-tdd": [_tool_use("Read", {"file_path": "/repo/README.md"})],
    }

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.calls = []

    def tearDown(self):
        self._tmp.cleanup()

    def _fake_run(self, command, **kwargs):
        self.calls.append((list(command), kwargs))
        stdout = ""
        if "-p" in command:
            prompt = command[command.index("-p") + 1]
            stdout = _stream(self.TRANSCRIPTS[prompt] + [_result_event(0.01)])
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    def _run(self, adapter_sets=("all", "four"), repeat=1):
        with mock.patch.object(routing_live.subprocess, "run", side_effect=self._fake_run):
            return routing_live.run_benchmark(
                adapter_sets=adapter_sets,
                cases=self.CASES,
                repeat=repeat,
                max_turns=3,
                timeout=5,
                claude_invocation=["claude"],
                root=self.root,
            )

    def _claude_calls(self):
        return [command for command, _ in self.calls if "-p" in command]

    def _install_calls(self):
        return [
            (command, kwargs)
            for command, kwargs in self.calls
            if any(str(part).endswith("install.py") for part in command)
        ]

    def test_case_requires_role_and_exact_skill(self):
        cases = [
            {
                "id": "matching-child",
                "prompt": "matching child",
                "expected": "named:orch-repair",
                "note": "",
                "required_role": "worker",
                "required_skill": "orch-repair",
            },
            {
                "id": "parent-only",
                "prompt": "parent only",
                "expected": "named:orch-repair",
                "note": "",
                "required_role": "worker",
                "required_skill": "orch-repair",
            },
        ]
        transcripts = {
            "matching child": [
                _launch("worker-1", "orch-worker", "Apply orch-repair exactly"),
                {
                    "type": "assistant",
                    "parent_tool_use_id": "worker-1",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "primary-1",
                                "name": "Skill",
                                "input": {"skill": "orch-repair"},
                            }
                        ]
                    },
                },
            ],
            "parent only": [_skill_use("orch-repair")],
        }

        def _fake_run(command, **kwargs):
            self.calls.append((list(command), kwargs))
            stdout = ""
            if "-p" in command:
                prompt = command[command.index("-p") + 1]
                stdout = _stream(transcripts[prompt])
            return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

        with mock.patch.object(routing_live.subprocess, "run", side_effect=_fake_run):
            records = routing_live.run_benchmark(
                adapter_sets=("all",),
                cases=cases,
                repeat=1,
                max_turns=3,
                timeout=5,
                claude_invocation=["claude"],
                root=self.root,
            )

        by_case = {record["case"]: record for record in records}
        self.assertTrue(by_case["matching-child"]["match"])
        self.assertEqual(
            "passed", by_case["matching-child"]["execution_conformance"]["status"]
        )
        self.assertFalse(by_case["parent-only"]["match"])
        self.assertEqual(
            "failed", by_case["parent-only"]["execution_conformance"]["status"]
        )

    def test_one_graded_launch_per_case_per_adapter_set_per_repeat(self):
        records = self._run(repeat=2)
        self.assertEqual(len(self.CASES) * 2 * 2, len(records))
        self.assertEqual(len(records), len(self._claude_calls()))
        self.assertEqual(
            {("all", 1), ("all", 2), ("four", 1), ("four", 2)},
            {(record["adapter_set"], record["repeat"]) for record in records},
        )

    def test_each_record_carries_the_grade_and_what_decided_it(self):
        records = {record["case"]: record for record in self._run(adapter_sets=("all",))}
        self.assertEqual("answer", records["a1"]["observed"])
        self.assertTrue(records["a1"]["match"])
        self.assertEqual("named:evolve", records["t1"]["observed"])
        self.assertFalse(records["t1"]["match"])
        self.assertEqual("ticket", records["t1"]["expected"])
        self.assertEqual("unrouted", records["n1"]["observed"])
        self.assertFalse(records["n1"]["match"])
        for record in records.values():
            self.assertEqual(0.01, record["cost_usd"])
            self.assertGreaterEqual(record["turns"], 1)

    def test_the_launch_command_carries_the_prompt_stream_and_turn_bound(self):
        self._run(adapter_sets=("all",))
        command = self._claude_calls()[0]
        self.assertEqual("claude", command[0])
        self.assertEqual("stream-json", command[command.index("--output-format") + 1])
        self.assertEqual("3", command[command.index("--max-turns") + 1])
        self.assertIn(command[command.index("-p") + 1], self.TRANSCRIPTS)

    def test_each_adapter_set_is_installed_into_its_own_temp_home(self):
        self._run()
        installs = self._install_calls()
        self.assertEqual(2, len(installs))
        homes = set()
        for command, kwargs in installs:
            self.assertIn("--user", command)
            adapter_set = command[command.index("--claude-adapters") + 1]
            env = kwargs["env"]
            home = Path(env["USERPROFILE"])
            self.assertEqual(Path(env["HOME"]), home)
            self.assertEqual(self.root, home.parent)
            self.assertIn(adapter_set, home.name)
            self.assertEqual(home / ".claude", Path(env["CLAUDE_CONFIG_DIR"]))
            homes.add(home)
        self.assertEqual(2, len(homes))

    def test_the_install_env_overrides_every_root_an_install_could_write(self):
        # A temporary directory can itself live under the real home on this
        # host, so the property is not "the string never appears" -- it is
        # that every root an install writes to is redirected away from the
        # one the developer actually uses, including any value inherited
        # from the ambient environment.
        real = Path.home()
        decoy = str(self.root / "inherited")
        ambient = {
            "HOME": decoy,
            "USERPROFILE": decoy,
            "CLAUDE_CONFIG_DIR": decoy,
            "CODEX_HOME": decoy,
            state_root.ENV_VAR: decoy,
        }
        with mock.patch.dict(os.environ, ambient):
            self._run()

        overridden = ("HOME", "USERPROFILE", "CLAUDE_CONFIG_DIR", "CODEX_HOME",
                      state_root.ENV_VAR)
        for _, kwargs in self._install_calls():
            env = kwargs["env"]
            home = Path(env["USERPROFILE"])
            self.assertNotEqual(real, home)
            self.assertEqual(self.root, home.parent)
            for key in overridden:
                with self.subTest(key=key):
                    self.assertNotEqual(decoy, env[key], "an inherited root was carried through")
                    self.assertTrue(str(Path(env[key])).startswith(str(home)), env[key])

    def test_the_session_runs_in_a_plain_repository_with_no_agents_file(self):
        self._run(adapter_sets=("four",))
        cwds = {Path(kwargs["cwd"]) for command, kwargs in self.calls if "-p" in command}
        self.assertEqual(1, len(cwds))
        repo = cwds.pop()
        self.assertEqual(self.root, repo.parent)
        self.assertFalse((repo / "AGENTS.md").exists())
        self.assertFalse((repo / "CLAUDE.md").exists())
        # Every session runs under the same isolated home as its install.
        for command, kwargs in self.calls:
            if "-p" in command:
                self.assertEqual(self.root / "home-four", Path(kwargs["env"]["USERPROFILE"]))

    def test_the_real_home_is_untouched(self):
        before = sorted(p.name for p in Path.home().glob(".claude/skills/*"))
        self._run()
        self.assertEqual(before, sorted(p.name for p in Path.home().glob(".claude/skills/*")))

    def test_no_call_reaches_a_real_claude_or_codex_binary(self):
        self._run()
        self.assertTrue(self.calls)
        for command, _ in self.calls:
            self.assertNotIn(Path(str(command[0])).stem, {"codex"})

    def test_a_failing_install_is_reported_rather_than_measured(self):
        def _failing(command, **kwargs):
            self.calls.append((list(command), kwargs))
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="boom")

        with mock.patch.object(routing_live.subprocess, "run", side_effect=_failing):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                routing_live.run_benchmark(
                    adapter_sets=("four",),
                    cases=self.CASES,
                    repeat=1,
                    max_turns=3,
                    timeout=5,
                    claude_invocation=["claude"],
                    root=self.root,
                )
        self.assertEqual([], self._claude_calls())

    def test_a_timed_out_case_is_recorded_as_an_error_not_a_misroute(self):
        """A session killed at the timeout never got to route. Grading it
        `unrouted` put it in the misroute numerator and left `errors` at 0,
        so README's "read no rate while errors is above 0" guard waved
        through a run where every session had been cut off."""

        expired = subprocess.TimeoutExpired(["claude"], 5, output="not-json", stderr="slow")

        def _timeout(command, **kwargs):
            self.calls.append((list(command), kwargs))
            if "-p" in command:
                raise expired
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with mock.patch.object(routing_live.subprocess, "run", side_effect=_timeout):
            records = routing_live.run_benchmark(
                adapter_sets=("four",),
                cases=self.CASES,
                repeat=1,
                max_turns=3,
                timeout=5,
                claude_invocation=["claude"],
                root=self.root,
            )
        self.assertEqual(len(self.CASES), len(records))
        for record in records:
            self.assertEqual("error", record["observed"])
            self.assertTrue(record["timed_out"])

    def test_the_budget_stops_launching_once_the_spend_passes_it(self):
        """An opt-in benchmark that spends real usage needs a ceiling that
        is not the case count: one long session is worth many short ones."""

        records = self._run_with_budget(0.025)
        # each mocked session reports 0.01; the fourth launch is the one
        # that would cross 0.025, so three are launched and no more
        self.assertEqual(3, len(records))
        self.assertEqual(3, len(self._claude_calls()))

    def test_no_budget_launches_every_case(self):
        self.assertEqual(len(self.CASES) * 2, len(self._run_with_budget(None)))

    def _run_with_budget(self, budget):
        with mock.patch.object(routing_live.subprocess, "run", side_effect=self._fake_run):
            return routing_live.run_benchmark(
                adapter_sets=("all", "four"),
                cases=self.CASES,
                repeat=1,
                max_turns=3,
                timeout=5,
                claude_invocation=["claude"],
                root=self.root,
                max_budget_usd=budget,
            )
