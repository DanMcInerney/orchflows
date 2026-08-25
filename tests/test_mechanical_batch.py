"""The mechanical batch's behaviors, one case family per item.

The batch is the successor-cycle handoff's section 4 -- mine-confirmed
mechanical fixes carrying no numbered proposal between them. Each family
here pins the behavior one item changes, so a reader grades the batch
item by item rather than reading one green and trusting the rest.

The sink idiom and the template helpers are
``tests/test_tickets_issue_cases/common.py``'s. They are imported rather
than restated because every family below drives the same ``tickets.py``
surface those helpers already build for, and a second copy of the sink
guard is the one thing a test module must not own twice.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.cutcheck as cutcheck  # noqa: E402
import scripts.tickets as tickets_mod  # noqa: E402  the ticket surface's one owner
import scripts.tickets_inputs as inputs  # noqa: E402
import scripts.tickets_reissue as reissue  # noqa: E402
import scripts.tickets_transitions as transitions  # noqa: E402  the table under test
import scripts.tickets_worklog as worklog  # noqa: E402
import tests.test_verification_owners as owners  # noqa: E402  the swept patterns' owner
from tests.test_tickets_issue_cases.common import (  # noqa: E402
    GOOD_CRITERION,
    GOOD_TICKET as SOURCE_TICKET,
    make_template,
    place,
    run_cmd,
    three_stubs,
    use_sink,
)

# The four public fields `is_v2` reads. Declaring any one opts a producer
# into v2, so a stub carrying one is the shortest v2 template there is.
V2_FIELD = "ownership_regions: []"

# One cut: a root and one unit under it, both in the root's own cohort.
CUT_COHORT = "cohort: v1:root:00-root"
ROOT_TICKET = (
    SOURCE_TICKET
    .replace("id: T1", "id: 00-root\n" + CUT_COHORT)
    .replace("executor: orch-tdd", "executor: orch-decompose")
    .replace("claimed_by:", "checked_by:\nclaimed_by:")
)
UNIT_TICKET = SOURCE_TICKET.replace("id: T1", "id: 00-root.01\n" + CUT_COHORT)


def v2_template(tmp: Path) -> Path:
    """A template whose first stub is a v2 producer."""

    stubs = three_stubs()
    stubs["A"] = stubs["A"].replace("bound: 30m", "bound: 30m\n" + V2_FIELD)
    return make_template(tmp, stubs)


def frontmatter(sink: Path, ticket_id: str, run: str = "testrun") -> dict:
    return tickets_mod._parse_frontmatter(
        (sink / "tickets" / run / f"{ticket_id}.md").read_text(encoding="utf-8")
    )


class InstantiateStampsItsOwnVersionTest(unittest.TestCase):
    """`instantiate` takes the pending sentinel from the transition
    table at the stub's own admission version, the way `new` and `recut`
    already do -- a hand-written `v1:pending` on a v2 stub is a ticket
    whose version and whose sentinel disagree from the moment it exists.
    """

    def test_a_v2_stub_lands_with_the_v2_pending_sentinel(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            directory = v2_template(tmp)
            payload = run_cmd(
                "instantiate", str(directory), "--run", "testrun",
                "--set", "target=scripts/a.py",
            )
            self.assertNotIn("error", payload)
            data = frontmatter(sink, "A")
            self.assertTrue(tickets_mod.is_v2(data))
            self.assertEqual(transitions.pending_admission(2), data["admission"])

    def test_a_v1_stub_keeps_the_v1_pending_sentinel(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            payload = run_cmd(
                "instantiate", str(directory), "--run", "testrun",
                "--set", "target=scripts/a.py",
            )
            self.assertNotIn("error", payload)
            data = frontmatter(sink, "A")
            self.assertFalse(tickets_mod.is_v2(data))
            self.assertEqual(transitions.pending_admission(1), data["admission"])

    def test_every_stub_lands_at_the_tables_stamped_status(self):
        entry = transitions.stamp("stamp", 1)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            run_cmd(
                "instantiate", str(directory), "--run", "testrun",
                "--set", "target=scripts/a.py",
            )
            for ticket_id in ("A", "B", "C"):
                data = frontmatter(sink, ticket_id)
                self.assertEqual(entry.status, data["status"])
                for field in entry.blanks:
                    self.assertEqual("", str(data.get(field) or ""))


class ReissueStampsFromTheTableTest(unittest.TestCase):
    """The successor's stamp and the lease it blanks are the transition
    table's row. `tickets_reissue` held a private copy of the lease field
    names, so the table could gain or lose one and the successor would go
    on blanking the old pair with nothing to say so.
    """

    def source(self, sink: Path) -> Path:
        text = SOURCE_TICKET.replace("status: ready", "status: complete")
        return place(sink, "testrun", "T1", text)

    def test_the_blanked_lease_is_the_tables_own_tuple(self):
        self.assertIs(transitions.LEASE_FIELDS, reissue.BLANKED_FIELDS)

    def test_the_successor_lands_at_the_tables_stamp(self):
        entry = transitions.stamp("stamp", 1)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            self.source(sink)
            payload = run_cmd("reissue", "testrun", "T1", "--run", "nextrun")
            self.assertNotIn("error", payload)
            data = frontmatter(sink, "T1", run="nextrun")
            self.assertEqual(entry.status, data["status"])
            self.assertEqual(entry.admission, data["admission"])
            for field in entry.blanks:
                self.assertIn(field, data)
                self.assertEqual("", str(data.get(field) or ""))


class WholeSuiteOracleExemptsAGrantedModuleTest(unittest.TestCase):
    """A whole-module oracle discriminates nothing *between siblings* --
    but a module the item itself was granted is the item's own artifact.
    No sibling runs it, because no sibling may write it, so naming it
    whole names exactly this item's work and the finding is a false one.
    """

    ORACLE = "python -m unittest tests.test_mechanical_batch"

    def ticket(self, scope: str) -> str:
        criterion = (
            f"the module's cases hold | oracle: `{self.ORACLE}` "
            "| oracle_class: deterministic"
        )
        return SOURCE_TICKET.replace(
            "write_scope: [scratch/t1.txt]", f"write_scope: [{scope}]"
        ).replace(GOOD_CRITERION, criterion)

    def codes(self, scope: str) -> list:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            place(sink, "testrun", "T1", self.ticket(scope))
            payload = run_cmd("lint", "testrun", "T1")
            return [item["code"] for item in payload["lint"]["findings"]]

    def test_a_granted_module_is_not_a_whole_suite_finding(self):
        self.assertNotIn("whole-suite-oracle", self.codes("tests/test_mechanical_batch.py"))

    def test_the_same_oracle_over_an_ungranted_module_still_fires(self):
        self.assertIn("whole-suite-oracle", self.codes("scratch/t1.txt"))


class ReadyWaitsForTheCutsCheckTest(unittest.TestCase):
    """A cut is checked before its first unit is dispatched. Once a unit
    has left the amendable statuses the cut checker's own corrections are
    refused and `tickets_packet` turns the checker packet away outright,
    so the ordering has to be kept at `ready` -- the step that makes a
    dispatch possible -- and not reported after it.
    """

    def sink_with_cut(self, tmp: Path, checked: bool) -> Path:
        sink = use_sink(tmp)
        root = ROOT_TICKET if not checked else ROOT_TICKET.replace(
            "checked_by:", "checked_by: cut-reader-1"
        )
        place(sink, "testrun", "00-root", root)
        place(sink, "testrun", "00-root.01", UNIT_TICKET)
        return sink

    def ready_ids(self, checked: bool) -> list:
        with tempfile.TemporaryDirectory() as tmp:
            self.sink_with_cut(Path(tmp), checked)
            return [item["id"] for item in run_cmd("ready", "--run", "testrun")["ready"]]

    def test_a_unit_under_an_unchecked_cut_is_not_ready(self):
        self.assertNotIn("00-root.01", self.ready_ids(checked=False))

    def test_the_same_unit_is_ready_once_the_cut_is_checked(self):
        self.assertIn("00-root.01", self.ready_ids(checked=True))


class IdentityKindRefusalNamesTheKindsTest(unittest.TestCase):
    """A producer who mistypes a kind is told what they wrote and, now,
    what they could have written. The set is in hand at both refusals --
    `SCHEMAS` at one, `ADAPTER_KINDS[adapter]` at the other -- so leaving
    it out spent a round trip on a question the refusal could answer.
    """

    def refusal(self, **identity) -> str:
        payload = inputs.resolve_identity_payload(identity=identity, adapter_id="git")
        return payload["findings"][0]["detail"]

    def test_an_unknown_kind_is_told_the_valid_kinds(self):
        detail = self.refusal(kind="git-blob")
        self.assertIn("git-blob", detail)
        for kind in ("git-tree", "git-path", "ticket-section", "artifact"):
            self.assertIn(kind, detail)

    def test_a_kind_the_adapter_does_not_take_is_told_what_it_takes(self):
        """A whole-schema `view-identity`, so the adapter check is reached:
        the git adapter is the one that does not take it."""

        detail = self.refusal(**{
            key: "x" for key in inputs.SCHEMAS["view-identity"]
        } | {"kind": "view-identity"})
        self.assertIn("view-identity", detail)
        self.assertIn("git-tree", detail)


class SweptCommandPatternsCarryABoundaryTest(unittest.TestCase):
    """Every swept `tickets.py <verb>` pattern stops at the verb it
    licenses. `tickets.py amend` once swept `amendment-request` through
    exactly this hole; two patterns still had no boundary, and the guard
    that would have caught them passes only while no live command name
    extends either prefix.
    """

    def patterns(self) -> list:
        return list(owners.PACKET_CARRIED_CLI) + list(owners.PACKET_BUILDS)

    def test_no_swept_pattern_matches_a_longer_verb(self):
        """The verb each pattern licenses, with three more letters on it."""

        for pattern in self.patterns():
            verb = re.sub(r"\(\?![^)]*\)", "", pattern)
            verb = verb.replace(r"\.", ".").replace(r"\b", "")
            with self.subTest(pattern=pattern):
                self.assertIsNone(
                    re.search(pattern, verb + "ly"),
                    f"`{pattern}` reaches past the command it licenses",
                )


class NoNameCheckerPacketWritesNoPlaceholderTest(unittest.TestCase):
    """`--by NAME` was pasteable. `check` accepts the literal word, so a
    packet emitted without `--by` handed its child a command that records
    a checker called NAME -- the very blank the packet's own prose tells
    that child never to fill in. A packet emits a runnable command or no
    command, so without a name the line is withheld.
    """

    def packet_prompt(self, *extra) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            claimed = SOURCE_TICKET.replace(
                "status: ready", "status: claimed"
            ).replace("claimed_by:", "claimed_by: worker-1")
            place(sink, "testrun", "T1", claimed)
            payload = run_cmd(
                "packet", "testrun", "T1", "--reply-to", "main",
                "--executor", "orch-critique", *extra,
            )
            self.assertNotIn("error", payload)
            return json.dumps(payload)

    def test_a_packet_without_a_name_writes_no_by_placeholder(self):
        self.assertNotIn("--by NAME", self.packet_prompt())

    def test_a_packet_given_a_name_still_writes_the_check_command(self):
        prompt = self.packet_prompt("--by", "checker-9")
        self.assertIn("--by checker-9", prompt)


class SharedScratchTreeIsQuarantinedTest(unittest.TestCase):
    """A scratch tree reached a second time is a shared run tree. The
    fresh path records its arrival state so the first span graded owns
    only the difference it made; the cached path skipped that, and handed
    the first span every path the tree already carried.
    """

    def test_a_cached_tree_is_primed_before_its_first_span_is_graded(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            scratch_root = tmp / "scratch"
            tree = scratch_root / "abc123"
            tree.mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=str(tree), check=True)
            (tree / "leftover.txt").write_text("a prior span's", encoding="utf-8")
            cutcheck._TREE_STATE.clear()
            self.assertEqual(tree, cutcheck._scratch_tree("abc123", tmp, scratch_root))
            self.assertEqual(
                [], cutcheck._mutations(tree),
                "the arriving tree's own contents were charged to the first span",
            )


class WorklogReportsTheReadyAndUnclaimedAgeTest(unittest.TestCase):
    """`never claimed` said nothing about a queue standing still, which
    is what a reader of this view is looking for. A ready, unclaimed item
    now carries how long it has been on offer.
    """

    def rendered(self, status: str, claimed_at: str = "") -> str:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "00-root.01.md"
            path.write_text("a ticket", encoding="utf-8")
            item = {
                "id": "00-root.01", "status": status, "claimed_at": claimed_at,
                "path": str(path), "depends_on": [], "sections": {},
            }
            root = {"id": "00-root", "status": "claimed", "sections": {}}
            return worklog._render_worklog("testrun", [item], root)

    def test_a_ready_unclaimed_item_says_how_long_it_has_been_on_offer(self):
        self.assertIn("on offer", self.rendered("ready"))

    def test_a_claimed_item_carries_its_lease_stamp_and_no_age(self):
        self.assertNotIn("on offer", self.rendered("claimed", "2026-08-24T00:00:00Z"))

    def test_a_pending_item_is_not_on_offer_at_all(self):
        self.assertNotIn("on offer", self.rendered("pending"))


if __name__ == "__main__":
    unittest.main()
