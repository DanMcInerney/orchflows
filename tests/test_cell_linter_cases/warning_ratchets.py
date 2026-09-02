"""Warning-ratchet behavior for the cell linter."""

import shutil
import tempfile
import unittest
from pathlib import Path

from .pack_cells import (
    BASELINE_WARNINGS,
    CLONE_SKIPS,
    CROSS_TIER,
    CROSS_TIER_WARNING_CEILING,
    NEAR,
    ROOT,
    WARNING_CEILING,
    run_validate,
    validate_the_real_tree,
    warning_lines,
)


def ceiling_breach(count, ceiling=None, kind=NEAR):
    """A ratchet's whole decision: None while the count holds, the
    sentence naming the breach once it does not. Every test below calls
    this one function, so the check that grades the real tree is the same
    check shown to fail against a wrong one."""
    ceiling = WARNING_CEILING if ceiling is None else ceiling
    if count > ceiling:
        return "%d WARN (%s), ceiling %d" % (count, kind, ceiling)
    return None


class WarningCeilingTest(unittest.TestCase):
    # One clause packs/orch-code-pack/references/craft.md's `## Lens`
    # already owns, restated in a third pack's same-named section with a
    # single noun changed. This is what a regression here looks like: not
    # a new kind of finding, one more copy of a clause that has an owner.
    # The clause carries no span MANDATED_FORM_RES strips, so the plant is
    # the pack's own content and the ratio is measured over all of it.
    # `## Lens` and not `## Slicing`: Lens keying
    # (`research/lens-keying-2026-09-02.md`) folds Slicing into
    # `## Lens` › `### cut`, and `validate_cell_duplication` only ever
    # compares same-named `##` sections, so a plant under a heading one
    # side has retired would pair with nothing and report nothing.
    REGRESSION = (
        "\n- Correctness: does the artifact satisfy the spec's acceptance,\n"
        "  including its failure paths, not only the happy path?\n"
    )

    def _clone_beside_the_tree(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        clone = Path(temporary.name) / "clone"
        shutil.copytree(ROOT, clone, ignore=CLONE_SKIPS, symlinks=True)
        return clone

    def test_the_tree_holds_at_or_under_the_ceiling(self):
        found = warning_lines(validate_the_real_tree().stdout, NEAR)
        self.assertIsNone(ceiling_breach(len(found)), "\n".join(found))
        self.assertLess(
            len(found),
            BASELINE_WARNINGS,
            "the ratchet must stand below the %d measured at ff30d60"
            % BASELINE_WARNINGS,
        )

    def test_the_tree_holds_at_or_under_the_cross_tier_ceiling(self):
        """The copies P3 deletes, counted while they are still here. The
        ceiling only ever moves down: a clause that gains a second owner
        after this point is a regression, and this is what says so."""

        found = warning_lines(validate_the_real_tree().stdout, CROSS_TIER)
        self.assertIsNone(
            ceiling_breach(len(found), CROSS_TIER_WARNING_CEILING, CROSS_TIER),
            "\n".join(found),
        )

    def test_the_two_ratchets_count_disjoint_findings(self):
        """Two ceilings over one report only mean anything if no finding is
        counted by both -- and if together they cover the report, so a WARN
        of some third kind stays an explicit, separately identified finding
        rather than becoming slack in one of these."""

        stdout = validate_the_real_tree().stdout
        near = set(warning_lines(stdout, NEAR))
        cross = set(warning_lines(stdout, CROSS_TIER))
        composition = {
            line for line in warning_lines(stdout)
            if line.startswith("WARN example-workflows/")
        }
        self.assertEqual(set(), near & cross)
        # Only the dated browser-game protocol exception remains; all shipped
        # compositions now instantiate through registered callables.
        self.assertEqual(1, len(composition), composition)
        self.assertEqual(set(warning_lines(stdout)), near | cross | composition)

    def test_a_count_above_the_ceiling_fails(self):
        tree_report = validate_the_real_tree().stdout
        held = warning_lines(tree_report, NEAR)
        clone = self._clone_beside_the_tree()
        planted = clone / "packs" / "orch-research-pack" / "references" / "craft.md"
        text = planted.read_text(encoding="utf-8")
        self.assertIn("## Lens\n", text)
        planted.write_text(
            text.replace("## Lens\n", "## Lens\n" + self.REGRESSION, 1),
            encoding="utf-8",
        )
        clone_report = run_validate(clone).stdout
        raised = warning_lines(clone_report, NEAR)
        # The clone's report has to be the tree's report plus the plant, and
        # the containment is what says so: a finding the tree makes and the
        # clone does not is CLONE_SKIPS having dropped something validate.py
        # grades, which would make the plant evidence about a subset of the
        # tree rather than about the check. Over every kind of WARN, not
        # only the planted one: what CLONE_SKIPS could drop is a file, and a
        # dropped file goes quiet in every check that reads it. Asserting it
        # here rather than in a second, unplanted run of the clone keeps the
        # reading at one validate.py run per tree.
        self.assertEqual(
            [],
            [
                line for line in warning_lines(tree_report)
                if line not in warning_lines(clone_report)
            ],
            "the clone lost findings the tree reports: CLONE_SKIPS dropped "
            "something validate.py grades",
        )
        self.assertGreater(len(raised), len(held), "the plant reported nothing")
        self.assertIsNotNone(
            ceiling_breach(len(raised)),
            "%d WARN in the clone did not breach the ceiling of %d"
            % (len(raised), WARNING_CEILING),
        )
