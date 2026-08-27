"""Behavioral cases imported by the ``tests.test_tickets_issue`` seam."""

from .common import *  # noqa: F401,F403

SYNTH_PACK = """---
name: orch-synth-pack
description: a synthetic pack
---

| cell | binding |
| --- | --- |
| executor | `orch-tdd` |
| required_spec_fields | target repository; standards owner by pointer; \
acceptance as runnable checks — the commands that decide it |
"""


def make_pack(root: Path, name: str = "orch-synth-pack", text: str = SYNTH_PACK) -> Path:
    """A stamped pack beside the template, as the library tree lays them out."""

    path = root / "packs" / name
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(text, encoding="utf-8")
    return path


def root_stub(fixed_inputs: str, pack: str = "orch-synth-pack") -> str:
    """A root stub: the decomposer, a stamped pack, and one Fixed inputs."""

    return stub("A", executor="orch-decompose", scope="scratch/x.txt").replace(
        "executor: orch-decompose", f"executor: orch-decompose\npack: {pack}"
    ).replace(
        '- input: {"name":"none","type":"literal","value":null}',
        fixed_inputs.rstrip("\n"),
    )


class RootStubSpecFieldsTest(unittest.TestCase):
    """contracts/work-item.md: the stamped pack's `required_spec_fields` are
    entries of the root ticket's `## Fixed inputs`, and orch-decompose's
    Require rejects a root that lacks them.

    That refusal fires inside the decomposer — after dispatch, in a child's
    context, against a ticket already written. `packet` grades shape and
    passes these through, so a template could ship a root stub its own
    executor cannot run and nothing said so until an agent was spending on
    it. The check belongs where the stub is admitted."""

    def defects(self, directory: Path):
        return [message for _, message in tickets_mod.template_defects(directory)]

    def test_a_root_stub_naming_none_of_the_required_fields_is_a_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            make_pack(tmp)
            directory = make_template(tmp, {
                "A": root_stub('- input: {"name":"directory","type":"literal","value":"items to cut"}\n'),
                "B": stub("B", "[A]"),
            })
            defects = self.defects(directory)
            self.assertEqual(1, len(defects), defects)
            for field in ("target repository", "standards owner by pointer",
                          "acceptance as runnable checks"):
                self.assertIn(field, defects[0])
            self.assertIn("orch-synth-pack", defects[0])

    def test_a_root_stub_naming_a_required_field_is_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            make_pack(tmp)
            directory = make_template(tmp, {
                "A": root_stub('- input: {"name":"target-repository","type":"literal","value":"scripts/"}\n'),
                "B": stub("B", "[A]"),
            })
            self.assertEqual([], self.defects(directory))

    def test_a_non_root_stub_is_not_asked_for_the_fields(self):
        """`pack` is optional on a unit stub and binds its workspace cell,
        not a cut. Only the ticket a decomposition is cut from carries the
        spec's fields."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            make_pack(tmp)
            unit = stub("A", scope="scratch/x.txt").replace(
                "pack: orch-code-pack", "pack: orch-synth-pack"
            )
            directory = make_template(tmp, {"A": unit, "B": stub("B", "[A]")})
            self.assertEqual([], self.defects(directory))

    def test_a_placeholder_pack_is_graded_once_instantiation_fills_it(self):
        """A stub whose pack is `{{pack}}` names no pack to read until a
        caller supplies one — and then it does, so instantiate applies the
        same check the tree's own grading applies."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            make_pack(tmp)
            directory = make_template(tmp, {
                "A": root_stub('- input: {"name":"directory","type":"literal","value":"items to cut"}\n', pack="{{pack}}"),
                "B": stub("B", "[A]"),
            })
            self.assertEqual([], self.defects(directory))

            payload = run_cmd(
                "instantiate", str(directory), "--run", "testrun",
                "--set", "pack=orch-synth-pack", "--set", "target=scripts/a.py",
            )
            self.assertIn("error", payload)
            self.assertIn("target repository", payload["error"])

    def test_a_tree_with_no_packs_directory_grades_nothing(self):
        """An installed copy of this script runs against a target repository
        that carries no `packs/` at all. No pack to read is not a defect in
        the stub."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, {
                "A": root_stub('- input: {"name":"directory","type":"literal","value":"items to cut"}\n'),
                "B": stub("B", "[A]"),
            })
            self.assertEqual([], self.defects(directory))
