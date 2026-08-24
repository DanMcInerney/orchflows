"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck.

Family 3's pricing and root-admissibility screens. Every case is graded
through `_check_ticket`, which is what the report calls, rather than through
a judgment alone: a screen wired nowhere reports nothing, and each of the six
below repairs a cut that had already passed.
"""

from tests.test_cutcheck import *  # noqa: F401,F403

import scripts.cutcheck_pricing as cutcheck_pricing  # noqa: E402  the screens' owner

try:
    del load_tests
except NameError:
    pass


class CutPricingScreenTest(unittest.TestCase):
    """The four pricing screens: a cut prices every file its objective grows."""

    SIBLINGS = {
        "00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR},
        "00-root.01": {"id": "00-root.01", "executor": "orch-tdd"},
    }
    JUDGED = "1. **A reviewer reads it.** oracle_class: judged. provenance: authored-here."

    def _ticket(self, inputs="", objective="Change one module.", scope="scripts/owner.py",
                mutations="[change:scripts/owner.py]"):
        return (
            "---\nid: 00-root.01\nexecutor: orch-tdd\ndepends_on: []\n"
            "write_scope: [{}]\nmutations: {}\n---\n\n## Objective\n\n{}\n\n"
            "## Fixed inputs\n\n{}\n\n## Completion test\n\n{}\n"
        ).format(scope, mutations, objective, inputs, self.JUDGED)

    def _findings(self, tree=None, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "00-root.01.md"
            path.write_text(self._ticket(**kwargs), encoding="utf-8")
            found = cutcheck._check_ticket(
                path, tree if tree is not None else ROOT, None, self.SIBLINGS)
        return [(klass, detail) for _, _, klass, detail in found]

    def _classes(self, **kwargs):
        return [klass for klass, _ in self._findings(**kwargs)]

    # Screen 1: pricing that skips a file the objective grows.

    PARTIAL = ('- input: {"name":"anchors","type":"literal","value":"The owner'
               ' scripts/owner.py is 429 of 510, headroom 81."}')
    BOTH = ('- input: {"name":"anchors","type":"literal","value":"The owner'
            ' scripts/owner.py is 429 of 510, headroom 81; tests/test_owner.py'
            ' is 401 of 510, headroom 109."}')
    GROWS_BOTH = "[change:scripts/owner.py, change:tests/test_owner.py]"
    OWNS_BOTH = "scripts/owner.py, tests/test_owner.py"

    def test_a_cut_that_prices_one_grown_file_and_skips_another_is_reported(self):
        """The test module is the half that gets skipped, so it is named here.

        A suite grows with the source it grades, and a ceiling reached there
        stops the work exactly as hard as one reached in the module.
        """

        self.assertIn(cutcheck_pricing.UNPRICED_GROWTH, self._classes(
            inputs=self.PARTIAL, scope=self.OWNS_BOTH, mutations=self.GROWS_BOTH))

    def test_pricing_every_grown_file_is_silent(self):
        self.assertNotIn(cutcheck_pricing.UNPRICED_GROWTH, self._classes(
            inputs=self.BOTH, scope=self.OWNS_BOTH, mutations=self.GROWS_BOTH))

    def test_a_cut_pricing_nothing_at_all_is_asked_for_nothing(self):
        """The screen grades partial pricing, never the absence of it.

        A cut whose files sit nowhere near a ceiling claims no measurement and
        owes none; asking every cut for arithmetic would report the corpus.
        """

        self.assertNotIn(cutcheck_pricing.UNPRICED_GROWTH, self._classes(
            scope=self.OWNS_BOTH, mutations=self.GROWS_BOTH))

    def test_a_created_file_is_priced_by_nobody(self):
        """`create:` names a file the baseline does not hold: no size to state."""

        self.assertNotIn(cutcheck_pricing.UNPRICED_GROWTH, self._classes(
            inputs=self.PARTIAL, scope="scripts/owner.py, scripts/new.py",
            mutations="[change:scripts/owner.py, create:scripts/new.py]"))

    # Screen 2: an owner closed at its cap with no lawful split granted.

    AT_CAP = ('- input: {"name":"anchors","type":"literal","value":"The owner'
              ' scripts/owner.py is 510 of 510, headroom 0."}')

    def test_an_owner_at_its_cap_with_no_sub_owner_granted_is_reported(self):
        """510 of 510 and one path in the grant is jointly unsatisfiable.

        The instance cost a unit most of its bound: the objective ordered
        growth into a file that could not lawfully grow by a single line.
        """

        self.assertIn(cutcheck_pricing.UNSPLITTABLE_OWNER,
                      self._classes(inputs=self.AT_CAP))

    def test_a_granted_split_destination_discharges_the_cap(self):
        self.assertNotIn(cutcheck_pricing.UNSPLITTABLE_OWNER, self._classes(
            inputs=self.AT_CAP, scope="scripts/owner.py, scripts/owner_split.py",
            mutations="[change:scripts/owner.py, create:scripts/owner_split.py]"))

    def test_an_owner_with_headroom_is_asked_for_no_split(self):
        self.assertNotIn(cutcheck_pricing.UNSPLITTABLE_OWNER,
                         self._classes(inputs=self.PARTIAL))

    # Screen 3: a numeric ceiling stated without its arithmetic.

    BARE = ('- input: {"name":"anchors","type":"literal","value":"Keep'
            ' scripts/owner.py under the 510-line ceiling."}')

    def test_a_ceiling_over_a_granted_file_without_arithmetic_is_reported(self):
        """Stating the cap and not the distance to it moves the measuring onto
        the unit, which is where most of one unit's bound went."""

        self.assertIn(cutcheck_pricing.CEILING_WITHOUT_ARITHMETIC,
                      self._classes(inputs=self.BARE))

    def test_a_ceiling_shipped_with_its_arithmetic_is_silent(self):
        self.assertNotIn(cutcheck_pricing.CEILING_WITHOUT_ARITHMETIC,
                         self._classes(inputs=self.PARTIAL))

    def test_a_ceiling_naming_no_granted_file_is_not_this_screens(self):
        """A word budget or a bound stated about the run at large commits no
        owner to an arithmetic anybody could have stated."""

        self.assertNotIn(cutcheck_pricing.CEILING_WITHOUT_ARITHMETIC, self._classes(
            inputs='- input: {"name":"policy","type":"literal","value":"The'
                   ' decomposer holds a 300-word ceiling."}'))

    # Screen 4: a changing owner whose output-pinning artifacts are ungranted.

    EMITS = "The item changes the filing shapes scripts/owner.py emits."

    def _tree_pinning_output(self):
        tmp = Path(tempfile.mkdtemp(prefix="cutcheck-outpin-"))
        # Never `ignore_errors`: the instrument may not silence a removal
        # failure, which is the thing several of this suite's subjects are on
        # trial for. `ScratchCleanupReportingTest` reads this line from source.
        self.addCleanup(shutil.rmtree, str(tmp))
        (tmp / "scripts").mkdir()
        (tmp / "scripts" / "owner.py").write_text("X = 1\n", encoding="utf-8")
        (tmp / "tests").mkdir()
        (tmp / "tests" / "test_help.py").write_text(
            "from scripts import owner\n", encoding="utf-8")
        (tmp / "tests" / "test_quiet.py").write_text(
            "def test_it():\n    assert True\n", encoding="utf-8")
        return tmp

    def test_an_output_change_names_the_ungranted_test_that_pins_the_output(self):
        """The class modelled once, and named where it was measured.

        Run 20260824T222500Z's own cut carried it at three of twelve units,
        one mechanism each time -- the source granted, the check pinning what
        that source emits left outside every grant:

        - `00-root.06` changes the filing shapes `scripts/tickets_packet.py`
          emits, pinned at `tests/test_tickets_cases/cli_help.py:140`;
        - `00-root.01`'s doc-paths change trips a topology pin in
          `tests/test_contracts_cases/topology.py`;
        - `00-root.08`'s `tickets_transitions` edit trips the import census in
          `tests/test_tickets_cases/run_state_resolution.py` -- the same
          census file that caught the preceding run twice.

        cutcheck exited 0 on all three because this screen did not exist.
        """

        found = self._findings(tree=self._tree_pinning_output(), objective=self.EMITS)
        pinned = [d for k, d in found if k == cutcheck_pricing.UNPINNED_OUTPUT]
        self.assertEqual(len(pinned), 1, found)
        self.assertIn("tests/test_help.py", pinned[0])
        self.assertNotIn("test_quiet.py", pinned[0])

    def test_granting_the_pinning_artifact_discharges_the_output_change(self):
        self.assertNotIn(cutcheck_pricing.UNPINNED_OUTPUT, self._classes(
            tree=self._tree_pinning_output(), objective=self.EMITS,
            scope="scripts/owner.py, tests/test_help.py"))

    def test_a_change_claiming_no_output_is_asked_for_no_pin(self):
        """The screen grades the claim, never the change: an objective that
        alters an internal call orders nothing about what anything emits."""

        self.assertNotIn(cutcheck_pricing.UNPINNED_OUTPUT, self._classes(
            tree=self._tree_pinning_output(),
            objective="The item renames a local in scripts/owner.py."))


