"""The command surface tells the truth about itself.

Two separate claims live here, and they fail for different reasons.

The first is that every operator a skill *requires* is one it *names*. A
skill that says "write one composite gate" without naming `tickets.py gate`
leaves the reader to rediscover the operator, and the v2 lifecycle -- draft
validation, the seal, the typed amendment request -- was reachable only by
reading `scripts/tickets_generations.py`. Naming is the whole fix; these
tests pin that the names stay.

The second is the converse, and it is the one that rots silently: no skill
may name a command `tickets.py` does not route. A deleted or renamed
subcommand leaves the prose behind as an instruction to run something that
refuses, so the set compared against is never restated here -- it is read
back out of `tickets.py` at run time. See `_routed_commands` for exactly
which surface that read lands on, and for the separate pin that makes it
equal to the dispatcher's own comparisons.
"""

import io
import json
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from scripts import tickets


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"

# `tickets.py` followed by one command token. The token class stops at the
# closing backtick and at any flag, so `tickets.py packet --executor` reads
# as `packet` and a bare "issued through `tickets.py`" matches nothing.
NAMED_COMMAND = re.compile(r"tickets\.py\s+([a-z][a-z-]*)")

# The operator each skill cannot do its job without. The pairing is the
# assertion: it is not enough that the name appears somewhere in the
# library, it must appear in the skill whose own procedure requires it.
#
# `amendment-request` sits with the engine rather than with the join that
# validates the record. The engine is what parks the worker the command
# suspends and what recomputes the frontier once the request is disposed of,
# so the placement is honest -- but it was also forced. The sweep in
# tests/test_verification_owners.py forbids a kernel skill from spelling out
# a packet-carried invocation, and its `tickets\.py amend` pattern carries no
# `\b` where its `new\b` and `check\b` siblings do, so it matches
# `amendment-request` by prefix. `scripts/tickets_packet.py` builds only
# `amend` (line 204), so that pattern's own premise does not reach this
# command. Filed as feedback; that file is outside this ticket's write scope.
REQUIRED_OPERATORS = {
    "gate": "kernel/orch-decompose",
    "draft-validate": "kernel/orch-decompose",
    "seal": "kernel/orch-decompose",
    "amendment-request": "engines/orch-frontier",
}

# The engine refuses a draft or merely-validated generation, so it is the
# other skill that requires the seal to have been taken.
SEAL_CONSUMER = "engines/orch-frontier"


def _skill_text(relative: str) -> str:
    return (SKILLS / relative / "SKILL.md").read_text(encoding="utf-8")


def _names(text: str, command: str) -> bool:
    """Whether ``text`` names ``tickets.py <command>``.

    Read through the same regex the surface-honesty half uses, so both
    halves of this module mean one thing by "names". These files wrap at
    prose width, and a command split across a line break is still named;
    a literal substring test would have graded the line breaks instead.
    """
    return command in NAMED_COMMAND.findall(text)


def _routed_commands() -> set:
    """The subcommands `tickets.py --help` publishes.

    Stated precisely, because the distinction is load-bearing: `--help`
    builds its table from `SUBCOMMAND_USAGE`
    (`scripts/tickets_dispatch.py:382`), a hand-maintained dict -- not from
    `_dispatch`'s own `command == ...` chain. Reading it is nonetheless a
    sound proxy for "what the dispatcher routes", but only because
    `tests/test_tickets_cases/cli_help.py`'s
    `test_the_usage_table_covers_exactly_the_dispatched_subcommands` pins
    `SUBCOMMAND_USAGE` equal to the names read off `_dispatch`'s AST.

    That pin lives in another module and is this one's silent dependency:
    weaken it and the honesty check below degrades from "no skill names a
    command the dispatcher does not route" to the far weaker "no skill names
    a command the usage table does not list", with nothing here failing.
    """

    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = tickets.main(["--help"])
        except SystemExit as exit_:
            code = exit_.code
    assert code == 0, f"tickets.py --help exited {code}: {stderr.getvalue()}"
    return set(json.loads(stdout.getvalue())["help"]["subcommands"])


