"""tools/validate.py's ticket-template checks: a template is a directory
`compositions/<name>/` holding `template.md` plus one ticket stub per
other `*.md` file (SPEC-ticket-set.md s2-s3, contracts/work-item.md).

Runs on the isolated tmp-tree harness tests/test_validator.py owns, so
every check is exercised at the real ROOT-relative seam.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.tickets as tickets  # noqa: E402  the ticket-shape law's one owner
from tests.test_validator import _IsolatedTree  # noqa: E402  the harness's one owner

STUB_SECTIONS = (
    "Objective",
    "Fixed inputs",
    "Completion test",
    "Return fields",
    "Result",
    "Verification",
    "Feedback",
    "Risks",
)
GOOD_CRITERION = (
    "the repaired tree passes its suite | oracle: the suite "
    "| oracle_class: deterministic | provenance: pre-existing"
)
MINIMAL_SKILL = (
    "---\nname: {name}\ndescription: a synthetic skill standing in as an "
    "executor\nrole: worker\n---\nRequire: x.\nNever: y.\nReturn: z.\n"
)


def template_md(
    name="demo",
    entry="named",
    placeholders="[target]",
    description="a synthetic template exercising the template checks",
    body="Repair one defect in {{target}} and prove the repair.",
    drop=(),
):
    """The template.md manifest; `drop` omits frontmatter keys by name."""
    fields = [
        ("name", name),
        ("description", description),
        ("entry", entry),
        ("placeholders", placeholders),
    ]
    lines = ["---"]
    lines += [f"{key}: {value}" for key, value in fields if key not in drop]
    lines += ["---", "", body, ""]
    return "\n".join(lines)


def _section_body(section, criteria):
    if section == "Objective":
        return "one repaired tree at {{target}}.\n"
    if section == "Fixed inputs":
        return "- the defect report\n"
    if section == "Completion test":
        return "".join(f"- {criterion}\n" for criterion in criteria)
    if section == "Return fields":
        return "status; result identity; verification\n"
    if section in ("Feedback", "Risks"):
        return "[]\n"
    return ""


def stub_md(
    stub_id,
    executor="orch-repair",
    depends="[]",
    write_scope="[{{target}}]",
    bound="<= 20 tool calls",
    criteria=(GOOD_CRITERION,),
    sections=STUB_SECTIONS,
    drop=(),
):
    """One ticket stub: contracts/work-item.md's shape minus run, status
    and claimed_*; `drop` omits frontmatter keys by name."""
    fields = [
        ("id", stub_id),
        ("executor", executor),
        ("depends_on", depends),
        ("write_scope", write_scope),
        ("bound", bound),
    ]
    lines = ["---"]
    lines += [f"{key}: {value}" for key, value in fields if key not in drop]
    lines += ["---", ""]
    for section in sections:
        lines += [f"## {section}", "", _section_body(section, criteria)]
    return "\n".join(lines)


GOOD_STUBS = {
    "diagnose": stub_md("diagnose"),
    "repair": stub_md("repair", depends="[diagnose]"),
    "verify": stub_md("verify", depends="[repair]"),
}


class _TemplateTree(_IsolatedTree):
    """An isolated tree carrying one resolvable executor skill, onto
    which each test writes a template directory."""

    def setUp(self):
        super().setUp()
        self.write_skill("orch-repair")

    def write_skill(self, name, tier="instances"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            MINIMAL_SKILL.format(name=name), encoding="utf-8"
        )

    def write_template(self, name, manifest=None, stubs=None):
        directory = self.tmp_path / "compositions" / name
        directory.mkdir(parents=True)
        (directory / "template.md").write_text(
            manifest if manifest is not None else template_md(name=name),
            encoding="utf-8",
        )
        for stub_id, text in (GOOD_STUBS if stubs is None else stubs).items():
            (directory / f"{stub_id}.md").write_text(text, encoding="utf-8")
        return directory

    def diagnostics(self, level="ERROR"):
        result = self._run()
        return result, [
            line for line in result.stdout.splitlines() if line.startswith(level)
        ]

    def assert_one_error(self, naming):
        """Exactly one ERROR line, naming `naming`."""
        result, errors = self.diagnostics()
        self.assertEqual(1, len(errors), result.stdout)
        self.assertIn(naming, errors[0])
        self.assertEqual(1, result.returncode)
        return errors[0]


class TestTemplateManifest(_TemplateTree):
    def test_a_clean_three_stub_template_passes(self):
        self.write_template("demo")
        result, errors = self.diagnostics()
        self.assertEqual([], errors)
        self.assertEqual(0, result.returncode, result.stdout)

    def test_name_not_matching_the_directory_is_one_error(self):
        self.write_template("demo", manifest=template_md(name="other"))
        self.assert_one_error("compositions/demo/template.md")

    def test_entry_outside_the_closed_set_is_an_error(self):
        self.write_template("demo", manifest=template_md(entry="scheduled"))
        _, errors = self.diagnostics()
        self.assertEqual(1, len(errors))
        self.assertIn("entry 'scheduled'", errors[0])

    def test_an_over_budget_description_is_an_error(self):
        self.write_template("demo", manifest=template_md(description="x" * 141))
        _, errors = self.diagnostics()
        self.assertEqual(1, len(errors))
        self.assertIn("141 chars", errors[0])

    def test_placeholders_that_are_not_a_list_is_an_error(self):
        self.write_template("demo", manifest=template_md(placeholders="target"))
        _, errors = self.diagnostics()
        self.assertIn("'placeholders' is not a list", errors[0])

    def test_a_directory_without_template_md_is_not_a_template(self):
        stray = self.tmp_path / "compositions" / "references"
        stray.mkdir(parents=True)
        (stray / "notes.md").write_text("# notes\n", encoding="utf-8")
        result, errors = self.diagnostics()
        self.assertEqual([], errors)
        self.assertEqual(0, result.returncode, result.stdout)


class TestStubShape(_TemplateTree):
    """contracts/work-item.md's frontmatter and body law, on a stub."""

    def _with(self, stub_id, text):
        stubs = dict(GOOD_STUBS)
        stubs[stub_id] = text
        return stubs

    def test_a_stub_without_an_executor_is_one_error(self):
        self.write_template(
            "demo",
            stubs=self._with("repair", stub_md("repair", depends="[diagnose]", drop=("executor",))),
        )
        error = self.assert_one_error("compositions/demo/repair.md")
        self.assertIn("'executor'", error)

    def test_a_stub_id_not_matching_its_file_stem_is_one_error(self):
        self.write_template(
            "demo",
            stubs=self._with("repair", stub_md("repare", depends="[diagnose]")),
        )
        error = self.assert_one_error("compositions/demo/repair.md")
        self.assertIn("'repare'", error)

    def test_depends_on_that_is_not_a_list_is_an_error(self):
        self.write_template(
            "demo", stubs=self._with("repair", stub_md("repair", depends="diagnose"))
        )
        _, errors = self.diagnostics()
        self.assertIn("'depends_on' is not a list", errors[0])

    def test_a_stub_missing_a_body_section_is_one_error(self):
        sections = tuple(s for s in STUB_SECTIONS if s != "Completion test")
        self.write_template(
            "demo",
            stubs=self._with("repair", stub_md("repair", depends="[diagnose]", sections=sections)),
        )
        error = self.assert_one_error("compositions/demo/repair.md")
        self.assertIn("## Completion test", error)

    def test_a_stub_with_sections_out_of_order_is_one_error(self):
        swapped = list(STUB_SECTIONS)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        self.write_template(
            "demo",
            stubs=self._with(
                "repair", stub_md("repair", depends="[diagnose]", sections=tuple(swapped))
            ),
        )
        error = self.assert_one_error("compositions/demo/repair.md")
        self.assertIn("order", error)

    def test_a_criterion_without_an_oracle_class_is_one_error(self):
        self.write_template(
            "demo",
            stubs=self._with(
                "repair",
                stub_md(
                    "repair",
                    depends="[diagnose]",
                    criteria=("the tree passes its suite | oracle: the suite",),
                ),
            ),
        )
        error = self.assert_one_error("compositions/demo/repair.md")
        self.assertIn("oracle_class", error)

    def test_a_criterion_without_an_oracle_is_one_error(self):
        self.write_template(
            "demo",
            stubs=self._with(
                "repair",
                stub_md(
                    "repair",
                    depends="[diagnose]",
                    criteria=("the tree passes | oracle_class: deterministic",),
                ),
            ),
        )
        error = self.assert_one_error("compositions/demo/repair.md")
        self.assertIn("oracle:", error)

    def test_an_oracle_class_outside_the_closed_set_is_one_error(self):
        self.write_template(
            "demo",
            stubs=self._with(
                "repair",
                stub_md(
                    "repair",
                    depends="[diagnose]",
                    criteria=("the tree passes | oracle: the suite | oracle_class: vibes",),
                ),
            ),
        )
        error = self.assert_one_error("compositions/demo/repair.md")
        self.assertIn("'vibes'", error)

    def test_a_completion_test_with_no_criterion_is_one_error(self):
        self.write_template(
            "demo",
            stubs=self._with("repair", stub_md("repair", depends="[diagnose]", criteria=())),
        )
        error = self.assert_one_error("compositions/demo/repair.md")
        self.assertIn("no criterion", error)


