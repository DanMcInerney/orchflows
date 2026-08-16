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


if __name__ == "__main__":
    unittest.main()
