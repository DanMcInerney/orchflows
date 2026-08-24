"""An admitted v2 ticket is re-graded in full, exactly as a v1 one is.

Three gates read the ticket's stored ``admission`` field and open only for a
``v1:`` prefix: ``tickets_inputs.grade_inputs``, ``tickets_scope.grade_scope``
and ``tickets_scope.unplanned_mutations``.  A v2 ticket never carries that
prefix -- it carries ``v2:pending`` before its receipt and
``v2:<adapter>:sha256:<digest>`` after -- so every v2 ticket in the system was
graded as if it predated the admission boundary: its Fixed inputs fingerprinted
to ``inputs:legacy-unadmitted`` without one identity being resolved, its scope
degraded to ``direct-only`` without one declared edge being closed, and any
actual mutation outside its plan was silently authorized at the join.

The gates are the whole subject.  A version prefix is not a grading decision,
so ``v2:pending`` opens the gate exactly as ``v1:pending`` does: the alternative
-- opening only for a fully graded ``v2:`` receipt -- would let ``ready`` stamp
a receipt over inputs it never graded and then have the first re-grade at claim
or packet produce findings, flip the recomputed receipt back to ``v2:pending``,
and refuse the packet of a ticket already admitted.  Grading at one version's
boundary and not the other's is the defect, not the fix for it.

What must not move is v1 and v0.  ``V1AndV0ParityTest`` proves that by grading
one corpus twice -- once by this tree's two modules and once by a tree whose
``tickets_inputs.py`` and ``tickets_scope.py`` are the pinned baseline's bytes,
everything else identical -- so a difference in that comparison is this change's
and nothing else's.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import tickets_inputs, tickets_scope  # noqa: E402
from scripts.tickets_admission import grade_admission  # noqa: E402
from scripts.tickets_dispatch import _dispatch  # noqa: E402
from scripts.tickets_format import _parse_frontmatter  # noqa: E402

BASELINE = "808a0381212164d26137c7529db316c5a7cfff91"
SOURCES = ROOT / "scripts"
GATED = ("tickets_inputs.py", "tickets_scope.py")
V1_RECEIPT = "v1:git:sha256:" + "a" * 64
V2_RECEIPT = "v2:git:sha256:" + "b" * 64
# Every value a real ticket's `admission` field can hold once a producer has
# written it.  A version prefix is not a grading decision, so all four open the
# gate and the absence of the field is the only thing that closes it.
ADMITTED = ("v1:pending", V1_RECEIPT, "v2:pending", V2_RECEIPT)
MANIFEST = json.dumps({
    "version": 1,
    "edges": [{
        "from": {"operation": "change", "path": "contracts/*.md"},
        "requires": [{"operation": "change", "path": "tests/pins.json"}],
        "reason": "canonical contract pin",
    }],
}, separators=(",", ":")).encode("utf-8")

TICKET = """---
id: {tid}
run: run
status: {status}
admission: {admission}
executor: {executor}
pack: orch-code-pack
independence: gate
depends_on: []
write_scope: [{scope}]
mutations: [{plan}]
excluded_actions: [vcs.integrate, vcs.push, vcs.open-pr]
isolation: required
bound: 30m
claimed_by:
claimed_at:
ownership_regions: []
---

## Objective

Change one observable artifact.

## Fixed inputs

- input: {{"identity":{{"kind":"git-tree","repo":"run-project","revision":"{baseline}"}},"name":"baseline","type":"identity"}}
- input: {{"name":"question","type":"literal","value":"fixed"}}

## Completion test

- the artifact carries the value | oracle: `python -m unittest` | oracle_class: deterministic | provenance: pre-existing

## Return fields

status; result; changed_artifacts; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]

## Handoff

