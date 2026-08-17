"""Public-seam checks for deterministic search planning."""

from pathlib import Path
from collections import Counter
import copy
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
# Since P4 both campaigns are ticket-set templates: a `template.md`
# manifest plus the stubs `tickets.py instantiate` writes into a run. The
# text graded below is the whole directory, stubs first, because the law
# that used to be one composition body is now spread across the stubs
# that carry it.
EVOLVE = ROOT / "compositions" / "evolve"
EVOLVE_GENERATION = ROOT / "compositions" / "references" / "evolve-generation.md"
TOURNAMENT = ROOT / "compositions" / "skill-tournament"
# Since P4-3 the planner is a script and nothing else: the `orch-search-plan`
# skill wrapped one command and one protocol in a dispatchable contract no
# caller used as one — the campaign always named the bare filename. The
# script is the leaf surface now, and its own docstring points at the
# protocol under `docs/`, where a document the installer ships reads it —
# `scripts/` is not a canonical directory, so a protocol beside the script
# reached no installed tree.
SEARCH_SCRIPT = ROOT / "scripts" / "search_plan.py"
SEARCH_PROTOCOL = ROOT / "docs" / "search-plan-protocol.md"

CALL_EDGE_RE = re.compile(r"`(orch-[a-z0-9-]+)`")
EXECUTOR_RE = re.compile(r"^executor:\s*(\S+)", re.MULTILINE)


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
            "evaluation_identity": "evaluation:judged-fixture",
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
        "evaluation_identity": "evaluation:judged-fixture",
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
        "evaluation_identity": slot["evaluation_identity"],
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
        "evaluation_identity": slot["evaluation_identity"],
        "result_identity": f"result:{suffix}",
        "evidence_identity": f"evidence:{suffix}",
        "eligibility_status": "FAIL",
        "eligibility_verdict_identity": f"verdict:{suffix}",
        "disposition": "failed-required-check",
    }


