"""Template budget, producer/consumer closure, and canonical-tree cases."""

import contextlib
import os
import tempfile
import unittest
from pathlib import Path

from tests.test_templates_cases.shape import (
    GOOD_CRITERION,
    GOOD_STUBS,
    ROOT,
    _TemplateTree,
    literal_input,
    stub_md,
    template_md,
    tickets,
    validate,
)

class TestTemplateBudgets(_TemplateTree):
    """rules/token-economy.md §11: a stub's instruction and a manifest are
    every-dispatch and every-run units with word ceilings; a stub's fixed
    input records never count."""

    EXCLUDED_ACTIONS = (
        "excluded_actions:\n  - adding a third-party dependency\n"
        "  - editing a T0 contract\n"
    )

    def stub_at(self, words):
        """One stub carrying excluded actions, its objective padded until
        `tickets.instruction_words` reads exactly `words`.

        Measured against the owner rather than recomputed here: what the
        caller pins is that the compiler reaches the same number, which it
        can only do by asking the owner.
        """

        def render(objective):
            text = stub_md("repair", depends="[diagnose]")
            text = text.replace("bound:", self.EXCLUDED_ACTIONS + "bound:")
            return text.replace("one repaired tree at {{target}}.", objective)

        spent = tickets.instruction_words(render("word")) - 1
        return render(" ".join(["word"] * (words - spent)))

    def test_a_stub_whose_instruction_exceeds_the_budget_is_one_error(self):
        fat = "- " + " ".join(["criterion"] * 320) + " | oracle: x | oracle_class: deterministic\n"
        stubs = dict(GOOD_STUBS)
        stubs["repair"] = stub_md("repair", depends="[diagnose]", criteria=(fat.strip("- \n"),))
        self.write_template("demo", stubs=stubs)
        error = self.assert_one_error("repair.md")
        self.assertIn("stub instruction has", error)
        self.assertIn(f"budget of {tickets.INSTRUCTION_BUDGET}", error)

    def test_the_compiler_puts_the_boundary_where_the_ticket_owner_puts_it(self):
        """A stub is a ticket before it is issued, and rules/token-economy.md
        §11 is one ceiling: the compiler grading the template and the script
        refusing the issued ticket have to put the boundary in the same
        place. This compiler kept a counter of its own, and that one charged
        an excluded action a word for its list marker -- so a stub the sink
        accepts at the ceiling was two words over here."""

        stubs = dict(GOOD_STUBS)
        stubs["repair"] = self.stub_at(tickets.INSTRUCTION_BUDGET)
        self.write_template("demo", stubs=stubs)
        result, errors = self.diagnostics()
        self.assertEqual([], errors, result.stdout)

    def test_fixed_inputs_do_not_count_toward_the_stub_budget(self):
        stubs = dict(GOOD_STUBS)
        text = stub_md("repair", depends="[diagnose]")
        text = text.replace(
            literal_input("defect", "the defect report"),
            literal_input("evidence", " ".join(["identity"] * 400)),
        )
        stubs["repair"] = text
        self.write_template("demo", stubs=stubs)
        result, errors = self.diagnostics()
        self.assertEqual([], errors, result.stdout)

    def test_a_manifest_over_the_budget_is_one_error(self):
        body = " ".join(["word"] * (validate.MANIFEST_BUDGET + 20))
        self.write_template("demo", manifest=template_md(body=body))
        error = self.assert_one_error("template.md")
        self.assertIn("manifest has", error)


DEFAULT_INPUTS = literal_input("defect", "the defect report")
DEFAULT_RETURNS = "status; result identity; verification\n"


def closure_stub(stub_id, inputs, returns=None, depends="[]", criteria=(GOOD_CRITERION,)):
    """One stub whose `## Fixed inputs` and `## Return fields` are the
    test's own: the closure law is about what those two sections say."""

    text = stub_md(stub_id, depends=depends, criteria=criteria)
    text = text.replace(DEFAULT_INPUTS, inputs)
    if returns is not None:
        text = text.replace(DEFAULT_RETURNS, returns)
    return text


