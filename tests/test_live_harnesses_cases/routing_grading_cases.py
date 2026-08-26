"""Routing case-set, grading, and loader regression cases."""

from . import _support
from ._support import *

# --- benchmarks/routing/cases.json ------------------------------------


ROUTING_DIR = Path(__file__).resolve().parents[2] / "benchmarks" / "routing"
ROUTING_CASES = ROUTING_DIR / "cases.json"
ROUTE_CLASSES = ("answer", "errand", "ticket", "doctor", "fix", "build", "named")
CASE_KEYS = {"id", "prompt", "expected", "note", "distractor"}
ROLE_SKILL_KEYS = {"required_role", "required_skill"}
# A deleted or never-routed name whose surface words a prompt can borrow
# without the prompt's correct route changing.
LURE_WORDS = ("diagnose", "triage", "review", "worklog")


class TestRoutingCases(unittest.TestCase):
    """The case set the routing benchmark measures. Graded here rather than
    only by the harness that reads it: a case file that has drifted below
    its spread is worthless whether or not the harness parses it."""

    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(ROUTING_CASES.read_text(encoding="utf-8"))

    def _class_of(self, case):
        return case["expected"].split(":", 1)[0]

    def test_every_case_has_exactly_the_documented_shape(self):
        self.assertIsInstance(self.cases, list)
        for case in self.cases:
            with self.subTest(case=case.get("id")):
                expected_keys = (
                    CASE_KEYS | ROLE_SKILL_KEYS
                    if case["expected"] == "build"
                    else CASE_KEYS
                )
                self.assertEqual(expected_keys, set(case))
                self.assertIsInstance(case["distractor"], bool)
                for key in ("id", "prompt", "expected", "note"):
                    self.assertTrue(case[key].strip(), key)

    def test_case_ids_are_unique(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))

    def test_the_set_carries_at_least_twenty_four_cases(self):
        self.assertGreaterEqual(len(self.cases), 24)

    def test_every_expected_route_is_in_the_enum(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                expected = case["expected"]
                if expected.startswith("named:"):
                    self.assertTrue(expected.split(":", 1)[1].strip())
                else:
                    self.assertIn(expected, ROUTE_CLASSES)
                    self.assertNotEqual("named", expected, "named needs a name")

    def test_the_route_enum_matches_both_consumers(self):
        self.assertEqual(ROUTE_CLASSES, _support.ROUTE_CLASSES)
        self.assertEqual(ROUTE_CLASSES, routing_live.ROUTE_CLASSES)

    def test_every_class_carries_enough_cases_to_read_a_rate_from(self):
        """Four apiece, except the deliberately narrow routed lanes.

        `build` is not a routed class the block decides — it is one named
        skill, and a prompt reaches it only by saying `orch-build`. Two
        cases say it: one new item, one amendment. Padding the class would
        mean inventing prompts whose honest route is `ticket`, which is what
        the five it replaced were doing.

        The graph-shaped `ticket` and dispatch-bootstrap `doctor` lanes each
        have one producer case; the one-executor cases live under `errand`.
        """

        counts = collections.Counter(self._class_of(case) for case in self.cases)
        self.assertEqual(set(ROUTE_CLASSES), set(counts))
        floors = {"build": 2, "ticket": 1, "doctor": 1}
        for route_class in ROUTE_CLASSES:
            with self.subTest(route_class=route_class):
                self.assertGreaterEqual(
                    counts[route_class], floors.get(route_class, 4), counts
                )

    def test_at_least_four_distractors_borrow_a_lure_word(self):
        distractors = [case for case in self.cases if case["distractor"]]
        self.assertGreaterEqual(len(distractors), 4)
        for case in distractors:
            with self.subTest(case=case["id"]):
                prompt = case["prompt"].lower()
                self.assertTrue(
                    any(word in prompt for word in LURE_WORDS),
                    "a distractor must borrow a deleted or non-routed name",
                )
                # The whole point: the surface word is a lure, and the
                # correct route is still one of the ordinary routed classes.
                self.assertIn(
                    self._class_of(case), ("answer", "errand", "ticket", "fix")
                )

    def test_no_routed_case_reads_as_an_instruction_to_the_grader(self):
        # Prompts are typed into a live session; a prompt that dictated its
        # own route would grade the transcript, not the routing.
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertNotIn("ROUTE:", case["prompt"])

    def test_the_readme_states_the_command_and_the_decision_rule(self):
        readme = ROUTING_DIR / "README.md"
        text = readme.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 25)
        self.assertIn("tools/live_routing_bench.py", text)
        self.assertIn("0.05", text)
        self.assertIn("--claude-adapters", text)


