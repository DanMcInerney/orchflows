"""Result-envelope and name-resolution validator regression cases."""

from .support import _IsolatedTree

class TestEnvelopeCheck(_IsolatedTree):
    """validate_envelope against contracts/result.md's bound units, on
    the synthetic skills-tree idiom."""

    def _write_skill(self, name: str, body: str, tier: str = "kernel"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a synthetic bound unit\nrole: none\n---\n{body}",
            encoding="utf-8",
        )

    def test_bound_unit_return_without_envelope_is_error(self):
        self._write_skill(
            "orch-do",
            "Require: a body and a bound.\nNever: exceed the bound.\n"
            "Return: assumptions and feedback.\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("orch-do", result.stdout)
        self.assertIn("does not lead with the result envelope", result.stdout)
        self.assertIn("contracts/result.md", result.stdout)

    def test_bound_unit_leading_with_the_envelope_passes(self):
        self._write_skill(
            "orch-do",
            "Require: a body and a bound.\nNever: exceed the bound.\n"
            "Return: status, results by identity, and final verification; "
            "then bounds spent. Terminal states are stalled or limited.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)

    def test_bound_unit_return_riding_the_work_item_carrier_passes(self):
        self._write_skill(
            "orch-task",
            "Require: one ready ticket.\nNever: skip the join.\n"
            "Return: the completed ticket per the work-item contract.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)

    def test_unbound_skill_return_is_not_checked(self):
        self._write_skill(
            "orch-elsewise",
            "Require: an input.\nNever: overreach.\nReturn: findings and feedback.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)


class TestNameResolution(_IsolatedTree):
    """validate_names: a backticked `orch-*` outside the skill tree still
    names something in it.

    The call-graph check reads skill bodies only, so a rule, a contract, a
    doc or a README naming a skill that no longer exists rode through exit 0
    and a green suite -- which is exactly how `orch-mechanize` survived in
    rules/token-economy.md and `orch-review-fix` in rules/topology.md after
    both packages were deleted. A name is a call edge wherever it is
    backticked (rules/composition.md rule 2), so it resolves or it is a
    defect.
    """

    def _write_skill(self, name: str, tier: str = "kernel"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: a synthetic package\nrole: worker\n---\n"
            "Require: an input.\nNever: overreach.\nReturn: status; result.\n",
            encoding="utf-8",
        )

    def _write_rule(self, text: str):
        # ARCHITECTURE.md is the marker that says this tree is a library
        # whose tiers a name can resolve in; without it the check skips, as
        # it does for every fixture that copies half a tree.
        (self.tmp_path / "ARCHITECTURE.md").write_text("# Tiers\n", encoding="utf-8")
        rules = self.tmp_path / "rules"
        rules.mkdir(exist_ok=True)
        (rules / "synthetic.md").write_text(text, encoding="utf-8")

    def unresolved(self, stdout):
        """The names this check reported, by name.

        Not the exit code: the fixture tree carries the real contracts/
        beside one synthetic skill, so every name the contracts legitimately
        call is unresolvable here for the fixture's own reason. The findings
        this check makes about the file the test wrote are what it decides.
        """

        return sorted(
            line.split("`")[1]
            for line in stdout.splitlines()
            if "names no package" in line and "rules/synthetic.md" in line
        )

    def test_a_backticked_name_with_no_package_is_an_error(self):
        self._write_skill("orch-real")
        self._write_rule("1. Mechanizing a step is `orch-nothing`'s.\n")
        result = self._run()
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertIn("rules/synthetic.md", result.stdout)
        self.assertEqual(["orch-nothing"], self.unresolved(result.stdout))

    def test_a_backticked_name_with_a_package_is_clean(self):
        self._write_skill("orch-real")
        self._write_rule("1. The cut is `orch-real`'s.\n")
        result = self._run()
        self.assertEqual([], self.unresolved(result.stdout))

    def test_a_pack_name_resolves_under_packs(self):
        self._write_skill("orch-real")
        pack_dir = self.tmp_path / "packs" / "orch-synth-pack"
        pack_dir.mkdir(parents=True)
        (pack_dir / "SKILL.md").write_text("---\nname: orch-synth-pack\n"
                                           "description: a synthetic pack\n---\n",
                                           encoding="utf-8")
        self._write_rule("1. The stamp is `orch-synth-pack`'s.\n")
        result = self._run()
        self.assertNotIn("`orch-synth-pack` names no package", result.stdout)

    def test_the_two_role_names_are_allowed(self):
        self._write_skill("orch-real")
        self._write_rule(
            "1. Children take one of two roles: `orch-planner` and `orch-worker`.\n"
        )
        result = self._run()
        self.assertEqual([], self.unresolved(result.stdout))

    def _write_named(self, relative: str, text: str):
        """One file at `relative`, in a tree marked as the library."""

        (self.tmp_path / "ARCHITECTURE.md").write_text("# Tiers\n", encoding="utf-8")
        path = self.tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_every_checked_directory_is_checked(self):
        """One case per directory the check reads, because the list was a
        tuple of four names with one synthetic rules/ file behind it: dropping
        "docs", "contracts" or "templates" from it failed nothing, and
        example-workflows/ — where every template stub lives, each one naming its
        executor — was never in it at all. A stub calling a deleted skill is
        the exact failure this check exists for, and it was outside the
        surface."""

        self._write_skill("orch-real")
        checked = (
            "rules/synthetic.md",
            "docs/synthetic.md",
            "contracts/synthetic.md",
            "templates/synthetic.md",
            "README.md",
            # recursive, all three: a stub, a nested reference, a pack
            # reference and a skill reference are each a file the old
            # non-recursive glob over four top-level directories never saw
            "example-workflows/demo/00-step.md",
            "example-workflows/references/protocol.md",
            "packs/orch-synth-pack/references/craft.md",
            "skills/kernel/orch-real/references/notes.md",
        )
        for relative in checked:
            with self.subTest(relative):
                path = self._write_named(relative, "The step is `orch-nothing`'s.\n")
                try:
                    result = self._run()
                    reported = [
                        line for line in result.stdout.splitlines()
                        if "orch-nothing" in line and relative in line.replace("\\", "/")
                    ]
                    self.assertEqual(1, len(reported), result.stdout)
                    self.assertEqual(1, result.returncode, result.stdout)
                finally:
                    path.unlink()

    def test_an_unbackticked_retired_name_is_history_and_not_a_finding(self):
        """DESIGN.md's supersession paragraphs name skills that were
        deleted. Plain text is the library's own way of saying `mentioned,
        not called` (rules/composition.md rule 2), so the check needs no
        per-file allowlist to let history stand."""

        self._write_skill("orch-real")
        self._write_rule("1. Three shapes were skills (orch-fix, orch-evolve).\n")
        result = self._run()
        self.assertEqual([], self.unresolved(result.stdout))