class TestProducerConsumerClosure(_TemplateTree):
    """contracts/work-item.md: a stub's criteria may read an upstream
    Result, and inside a template the identities on offer are what the stubs
    before it return plus what instantiation supplies. A stub reading
    `<other>'s ## Result` for something that stub's `## Return fields` never
    names is a thread with a producer at one end and nothing at the other --
    eleven of eighteen composition threads in the 2026-08-16 review broke
    exactly there, and every one of them instantiated cleanly.
    """

    PRODUCER = closure_stub(
        "00",
        literal_input("failure", "the failing command"),
        returns="status; result -- the reproduction identity; verification\n",
    )

    def _template(self, consumer, extra=None):
        stubs = {"00": self.PRODUCER, "01": consumer}
        stubs.update(extra or {})
        return self.write_template("demo", stubs=stubs)

    def messages(self, directory):
        return [message for _, message in tickets.template_defects(directory)]

    def test_a_field_the_producer_never_returns_breaks_closure(self):
        directory = self._template(
            closure_stub(
                "01",
                DEFAULT_INPUTS,
                depends="[00]",
                criteria=(
                    "the repair holds | oracle: the promotion rule and the margin "
                    "from 00's Result | oracle_class: deterministic | "
                    "provenance: pre-existing",
                ),
            )
        )
        messages = self.messages(directory)
        self.assertEqual(1, len(messages), messages)
        self.assertIn("01", messages[0])
        self.assertIn("00", messages[0], "the missing producer goes unnamed")
        self.assertIn("promotion rule", messages[0])
        self.assertIn("margin", messages[0])

    def test_a_field_the_producer_returns_keeps_closure(self):
        directory = self._template(
            closure_stub(
                "01",
                inputs=DEFAULT_INPUTS,
                depends="[00]",
                criteria=(
                    "the repair holds | oracle: the reproduction identity from "
                    "00's Result | oracle_class: deterministic | "
                    "provenance: pre-existing",
                ),
            )
        )
        self.assertEqual([], self.messages(directory))

    def test_an_oracle_reading_a_field_no_producer_returns_breaks_closure(self):
        """A criterion reads upstream too -- `the promotion rule from 00's
        Result` -- and the seam is the same one."""

        directory = self._template(
            closure_stub(
                "01",
                DEFAULT_INPUTS,
                depends="[00]",
                criteria=(
                    "the repair holds | oracle: the promotion rule from 00's "
                    "Result | oracle_class: deterministic | provenance: pre-existing",
                ),
            )
        )
        messages = self.messages(directory)
        self.assertEqual(1, len(messages), messages)
        self.assertIn("promotion rule", messages[0])

    def test_reading_a_stub_that_is_not_in_the_template_breaks_closure(self):
        directory = self._template(
            closure_stub(
                "01",
                depends="[00]",
                inputs=DEFAULT_INPUTS,
                criteria=(
                    "the repair holds | oracle: the reproduction identity from "
                    "99's Result | oracle_class: deterministic | "
                    "provenance: pre-existing",
                ),
            )
        )
        messages = self.messages(directory)
        self.assertEqual(1, len(messages), messages)
        self.assertIn("99", messages[0])

    def test_reading_a_stub_it_does_not_depend_on_breaks_closure(self):
        """Nothing orders an unordered producer before its reader: at
        dispatch the reader is ready while the field it names is unwritten."""

        directory = self._template(
            closure_stub(
                "01",
                DEFAULT_INPUTS,
                criteria=(
                    "the repair holds | oracle: the reproduction identity from "
                    "00's Result | oracle_class: deterministic | "
                    "provenance: pre-existing",
                ),
            ),
            extra={"02": closure_stub("02", DEFAULT_INPUTS, depends="[00, 01]")},
        )
        messages = self.messages(directory)
        self.assertEqual(1, len(messages), messages)
        self.assertIn("01", messages[0])
        self.assertIn("00", messages[0])

    def test_an_instantiation_supplied_identity_keeps_closure(self):
        """A canonical literal holding `{{placeholder}}` is produced by
        the manifest, not by a stub; whether it is declared is
        tools/validate.py's, so nothing here reports it twice -- and the
        instantiator, which sees the filled value, agrees with the
        validator, which sees the placeholder."""

        directory = self._template(
            closure_stub(
                "01",
                literal_input("target", "{{target}}"),
                depends="[00]",
            )
        )
        self.assertEqual([], self.messages(directory))
        with _temporary_sink():
            result = tickets._cmd_instantiate(
                [str(directory), "--run", "20260101T000000Z-closure",
                 "--set", "target=zebra-thing"]
            )
        self.assertNotIn("error", result, result)

    def test_a_placeholder_beside_a_field_no_producer_returns_breaks_closure(self):
        """The placeholder is produced; the words beside it are still a
        claim on the producer, at the validator and at instantiation."""

        directory = self._template(
            closure_stub(
                "01",
                depends="[00]",
                inputs=literal_input("target", "{{target}}"),
                criteria=(
                    "the repair holds | oracle: the promotion rule for {{target}} "
                    "from 00's Result | oracle_class: deterministic | "
                    "provenance: pre-existing",
                ),
            )
        )
        messages = self.messages(directory)
        self.assertEqual(1, len(messages), messages)
        self.assertIn("promotion rule", messages[0])
        with _temporary_sink() as sink:
            result = tickets._cmd_instantiate(
                [str(directory), "--run", "20260101T000000Z-closure",
                 "--set", "target=x"]
            )
            self.assertIn("error", result)
            self.assertIn("promotion rule", result["error"])
            self.assertEqual([], sorted((sink / "tickets").glob("*/*.md")))

    def test_the_validator_reports_the_broken_closure_as_one_error(self):
        self._template(
            closure_stub(
                "01",
                DEFAULT_INPUTS,
                depends="[00]",
                criteria=(
                    "the repair holds | oracle: the promotion rule from 00's "
                    "Result | oracle_class: deterministic | provenance: pre-existing",
                ),
            )
        )
        error = self.assert_one_error("compositions/demo/01.md")
        self.assertIn("promotion rule", error)

    def test_instantiate_refuses_a_template_whose_closure_is_broken(self):
        directory = self._template(
            closure_stub(
                "01",
                DEFAULT_INPUTS,
                depends="[00]",
                criteria=(
                    "the repair holds | oracle: the promotion rule from 00's "
                    "Result | oracle_class: deterministic | provenance: pre-existing",
                ),
            )
        )
        with _temporary_sink() as sink:
            result = tickets._cmd_instantiate(
                [str(directory), "--run", "20260101T000000Z-closure", "--set", "target=x"]
            )
            self.assertIn("error", result)
            self.assertIn("promotion rule", result["error"])
            self.assertEqual([], sorted((sink / "tickets").glob("*/*.md")))


