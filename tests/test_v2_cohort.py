"""A v2 ticket carries no cohort, and the ruling lands where one is written.

The cohort is v1's freezing mechanism: `cohort_sealed` refuses cut-time
amendment of a member whose cohort has been taken up, and `_canonical_cut`
hashes ticket- and batch-cohort siblings into the v1 receipt.  v2 freezes a
cut by its sealed generation instead -- `root_generation`, `cut_generation`
and `assignment_seal`, bound to the script-owned sealed run-state record --
and its grade says so in both directions: `assignment_payload` names no
cohort among the sealed assignment facets, and the v2 receipt's
`snapshot_ids` carry dependencies only, never cohort siblings.

So a cohort stamped onto a v2 ticket was a required-looking field graded by
nothing.  The ruling is that v2 stamps none.  It lands at the stamping
sites in `scripts/tickets_issue.py`, because that is the only place the
field is written: `new --file`, `recut`, and `amend`'s re-stamp.  A cohort a
v2 file carries is normalized away exactly as one used to be overwritten,
and a `--cohort` the caller states outright is refused rather than dropped
in silence -- a caller who asked for a cohort asked for the mechanism v2
does not have.

`V1CohortUnchangedTest` pins the other half of the ruling: v1 stamping,
defaulting, and refusal are byte-for-byte what they were.
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.tickets_format import _parse_frontmatter  # noqa: E402
from tests.test_tickets_cases.admission_v1 import initialize_git_fixture  # noqa: E402
from tests.test_tickets_cases.common import run_cmd, use_sink  # noqa: E402
from tests.test_tickets_issue_cases.generation_lifecycle import ticket as v2_ticket  # noqa: E402

UNIT_ID = "00-root.01"

V1_TICKET = """---
id: {tid}
run: run
status: pending
admission: v1:pending
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
write_scope: [scripts/example.py]
mutations: [change:scripts/example.py]
isolation: required
bound: 30m
claimed_by:
claimed_at:
---

## Objective

Change one observable artifact.

## Fixed inputs

- input: {{"name":"fixture","type":"literal","value":1}}

## Completion test

- works | oracle: `fixture` | oracle_class: deterministic | provenance: authored-here

## Return fields

status; result

## Result

## Verification

## Feedback

[]

## Risks

[]
"""


class CohortRulingCase(unittest.TestCase):
    """One temporary sink per case, and the two ticket shapes to place into it."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.sink = use_sink(self.tmp)
        self.run_dir = self.sink / "tickets" / "run"
        # `orch-code-pack` input rendering resolves the run-project HEAD, so
        # the fixture directory a dispatch stands in has to be a checkout.
        initialize_git_fixture(self.tmp)

    def write_candidate(self, name, text):
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def place(self, text, *flags, name="candidate.md"):
        candidate = self.write_candidate(name, text)
        return run_cmd(self.tmp, "new", "run", "--file", candidate, *flags)

    def stored(self, ticket_id=UNIT_ID):
        return _parse_frontmatter(
            (self.run_dir / f"{ticket_id}.md").read_text(encoding="utf-8")
        )


class V2CohortRulingTest(CohortRulingCase):
    """Every site that writes a cohort declines to write one onto v2."""

    def test_placing_a_v2_ticket_stamps_no_cohort(self):
        payload = self.place(v2_ticket(UNIT_ID))
        self.assertNotIn("error", payload)
        self.assertNotIn("cohort", self.stored())

    def test_a_cohort_the_v2_file_carries_is_normalized_away(self):
        carried = v2_ticket(UNIT_ID).replace(
            "run: run\n", f"run: run\ncohort: v1:ticket:{UNIT_ID}\n"
        )
        payload = self.place(carried)
        self.assertNotIn("error", payload)
        self.assertNotIn("cohort", self.stored())

    def test_an_explicit_cohort_on_a_v2_ticket_is_refused_and_nothing_is_written(self):
        payload = self.place(v2_ticket(UNIT_ID), "--cohort", "v1:root:00-root")
        self.assertIn("generation seal", payload.get("error", ""))
        self.assertFalse((self.run_dir / f"{UNIT_ID}.md").exists())

    def test_amend_leaves_a_v2_ticket_without_a_cohort(self):
        self.assertNotIn("error", self.place(v2_ticket(UNIT_ID)))
        amended = run_cmd(
            self.tmp, "amend", "run", UNIT_ID,
            "--section", "Objective", "--text", "deliver, corrected",
        )
        self.assertNotIn("error", amended)
        self.assertNotIn("cohort", self.stored())

    def test_recut_leaves_a_v2_ticket_without_a_cohort(self):
        self.assertNotIn("error", self.place(v2_ticket(UNIT_ID)))
        candidate = self.write_candidate(
            "recut.md",
            v2_ticket(UNIT_ID, objective="recut assignment").replace(
                "run: run\n", f"run: run\ncohort: v1:batch:0123456789ab\n"
            ),
        )
        payload = run_cmd(self.tmp, "recut", "run", UNIT_ID, "--file", candidate)
        self.assertNotIn("error", payload)
        self.assertNotIn("cohort", self.stored())


class V1CohortUnchangedTest(CohortRulingCase):
    """v1 keeps the cohort it always had: defaulted, stated, or refused."""

    def test_v1_placement_defaults_states_and_refuses_a_cohort_as_before(self):
        self.assertNotIn("error", self.place(V1_TICKET.format(tid=UNIT_ID)))
        self.assertEqual(f"v1:ticket:{UNIT_ID}", self.stored()["cohort"])

        second = "T2"
        self.assertNotIn("error", self.place(
            V1_TICKET.format(tid=second), "--cohort", "v1:root:00-root", name="second.md",
        ))
        self.assertEqual("v1:root:00-root", self.stored(second)["cohort"])

        refused = self.place(
            V1_TICKET.format(tid="T3"), "--cohort", "nonsense", name="third.md",
        )
        self.assertIn("is not v1:<ticket|root|batch>", refused.get("error", ""))
        self.assertFalse((self.run_dir / "T3.md").exists())

    def test_v1_amend_and_recut_keep_stamping_the_cohort(self):
        self.assertNotIn("error", self.place(V1_TICKET.format(tid=UNIT_ID)))
        amended = run_cmd(
            self.tmp, "amend", "run", UNIT_ID,
            "--section", "Objective", "--text", "Change one observable artifact, again.",
        )
        self.assertNotIn("error", amended)
        self.assertEqual(f"v1:ticket:{UNIT_ID}", self.stored()["cohort"])

        candidate = self.write_candidate(
            "recut.md",
            V1_TICKET.format(tid=UNIT_ID).replace(
                "run: run\n", "run: run\ncohort: v1:root:00-root\n"
            ),
        )
        self.assertNotIn("error", run_cmd(self.tmp, "recut", "run", UNIT_ID, "--file", candidate))
        self.assertEqual("v1:root:00-root", self.stored()["cohort"])


if __name__ == "__main__":
    unittest.main()