class TestStubGraph(_TemplateTree):
    """The depends_on graph: every edge lands inside the template, the
    graph is acyclic, and exactly one stub is terminal.

    All three are reported at the manifest, in scripts/tickets.py's words:
    the graph is the template's property, not any one stub's, and the
    script that instantiates it is the law's one owner. Each message still
    names the stub it found the defect at.
    """

    def test_a_cycle_is_one_error_naming_the_template(self):
        self.write_template(
            "demo",
            stubs={
                "diagnose": stub_md("diagnose", depends="[verify]"),
                "repair": stub_md("repair", depends="[diagnose]"),
                "verify": stub_md("verify", depends="[repair]"),
            },
        )
        error = self.assert_one_error("compositions/demo/template.md")
        self.assertIn("cyclic", error)

    def test_a_stub_depending_on_itself_is_a_cycle(self):
        self.write_template(
            "demo",
            stubs={
                "diagnose": stub_md("diagnose"),
                "repair": stub_md("repair", depends="[diagnose]"),
                "verify": stub_md("verify", depends="[repair, verify]"),
            },
        )
        error = self.assert_one_error("compositions/demo/template.md")
        self.assertIn("cyclic", error)
        self.assertIn("verify", error)

    def test_two_terminal_stubs_is_one_error(self):
        self.write_template(
            "demo",
            stubs={
                "diagnose": stub_md("diagnose"),
                "repair": stub_md("repair", depends="[diagnose]"),
                "verify": stub_md("verify"),
            },
        )
        error = self.assert_one_error("compositions/demo/template.md")
        self.assertIn("terminal", error)
        self.assertIn("repair", error)
        self.assertIn("verify", error)

    def test_depends_on_naming_a_stub_outside_the_template_is_one_error(self):
        stubs = dict(GOOD_STUBS)
        stubs["repair"] = stub_md("repair", depends="[diagnose, triage]")
        self.write_template("demo", stubs=stubs)
        error = self.assert_one_error("compositions/demo/template.md")
        self.assertIn("'triage'", error)
        self.assertIn("repair", error, "the edge's own stub goes unnamed")


