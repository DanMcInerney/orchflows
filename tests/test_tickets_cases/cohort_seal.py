"""Root cohorts seal one member at a time, not all at once.

A `v1:root:<root-id>` cohort is judged on the graded member alone. A
member that is still pending or ready, with no claim and no claim time,
stays correctable however far its siblings have run: under rolling
dispatch the decomposer is still cutting while units complete, and no
running sibling can depend on a pending one -- an incomplete dependency
is refused admission -- so a correction that touches only pending members
cannot reach anything in flight. A stale cohort-member receipt on a
claimed sibling is the receipt layer's concern, not the seal's.

The member's own state is what still seals it: claimed, suspended,
terminal, or carrying a `claimed_at` a lease left behind.

`v1:ticket:` and `v1:batch:` cohorts are untouched -- there any other
member that has been taken up seals the cohort, as it always did.
"""

from .common import *  # noqa: F401,F403
from .admission_v1 import initialize_git_fixture, v1_ticket  # noqa: F401

ROOT_ID = "00-root"
UNIT_ID = "00-root.05"
DONE_ID = "00-root.01"
RUNNING_ID = "00-root.02"
GATE_ID = "00-root.gate.critique.code"
CLAIMED_AT = "2026-08-23T14:00:00Z"

# The frontier mid-run: the decomposer holding the root, one unit
# finished, one in flight, and the cut still to correct -- one pending
# unit and the pending gate stub behind them all.
RUNNING_FRONTIER = {
    ROOT_ID: "claimed",
    DONE_ID: "complete",
    RUNNING_ID: "claimed",
    UNIT_ID: "pending",
    GATE_ID: "pending",
}

_BASELINE = []


def repository_head():
    """This checkout's HEAD, read once: every fixture below wants the same
    baseline, and `v1_ticket` would otherwise shell out per ticket."""

    if not _BASELINE:
        _BASELINE.append(subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip())
    return _BASELINE[0]


def taken_up(text, status="claimed", by="agent-a"):
    """One member as the tracker leaves it once it has been taken up."""

    text = tickets_mod._set_frontmatter_field(text, "status", status)
    if status == "claimed":
        text = tickets_mod._set_frontmatter_field(text, "claimed_by", by)
    return tickets_mod._set_frontmatter_field(text, "claimed_at", CLAIMED_AT)


def members(states, cohort=None, deps=None):
    """One cohort's tickets by id, each at the status ``states`` names."""

    cohort = cohort or tickets_mod.root_cohort(ROOT_ID)
    texts = {}
    for tid, status in states.items():
        text = v1_ticket(
            tid, cohort=cohort, baseline=repository_head(),
            deps=(deps or {}).get(tid, "[]"),
        )
        texts[tid] = text if status in ("pending", "ready") else taken_up(text, status)
        if status == "ready":
            texts[tid] = tickets_mod._set_frontmatter_field(text, "status", "ready")
    return texts


def sealed(texts, ticket_id):
    return tickets_mod.cohort_sealed(ticket_id, texts[ticket_id], texts)


class MemberSealTest(unittest.TestCase):
    """The graded member alone decides a root cohort."""

    def test_a_pending_member_is_open_however_far_its_siblings_have_run(self):
        texts = members(RUNNING_FRONTIER)
        for ticket_id in (UNIT_ID, GATE_ID):
            with self.subTest(ticket=ticket_id):
                self.assertFalse(sealed(texts, ticket_id))

    def test_a_ready_member_is_as_open_as_a_pending_one(self):
        states = dict(RUNNING_FRONTIER, **{UNIT_ID: "ready"})
        self.assertFalse(sealed(members(states), UNIT_ID))

    def test_the_graded_member_seals_its_own_cut_once_it_is_taken_up(self):
        for status in ("claimed", "suspended", "complete", "blocked",
                       "stalled", "limited", "failed"):
            with self.subTest(status=status):
                states = {ROOT_ID: "claimed", UNIT_ID: status, GATE_ID: "pending"}
                self.assertTrue(sealed(members(states), UNIT_ID))

    def test_a_claim_time_the_lease_left_behind_still_seals_the_member(self):
        # `claimed_at` outlives a released claim, and it is the field the
        # seal reads: a pending member carrying one is not open.
        texts = members({ROOT_ID: "claimed", UNIT_ID: "pending"})
        texts[UNIT_ID] = tickets_mod._set_frontmatter_field(
            texts[UNIT_ID], "claimed_at", CLAIMED_AT
        )
        self.assertTrue(sealed(texts, UNIT_ID))

    def test_a_claimed_root_does_not_seal_the_cut_it_is_still_writing(self):
        texts = members({ROOT_ID: "claimed", UNIT_ID: "pending", GATE_ID: "pending"})
        self.assertFalse(sealed(texts, UNIT_ID))
        texts[ROOT_ID] = tickets_mod._set_frontmatter_field(
            texts[ROOT_ID], "claimed_at", CLAIMED_AT
        )
        self.assertFalse(sealed(texts, UNIT_ID))

    def test_ticket_and_batch_cohorts_seal_on_every_member_as_before(self):
        # `v1:ticket:`'s id segment names a real member and a batch digest
        # names none; neither kind is judged on the graded member, so a
        # pending member of one is still sealed by a claimed sibling.
        ticket = members({"T1": "claimed", "T2": "pending"},
                         cohort=tickets_mod.ticket_cohort("T1"))
        self.assertTrue(sealed(ticket, "T2"))
        batch = members({"A": "claimed", "B": "pending"},
                        cohort=tickets_mod.batch_cohort(["A", "B"]))
        self.assertTrue(sealed(batch, "B"))


