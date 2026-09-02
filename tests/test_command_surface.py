"""The maintained skills name only callable current ticket commands."""

from __future__ import annotations

import io
import json
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout

from scripts import tickets
from scripts.tickets_commands import SUBCOMMAND_SUMMARY, SUBCOMMAND_USAGE

from tests._retired_commands import RETIRED_COMMAND_NAMES

from tests._repo_root import ROOT
SKILLS = ROOT / "skills"
RULES = ROOT / "rules"
NAMED_COMMAND = re.compile(r"tickets\.py\s+([a-z][a-z-]*)")
REMOVED_INLINE_COMMAND = re.compile(r"`(amend|recut)`")


def routed_commands() -> set[str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = tickets.main(["--help"])
    assert code == 0, stderr.getvalue()
    return set(json.loads(stdout.getvalue())["help"]["subcommands"])


class CurrentCommandSurfaceTest(unittest.TestCase):
    def test_help_usage_and_summary_name_one_exact_surface(self):
        routed = routed_commands()
        self.assertEqual(set(SUBCOMMAND_USAGE), routed)
        self.assertEqual(set(SUBCOMMAND_SUMMARY), routed)

    def test_every_command_named_by_a_skill_is_routed(self):
        routed = routed_commands()
        stale = []
        for path in sorted(SKILLS.rglob("SKILL.md")):
            for command in NAMED_COMMAND.findall(path.read_text(encoding="utf-8")):
                if command not in routed:
                    stale.append(f"{path.relative_to(ROOT).as_posix()}: {command}")
        self.assertEqual([], stale)

    def test_the_retired_generation_and_gate_commands_are_named_nowhere(self):
        """The four pre-callable commands and the gate family left the surface.

        `stamp-generation`, `draft-validate`, `seal`, and `ready` are folded
        inside `tickets.py do`, `tickets.py judge`, and `tickets.py dispatch`
        (`tests/_retired_commands.py` owns this closed set, and reaches their
        internals for fixtures that still need one directly); `gate` and
        `checker-stage` are gone with the choreography, and critique-to-repair
        is prose over `judge` and `do`. `instantiate` left with the template
        layer it read, and `join-noop-repair` left with the `.gate.` id
        family it discriminated -- unreachable once nothing minted a
        `.gate.repair` ticket, and now not routed either. A skill that still
        walked a caller through one of them would be walking it into
        `unknown subcommand`.
        """

        gate_and_loop_family = {
            "gate", "checker-stage", "loop-arm", "loop-evaluate",
            "loop-advance", "instantiate", "join-noop-repair",
        }
        retired = RETIRED_COMMAND_NAMES | gate_and_loop_family
        self.assertEqual(set(), retired & routed_commands())
        named = set()
        for path in SKILLS.rglob("SKILL.md"):
            named.update(NAMED_COMMAND.findall(path.read_text(encoding="utf-8")))
        self.assertEqual(set(), retired & named)

    def test_removed_authority_commands_have_no_route_or_facade_export(self):
        removed = {"amend", "amendment-request", "grant", "recut", "reissue", "result-grade"}
        self.assertEqual(set(), removed & routed_commands())
        self.assertEqual(set(), {"claim", "packet"} & routed_commands())
        for command in removed:
            self.assertFalse(hasattr(tickets, "_cmd_" + command.replace("-", "_")), command)

    def test_canonical_rules_name_only_current_ticket_commands(self):
        routed = routed_commands()
        stale = []
        for path in sorted(RULES.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for command in NAMED_COMMAND.findall(text):
                if command not in routed:
                    stale.append(f"{path.relative_to(ROOT).as_posix()}: {command}")
            for command in REMOVED_INLINE_COMMAND.findall(text):
                stale.append(f"{path.relative_to(ROOT).as_posix()}: `{command}`")
        self.assertEqual([], stale)


if __name__ == "__main__":
    unittest.main()
