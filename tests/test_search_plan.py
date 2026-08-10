"""Public-seam checks for deterministic search planning."""

from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVOLVE = ROOT / "compositions" / "evolve.md"
EVOLVE_GENERATION = ROOT / "compositions" / "references" / "evolve-generation.md"
TOURNAMENT = ROOT / "compositions" / "skill-tournament.md"
SEARCH_SKILL = ROOT / "skills" / "utilities" / "orch-search-plan" / "SKILL.md"
SEARCH_SCRIPT = (
    ROOT
    / "skills"
    / "utilities"
    / "orch-search-plan"
    / "scripts"
    / "search_plan.py"
)

CALL_EDGE_RE = re.compile(r"`(orch-[a-z0-9-]+)`")


def canonical_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def tagged_identity(tag, payload):
    digest = hashlib.sha256(tag.encode("utf-8") + b"\0" + canonical_bytes(payload))
    return "sha256:" + digest.hexdigest()


def with_identity(tag, payload):
    value = copy.deepcopy(payload)
    value["identity"] = tagged_identity(tag, payload)
    return value


def generation_zero_request():
    policy = with_identity(
        "search-policy/v1",
        {
            "schema": "search-policy/v1",
            "planner_revision": "git:planner-1",
            "target_owner_identity": "owner:fixture",
            "mutation_surface_identities": ["surface:prompt"],
            "benchmark_revision": "git:benchmark-1",
            "scoring_identity": "scoring:fixture",
            "dimensions": [
                {
                    "identity": "dimension:quality",
                    "direction": "maximize",
                    "source_identity": "source:public-score",
                    "resolution": "0.1",
                }
            ],
            "feedback_source_identities": ["source:public-feedback"],
            "ordering_seed": "seed:fixture",
            "generation_width": 1,
            "merge_slots": 0,
            "bound_unit_names": ["runs"],
            "reservations": {
                "reflect": {"runs": 1},
                "merge": {"runs": 2},
            },
        },
    )
    origin = {
        "kind": "admitted",
        "outcome_identity": "outcome:origin",
        "slot_identity": None,
        "cost": {"runs": 0},
        "candidate_identity": "candidate:origin",
        "parent_identities": [],
        "target_owner_identity": "owner:fixture",
        "mutation_surface_identities": ["surface:prompt"],
        "benchmark_revision": "git:benchmark-1",
        "result_identity": "result:origin",
        "evidence_identity": "evidence:origin",
        "eligibility_status": "PASS",
        "eligibility_verdict_identity": "verdict:origin",
        "score_card_identity": "score-card:origin",
        "dimension_vector": [
            {"identity": "dimension:quality", "value": "0.5"}
        ],
        "feedback": [
            {
                "source_identity": "source:public-feedback",
                "dimension_identity": "dimension:quality",
                "reference_identity": "feedback:origin",
            }
        ],
    }
    return {
        "policy": policy,
        "projection": None,
        "settled": {
            "preferred_incumbent_identity": "candidate:origin",
            "outcomes": [origin],
        },
        "remaining_bound": {"runs": 1},
    }


def two_dimension_request(width=3, merge_slots=1, resolution="0.1"):
    request = generation_zero_request()
    policy = request["policy"]
    policy["dimensions"] = [
        {
            "identity": "dimension:quality",
            "direction": "maximize",
            "source_identity": "source:public-score",
            "resolution": resolution,
        },
        {
            "identity": "dimension:cost",
            "direction": "minimize",
            "source_identity": "source:public-cost",
            "resolution": resolution,
        },
    ]
    policy["generation_width"] = width
    policy["merge_slots"] = merge_slots
    policy["identity"] = tagged_identity(
        "search-policy/v1",
        {key: value for key, value in policy.items() if key != "identity"},
    )
    origin = request["settled"]["outcomes"][0]
    origin["dimension_vector"] = [
        {"identity": "dimension:quality", "value": "0.5"},
        {"identity": "dimension:cost", "value": "0.5"},
    ]
    origin["feedback"].append(
        {
            "source_identity": "source:public-feedback",
            "dimension_identity": "dimension:cost",
            "reference_identity": "feedback:origin-cost",
        }
    )
    request["remaining_bound"] = {"runs": width * 2}
    return request


