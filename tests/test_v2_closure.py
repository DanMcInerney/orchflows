"""Closure membership: which tickets one mutation plan is graded against.

Two reproducers drive this module.  The first is checker-opus-02's, filed on
ticket 00-root.02: once v2 tickets stamp no cohort, every cohortless ticket in
a run reads the same empty cohort string, collapses into one closure, and each
member inherits every other member's mutation findings.  The second is live in
this repository's own run -- a terminal member's spent plan still counted as a
companion owner, so a completed unit and a pending one were reported as two
owners of the same required node.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import tickets_admission  # noqa: E402
from scripts import tickets_scope  # noqa: E402
from scripts.tickets_format import _set_frontmatter_field  # noqa: E402
from tests.test_tickets_issue_cases.generation_lifecycle import (  # noqa: E402
    ticket as reproducer_ticket,
)


CUT_ONE = "v2:cut:00-root:1:sha256:" + "a1" * 32
CUT_TWO = "v2:cut:00-root:2:sha256:" + "b2" * 32


def _body(ticket_id, header, *, mutations, scope, depends, status):
    lines = [
        "---",
        f"id: {ticket_id}",
        "run: closure-run",
        f"status: {status}",
        *header,
        "executor: orch-tdd",
        "pack: orch-code-pack",
        f"depends_on: [{', '.join(depends)}]",
        f"write_scope: [{', '.join(scope)}]",
        f"mutations: [{', '.join(mutations)}]",
        "bound: 30m",
        "---",
        "",
        "## Objective",
        "",
        "Fixture.",
        "",
    ]
    return "\n".join(lines)


def v1_ticket(ticket_id, *, mutations=(), scope=(), depends=(), status="pending", cohort="v1:root:R"):
    """A v1 ticket, or -- with ``cohort=None`` -- one that stamps none."""

    header = ["admission: v1:pending"]
    if cohort is not None:
        header.append(f"cohort: {cohort}")
    return _body(ticket_id, header, mutations=mutations, scope=scope, depends=depends, status=status)


def v2_ticket(ticket_id, *, mutations=(), scope=(), depends=(), status="pending", cut_generation=None):
    """A v2 ticket: no cohort, and a sealed cut identity only once sealed."""

    header = ["admission: v2:pending", "ownership_regions: []"]
    if cut_generation is not None:
        header.append(f"cut_generation: {cut_generation}")
    return _body(ticket_id, header, mutations=mutations, scope=scope, depends=depends, status=status)


def manifest(*edges):
    value = {"version": 1, "edges": list(edges)}
    return json.dumps(value, separators=(",", ":")).encode("utf-8")


def edge(source, required, reason="fixture edge"):
    operation, path = source.split(":", 1)
    required_operation, required_path = required.split(":", 1)
    return {
        "from": {"operation": operation, "path": path},
        "requires": [{"operation": required_operation, "path": required_path}],
        "reason": reason,
    }


def grade(ticket_id, members, content=manifest()):
    return tickets_scope.grade_scope(
        ticket_id=ticket_id,
        text=members[ticket_id],
        siblings=members,
        adapter_id="git",
        context={"scope_manifest": content},
    )


def codes(result):
    return sorted({item["code"] for item in result["findings"]})


def fields(result):
    return sorted({item["field"] for item in result["findings"]})


def lawful_and_defective(build, **extra):
    """One lawful member and one whose plan leaves its own write scope."""

    return {
        "00-root.01": build("00-root.01", mutations=["change:scripts/one.py"], scope=["scripts/one.py"], **extra),
        "00-root.02": build("00-root.02", mutations=["change:scripts/OUTSIDE_ITS_SCOPE.py"], scope=["scripts/two.py"], **extra),
    }


class CohortlessV2MembershipTest(unittest.TestCase):
    """checker-opus-02's reproducer: the absent cohort is not a cohort."""

    def test_a_cohortless_v2_sibling_defect_stays_out_of_a_lawful_grade(self):
        members = lawful_and_defective(v2_ticket)
        result = grade("00-root.01", members)
        self.assertEqual([], [name for name in fields(result) if name.startswith("00-root.02")])
        self.assertNotIn("mutation-outside-write-scope", codes(result))

    def test_v2_tickets_with_distinct_cut_generations_grade_independently(self):
        members = {
            "00-root.01": v2_ticket(
                "00-root.01", mutations=["change:scripts/one.py"], scope=["scripts/one.py"],
                cut_generation=CUT_ONE,
            ),
            "00-root.02": v2_ticket(
                "00-root.02", mutations=["change:scripts/OUTSIDE_ITS_SCOPE.py"], scope=["scripts/two.py"],
                cut_generation=CUT_TWO,
            ),
        }
        result = grade("00-root.01", members)
        self.assertEqual([], [name for name in fields(result) if name.startswith("00-root.02")])

    def test_one_sealed_cut_is_still_one_closure(self):
        """The fix must not make every v2 ticket its own closure."""

        members = lawful_and_defective(v2_ticket, cut_generation=CUT_ONE)
        result = grade("00-root.01", members)
        self.assertIn("mutation-outside-write-scope", codes(result))
        self.assertIn("00-root.02.mutations", fields(result))

    def test_a_v2_ticket_still_grades_its_own_plan(self):
        members = lawful_and_defective(v2_ticket)
        result = grade("00-root.02", members)
        self.assertIn("mutation-outside-write-scope", codes(result))
        self.assertIn("00-root.02.mutations", fields(result))