@contextlib.contextmanager
def _temporary_sink():
    """A state sink of this run's own, so instantiating writes nowhere the
    user can see."""

    variable = tickets.state_root.ENV_VAR
    previous = os.environ.get(variable)
    with tempfile.TemporaryDirectory() as tmp:
        os.environ[variable] = tmp
        try:
            yield Path(tmp)
        finally:
            if previous is None:
                os.environ.pop(variable, None)
            else:
                os.environ[variable] = previous


class TestCanonicalTemplatesClose(unittest.TestCase):
    """The seven templates in the tree, against the same law: every
    identity a stub reads is one a stub before it returns or one
    instantiation supplies, and each template still instantiates whole."""

    def directories(self):
        found = sorted(
            path.parent for path in (ROOT / "compositions").glob("*/template.md")
        )
        self.assertGreaterEqual(len(found), 7, "the canonical templates are missing")
        return found

    def test_every_canonical_template_holds_its_closure(self):
        for directory in self.directories():
            with self.subTest(template=directory.name):
                self.assertEqual(
                    [], [message for _, message in tickets.template_defects(directory)]
                )

    def test_every_canonical_template_instantiates_under_closure(self):
        placeholders = {
            "executor": "orch-tdd",
            "isolation": "required",
            "mutations": "change:scripts/a.py",
            "oracle_command": "uv run --no-project python -m unittest tests.test_templates",
            "oracle_name": "the named fixture oracle",
            "oracle_provenance": "pre-existing",
            "paths": "scripts/a.py",
            "simple_task": "Deliver one simple code change.",
        }
        for directory in self.directories():
            manifest = tickets._parse_frontmatter(
                (directory / tickets.TEMPLATE_FILE).read_text(encoding="utf-8")
            )
            settings = []
            for name in manifest.get("placeholders") or []:
                value = (
                    "<= 40 tool calls"
                    if name == "bound"
                    else placeholders.get(name, f"{name}-identity")
                )
                settings += ["--set", f"{name}={value}"]
            with self.subTest(template=directory.name), _temporary_sink():
                result = tickets._cmd_instantiate(
                    [str(directory), "--run", f"20260101T000000Z-{directory.name}"]
                    + settings
                )
                self.assertNotIn("error", result, result)
