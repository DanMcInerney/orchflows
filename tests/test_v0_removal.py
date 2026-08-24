"""One grade path for both admission versions, and the v0 branches that go.

``grade_admission`` and ``_grade_v2_admission`` ran the same dependency,
authority and lower-validator block verbatim.  It lives at one site now, and
the proof that the move changed nothing is a parity run: one fixture corpus
graded twice, by this tree and by a tree identical to it except that
``scripts/tickets_admission.py`` is the baseline revision's copy.  Everything
else -- the lower validators, the format module, the fixtures -- is the same
bytes in both, so a difference in that comparison is the factoring's and
nothing else's.

The second half is the deletion.  No CLI write path can produce a ticket
without a ``v1:``/``v2:`` admission field, so the version-keyed refusal the
packet carried for a never-claimed v0 ticket was a second spelling of the
status guard beside it; the guard is now one site above both versions and the
refusal survives it.  What does not go is the ``legacy-unadmitted`` dispatch
marker: a v0 claim taken up before the admission boundary existed is still
live on disk, and its packet still says exactly that about it.
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

from scripts import tickets_generations as generations  # noqa: E402
from scripts.tickets_dispatch import _dispatch  # noqa: E402
from tests.test_tickets_cases.admission_v1 import v1_ticket  # noqa: E402
from tests.test_tickets_issue_cases.generation_lifecycle import snapshot  # noqa: E402

BASELINE = "808a0381212164d26137c7529db316c5a7cfff91"
SOURCES = ROOT / "scripts"
ADMISSION = SOURCES / "tickets_admission.py"

GRADE_CHILD = """
import json, sys
sys.path.insert(0, sys.argv[1])
import tickets_admission as admission
FIELDS = ("adapter", "findings", "receipt", "snapshot_ids",
          "input_fingerprint", "scope_fingerprint")
out = []
for case in json.loads(sys.stdin.read()):
    grade = admission.grade_admission(
        case["id"], case["text"], case["siblings"], context=case.get("context"),
    )
    out.append({name: grade[name] for name in FIELDS})