class NamedOperatorsTest(unittest.TestCase):
    """Each required operator is named by the skill that requires it."""

    def test_orch_spec_routes_only_unresolved_roots_through_every_v2_door(self):
        text = _skill_text("workflows/orch-spec")
        frontmatter = text.split("---", 2)[1]
        description = next(
            (line.removeprefix("description:").strip()
             for line in frontmatter.splitlines()
             if line.startswith("description:")),
            "",
        ).lower()
        missing = sorted(
            {
                *(f"description omits {anchor!r}"
                  for anchor in ("evidence", "decisions", "kind boundaries",
                                 "unresolved")
                  if anchor not in description),
                *(f"orch-spec does not name tickets.py {command}"
                  for command in ("stamp-generation", "draft-validate", "seal")
                  if not _names(text, command)),
            }
        )
        if re.search(r"\b(?:any|every) delivery\b", description):
            missing.append("description still routes every delivery")
        self.assertEqual([], missing)

    def test_orch_decompose_names_the_command_that_writes_the_composite_gate(self):
        text = _skill_text("kernel/orch-decompose")
        self.assertTrue(_names(text, "gate"))
        # Named where the requirement is stated, not in an unrelated aside:
        # the composite-gate sentence is the one a decomposer acts on.
        sentence = next(
            (line for line in text.splitlines() if "composite gate" in line), ""
        )
        self.assertNotEqual("", sentence)
        at = text.find(sentence)
        self.assertTrue(_names(text[max(0, at - 200):at + 400], "gate"))

    def test_each_required_operator_is_named_by_the_skill_that_requires_it(self):
        missing = sorted(
            f"{skill} does not name tickets.py {command}"
            for command, skill in REQUIRED_OPERATORS.items()
            if not _names(_skill_text(skill), command)
        )
        self.assertEqual([], missing)

    def test_the_engine_that_refuses_an_unsealed_generation_names_the_seal(self):
        self.assertTrue(_names(_skill_text(SEAL_CONSUMER), "seal"))

    def test_the_v2_lifecycle_operators_are_all_reachable_by_name(self):
        # The three generation subcommands exist as a table in
        # `tickets_generations.py`; this is the claim that the library's own
        # prose reaches every one of them.
        named = set()
        for path in SKILLS.rglob("SKILL.md"):
            named.update(NAMED_COMMAND.findall(path.read_text(encoding="utf-8")))
        self.assertEqual(
            set(), {"draft-validate", "seal", "amendment-request"} - named
        )


class SurfaceHonestyTest(unittest.TestCase):
    """No skill names a command the dispatcher does not route."""

    def test_every_command_a_skill_names_is_one_tickets_py_routes(self):
        routed = _routed_commands()
        unrouted = set()
        for path in SKILLS.rglob("SKILL.md"):
            for command in NAMED_COMMAND.findall(path.read_text(encoding="utf-8")):
                if command not in routed:
                    unrouted.add(f"{path.relative_to(ROOT).as_posix()}: {command}")
        self.assertEqual(set(), unrouted)


class ReissueRulingTest(unittest.TestCase):
    """The ruling recorded for `scripts/tickets_reissue.py`: kept.

    The ablation is at `sink:runs/20260823T210000Z-trunk-slimming/
    00-root.09-reissue-ablation.md`. Removing the module breaks four sites,
    all mechanically repairable; the demand evidence decided it, and the
    surface therefore stands whole. These pin the kept surface: were the
    module deleted without its callers following, every one of them fails.
    """

    def test_the_kept_command_is_routed_carrying_its_usage_and_summary(self):
        from scripts import tickets_commands

        self.assertIn("reissue", _routed_commands())
        self.assertIn("reissue", tickets_commands.SUBCOMMAND_USAGE)
        self.assertIn("reissue", tickets_commands.SUBCOMMAND_SUMMARY)

    def test_the_facade_still_re_exports_the_kept_implementation(self):
        self.assertTrue(callable(tickets._cmd_reissue))

    def test_the_compat_pin_names_the_surviving_surface_exactly(self):
        from tests.test_refactor_compat import TicketsFacadeCompatibilityTest

        self.assertEqual(TicketsFacadeCompatibilityTest.COMMANDS, _routed_commands())


if __name__ == "__main__":
    unittest.main()
