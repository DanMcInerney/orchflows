"""`tickets.py reissue`: one blocked ticket superseded without a re-spec.

A ticket that blocks on a field problem used to cost a whole specification
pass to replace, and the replacement was written by hand -- which is the one
path around every refusal `new` applies to the same bytes. What is pinned
here is that the successor arrives through `new --file`, carrying the
predecessor's cited section by identity and digest, with every lifecycle
field of the source dropped and the source's own bytes untouched.

Self-contained by write scope: the shared case chains under
`tests/test_tickets_cases/` are other items' to edit in this run, so the
fixtures here are built from their published primitives alone.
"""

import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from tests.test_tickets_issue_cases.common import run_cmd, use_sink
from tests.test_tickets_cases.admission_v1 import initialize_git_fixture, v1_ticket

import scripts.tickets as tickets_mod  # noqa: E402
from scripts.tickets_format import _parse_frontmatter, _scope_entries, _sections

HANDOFF = "The excluded action this item suspended through: vcs.integrate.\n"
# `python -m unittest` is the whole-suite finding every grader reports; a
# case that means "nothing is left to report" has to state a narrower one.
NARROW_ORACLE = "`python -m unittest tests.test_thing.CaseTest.test_one`"
LIFECYCLE = {
    "claimed_by": "unit-a",
    "claimed_at": "2026-08-23T10:00:00Z",
    "checked_by": "checker-a",
    "workspace_branch": "worktree-a",
    "workspace_baseline": "0123456789abcdef0123456789abcdef01234567 clean",
    "root_generation": "root:00-root:1:sha256:" + "0" * 64,
    "cut_generation": "cut:00-root:1:sha256:" + "1" * 64,
    "assignment_seal": "sha256:" + "2" * 64,
}
DROPPED = ("checked_by", "workspace_branch", "workspace_baseline",
           "root_generation", "cut_generation", "assignment_seal")


class ReissueFixture(unittest.TestCase):
    """A sink holding one blocked root, and a checkout to stand in."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.sink = use_sink(self.tmp)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.baseline = initialize_git_fixture(self.repo)
        self._cwd = os.getcwd()
        os.chdir(self.repo)
        self.source_path = self.place_source()

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def source_text(self, *, status="blocked", handoff=True, tid="00-root",
                    executor="orch-decompose", cohort=None, oracle=None):
        text = v1_ticket(
            tid, cohort=cohort or f"v1:root:{tid}", executor=executor,
            baseline=self.baseline,
        )
        text = text.replace("run: testrun", "run: oldrun")
        if oracle is not None:
            text = text.replace("`python -m unittest`", oracle)
        text = tickets_mod._set_frontmatter_field(text, "status", status)
        for key, value in LIFECYCLE.items():
            text = tickets_mod._set_frontmatter_field(text, key, value)
        text = text.rstrip("\n") + "\n"
        if handoff:
            text += f"\n## Handoff\n\n{HANDOFF}"
        return text

    def place_source(self, **kwargs):
        run = kwargs.pop("run", "oldrun")
        tid = kwargs.get("tid", "00-root")
        run_dir = self.sink / "tickets" / run
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"{tid}.md"
        path.write_bytes(self.source_text(**kwargs).encode("utf-8"))
        return path

    def reissue(self, *args):
        return run_cmd("reissue", "oldrun", "00-root", *args)

    def placed(self, run="newrun", tid="00-root"):
        return (self.sink / "tickets" / run / f"{tid}.md").read_text(encoding="utf-8")


class ReissueSuccessionTest(ReissueFixture):
    def test_a_blocked_root_reissued_carries_its_predecessor_and_drops_its_lifecycle(self):
        before = self.source_path.read_bytes()
        payload = self.reissue(
            "--run", "newrun",
            "--add-scope", "web/src/smoke.spec.ts",
            "--set", "isolation=required",
        )
        self.assertNotIn("error", payload)
        self.assertEqual(
            str(self.sink / "tickets" / "newrun" / "00-root.md"),
            payload["reissue"]["path"],
        )
        self.assertEqual("Handoff", payload["reissue"]["cite"])
        text = self.placed()
        data = _parse_frontmatter(text)

        self.assertEqual("newrun", data["run"])
        self.assertEqual("pending", data["status"])
        self.assertEqual("v1:pending", data["admission"])
        self.assertEqual("v1:root:00-root", data["cohort"])
        self.assertEqual("required", data["isolation"])
        self.assertEqual("", str(data.get("claimed_by") or ""))
        self.assertEqual("", str(data.get("claimed_at") or ""))
        for key in DROPPED:
            self.assertNotIn(key, data)

        self.assertIn("web/src/smoke.spec.ts", _scope_entries(data["write_scope"]))
        self.assertIn("change:web/src/smoke.spec.ts", _scope_entries(data["mutations"]))
        self.assertIn("scratch/00-root.txt", _scope_entries(data["write_scope"]))

        digest = hashlib.sha256(HANDOFF.strip().encode("utf-8")).hexdigest()
        record = (
            '- input: {"identity":{"kind":"ticket-section","run":"oldrun",'
            f'"section":"Handoff","sha256":"{digest}","ticket":"00-root"}},'
            '"name":"predecessor","type":"identity"}'
        )
        self.assertIn(record, _sections(text)["Fixed inputs"])

        self.assertEqual(
            [], tickets_mod.grade_admission("00-root", text, {"00-root": text})["findings"],
        )
        self.assertEqual(before, self.source_path.read_bytes())

    def test_the_lint_report_of_the_placed_ticket_is_printed(self):
        """A defect the cut carried forward is reported, and exits nonzero.

        The successor is admitted, not judged clean: `new --file` refuses an
        off-contract cut, and lint reports what is merely wrong with an
        on-contract one -- the difference between a ticket that cannot land
        and one whose caller still has a decision to make.
        """
        payload = self.reissue("--run", "newrun")
        report = payload["reissue"]["lint"]
        self.assertEqual(
            str(self.sink / "tickets" / "newrun" / "00-root.md"), report["target"],
        )
        self.assertEqual(
            {"whole-suite-oracle"}, {item["code"] for item in report["findings"]},
        )
        self.assertEqual(1, payload["exit_code"])

    def test_a_successor_with_nothing_left_to_report_exits_zero(self):
        self.source_path = self.place_source(oracle=NARROW_ORACLE)
        payload = self.reissue("--run", "newrun")
        self.assertEqual([], payload["reissue"]["lint"]["findings"], payload)
        self.assertEqual(0, payload["exit_code"])

    def test_a_new_id_renames_the_successor_and_its_fresh_cohort(self):
        payload = self.reissue("--run", "newrun", "--id", "00-root-b")
        self.assertNotIn("error", payload)
        text = self.placed(tid="00-root-b")
        data = _parse_frontmatter(text)
        self.assertEqual("00-root-b", data["id"])
        self.assertEqual("v1:root:00-root-b", data["cohort"])

    def test_cite_result_names_the_result_section_and_its_digest(self):
        payload = self.reissue("--run", "newrun", "--cite", "result")
        self.assertEqual("Result", payload["reissue"]["cite"])
        digest = hashlib.sha256(b"").hexdigest()
        self.assertIn(f'"sha256":"{digest}"', _sections(self.placed())["Fixed inputs"])


if __name__ == "__main__":
    unittest.main()
