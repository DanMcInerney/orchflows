"""The gate repair stub consumes accepted blocking findings only.

An `orch-critique` finding carries `blocking: true|false`, and the code
pack's lens cell decides which a finding is. The repair stub the gate
writes acts on the accepted blocking ones inside its own write scope;
an accepted non-blocking one is a candidate for its own spec, queued
rather than swept into this run's correction (rules/verification.md
section 9). These cases read the stub the dispatcher writes and the
anchors the owner files carry, never their sentences.
"""

from .common import *  # noqa: F401,F403

import unittest

from .common import ROOT
from scripts import tickets_dispatch
from scripts.cutcheck_contract import CITATION_RE, SECTION_CITATION_RE

CRITIQUE_MD = ROOT / "skills" / "kernel" / "orch-critique" / "SKILL.md"
INTEGRATE_MD = ROOT / "skills" / "kernel" / "orch-integrate" / "SKILL.md"
CRAFT_MD = ROOT / "packs" / "orch-code-pack" / "references" / "craft.md"


def repair_sections() -> dict:
    """The sections `gate` renders into one `<root>.gate.repair` stub."""

    return dict(
        tickets_dispatch._gate_body(
            "repair",
            "00-root",
            "code",
            ["scripts/one.py"],
            "00-root",
            "- the suite exits 0 | oracle: `t` | oracle_class: deterministic",
            ["00-root.gate.critique.code"],
            run="testrun",
        )
    )


def section_of(path, heading: str) -> str:
    """One `## <heading>` section of a markdown owner file."""

    body = path.read_text(encoding="utf-8").split("## " + heading, 1)
    if len(body) == 1:
        raise AssertionError("{} states no ## {}".format(path.name, heading))
    return body[1].split("\n## ", 1)[0]


class GateRepairConsumesBlockingFindingsTest(unittest.TestCase):
    """The stub's objective and completion test name which findings it
    consumes and where the rest go, in the two criteria it already had."""

    def test_the_objective_repairs_the_accepted_blocking_findings(self):
        objective = repair_sections()["Objective"]
        self.assertIn("accepted blocking finding", objective)
        self.assertIn("candidate scope", objective)

    def test_the_objective_keeps_the_non_blocking_ones_out_of_the_repair(self):
        objective = repair_sections()["Objective"]
        self.assertIn("non-blocking", objective)

    def test_the_first_criterion_splits_the_two_dispositions(self):
        criteria = repair_sections()["Completion test"].splitlines()
        self.assertIn("accepted blocking finding", criteria[0])
        self.assertIn("non-blocking", criteria[0])
        self.assertIn("candidate scope", criteria[0])

    def test_the_stub_cites_no_file_section_it_does_not_quote_from(self):
        """The stub quotes `## Result`, so any `<file>.<ext> §<n>` citation
        beside it is read as that quote's source and graded against it:
        `cutcheck` reports quote-not-at-citation, which is no advisory. The
        rule the objective names is stated without a path for that reason."""

        sections = repair_sections()
        for name in ("Objective", "Completion test"):
            with self.subTest(section=name):
                self.assertEqual(
                    [], SECTION_CITATION_RE.findall(sections[name])
                )
                self.assertEqual([], CITATION_RE.findall(sections[name]))

    def test_the_stub_still_states_exactly_its_two_criteria(self):
        criteria = repair_sections()["Completion test"].splitlines()
        self.assertEqual(2, len(criteria))
        self.assertIn("nothing outside the write scope changed", criteria[1])


class CritiqueReturnsTheFlagTest(unittest.TestCase):
    """The flag is part of what a critique returns, and the pack's lens
    cell -- not the skill -- is where its per-lens value is decided."""

    def test_the_return_shape_carries_the_field(self):
        returned = CRITIQUE_MD.read_text(encoding="utf-8").rsplit("\nReturn:", 1)
        self.assertEqual(2, len(returned), "orch-critique states no Return")
        self.assertIn("`blocking: true|false`", returned[1])

    def test_the_lens_cell_decides_the_value(self):
        lens = section_of(CRAFT_MD, "Lens")
        self.assertIn("`blocking: true`", lens)
        self.assertIn("`blocking: false`", lens)

    def test_the_join_routes_the_non_blocking_ones_elsewhere(self):
        self.assertIn("non-blocking", INTEGRATE_MD.read_text(encoding="utf-8"))
