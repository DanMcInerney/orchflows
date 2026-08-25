"""A member's admission version is its root's, and divergence is refused.

The class this module closes: every door computed a ticket's version from
the ticket's own bytes, and the bytes were whatever the door wrote. A door
that wrote v1 bytes under a v2 root produced a member every grader read
self-consistently down the v1 path -- the recorded instance was the gate's
stubs, clean at emission and one `ready` refuse each -- and the response
had been a per-door stopgap in front of one builder. The law now lives in
the one grade (`tickets_context.graded_admission`): `version-root-divergence`
names a member disagreeing with the root of the run it stands in, at every
door that grades or emits, while the flag is still in the caller's hand.

The gate builder is the capability half: it emits at the root's declared
version, so a sealed v2 root grows a drafting gate family that the next
`draft-validate` and `seal` cover at the next generation.

The sink idiom (a temporary ``ORCHFLOWS_STATE_HOME``) is restated here
rather than imported, the convention `tests/test_tickets_gate.py` states,
so this module runs alone under `tools/run_tests.py`'s per-module child.
"""

from __future__ import annotations

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
from scripts import tickets_emission  # noqa: E402
from scripts.tickets_context import graded_admission  # noqa: E402
from scripts.tickets_transitions import declared_version, version_divergence  # noqa: E402

STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"

STUB = """---
id: {tid}
run: testrun
status: pending
admission: v1:pending
cohort: v1:ticket:{tid}
executor: {executor}
{pack}independence: {independence}
depends_on: {depends_on}
write_scope: [scripts/a.py]
mutations: [change:scripts/a.py]
isolation: required
bound: 60m
claimed_by:
claimed_at:
---
"""
BODY = ("\n## Objective\n\nDeliver the one thing this item is for.\n\n"
        "## Fixed inputs\n\n{inputs}\n\n"
        "## Completion test\n\n- it works | oracle: `true` | oracle_class: "
        "deterministic | provenance: authored-here\n\n## Return fields\n\n"
        "status; result; verification; feedback; risks\n\n## Result\n\n"
        "## Verification\n\n## Feedback\n\n[]\n\n## Risks\n\n[]\n")
PLAIN_INPUT = '- input: {"name":"subject","type":"literal","value":"the subject"}'
GIT_INPUT = ('- input: {{"identity":{{"kind":"git-tree","repo":"run-project",'
             '"revision":"{baseline}"}},"name":"baseline","type":"identity"}}')


def stub(tid, baseline=None, executor=None, independence="checker",
         depends_on="[]", v2=False):
    """One admissible ticket, v1 by default, drafting-v2 when asked."""

    git = baseline is not None
    text = (STUB + BODY).format(
        tid=tid, pack="pack: orch-code-pack\n" if git else "",
        executor=executor or ("orch-tdd" if git else "orch-investigate"),
        inputs=GIT_INPUT.format(baseline=baseline) if git else PLAIN_INPUT,
        independence=independence, depends_on=depends_on)
    if v2:
        text = text.replace(f"cohort: v1:ticket:{tid}\n", "").replace(
            "admission: v1:pending", "admission: v2:pending")
    return text


def use_sink(tmp: Path) -> Path:
    sink = (tmp / "state-sink").resolve()
    os.environ[STATE_HOME_ENV_VAR] = str(sink)
    return sink


def run_dir_of(run: str = "testrun") -> Path:
    return Path(os.environ[STATE_HOME_ENV_VAR]) / "tickets" / run


def git_repo(tmp: Path):
    repo = tmp / "repo"
    repo.mkdir(parents=True)
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@example.invalid"],
        ["git", "config", "user.name", "t"],
    ):
        subprocess.run(command, cwd=repo, check=True)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=repo, check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()
    return repo, head


@contextmanager
def workspace():
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        use_sink(tmp)
        repo, head = git_repo(tmp)
        yield tmp, repo, head


def run_cmd(cwd: Path, *args):
    original = tickets_mod._cwd
    tickets_mod._cwd = lambda: Path(cwd).resolve()
    try:
        try:
            payload = tickets_mod._dispatch([str(arg) for arg in args])
        except Exception as error:  # what `main` does with one
            payload = {"error": str(error)}
    finally:
        tickets_mod._cwd = original
    return json.loads(json.dumps(payload, ensure_ascii=False))


def codes(payload) -> set:
    return {finding.get("code") for finding in payload.get("findings") or []}


def frontmatter(path: Path) -> dict:
    data = {}
    for line in path.read_text(encoding="utf-8").split("---")[1].strip().splitlines():
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


def place_root(head, v2=False):
    """A root and one unit of its cut, in the sink, as a door finds them."""

    run_dir = run_dir_of()
    run_dir.mkdir(parents=True, exist_ok=True)
    for tid, extra in (("00-root", {"executor": "orch-decompose",
                                    "independence": "gate"}), ("00-root.01", {})):
        (run_dir / f"{tid}.md").write_text(stub(tid, head, v2=v2, **extra),
                                           encoding="utf-8")
    return run_dir


def seal_run(repo):
    """Validate and seal testrun's root; returns the sealed cut identity."""

    validated = run_cmd(repo, "draft-validate", "testrun", "00-root")
    identity = validated["draft_validation"]["cut_generation"]
    sealed = run_cmd(repo, "seal", "testrun", "00-root",
                     "--cut-generation", identity)
    assert "error" not in sealed, sealed
    return identity


