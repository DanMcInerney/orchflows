"""Validator availability and synthetic-package regression cases."""
import shutil
import subprocess
import sys

from .support import ROOT, VALIDATE, _IsolatedTree, loop_lint_warnings, validate

class TestASkippedCheckSaysSo(_IsolatedTree):
    """A check that finds nothing to check has not passed.

    The isolated tree is contracts/, tools/ and tests/ -- so the checks
    keyed to skills/, packs/, compositions/, docs/, templates/ and
    scripts/ find no owner and return. Returning is right: a fixture tree
    is not the library. Returning *silently* is the fallback -- the report
    then reads exactly like a run that graded all of it, and the one
    reader of that report is a run deciding whether the tree is admissible.
    """

    SKIP_NOTE = "absent; check skipped"

    def _skipped(self, stdout):
        return [line for line in stdout.splitlines() if self.SKIP_NOTE in line]

    def test_each_absent_owner_is_named_rather_than_passed_over(self):
        result = self._run()
        named = " ".join(self._skipped(result.stdout))

        for owner in (
            "scripts/state_root.py",      # the friction-location copies
            "AGENTS.md",                  # a surface budget
            "templates/host-block.md",    # the other surface budget
            "compositions",               # the template contract
            "ARCHITECTURE.md",            # the backticked-name check
            "docs",                       # markdown link resolution
            "benchmarks",                 # ditto: one absent root silences it
        ):
            with self.subTest(owner=owner):
                self.assertIn(owner, named)

    def test_the_link_check_names_every_root_that_bought_its_silence(self):
        # This skip is not one file's but the whole check's:
        # `validate_markdown_links` grades nothing at all unless every root
        # is there, so a report naming only the first would leave the
        # operator restoring roots one run at a time. `contracts/` is the
        # control -- the isolated tree has it, and a check that named it
        # would be naming roots it did not miss.
        result = self._run()
        named = self._skipped(result.stdout)

        for root in validate.LINKED_MD_ROOTS:
            with self.subTest(root=root):
                present = (self.tmp_path / root).is_dir()
                self.assertEqual(
                    not present, any(line.startswith("WARN " + root + ":") for line in named)
                )
        self.assertTrue((self.tmp_path / "contracts").is_dir())

    def test_a_check_that_starts_and_finds_half_its_tree_says_that_too(self):
        # With the friction owner present the check runs and then finds no
        # term owner to compare against -- the half that was silent.
        (self.tmp_path / "scripts").mkdir(exist_ok=True)
        shutil.copy(
            ROOT / "scripts" / "state_root.py", self.tmp_path / "scripts" / "state_root.py"
        )

        result = self._run()

        self.assertIn("docs/vocabulary.md", " ".join(self._skipped(result.stdout)))

    def test_a_skipped_check_is_a_warning_and_not_an_error(self):
        # Fixture trees are graded by these tests all day; the note may not
        # turn them red, and `has_errors` is what the exit code reads.
        result = self._run()

        self.assertTrue(self._skipped(result.stdout))
        for line in self._skipped(result.stdout):
            self.assertTrue(line.startswith("WARN "), line)
        self.assertEqual(0, result.returncode, result.stdout)

    def test_the_library_itself_skips_nothing(self):
        # The same note over the real tree would mean a check silently
        # stopped running here, which is the finding this closes.
        result = subprocess.run(
            [sys.executable, str(VALIDATE)], capture_output=True, text=True
        )

        self.assertEqual([], self._skipped(result.stdout))


