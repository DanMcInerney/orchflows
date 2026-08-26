"""The gate-only route has one decomposition dispatch and no padding.

The production fixture crosses the real generation, claim, packet, result,
status, and ready doors.  The small trace validator is also exercised against
the four false shapes that previously had no focused discrimination record.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402

STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"
RUN = "gate-only"
ROOT_ID = "00-root"
LENSES = "code,library"

ROOT_TICKET = """---
id: 00-root
run: gate-only
status: pending
admission: pending
executor: orch-decompose
pack: orch-code-pack
independence: gate
depends_on: []
write_scope: [scripts/a.py]
mutations: [change:scripts/a.py]
isolation: required
bound: 60m
claimed_by:
claimed_at:
---

## Objective

Close this result through the composite gate without implementation padding.

## Fixed inputs

- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"%s"},"name":"baseline","type":"identity"}
- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"%s"},"name":"code-baseline","type":"identity"}
- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"%s"},"name":"library-baseline","type":"identity"}
- input: {"name":"ordered-lens-bundle","type":"literal","value":[{"evidence":["code-baseline"],"identity":"code"},{"evidence":["library-baseline"],"identity":"library"}]}

## Completion test

- the result is correct | oracle: `true` | oracle_class: deterministic | provenance: pre-existing
- the result is compatible | oracle: `true` | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result; verification; feedback; risks; Context

## Result


## Verification


## Feedback

[]

## Risks

[]

## Context