class TheVersionLaw(unittest.TestCase):
    """`version-root-divergence`, stated once and graded everywhere."""

    def grade(self, member_v2: bool, root_v2: bool):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            root = stub("00-root", executor="orch-decompose",
                        independence="gate", v2=root_v2)
            member = stub("00-root.01", v2=member_v2)
            return graded_admission(
                "00-root.01", member,
                {"00-root": root, "00-root.01": member}, "testrun")

    def test_a_v1_member_under_a_v2_root_diverges(self):
        grade = self.grade(member_v2=False, root_v2=True)
        self.assertIn("version-root-divergence", codes(grade))
        self.assertEqual("v1:pending", grade["receipt"],
                         "a divergent member is never granted a receipt")

    def test_a_v2_member_under_a_v1_root_diverges(self):
        self.assertIn("version-root-divergence",
                      codes(self.grade(member_v2=True, root_v2=False)))

    def test_a_member_at_its_root_version_carries_no_divergence(self):
        for both in (False, True):
            with self.subTest(v2=both):
                self.assertNotIn("version-root-divergence",
                                 codes(self.grade(member_v2=both, root_v2=both)))

    def test_the_root_itself_is_exempt(self):
        """The root defines the version; only members can disagree with it."""

        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            root = stub("00-root", executor="orch-decompose",
                        independence="gate", v2=True)
            self.assertNotIn("version-root-divergence", codes(graded_admission(
                "00-root", root, {"00-root": root}, "testrun")))

    def test_the_law_refuses_at_emission_and_is_not_deferred(self):
        """Fail-closed at every door: divergence is the emitter's own."""

        self.assertNotIn("version-root-divergence",
                         tickets_emission.DEFERRED_CODES)
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            root = stub("00-root", executor="orch-decompose",
                        independence="gate", v2=True)
            refusal = tickets_emission.grade_emission(
                "new", "testrun", {"00-root.01": stub("00-root.01")},
                {"00-root": root})
            self.assertIsNotNone(refusal)
            self.assertIn("version-root-divergence", codes(refusal))

    def test_the_pure_halves_answer_alone(self):
        """`declared_version` and `version_divergence` are the stated law."""

        self.assertEqual(2, declared_version({"admission": "v2:pending"}))
        self.assertEqual(2, declared_version({"root_generation": "v2:root:r:1:sha256:" + "0" * 64}))
        self.assertEqual(1, declared_version({"admission": "v1:pending"}))
        self.assertIsNone(version_divergence(
            "r.01", {"admission": "v2:pending"}, {"assignment_seal": "sha256:x"}))
        finding = version_divergence("r.01", {}, {"admission": "v2:pending"})
        self.assertEqual("version-root-divergence", finding["code"])


class TheDoorsRefuseDivergence(unittest.TestCase):
    """The recorded instance's class, closed at a real door: `new --file`
    writing a v1 member into a sealed v2 run refuses before the write."""

    def test_new_file_refuses_a_v1_member_under_a_sealed_v2_root(self):
        with workspace() as (tmp, repo, head):
            run_dir = place_root(head, v2=True)
            seal_run(repo)
            candidate = tmp / "candidate.md"
            candidate.write_text(stub("00-root.02", head), encoding="utf-8")
            payload = run_cmd(repo, "new", "testrun", "00-root.02",
                              "--file", str(candidate))
            self.assertIn("version-root-divergence", codes(payload))
            self.assertFalse((run_dir / "00-root.02.md").exists(),
                             "a refused emission writes nothing")

    def test_new_file_lands_a_drafting_member_that_matches(self):
        with workspace() as (tmp, repo, head):
            run_dir = place_root(head, v2=True)
            seal_run(repo)
            candidate = tmp / "candidate.md"
            candidate.write_text(
                stub("00-root.02", head).replace(
                    "admission: v1:pending",
                    "root_generation: " + frontmatter(
                        run_dir / "00-root.md")["root_generation"]),
                encoding="utf-8")
            payload = run_cmd(repo, "new", "testrun", "00-root.02",
                              "--file", str(candidate))
            self.assertNotIn("error", payload)
            self.assertNotIn("cohort", frontmatter(run_dir / "00-root.02.md"),
                             "a v2 member is frozen by its seal, not a cohort")


class TheGateCompletesUnderV2(unittest.TestCase):
    """The capability half, end to end: gate, then the seal covers it."""

    def test_the_family_is_sealed_at_the_next_generation(self):
        with workspace() as (tmp, repo, head):
            run_dir = place_root(head, v2=True)
            first = seal_run(repo)
            payload = run_cmd(repo, "gate", "testrun", "00-root")
            self.assertNotIn("error", payload)
            self.assertTrue(payload["gate"]["next"][0].startswith("draft-validate"),
                            "a v2 family names its completing doors")
            second = seal_run(repo)
            self.assertNotEqual(first, second,
                                "new members are a new generation, by design")
            for stub_id in payload["gate"]["ids"]:
                data = frontmatter(run_dir / f"{stub_id}.md")
                self.assertEqual(second, data.get("cut_generation"),
                                 f"{stub_id} is covered by the new seal")
                self.assertTrue(data.get("assignment_seal", "").startswith("sha256:"))

    def test_a_v1_root_still_issues_a_v1_gate(self):
        with workspace() as (tmp, repo, head):
            run_dir = place_root(head, v2=False)
            payload = run_cmd(repo, "gate", "testrun", "00-root")
            self.assertNotIn("error", payload)
            self.assertNotIn("next", payload["gate"],
                             "v1 completion is admission's, not the seal's")
            for stub_id in payload["gate"]["ids"]:
                data = frontmatter(run_dir / f"{stub_id}.md")
                self.assertEqual("v1:pending", data.get("admission"))
                self.assertEqual(f"v1:ticket:{stub_id}", data.get("cohort"))
                self.assertNotIn("root_generation", data)


if __name__ == "__main__":
    unittest.main()
