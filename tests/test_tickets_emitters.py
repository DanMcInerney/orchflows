"""Every ticket-emitting door grades its emission before it writes.

A door that writes a ticket the next door refuses has spent the run's time
to produce a refusal. `new`, `amend`, `recut`, `instantiate`, `gate` and
`stamp-generation` all grade what they are about to write through the one
grading context (`scripts/tickets_context.py`), against the snapshot as it
would stand after the write, and refuse rather than emit.

The partition makes the law usable: an emitted ticket names dependencies
that have not run and an assignment `seal` has not sealed, neither of
which is the emitter's fault or repairable at emission, so both defer.
Everything else -- a locator no adapter resolves, an executor its pack
does not bind, an absent mutation plan -- is refused while the flag that
was wrong is still in the caller's hand.

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

STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"
COMPOSITIONS = ROOT / "compositions"

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
BODY = ("\n## Objective\n\n{objective}\n\n## Fixed inputs\n\n{inputs}\n\n"
        "## Completion test\n\n- it works | oracle: `true` | oracle_class: "
        "deterministic | provenance: authored-here\n\n## Return fields\n\n"
        "status; result; verification; feedback; risks\n\n## Result\n\n"
        "## Verification\n\n## Feedback\n\n[]\n\n## Risks\n\n[]\n")


PLAIN_INPUT = '- input: {"name":"subject","type":"literal","value":"the subject"}'
GIT_INPUT = ('- input: {{"identity":{{"kind":"git-tree","repo":"run-project",'
             '"revision":"{baseline}"}},"name":"baseline","type":"identity"}}')


def stub(tid, baseline=None, executor=None, independence="checker",
         depends_on="[]", objective="Deliver the one thing this item is for."):
    """One ticket its adapter admits, in either of the two shapes.

    With ``baseline`` -- the fixture repository's own HEAD -- it is a code
    pack ticket, whose git adapter reads one ``git-tree`` identity and
    resolves it against the checkout. Without one it carries no pack, the
    shape most shipped composition stubs have and the one the pure-law
    cases need, since a grade with no checkout cannot resolve a revision.
    """
    git = baseline is not None
    return (STUB + BODY).format(
        tid=tid, pack="pack: orch-code-pack\n" if git else "",
        executor=executor or ("orch-tdd" if git else "orch-investigate"),
        inputs=GIT_INPUT.format(baseline=baseline) if git else PLAIN_INPUT,
        independence=independence, depends_on=depends_on, objective=objective)


def use_sink(tmp: Path) -> Path:
    sink = (tmp / "state-sink").resolve()
    os.environ[STATE_HOME_ENV_VAR] = str(sink)
    return sink


def sink_root() -> Path:
    return Path(os.environ[STATE_HOME_ENV_VAR])


def run_dir_of(run: str = "testrun") -> Path:
    return sink_root() / "tickets" / run


def git_repo(tmp: Path):
    """``(repo, head)``: a real checkout, and the commit its tickets pin.

    The doors render a real HEAD and the adapter resolves a real revision.
    """

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
    """``(tmp, repo, head)``: a temporary sink and a real checkout in it.

    Stated once rather than three lines at a time in sixteen places.
    """

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


def declared_placeholders(directory: Path) -> list:
    """The names one template's manifest requires a ``--set`` for."""

    for line in (directory / "template.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("placeholders:"):
            return [name.strip() for name in
                    line.partition(":")[2].strip().strip("[]").split(",") if name.strip()]
    return []


def frontmatter(path: Path) -> dict:
    data = {}
    for line in path.read_text(encoding="utf-8").split("---")[1].strip().splitlines():
        key, _, value = line.partition(":")
        data[key.strip()] = value.strip()
    return data


def place_root(head, v2=False, root_status=None):
    """A root and one unit of its cut, in the sink, as a door finds them."""

    run_dir = run_dir_of()
    run_dir.mkdir(parents=True, exist_ok=True)
    for tid, extra in (("00-root", {"executor": "orch-decompose",
                                    "independence": "gate"}), ("00-root.01", {})):
        text = stub(tid, head, **extra)
        if v2:
            text = text.replace(f"cohort: v1:ticket:{tid}\n", "").replace(
                "admission: v1:pending", "admission: v2:pending")
        if root_status is not None and tid == "00-root":
            text = text.replace("status: pending", f"status: {root_status}").replace(
                "claimed_by:", "claimed_by: someone")
        (run_dir / f"{tid}.md").write_text(text, encoding="utf-8")
    return run_dir


class EmissionLawPartition(unittest.TestCase):
    """What the law refuses at emission, and what it defers."""

    def test_a_dependency_that_has_not_run_yet_is_deferred(self):
        """A unit naming a sibling still pending: the commonest emission,
        and if the law refused it no cut could issue its second item."""

        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            siblings = {"00-a": stub("00-a")}
            incoming = {"00-b": stub("00-b", depends_on="[00-a]")}
            self.assertIsNone(tickets_emission.grade_emission(
                "new", "testrun", incoming, siblings))

    def test_an_unsealed_v2_assignment_is_deferred(self):
        """A v2 ticket is emitted before `seal` runs, by construction."""

        for code in ("seal-state-unavailable", "seal-state-missing",
                     "seal-state-mismatch", "sealed-assignment-mismatch",
                     "validation-receipt-mismatch", "v2-opt-in-missing"):
            with self.subTest(code=code):
                self.assertIn(code, tickets_emission.DEFERRED_CODES)

    def test_an_emitter_owned_finding_is_refused(self):
        """A locator no adapter resolves is the emitter's own and refuses."""

        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            text = stub("00-a").replace(
                PLAIN_INPUT,
                '- input: {"identity":{"kind":"artifact","locator":'
                '"project:rules/improvement.md","sha256":"' + "5" * 64 + '"},'
                '"name":"law","type":"identity"}')
            refusal = tickets_emission.grade_emission(
                "new", "testrun", {"00-a": text}, {})
            self.assertIsNotNone(refusal)
            self.assertIn("identity-locator-invalid", codes(refusal))

    def test_a_finding_code_the_law_does_not_know_refuses(self):
        """Fail-closed: an unclassified code is the emitter's until stated.

        A code added to the grader later lands as a refusal a reader sees,
        never as a silent admission.
        """

        self.assertNotIn("some-code-invented-later",
                         tickets_emission.DEFERRED_CODES)
        self.assertTrue(tickets_emission.refusable(
            [{"code": "some-code-invented-later", "field": "x", "detail": "y"}]))


class NewGradesItsEmission(unittest.TestCase):
    def test_new_refuses_the_locator_claim_refuses(self):
        """The recorded instance: issue-time acceptance, claim-time refusal."""

        with workspace() as (tmp, repo, head):
            payload = run_cmd(
                repo, "new", "testrun", "10-abs",
                "--executor", "orch-tdd",
                "--objective", "An absolute locator in a fixed input.",
                "--criterion", "it works | oracle: `true` | oracle_class: "
                               "deterministic | provenance: authored-here",
                "--pack", "orch-code-pack",
                "--input", json.dumps({
                    "name": "baseline", "type": "identity",
                    "identity": {"kind": "git-tree", "repo": "run-project",
                                 "revision": head},
                }),
                "--input", json.dumps({
                    "name": "spec", "type": "identity",
                    "identity": {"kind": "git-path", "repo": "run-project",
                                 "revision": head,
                                 "path": "C:/Users/danhm/tools/orchflows-public/AGENTS.md"},
                }),
                "--write-scope", "scripts/b.py",
                "--mutation", "change:scripts/b.py",
                "--isolation", "required",
            )
            self.assertIn("error", payload)
            self.assertIn("identity-path-invalid", codes(payload))
            self.assertFalse((run_dir_of() / "10-abs.md").exists(),
                             "a refused emission writes nothing")

    def test_new_still_issues_a_clean_ticket(self):
        """The law must not cost the emission it was written to protect."""

        with workspace() as (tmp, repo, head):
            payload = run_cmd(
                repo, "new", "testrun", "10-ok",
                "--executor", "orch-tdd",
                "--objective", "Deliver the one thing this item is for.",
                "--criterion", "it works | oracle: `true` | oracle_class: "
                               "deterministic | provenance: authored-here",
                "--pack", "orch-code-pack",
                "--input", json.dumps({
                    "name": "baseline", "type": "identity",
                    "identity": {"kind": "git-tree", "repo": "run-project",
                                 "revision": head},
                }),
                "--write-scope", "scripts/b.py",
                "--mutation", "change:scripts/b.py",
                "--isolation", "required",
            )
            self.assertNotIn("error", payload)
            self.assertTrue((run_dir_of() / "10-ok.md").exists())


class InstantiateGradesItsEmission(unittest.TestCase):
    def test_instantiate_refuses_stubs_the_next_door_refuses(self):
        """Nothing may be written when the grade is a later refusal."""

        with workspace() as (tmp, repo, head):
            directory = tmp / "template"
            directory.mkdir()
            (directory / "template.md").write_text(
                "---\nname: broken\nentry: named\nplaceholders: []\n---\n\n"
                "A template whose stubs the next door refuses.\n",
                encoding="utf-8")
            (directory / "00-a.md").write_text(
                stub("00-a", "{{baseline}}").replace(
                    "mutations: [change:scripts/a.py]\n", ""),
                encoding="utf-8")
            payload = run_cmd(repo, "instantiate", str(directory),
                              "--run", "testrun")
            self.assertIn("error", payload)
            self.assertFalse((run_dir_of() / "00-a.md").exists(),
                             "a refused template writes none of its stubs")

    def test_every_shipped_composition_passes_its_own_door(self):
        """Every composition orchflows ships must instantiate admissibly.

        Four did not. `instantiate` wrote self-improve's two stubs and
        `ready` then skipped both, so the shipped template could not be run
        at all; evolve, skill-tournament and benchmaker carried the same
        class. One broken template is a defect -- the door is the law for
        all of them, which is why this iterates the directory rather than
        naming the one that was reported.
        """

        placeholders = {
            "bound": "30m",
            "brief_bound": "30m",
            "executor": "orch-tdd",
            "isolation": "required",
            "mutations": "change:scripts/a.py",
            "oracle_command": "uv run --no-project python -m unittest tests.test_templates",
            "oracle_name": "the named fixture oracle",
            "oracle_provenance": "pre-existing",
            "paths": "scripts/a.py",
            "simple_task": "Deliver one simple code change.",
            "skill": "orch-tdd",
            "target": "scripts/a.py",
            "window": "the last seven days",
        }
        for directory in sorted(p for p in COMPOSITIONS.iterdir()
                                if p.is_dir() and p.name != "references"):
            with self.subTest(composition=directory.name):
                with workspace() as (tmp, repo, head):
                    settings = []
                    for name in declared_placeholders(directory):
                        settings += ["--set", "%s=%s" % (name, repo.as_posix()
                                     if name == "workspace"
                                     else placeholders.get(name, "the value"))]
                    self.assertNotIn("error", run_cmd(
                        repo, "instantiate", str(directory), "--run", "testrun",
                        *settings))
                    for entry in run_cmd(repo, "ready", "--run", "testrun").get("skipped") or []:
                        self.assertEqual(
                            set(), codes(entry) - tickets_emission.DEFERRED_CODES,
                            f"{directory.name}/{entry.get('id')} is inadmissible as shipped")


class TheSealedBatchWedge(unittest.TestCase):
    """A template's stubs are one atom, so none of them may need correcting.

    `instantiate` cuts every stub into one batch cohort, and a cohort seals
    whole the moment a member goes live: claiming the first freezes the
    rest against `amend` and `recut`. That is the right shape, and exactly
    why a stub needing correction mid-flight is a wedge with no way out.
    The self-improve template was that stub -- it named its predecessor's
    finding in prose, so the proposal had to be amended in after `00-mine`
    landed, by which time the cohort was sealed. What closes it is removing
    the need, not loosening the seal: the predecessor's Result is a fixed
    input identity, and the stub is complete as shipped.
    """

    def test_the_shipped_chain_needs_no_correction_once_its_first_stub_lands(self):
        with workspace() as (tmp, repo, head):
            self.assertNotIn("error", run_cmd(
                repo, "instantiate", str(COMPOSITIONS / "self-improve"),
                "--run", "testrun",
                "--set", "window=the last seven days",
                "--set", f"workspace={repo.as_posix()}"))

            run_cmd(repo, "ready", "--run", "testrun")
            self.assertNotIn("error",
                             run_cmd(repo, "claim", "testrun", "00-mine", "--by", "probe"))

            # The cohort is now sealed, so the second stub cannot be
            # repaired -- and must not need to be.
            body = tmp / "objective.md"
            body.write_text("Land the proposal 00-mine ranked first.\n",
                            encoding="utf-8")
            self.assertIn("error", run_cmd(
                repo, "amend", "testrun", "01-deliver",
                "--section", "Objective", "--file", str(body)),
                "a live cohort is sealed, as the contract says")

            deliver = (run_dir_of() / "01-deliver.md").read_text(encoding="utf-8")
            self.assertIn('"ticket":"00-mine"},"name":"ranked-proposals"', deliver.replace(" ", ""),
                          "the predecessor's finding is the template's own identity, not a hole")
            self.assertNotIn("{{", deliver, "no placeholder survives instantiation")

    def test_the_second_stub_carries_only_findings_time_repairs(self):
        """Only its predecessor finishing stands between the second stub and
        its dispatch -- nothing a corrector would have to fix."""

        with workspace() as (tmp, repo, head):
            self.assertNotIn("error", run_cmd(
                repo, "instantiate", str(COMPOSITIONS / "self-improve"),
                "--run", "testrun",
                "--set", "window=the last seven days",
                "--set", f"workspace={repo.as_posix()}"))
            for entry in run_cmd(repo, "ready", "--run", "testrun").get("skipped") or []:
                self.assertEqual(
                    set(), codes(entry) - tickets_emission.DEFERRED_CODES,
                    f"{entry.get('id')} needs a correction the seal forbids")


class GateGradesItsEmission(unittest.TestCase):
    def test_gate_joins_a_sealed_v2_root_as_a_drafting_family(self):
        """The recorded instance, closed: stubs join the root's declared
        version, and the law's half is `tests/test_v2_membership.py`."""

        with workspace() as (tmp, repo, head):
            run_dir = place_root(head, v2=True)
            validated = run_cmd(repo, "draft-validate", "testrun", "00-root")
            sealed = run_cmd(
                repo, "seal", "testrun", "00-root", "--cut-generation",
                validated["draft_validation"]["cut_generation"])
            self.assertNotIn("error", sealed)
            payload = run_cmd(repo, "gate", "testrun", "00-root")
            self.assertNotIn("error", payload)
            stubs = sorted(run_dir.glob("*.gate.*.md"))
            self.assertEqual(2, len(stubs), "one lens: chained critique + verify")
            for data in map(frontmatter, stubs):
                self.assertEqual(("v2:pending", None), (data.get("admission"), data.get("cohort")))
                self.assertTrue(data.get("root_generation", "").startswith("v2:root:"))


class RecutAndAmendGradeTheirEmission(unittest.TestCase):
    def _issued(self, head):
        run_dir = run_dir_of()
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "20-a.md").write_text(stub("20-a", head), encoding="utf-8")
        return run_dir

    def test_recut_refuses_a_candidate_the_next_door_refuses(self):
        with workspace() as (tmp, repo, head):
            run_dir = self._issued(head)
            before = (run_dir / "20-a.md").read_text(encoding="utf-8")
            candidate = tmp / "candidate.md"
            candidate.write_text(
                before.replace("mutations: [change:scripts/a.py]\n", ""),
                encoding="utf-8")
            payload = run_cmd(repo, "recut", "testrun", "20-a",
                              "--file", str(candidate))
            self.assertIn("error", payload)
            self.assertEqual(before, (run_dir / "20-a.md").read_text(encoding="utf-8"),
                             "a refused recut leaves the ticket exactly as it was")

    def test_amend_refuses_a_section_the_next_door_refuses(self):
        with workspace() as (tmp, repo, head):
            run_dir = self._issued(head)
            before = (run_dir / "20-a.md").read_text(encoding="utf-8")
            body = tmp / "inputs.md"
            body.write_text(
                '- input: {"identity":{"kind":"artifact","locator":'
                '"project:rules/improvement.md","sha256":"' + "5" * 64 + '"},'
                '"name":"law","type":"identity"}\n', encoding="utf-8")
            payload = run_cmd(repo, "amend", "testrun", "20-a",
                              "--section", "Fixed inputs", "--file", str(body))
            self.assertIn("error", payload)
            self.assertEqual(before, (run_dir / "20-a.md").read_text(encoding="utf-8"),
                             "a refused amend leaves the ticket exactly as it was")