"""


def _head() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()


def ticket(tid="00-root.01", *, admission="v2:pending", status="pending",
           executor="orch-tdd", scope="scratch/unit.txt",
           plan="change:scratch/unit.txt", baseline=None):
    """One ticket body whose only moving part is the admission field.

    A gate reads that field and nothing else about a version, so holding the
    rest of the ticket byte-identical across versions is what makes the
    comparison a statement about the gate.
    """

    text = TICKET.format(tid=tid, admission=admission, status=status, executor=executor,
                         scope=scope, plan=plan, baseline=baseline or _head())
    if admission is None:
        text = text.replace(f"admission: {admission}\n", "")
    return text


def v0_ticket(**kwargs):
    """The one shape that predates the boundary: no admission field at all."""

    text = ticket(**kwargs)
    marker = text.split("\n")
    return "\n".join(line for line in marker if not line.startswith("admission:"))


def _inputs(text, tid="00-root.01"):
    return tickets_inputs.grade_inputs(
        ticket_id=tid, text=text, siblings={tid: text}, adapter_id="git", context={},
    )


def _scope(text, tid="00-root.01", manifest=MANIFEST):
    return tickets_scope.grade_scope(
        ticket_id=tid, text=text, siblings={tid: text}, adapter_id="git",
        context={"scope_manifest": manifest},
    )


def _codes(graded):
    return {item["code"] for item in graded["findings"]}


class AdmissionVersionGateTest(unittest.TestCase):
    """The three gates open for a v2 ticket exactly as they do for a v1 one."""

    def test_inputs_are_graded_under_every_admitted_version(self):
        graded = {value: _inputs(ticket(admission=value)) for value in ADMITTED}
        for value, result in graded.items():
            with self.subTest(admission=value):
                self.assertNotEqual("inputs:legacy-unadmitted", result["fingerprint"])
                self.assertTrue(result["fingerprint"].startswith("inputs:sha256:"),
                                f"{value} did not reach identity resolution: {result['fingerprint']}")
        self.assertEqual(1, len({result["fingerprint"] for result in graded.values()}),
                         "the same ticket must fingerprint identically under every version")

    def test_a_ticket_with_no_admission_field_is_still_the_legacy_one(self):
        result = _inputs(v0_ticket())
        self.assertEqual("inputs:legacy-unadmitted", result["fingerprint"])
        self.assertEqual([], result["findings"])

    def test_inputs_grading_of_a_v2_ticket_can_fail(self):
        """A fingerprint alone would not show the identity was resolved."""

        broken = ticket(admission=V2_RECEIPT, baseline="0" * 40)
        self.assertIn("git-revision-unresolved", _codes(_inputs(broken)))
        self.assertEqual([], _inputs(v0_ticket(baseline="0" * 40))["findings"],
                         "the legacy path must still resolve nothing at all")

    def test_scope_is_graded_at_full_strength_under_every_admitted_version(self):
        for value in ADMITTED:
            with self.subTest(admission=value):
                result = _scope(ticket(admission=value))
                self.assertEqual("declared-edges", result["mode"])
                self.assertTrue(result["fingerprint"].startswith("scope:sha256:"))
        degraded = _scope(v0_ticket())
        self.assertEqual("direct-only", degraded["mode"])
        self.assertEqual("scope:direct-only:git", degraded["fingerprint"])

    def test_a_v2_ticket_declared_edge_is_actually_closed(self):
        """Mode is a label; the finding is the grading the label stands for."""

        unclosed = {"scope": "contracts/example.md", "plan": "change:contracts/example.md"}
        self.assertIn("scope-owner-missing", _codes(_scope(ticket(admission=V2_RECEIPT, **unclosed))))
        self.assertEqual(set(), _codes(_scope(v0_ticket(**unclosed))))

    def test_a_v2_ticket_plan_still_bounds_its_actual_mutations(self):
        outside = [("change", "scratch/elsewhere.txt")]
        for value in ADMITTED:
            with self.subTest(admission=value):
                data = _parse_frontmatter(ticket(admission=value))
                self.assertEqual(sorted(outside), tickets_scope.unplanned_mutations(data, outside))
                self.assertEqual([], tickets_scope.unplanned_mutations(data, [("change", "scratch/unit.txt")]))
        self.assertEqual([], tickets_scope.unplanned_mutations(_parse_frontmatter(v0_ticket()), outside))


def _seal(directory: str) -> Path:
    """A sealed, fully specified v2 generation on disk, ready to be released."""

    run_dir = Path(directory) / "tickets" / "run"
    run_dir.mkdir(parents=True)
    head = _head()
    for tid, executor in (("00-root", "orch-decompose"), ("00-root.01", "orch-tdd")):
        (run_dir / f"{tid}.md").write_text(
            ticket(tid, executor=executor, baseline=head), encoding="utf-8",
        )
    validated = _dispatch(["draft-validate", "run", "00-root"])
    cut = validated["draft_validation"]["cut_generation"]
    sealed = _dispatch(["seal", "run", "00-root", "--cut-generation", cut])
    if "error" in sealed:
        raise AssertionError(f"seal failed: {sealed}")
    return run_dir


class LifecycleRegradeTest(unittest.TestCase):
    """Ready, claim and packet each re-grade the admitted v2 ticket in full."""

    def _assert_full_grade(self, stage, run_dir, sink, tid="00-root.01"):
        """The exact grade the named stage runs, on the exact bytes it reads.

        ``ready``, ``claim`` and ``packet`` each call ``grade_admission`` with
        this context, so re-running it here is that stage's own re-grade and
        not a second, kinder one.
        """

        texts = {path.stem: path.read_text(encoding="utf-8") for path in sorted(run_dir.glob("*.md"))}
        context = {"runs_root": str(Path(sink) / "runs"), "run": "run"}
        graded = grade_admission(tid, texts[tid], texts, context=context)
        self.assertEqual([], graded["findings"], f"{stage} refused the admitted v2 ticket")
        self.assertNotEqual("inputs:legacy-unadmitted", graded["input_fingerprint"],
                            f"{stage} re-graded the ticket as legacy")
        self.assertTrue(graded["input_fingerprint"].startswith("inputs:sha256:"), stage)
        self.assertNotEqual("scope:direct-only:git", graded["scope_fingerprint"],
                            f"{stage} degraded scope grading to direct-only")
        self.assertTrue(graded["scope_fingerprint"].startswith("scope:sha256:"), stage)
        return graded, texts[tid]

    def test_ready_claim_and_packet_each_grade_the_v2_ticket_in_full(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                run_dir = _seal(directory)
                self._assert_full_grade("ready", run_dir, directory)
                ready = _dispatch(["ready", "--run", "run"])
                self.assertIn("00-root.01", {item["id"] for item in ready["ready"]},
                              f"admitted v2 unit was not released: {ready.get('skipped')}")

                graded, text = self._assert_full_grade("claim", run_dir, directory)
                self.assertEqual(graded["receipt"], _parse_frontmatter(text)["admission"])
                claimed = _dispatch(["claim", "run", "00-root.01", "--by", "tester"])
                self.assertNotIn("error", claimed)

                graded, _ = self._assert_full_grade("packet", run_dir, directory)
                packet = _dispatch(["packet", "run", "00-root.01", "--reply-to", "main"])
                self.assertNotIn("error", packet)
                self.assertEqual(graded["receipt"], packet["packet"]["admission"])


GRADE_CHILD = """
import json, sys
sys.path.insert(0, sys.argv[1])
import tickets_inputs, tickets_scope
from tickets_format import _parse_frontmatter
out = []
for case in json.loads(sys.stdin.read()):
    common = {"ticket_id": case["id"], "text": case["text"],
              "siblings": {case["id"]: case["text"]}, "adapter_id": case["adapter"]}
    graded = tickets_inputs.grade_inputs(context={}, **common)
    scope = tickets_scope.grade_scope(
        context={"scope_manifest": case["manifest"].encode("utf-8")}, **common,
    )
    out.append({
        "inputs": graded,
        "scope": {key: scope[key] for key in ("findings", "fingerprint", "mode")},
        "unplanned": tickets_scope.unplanned_mutations(
            _parse_frontmatter(case["text"]), [tuple(row) for row in case["actual"]],
        ),
    })
