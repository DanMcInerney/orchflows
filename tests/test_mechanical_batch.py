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

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets_mod  # noqa: E402  the ticket surface's one owner
import scripts.tickets_reissue as reissue  # noqa: E402
import scripts.tickets_transitions as transitions  # noqa: E402  the table under test
from tests.test_tickets_issue_cases.common import (  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
