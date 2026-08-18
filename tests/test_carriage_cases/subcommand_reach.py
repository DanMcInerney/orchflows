"""Reachability checks for the tickets CLI subcommands."""

import re
import tempfile
import unittest
from pathlib import Path

from ._support import ROOT

SCRIPTS = ROOT / "scripts"
ARCHITECTURE = ROOT / "ARCHITECTURE.md"
TICKETS = SCRIPTS / "tickets.py"
SKILLS = ROOT / "skills"

# scripts/tickets.py declares one `_cmd_<name>` per subcommand and dashes the
# name on the command line (its `_dispatch`).
_SUBCOMMAND_DEF = re.compile(r"^def _cmd_([a-z_]+)\(", re.MULTILINE)
# A skill body reaches a subcommand by naming it inside a code span.
_SKILL_CALL = re.compile(r"`[^`]*tickets\.py ([a-z-]+)[^`]*`")
# The form ARCHITECTURE.md records for a subcommand no skill body runs.
_OPERATOR_ONLY_CLAUSE = re.compile(r"`tickets\.py ([a-z-]+)` is operator-only: ([^;.]+)")


def _subcommands_without_reach(tickets_source, skill_bodies, architecture_text):
    """Return subcommands with neither a skill caller nor operator status."""
    called = set()
    for body in skill_bodies:
        called.update(_SKILL_CALL.findall(re.sub(r"\s+", " ", body)))
    flat = re.sub(r"\s+", " ", architecture_text)
    recorded = {
        name for name, reason in _OPERATOR_ONLY_CLAUSE.findall(flat) if reason.strip()
    }
    return sorted(
        name.replace("_", "-")
        for name in _SUBCOMMAND_DEF.findall(tickets_source)
        if name.replace("_", "-") not in called | recorded
    )


class SubcommandReachTest(unittest.TestCase):
    """Every tickets subcommand is either called or recorded operator-only."""

    def _skill_bodies(self):
        return [
            path.read_text(encoding="utf-8")
            for path in sorted(SKILLS.glob("*/*/SKILL.md"))
        ]

    def test_every_subcommand_is_called_by_a_skill_or_recorded_operator_only(self):
        unreached = _subcommands_without_reach(
            TICKETS.read_text(encoding="utf-8"),
            self._skill_bodies(),
            ARCHITECTURE.read_text(encoding="utf-8"),
        )
        self.assertEqual(
            [],
            unreached,
            "no skill body names `tickets.py <name>` and ARCHITECTURE.md "
            "records no '`tickets.py <name>` is operator-only: <reason>' "
            f"clause for: {', '.join(unreached)}",
        )

    def test_a_subcommand_with_neither_caller_nor_status_fails_the_check(self):
        """The can-fail direction uses a scratch copy beside the tree."""
        bodies = self._skill_bodies()
        architecture_text = ARCHITECTURE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "tickets.py"
            beside.write_text(TICKETS.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(
                [],
                _subcommands_without_reach(
                    beside.read_text(encoding="utf-8"), bodies, architecture_text
                ),
                "the copy must start fully reached, or the newcomer below is "
                "not what the check reacted to",
            )
            with open(beside, "a", encoding="utf-8") as handle:
                handle.write("\n\ndef _cmd_newcomer(rest):\n    return {}\n")
            self.assertEqual(
                ["newcomer"],
                _subcommands_without_reach(
                    beside.read_text(encoding="utf-8"), bodies, architecture_text
                ),
            )