def admitted_outcome(slot, candidate, quality, cost, suffix=None):
    suffix = suffix or candidate.rsplit(":", 1)[-1]
    return {
        "kind": "admitted",
        "outcome_identity": f"outcome:{suffix}",
        "slot_identity": slot["identity"],
        "cost": {"runs": 1},
        "candidate_identity": candidate,
        "parent_identities": copy.deepcopy(slot["parent_identities"]),
        "target_owner_identity": slot["target_owner_identity"],
        "mutation_surface_identities": copy.deepcopy(
            slot["mutation_surface_identities"]
        ),
        "benchmark_revision": slot["benchmark_revision"],
        "result_identity": f"result:{suffix}",
        "evidence_identity": f"evidence:{suffix}",
        "eligibility_status": "PASS",
        "eligibility_verdict_identity": f"verdict:{suffix}",
        "score_card_identity": f"score-card:{suffix}",
        "dimension_vector": [
            {"identity": "dimension:quality", "value": quality},
            {"identity": "dimension:cost", "value": cost},
        ],
        "feedback": [
            {
                "source_identity": "source:public-feedback",
                "dimension_identity": "dimension:quality",
                "reference_identity": f"feedback:{suffix}-quality",
            },
            {
                "source_identity": "source:public-feedback",
                "dimension_identity": "dimension:cost",
                "reference_identity": f"feedback:{suffix}-cost",
            },
        ],
    }


def ineligible_outcome(slot, candidate, suffix=None):
    suffix = suffix or candidate.rsplit(":", 1)[-1]
    return {
        "kind": "ineligible",
        "outcome_identity": f"outcome:{suffix}",
        "slot_identity": slot["identity"],
        "cost": {"runs": 1},
        "candidate_identity": candidate,
        "parent_identities": copy.deepcopy(slot["parent_identities"]),
        "target_owner_identity": slot["target_owner_identity"],
        "mutation_surface_identities": copy.deepcopy(
            slot["mutation_surface_identities"]
        ),
        "benchmark_revision": slot["benchmark_revision"],
        "result_identity": f"result:{suffix}",
        "evidence_identity": f"evidence:{suffix}",
        "eligibility_status": "FAIL",
        "eligibility_verdict_identity": f"verdict:{suffix}",
        "disposition": "failed-required-check",
    }


def settled_request(policy, response, outcomes, preferred, remaining=20):
    return {
        "policy": copy.deepcopy(policy),
        "projection": copy.deepcopy(response["projection"]),
        "settled": {
            "preferred_incumbent_identity": preferred,
            "outcomes": copy.deepcopy(outcomes),
        },
        "remaining_bound": {"runs": remaining},
    }


def reverse_object_keys(value):
    if isinstance(value, dict):
        return {
            key: reverse_object_keys(value[key])
            for key in reversed(list(value))
        }
    if isinstance(value, list):
        return [reverse_object_keys(item) for item in value]
    return value


def run_advance(payload=None, raw=None, cwd=None):
    data = raw if raw is not None else canonical_bytes(payload)
    return subprocess.run(
        [sys.executable, str(SEARCH_SCRIPT), "advance"],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        check=False,
    )


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


def worklog_restart_errors(generation: str):
    contract = normalized(generation)
    errors = []
    if (
        "latest worklog entry persists the accepted response's complete projection, "
        "including every archive member"
        not in contract
    ):
        errors.append("archive-persistence")
    if "`in_flight` in the same worklog entry before delegation" not in contract:
        errors.append("in-flight-order")
    if "a `pending` response launches nothing" not in contract:
        errors.append("pending-replan")
    if "never redispatch a live slot" not in contract:
        errors.append("duplicate-restart-dispatch")
    return errors


def plan_shape(response):
    return [
        {
            key: copy.deepcopy(value)
            for key, value in slot.items()
            if key not in {"identity", "target_owner_identity"}
        }
        for slot in response["plan"]["slots"]
    ]


def recursive_target_errors(evolve: str, generation: str, tournament: str):
    evolve_contract = normalized(evolve)
    generation_contract = normalized(generation)
    tournament_contract = normalized(tournament)
    errors = []
    if (
        "active controller and planner revisions remain outside candidate mutation authority"
        not in generation_contract
    ):
        errors.append("active-revision-authority")
    if (
        "a self-target candidate remains non-control and cannot become the active campaign "
        "controller or planner"
        not in generation_contract
    ):
        errors.append("self-target-control")
    if (
        "activate a selected candidate" not in evolve_contract
        or "selected result is never activated by this campaign" not in generation_contract
        or "separate authorized integration before activation" not in tournament_contract
    ):
        errors.append("activation")
    return errors


