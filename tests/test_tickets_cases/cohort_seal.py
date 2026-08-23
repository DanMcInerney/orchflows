"""Root cohorts: a decomposer's own claim does not seal the cut it holds.

A cohort of the form ``v1:root:<root-id>`` is read as open against the
member whose id is ``<root-id>``: the decomposer holds that claim by
definition for as long as it is cutting and correcting, so counting it
would freeze the cut while it is still being written. Every other member
seals exactly as before, and ``v1:ticket:`` and ``v1:batch:`` cohorts --
whose id segment is a ticket id and a digest respectively -- are
untouched.
"""

from .common import *  # noqa: F401,F403
from .admission_v1 import initialize_git_fixture, v1_ticket  # noqa: F401

ROOT_ID = "00-root"
UNIT_ID = "00-root.01"
SIBLING_ID = "00-root.02"
CLAIMED_AT = "2026-08-23T14:00:00Z"

_BASELINE = []


def repository_head():
    """This checkout's HEAD, read once: every fixture below wants the same
    baseline, and `v1_ticket` would otherwise shell out per ticket."""

    if not _BASELINE:
        _BASELINE.append(subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip())
    return _BASELINE[0]


def claimed(text, by="decomposer"):
    text = tickets_mod._set_frontmatter_field(text, "status", "claimed")
    text = tickets_mod._set_frontmatter_field(text, "claimed_by", by)
    return tickets_mod._set_frontmatter_field(text, "claimed_at", CLAIMED_AT)


def members(ids, cohort, claims=()):
    """One cohort's tickets by id, with ``claims`` claimed and the rest
    pending."""

    texts = {
        tid: v1_ticket(tid, cohort=cohort, baseline=repository_head())
        for tid in ids
    }
    for tid in claims:
        texts[tid] = claimed(texts[tid])
    return texts


class RootCohortSealTest(unittest.TestCase):
    def root_cohort_members(self, claims=()):
        return members(
            (ROOT_ID, UNIT_ID, SIBLING_ID),
            tickets_mod.root_cohort(ROOT_ID),
            claims,
        )

    def sealed(self, texts, ticket_id=UNIT_ID):
        return tickets_mod.cohort_sealed(ticket_id, texts[ticket_id], texts)

    def test_a_claimed_root_does_not_seal_its_own_pending_cut(self):
        self.assertFalse(self.sealed(self.root_cohort_members([ROOT_ID])))

    def test_a_root_carrying_only_claimed_at_does_not_seal_either(self):
        texts = self.root_cohort_members()
        texts[ROOT_ID] = tickets_mod._set_frontmatter_field(
            texts[ROOT_ID], "claimed_at", CLAIMED_AT
        )
        self.assertFalse(self.sealed(texts))

    def test_any_non_root_member_still_seals_the_root_cohort(self):
        for field, value in (("status", "claimed"), ("claimed_at", CLAIMED_AT)):
            with self.subTest(field=field):
                texts = self.root_cohort_members([ROOT_ID])
                texts[SIBLING_ID] = tickets_mod._set_frontmatter_field(
                    texts[SIBLING_ID], field, value
                )
                self.assertTrue(self.sealed(texts))

    def test_a_claimed_root_is_itself_still_sealed_by_a_claimed_unit(self):
        texts = self.root_cohort_members([ROOT_ID, SIBLING_ID])
        self.assertTrue(self.sealed(texts, ROOT_ID))
        self.assertFalse(self.sealed(self.root_cohort_members([ROOT_ID]), ROOT_ID))

    def test_ticket_and_batch_cohorts_seal_on_every_member_as_before(self):
        # `v1:ticket:T1`'s id segment names a real member, and a batch
        # digest names none: neither is exempt from sealing the cohort.
        ticket = members(("T1", "T2"), tickets_mod.ticket_cohort("T1"), ["T1"])
        self.assertTrue(tickets_mod.cohort_sealed("T2", ticket["T2"], ticket))
        ids = ("A", "B")
        batch = members(ids, tickets_mod.batch_cohort(ids), ["A"])
        self.assertTrue(tickets_mod.cohort_sealed("B", batch["B"], batch))


class RootCohortAmendTest(unittest.TestCase):
    """The refusal the defect produced, at the caller that produced it."""

    def place_root_cut(self, tmp, claims=(ROOT_ID,)):
        initialize_git_fixture(tmp)
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        texts = members(
            (ROOT_ID, UNIT_ID, SIBLING_ID),
            tickets_mod.root_cohort(ROOT_ID),
            claims,
        )
        for tid, text in texts.items():
            (run_dir / f"{tid}.md").write_text(text, encoding="utf-8")
        return run_dir

    def test_amend_reaches_a_pending_unit_of_a_claimed_root(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = self.place_root_cut(tmp)
            before = (run_dir / f"{ROOT_ID}.md").read_text(encoding="utf-8")
            payload = run_cmd(
                tmp, "amend", "testrun", UNIT_ID, "--section", "Objective",
                "--text", "Change one observable artifact, corrected.",
            )
            self.assertNotIn("error", payload)
            self.assertIn(
                "corrected", (run_dir / f"{UNIT_ID}.md").read_text(encoding="utf-8")
            )
            self.assertEqual(before, (run_dir / f"{ROOT_ID}.md").read_text(encoding="utf-8"))

    def test_amend_still_refuses_once_a_unit_of_that_root_is_claimed(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = self.place_root_cut(tmp, claims=(ROOT_ID, SIBLING_ID))
            before = (run_dir / f"{UNIT_ID}.md").read_text(encoding="utf-8")
            payload = run_cmd(
                tmp, "amend", "testrun", UNIT_ID, "--section", "Objective",
                "--text", "Change one observable artifact, corrected.",
            )
            self.assertIn("sealed", payload["error"])
            self.assertEqual(before, (run_dir / f"{UNIT_ID}.md").read_text(encoding="utf-8"))
