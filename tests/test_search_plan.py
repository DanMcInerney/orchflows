"""Public-seam checks for deterministic search planning."""

from collections import Counter
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


# Case partitions import this public seam by its package-qualified name.
# Top-level discovery must bind that name before loading the partitions.
sys.modules.setdefault("tests.test_search_plan", sys.modules[__name__])


from tests._repo_root import ROOT  # noqa: E402
# Both campaigns are workflow skills: one `SKILL.md` whose prose opens a
# frame and writes the callable calls that used to be stubs. The text graded
# below is that whole body, because the law that was spread across a
# directory of stubs is back in one place.
EVOLVE = ROOT / "example-workflows" / "evolve"
EVOLVE_GENERATION = ROOT / "example-workflows" / "references" / "evolve-generation.md"
TOURNAMENT = ROOT / "example-workflows" / "skill-tournament"
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
# One callable call as the prose writes it: the verb, then the pack it stamps.
CALLABLE_CALL_RE = re.compile(r"\b(do|judge)(?: <run>)? --pack ")


def canonical_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
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
    """One workflow as one string. A workflow is a skill whose prose calls
    callables, so its whole surface is the one body -- there are no stubs
    beside it to concatenate."""
    return read(directory / "SKILL.md")


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


# The restart controls no script can observe -- the controller's, not the
# module's -- each pinned by the term that distinguishes its clause rather than
# by the sentence spelling it (`packs/orch-code-pack/references/craft.md`):
# `before delegation` is the ordering the `in_flight` record must keep (the
# field name itself recurs in the restart clause, so it cannot tell the two
# apart), `redispatch` the verb a restart forbids, `every archive member` what
# the Worklog entry must persist. That the module's own projection carries the
# archive, and that a `pending` response carries no plan, are module behaviour
# and are pinned there instead (`test_partial_settlement_keeps_projection_
# and_complete_archive`, `test_settlement_is_exact_and_atomic`).
RESTART_ANCHORS = (
    ("in-flight-order", "before delegation"),
    ("duplicate-restart-dispatch", "redispatch"),
    ("archive-persistence", "every archive member"),
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


# The two authority controls, by the terms the generation contract carries
# them under: a revision outside `mutation authority`, a self-target candidate
# that stays `non-control`. Each campaign carries the activation fact in its
# Context; it is not a separate authored authority field.
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
    # Each template states it on its own; one carrying the fact never excuses
    # the other.
    if not all(ACTIVATION_ANCHOR in text.lower() for text in (evolve, tournament)):
        errors.append("activation")
    return errors


def architecture_errors(evolve: str, generation: str, tournament: str, leaf: str):
    errors = []
    combined_evolve = evolve + generation
    # Who runs each step is the pack the callable call stamps, read off the
    # call line the prose writes. `judge` twice: eligibility opens the
    # campaign, the final score card closes it; `do` twice: the frozen
    # evaluation, then the per-candidate write. Since P3 the *scorer* was
    # also a candidate standalone skill named `orch-judge` -- unrelated to
    # the callable of that name today -- merged into `orch-check` instead
    # (a score scale in the criteria); `orch-delegate` merged into
    # rules/delegation.md, `orch-worklog` into the `tickets.py` view -- and
    # since P4 `orch-panel` too, judging being N blind verify lanes plus the
    # loop body's reduce. None of those three demoted names may reappear.
    calls = Counter(CALLABLE_CALL_RE.findall(evolve))
    required = Counter({"do": 2, "judge": 2})
    if calls != required:
        errors.append("evolve-call-graph")
    admission = evolve.partition("Admit the incumbent")[2].partition("Generations,")[0]
    generations = evolve.partition("Generations,")[2].partition("Close the campaign")[0]
    if "judge --pack" not in admission:
        errors.append("eligibility-unit")
    # The generations reuse the admission verdicts rather than re-taking
    # them: each candidate is handed that judge's findings unaltered.
    if "eligibility findings verbatim" not in generations:
        errors.append("generation-verify-binding")
    # Nothing follows the close but the Never and Return paragraphs: a
    # further stage after it is the closing wrapper the campaign refuses.
    if "**" in evolve.partition("\nReturn:")[2] or "**" in evolve.partition(
        "Close the campaign**"
    )[2].partition("\nNever:")[0]:
        errors.append("closing-wrapper")
    for demoted in ("orch-panel", "orch-delegate", "orch-worklog"):
        if demoted in combined_evolve:
            errors.append("judge-owner")
            break
    # A workflow binds its executor in the callable call's `--pack`; a
    # backticked callable name in the prose is the second grammar P4 removed.
    if set(CALL_EDGE_RE.findall(combined_evolve)):
        errors.append("evolve-call-edge")

    tournament_calls = set(CALL_EDGE_RE.findall(tournament))
    if tournament_calls:
        errors.append("tournament-internal-call")
    if "writer=orch-do" not in normalized(tournament):
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


from tests.test_search_plan_cases.protocol import TestArchitecture, TestCanonicalAdvance
from tests.test_search_plan_cases.archive import TestMergeLineage, TestParetoReflection
from tests.test_search_plan_cases.projection import TestBoundedResume
from tests.test_search_plan_cases.generation import TestVisibilityAndSelfTarget


if __name__ == "__main__":
    unittest.main()
