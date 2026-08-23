"""`packet --executor orch-critique` refuses where verification §10 exempts.

An all-pre-existing completion test is itself one of that section's ordinary
independence paths, and exactly one path enters an item — so the checker
packet on such a ticket is a child dispatched against an exemption the cut
already took. orch-frontier has said so in prose since its first version
("For gate-deferred, already checked, or pre-existing-only tickets, never
emit it"); only the first two clauses had a refusal behind them.

Self-contained by write scope: the shared case chain under
`tests/test_tickets_cases/` is another item's to edit in this run, so the
ticket bodies and the sink fixture here are built from `common`'s primitives
alone rather than by extending that chain's fixtures.
"""

import tempfile
import unittest
from pathlib import Path

from tests.test_tickets_cases.common import run_cmd, run_full, use_sink

REFUSAL = "checker not required: every criterion carries provenance: pre-existing"

PRE_EXISTING_TICKET = """---
id: T1
run: testrun
status: claimed
executor: orch-tdd
pack: orch-code-pack
depends_on: []
isolation: required
write_scope: scratch/t1.txt
bound: 30m
claimed_by: agent-a
claimed_at: 2099-01-01T00:00:00Z
---

## Objective

Add `double(n)`.

## Fixed inputs

None.

## Completion test

- the existing suite stays green | oracle: `python -m unittest` | oracle_class: deterministic | provenance: pre-existing
- the change introduces no whitespace defect | oracle: `git diff --check` | oracle_class: deterministic | provenance: pre-existing

## Return fields

status, changed_artifacts, verification.
"""

AUTHORED_HERE_TICKET = PRE_EXISTING_TICKET.replace(
    "`git diff --check` | oracle_class: deterministic | provenance: pre-existing",
    "`git diff --check` | oracle_class: deterministic | provenance: authored-here",
)
UNDECLARED_TICKET = PRE_EXISTING_TICKET.replace(" | provenance: pre-existing", "")
CHECKER_TICKET = PRE_EXISTING_TICKET.replace(
    "executor: orch-tdd", "executor: orch-tdd\nindependence: checker"
)
GATE_TICKET = PRE_EXISTING_TICKET.replace(
    "executor: orch-tdd", "executor: orch-tdd\nindependence: gate"
)
GATE_ROOT_TICKET = PRE_EXISTING_TICKET.replace(
    "executor: orch-tdd", "executor: orch-decompose\nindependence: gate"
)


def make_repo(tmp: Path, body: str) -> Path:
    """A checkout at ``tmp`` and one claimed ticket in this test's own sink."""

    (tmp / ".git").mkdir()
    run_dir = use_sink(tmp) / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    path = run_dir / "T1.md"
    path.write_text(body, encoding="utf-8")
    return path


class TestCheckerNotDispatchedWhenSectionTenExempts(unittest.TestCase):
    """The refusal, and each direction it must not reach."""

    def packet(self, tmp: Path, *extra):
        return run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main", *extra)

    def test_an_all_pre_existing_ticket_is_refused_the_checker_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = make_repo(tmp, PRE_EXISTING_TICKET)
            before = path.read_bytes()
            payload = self.packet(tmp, "--executor", "orch-critique")
            self.assertIn(REFUSAL, payload.get("error", ""), payload)
            # the refusal names the rule, never only the condition
            self.assertIn("verification.md §10", payload["error"])
            self.assertNotIn("packet", payload)
            self.assertEqual(before, path.read_bytes())

    def test_the_refusal_is_a_non_zero_exit_across_the_process_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, PRE_EXISTING_TICKET)
            completed = run_full(
                tmp, "packet", "testrun", "T1", "--reply-to", "main",
                "--executor", "orch-critique",
            )
            self.assertNotEqual(0, completed.returncode, completed.stdout)
            self.assertIn(REFUSAL, completed.stdout)

    def test_an_explicit_independence_checker_is_refused_the_same_way(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, CHECKER_TICKET)
            payload = self.packet(tmp, "--executor", "orch-critique")
            self.assertIn(REFUSAL, payload.get("error", ""), payload)

    def test_the_same_ticket_still_gets_its_own_executor_packet(self):
        """The exemption is of the further §10 child, never of the work."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, PRE_EXISTING_TICKET)
            packet = self.packet(tmp)["packet"]
            self.assertEqual("orch-tdd", packet["executor"])
            self.assertIn("Apply skill orch-tdd", packet["prompt"])

    def test_one_authored_here_criterion_still_issues_the_checker_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, AUTHORED_HERE_TICKET)
            packet = self.packet(tmp, "--executor", "orch-critique")["packet"]
            self.assertEqual("orch-critique", packet["executor"])
            self.assertIn("Apply skill orch-critique", packet["prompt"])

    def test_a_criterion_declaring_no_provenance_still_issues_it(self):
        """`provenance` is optional (contracts/work-item.md), and an absent
        one is not a claim that the oracle predates the item: the exemption
        is read off what the ticket carries, never off what it omits."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, UNDECLARED_TICKET)
            packet = self.packet(tmp, "--executor", "orch-critique")["packet"]
            self.assertEqual("orch-critique", packet["executor"])

    def test_the_re_verifier_packet_is_unchanged(self):
        """§10's other further child re-verifies a checked result; what
        exempts the checker says nothing about it."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, PRE_EXISTING_TICKET)
            packet = self.packet(tmp, "--executor", "orch-verify")["packet"]
            self.assertEqual("orch-verify", packet["executor"])

    def test_gate_deferred_behaviour_is_unchanged(self):
        """A gate-deferred ticket is refused for its own reason and with its
        own message, both further children alike."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, GATE_TICKET)
            for executor in ("orch-critique", "orch-verify"):
                with self.subTest(executor=executor):
                    payload = self.packet(tmp, "--executor", executor)
                    self.assertIn("downstream gate", payload.get("error", ""), payload)
                    self.assertNotIn(REFUSAL, payload["error"])

    def test_a_gate_root_still_reaches_its_cut_reader(self):
        """`independence` is the load-bearing half of the condition only on a
        root: `gate` is the one value that is not `checker`, and the branch
        above returns for every *non-root* ticket carrying it, so the case
        above passes whether the condition reads `independence` or not. The
        root is where it decides — contracts/work-item.md gives every root
        `independence: gate`, and the cut reader's lens is the issued subtree,
        never the root's own completion test, however that test is sourced."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, GATE_ROOT_TICKET)
            payload = self.packet(tmp, "--executor", "orch-critique")
            self.assertNotIn(REFUSAL, payload.get("error", ""), payload)
            self.assertIn("subtree ticket yet", payload["error"])


if __name__ == "__main__":
    unittest.main()