# --- tools/live_routing_bench.py --------------------------------------


def _tool_use(name: str, tool_input: dict, tool_id: str = "t1") -> dict:
    """A parent-level tool call, the only kind the router's first move can be."""

    return {
        "type": "assistant",
        "parent_tool_use_id": None,
        "message": {
            "content": [
                {"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}
            ]
        },
    }


def _skill_use(skill: str, tool_id: str = "t1") -> dict:
    return _tool_use("Skill", {"skill": skill}, tool_id)


def _bash_use(command: str, tool_id: str = "t1") -> dict:
    return _tool_use("Bash", {"command": command}, tool_id)


def _result_event(cost: float) -> dict:
    return {"type": "result", "subtype": "success", "total_cost_usd": cost}


def _child_skill(parent_tool_use_id: str, skill: str, tool_id: str = "s1") -> dict:
    return {
        "type": "assistant",
        "parent_tool_use_id": parent_tool_use_id,
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": "Skill",
                    "input": {"skill": skill},
                }
            ]
        },
    }


class TestRoutingGrading(unittest.TestCase):
    """Every grading branch, against a fabricated stream-json transcript.
    No branch below reaches a `claude` process."""

    def _observed(self, events):
        return routing_live.grade_transcript(_stream(events))["observed"]

    def _conformance(self, events, role="worker", skill="orch-build"):
        return routing_live.grade_transcript(
            _stream(events), expected_role=role, expected_skill=skill
        )["execution_conformance"]

    def test_parent_only_skill_fails_without_matching_role_child(self):
        graded = self._conformance([_skill_use("orch-build")])

        self.assertEqual("failed", graded["status"])
        self.assertIn("missing_matching_role_child", graded["reasons"])
        self.assertEqual(0, graded["primary_skill_executions"])

    def test_root_primary_skill_fails_even_with_matching_child_execution(self):
        graded = self._conformance(
            [
                _skill_use("orch-build"),
                _launch("role-1", "orch-worker", "Apply orch-build exactly"),
                _child_skill("role-1", "orch-build"),
            ]
        )

        self.assertEqual("failed", graded["status"])
        self.assertIn("root_primary_skill_execution", graded["reasons"])
        self.assertEqual(1, graded["root_primary_skill_executions"])

    def test_matching_role_child_requires_exact_skill(self):
        wrong_skill = [
            _launch("role-1", "orch-worker", "Apply orch-build exactly"),
            _child_skill("role-1", "orch-repair"),
        ]
        graded = self._conformance(wrong_skill)
        self.assertEqual("failed", graded["status"])
        self.assertIn("missing_exact_primary_skill", graded["reasons"])

        exact_skill = [
            _launch("role-1", "orch-worker", "Apply orch-build exactly"),
            _child_skill("role-1", "orch-build"),
        ]
        graded = self._conformance(exact_skill)
        self.assertEqual("passed", graded["status"])
        self.assertEqual(1, graded["primary_skill_executions"])

    def test_planner_helper_edges_preserve_primary_skill_single_execution(self):
        events = [
            _launch("planner-1", "orch-planner", "Apply orch-spec exactly"),
            {
                "type": "assistant",
                "parent_tool_use_id": "planner-1",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "primary-1",
                            "name": "Skill",
                            "input": {"skill": "orch-spec"},
                        },
                        {
                            "type": "tool_use",
                            "id": "helper-1",
                            "name": "Agent",
                            "input": {
                                "subagent_type": "orch-worker",
                                "prompt": "Apply orch-investigate to the bounded evidence question",
                            },
                        },
                    ]
                },
            },
            _child_skill("helper-1", "orch-investigate", tool_id="helper-skill"),
        ]
        graded = self._conformance(events, role="planner", skill="orch-spec")
        self.assertEqual("passed", graded["status"])
        self.assertEqual(1, graded["primary_skill_executions"])
        self.assertEqual(1, graded["helper_launches"])

        redispatched = events + [
            _child_skill("helper-1", "orch-spec", tool_id="redispatched-primary")
        ]
        graded = self._conformance(redispatched, role="planner", skill="orch-spec")
        self.assertEqual("failed", graded["status"])
        self.assertIn("primary_skill_redispatched", graded["reasons"])

    def test_the_two_ticket_skills_grade_as_ticket(self):
        for skill in ("orch-frontier", "orch-spec"):
            with self.subTest(skill=skill):
                self.assertEqual("ticket", self._observed([_skill_use(skill)]))

    def test_issuing_a_ticket_from_bash_grades_as_ticket(self):
        command = "python ~/.orchflows/bin/tickets.py new --run r --id A --executor orch-tdd"
        self.assertEqual("ticket", self._observed([_bash_use(command)]))

    def test_errand_and_doctor_commands_grade_as_their_routes(self):
        commands = (
            ("errand", "python ~/.orchflows/bin/tickets.py errand --run r --id A"),
            ("doctor", "python ~/.orchflows/lib/install.py doctor"),
        )
        for expected, command in commands:
            with self.subTest(expected=expected):
                self.assertEqual(expected, self._observed([_bash_use(command)]))

    def test_the_fix_skill_and_the_fix_instantiation_both_grade_as_fix(self):
        self.assertEqual("fix", self._observed([_skill_use("fix")]))
        posix = "tickets.py instantiate ~/.orchflows/lib/compositions/fix --run r"
        self.assertEqual("fix", self._observed([_bash_use(posix)]))

    def test_a_windows_rendered_fix_path_still_grades_as_fix(self):
        # The installed library path is what the host block hands the session,
        # and on Windows it arrives with backslashes.
        windows = r"tickets.py instantiate C:\Users\x\.orchflows\lib\compositions\fix --run r"
        self.assertEqual("fix", self._observed([_bash_use(windows)]))

    def test_orch_build_grades_as_build(self):
        self.assertEqual("build", self._observed([_skill_use("orch-build")]))

    def test_any_other_skill_grades_as_that_name(self):
        for skill in ("evolve", "benchmaker", "drift-canary", "orch-critique"):
            with self.subTest(skill=skill):
                self.assertEqual(f"named:{skill}", self._observed([_skill_use(skill)]))

    def test_a_route_answer_line_grades_as_answer(self):
        self.assertEqual(
            "answer", self._observed([_parent_text("ROUTE: answer\nwrite_scope is ...")])
        )

    def test_a_final_text_with_no_tool_use_grades_as_answer(self):
        events = [_parent_text("write_scope names the paths a ticket may write.")]
        self.assertEqual("answer", self._observed(events))

    def test_reading_the_library_and_then_answering_grades_as_answer(self):
        """Six of the seven `answer` cases need a read before they can be
        answered — the block's own instruction is to read the owner. Any
        tool use at all used to sink the transcript to `unrouted`, so the
        cases that most need reading were the ones that could not pass."""

        events = [
            _tool_use("Read", {"file_path": "/lib/docs/vocabulary.md"}),
            _tool_use("Grep", {"pattern": "write_scope"}, tool_id="t2"),
            _parent_text("write_scope names the paths a ticket may write."),
        ]
        self.assertEqual("answer", self._observed(events))

    def test_a_slash_command_is_read_by_its_first_token(self):
        """`SlashCommand` carries the whole typed line. `/orch-build foo`
        graded `named:orch-build foo` — a route class no case can expect."""

        self.assertEqual(
            "build",
            self._observed([_tool_use("SlashCommand", {"command": "/orch-build a new skill"})]),
        )
        self.assertEqual(
            "named:evolve",
            self._observed([_tool_use("SlashCommand", {"command": "/evolve orch-tdd"})]),
        )

    def test_a_by_name_read_is_the_route_the_four_adapter_set_takes(self):
        """Under `four` the block's fallback for an unadapted name is a read
        of `by-name/<name>/SKILL.md`. Grading that as no route at all gave
        the four-adapter set a structural misroute floor on every `named:`
        case however well the session behaved."""

        for reader in (
            _tool_use("Read", {"file_path": "/home/u/.orchflows/lib/by-name/evolve/SKILL.md"}),
            _bash_use("cat ~/.orchflows/lib/by-name/evolve/SKILL.md"),
            _bash_use(r"type C:\Users\u\.orchflows\lib\by-name\evolve\SKILL.md"),
        ):
            with self.subTest(reader["message"]["content"][0]["name"]):
                self.assertEqual("named:evolve", self._observed([reader]))

    def test_instantiating_a_template_grades_as_that_template(self):
        for name, expected in (("renovate", "named:renovate"), ("fix", "fix")):
            with self.subTest(name):
                command = f"tickets.py instantiate ~/.orchflows/lib/compositions/{name} --run r"
                self.assertEqual(expected, self._observed([_bash_use(command)]))

    def test_a_transcript_with_nothing_route_bearing_is_unrouted(self):
        events = [
            _tool_use("Read", {"file_path": "/repo/AGENTS.md"}),
            _bash_use("git status --short", tool_id="t2"),
        ]
        self.assertEqual("unrouted", self._observed(events))

    def test_an_empty_transcript_is_unrouted(self):
        self.assertEqual("unrouted", self._observed([]))

    def test_an_unauthenticated_session_grades_error_not_answer(self):
        # The first live run: a fresh config dir has no login, the CLI
        # answers "Not logged in" as assistant text and a result event with
        # is_error -- which the text rule read as `answer`.
        events = [
            {
                "type": "assistant",
                "parent_tool_use_id": None,
                "is_api_error_message": True,
                "error": "authentication_failed",
                "message": {"content": [{"type": "text", "text": "Not logged in \u00b7 Please run /login"}]},
            },
            {"type": "result", "is_error": True, "result": "Not logged in", "total_cost_usd": 0},
        ]
        graded = routing_live.grade_transcript(_stream(events))
        self.assertEqual("error", graded["observed"])
        self.assertIn("error", graded["first_event"])

    def test_reading_before_routing_does_not_change_the_route(self):
        events = [
            _tool_use("Read", {"file_path": "/repo/scripts/ui.py"}),
            _skill_use("orch-frontier", tool_id="t2"),
        ]
        graded = routing_live.grade_transcript(_stream(events))
        self.assertEqual("ticket", graded["observed"])
        self.assertEqual(2, graded["turns"])

    def test_the_first_route_bearing_event_decides_it(self):
        events = [_skill_use("evolve"), _bash_use("tickets.py new --id A", tool_id="t2")]
        self.assertEqual("named:evolve", self._observed(events))
        reversed_events = [
            _bash_use("tickets.py new --id A"),
            _skill_use("evolve", tool_id="t2"),
        ]
        self.assertEqual("ticket", self._observed(reversed_events))

    def test_a_text_answer_after_a_skill_never_overrides_the_skill(self):
        events = [_skill_use("fix"), _parent_text("ROUTE: answer")]
        self.assertEqual("fix", self._observed(events))

    def test_the_deciding_event_is_reported(self):
        graded = routing_live.grade_transcript(_stream([_skill_use("orch-build")]))
        self.assertIn("orch-build", graded["first_event"])
        self.assertIsNone(
            routing_live.grade_transcript(_stream([]))["first_event"]
        )

    def test_the_cost_is_taken_from_the_stream_when_it_reports_one(self):
        events = [_skill_use("fix"), _result_event(0.0125)]
        self.assertEqual(0.0125, routing_live.grade_transcript(_stream(events))["cost_usd"])
        self.assertIsNone(
            routing_live.grade_transcript(_stream([_skill_use("fix")]))["cost_usd"]
        )

    def test_subagent_events_never_decide_the_route(self):
        # A child's own tool use is not the session's routing decision.
        child = {
            "type": "assistant",
            "parent_tool_use_id": "t9",
            "message": {
                "content": [
                    {"type": "tool_use", "id": "c1", "name": "Skill", "input": {"skill": "evolve"}}
                ]
            },
        }
        self.assertEqual("unrouted", self._observed([child]))

    def test_non_dict_stream_entries_are_tolerated(self):
        events = [_skill_use("orch-build")]
        events[0]["message"]["content"].insert(0, "bare string block")
        stream = _stream(events) + '\n"a bare json string"\n[1, 2]'
        self.assertEqual("build", routing_live.grade_transcript(stream)["observed"])


