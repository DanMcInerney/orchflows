"""The ownership-region ruling: nothing ships that can only refuse.

`scripts/tickets_regions.py` graded same-artifact parallelism behind a
prover, and `scripts/cutcheck.py` -- the one production caller of family
4 -- never passed one, so the module's admit branch was unreachable from
every shipped path and a flawless region pair could draw exactly one
verdict: `region-proof-failed`. These tests hold the ruling either way.
A bound prover has to carry its admission all the way out through the
production call; an unbound one has to be gone, leaving same-artifact
parallelism to the two orderings that need no proof.
"""

import ast
import unittest
from pathlib import Path

from scripts import cutcheck_graph

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
REGIONS = SCRIPTS / "tickets_regions.py"
PROOF_FAILED = "region-proof-failed"
ARTIFACT = "scripts/shared.py"


def item(owner, pointer, *, scope=(ARTIFACT,), depends_on=(), artifact=ARTIFACT):
    """A sibling declaring one flawless region: the best case a cut can offer.

    Stable selector kind, adapter the code pack binds, owner matching the
    id, and a merge oracle identical to its partner's -- every complaint
    `region_findings` could raise is answered here on purpose, so whatever
    a grading returns is the prover's word and not a shape defect's.
    """

    return {
        "executor": "orch-tdd",
        "pack": "orch-code-pack",
        "depends_on": list(depends_on),
        "write_scope": list(scope),
        "ownership_regions": [
            {
                "artifact": artifact,
                "merge_oracle": "oracle:git:abc",
                "owner": owner,
                "selector": {"kind": "json-pointer", "value": pointer},
            }
        ],
    }


def live_strings(source):
    """Every string literal in ``source`` that is not a docstring.

    A finding code reaches the report as a value, so an emitter has to
    hold it in a live literal. Prose naming a retired code -- the
    docstring saying why it is retired, and what restoring it would
    take -- is history the next reader needs, not machinery.
    """

    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        head = body[0] if body else None
        if isinstance(head, ast.Expr) and isinstance(head.value, ast.Constant):
            docstrings.add(id(head.value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def graded(siblings):
    """Family 4 read the way `scripts/cutcheck.py` issues it: no prover.

    Passing one here is what made the old case module agree with a
    mechanism production never ran, so the omission is the point. The
    tree stays None because a baseline tree only adds the advisory
    shared-test-module class; the reading under test is the collision one.
    """

    return cutcheck_graph._pairwise(siblings, {}, tree=None)


def disjoint_pair():
    return {"left": item("left", "/alpha"), "right": item("right", "/beta")}


class RegionMachineryRulingTest(unittest.TestCase):
    """Bound to a production prover, or gone. There is no third standing."""

    def test_region_machinery_ships_only_with_an_admit_branch_production_reaches(self):
        if REGIONS.exists():
            # Ruled bound: the prover the module ships with must admit this
            # pair through the same call cutcheck makes, with no test-only
            # prover injected. An admit branch only a test can reach is not
            # an admit branch.
            self.assertEqual([], graded(disjoint_pair()))
            return
        # Ruled deleted: no shipped source may still emit the verdict that
        # was the module's only reachable one, nor reach what emitted it.
        emitters, importers = [], []
        for path in sorted(SCRIPTS.glob("*.py")):
            source = path.read_text(encoding="utf-8")
            if any(PROOF_FAILED in value for value in live_strings(source)):
                emitters.append(path.name)
            if "tickets_regions" in source:
                importers.append(path.name)
        self.assertEqual(([], []), (emitters, importers))


class UnprovenParallelismTest(unittest.TestCase):
    """What a cut is told when it asks two owners to share one artifact."""

    def test_same_artifact_parallelism_refuses_in_one_voice_and_orders_or_sole_owns(self):
        findings = graded(disjoint_pair())
        self.assertEqual(1, len(findings))
        left, _, klass, detail = findings[0]
        self.assertEqual(("left", cutcheck_graph.SCOPE_COLLISION), (left, klass))
        # One refusal, in one language. A detail that also reported a proof
        # attempt and a fallback would advertise machinery no shipped path
        # runs -- the false confidence this ruling exists to remove.
        self.assertEqual("with right: %s" % ARTIFACT, detail)

        # And the two orderings that need no proof still clear the family.
        ordered = disjoint_pair()
        ordered["right"]["depends_on"] = ["left"]
        self.assertEqual([], graded(ordered))
        sole = disjoint_pair()
        sole["right"] = item("right", "/beta", scope=["scripts/other.py"], artifact="scripts/other.py")
        self.assertEqual([], graded(sole))


if __name__ == "__main__":
    unittest.main()