json.dump(out, sys.stdout)
"""


def _tree(tmp: Path, name: str, admission_source: bytes = None) -> Path:
    """A standalone copy of ``scripts/``, optionally with another admission."""

    dest = tmp / name
    shutil.copytree(SOURCES, dest, ignore=shutil.ignore_patterns("__pycache__"))
    if admission_source is not None:
        (dest / "tickets_admission.py").write_bytes(admission_source)
    return dest


def _graded(tree: Path, corpus: list) -> list:
    """The corpus graded by whichever ``tickets_admission`` ``tree`` holds."""

    result = subprocess.run(
        [sys.executable, "-c", GRADE_CHILD, str(tree)],
        input=json.dumps(corpus), capture_output=True, text=True, cwd=str(ROOT),
    )
    if result.returncode != 0:
        raise AssertionError(f"grade child failed for {tree.name}: {result.stderr}")
    return json.loads(result.stdout)


def _corpus() -> list:
    """V1 and v2 cases covering clean receipts and every finding family."""

    clean = v1_ticket()
    cases = [
        {"id": "T1", "text": clean, "siblings": {"T1": clean}},
        {"id": "T1", "text": clean.replace("depends_on: []", "depends_on: [T9]"),
         "siblings": {"T1": clean}},
        {"id": "T1", "text": clean.replace("cohort: v1:ticket:T1", "cohort: nonsense"),
         "siblings": {"T1": clean}},
        {"id": "T1", "text": clean.replace("isolation: required", "isolation: none"),
         "siblings": {"T1": clean}},
        {"id": "T1", "text": clean.replace("executor: orch-tdd", "executor: orch-draft"),
         "siblings": {"T1": clean}},
    ]
    incomplete = clean.replace("depends_on: []", "depends_on: [T2]")
    partner = v1_ticket("T2")
    cases.append({"id": "T1", "text": incomplete,
                  "siblings": {"T1": incomplete, "T2": partner}})
    # A dependency that really is complete, so the corpus reaches the silence
    # of the incomplete predicate and not only its noise: a check that a code
    # fires cannot catch a predicate widened to fire too often.
    satisfied = clean.replace("depends_on: []", "depends_on: [T3]")
    done = v1_ticket("T3").replace("status: pending", "status: complete")
    cases.append({"id": "T1", "text": satisfied,
                  "siblings": {"T1": satisfied, "T3": done}})
    # A return-size clause that does not parse, so the third `_optional_probe`
    # the shared block runs contributes a finding somewhere in the corpus.
    # Without this every case grades `grade_return_fixture` to the empty list
    # and the extend that carries it could be dropped unobserved.
    unparsable = clean.replace(
        "status; result; changed_artifacts; verification; feedback; risks",
        "status; result; changed_artifacts\n- return-size: not-a-canonical-object",
    )
    cases.append({"id": "T1", "text": unparsable, "siblings": {"T1": unparsable}})
    # The other two `_optional_probe` findings the shared block carries.  Their
    # fingerprints are compared for every case, so the probe calls are covered
    # either way -- but a fingerprint says nothing about whether the findings
    # beside it were extended onto the list, and nothing else in the corpus
    # makes either validator speak.  One case each, so deleting either extend
    # cannot pass the parity comparison in silence.
    duplicate_input = clean.replace('"name":"question"', '"name":"baseline"')
    cases.append({"id": "T1", "text": duplicate_input,
                  "siblings": {"T1": duplicate_input}})
    unplanned = clean.replace("mutations: [change:scratch/T1.txt]\n", "")
    cases.append({"id": "T1", "text": unplanned, "siblings": {"T1": unplanned}})
    current = snapshot()
    cases.append({"id": "00-root.01", "text": current["00-root.01"], "siblings": current})
    draft = generations.draft_snapshot("00-root", current)
    sealed = generations.seal_assignments(
        "00-root", current, draft, generations.validate_draft("00-root", current, draft),
    )
    cases.append({"id": "00-root.01", "text": sealed["00-root.01"], "siblings": sealed})
    return cases


def _sealed_run(directory: str) -> dict:
    """A sealed v2 generation on disk, and the grading context that reads it."""

    run_dir = Path(directory) / "tickets" / "run"
    run_dir.mkdir(parents=True)
    for ticket_id, value in snapshot().items():
        (run_dir / f"{ticket_id}.md").write_text(value, encoding="utf-8")
    cut = _dispatch(["draft-validate", "run", "00-root"])["draft_validation"]["cut_generation"]
    _dispatch(["seal", "run", "00-root", "--cut-generation", cut])
    texts = {
        path.stem: path.read_text(encoding="utf-8") for path in sorted(run_dir.glob("*.md"))
    }
    return {"id": "00-root.01", "text": texts["00-root.01"], "siblings": texts,
            "context": {"runs_root": str(Path(directory) / "runs"), "run": "run"}}


class SingleGradeSiteTest(unittest.TestCase):
    """The block both versions run is written once."""

    ONCE = (
        '"tickets_inputs", "grade_inputs"',
        '"tickets_scope", "grade_scope"',
        '"tickets_result", "grade_return_fixture"',
        "authority_findings(ticket_id, data)",
        "dependency-dangling",
        "dependency-incomplete",
    )

    def test_the_shared_grade_block_is_written_once(self):
        source = ADMISSION.read_text(encoding="utf-8")
        for fragment in self.ONCE:
            with self.subTest(fragment=fragment):
                self.assertEqual(
                    1, source.count(fragment),
                    f"{fragment} still appears on more than one grade path",
                )
        # One definition and one call from each of the two graders.
        self.assertEqual(3, source.count("_shared_grade("))

    def test_the_module_shrank_and_stays_inside_the_source_size_cap(self):
        current = len(ADMISSION.read_text(encoding="utf-8").splitlines())
        baseline = len(_baseline_admission().decode("utf-8").splitlines())
        self.assertLessEqual(current, 510)
        self.assertLess(current, baseline, "factoring must remove lines, not add them")


def _baseline_admission() -> bytes:
    return subprocess.run(
        ["git", "show", f"{BASELINE}:scripts/tickets_admission.py"],
        cwd=str(ROOT), capture_output=True, check=True,
    ).stdout


class GradeParityTest(unittest.TestCase):
    """The factoring is observably nothing: same findings, same receipts."""

    def test_v1_and_v2_grades_match_the_baseline_admission_module_exactly(self):
        baseline_source = _baseline_admission()
        self.assertNotIn(b"_shared_grade", baseline_source,
                         "the baseline copy must be the unfactored one")
        self.assertIn(b"_shared_grade", ADMISSION.read_bytes(),
                      "this tree must be the factored one")
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": str(tmp / "sink")}):
                corpus = _corpus() + [_sealed_run(str(tmp / "sink"))]
            here = _tree(tmp, "here")
            there = _tree(tmp, "there", baseline_source)
            graded = _graded(here, corpus)
            self.assertEqual(_graded(there, corpus), graded)
        self._assert_the_corpus_reached_what_it_claims(corpus, graded)

    def _assert_the_corpus_reached_what_it_claims(self, corpus: list, graded: list) -> None:
        """A parity run over cases that all refuse alike would prove nothing."""

        receipts = {row["receipt"].split(":")[0] for row in graded if "sha256" in row["receipt"]}
        codes = {item["code"] for row in graded for item in row["findings"]}
        self.assertEqual({"v1", "v2"}, receipts, "both receipt constructions must be exercised")
        # One code per source the shared block draws from: the inline
        # dependency loop, `authority_findings`, and each of the three
        # `_optional_probe` calls whose findings it extends on.
        for code in ("cohort-invalid", "dependency-dangling", "dependency-incomplete",
                     "return-size-invalid", "vcs-isolation-required",
                     "executor-pack-mismatch", "input-name-duplicate",
                     "mutation-plan-missing"):
            with self.subTest(code=code):
                self.assertIn(code, codes)
        # And the other half of the dependency predicate: one case whose
        # dependency is complete, which must grade to nothing at all.  Asserting
        # only that a code appears leaves a widened predicate invisible.
        silent = [row for case, row in zip(corpus, graded)
                  if "depends_on: [T3]" in case["text"]]
        self.assertEqual(1, len(silent), "the satisfied-dependency case must be in the corpus")
        self.assertEqual([], silent[0]["findings"],
                         "a complete dependency must contribute no finding")


class PacketV0BranchTest(unittest.TestCase):
    """The packet's version-keyed status refusal collapses to one guard.

    The refusal itself is not what went: a ticket nobody has claimed still
    gets no packet.  What went is the second spelling of it, reachable only
    for a ticket carrying no admission field at all -- which no CLI write
    path can produce, every one of them stamping ``v1:pending``.
    """

    def test_no_version_keyed_status_refusal_survives(self):
        source = (SOURCES / "tickets_packet.py").read_text(encoding="utf-8")
        self.assertNotIn("legacy ticket is not claimed", source)
        self.assertNotIn("re-cut it before packet emission", source)
        self.assertNotIn("v1 packet emission", source)
        self.assertEqual(1, source.count("legacy-unadmitted"),
                         "the dispatch marker for a live v0 claim stays, once")

    def test_a_never_claimed_v0_ticket_is_refused_and_a_live_one_still_dispatches(self):
        from scripts import tickets as tickets_mod

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            (tmp / ".git").mkdir()
            sink = (tmp / "state-sink").resolve()
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": str(sink)}):
                run_dir = sink / "tickets" / "testrun"
                run_dir.mkdir(parents=True)
                path = run_dir / "T1.md"
                v0 = v1_ticket().replace("status: pending", "status: ready")
                v0 = v0.replace("admission: v1:pending\n", "").replace("cohort: v1:ticket:T1\n", "")
                path.write_text(v0, encoding="utf-8")
                refused = _dispatch(["packet", "testrun", "T1", "--reply-to", "main"])
                self.assertIn("not claimed", refused["error"])
                self.assertNotIn("re-cut", refused["error"])
                live = path.read_text(encoding="utf-8")
                for field, value in (("status", "claimed"), ("claimed_by", "legacy-agent"),
                                     ("claimed_at", "2026-08-19T00:00:00Z")):
                    live = tickets_mod._set_frontmatter_field(live, field, value)
                path.write_text(live, encoding="utf-8")
                packet = _dispatch(["packet", "testrun", "T1", "--reply-to", "main"])
            self.assertEqual("legacy-unadmitted", packet["packet"]["admission"])


if __name__ == "__main__":
    unittest.main()
