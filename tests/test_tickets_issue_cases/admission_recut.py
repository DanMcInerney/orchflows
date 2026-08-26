"""Recut and cohort invalidation cases for v1 admission.

Both paths re-stamp what they rewrite, and every ticket here is a v1 one,
so v1's sentinel is the version-correct value -- taken from the table that
owns it. A v2 candidate's stamp is `StampingTest`'s, in
`tests/test_lifecycle_table.py`.
"""

from .common import *  # noqa: F401,F403
from scripts.tickets_transitions import pending_admission

#: What a v1 ticket's producer stamps, from the table that owns the value.
V1_PENDING = f"admission: {pending_admission(1)}"


def issue_v1(ticket_id: str, cohort: str):
    return run_cmd(
        "new", "testrun", ticket_id, "--executor", "orch-tdd",
        "--objective", f"Change {ticket_id}.", "--criterion", GOOD_CRITERION,
        "--pack", "orch-code-pack", "--isolation", "required",
        "--cohort", cohort,
    )


class RecutAndCohortTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temporary.name)
        self.sink = use_sink(self.tmp)
        self.run_dir = self.sink / "tickets" / "testrun"

    def tearDown(self):
        self.temporary.cleanup()

    def test_amend_demotes_and_invalidates_every_unsealed_cohort_receipt(self):
        cohort = "v1:batch:abcdef123456"
        for ticket_id in ("A", "B"):
            issue_v1(ticket_id, cohort)
        ready = run_cmd("ready", "--run", "testrun")
        self.assertEqual(["A", "B"], [item["id"] for item in ready["ready"]])
        amended = run_cmd(
            "amend", "testrun", "A", "--section", "Objective",
            "--text", "Change A after correction.",
        )
        self.assertNotIn("error", amended)
        for ticket_id in ("A", "B"):
            text = (self.run_dir / f"{ticket_id}.md").read_text(encoding="utf-8")
            self.assertIn("status: pending", text)
            self.assertIn(V1_PENDING, text)

    def test_amend_refuses_a_checked_or_sealed_cohort_without_changing_bytes(self):
        cohort = "v1:batch:abcdef123456"
        for ticket_id in ("A", "B"):
            issue_v1(ticket_id, cohort)
        before = {path.name: path.read_text(encoding="utf-8") for path in self.run_dir.glob("*.md")}
        claimed = run_cmd("claim", "testrun", "B", "--by", "agent-b")
        self.assertIn("claimed", claimed)
        payload = run_cmd("amend", "testrun", "A", "--section", "Objective", "--text", "Too late.")
        self.assertIn("sealed", payload["error"])
        self.assertEqual(before["A.md"], (self.run_dir / "A.md").read_text(encoding="utf-8"))

    def test_recut_converts_v0_and_preserves_executor_sections(self):
        self.run_dir.mkdir(parents=True)
        current = GOOD_TICKET.replace("status: ready", "status: pending").replace("## Result\n", "## Result\n\nold result\n")
        current = current.replace("## Verification\n", "## Verification\n\nold verification\n")
        current = tickets_mod._write_section(
            current, "Context", "- state: canonical conclusion"
        )
        target = self.run_dir / "T1.md"
        target.write_text(current, encoding="utf-8")
        candidate = self.tmp / "candidate.md"
        candidate.write_text(GOOD_TICKET.replace("Add `double(n)`.", "Corrected cut."), encoding="utf-8")
        payload = run_cmd("recut", "testrun", "T1", "--file", candidate)
        self.assertNotIn("error", payload)
        text = target.read_text(encoding="utf-8")
        self.assertIn("status: pending", text)
        self.assertIn(V1_PENDING, text)
        self.assertIn("cohort: v1:ticket:T1", text)
        self.assertIn("Corrected cut.", text)
        self.assertIn("old result", tickets_mod._sections(text)["Result"])
        self.assertIn("old verification", tickets_mod._sections(text)["Verification"])
        self.assertEqual(
            "- state: canonical conclusion", tickets_mod._sections(text)["Context"]
        )

    def test_new_issuance_omits_optional_successor_context(self):
        issue_v1("T1", "v1:ticket:T1")
        sections = tickets_mod._sections(
            (self.run_dir / "T1.md").read_text(encoding="utf-8")
        )
        self.assertNotIn("Context", sections)
        candidate = self.tmp / "malformed-context.md"
        candidate.write_text(
            tickets_mod._write_section(
                GOOD_TICKET.replace("id: T1", "id: T2"), "Context", "[]"
            ),
            encoding="utf-8",
        )
        payload = run_cmd("new", "testrun", "--file", candidate)
        self.assertIn("Context", payload["error"])
        self.assertFalse((self.run_dir / "T2.md").exists())

        source = (ROOT / "scripts" / "tickets_issue.py").read_text(encoding="utf-8")
        legacy_heading = "Car" + "ry"
        self.assertNotIn(f"'{legacy_heading}'", source)
        self.assertNotIn("FILEABLE_EXECUTOR_SECTIONS", source)
        self.assertNotIn("allow_legacy_" + legacy_heading.lower(), source)

    def test_recut_rejects_a_ticket_id_that_traverses_into_another_run(self):
        foreign = self.sink / "tickets" / "other"
        foreign.mkdir(parents=True)
        target = foreign / "T1.md"
        target.write_text(GOOD_TICKET.replace("run: testrun", "run: other"), encoding="utf-8")
        before = target.read_bytes()
        candidate = self.tmp / "candidate.md"
        candidate.write_text(GOOD_TICKET, encoding="utf-8")
        payload = run_cmd("recut", "testrun", "../other/T1", "--file", candidate)
        self.assertIn("ticket id", payload["error"])
        self.assertEqual(before, target.read_bytes())