class RootGenerationStamping(unittest.TestCase):
    """The v2 opt-in a root needed and no subcommand wrote.

    `draft-validate` requires the root to already carry a v2 field, and the
    only thing producing one was a hand edit of the file in the sink -- the
    one write path around every refusal the doors apply to those bytes.
    """

    def test_the_subcommand_is_offered(self):
        with workspace() as (tmp, repo, head):
            self.assertIn("stamp-generation",
                          run_cmd(repo, "help")["help"]["subcommands"])

    def test_stamping_a_v1_root_opens_the_v2_path_without_a_hand_edit(self):
        with workspace() as (tmp, repo, head):
            run_dir = place_root(head)

            self.assertIn("error", run_cmd(repo, "draft-validate", "testrun", "00-root"),
                          "an unstamped root is not yet a v2 draft")
            stamped = run_cmd(repo, "stamp-generation", "testrun", "00-root")
            self.assertNotIn("error", stamped)

            for path in (run_dir / "00-root.md", run_dir / "00-root.01.md"):
                data = frontmatter(path)
                self.assertTrue(data.get("root_generation", "").startswith("v2:root:"))
                self.assertEqual("v2:pending", data.get("admission"))
                self.assertNotIn("cohort", data,
                                 "a v2 ticket is frozen by its seal, not by a cohort")
            self.assertNotIn("error",
                             run_cmd(repo, "draft-validate", "testrun", "00-root"))

    def test_stamping_refuses_a_root_that_is_already_taken_up(self):
        with workspace() as (tmp, repo, head):
            place_root(head, root_status="claimed")
            self.assertIn("error",
                          run_cmd(repo, "stamp-generation", "testrun", "00-root"))


if __name__ == "__main__":
    unittest.main()
