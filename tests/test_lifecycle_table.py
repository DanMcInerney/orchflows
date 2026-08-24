"""The state-times-command table, and the lifecycle commands that read it.

`scripts/tickets_transitions.py` is the one place that answers, for a
ticket status and a lifecycle command, whether the transition is allowed
and which frontmatter fields it sets or blanks. Every refusal a lifecycle
command emits on a refused transition is rendered from those rows, so no
refusal can name a remedy the table forbids.

Two of them did. `set-status pending` wrote only the status field, leaving
`claimed_at` behind; `cohort_sealed` reads that leftover as a taken-up
ticket, so `recut` refused -- while the stale-claim refusal and `grant`'s
widening refusal both recommended exactly `set-status pending, then
recut`. The fix is the blanking; the guard is that the sentences are no
longer written by hand at all.

`TransitionTableTest` and `LifecycleCommandsTest` are this item's.
`StampingTest` grades the version-aware entries, and inherits from
`tests/test_tickets_issue_cases/admission_producers.py` the live cases
for the three sites now stamping through them -- so the entries and their
consumers are graded together here without a second copy of either.
`DraftValidateTest` grades its entry alone: `tickets_generations.py`'s
draft validator is rewired by its own item.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from scripts import tickets_admission, tickets_format, tickets_generations, tickets_transitions
from tests.test_tickets_issue_cases import admission_producers, generation_lifecycle
from tests.test_tickets_cases.admission_v1 import initialize_git_fixture, v1_ticket
from tests.test_tickets_cases.common import backdate, make_tickets, run_cmd, use_sink

#: Any backticked token in a rendered refusal that names a table command.
#: The table's own vocabulary decides which tokens count, so a command
#: added to the table is graded without an edit here.
BACKTICKED = re.compile(r"`([a-z][a-z-]*(?: [a-z-]+)?)`")


def commands_named(text: str) -> set:
    """Every table command a rendered refusal names."""

    return {
        token for token in BACKTICKED.findall(text)
        if token in tickets_transitions.COMMANDS
    }


def chain_commands(status: str, command: str) -> set:
    """The commands the table's own chain for this pair names.

    The refused command itself joins the set only when the refusal actually
    reaches it -- by a chain, or because the table already runs it there and
    the refusal was raised for some other reason. Where the table declines
    to name a remedy at all, a refusal that named one would be the defect.
    """

    path = tickets_transitions.remedy_path(status, command)
    if not path and not tickets_transitions.allows(status, command):
        return set()
    return commands_named(" ".join(path)) | {command}


def age(path: Path) -> None:
    """Put a live claim's lease and its file's motion both far in the past.

    Staleness reads the clock against `claimed_at` and the artifact's own
    motion, so a fixture that only backdates the mtime leaves a claim whose
    bound has not run out, and one that only rewrites `claimed_at` leaves a
    ticket that moved a moment ago.
    """

    path.write_text(
        re.sub(
            r"(?m)^claimed_at: .*$", "claimed_at: 2026-01-01T00:00:00Z",
            path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    backdate(path, 10 * 24 * 60)


def v0_repo(tmp: Path, status: str, **fields) -> Path:
    """A run holding one legacy ticket -- no admission receipt, no cohort."""

    lines = "".join(f"\n{key}: {value}" for key, value in fields.items())
    run_dir = make_tickets(use_sink(tmp) / "tickets" / "testrun", {"T1": (status, "[]")})
    (tmp / ".git").mkdir()
    path = run_dir / "T1.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("bound: 30m", f"bound: 30m{lines}"),
        encoding="utf-8",
    )
    return run_dir


def v1_repo(tmp: Path, ids=("T1",), cohort="v1:root:T1", **kwargs) -> Path:
    """A real git fixture and one admissible v1 ticket per id.

    The default cohort is `v1:root:`, whose seal is read off the graded
    member alone -- so a lease this fixture leaves behind is a seal this
    fixture can observe, which a `v1:ticket:` cohort with no siblings
    could not. Pass a shared cohort and two ids for the other direction:
    a seal a sibling holds, which no lease of T1's own can lift.
    """

    baseline = initialize_git_fixture(tmp)
    run_dir = use_sink(tmp) / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    for tid in ids:
        (run_dir / f"{tid}.md").write_text(
            v1_ticket(tid, cohort=cohort, baseline=baseline, **kwargs), encoding="utf-8"
        )
    return run_dir


class TransitionTableTest(unittest.TestCase):
    """The table itself: rows, the fields they write, and what they allow."""

    def test_the_status_vocabulary_is_the_librarys_own(self):
        self.assertEqual(tuple(sorted(tickets_format.VALID_STATUSES)), tickets_transitions.STATUSES)
        for command in ("claim", "grant", "check", "recut", "set-status pending"):
            with self.subTest(command=command):
                self.assertIn(command, tickets_transitions.COMMANDS)

    def test_claim_runs_only_at_the_admission_boundarys_two_statuses(self):
        for status in tickets_transitions.STATUSES:
            with self.subTest(status=status):
                self.assertEqual(status in ("pending", "ready"), tickets_transitions.allows(status, "claim"))

    def test_grant_and_check_run_only_on_an_item_someone_is_working(self):
        self.assertEqual(frozenset({"claimed", "suspended"}), tickets_transitions.GRANTABLE_STATUSES)
        self.assertEqual(tickets_transitions.GRANTABLE_STATUSES, tickets_transitions.CHECKABLE_STATUSES)
        for status in tickets_transitions.STATUSES:
            for command in ("grant", "check"):
                with self.subTest(status=status, command=command):
                    self.assertEqual(status in tickets_transitions.GRANTABLE_STATUSES, tickets_transitions.allows(status, command))

    def test_set_status_cannot_reach_the_two_statuses_admission_owns(self):
        for target in tickets_transitions.ADMISSION_OWNED_TARGETS:
            with self.subTest(target=target):
                self.assertNotIn(tickets_transitions.set_status_command(target), tickets_transitions.COMMANDS)

    def test_only_the_pending_target_releases_the_lease(self):
        """The blanking this whole item turns on, and its two exceptions.

        `suspended` keeps the lease because a suspended item is still
        someone's; a terminal one keeps it because the worklog orders a run
        by `claimed_at`. Only `pending` puts the item back on offer.
        """

        self.assertEqual(("claimed_by", "claimed_at"), tickets_transitions.LEASE_FIELDS)
        self.assertEqual(tickets_transitions.LEASE_FIELDS, tickets_transitions.set_status_blanks("pending"))
        for target in ("suspended", *tickets_format.TERMINAL_STATES):
            with self.subTest(target=target):
                self.assertEqual((), tickets_transitions.set_status_blanks(target))

    def test_the_chain_out_of_claimed_releases_the_lease_before_anything_else(self):
        """`claim` and `recut` are both refused at `claimed`, and the table
        reaches each by the one status write that frees the lease -- never
        by naming `recut` while the lease is still on the item."""

        for command in ("claim", "recut", "amend"):
            with self.subTest(command=command):
                chain = tickets_transitions.remedy_path("claimed", command)
                self.assertEqual(2, len(chain), chain)
                self.assertIn("`set-status pending`", chain[0])
                self.assertIn("claimed_at", chain[0])
                self.assertIn(f"`{command}`", chain[1])
        self.assertEqual((), tickets_transitions.remedy_path("pending", "claim"))

    def test_a_refusal_names_exactly_the_commands_its_own_chain_visits(self):
        for status in tickets_transitions.STATUSES:
            for command in tickets_transitions.COMMANDS:
                with self.subTest(status=status, command=command):
                    text = tickets_transitions.refusal("subject", command, status)
                    self.assertEqual(chain_commands(status, command), commands_named(text), text)

    def test_the_reader_separates_a_rendered_remedy_from_a_hand_written_one(self):
        """Can-fail: the check above has to react to the sentence that
        caused this item -- a remedy naming `recut` where the table's chain
        for the pair names no such command."""

        expected = chain_commands("claimed", "claim")
        self.assertNotIn("recut", expected)
        forged = (
            tickets_transitions.refusal("subject", "claim", "claimed")
            + " then `recut` it"
        )
        self.assertNotEqual(expected, commands_named(forged))
        self.assertEqual(set(), commands_named("subject: `git rebase` it"))

    def test_a_seal_drops_the_gated_commands_out_of_the_chain(self):
        """The seal is evaluated, not narrated. Under one, `recut` and
        `amend` leave the chain entirely and the successor path is what
        remains -- a caveat in the sentence would still be a caveat the
        caller has to adjudicate, which is how the original text failed."""

        for command in tickets_transitions.SEAL_REFUSED:
            with self.subTest(command=command):
                live = tickets_transitions.remedy_path("claimed", command)
                sealed = tickets_transitions.remedy_path("claimed", command, sealed=True)
                self.assertIn(f"`{command}`", " ".join(live))
                self.assertNotIn(f"`{command}`", " ".join(sealed))
                self.assertEqual({"set-status suspended"}, commands_named(" ".join(sealed)))
        self.assertEqual(
            tickets_transitions.remedy_path("claimed", "claim"),
            tickets_transitions.remedy_path("claimed", "claim", sealed=True),
            "the seal gates recut and amend, and nothing else",
        )

    def test_no_remedy_reopens_an_item_to_grant_or_check_it(self):
        """`grant` and `check` act on an item a child is already executing.
        A chain reaching either by rewriting a status would tell a caller to
        reopen an item to widen it -- and at a terminal status, to reopen a
        verdict the join has already read -- which is what the notes at both
        sites forbid in the same breath. The table names no such remedy."""

        for command in tickets_transitions.NOT_A_REMEDY:
            for status in tickets_transitions.STATUSES:
                if status in tickets_transitions.GRANTABLE_STATUSES:
                    continue
                with self.subTest(status=status, command=command):
                    text = tickets_transitions.refusal("subject", command, status)
                    self.assertEqual((), tickets_transitions.remedy_path(status, command))
                    self.assertEqual(set(), commands_named(text), text)
                    self.assertNotIn("set-status", text)
                    self.assertEqual("subject.", text)

    def test_a_refusal_carries_its_subject_and_its_callers_note(self):
        text = tickets_transitions.refusal(
            "ticket is not claimed (status 'pending')", "grant", "pending",
            note="ticket: /tmp/T1.md",
        )
        self.assertTrue(text.startswith("ticket is not claimed (status 'pending')"))
        self.assertIn("ticket: /tmp/T1.md", text)


class StampingTest(admission_producers.ProducerStampingTest):
    """The version-aware entry `scripts/tickets_issue.py` stamps with, and
    -- inherited -- every producer path that stamps through it live."""

    def test_each_version_stamps_its_own_pending_sentinel(self):
        self.assertEqual(tickets_admission.ADMISSION_PENDING, tickets_transitions.pending_admission(1))
        self.assertEqual(tickets_admission.ADMISSION_V2_PENDING, tickets_transitions.pending_admission(2))
        self.assertNotEqual(
            tickets_transitions.pending_admission(1),
            tickets_transitions.pending_admission(2),
        )

    def test_a_stamp_is_pending_with_the_lease_blanked(self):
        """A freshly stamped ticket has had no execution, so it carries no
        lease -- the blanking `new` and `recut` already write by hand."""

        for version in (1, 2):
            with self.subTest(version=version):
                entry = tickets_transitions.stamp("stamp", version)
                self.assertEqual("pending", entry.status)
                self.assertEqual(
                    tickets_transitions.pending_admission(version), entry.admission
                )
                self.assertEqual(tickets_transitions.LEASE_FIELDS, entry.blanks)


class DraftValidateTest(unittest.TestCase):
    """The entry `scripts/tickets_generations.py` validates a draft against."""

    def test_draft_validate_is_a_v2_entry_only(self):
        entry = tickets_transitions.stamp("draft-validate", 2)
        self.assertEqual(tickets_admission.ADMISSION_V2_PENDING, entry.admission)
        self.assertIsNone(tickets_transitions.stamp("draft-validate", 1))

    def test_a_v2_draft_may_sit_at_any_status_no_execution_has_reached(self):
        entry = tickets_transitions.stamp("draft-validate", 2)
        self.assertEqual(("pending", "ready", "suspended"), entry.draft_statuses)
        for status in entry.draft_statuses:
            with self.subTest(status=status):
                self.assertIn(status, tickets_format.VALID_STATUSES)
                self.assertNotIn(status, tickets_format.TERMINAL_STATES)

    def test_a_claimed_root_is_a_vantage_and_a_claimed_member_is_not(self):
        """Both directions, against the table and against the live command.

        A draft is graded from its root, so a claimed root is the position
        the snapshot is read from -- the route this run's own root took --
        while a claimed member is an execution the draft would be rewriting
        underneath it. The member set stays the entry's own; the root adds
        exactly `claimed` to it, which is why the entry must not carry it.
        """

        self.assertNotIn(
            tickets_transitions.CLAIMED,
            tickets_transitions.stamp("draft-validate", 2).draft_statuses,
        )
        for ticket_id, codes in (("00-root", []), ("00-root.01", ["v2-draft-status"])):
            with self.subTest(ticket=ticket_id), tempfile.TemporaryDirectory() as raw:
                current = dict(generation_lifecycle.snapshot())
                current[ticket_id] = tickets_format._set_frontmatter_field(
                    current[ticket_id], "status", tickets_transitions.CLAIMED)
                findings = tickets_generations._v2_draft_findings("00-root", current)
                self.assertEqual(codes, [item["code"] for item in findings])
                run_dir = use_sink(Path(raw)) / "tickets" / "run"
                run_dir.mkdir(parents=True)
                for tid, text in current.items():
                    (run_dir / f"{tid}.md").write_text(text, encoding="utf-8")
                live = run_cmd(Path(raw), "draft-validate", "run", "00-root")
                self.assertEqual(codes, [item["code"] for item in live.get("findings", [])])
                self.assertEqual(not codes, "draft_validation" in live)


class LifecycleCommandsTest(unittest.TestCase):
    """The live commands, and the sequences their refusals now name."""

    def claimed(self, tmp: Path, **kwargs) -> Path:
        run_dir = v1_repo(tmp, **kwargs)
        self.assertNotIn(
            "error", run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
        )
        return run_dir

    def test_set_status_pending_releases_the_lease(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = self.claimed(tmp)
            self.assertNotIn(
                "error", run_cmd(tmp, "set-status", "testrun", "T1", "pending")
            )
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertIn("status: pending", text)
            self.assertNotIn("agent-a", text)
            for field in tickets_transitions.LEASE_FIELDS:
                with self.subTest(field=field):
                    self.assertIn(f"{field}:", text)
                    self.assertRegex(text, rf"(?m)^{field}:\s*$")

    def test_set_status_suspended_still_keeps_the_lease(self):
        """The blanking is the `pending` row's alone: a suspended item is
        still someone's, and putting it back on offer is a different act."""

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = self.claimed(tmp)
            self.assertNotIn(
                "error", run_cmd(tmp, "set-status", "testrun", "T1", "suspended")
            )
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertIn("claimed_by: agent-a", text)
            self.assertRegex(text, r"(?m)^claimed_at: \S")

    def test_the_sequence_the_stale_claim_refusal_names_runs_end_to_end(self):
        """The proposal's replay: claim, be refused, then run exactly what
        the refusal names. Grading the destination -- the path has to work."""

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = self.claimed(tmp)
            age(run_dir / "T1.md")
            refusal = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")["error"]
            self.assertEqual(chain_commands("claimed", "claim"), commands_named(refusal))
            self.assertIn("claimed_at", refusal)
            self.assertNotIn(
                "error", run_cmd(tmp, "set-status", "testrun", "T1", "pending")
            )
            claimed = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")
            self.assertNotIn("error", claimed)
            self.assertEqual("agent-b", claimed["claimed"]["claimed_by"])

    def test_the_ready_skip_and_the_claim_refusal_speak_with_one_voice(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = self.claimed(tmp)
            age(run_dir / "T1.md")
            skipped = run_cmd(tmp, "ready", "--run", "testrun")["skipped"]
            reasons = [item["reason"] for item in skipped if item["id"] == "T1"]
            self.assertEqual(1, len(reasons), skipped)
            claim = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")["error"]
            for text in (reasons[0], claim):
                with self.subTest(text=text):
                    self.assertEqual(
                        chain_commands("claimed", "claim"), commands_named(text)
                    )

    def test_a_legacy_claimed_ticket_is_not_told_to_recut_in_place(self):
        """`recut` accepts only `pending` and `ready`, so a claimed legacy
        ticket told to `recut` was told to run a command the table refuses.
        Its `ready` sibling keeps naming `recut`, which does run there."""

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = v0_repo(
                tmp, "claimed",
                claimed_by="agent-a", claimed_at="2026-07-18T00:00:00Z",
            )
            age(run_dir / "T1.md")
            refusal = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")["error"]
            self.assertEqual(chain_commands("claimed", "recut"), commands_named(refusal))
            self.assertIn("`set-status pending`", refusal)
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            v0_repo(tmp, "ready")
            ready = run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-b")["error"]
            self.assertEqual(chain_commands("ready", "recut"), commands_named(ready))
            self.assertIn("requires `recut`", ready)

    def test_a_sealed_cohort_member_is_never_sent_through_recut(self):
        """The join's own counterexample, live.

        `grant` was refused on this very run's 00-root.02 while its cohort
        was sealed, and the refusal still named `recut`. The two halves
        below are one fixture apart: the seal is held by a sibling, which
        no release of T1's own lease can lift, and the control is the same
        cohort with that sibling left unclaimed.
        """

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            v1_repo(tmp, ids=("T1", "T2"), cohort="v1:batch:shared")
            for tid, agent in (("T1", "agent-a"), ("T2", "agent-b")):
                self.assertNotIn(
                    "error", run_cmd(tmp, "claim", "testrun", tid, "--by", agent)
                )
            sealed = run_cmd(
                tmp, "grant", "testrun", "T1",
                "--write-scope", "scripts/new.py", "--by", "main",
            )["error"]
            self.assertNotIn("recut", commands_named(sealed))
            self.assertEqual({"set-status suspended"}, commands_named(sealed))
            self.assertIn("successor", sealed)

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            v1_repo(tmp, ids=("T1", "T2"), cohort="v1:batch:shared")
            self.assertNotIn(
                "error", run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            )
            live = run_cmd(
                tmp, "grant", "testrun", "T1",
                "--write-scope", "scripts/new.py", "--by", "main",
            )["error"]
            self.assertEqual(chain_commands("claimed", "recut"), commands_named(live))

    def test_the_not_claimed_refusals_never_offer_to_reopen_the_item(self):
        """Live, at a terminal status: the verdict has been read, so neither
        refusal may offer a status rewrite that puts the item back in flight.
        Each carries its own note instead, which is the real remedy."""

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = self.claimed(tmp)
            self.assertNotIn(
                "error", run_cmd(tmp, "set-status", "testrun", "T1", "complete")
            )
            for command, extra in (("grant", ("--write-scope", "scripts/new.py")),
                                   ("check", ())):
                with self.subTest(command=command):
                    text = run_cmd(
                        tmp, command, "testrun", "T1", *extra, "--by", "main",
                    )["error"]
                    self.assertIn("not claimed", text)
                    self.assertEqual(set(), commands_named(text), text)
                    self.assertNotIn("set-status", text)
            # And the third live half of the blanking rule: `pending` releases
            # the lease, `suspended` keeps it, and a terminal status keeps it
            # too -- the worklog orders a run by `claimed_at`.
            closed = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertIn("status: complete", closed)
            self.assertIn("claimed_by: agent-a", closed)
            self.assertRegex(closed, r"(?m)^claimed_at: \S")

    def test_the_grant_widening_refusal_names_a_sequence_the_seal_allows(self):
        """`grant` refuses to invent an operation on a planned v1 item. The
        remedy it names has to survive the cohort seal, which reads a
        leftover `claimed_at` as a ticket somebody has taken up."""

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = self.claimed(tmp)
            refusal = run_cmd(
                tmp, "grant", "testrun", "T1",
                "--write-scope", "scripts/new.py", "--by", "main",
            )["error"]
            self.assertIn("explicit mutation", refusal)
            self.assertIn("suspend", refusal.lower())
            self.assertIn("`set-status pending`", refusal)
            for named in commands_named(refusal):
                with self.subTest(named=named):
                    self.assertTrue(
                        tickets_transitions.allows("claimed", named)
                        or named in chain_commands("claimed", "recut"),
                        refusal,
                    )
            self.assertNotIn(
                "error", run_cmd(tmp, "set-status", "testrun", "T1", "pending")
            )
            self.assertFalse(
                tickets_admission.cohort_sealed(
                    "T1", (run_dir / "T1.md").read_text(encoding="utf-8"), {}
                ),
                "the lease leftover still seals the cohort the refusal routes through",
            )


if __name__ == "__main__":
    unittest.main()