def architecture_errors(evolve: str, generation: str, tournament: str, leaf: str):
    errors = []
    combined_evolve = evolve + generation
    evolve_calls = Counter(CALL_EDGE_RE.findall(combined_evolve))
    required = {
        "orch-delegate",
        "orch-integrate",
        "orch-judge",
        "orch-loop",
        "orch-panel",
        "orch-search-plan",
        "orch-verify",
        "orch-worklog",
    }
    if evolve_calls != Counter({name: 1 for name in required}):
        errors.append("evolve-call-graph")
    if re.search(r"^-\s*closing\b", evolve, re.IGNORECASE | re.MULTILINE):
        errors.append("closing-wrapper")
    if normalized(combined_evolve).count("`orch-judge`") != 1:
        errors.append("judge-owner")

    tournament_calls = set(CALL_EDGE_RE.findall(tournament))
    if tournament_calls:
        errors.append("tournament-internal-call")
    if "writer binding orch-build" not in normalized(tournament):
        errors.append("tournament-writer-binding")
    if "promotion" in normalized(tournament):
        errors.append("tournament-promotion")

    leaf_calls = set(CALL_EDGE_RE.findall(leaf)) - {"orch-search-plan"}
    if leaf_calls:
        errors.append("leaf-call")
    return errors


class TestArchitecture(unittest.TestCase):
    def test_thin_evolve_owns_one_campaign_call_graph(self):
        for path in (EVOLVE, EVOLVE_GENERATION, TOURNAMENT, SEARCH_SKILL, SEARCH_SCRIPT):
            self.assertTrue(path.is_file(), f"missing search-planning surface: {path}")

        evolve = read(EVOLVE)
        generation = read(EVOLVE_GENERATION)
        tournament = read(TOURNAMENT)
        leaf = read(SEARCH_SKILL)
        self.assertEqual([], architecture_errors(evolve, generation, tournament, leaf))
        self.assertIn("role: none", leaf)
        command = "python skills/utilities/orch-search-plan/scripts/search_plan.py advance"
        self.assertEqual(1, leaf.count(command))
        self.assertNotIn("operation registry", normalized(leaf))

    def test_known_wrong_ownership_fixtures_are_rejected(self):
        evolve = read(EVOLVE)
        generation = read(EVOLVE_GENERATION)
        tournament = read(TOURNAMENT)
        leaf = read(SEARCH_SKILL)

        closing = evolve + "\n- closing — a fresh `orch-judge` wrapper.\n"
        self.assertIn(
            "closing-wrapper",
            architecture_errors(closing, generation, tournament, leaf),
        )
        direct_panel = tournament + "\nDirectly call `orch-panel`.\n"
        self.assertIn(
            "tournament-internal-call",
            architecture_errors(evolve, generation, direct_panel, leaf),
        )
        extra_leaf_call = leaf + "\nCall `orch-verify`.\n"
        self.assertIn(
            "leaf-call",
            architecture_errors(evolve, generation, tournament, extra_leaf_call),
        )


