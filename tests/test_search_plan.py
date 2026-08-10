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


if __name__ == "__main__":
    unittest.main()