class TestPlaceholders(_TemplateTree):
    """Every `{{placeholder}}` a stub uses is declared in template.md;
    a declared placeholder no stub uses is a WARN, never an ERROR."""

    def test_a_placeholder_no_stub_declares_is_one_error(self):
        stubs = dict(GOOD_STUBS)
        stubs["repair"] = stub_md("repair", depends="[diagnose]", write_scope="[{{scope}}]")
        self.write_template("demo", stubs=stubs)
        error = self.assert_one_error("compositions/demo/repair.md")
        self.assertIn("{{scope}}", error)

    def test_a_declared_placeholder_no_stub_uses_is_a_warn_not_an_error(self):
        self.write_template("demo", manifest=template_md(placeholders="[target, spare]"))
        result, errors = self.diagnostics()
        self.assertEqual([], errors)
        self.assertEqual(0, result.returncode, result.stdout)
        warns = [
            line for line in result.stdout.splitlines()
            if line.startswith("WARN") and "compositions/demo" in line
        ]
        self.assertEqual(1, len(warns), result.stdout)
        self.assertIn("{{spare}}", warns[0])


class TestStubExecutorResolves(_TemplateTree):
    """A stub's executor names a skill in the tree or a script that
    exists (SPEC-ticket-set.md s3: `executor: script:<path>`)."""

    def _with_executor(self, executor):
        stubs = dict(GOOD_STUBS)
        stubs["repair"] = stub_md("repair", depends="[diagnose]", executor=executor)
        return stubs

    def test_an_executor_naming_no_skill_in_the_tree_is_one_error(self):
        self.write_template("demo", stubs=self._with_executor("orch-nonesuch"))
        error = self.assert_one_error("compositions/demo/repair.md")
        self.assertIn("orch-nonesuch", error)

    def test_a_script_executor_whose_path_exists_passes(self):
        self.write_template("demo", stubs=self._with_executor("script:tools/validate.py"))
        result, errors = self.diagnostics()
        self.assertEqual([], errors)
        self.assertEqual(0, result.returncode, result.stdout)

    def test_a_script_executor_whose_path_is_absent_is_one_error(self):
        self.write_template("demo", stubs=self._with_executor("script:scripts/absent.py"))
        error = self.assert_one_error("compositions/demo/repair.md")
        self.assertIn("scripts/absent.py", error)

    def test_an_executor_carrying_a_placeholder_is_left_to_instantiation(self):
        stubs = dict(GOOD_STUBS)
        stubs["repair"] = stub_md("repair", depends="[diagnose]", executor="{{writer}}")
        self.write_template(
            "demo", manifest=template_md(placeholders="[target, writer]"), stubs=stubs
        )
        result, errors = self.diagnostics()
        self.assertEqual([], errors)
        self.assertEqual(0, result.returncode, result.stdout)