class RunningFrontierCorrectionTest(unittest.TestCase):
    """The two callers, in the state the reproduction reports."""

    def place(self, tmp, states=None, deps=None):
        initialize_git_fixture(tmp)
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        for tid, text in members(states or RUNNING_FRONTIER, deps=deps).items():
            (run_dir / f"{tid}.md").write_text(text, encoding="utf-8")
        return run_dir

    def untouched(self, run_dir, before):
        """Every member that was in flight is byte-for-byte where it was."""

        for tid, text in before.items():
            self.assertEqual(text, (run_dir / f"{tid}.md").read_text(encoding="utf-8"))

    def test_amend_reaches_a_pending_member_while_its_siblings_run(self):
        for ticket_id in (UNIT_ID, GATE_ID):
            with self.subTest(ticket=ticket_id), tempfile.TemporaryDirectory() as raw:
                tmp = Path(raw)
                run_dir = self.place(tmp)
                before = {
                    tid: (run_dir / f"{tid}.md").read_text(encoding="utf-8")
                    for tid in (DONE_ID, RUNNING_ID, ROOT_ID)
                }
                payload = run_cmd(
                    tmp, "amend", "testrun", ticket_id, "--section", "Objective",
                    "--text", "Change one observable artifact, corrected mid-run.",
                )
                self.assertNotIn("error", payload)
                self.assertIn(
                    "corrected mid-run",
                    (run_dir / f"{ticket_id}.md").read_text(encoding="utf-8"),
                )
                self.untouched(run_dir, before)

    def test_recut_reaches_the_pending_gate_stub_while_its_siblings_run(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = self.place(tmp)
            before = {
                tid: (run_dir / f"{tid}.md").read_text(encoding="utf-8")
                for tid in (DONE_ID, RUNNING_ID, ROOT_ID)
            }
            # what the reproduction recuts for: one more member on the
            # stub's `depends_on`.
            candidate = tmp / "candidate.md"
            candidate.write_text(
                members({GATE_ID: "pending"}, deps={GATE_ID: f"[{UNIT_ID}]"})[GATE_ID],
                encoding="utf-8",
            )
            payload = run_cmd(tmp, "recut", "testrun", GATE_ID, "--file", candidate)
            self.assertNotIn("error", payload)
            self.assertIn(
                f"depends_on: [{UNIT_ID}]",
                (run_dir / f"{GATE_ID}.md").read_text(encoding="utf-8"),
            )
            self.untouched(run_dir, before)

    def test_both_callers_still_refuse_a_member_the_seal_holds(self):
        # A pending member carrying a claim time reaches `cohort_sealed`
        # in both callers -- the guards above it pass -- so this is the
        # refusal that is still the seal's own, by its own message.
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = self.place(tmp)
            path = run_dir / f"{UNIT_ID}.md"
            path.write_text(
                tickets_mod._set_frontmatter_field(
                    path.read_text(encoding="utf-8"), "claimed_at", CLAIMED_AT
                ),
                encoding="utf-8",
            )
            before = path.read_text(encoding="utf-8")
            candidate = tmp / "candidate.md"
            candidate.write_text(members({UNIT_ID: "pending"})[UNIT_ID], encoding="utf-8")
            for args in (
                ("amend", "testrun", UNIT_ID, "--section", "Objective", "--text", "Too late."),
                ("recut", "testrun", UNIT_ID, "--file", candidate),
            ):
                with self.subTest(command=args[0]):
                    payload = run_cmd(tmp, *args)
                    self.assertIn("sealed", payload["error"])
                    self.assertEqual(before, path.read_text(encoding="utf-8"))