class TestRoutingCaseLoader(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, payload):
        path = self.tmp / "cases.json"
        path.write_bytes(json.dumps(payload).encode("utf-8"))
        return path

    def test_only_a_prompt_naming_orch_build_expects_the_build_route(self):
        """templates/host-block.md routes an unnamed request to answer,
        ticket or fix, and says everything else runs only when named.
        `orch-build` appears in the block as a scope-law pointer, not as a
        route — so five prompts that never said `orch-build` and expected
        `build` were measuring the benchmark's own invention."""

        cases = json.loads(ROUTING_CASES.read_text(encoding="utf-8"))
        build = [case for case in cases if case["expected"] == "build"]
        self.assertEqual(2, len(build), [case["id"] for case in build])
        for case in build:
            self.assertIn("orch-build", case["prompt"])
            self.assertEqual("worker", case["required_role"])
            self.assertEqual("orch-build", case["required_skill"])
        for case in cases:
            if case["expected"] != "build":
                self.assertNotIn("orch-build", case["prompt"], case["id"])
        self.assertEqual(37, len(cases))

    def test_the_catalog_counterfactual_uses_answer_then_one_known_cause_errand(self):
        cases = {
            case["id"]: case
            for case in json.loads(ROUTING_CASES.read_text(encoding="utf-8"))
        }

        explanation = cases["answer-codex-catalog-gap"]
        self.assertEqual("answer", explanation["expected"])
        self.assertIn("explanation only", explanation["note"])

        implementation = cases["ticket-codex-catalog-gap"]
        self.assertEqual("errand", implementation["expected"])
        for expectation in (
            "known cause",
            "one ordered errand",
            "derived consequences",
        ):
            with self.subTest(expectation=expectation):
                self.assertIn(expectation, implementation["note"].lower())
        self.assertIn(
            "with no spec, decompose, or fix workflow", implementation["note"].lower()
        )

    def test_the_shipped_case_file_loads(self):
        self.assertEqual(
            len(json.loads(ROUTING_CASES.read_text(encoding="utf-8"))),
            len(routing_live.load_cases(routing_live.DEFAULT_CASES)),
        )

    def test_a_non_list_is_refused(self):
        with self.assertRaisesRegex(ValueError, "non-empty list"):
            routing_live.load_cases(self._write({"cases": []}))

    def test_a_case_missing_a_field_is_refused(self):
        with self.assertRaisesRegex(ValueError, "expected"):
            routing_live.load_cases(self._write([{"id": "a", "prompt": "p"}]))

    def test_an_off_enum_expected_route_is_refused(self):
        payload = [{"id": "a", "prompt": "p", "expected": "escalate", "note": "n"}]
        with self.assertRaisesRegex(ValueError, "escalate"):
            routing_live.load_cases(self._write(payload))

    def test_a_named_route_without_a_name_is_refused(self):
        payload = [{"id": "a", "prompt": "p", "expected": "named:", "note": "n"}]
        with self.assertRaisesRegex(ValueError, "named"):
            routing_live.load_cases(self._write(payload))

    def test_a_role_bearing_route_requires_its_exact_role_skill_pair(self):
        payload = [{"id": "a", "prompt": "p", "expected": "build", "note": "n"}]
        with self.assertRaisesRegex(ValueError, "role/skill"):
            routing_live.load_cases(self._write(payload))

        payload[0]["required_role"] = "planner"
        payload[0]["required_skill"] = "orch-spec"
        with self.assertRaisesRegex(ValueError, "role/skill"):
            routing_live.load_cases(self._write(payload))