class TestSyntheticPackageBoundaryInputs(_IsolatedTree):
    """Full runs against a synthetic skills/ tree, so the ERROR/exit-code
    contract is checked at the actual ROOT-relative seam, not just
    parse_frontmatter."""

    def _write_skill(self, name: str, content: bytes, tier: str = "instances"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_bytes(content)

    def _write_pack(self, name: str, content: bytes):
        pack_dir = self.tmp_path / "packs" / name
        pack_dir.mkdir(parents=True)
        (pack_dir / "SKILL.md").write_bytes(content)

    def test_a_references_only_directory_is_no_package_and_no_finding(self):
        """A tier directory holding only `references/` is read as no package
        at all -- not as a package missing its SKILL.md, which would take the
        tree red on a directory the library merely has not finished emptying.
        (Such a home is still no place for a public reference: visibility §4
        wants an owning body naming the path, which is why `profiles.md` now
        sits under `skills/engines/orch-frontier/`.)"""
        refs = self.tmp_path / "skills" / "kernel" / "orch-refsonly" / "references"
        refs.mkdir(parents=True)
        (refs / "profiles.md").write_text("A reference with no skill.\n", encoding="utf-8")
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn("orch-refsonly", result.stdout)
        self.assertEqual("", result.stderr.strip())

    def test_missing_closing_fence_is_error_line_and_exit_1_no_traceback(self):
        self._write_skill(
            "badpkg",
            b"---\nname: badpkg\ndescription: missing closing fence\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing closing frontmatter fence", result.stdout)
        self.assertEqual("", result.stderr.strip())

    def test_bom_prefixed_valid_skill_md_is_not_falsely_flagged(self):
        body = (
            "---\nname: bompkg\ndescription: a bom-prefixed valid skill\nrole: worker\n---\n"
            "Require: one thing.\nNever: another thing.\nReturn: a result.\n"
        )
        self._write_skill("bompkg", b"\xef\xbb\xbf" + body.encode("utf-8"))
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn("missing opening frontmatter fence", result.stdout)

    def test_empty_skill_md_is_error_line_and_exit_1_no_traceback(self):
        self._write_skill("emptypkg", b"")
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing opening frontmatter fence", result.stdout)
        self.assertEqual("", result.stderr.strip())

    def test_skill_missing_role_is_error(self):
        self._write_skill(
            "norolepkg",
            b"---\nname: norolepkg\ndescription: a skill without a role\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("missing required key 'role'", result.stdout)

    def test_role_value_outside_allowed_set_is_error(self):
        self._write_skill(
            "badrolepkg",
            b"---\nname: badrolepkg\ndescription: a skill with a bad role\nrole: judge\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("role", result.stdout)
        self.assertIn("badrolepkg", result.stdout)

    def test_engine_declaring_role_other_than_none_is_error(self):
        self._write_skill(
            "someenginepkg",
            b"---\nname: someenginepkg\ndescription: an engine with a non-none role\nrole: worker\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
            tier="engines",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("engines skill must declare role: none", result.stdout)

    def test_workflow_declaring_planner_role_is_valid(self):
        self._write_skill(
            "someworkflowpkg",
            b"---\nname: someworkflowpkg\ndescription: a workflow with a non-none role\nrole: planner\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
            tier="workflows",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)

    def test_workflow_declaring_none_role_is_error(self):
        self._write_skill(
            "someworkflowpkg",
            b"---\nname: someworkflowpkg\ndescription: a glue workflow\nrole: none\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
            tier="workflows",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("workflows skill must declare planner or worker", result.stdout)

    def test_pack_declaring_role_at_all_is_error(self):
        self._write_pack(
            "somepack",
            b"---\nname: somepack\ndescription: a pack that wrongly declares a role\nrole: worker\n---\n"
            b"| slicing | x |\n",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("pack frontmatter must not declare 'role'", result.stdout)

    def test_orch_worklog_shaped_prose_does_not_warn_loop_lint(self):
        """T7: 'after every iteration or join' (frontmatter description,
        a dispatch-timing adverbial) and 'the loop's done-check' / 'a
        loop run' / 'later iteration' (noun references to another
        skill's loop, not an instruction to iterate) must not trigger
        the loop-term lint -- the false positive named in
        REVIEW-2026-08-06.md thread T7."""
        self._write_skill(
            "worklogshaped",
            b"---\nname: worklogshaped\n"
            b"description: Create or advance state. Use at start and after every iteration or join.\n"
            b"role: none\n---\n"
            b"Require: the run id -- with the spec's objective and acceptance (or\n"
            b"the loop's done-check) at creation.\n"
            b"Maintain the file: append iteration entries, failed approaches; detail\n"
            b"that decides nothing for a later iteration stays out.\n"
            b"Never: edit the frozen goal; delete a failed approach.\n"
            b"Return: the path and the next action it implies.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertEqual([], loop_lint_warnings(result.stdout), result.stdout)

    def test_orch_triage_shaped_prose_does_not_warn_loop_lint(self):
        """T7: 'never a loop' (description) and 'Never: ... an open-ended
        loop' (body) are prohibitions of looping, not instructions to
        iterate -- must not trigger the loop-term lint."""
        self._write_skill(
            "triageshaped",
            b"---\nname: triageshaped\n"
            b"description: Triage a queue into dispositions. A scheduled snapshot, never a loop.\n"
            b"role: none\n---\n"
            b"Require: the queue and the disposition vocabulary.\n"
            b"For each item, decide from the item's own content plus cheap checks.\n"
            b"Never: fix items while triaging; dispose an item on a stale read; let\n"
            b"the snapshot become an open-ended loop.\n"
            b"Return: per-item dispositions, the briefs, and queue statistics.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertEqual([], loop_lint_warnings(result.stdout), result.stdout)

    def test_genuinely_boundless_loop_mention_still_warns(self):
        """A body that actually instructs iteration, with no bound/budget
        or stalled/limited/exit/terminal term anywhere, must still WARN
        -- the narrowed heuristic must not swallow the real signal."""
        self._write_skill(
            "boundlesspkg",
            b"---\nname: boundlesspkg\ndescription: a skill that repeats work\nrole: none\n---\n"
            b"Require: a task.\n"
            b"Iterate on the task until it looks right, then repeat until the\n"
            b"reviewer is satisfied.\n"
            b"Never: skip a step.\n"
            b"Return: the result.\n",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)
        found = loop_lint_warnings(result.stdout)
        self.assertTrue(found, result.stdout)
        self.assertTrue(all("boundlesspkg" in line for line in found), found)