class TestTheValidatorRefusesWhatTheOwnerRefuses(_TemplateTree):
    """`scripts/tickets.py` is the one owner of ticket-shape and
    template-graph law: `tickets.py new` and `instantiate` grade through
    it, and the validator now reads it instead of carrying a second
    spelling. Two spellings is how a stub the cutter admits is refused by
    the dispatcher — the P1 gate found the two disagreeing on eight inputs
    and on which executors are legal.

    So the assertion is not that the validator reports *something*: it is
    that every refusal the owner reports comes back word for word.
    """

    # One template per defect, all in one tree, so the whole set is read
    # from a single validate run.
    OFF_CONTRACT = {
        "noclass": stub_md(
            "repair", depends="[diagnose]",
            criteria=("the tree passes its suite | oracle: the suite",),
        ),
        "wrongclass": stub_md(
            "repair", depends="[diagnose]",
            criteria=("the tree passes | oracle: the suite | oracle_class: vibes",),
        ),
        "nosection": stub_md(
            "repair", depends="[diagnose]",
            sections=tuple(s for s in STUB_SECTIONS if s != "Feedback"),
        ),
        # An engine dispatches a ticket's executor and cannot be one: the
        # validator admitted orch-compose and orch-panel while
        # tickets.py refused them, so a template it passed could not be
        # instantiated.
        "engine": stub_md("repair", depends="[diagnose]", executor="orch-panel"),
        "noframes": "id: repair\nexecutor: orch-repair\n\n## Objective\n\nnone.\n",
    }

    def _write_all(self):
        # The engine case is about legality, not resolution: with the skill
        # in the tree the validator's own executor check passes, so the one
        # ERROR left on that stub is the owner's refusal.
        self.write_skill("orch-panel", tier="engines")
        for name, bad in sorted(self.OFF_CONTRACT.items()):
            stubs = dict(GOOD_STUBS)
            stubs["repair"] = bad
            self.write_template(name, manifest=template_md(name=name), stubs=stubs)

    def test_every_refusal_the_owner_reports_comes_back_verbatim(self):
        self._write_all()
        result = self._run()
        reported = 0
        for name in sorted(self.OFF_CONTRACT):
            directory = self.tmp_path / "compositions" / name
            defects = tickets.template_defects(directory)
            self.assertTrue(defects, f"{name}: the owner refuses nothing")
            for path, message in defects:
                reported += 1
                with self.subTest(template=name, message=message[:50]):
                    self.assertIn(message, result.stdout)
                    self.assertIn(
                        Path(path).name, result.stdout,
                        "the finding does not name the file it is about",
                    )
        self.assertEqual(1, result.returncode, result.stdout)
        self.assertTrue(reported)

    def test_the_owner_and_the_validator_refuse_the_same_stubs(self):
        """The other direction: no ERROR the validator reports about a
        stub is one the owner would admit. Without it the validator could
        keep a private refusal and the two would disagree again."""

        self._write_all()
        result = self._run()
        owned = set()
        for name in sorted(self.OFF_CONTRACT):
            for _, message in tickets.template_defects(
                self.tmp_path / "compositions" / name
            ):
                owned.add(message)
        stray = [
            line for line in result.stdout.splitlines()
            if line.startswith("ERROR") and "/repair.md" in line
            and not any(message in line for message in owned)
        ]
        self.assertEqual([], stray, result.stdout)


if __name__ == "__main__":
    unittest.main()