def no_candidate_outcome(slot, suffix):
    return {
        "kind": "no_candidate",
        "outcome_identity": f"outcome:{suffix}",
        "slot_identity": slot["identity"],
        "cost": {unit: 0 for unit in slot["reservation"]},
        "disposition": "no-candidate",
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


def spawn_advance(payload=None, raw=None, cwd=None):
    """A real `python search_plan.py advance`.

    Kept for the two claims only a process can make: that the command
    writes nothing into the directory it runs from, and that input deep
    enough to exhaust the parser is refused rather than crashing the
    interpreter the rest of the suite is running in.
    """
    data = raw if raw is not None else canonical_bytes(payload)
    return subprocess.run(
        [sys.executable, str(SEARCH_SCRIPT), "advance"],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        check=False,
    )


class _Advance:
    """The three fields of a CompletedProcess the assertions read."""

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _ByteStream:
    """A stdin/stdout stand-in exposing the `.buffer` the script uses."""

    def __init__(self, data=b""):
        self.buffer = io.BytesIO(data)


def run_advance(payload=None, raw=None, argv=("advance",)):
    """`search_plan.py advance` in process, one call per assertion.

    `main` reads `sys.stdin.buffer`, writes `sys.stdout.buffer` and
    returns the exit status, so swapping the three streams is the whole
    command minus an interpreter start. spawn_advance keeps the process
    boundary itself covered.
    """
    data = raw if raw is not None else canonical_bytes(payload)
    module = load_search_module()
    stdin, stdout, stderr = _ByteStream(data), _ByteStream(), io.StringIO()
    saved = (sys.stdin, sys.stdout, sys.stderr)
    sys.stdin, sys.stdout, sys.stderr = stdin, stdout, stderr
    try:
        code = module.main(list(argv))
    finally:
        sys.stdin, sys.stdout, sys.stderr = saved
    return _Advance(code, stdout.buffer.getvalue(), stderr.getvalue().encode("utf-8"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def template_text(directory: Path) -> str:
    """One template as one string: `00-...` through the terminal stub,
    then the manifest."""
    stubs = sorted(p for p in directory.glob("*.md") if p.name != "template.md")
    return "".join(read(path) for path in stubs + [directory / "template.md"])


_MODULE = []


def load_search_module():
    """The script as a module, loaded once. It holds no mutable state
    between calls -- `_advance` is a pure function of its request -- so
    one instance serves every test."""
    if not _MODULE:
        spec = importlib.util.spec_from_file_location(
            "search_plan_test_module", SEARCH_SCRIPT
        )
        if spec is None or spec.loader is None:
            raise AssertionError("search-plan module could not be loaded")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _MODULE.append(module)
    return _MODULE[0]


def rehash_open_plan_slot(projection, index):
    plan = projection["last_plan"]
    slot = plan["slots"][index]
    old_slot_identity = slot["identity"]
    slot["identity"] = tagged_identity(
        "search-slot/v1",
        {key: value for key, value in slot.items() if key != "identity"},
    )
    projection["seen_slot_identities"] = [
        slot["identity"] if identity == old_slot_identity else identity
        for identity in projection["seen_slot_identities"]
    ]
    plan["identity"] = tagged_identity(
        "search-plan/v1",
        {key: value for key, value in plan.items() if key != "identity"},
    )
    projection["identity"] = tagged_identity(
        "search-projection/v1",
        {key: value for key, value in projection.items() if key != "identity"},
    )


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


# The two restart controls no script can observe, each pinned by the term the
# contract carries it under rather than by the sentence spelling it
# (`packs/orch-code-pack/references/craft.md`): `in_flight` is the field a
# restart reconciles, `redispatch` the verb it forbids. The other two controls
# the contract states are module behaviour and are pinned there instead --
# the archive survives in the emitted projection, and a `pending` response
# carries no plan.
RESTART_ANCHORS = (
    ("in-flight-order", "`in_flight`"),
    ("duplicate-restart-dispatch", "redispatch"),
)


def worklog_restart_errors(generation: str):
    contract = normalized(generation)
    return [name for name, anchor in RESTART_ANCHORS if anchor not in contract]


def plan_shape(response):
    return [
        {
            key: copy.deepcopy(value)
            for key, value in slot.items()
            if key not in {"identity", "target_owner_identity"}
        }
        for slot in response["plan"]["slots"]
    ]


def excluded_actions(text: str):
    """Every `excluded_actions` entry of every stub in one template text,
    lowercased. A clause's owner is the field it sits in, so what a check
    asserts is membership of that field."""
    return [
        line.strip()[2:].strip().lower()
        for block in re.findall(
            r"^excluded_actions:\n((?:  - .*\n)+)", text, re.MULTILINE
        )
        for line in block.splitlines()
    ]


# The two authority controls, by the terms the generation contract carries
# them under: a revision outside `mutation authority`, a self-target candidate
# that stays `non-control`. Activation is a clause of each campaign template's
# `excluded_actions` field, so the check reads the field.
RECURSION_ANCHORS = (
    ("active-revision-authority", "mutation authority"),
    ("self-target-control", "non-control"),
)
ACTIVATION_ANCHOR = "activat"


def recursive_target_errors(evolve: str, generation: str, tournament: str):
    generation_contract = normalized(generation)
    errors = [
        name for name, anchor in RECURSION_ANCHORS if anchor not in generation_contract
    ]
    # Each template excludes it on its own; one carrying the clause never
    # excuses the other.
    if not all(
        any(ACTIVATION_ANCHOR in action for action in excluded_actions(text))
        for text in (evolve, tournament)
    ):
        errors.append("activation")
    return errors


def architecture_errors(evolve: str, generation: str, tournament: str, leaf: str):
    errors = []
    combined_evolve = evolve + generation
    # Who runs each step is the stubs' `executor`, not a backticked name in
    # prose. `orch-verify` twice: eligibility opens the campaign, the final
    # score card closes it. Since P3 it is also the one scorer -- `orch-judge`
    # merged into it (a score scale in the criteria), `orch-delegate` into
    # rules/delegation.md, `orch-worklog` into the `tickets.py` view -- and
    # since P4 `orch-panel` too, judging being N blind verify lanes plus the
    # loop body's reduce. None of the four may reappear.
    executors = Counter(EXECUTOR_RE.findall(evolve))
    required = Counter({
        "orch-eval-design": 1,
        "orch-loop": 1,
        "orch-verify": 2,
    })
    if executors != required:
        errors.append("evolve-call-graph")
    eligibility = evolve[
        evolve.index("id: 01-eligibility") : evolve.index("id: 02-campaign")
    ]
    campaign = evolve[evolve.index("id: 02-campaign") : evolve.index("id: 03-result")]
    if "executor: orch-verify" not in eligibility:
        errors.append("eligibility-unit")
    # The campaign reuses the eligibility verdicts rather than re-taking
    # them: it cites that stub's Result as its own fixed input.
    if "01-eligibility's `## Result`" not in campaign:
        errors.append("generation-verify-binding")
    if re.search(r"^id:\s*04-", evolve, re.MULTILINE):
        errors.append("closing-wrapper")
    for demoted in ("orch-panel", "orch-judge", "orch-delegate", "orch-worklog"):
        if demoted in combined_evolve:
            errors.append("judge-owner")
            break
    # A template binds its executors in frontmatter; a backticked call edge
    # in the prose is the second grammar P4 removed.
    if set(CALL_EDGE_RE.findall(combined_evolve)):
        errors.append("evolve-call-edge")

    tournament_calls = set(CALL_EDGE_RE.findall(tournament))
    if tournament_calls:
        errors.append("tournament-internal-call")
    if "writer=orch-build" not in normalized(tournament):
        errors.append("tournament-writer-binding")
    # The campaign's promotion judgment is evolve's, and the tournament may
    # not restate it. Since 2026-08-16 (thread T27) the tournament does name
    # the frozen `promotion rule` it freezes in `policy` and hands down as
    # part of the evaluation -- evolve reads a margin no producer wrote
    # otherwise -- so that phrase is licensed and every other use of the word
    # is the judgment restated here.
    if re.search(r"promotion(?! rule)", normalized(tournament)):
        errors.append("tournament-promotion")

    # The leaf is `scripts/search_plan.py` itself. A script is the ladder's
    # floor: it dispatches nothing, so any backticked `orch-*` in it is a
    # call edge that cannot exist.
    leaf_calls = set(CALL_EDGE_RE.findall(leaf))
    if leaf_calls:
        errors.append("leaf-call")
    return errors


class TestArchitecture(unittest.TestCase):
    def test_thin_evolve_owns_one_campaign_call_graph(self):
        for path in (EVOLVE, TOURNAMENT):
            self.assertTrue(path.is_dir(), f"missing campaign template: {path}")
            self.assertTrue((path / "template.md").is_file(), f"{path} has no manifest")
        for path in (EVOLVE_GENERATION, SEARCH_PROTOCOL, SEARCH_SCRIPT):
            self.assertTrue(path.is_file(), f"missing search-planning surface: {path}")
        self.assertFalse(
            (ROOT / "skills" / "utilities" / "orch-search-plan").exists(),
            "the search planner is a script, not a skill wrapping one command",
        )

        evolve = template_text(EVOLVE)
        generation = read(EVOLVE_GENERATION)
        tournament = template_text(TOURNAMENT)
        leaf = read(SEARCH_SCRIPT)
        self.assertEqual([], architecture_errors(evolve, generation, tournament, leaf))
        # One command, stated once, at the path the script now lives at.
        command = "python scripts/search_plan.py advance"
        self.assertEqual(1, leaf.count(command))
        self.assertIn("docs/search-plan-protocol.md", leaf)
        self.assertNotIn("operation registry", normalized(leaf))

    def test_the_campaign_stub_names_the_planner_it_selects_through(self):
        """The one caller of the search planner is the loop body, and it
        names the script by bare filename -- the path moves when the script
        does, and a template that named the path would be stale the day it
        moved."""
        campaign = read(EVOLVE / "02-campaign.md")
        self.assertIn("search_plan.py advance", campaign)
        self.assertEqual("orch-loop", EXECUTOR_RE.search(campaign).group(1))

    def test_planner_is_evaluation_mode_agnostic(self):
        protocol = read(SEARCH_PROTOCOL)
        script = read(SEARCH_SCRIPT)
        self.assertIn("evaluation_identity", protocol)
        self.assertIn('"evaluation_identity"', script)
        self.assertNotIn("benchmark_revision", protocol)
        self.assertNotIn('"benchmark_revision"', script)

    def test_known_wrong_ownership_fixtures_are_rejected(self):
        evolve = template_text(EVOLVE)
        generation = read(EVOLVE_GENERATION)
        tournament = template_text(TOURNAMENT)
        leaf = read(SEARCH_SCRIPT)

        closing = evolve + "\n---\nid: 04-closing\nexecutor: orch-verify\n---\n"
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
        readmitted_panel = generation + "\nScore the set through `orch-panel`.\n"
        self.assertIn(
            "judge-owner",
            architecture_errors(evolve, readmitted_panel, tournament, leaf),
        )

        judged_here = tournament + "\nThe promotion decision is taken here.\n"
        self.assertIn(
            "tournament-promotion",
            architecture_errors(evolve, generation, judged_here, leaf),
        )

        unresolved = evolve.replace("executor: orch-verify", "executor: orch-critique", 1)
        self.assertIn(
            "eligibility-unit",
            architecture_errors(unresolved, generation, tournament, leaf),
        )


class TestCanonicalAdvance(unittest.TestCase):
    def assert_rejected(self, payload=None, raw=None):
        result = run_advance(payload=payload, raw=raw)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertTrue(result.stderr.startswith(b"search-plan: "))
        self.assertLessEqual(len(result.stderr), 512)

    def test_advance_is_the_only_subcommand_and_a_second_word_is_not_ignored(self):
        """`main`'s argv guard, which every other test walks straight past.

        Each argv below is handed a request the command would answer at
        exit 0, so the refusal is the guard's and not the request's: an
        argv this script does not define must not be read as `advance`
        with extra words, and a caller that passed nothing must not have
        its stdin consumed by a default.
        """

        request = generation_zero_request()
        for argv in ([], ["plan"], ["advance", "--force"], ["--help"], ["ADVANCE"]):
            with self.subTest(argv=argv):
                result = run_advance(payload=request, argv=argv)
                self.assertEqual(2, result.returncode)
                self.assertEqual(b"", result.stdout)
                self.assertEqual(b"search-plan: expected advance\n", result.stderr)

    def test_generation_zero_is_byte_stable_and_read_only(self):
        request = generation_zero_request()
        with tempfile.TemporaryDirectory() as directory:
            first = spawn_advance(request, cwd=directory)
            second = spawn_advance(reverse_object_keys(request), cwd=directory)
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

    def test_opaque_evaluation_identity_has_no_mode_branch(self):
        judged = generation_zero_request()
        benchmark = copy.deepcopy(judged)
        benchmark["policy"]["evaluation_identity"] = "evaluation:benchmark-fixture"
        benchmark["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in benchmark["policy"].items()
                if key != "identity"
            },
        )
        benchmark["settled"]["outcomes"][0]["evaluation_identity"] = (
            "evaluation:benchmark-fixture"
        )

        judged_result = run_advance(judged)
        benchmark_result = run_advance(benchmark)
        self.assertEqual(0, judged_result.returncode, judged_result.stderr.decode())
        self.assertEqual(0, benchmark_result.returncode, benchmark_result.stderr.decode())
        judged_response = json.loads(judged_result.stdout)
        benchmark_response = json.loads(benchmark_result.stdout)
        self.assertEqual(judged_response["status"], benchmark_response["status"])
        self.assertEqual(
            [slot["kind"] for slot in judged_response["plan"]["slots"]],
            [slot["kind"] for slot in benchmark_response["plan"]["slots"]],
        )

        drift = copy.deepcopy(judged)
        drift["settled"]["outcomes"][0]["evaluation_identity"] = (
            "evaluation:benchmark-fixture"
        )
        self.assert_rejected(drift)

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

    def test_deep_json_recursion_is_invalid_input(self):
        # Spawned: 5000 levels is deep enough to exhaust the parser, and the
        # refusal is only a refusal if it costs the caller its own stack.
        raw = b'{"policy":' + b"[" * 5_000 + b"0" + b"]" * 5_000 + b"}"
        result = spawn_advance(raw=raw)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)
        self.assertTrue(result.stderr.startswith(b"search-plan: "))
        self.assertLessEqual(len(result.stderr), 512)

    def test_public_request_identity_and_decimal_caps_are_exact(self):
        module = load_search_module()
        # The protocol states the three caps the module enforces, and the
        # numbers are read off the module rather than repeated here: a cap
        # changed in one place and not the other is what this half catches.
        protocol = normalized(read(SEARCH_PROTOCOL))
        for cap in (
            module.MAX_INPUT_BYTES,
            module.MAX_IDENTITY_CHARS,
            module.MAX_DECIMAL_CHARS,
        ):
            self.assertIn(f"at most {cap:,}", protocol)
            # The number is the claim: a protocol stating a neighbouring cap
            # would satisfy a check that only looked for a digit run.
            self.assertNotIn(f"at most {cap + 1:,}", protocol)

        at_request_cap = b"0" + b" " * (module.MAX_INPUT_BYTES - 1)
        self.assertEqual(0, module._load_request(at_request_cap))
        with self.assertRaises(module.ProtocolError):
            module._load_request(at_request_cap + b" ")

        identity_at_cap = generation_zero_request()
        identity_at_cap["policy"]["planner_revision"] = "x" * 256
        identity_at_cap["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in identity_at_cap["policy"].items()
                if key != "identity"
            },
        )
        self.assertEqual(0, run_advance(identity_at_cap).returncode)
        identity_over_cap = copy.deepcopy(identity_at_cap)
        identity_over_cap["policy"]["planner_revision"] += "x"
        identity_over_cap["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in identity_over_cap["policy"].items()
                if key != "identity"
            },
        )
        self.assert_rejected(identity_over_cap)

        decimal_at_cap = generation_zero_request()
        decimal_at_cap["policy"]["dimensions"][0]["resolution"] = "1" + "0" * 127
        decimal_at_cap["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in decimal_at_cap["policy"].items()
                if key != "identity"
            },
        )
        self.assertEqual(0, run_advance(decimal_at_cap).returncode)
        decimal_over_cap = copy.deepcopy(decimal_at_cap)
        decimal_over_cap["policy"]["dimensions"][0]["resolution"] += "0"
        decimal_over_cap["policy"]["identity"] = tagged_identity(
            "search-policy/v1",
            {
                key: value
                for key, value in decimal_over_cap["policy"].items()
                if key != "identity"
            },
        )
        self.assert_rejected(decimal_over_cap)

    def test_rehashed_open_plans_must_be_current_lawful_policy_prefixes(self):
        request = two_dimension_request()
        initial_result = run_advance(request)
        self.assertEqual(0, initial_result.returncode, initial_result.stderr.decode())
        initial = json.loads(initial_result.stdout)

        cases = []
        dangling = copy.deepcopy(initial["projection"])
        dangling["last_plan"]["slots"][0]["parent_identities"] = ["candidate:missing"]
        rehash_open_plan_slot(dangling, 0)
        cases.append(dangling)

        reservation_drift = copy.deepcopy(initial["projection"])
        reservation_drift["last_plan"]["slots"][0]["reservation"]["runs"] = 0
        rehash_open_plan_slot(reservation_drift, 0)
        cases.append(reservation_drift)

        proposal_drift = copy.deepcopy(initial["projection"])
        proposal_drift["last_plan"]["slots"][0][
            "focus_dimension_identity"
        ] = "dimension:cost"
        rehash_open_plan_slot(proposal_drift, 0)
        cases.append(proposal_drift)

        unseen = copy.deepcopy(initial["projection"])
        unseen["seen_slot_identities"].remove(
            unseen["last_plan"]["slots"][0]["identity"]
        )
        unseen["identity"] = tagged_identity(
            "search-projection/v1",
            {key: value for key, value in unseen.items() if key != "identity"},
        )
        cases.append(unseen)

        for projection in cases:
            with self.subTest(case=cases.index(projection)):
                replay = settled_request(
                    request["policy"],
                    {"projection": projection},
                    [],
                    "candidate:origin",
                )
                self.assert_rejected(replay)

    def test_emitted_projection_replays_as_valid_pending_state(self):
        request = two_dimension_request()
        first = run_advance(request)
        self.assertEqual(0, first.returncode, first.stderr.decode())
        response = json.loads(first.stdout)
        replay = settled_request(
            request["policy"], response, [], "candidate:origin"
        )
        pending = run_advance(replay)
        self.assertEqual(0, pending.returncode, pending.stderr.decode())
        self.assertEqual("pending", json.loads(pending.stdout)["status"])


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

    def test_feedback_changes_the_reflection_packet_identity(self):
        request, outcomes = self.settled_fixture()
        original = self.run_ok(request)
        changed = copy.deepcopy(request)
        dominated = next(
            item
            for item in changed["settled"]["outcomes"]
            if item.get("candidate_identity") == "candidate:dominated"
        )
        original_slot = original["plan"]["slots"][0]
        focused_feedback = next(
            item
            for item in dominated["feedback"]
            if item["dimension_identity"]
            == original_slot["focus_dimension_identity"]
        )
        focused_feedback["reference_identity"] += "-v2"
        revised = self.run_ok(changed)
        revised_slot = revised["plan"]["slots"][0]
        self.assertNotEqual(original_slot["feedback"], revised_slot["feedback"])
        self.assertNotEqual(original_slot["identity"], revised_slot["identity"])
        self.assertEqual(
            revised_slot["identity"],
            tagged_identity(
                "search-slot/v1",
                {
                    key: value
                    for key, value in revised_slot.items()
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

    def test_width_one_focus_rotates_across_generations(self):
        initial_request = two_dimension_request(width=1, merge_slots=0)
        generation_one = self.run_ok(initial_request)
        first_slot = generation_one["plan"]["slots"][0]
        generation_two = self.run_ok(
            settled_request(
                initial_request["policy"],
                generation_one,
                [admitted_outcome(first_slot, "candidate:best", "0.8", "0.2")],
                "candidate:origin",
            )
        )
        second_slot = generation_two["plan"]["slots"][0]
        generation_three = self.run_ok(
            settled_request(
                initial_request["policy"],
                generation_two,
                [no_candidate_outcome(second_slot, "generation-two")],
                "candidate:origin",
            )
        )
        self.assertEqual(
            ["dimension:quality", "dimension:cost", "dimension:quality"],
            [
                first_slot["focus_dimension_identity"],
                second_slot["focus_dimension_identity"],
                generation_three["plan"]["slots"][0]["focus_dimension_identity"],
            ],
        )


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
            "candidate:dominated",
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

        changed_incumbent = copy.deepcopy(partial)
        changed_incumbent["settled"][
            "preferred_incumbent_identity"
        ] = "candidate:partial"
        self.assert_rejected(changed_incumbent)

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

        invalid_bound = copy.deepcopy(partial)
        invalid_bound["remaining_bound"] = {"unexpected": -1}
        result = run_advance(invalid_bound)
        self.assertEqual(2, result.returncode)
        self.assertEqual(b"", result.stdout)

    def test_first_no_fit_does_not_materialize_the_proposal_suffix(self):
        initial_request = two_dimension_request(width=5, merge_slots=0)
        initial = self.run_ok(initial_request)
        outcomes = [
            no_candidate_outcome(slot, f"generation-one-{index}")
            for index, slot in enumerate(initial["plan"]["slots"])
        ]
        request = settled_request(
            initial_request["policy"],
            initial,
            outcomes,
            "candidate:origin",
            remaining=0,
        )
        module = load_search_module()
        original_identified = module._identified
        produced_slots = []

        def tracking_identified(tag, payload):
            if tag == "search-slot/v1" and payload["generation"] == 2:
                produced_slots.append(payload["ordinal"])
            return original_identified(tag, payload)

        # The module instance is shared with every other test, so the patch
        # is undone whatever this one does.
        self.addCleanup(setattr, module, "_identified", original_identified)
        module._identified = tracking_identified
        response = module._advance(copy.deepcopy(request))
        self.assertEqual("no_fit", response["status"])
        self.assertEqual([0], produced_slots)

    def test_worklog_launch_and_restart_contract_has_failure_controls(self):
        """The restart controls a script can observe are pinned as behaviour:
        `test_partial_settlement_keeps_projection_and_complete_archive` is
        archive-persistence, and the `plan is None` it asserts beside the
        `pending` status is what "launches nothing" means to a caller. The
        two left here are the controller's own -- no script sees a live slot
        -- so each is pinned by the term the contract carries it under."""
        generation = read(EVOLVE_GENERATION)
        self.assertEqual([], worklog_restart_errors(generation))

        for control, anchor in RESTART_ANCHORS:
            with self.subTest(control=control):
                self.assertIn(
                    control, worklog_restart_errors(generation.replace(anchor, ""))
                )


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

    def test_recursive_target_authority_and_activation_have_failure_controls(self):
        evolve = template_text(EVOLVE)
        generation = read(EVOLVE_GENERATION)
        tournament = template_text(TOURNAMENT)
        self.assertEqual([], recursive_target_errors(evolve, generation, tournament))

        for control, anchor in RECURSION_ANCHORS:
            with self.subTest(control=control):
                self.assertIn(
                    control,
                    recursive_target_errors(
                        evolve, generation.replace(anchor, ""), tournament
                    ),
                )
        # Each template's own clause, dropped one at a time.
        for name, evolve_text, tournament_text in (
            ("evolve", evolve.replace(ACTIVATION_ANCHOR, ""), tournament),
            ("tournament", evolve, tournament.replace(ACTIVATION_ANCHOR, "")),
        ):
            with self.subTest(control="activation", template=name):
                self.assertIn(
                    "activation",
                    recursive_target_errors(evolve_text, generation, tournament_text),
                )


if __name__ == "__main__":
    unittest.main()
