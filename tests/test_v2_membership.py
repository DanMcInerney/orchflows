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
    original_store = tickets_mod._tickets_store_module._cwd
    tickets_mod._cwd = lambda: Path(cwd).resolve()
    try:
        try:
            payload = tickets_mod._dispatch([str(arg) for arg in args])
        except Exception as error:  # what `main` does with one
            payload = {"error": str(error)}
    finally:
        tickets_mod._cwd = original
        tickets_mod._tickets_store_module._cwd = original_store
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

    def test_same_planner_full_route_terminalizes_root_before_frontier(self):
        """The dispatch-only planner continuation crosses every real door.

        The sequence is deliberately an action trace rather than ticket
        authority: the created root is sealed, admitted to one planner,
        packeted to that same planner for decomposition, resealed with its
        cut, and terminalized by the outer join before frontier sees work.
        """

        with workspace() as (tmp, repo, head):
            run_dir = run_dir_of()
            run_dir.mkdir(parents=True, exist_ok=True)
            root_path = run_dir / "00-root.md"
            root_path.write_text(
                stub("00-root", head, executor="orch-decompose",
                     independence="gate", v2=True),
                encoding="utf-8",
            )
            first_generation = seal_run(repo)

            ready = run_cmd(repo, "ready", "--run", "testrun")
            self.assertEqual(["00-root"], [item["id"] for item in ready["ready"]])
            claim = run_cmd(
                repo, "claim", "testrun", "00-root", "--by", "planner-lane"
            )
            self.assertNotIn("error", claim)
            root_packet = run_cmd(
                repo, "packet", "testrun", "00-root", "--reply-to", "outer",
                "--by", "planner-lane",
            )["packet"]
            self.assertEqual("planner-lane", root_packet["assigned_name"])
            self.assertEqual(
                frontmatter(root_path)["admission"], root_packet["admission"],
                "claim and packet retain the shared admission receipt",
            )
            self.assertEqual("orch-decompose", root_packet["executor"])

            root_generation = frontmatter(root_path)["root_generation"]
            for ticket_id, depends_on in (
                ("00-root.01", "[]"),
                ("00-root.02", "[00-root.01]"),
            ):
                candidate = tmp / f"{ticket_id}.md"
                candidate.write_text(
                    stub(ticket_id, head, depends_on=depends_on).replace(
                        "admission: v1:pending",
                        f"root_generation: {root_generation}",
                    ),
                    encoding="utf-8",
                )
                emitted = run_cmd(
                    repo, "new", "testrun", ticket_id, "--file", str(candidate)
                )
                self.assertNotIn("error", emitted, emitted)

            gate = run_cmd(repo, "gate", "testrun", "00-root")
            self.assertNotIn("error", gate, gate)
            second_generation = seal_run(repo)
            self.assertNotEqual(first_generation, second_generation)
            cut_ids = ["00-root.01", "00-root.02", *gate["gate"]["ids"]]
            for ticket_id in ["00-root", *cut_ids]:
                with self.subTest(sealed=ticket_id):
                    data = frontmatter(run_dir / f"{ticket_id}.md")
                    self.assertNotEqual(
                        "[orch-spec, orch-decompose]", data.get("sequence"),
                        "the planner continuation is dispatch-only authority",
                    )
                    self.assertEqual(second_generation, data["cut_generation"])
                    self.assertTrue(data["assignment_seal"].startswith("sha256:"))
            for ticket_id in ("00-root", "00-root.01", "00-root.02"):
                self.assertNotIn("sequence", frontmatter(run_dir / f"{ticket_id}.md"))

            carry_file = tmp / "root-carry.md"
            carry_file.write_text(
                "- admission: root ready, claim, and packet used one receipt\n"
                "- continuation: cut resealed before frontier\n",
                encoding="utf-8",
            )
            filed = run_cmd(
                repo, "result", "testrun", "00-root", "--section", "Carry",
                "--file", str(carry_file), "--append",
            )
            self.assertNotIn("error", filed, filed)
            joined = run_cmd(repo, "set-status", "testrun", "00-root", "complete")
            self.assertNotIn("error", joined, joined)
            self.assertEqual("complete", frontmatter(root_path)["status"])

            frontier = run_cmd(repo, "ready", "--run", "testrun")
            frontier_ids = [item["id"] for item in frontier["ready"]]
            self.assertNotIn("00-root", frontier_ids,
                             "frontier cannot dispatch decomposition twice")
            self.assertIn("00-root.01", frontier_ids)

            claimed_unit = run_cmd(
                repo, "claim", "testrun", "00-root.01", "--by", "worker-lane"
            )
            self.assertNotIn("error", claimed_unit, claimed_unit)
            worker_packet = run_cmd(
                repo, "packet", "testrun", "00-root.01", "--reply-to", "outer",
                "--by", "worker-lane",
            )["packet"]
            self.assertIn("file `## Carry`", worker_packet["prompt"])
            checker_packet = run_cmd(
                repo, "packet", "testrun", "00-root.01", "--reply-to", "outer",
                "--executor", "orch-critique", "--by", "verifier-lane",
            )["packet"]
            self.assertEqual("verifier-lane", checker_packet["assigned_name"])
            self.assertNotEqual(worker_packet["assigned_name"],
                                checker_packet["assigned_name"])
            checked = run_cmd(
                repo, "check", "testrun", "00-root.01", "--by", "verifier-lane"
            )
            self.assertNotIn("error", checked, checked)

            unit_carry = tmp / "unit-carry.md"
            unit_carry.write_text(
                "- landed: lawful v2 member\n- verify: verifier-lane\n",
                encoding="utf-8",
            )
            filed = run_cmd(
                repo, "result", "testrun", "00-root.01", "--section", "Carry",
                "--file", str(unit_carry), "--append",
            )
            self.assertNotIn("error", filed, filed)
            completed = run_cmd(
                repo, "set-status", "testrun", "00-root.01", "complete"
            )
            self.assertNotIn("error", completed, completed)

            next_frontier = run_cmd(repo, "ready", "--run", "testrun")
            self.assertIn(
                "00-root.02", [item["id"] for item in next_frontier["ready"]]
            )
            claimed_next = run_cmd(
                repo, "claim", "testrun", "00-root.02", "--by", "worker-next"
            )
            self.assertNotIn("error", claimed_next, claimed_next)
            successor_prompt = run_cmd(
                repo, "packet", "testrun", "00-root.02", "--reply-to", "outer",
                "--by", "worker-next",
            )["packet"]["prompt"]
            self.assertIn("Carried context from 00-root.01 (complete)",
                          successor_prompt)
            self.assertIn("landed: lawful v2 member", successor_prompt)
            self.assertIn("verify: verifier-lane", successor_prompt)

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
