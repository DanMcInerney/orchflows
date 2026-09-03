"""Validator availability and synthetic-package regression cases."""
import shutil
import subprocess
import sys

from scripts import orchflows_scaffold

from .support import ROOT, VALIDATE, _IsolatedTree, loop_lint_warnings, validate

class TestASkippedCheckSaysSo(_IsolatedTree):
    """A check that finds nothing to check has not passed.

    The isolated tree is contracts/, tools/ and tests/ -- so the checks
    keyed to skills/, packs/, example-workflows/, docs/, templates/ and
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
            "example-workflows",               # the template contract
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

    def _write_skill(self, name: str, content: bytes, tier: str = "kernel"):
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
        sits in `hosts/`, beside the records it describes.)"""
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

    def test_workflow_declaring_no_role_is_valid(self):
        """A workflow's frontmatter is the gallery home's, role included.

        The skills tier once held role-bearing driver skills, and the rule
        here read the tier name. `skills/workflows/` now holds reusable
        workflows: prose an orchestrator runs in place, invoked by name and
        never forked into a child, which is why the installer renders its
        host surfaces as a flat pointer and refuses to render a role-bearing
        one without a profile row.
        """

        self._write_skill(
            "someworkflowpkg",
            b"---\nname: someworkflowpkg\ndescription: a reusable workflow\n"
            b"disable-model-invocation: true\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
            tier="workflows",
        )
        result = self._run()
        self.assertEqual(0, result.returncode, result.stdout)

    def test_workflow_declaring_a_role_is_error(self):
        """`planner` is the role the tier rule used to require, so it is the
        one whose refusal says the rule turned over rather than loosened."""

        self._write_skill(
            "someworkflowpkg",
            b"---\nname: someworkflowpkg\ndescription: a reusable workflow\n"
            b"role: planner\ndisable-model-invocation: true\n---\n"
            b"Require: x.\nNever: y.\nReturn: z.\n",
            tier="workflows",
        )
        result = self._run()
        self.assertEqual(1, result.returncode)
        self.assertIn("never forked, so it declares no role", result.stdout)

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


class TestWorkflowLibraryHomes(_IsolatedTree):
    """Two library directories hold workflows, and one name may sit in one.

    `scripts/rings.py` resolves `skills/workflows` before
    `example-workflows`, so a name in both resolves to the first and
    silently shadows the second -- a hiding nobody authored, in the one
    kind whose body a driver reads rather than dispatches. The validator
    is where that collision is a refusal instead.
    """

    # `role` as well as the flag: `skills/workflows` is a skills tier
    # too, so a body there answers to both check sets. Everything else
    # is the minimum a skill body owes, so the only finding a case
    # below sees is the one it plants.
    BODY = (
        "---\nname: {name}\ndescription: a synthetic workflow\n"
        "role: planner\ndisable-model-invocation: true\n---\n"
        "Require: a goal.\nNever: improvise.\n"
        "Return: `tickets.py frame-close <run> <frame> --done <check>`.\n"
    )

    def _write_workflow(self, name: str, home: str, body: str = None):
        directory = self.tmp_path / home / name
        directory.mkdir(parents=True)
        (directory / "SKILL.md").write_text(
            (body or self.BODY).format(name=name), encoding="utf-8"
        )

    def test_a_workflow_in_the_skills_tier_is_graded_like_a_gallery_one(self):
        """The manual-only flag is the workflow check with no skill
        analogue, so it is the one that says which check set ran."""

        self._write_workflow(
            "nomanualflow", "skills/workflows",
            self.BODY.replace("disable-model-invocation: true\n", ""),
        )

        result = self._run()

        self.assertEqual(1, result.returncode)
        self.assertIn("must declare 'disable-model-invocation: true'", result.stdout)
        self.assertIn("nomanualflow", result.stdout)

    def test_one_name_in_both_homes_is_refused(self):
        self._write_workflow("bothflow", "skills/workflows")
        self._write_workflow("bothflow", "example-workflows")

        result = self._run()

        self.assertEqual(1, result.returncode)
        self.assertIn(
            "workflow name 'bothflow' is also at skills/workflows/bothflow/SKILL.md",
            result.stdout.replace("\\", "/"),
        )

    def test_the_same_name_in_one_home_alone_is_no_finding(self):
        """The can-fail control: the collision, not the name, is the defect."""

        self._write_workflow("bothflow", "example-workflows")

        result = self._run()

        self.assertEqual(0, result.returncode, result.stdout)
        self.assertNotIn("is also at", result.stdout)


