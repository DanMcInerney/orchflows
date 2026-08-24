"""Guidance a refusal derives rather than writes: remedies and arithmetic.

Three refusal families that each cost a caller a blind round-trip, and each
for the same reason -- the refusal held the facts that would have named the
next act, and spent them on prose instead.

The remedy half: a refusal that recommends a command names it from
`scripts/tickets_transitions.py`'s rows, so it cannot send a caller at a
transition the table refuses. The measured failure was a grant refusal
recommending `set-status pending, then recut` while the lease-leftover
cohort seal refused exactly that recut.

The arithmetic half: the instruction-ceiling refusal already counts every
part it grades, and printed only the total -- so a cutter over the ceiling
learned that the ticket was too long and not which section was long. The
measured cost was two blind recut round-trips per over-ceiling ticket.

The sentinel half: the refusal that should not have existed at all. A
generator prefilled an executor-owned section with the empty-collection
marker, and the filing law then protected the marker as though a writer
had written it -- so the executor's *first* real content was refused, once
per executor per run. The facts that would have named the next act were the
section's own bytes, and the guard never compared them.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import tickets as tickets_mod
from scripts import tickets_ceiling, tickets_format, tickets_transitions
from scripts import tickets_markdown, tickets_result
from scripts.tickets_dispatch import _dispatch
from tests.test_lifecycle_table import chain_commands, commands_named, v1_repo
from tests.test_tickets_cases.common import run_cmd
from tests.test_tickets_issue_cases.common import ceiling_ticket
from tests.test_tickets_issue_cases.generation_lifecycle import snapshot

AMEND = ("amend", "testrun", "T1", "--section", "Objective", "--text", "A new objective.")
CRITERION = "holds | oracle: `true` | oracle_class: deterministic | provenance: authored-here"


class InstructionBreakdownTest(unittest.TestCase):
    """The counter reports its parts, and the parts are the count."""

    def test_the_breakdown_names_every_graded_part(self):
        parts = dict(tickets_ceiling.instruction_breakdown(ceiling_ticket(320)))
        for name in tickets_ceiling.INSTRUCTION_SECTIONS:
            with self.subTest(name):
                self.assertIn(name, parts)
        self.assertIn(tickets_ceiling.EXCLUDED_ACTIONS_LABEL, parts)

    def test_the_parts_sum_to_the_total_the_ceiling_grades(self):
        """The breakdown is the counter's own arithmetic, not a second one.

        A per-section report that did not add up to the graded total would
        send a cutter to trim a section the ceiling never charged.
        """

        for total in (120, 300, 320, 460):
            text = ceiling_ticket(total)
            with self.subTest(total):
                parts = tickets_ceiling.instruction_breakdown(text)
                self.assertEqual(total, sum(count for _, count in parts))
                self.assertEqual(total, tickets_ceiling.instruction_words(text))

    def test_fixed_inputs_stay_free_of_every_part(self):
        """`## Fixed inputs` is evidence, and no part may charge for it."""

        padded = ceiling_ticket(320, inputs="- " + " ".join(["identity"] * 400))
        self.assertEqual(
            tickets_ceiling.instruction_breakdown(ceiling_ticket(320)),
            tickets_ceiling.instruction_breakdown(padded),
        )

    def test_the_breakdown_leads_with_the_section_worth_cutting(self):
        """Largest first: the first name printed is the one to shorten."""

        counts = [c for _, c in tickets_ceiling.instruction_breakdown(ceiling_ticket(320))]
        self.assertEqual(sorted(counts, reverse=True), counts)

    def test_the_counter_keeps_its_old_holders(self):
        """`tickets_format` and the facade still answer for the counter."""

        text = ceiling_ticket(320)
        self.assertEqual(320, tickets_format.instruction_words(text))
        self.assertEqual(320, tickets_mod.instruction_words(text))
        self.assertEqual(
            tickets_ceiling.INSTRUCTION_BUDGET, tickets_mod.INSTRUCTION_BUDGET
        )


class CeilingArithmeticTest(unittest.TestCase):
    """What an over-ceiling refusal prints of the sum it already has."""

    def test_the_arithmetic_prints_every_part_and_the_total(self):
        text = ceiling_ticket(322)
        rendered = tickets_ceiling.ceiling_arithmetic(text)
        for name, count in tickets_ceiling.instruction_breakdown(text):
            with self.subTest(name):
                self.assertIn(f"{name} {count}", rendered)
        self.assertIn("= 322", rendered)

    def test_the_refusal_carries_the_arithmetic_and_the_overage(self):
        over = tickets_ceiling.INSTRUCTION_BUDGET + 22
        sentence = tickets_ceiling.ceiling_sentence("the ticket", ceiling_ticket(over))
        self.assertIsNotNone(sentence)
        self.assertIn(tickets_ceiling.ceiling_arithmetic(ceiling_ticket(over)), sentence)
        self.assertIn("22 over", sentence)
        for kept in (str(over), "rules/token-economy.md", "two items"):
            with self.subTest(kept):
                self.assertIn(kept, sentence)

    def test_an_instruction_at_the_ceiling_draws_no_sentence(self):
        at = tickets_ceiling.INSTRUCTION_BUDGET
        self.assertIsNone(tickets_ceiling.ceiling_sentence("the ticket", ceiling_ticket(at)))

    def test_the_rendered_order_is_the_breakdowns_order(self):
        """Largest-first survives rendering, which is where it is read.

        `instruction_breakdown` sorting largest-first is pinned next door,
        but a caller never sees the tuple -- it sees this string, and a
        renderer that re-ordered while re-summing correctly would still
        send "cut the part named first" at the smallest part. The two
        assertions next door cannot see that: one checks membership per
        part, and the other compares the sentence against this same
        renderer, so a re-ordering moves both sides together.
        """

        for total in (312, 322, 460):
            text = ceiling_ticket(total)
            with self.subTest(total):
                head, _, printed = tickets_ceiling.ceiling_arithmetic(text).rpartition(" = ")
                rendered = []
                for term in head.split(" + "):
                    name, _, count = term.rpartition(" ")
                    rendered.append((name, int(count)))
                counts = [count for _, count in rendered]
                self.assertEqual(sorted(counts, reverse=True), counts)
                self.assertEqual(list(tickets_ceiling.instruction_breakdown(text)), rendered)
                self.assertEqual(tickets_ceiling.instruction_words(text), int(printed))


class CutTimeRemedyTest(unittest.TestCase):
    """`amend` and `recut` refusals, and whether the chain they name runs.

    Both were written by hand while `grant` and `claim` next door rendered
    theirs, so both restated the table from memory -- including, at a
    claimed ticket, the untabled `take the claim back first`.
    """

    def test_the_claimed_amend_chain_runs_under_sibling_held_leases(self):
        """A root cohort is judged on the graded member alone.

        Observed live: a member of `v1:root:00-root` was refused with the
        release-then-recut chain while six sibling leases were held, and
        running the chain succeeded. The seal is per-member, so sibling
        leases are not the caller's problem and the chain is honest --
        which this pins by executing it, not by reading it.
        """

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            v1_repo(tmp, ids=("T1", "T2", "T3"), cohort="v1:root:R")
            for tid in ("T1", "T2", "T3"):
                self.assertNotIn(
                    "error", run_cmd(tmp, "claim", "testrun", tid, "--by", f"agent-{tid}")
                )
            refused = run_cmd(tmp, *AMEND)["error"]
            self.assertEqual(chain_commands("claimed", "amend"), commands_named(refused))
            for step in ("set-status", "testrun", "T1", "pending"), AMEND:
                with self.subTest(step[0]):
                    self.assertNotIn("error", run_cmd(tmp, *step))

    def test_the_sealed_amend_refusal_declines_the_chain_the_seal_refuses(self):
        """The narrower state the old wording really described.

        A `v1:batch:` cohort seals on any other member, so releasing this
        item's own lease cannot lift it -- and the release-then-amend chain
        that is honest one fixture over is forbidden here. The refusal must
        name the successor path instead, and the proof that it must is the
        second half: the chain, run anyway, is still refused.
        """

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            v1_repo(tmp, ids=("T1", "T2"), cohort="v1:batch:shared")
            for tid, agent in (("T1", "agent-a"), ("T2", "agent-b")):
                self.assertNotIn(
                    "error", run_cmd(tmp, "claim", "testrun", tid, "--by", agent)
                )
            refused = run_cmd(tmp, *AMEND)["error"]
            self.assertEqual({"set-status suspended"}, commands_named(refused))
            self.assertIn("successor", refused)
            self.assertNotIn(
                "error", run_cmd(tmp, "set-status", "testrun", "T1", "pending")
            )
            self.assertIn("error", run_cmd(tmp, *AMEND))

    def test_the_claimed_recut_refusal_names_the_chain_the_table_runs(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            v1_repo(tmp, ids=("T1",), cohort="v1:root:T1")
            self.assertNotIn(
                "error", run_cmd(tmp, "claim", "testrun", "T1", "--by", "agent-a")
            )
            candidate = tmp / "candidate.md"
            candidate.write_text("---\nid: T1\nrun: testrun\n---\n", encoding="utf-8")
            refused = run_cmd(
                tmp, "recut", "testrun", "T1", "--file", str(candidate)
            )["error"]
            self.assertEqual(chain_commands("claimed", "recut"), commands_named(refused))


class NotARemedyTest(unittest.TestCase):
    """The correction that must not come back (95175a7).

    `grant` and `check` act on an item a child is executing; reaching either
    by rewriting a status reopens an item rather than repairing one, and at
    a terminal status it reopens a verdict the join has already read.
    """

    def test_no_status_write_is_offered_as_a_route_to_grant_or_check(self):
        for command in tickets_transitions.NOT_A_REMEDY:
            for status in tickets_transitions.STATUSES:
                with self.subTest(command=command, status=status):
                    self.assertEqual(
                        (), tickets_transitions.remedy_path(status, command)
                    )
                    self.assertNotIn(
                        "set-status",
                        tickets_transitions.refusal("subject", command, status),
                    )


class SentinelIsNotContentTest(unittest.TestCase):
    """The placeholder a generator writes into a section it then protects.

    Five refusal round-trips across three projects in one cycle, all one
    shape: the generator prefills `## Risks` with the empty-collection
    marker, the sealed (v2) filing law makes an executor-owned section
    append-only, and the executor's first real content is then refused --
    `--replace` outright, and `--append` by succeeding and leaving a
    section that reads `[]` above the risk it just listed. The packet said
    the marker fills only an *empty* section while the API declined to
    treat its own marker as empty.

    One sentence removes both faces: the sentinel is not content, so the
    first real write consumes it whatever flag carries it. `result_sections
    .ResultOverwriteTest` already held exactly that for the bare write; the
    law here is that same one, told to the two flags that carry a write
    past that guard. The comparison is byte equality against the single
    constant, so a near miss is content and keeps every protection -- which
    is what makes the trap unconstructible rather than merely narrower.
    """

    CONTENT = "a real risk the executor found"

    def sealed(self, directory):
        """One sealed, claimed v2 ticket in `directory`'s sink."""

        run_dir = Path(directory) / "tickets" / "run"
        run_dir.mkdir(parents=True)
        for ticket_id, value in snapshot().items():
            (run_dir / f"{ticket_id}.md").write_text(value, encoding="utf-8")
        drafted = _dispatch(["draft-validate", "run", "00-root"])
        _dispatch(["seal", "run", "00-root", "--cut-generation",
                   drafted["draft_validation"]["cut_generation"]])
        _dispatch(["claim", "run", "00-root.01", "--by", "worker"])
        return run_dir / "00-root.01.md"

    def body(self, ticket, section="Risks"):
        return tickets_format._sections(ticket.read_text(encoding="utf-8"))[section]

    def test_the_generator_prefills_the_one_sentinel_the_filing_law_names(self):
        """The two ends of the trap, pinned to one constant.

        The generators are not this module's to change, so nothing but this
        stops `new` from prefilling a marker the filing law would go back to
        reading as content -- which is the trap, rebuilt from the other end.
        """

        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                self.assertNotIn("error", _dispatch([
                    "new", "run", "T1", "--executor", "orch-tdd",
                    "--objective", "deliver", "--criterion", CRITERION,
                ]))
                sections = tickets_format._sections(
                    (Path(directory) / "tickets" / "run" / "T1.md").read_text(encoding="utf-8")
                )
                for name in ("Feedback", "Risks"):
                    with self.subTest(name):
                        self.assertEqual(tickets_markdown.SECTION_SENTINEL, sections[name])

    def test_the_first_real_write_consumes_the_sentinel_under_every_flag(self):
        """No flag, `--append`, `--replace`: one law, and no round-trip.

        `--append` is the flag the packet recommends and the one that used
        to succeed dishonestly, so the assertion is equality rather than
        membership: nothing of the marker survives above the content. The
        reported mode is `write` throughout, because that is what happened
        -- there was nothing to append to and nothing real to replace.
        """

        for flag in ((), ("--append",), ("--replace",)):
            with self.subTest(flag=" ".join(flag) or "no flag"):
                with tempfile.TemporaryDirectory() as directory:
                    with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                        ticket = self.sealed(directory)
                        written = _dispatch([
                            "result", "run", "00-root.01", "--section", "Risks",
                            "--text", self.CONTENT, *flag,
                        ])
                        self.assertNotIn("error", written)
                        self.assertEqual("write", written["result"]["mode"])
                        self.assertEqual(self.CONTENT, self.body(ticket))

    def test_a_section_holding_real_content_keeps_every_protection(self):
        """The exception composes with the guards rather than widening them.

        checker-c06 proved both directions live: `--append` is lawful, and
        a non-append write onto existing content is refused. Under a seal
        `--replace` is refused too. All three still hold once the section
        is real, which is the half a looser sentinel test cannot see.
        """

        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                ticket = self.sealed(directory)
                _dispatch(["result", "run", "00-root.01", "--section", "Risks",
                           "--text", self.CONTENT])
                refused = _dispatch(["result", "run", "00-root.01", "--section", "Risks",
                                     "--text", "second", "--replace"])
                self.assertIn("append-only", refused["error"])
                bare = _dispatch(["result", "run", "00-root.01", "--section", "Risks",
                                  "--text", "second"])
                self.assertIn("already carries content", bare["error"])
                appended = _dispatch(["result", "run", "00-root.01", "--section", "Risks",
                                      "--text", "second", "--append"])
                self.assertNotIn("error", appended)
                self.assertEqual(f"{self.CONTENT}\n\nsecond", self.body(ticket))

    def test_an_empty_section_is_not_the_sentinel_and_stays_append_only(self):
        """`exactly when`: the exception is the marker, not emptiness.

        A guard that asked "is there anything worth protecting" rather than
        "are these the sentinel's bytes" would open `--replace` on every
        section a cut leaves blank. `--append` is the lawful path there,
        so closing this costs the caller nothing.
        """

        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                ticket = self.sealed(directory)
                self.assertEqual("", self.body(ticket, "Verification"))
                refused = _dispatch(["result", "run", "00-root.01", "--section",
                                     "Verification", "--text", "a pass", "--replace"])
                self.assertIn("append-only", refused["error"])
                self.assertNotIn("error", _dispatch([
                    "result", "run", "00-root.01", "--section", "Verification",
                    "--text", "a pass", "--append",
                ]))
                self.assertEqual("a pass", self.body(ticket, "Verification"))

    def test_only_the_exact_sentinel_bytes_are_the_exception(self):
        """A near miss is content, and a guard that fuzzed would hand
        `--replace` a section a writer had already written.

        Each body here is installed through the public verb -- the bare
        write the sentinel makes lawful -- so the panel proves the two
        halves in one pass: the marker is consumed, and what replaced it
        is protected immediately.
        """

        for near in ("[ ]", "[]]", "[[]]", "- []", "[] and one more", "None"):
            with self.subTest(body=near):
                with tempfile.TemporaryDirectory() as directory:
                    with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                        ticket = self.sealed(directory)
                        self.assertNotIn("error", _dispatch([
                            "result", "run", "00-root.01", "--section", "Risks",
                            "--text", near,
                        ]))
                        self.assertEqual(near, self.body(ticket))
                        refused = _dispatch(["result", "run", "00-root.01", "--section",
                                             "Risks", "--text", "later", "--replace"])
                        self.assertIn("append-only", refused["error"])
                        self.assertEqual(near, self.body(ticket))

    def test_the_help_states_the_append_only_law_the_command_enforces(self):
        """The usage line a refusal prints says what the refusal will do.

        The recorded round-trips read a usage line that named the two flags
        and neither the law governing them nor the marker that law excepts,
        so a caller learned both by being refused. The second half is the
        one that matters: the law has to travel on the refusals.
        """

        for phrase in ("append-only", tickets_markdown.SECTION_SENTINEL):
            with self.subTest(phrase):
                self.assertIn(phrase, tickets_result.RESULT_USAGE)
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                self.sealed(directory)
                refused = _dispatch(["result", "run", "00-root.01",
                                     "--section", "Risks"])["error"]
                self.assertIn(tickets_result.RESULT_USAGE, refused)

    def test_the_filing_law_names_the_sentinel_rather_than_spelling_it(self):
        """One holder, so the marker cannot drift between its readers.

        The format owner states it; the filing law imports it. A literal
        spelled here again is how the generator and the guard came to
        disagree in the first place.
        """

        lines = Path(tickets_result.__file__).read_text(encoding="utf-8").splitlines()
        self.assertTrue(any("SECTION_SENTINEL" in line for line in lines))
        for spelled in ("'[]'", '"[]"'):
            with self.subTest(spelled):
                self.assertEqual([], [line for line in lines if spelled in line])


if __name__ == "__main__":
    unittest.main()