class TestCanonicalAdvance(unittest.TestCase):
    def assert_rejected(self, payload=None, raw=None):
        result = run_advance(payload=payload, raw=raw)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertTrue(result.stderr.startswith(b"search-plan: "))
        self.assertLessEqual(len(result.stderr), 512)

    def test_generation_zero_is_byte_stable_and_read_only(self):
        request = generation_zero_request()
        with tempfile.TemporaryDirectory() as directory:
            first = run_advance(request, cwd=directory)
            second = run_advance(reverse_object_keys(request), cwd=directory)
            self.assertEqual([], list(Path(directory).iterdir()))

        self.assertEqual(0, first.returncode, first.stderr.decode())
        self.assertEqual(b"", first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertTrue(first.stdout.endswith(b"\n"))
        self.assertNotEqual(b"\n\n", first.stdout[-2:])

        response = json.loads(first.stdout)
        self.assertEqual("search-advance/v1", response["schema"])
        self.assertEqual("planned", response["status"])
        self.assertIsNone(response["input_projection_identity"])
        self.assertEqual([], response["missing_slot_identities"])
        self.assertEqual([], response["diagnostics"])

        projection = response["projection"]
        plan = response["plan"]
        self.assertEqual(projection["identity"], response["output_projection_identity"])
        self.assertEqual(
            projection["identity"],
            tagged_identity(
                "search-projection/v1",
                {key: value for key, value in projection.items() if key != "identity"},
            ),
        )
        self.assertEqual(
            plan["identity"],
            tagged_identity(
                "search-plan/v1",
                {key: value for key, value in plan.items() if key != "identity"},
            ),
        )
        self.assertEqual(0, projection["last_settled_generation"])
        self.assertEqual(plan, projection["last_plan"])
        self.assertEqual(["candidate:origin"], projection["archive"])
        self.assertEqual([request["settled"]["outcomes"][0]], projection["nodes"])
        self.assertEqual(["outcome:origin"], plan["basis_outcome_identities"])
        self.assertEqual(1, plan["generation"])

        self.assertEqual(1, len(plan["slots"]))
        slot = plan["slots"][0]
        self.assertEqual("reflect", slot["kind"])
        self.assertEqual(["candidate:origin"], slot["parent_identities"])
        self.assertEqual("dimension:quality", slot["focus_dimension_identity"])
        self.assertEqual([], slot["complementary_dimension_identities"])
        self.assertEqual({"runs": 1}, slot["reservation"])
        self.assertEqual(request["settled"]["outcomes"][0]["feedback"], slot["feedback"])
        self.assertEqual(
            slot["identity"],
            tagged_identity(
                "search-slot/v1",
                {key: value for key, value in slot.items() if key != "identity"},
            ),
        )

    def test_closed_schema_identity_numeric_and_reference_failures_exit_two(self):
        cases = []

        protected = generation_zero_request()
        protected["settled"]["outcomes"][0]["protected_locator"] = "secret:item"
        cases.append(protected)

        feedback = generation_zero_request()
        feedback["settled"]["outcomes"][0]["feedback"][0][
            "source_identity"
        ] = "source:held-back"
        cases.append(feedback)

        identity = generation_zero_request()
        identity["policy"]["identity"] = "sha256:" + "0" * 64
        cases.append(identity)

        numeric = generation_zero_request()
        numeric["policy"]["dimensions"][0]["resolution"] = "0.10"
        numeric["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {key: value for key, value in numeric["policy"].items() if key != "identity"},
        )
        cases.append(numeric)

        reference = generation_zero_request()
        reference["settled"]["preferred_incumbent_identity"] = "candidate:absent"
        cases.append(reference)

        for case in cases:
            with self.subTest(case=cases.index(case)):
                self.assert_rejected(case)

        floating = generation_zero_request()
        floating["remaining_bound"]["runs"] = 1.0
        self.assert_rejected(floating)

        duplicate = canonical_bytes(generation_zero_request()).replace(
            b'"projection":null',
            b'"projection":null,"projection":null',
            1,
        )
        self.assert_rejected(raw=duplicate)


class TestParetoReflection(unittest.TestCase):
    def run_ok(self, request):
        result = run_advance(request)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        self.assertEqual(b"", result.stderr)
        return json.loads(result.stdout)

    def settled_fixture(self, resolution="0.1"):
        initial_request = two_dimension_request(resolution=resolution)
        initial = self.run_ok(initial_request)
        slots = initial["plan"]["slots"]
        outcomes = [
            admitted_outcome(slots[0], "candidate:a", "0.8", "0.6", "a"),
            admitted_outcome(slots[1], "candidate:b", "0.4", "0.2", "b"),
            admitted_outcome(slots[2], "candidate:dominated", "0.3", "0.8", "d"),
        ]
        request = settled_request(
            initial_request["policy"],
            initial,
            list(reversed(outcomes)),
            "candidate:dominated",
        )
        return request, outcomes

    def assert_pareto_response(self, response):
        projection = response["projection"]
        self.assertEqual(
            {"candidate:origin", "candidate:a", "candidate:b"},
            set(projection["archive"]),
        )
        self.assertEqual(4, len(projection["nodes"]))
        first = response["plan"]["slots"][0]
        self.assertEqual("reflect", first["kind"])
        self.assertEqual(["candidate:dominated"], first["parent_identities"])
        self.assertIn(
            first["focus_dimension_identity"],
            {"dimension:quality", "dimension:cost"},
        )
        self.assertTrue(first["feedback"])
        self.assertTrue(
            all(
                item["dimension_identity"] == first["focus_dimension_identity"]
                for item in first["feedback"]
            )
        )

    def test_resolution_aware_archive_reflection_and_replay(self):
        request, _ = self.settled_fixture()
        response = self.run_ok(request)
        replay = run_advance(reverse_object_keys(request))
        self.assertEqual(0, replay.returncode, replay.stderr.decode())
        self.assertEqual(canonical_bytes(response) + b"\n", replay.stdout)
        self.assert_pareto_response(response)

        dominated_retained = copy.deepcopy(response)
        dominated_retained["projection"]["archive"].append("candidate:dominated")
        with self.assertRaises(AssertionError):
            self.assert_pareto_response(dominated_retained)

    def test_feedback_changes_the_reflection_packet_identity(self):
        request, outcomes = self.settled_fixture()
        original = self.run_ok(request)
        changed = copy.deepcopy(request)
        dominated = next(
            item
            for item in changed["settled"]["outcomes"]
            if item.get("candidate_identity") == "candidate:dominated"
        )
        dominated["feedback"][0]["reference_identity"] = "feedback:d-quality-v2"
        revised = self.run_ok(changed)
        original_slot = original["plan"]["slots"][0]
        revised_slot = revised["plan"]["slots"][0]
        self.assertNotEqual(original_slot["feedback"], revised_slot["feedback"])
        self.assertNotEqual(original_slot["identity"], revised_slot["identity"])

        ignored_feedback = copy.deepcopy(revised_slot)
        ignored_feedback["identity"] = original_slot["identity"]
        with self.assertRaises(AssertionError):
            self.assertEqual(
                ignored_feedback["identity"],
                tagged_identity(
                    "search-slot/v1",
                    {
                        key: value
                        for key, value in ignored_feedback.items()
                        if key != "identity"
                    },
                ),
            )

    def test_comparison_exceeds_decimal_context_precision(self):
        resolution = "0.123456789012345678901234567890123456789"
        request, _ = self.settled_fixture(resolution=resolution)
        for outcome in request["settled"]["outcomes"]:
            if outcome["candidate_identity"] == "candidate:a":
                outcome["dimension_vector"] = [
                    {"identity": "dimension:quality", "value": resolution},
                    {"identity": "dimension:cost", "value": "0"},
                ]
            elif outcome["candidate_identity"] == "candidate:b":
                outcome["dimension_vector"] = [
                    {"identity": "dimension:quality", "value": "0"},
                    {"identity": "dimension:cost", "value": resolution},
                ]
            else:
                outcome["dimension_vector"] = [
                    {"identity": "dimension:quality", "value": "0"},
                    {"identity": "dimension:cost", "value": "1"},
                ]
        response = self.run_ok(request)
        self.assertNotIn("candidate:dominated", response["projection"]["archive"])


class TestMergeLineage(unittest.TestCase):
    def run_ok(self, request):
        result = run_advance(request)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        self.assertEqual(b"", result.stderr)
        return json.loads(result.stdout)

    def assert_rejected(self, request):
        result = run_advance(request)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)

    def merge_fixture(self):
        initial_request = two_dimension_request()
        initial = self.run_ok(initial_request)
        slots = initial["plan"]["slots"]
        outcomes = [
            admitted_outcome(slots[0], "candidate:a", "0.8", "0.6", "a"),
            admitted_outcome(slots[1], "candidate:b", "0.4", "0.2", "b"),
            admitted_outcome(slots[2], "candidate:dominated", "0.3", "0.8", "d"),
        ]
        request = settled_request(
            initial_request["policy"],
            initial,
            outcomes,
            "candidate:dominated",
        )
        return initial_request["policy"], self.run_ok(request)

    def test_complementary_merge_and_complete_fresh_lineage(self):
        policy, generation_two = self.merge_fixture()
        slots = generation_two["plan"]["slots"]
        self.assertEqual(["reflect", "reflect", "merge"], [s["kind"] for s in slots])
        merge = slots[-1]
        self.assertEqual(2, len(merge["parent_identities"]))
        self.assertEqual(
            {"dimension:quality", "dimension:cost"},
            set(merge["complementary_dimension_identities"]),
        )

        outcomes = [
            admitted_outcome(slots[0], "candidate:reflected", "0.7", "0.4", "r"),
            ineligible_outcome(slots[1], "candidate:ineligible", "i"),
            admitted_outcome(merge, "candidate:merged", "0.9", "0.1", "m"),
        ]
        request = settled_request(
            policy, generation_two, outcomes, "candidate:merged"
        )
        advanced = self.run_ok(request)
        nodes = advanced["projection"]["nodes"]
        self.assertEqual(7, len(nodes))
        self.assertIn("candidate:ineligible", [node["candidate_identity"] for node in nodes])
        self.assertNotIn("candidate:ineligible", advanced["projection"]["archive"])
        seen = set()
        for node in nodes:
            self.assertTrue(set(node["parent_identities"]) <= seen)
            self.assertNotIn(node["candidate_identity"], seen)
            seen.add(node["candidate_identity"])

        merged = next(node for node in nodes if node["candidate_identity"] == "candidate:merged")
        parents = [
            node for node in nodes if node["candidate_identity"] in merged["parent_identities"]
        ]
        for field in (
            "candidate_identity",
            "result_identity",
            "evidence_identity",
            "eligibility_verdict_identity",
            "score_card_identity",
        ):
            self.assertNotIn(merged[field], [parent[field] for parent in parents])

        for slot in generation_two["plan"]["slots"]:
            self.assertEqual(
                slot["identity"],
                tagged_identity(
                    "search-slot/v1",
                    {key: value for key, value in slot.items() if key != "identity"},
                ),
            )
            self.assertNotIn("plan_identity", slot)
        self.assertEqual(
            generation_two["plan"]["identity"],
            tagged_identity(
                "search-plan/v1",
                {
                    key: value
                    for key, value in generation_two["plan"].items()
                    if key != "identity"
                },
            ),
        )
        projection = advanced["projection"]
        self.assertEqual(
            projection["identity"],
            tagged_identity(
                "search-projection/v1",
                {key: value for key, value in projection.items() if key != "identity"},
            ),
        )

    def test_settlement_is_exact_and_atomic(self):
        policy, generation_two = self.merge_fixture()
        slots = generation_two["plan"]["slots"]
        partial = settled_request(
            policy,
            generation_two,
            [admitted_outcome(slots[0], "candidate:partial", "0.6", "0.4", "p")],
            "candidate:partial",
        )
        pending = self.run_ok(partial)
        self.assertEqual("pending", pending["status"])
        self.assertEqual(generation_two["projection"], pending["projection"])
        self.assertEqual(
            generation_two["projection"]["identity"],
            pending["output_projection_identity"],
        )
        self.assertIsNone(pending["plan"])
        self.assertEqual([slot["identity"] for slot in slots[1:]], pending["missing_slot_identities"])

        malformed = copy.deepcopy(partial)
        malformed["settled"]["atomic"] = True
        self.assert_rejected(malformed)

    def test_cycle_dangling_reuse_and_inherited_score_are_rejected(self):
        policy, generation_two = self.merge_fixture()
        slots = generation_two["plan"]["slots"]
        outcomes = [
            admitted_outcome(slots[0], "candidate:reflected", "0.7", "0.4", "r"),
            ineligible_outcome(slots[1], "candidate:ineligible", "i"),
            admitted_outcome(slots[2], "candidate:merged", "0.9", "0.1", "m"),
        ]

        reused = settled_request(policy, generation_two, outcomes, "candidate:merged")
        reused["settled"]["outcomes"][0]["candidate_identity"] = "candidate:origin"
        self.assert_rejected(reused)

        inherited = settled_request(policy, generation_two, outcomes, "candidate:merged")
        merge_outcome = inherited["settled"]["outcomes"][2]
        parent_identity = merge_outcome["parent_identities"][0]
        parent = next(
            node
            for node in inherited["projection"]["nodes"]
            if node["candidate_identity"] == parent_identity
        )
        merge_outcome["score_card_identity"] = parent["score_card_identity"]
        self.assert_rejected(inherited)

        valid = settled_request(policy, generation_two, outcomes, "candidate:merged")
        advanced = self.run_ok(valid)
        for replacement in ("candidate:missing", "candidate:merged"):
            broken = copy.deepcopy(advanced)
            broken_node = broken["projection"]["nodes"][1]
            broken_node["parent_identities"] = [replacement]
            payload = {
                key: value
                for key, value in broken["projection"].items()
                if key != "identity"
            }
            broken["projection"]["identity"] = tagged_identity(
                "search-projection/v1", payload
            )
            next_request = settled_request(
                policy, broken, [], "candidate:merged"
            )
            self.assert_rejected(next_request)