class TerminalMembershipTest(unittest.TestCase):
    """A spent plan is history, not authority."""

    CONTENT = manifest(edge("change:scripts/feature.py", "change:tests/pins.json"))

    def companions(self, owner_status):
        return {
            "00-root.05": v1_ticket(
                "00-root.05", mutations=["change:scripts/feature.py"], scope=["scripts/feature.py"],
            ),
            "00-root.07": v1_ticket(
                "00-root.07", mutations=["change:tests/pins.json"], scope=["tests/pins.json"],
                status=owner_status,
            ),
            "00-root.11": v1_ticket(
                "00-root.11", mutations=["change:tests/pins.json"], scope=["tests/pins.json"],
            ),
        }

    def test_a_terminal_member_is_not_a_second_owner_of_a_companion(self):
        for status in ("complete", "blocked", "stalled", "limited", "failed"):
            with self.subTest(status=status):
                result = grade("00-root.05", self.companions(status), self.CONTENT)
                self.assertNotIn("scope-owner-multiple", codes(result))
                self.assertNotIn("scope-owner-missing", codes(result))

    def test_two_live_members_are_still_two_owners(self):
        result = grade("00-root.05", self.companions("pending"), self.CONTENT)
        self.assertIn("scope-owner-multiple", codes(result))
        self.assertIn(
            "change:tests/pins.json owned by 00-root.07, 00-root.11",
            [item["detail"] for item in result["findings"]],
        )

    def test_a_terminal_ticket_being_graded_is_a_member_of_its_own_closure(self):
        members = {
            "00-root.07": v1_ticket(
                "00-root.07", mutations=["change:tests/pins.json"], scope=["scripts/elsewhere.py"],
                status="limited",
            ),
        }
        result = grade("00-root.07", members)
        self.assertIn("mutation-outside-write-scope", codes(result))
        self.assertIn("00-root.07.mutations", fields(result))


class V1GroupingUnchangedTest(unittest.TestCase):
    """Whatever a cohort string is, it groups exactly as it did."""

    def test_a_member_of_another_cohort_stays_outside_the_closure(self):
        members = lawful_and_defective(v1_ticket)
        members["00-root.02"] = _set_frontmatter_field(members["00-root.02"], "cohort", "v1:ticket:00-root.02")
        result = grade("00-root.01", members)
        self.assertEqual([], [name for name in fields(result) if name.startswith("00-root.02")])

    def test_members_of_one_cohort_are_one_closure(self):
        members = lawful_and_defective(v1_ticket)
        result = grade("00-root.01", members)
        self.assertIn("00-root.02.mutations", fields(result))

    def test_cohortless_v1_members_group_exactly_as_they_did(self):
        """No v2 field, no cohort: the legacy shape is not re-keyed per ticket."""

        members = lawful_and_defective(v1_ticket, cohort=None)
        result = grade("00-root.01", members)
        self.assertIn("00-root.02.mutations", fields(result))


class ReproducerAtTheAdmissionGradeTest(unittest.TestCase):
    """The same reproducer through the whole admission grade, not one call."""

    def test_a_lawful_v2_ticket_is_admitted_beside_a_defective_sibling(self):
        lawful = reproducer_ticket("00-root.01")
        defective = _set_frontmatter_field(
            reproducer_ticket("00-root.02"), "mutations", "[change:scripts/OUTSIDE_ITS_SCOPE.py]",
        )
        snapshot = {"00-root.01": lawful, "00-root.02": defective}
        result = tickets_admission.grade_admission("00-root.01", lawful, snapshot)
        named = [item for item in result["findings"] if str(item["field"]).startswith("00-root.02")]
        self.assertEqual([], named)


if __name__ == "__main__":
    unittest.main()