class TestSheetAnatomy(_IsolatedTree):
    """A sheet is graded against `contracts/sheet.md`, at the tree seam.

    Every case writes one synthetic `sheets/<name>/SHEET.md` beside one
    synthetic pack and runs the whole validator, so what is checked is the
    ERROR/exit-code contract a run reads, not a helper called in isolation.
    The pack is written rather than copied because two of the checks are
    *about* the pack: which packs a sheet may be stamped beside, and which
    `## Lens` keys its adapter makes readable.
    """

    PACK = "orch-widget-pack"

    def _write_pack(self, name=None, adapter="git"):
        """The scaffold's own pack skeleton, so the fixture pack is the pack
        `orchflows new pack` writes -- a hand-rolled one drifts from what a
        real pack must carry and reds these cases on its own defects."""

        name = name or self.PACK
        pack = self.tmp_path / "packs" / name
        for relative, text in orchflows_scaffold.files_for("pack", name):
            path = pack / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative == "SKILL.md" and adapter != "git":
                text = text.replace("| adapter | git |", f"| adapter | {adapter} |")
            path.write_bytes(text.encode("utf-8"))
        return pack

    def _write_sheet(self, name: str, text: str):
        sheet = self.tmp_path / "sheets" / name
        sheet.mkdir(parents=True)
        (sheet / "SHEET.md").write_bytes(text.encode("utf-8"))
        return sheet

    def _sheet_text(self, name: str, *, packs=None, sections=None, lens=("git",)):
        packs = self.PACK if packs is None else packs
        body = sections if sections is not None else [
            ("Craft", "Narrow the craft here."),
        ]
        lines = [
            "---", f"name: {name}", "description: When to stamp it.",
            f"packs: [{packs}]", "---", "", f"# {name}", "",
        ]
        for heading, prose in body:
            lines.extend([f"## {heading}", "", prose, ""])
        lines.extend(["## Lens", ""])
        for key in lens:
            lines.extend([f"### {key}", "", f"What a {key} artifact must satisfy.", ""])
        return "\n".join(lines)

    def _errors(self, stdout, name):
        return [
            line for line in stdout.splitlines()
            if line.startswith("ERROR") and f"sheets/{name}" in line
        ]

    def test_a_well_formed_sheet_passes(self):
        self._write_pack()
        self._write_sheet("market-brief", self._sheet_text("market-brief"))

        result = self._run()

        self.assertEqual([], self._errors(result.stdout, "market-brief"))
        self.assertEqual(0, result.returncode, result.stdout)

    def test_a_pack_only_section_inside_a_sheet_is_refused(self):
        """`## Workspace` states identities and isolation -- a fact about the
        domain, which the pack owns. A sheet carrying it is a second owner."""

        self._write_pack()
        self._write_sheet("market-brief", self._sheet_text(
            "market-brief",
            sections=[("Craft", "Narrow it."), ("Workspace", "Commits, branches.")],
        ))

        result = self._run()

        self.assertEqual(1, result.returncode)
        self.assertTrue(
            any("## Workspace" in line for line in self._errors(result.stdout, "market-brief")),
            result.stdout,
        )

    def test_a_scripts_directory_inside_a_sheet_is_refused(self):
        """A sheet carries prose and nothing executable, so it declares no
        dependencies and owns no environment."""

        self._write_pack()
        sheet = self._write_sheet("market-brief", self._sheet_text("market-brief"))
        (sheet / "scripts").mkdir()
        (sheet / "scripts" / "run.py").write_text("print(1)\n", encoding="utf-8")

        result = self._run()

        self.assertEqual(1, result.returncode)
        self.assertTrue(
            any("'scripts'" in line for line in self._errors(result.stdout, "market-brief")),
            result.stdout,
        )

    def test_a_requirements_file_inside_a_sheet_is_refused(self):
        self._write_pack()
        sheet = self._write_sheet("market-brief", self._sheet_text("market-brief"))
        (sheet / "requirements.txt").write_text("requests\n", encoding="utf-8")

        result = self._run()

        self.assertEqual(1, result.returncode)
        self.assertTrue(
            any("'requirements.txt'" in line for line in self._errors(result.stdout, "market-brief")),
            result.stdout,
        )

    def test_a_packs_name_that_resolves_to_no_pack_is_refused(self):
        self._write_pack()
        self._write_sheet("market-brief", self._sheet_text(
            "market-brief", packs="orch-absent-pack",
        ))

        result = self._run()

        self.assertEqual(1, result.returncode)
        self.assertTrue(
            any("orch-absent-pack" in line for line in self._errors(result.stdout, "market-brief")),
            result.stdout,
        )

    def test_a_lens_entry_keyed_by_a_kind_the_named_pack_never_emits_is_refused(self):
        """The key selects the entry a child is sent to. An entry under a
        kind that pack's adapter does not emit is criteria nothing reads."""

        self._write_pack()
        self._write_sheet("market-brief", self._sheet_text(
            "market-brief", lens=("doc",),
        ))

        result = self._run()

        self.assertEqual(1, result.returncode)
        self.assertTrue(
            any("### doc" in line for line in self._errors(result.stdout, "market-brief")),
            result.stdout,
        )

    def test_a_sheet_over_the_budget_is_refused(self):
        self._write_pack()
        self._write_sheet("market-brief", self._sheet_text(
            "market-brief",
            sections=[("Craft", "\n".join(f"- clause {n}" for n in range(120)))],
        ))

        result = self._run()

        self.assertEqual(1, result.returncode)
        self.assertTrue(
            any("sheet budget" in line for line in self._errors(result.stdout, "market-brief")),
            result.stdout,
        )

    def test_a_missing_mandatory_section_is_refused(self):
        self._write_pack()
        self._write_sheet("market-brief", self._sheet_text(
            "market-brief", sections=[],
        ).replace("## Lens", "## Vocabulary"))

        result = self._run()

        self.assertEqual(1, result.returncode)
        errors = " ".join(self._errors(result.stdout, "market-brief"))
        self.assertIn("## Craft", errors)
        self.assertIn("## Lens", errors)