class TestBoundedResume(unittest.TestCase):
    def run_ok(self, request):
        result = run_advance(request)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        self.assertEqual(b"", result.stderr)
        return json.loads(result.stdout)

    def bounded_request(self, remaining):
        request = generation_zero_request()
        policy = request["policy"]
        policy["generation_width"] = 3
        policy["bound_unit_names"] = ["runs", "tokens"]
        policy["reservations"] = {
            "reflect": {"runs": 2, "tokens": 3},
            "merge": {"runs": 1, "tokens": 1},
        }
        policy["identity"] = tagged_identity(
            "search-policy/v1",
            {key: value for key, value in policy.items() if key != "identity"},
        )
        request["settled"]["outcomes"][0]["cost"] = {"runs": 0, "tokens": 0}
        request["remaining_bound"] = remaining
        return request

    def assert_within_bound(self, response, remaining):
        spent = {unit: 0 for unit in remaining}
        plan = response["plan"]
        if plan is not None:
            for slot in plan["slots"]:
                for unit in remaining:
                    spent[unit] += slot["reservation"][unit]
        self.assertTrue(
            all(spent[unit] <= remaining[unit] for unit in remaining),
            f"reservation {spent} exceeds {remaining}",
        )

    def test_componentwise_maximal_prefix_exact_fit_and_no_fit(self):
        for remaining in ({"runs": 4, "tokens": 100}, {"runs": 100, "tokens": 6}):
            with self.subTest(remaining=remaining):
                response = self.run_ok(self.bounded_request(remaining))
                self.assertEqual("planned", response["status"])
                self.assertEqual(2, len(response["plan"]["slots"]))
                self.assert_within_bound(response, remaining)
                reservation = response["plan"]["slots"][0]["reservation"]
                spent = {
                    unit: sum(slot["reservation"][unit] for slot in response["plan"]["slots"])
                    for unit in remaining
                }
                self.assertTrue(
                    any(spent[unit] + reservation[unit] > remaining[unit] for unit in remaining)
                )

        exact_bound = {"runs": 6, "tokens": 9}
        exact = self.run_ok(self.bounded_request(exact_bound))
        self.assertEqual(3, len(exact["plan"]["slots"]))
        self.assert_within_bound(exact, exact_bound)
        self.assertEqual(
            exact_bound,
            {
                unit: sum(slot["reservation"][unit] for slot in exact["plan"]["slots"])
                for unit in exact_bound
            },
        )

        no_fit = self.run_ok(self.bounded_request({"runs": 1, "tokens": 100}))
        self.assertEqual("no_fit", no_fit["status"])
        self.assertIsNone(no_fit["plan"])
        self.assertIsNone(no_fit["projection"]["last_plan"])
        self.assertEqual(["candidate:origin"], no_fit["projection"]["archive"])

        over_reserved = copy.deepcopy(exact)
        over_reserved["plan"]["slots"].append(
            copy.deepcopy(over_reserved["plan"]["slots"][-1])
        )
        with self.assertRaises(AssertionError):
            self.assert_within_bound(over_reserved, exact_bound)

    def test_partial_settlement_keeps_projection_and_complete_archive(self):
        initial_request = two_dimension_request()
        initial = self.run_ok(initial_request)
        slots = initial["plan"]["slots"]
        outcomes = [
            admitted_outcome(slots[0], "candidate:a", "0.8", "0.6", "a"),
            admitted_outcome(slots[1], "candidate:b", "0.4", "0.2", "b"),
            admitted_outcome(slots[2], "candidate:dominated", "0.3", "0.8", "d"),
        ]
        generation_two = self.run_ok(
            settled_request(
                initial_request["policy"], initial, outcomes, "candidate:origin"
            )
        )
        generation_two_slots = generation_two["plan"]["slots"]
        partial = settled_request(
            initial_request["policy"],
            generation_two,
            [
                admitted_outcome(
                    generation_two_slots[0], "candidate:partial", "0.7", "0.4", "p"
                )
            ],
            "candidate:origin",
        )
        pending = self.run_ok(partial)
        self.assertEqual("pending", pending["status"])
        self.assertIsNone(pending["plan"])
        self.assertEqual(generation_two["projection"], pending["projection"])
        self.assertEqual(
            generation_two["projection"]["archive"], pending["projection"]["archive"]
        )
        self.assertEqual(
            [slot["identity"] for slot in generation_two_slots[1:]],
            pending["missing_slot_identities"],
        )

    def test_worklog_launch_and_restart_contract_has_failure_controls(self):
        generation = read(EVOLVE_GENERATION)
        self.assertEqual([], worklog_restart_errors(generation))

        controls = {
            "archive-persistence": generation.replace(
                "complete projection, including every archive member",
                "projection without the full archive",
            ),
            "in-flight-order": generation.replace(
                "same Worklog entry before delegation",
                "same Worklog entry after delegation",
            ),
            "pending-replan": generation.replace(
                "a `pending` response launches nothing",
                "a `pending` response launches a replacement",
            ),
            "duplicate-restart-dispatch": generation.replace(
                "never redispatch a live slot",
                "redispatch a live slot",
            ),
        }
        for expected, wrong in controls.items():
            with self.subTest(control=expected):
                self.assertIn(expected, worklog_restart_errors(wrong))