class RootAdmissibilityScreenTest(unittest.TestCase):
    """The two root screens: a root its own pack cannot execute, and a required
    command the same root's exclusions forbid."""

    def _root(self, pack="orch-code-pack", isolation="none", inputs="", excluded=""):
        return (
            "---\nid: 00-root\nexecutor: {}\npack: {}\ndepends_on: []\n"
            "write_scope: [scripts/owner.py]\nisolation: {}\n{}---\n\n"
            "## Objective\n\nDeliver it.\n\n## Fixed inputs\n\n{}\n\n"
            "## Completion test\n\n1. **A reviewer reads it.** oracle_class:"
            " judged. provenance: authored-here.\n"
        ).format(cutcheck.ROOT_EXECUTOR, pack, isolation, excluded, inputs)

    def _classes(self, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "00-root.md"
            path.write_text(self._root(**kwargs), encoding="utf-8")
            found = cutcheck._check_ticket(
                path, ROOT, None,
                {"00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR}})
        return [klass for _, _, klass, _ in found]

    def test_a_code_pack_root_fixing_isolation_none_is_refused(self):
        """Three respec cycles: the pack's workspace cell binds isolation to
        branch or worktree, and the root fixed it at none."""

        self.assertIn(cutcheck_pricing.PACK_INADMISSIBLE_ROOT,
                      self._classes(isolation="none"))

    def test_a_root_whose_isolation_its_pack_permits_is_silent(self):
        for isolation in ("required", "worktree", "branch"):
            with self.subTest(isolation=isolation):
                self.assertNotIn(cutcheck_pricing.PACK_INADMISSIBLE_ROOT,
                                 self._classes(isolation=isolation))

    def test_a_root_naming_no_pack_is_graded_against_nothing(self):
        self.assertNotIn(cutcheck_pricing.PACK_INADMISSIBLE_ROOT,
                         self._classes(pack="", isolation="none"))

    EXCLUDES_PUSH = "excluded_actions: [vcs.push, vcs.open-pr]\n"
    PUSHES = ('- input: {"name":"acceptance-as-runnable-checks","type":"literal",'
              '"value":["git push --dry-run origin HEAD"]}')
    CLEAN = ('- input: {"name":"acceptance-as-runnable-checks","type":"literal",'
             '"value":["git diff --check"]}')

    def test_a_required_command_its_own_exclusions_forbid_is_flagged(self):
        """It passed at exit 0: the root required a command whose own program
        tokens spell an action the same root excludes."""

        self.assertIn(cutcheck_pricing.EXCLUDED_REQUIRED_COMMAND, self._classes(
            isolation="required", excluded=self.EXCLUDES_PUSH, inputs=self.PUSHES))

    def test_a_required_command_no_exclusion_names_is_silent(self):
        self.assertNotIn(cutcheck_pricing.EXCLUDED_REQUIRED_COMMAND, self._classes(
            isolation="required", excluded=self.EXCLUDES_PUSH, inputs=self.CLEAN))

    def test_a_prose_exclusion_contributes_no_tokens(self):
        """Structured actions only. A sentence of policy holds every ordinary
        word in the language, and reading those as program tokens would flag
        the acceptance of every root ever cut."""

        self.assertNotIn(cutcheck_pricing.EXCLUDED_REQUIRED_COMMAND, self._classes(
            isolation="required", inputs=self.CLEAN,
            excluded="excluded_actions:\n- Rewriting a claimed ticket, or"
                     " running git diff outside this run.\n"))


class PricingScreenRegistrationTest(unittest.TestCase):
    """Every new class is family 3's, all six refuse, none reads as a summary."""

    SCREENS = ("UNPRICED_GROWTH", "UNSPLITTABLE_OWNER", "CEILING_WITHOUT_ARITHMETIC",
               "UNPINNED_OUTPUT", "PACK_INADMISSIBLE_ROOT", "EXCLUDED_REQUIRED_COMMAND")

    def test_every_screen_is_family_three_and_moves_the_status(self):
        """None is advisory. `ADVISORY` is a frozen contract constant this
        unit does not own, and each of the six names a contradiction the cut
        carries rather than a weak reading of one.
        """

        for name in self.SCREENS:
            klass = getattr(cutcheck_pricing, name)
            with self.subTest(klass=klass):
                self.assertEqual(cutcheck.FAMILY_OF[klass], cutcheck.FAMILY_3)
                self.assertNotIn(klass, cutcheck.ADVISORY)

    def test_no_screen_name_can_be_read_off_a_summary_line(self):
        """The rule every finding class answers to, asked of the new six."""

        for name in self.SCREENS:
            for line in (cutcheck.ADVISORY_HEADING, cutcheck.GRAPH_HEADING,
                         cutcheck.NO_FINDING_OUTSIDE):
                self.assertNotIn(getattr(cutcheck_pricing, name), line)

    def test_the_ticket_module_re_exports_every_screen(self):
        """The report calls `_check_ticket`; the screens reach it from there."""

        for name in self.SCREENS:
            with self.subTest(name=name):
                self.assertIn(name, cutcheck_ticket.__all__)