[]
"""


def _git_repo(parent: Path) -> tuple[Path, str]:
    repo = parent / "repo"
    repo.mkdir()
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "test@example.invalid"],
        ["git", "config", "user.name", "test"],
    ):
        subprocess.run(command, cwd=repo, check=True)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=repo, check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    return repo, head


@contextmanager
def fixture(coverage: str):
    previous_sink = os.environ.get(STATE_HOME_ENV_VAR)
    previous_cwd = tickets_mod._cwd
    previous_store_cwd = tickets_mod._tickets_store_module._cwd
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)
        sink = (base / "state").resolve()
        os.environ[STATE_HOME_ENV_VAR] = str(sink)
        repo, head = _git_repo(base)
        tickets_mod._cwd = lambda: repo.resolve()
        run_dir = sink / "tickets" / RUN
        run_dir.mkdir(parents=True)
        (run_dir / f"{ROOT_ID}.md").write_text(
            ROOT_TICKET % (head, head, head), encoding="utf-8"
        )
        coverage_path = sink / "runs" / RUN / f"{ROOT_ID}.coverage.md"
        coverage_path.parent.mkdir(parents=True)
        coverage_path.write_text(coverage, encoding="utf-8")
        try:
            yield base, run_dir
        finally:
            tickets_mod._cwd = previous_cwd
            tickets_mod._tickets_store_module._cwd = previous_store_cwd
            if previous_sink is None:
                os.environ.pop(STATE_HOME_ENV_VAR, None)
            else:
                os.environ[STATE_HOME_ENV_VAR] = previous_sink


def dispatch(*args) -> dict:
    value = tickets_mod._dispatch([str(arg) for arg in args])
    return json.loads(json.dumps(value, ensure_ascii=False))


def seal() -> str:
    validation = dispatch("draft-validate", RUN, ROOT_ID)
    if "error" in validation:
        raise AssertionError(validation)
    generation = validation["draft_validation"]["cut_generation"]
    sealed = dispatch(
        "seal", RUN, ROOT_ID, "--cut-generation", generation
    )
    if "error" in sealed:
        raise AssertionError(sealed)
    return generation


def frontmatter_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("---", 2)[1]


def validate_gate_only_trace(trace: dict) -> None:
    """Reject every way a nominal zero-unit route can cease to be one."""

    if trace["coverage"] != [(1, "gate"), (2, "gate")]:
        raise AssertionError("every root criterion must be covered once by gate")
    if trace["implementation_members"]:
        raise AssertionError("a gate-only cut contains no .NN padding member")
    if trace["root_packet_count"] != 1:
        raise AssertionError("the decomposition root is dispatched exactly once")
    if trace["reviewer"] == trace["verifier"]:
        raise AssertionError("terminal verification must use a fresh identity")
    if trace["ready_after_root"] != [f"{ROOT_ID}.gate.critique.bundle"]:
        raise AssertionError("frontier must not redispatch the completed root")


class GateOnlyLifecycleTest(unittest.TestCase):
    COVERAGE = "| criterion | owner |\n| --- | --- |\n| 1 | gate |\n| 2 | gate |\n"

    def test_seal_claim_packet_gate_verify_and_no_redispatch(self):
        with fixture(self.COVERAGE) as (base, run_dir):
            first_generation = seal()

            self.assertEqual(
                [ROOT_ID],
                [item["id"] for item in dispatch("ready", "--run", RUN)["ready"]],
            )
            self.assertNotIn(
                "error", dispatch("claim", RUN, ROOT_ID, "--by", "planner")
            )
            root_packet = dispatch(
                "packet", RUN, ROOT_ID, "--reply-to", "outer", "--by", "planner"
            )["packet"]
            self.assertEqual("orch-decompose", root_packet["executor"])
            redispatch = dispatch(
                "packet", RUN, ROOT_ID, "--reply-to", "outer", "--by", "planner"
            )
            self.assertIn("already emitted for this claim", redispatch["error"])

            gate = dispatch(
                "gate", RUN, ROOT_ID, "--ordered-lens-bundle", LENSES,
                "--write-scope", "scripts/a.py",
            )
            self.assertNotIn("error", gate, gate)
            self.assertEqual(
                [f"{ROOT_ID}.gate.critique.bundle", f"{ROOT_ID}.gate.verify"],
                gate["gate"]["ids"],
            )
            second_generation = seal()
            self.assertNotEqual(first_generation, second_generation)

            self.assertNotIn(
                "error",
                dispatch("result", RUN, ROOT_ID, "--section", "Result",
                         "--text", "gate-only decomposition emitted", "--append"),
            )
            self.assertNotIn(
                "error",
                dispatch("result", RUN, ROOT_ID, "--section", "Context",
                         "--text", "- state: sealed composite family", "--append"),
            )
            self.assertNotIn(
                "error", dispatch("set-status", RUN, ROOT_ID, "complete")
            )

            ready_after_root = [
                item["id"] for item in dispatch("ready", "--run", RUN)["ready"]
            ]
            closer = f"{ROOT_ID}.gate.critique.bundle"
            verifier = f"{ROOT_ID}.gate.verify"
            self.assertNotIn(
                "error", dispatch("claim", RUN, closer, "--by", "bundle-reviewer")
            )
            review_packet = dispatch(
                "packet", RUN, closer, "--reply-to", "outer",
                "--by", "bundle-reviewer",
            )["packet"]
            self.assertEqual("bundle-reviewer", review_packet["assigned_name"])
            closer_frontmatter = frontmatter_text(run_dir / f"{closer}.md")
            self.assertIn("sequence: [orch-critique, orch-repair]", closer_frontmatter)

            for section, text in (
                ("Result", "code and library reviewed; one repair pass completed"),
                ("Context", "- state: final-review-result is the repaired identity"),
            ):
                self.assertNotIn(
                    "error",
                    dispatch("result", RUN, closer, "--section", section,
                             "--text", text, "--append"),
                )
            self.assertNotIn(
                "error", dispatch("set-status", RUN, closer, "complete")
            )
            self.assertEqual(
                [verifier],
                [item["id"] for item in dispatch("ready", "--run", RUN)["ready"]],
            )
            self.assertNotIn(
                "error", dispatch("claim", RUN, verifier, "--by", "fresh-verifier")
            )
            verify_packet = dispatch(
                "packet", RUN, verifier, "--reply-to", "outer",
                "--by", "fresh-verifier",
            )["packet"]
            self.assertEqual("orch-verify", verify_packet["executor"])

            trace = {
                "coverage": [(1, "gate"), (2, "gate")],
                "implementation_members": [
                    path.stem for path in run_dir.glob(f"{ROOT_ID}.[0-9][0-9].md")
                ],
                "root_packet_count": 1 + int("packet" in redispatch),
                "reviewer": review_packet["assigned_name"],
                "verifier": verify_packet["assigned_name"],
                "ready_after_root": ready_after_root,
            }
            validate_gate_only_trace(trace)

    def test_controlled_wrong_variants_are_discriminated(self):
        with fixture("") as (_base, run_dir):
            seal()
            refused = dispatch(
                "gate", RUN, ROOT_ID, "--ordered-lens-bundle", LENSES,
                "--write-scope", "scripts/a.py",
            )
            self.assertIn("coverage map", refused["error"])
            self.assertEqual([f"{ROOT_ID}.md"], [path.name for path in run_dir.glob("*.md")])

        valid = {
            "coverage": [(1, "gate"), (2, "gate")],
            "implementation_members": [],
            "root_packet_count": 1,
            "reviewer": "bundle-reviewer",
            "verifier": "fresh-verifier",
            "ready_after_root": [f"{ROOT_ID}.gate.critique.bundle"],
        }
        mutants = []
        padding = copy.deepcopy(valid)
        padding["implementation_members"] = [f"{ROOT_ID}.01"]
        mutants.append(padding)
        redispatch = copy.deepcopy(valid)
        redispatch["root_packet_count"] = 2
        mutants.append(redispatch)
        reused = copy.deepcopy(valid)
        reused["verifier"] = reused["reviewer"]
        mutants.append(reused)
        for mutant in mutants:
            with self.subTest(mutant=mutant), self.assertRaises(AssertionError):
                validate_gate_only_trace(mutant)


if __name__ == "__main__":
    unittest.main()