class TestVisibilityAndSelfTarget(unittest.TestCase):
    def run_ok(self, request):
        result = run_advance(request)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        self.assertEqual(b"", result.stderr)
        return json.loads(result.stdout)

    def assert_rejected(self, request):
        result = run_advance(request)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)

    def test_closed_schema_rejects_protected_inputs(self):
        cases = []

        request_field = generation_zero_request()
        request_field["protected_locator"] = "protected:item"
        cases.append(request_field)

        policy_field = generation_zero_request()
        policy_field["policy"]["held_back_result_identity"] = "result:held-back"
        cases.append(policy_field)

        outcome_field = generation_zero_request()
        outcome_field["settled"]["outcomes"][0][
            "closing_verdict_identity"
        ] = "verdict:closing"
        cases.append(outcome_field)

        feedback_field = generation_zero_request()
        feedback_field["settled"]["outcomes"][0]["feedback"][0][
            "protected_derived"
        ] = True
        cases.append(feedback_field)

        for case in cases:
            with self.subTest(field=cases.index(case)):
                self.assert_rejected(case)

    def test_target_renaming_preserves_plan_shape(self):
        original_request = two_dimension_request()
        original = self.run_ok(original_request)

        renamed_request = copy.deepcopy(original_request)
        renamed_request["policy"]["target_owner_identity"] = "owner:self-target"
        renamed_request["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in renamed_request["policy"].items()
                if key != "identity"
            },
        )
        renamed_request["settled"]["outcomes"][0][
            "target_owner_identity"
        ] = "owner:self-target"
        renamed = self.run_ok(renamed_request)

        self.assertEqual(plan_shape(original), plan_shape(renamed))
        self.assertNotEqual(original["plan"]["identity"], renamed["plan"]["identity"])

        target_branched = copy.deepcopy(renamed)
        target_branched["plan"]["slots"][0][
            "focus_dimension_identity"
        ] = "dimension:target-special"
        with self.assertRaises(AssertionError):
            self.assertEqual(plan_shape(original), plan_shape(target_branched))

    def test_recursive_target_authority_and_activation_have_failure_controls(self):
        evolve = read(EVOLVE)
        generation = read(EVOLVE_GENERATION)
        tournament = read(TOURNAMENT)
        self.assertEqual([], recursive_target_errors(evolve, generation, tournament))

        controls = {
            "active-revision-authority": generation.replace(
                "remain outside candidate mutation authority",
                "enter candidate mutation authority",
            ),
            "self-target-control": generation.replace(
                "remains non-control and cannot become the active campaign controller or planner",
                "becomes the active campaign controller",
            ),
            "activation": tournament.replace(
                "separate authorized integration before activation",
                "activation inside the campaign",
            ),
        }
        for expected, wrong in controls.items():
            with self.subTest(control=expected):
                candidate_generation = wrong if expected != "activation" else generation
                candidate_tournament = wrong if expected == "activation" else tournament
                self.assertIn(
                    expected,
                    recursive_target_errors(
                        evolve, candidate_generation, candidate_tournament
                    ),
                )


if __name__ == "__main__":
    unittest.main()