json.dump(out, sys.stdout, default=list)
"""


def _tree(tmp: Path, name: str, baseline: bool = False) -> Path:
    """A standalone ``scripts/`` copy, optionally with the pinned gates back."""

    dest = tmp / name
    shutil.copytree(SOURCES, dest, ignore=shutil.ignore_patterns("__pycache__"))
    if baseline:
        for module in GATED:
            dest.joinpath(module).write_bytes(_pinned(module))
    return dest


def _pinned(module: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{BASELINE}:scripts/{module}"],
        cwd=str(ROOT), capture_output=True, check=True,
    ).stdout


def _graded(tree: Path, corpus: list) -> list:
    result = subprocess.run(
        [sys.executable, "-c", GRADE_CHILD, str(tree)],
        input=json.dumps(corpus), capture_output=True, text=True, cwd=str(ROOT),
    )
    if result.returncode != 0:
        raise AssertionError(f"grade child failed for {tree.name}: {result.stderr}")
    return json.loads(result.stdout)


class V1AndV0ParityTest(unittest.TestCase):
    """v1 and v0 interpretation is byte-for-byte what the pin says it was."""

    def _corpus(self) -> list:
        head = _head()
        rows = []
        for admission in ("v1:pending", V1_RECEIPT):
            rows.append(ticket(admission=admission, baseline=head))
            rows.append(ticket(admission=admission, baseline="0" * 40))
            rows.append(ticket(admission=admission, baseline=head,
                               scope="contracts/example.md", plan="change:contracts/example.md"))
        rows.append(v0_ticket(baseline=head))
        rows.append(v0_ticket(baseline=head, scope="contracts/example.md",
                              plan="change:contracts/example.md"))
        return [{"id": "00-root.01", "text": text, "adapter": "git",
                 "manifest": MANIFEST.decode("utf-8"),
                 "actual": [["change", "scratch/elsewhere.txt"]]} for text in rows]

    def test_no_v1_or_v0_grade_moves_off_the_pinned_baseline(self):
        for module in GATED:
            with self.subTest(module=module):
                self.assertNotEqual(
                    _pinned(module), SOURCES.joinpath(module).read_bytes(),
                    f"scripts/{module} still carries the pinned gate, so this comparison proves nothing",
                )
        corpus = self._corpus()
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            self.assertEqual(_graded(_tree(tmp, "pinned", baseline=True), corpus),
                             _graded(_tree(tmp, "here"), corpus))

    def test_the_corpus_reaches_the_grading_it_claims_to_hold_still(self):
        """A corpus that refused alike everywhere would prove nothing."""

        graded = [
            (_inputs(case["text"]), _scope(case["text"]),
             tickets_scope.unplanned_mutations(_parse_frontmatter(case["text"]),
                                               [("change", "scratch/elsewhere.txt")]))
            for case in self._corpus()
        ]
        fingerprints = {row[0]["fingerprint"] for row in graded}
        self.assertIn("inputs:legacy-unadmitted", fingerprints, "the v0 half must be present")
        self.assertTrue(any(value.startswith("inputs:sha256:") for value in fingerprints),
                        "the v1 half must reach identity resolution")
        codes = {item["code"] for row in graded for item in row[0]["findings"] + row[1]["findings"]}
        for code in ("git-revision-unresolved", "scope-owner-missing"):
            with self.subTest(code=code):
                self.assertIn(code, codes)
        self.assertEqual({"declared-edges", "direct-only"}, {row[1]["mode"] for row in graded})
        self.assertIn([("change", "scratch/elsewhere.txt")], [row[2] for row in graded])


if __name__ == "__main__":
    unittest.main()
