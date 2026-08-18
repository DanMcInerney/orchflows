"""Friction logger fallback destination and route-count checks."""

import re
import tempfile
import unittest
from pathlib import Path

from ._support import ROOT, clause

IMPROVEMENT = ROOT / "rules" / "improvement.md"
HOST_BLOCK = ROOT / "templates" / "host-block.md"

_FALLBACK_DESTINATION = {
    "the refusal the fallback has to survive": ("refusal", "git worktree"),
    "a destination reachable under it": ("outside every worktree", "dispatch permits"),
    "how the entry gets back": ("the return", "collect"),
}

_LOGGER_NAME = re.compile(r"\b([a-z]+) logger\b")
_DETERMINERS = frozenset(
    {"the", "a", "an", "its", "this", "that", "one", "same", "installed"}
)
_SECOND_ROUTE = re.compile(
    r"\b(?:second|third|another|alternative|additional|backup|fallback)\s+"
    r"(?:friction\s+)?(?:logger|tool|script|command)\b"
)
_SPELLED_COMMAND_OR_PATH = re.compile(r"`[^`]*(?:\.py\b|/)[^`]*`")

_DESTINATION_CLAUSE_RE = re.compile(
    r" Where the refusal covers writing inside a git worktree,.*?collect it\.",
    re.S,
)

_SECOND_ROUTE_SPLICE = (
    "When the logger cannot run, a second logger at "
    "`scripts/friction_fallback.py` takes the entry. "
)


def _fallback_destination_gaps(host_block_text):
    """Return parts of the fallback-destination clause that are absent."""
    return sorted(
        name
        for name, phrases in _FALLBACK_DESTINATION.items()
        if not all(phrase in host_block_text for phrase in phrases)
    )


def _logger_names(improvement_text):
    """Return every logger name in improvement clause 1."""
    improvement_clause = clause(improvement_text, 1)
    return sorted(
        {
            name
            for name in _LOGGER_NAME.findall(improvement_clause)
            if name not in _DETERMINERS
        }
    )


def _routes_beyond_the_one(improvement_text):
    """Return routes in clause 1 besides the one installed logger."""
    improvement_clause = clause(improvement_text, 1)
    return sorted(
        _SECOND_ROUTE.findall(improvement_clause)
        + _SPELLED_COMMAND_OR_PATH.findall(improvement_clause)
    )


class FrictionDestinationTest(unittest.TestCase):
    """The fallback remains reachable when worktree writes are refused."""

    def test_the_block_states_a_destination_that_survives_the_refusal(self):
        gaps = _fallback_destination_gaps(HOST_BLOCK.read_text(encoding="utf-8"))
        self.assertEqual(
            [],
            gaps,
            "templates/host-block.md states no fallback destination covering: "
            f"{', '.join(gaps)}",
        )

    def test_section_one_still_names_exactly_one_primary_route(self):
        self.assertEqual(
            ["friction"],
            _logger_names(IMPROVEMENT.read_text(encoding="utf-8")),
            "§1 names one primary route, the installed friction logger; the "
            "destination gap is not answered by a second one",
        )
        extra = _routes_beyond_the_one(IMPROVEMENT.read_text(encoding="utf-8"))
        self.assertEqual(
            [],
            extra,
            "§1 delegates the command's spelling to the host block and adds "
            f"no route of its own; it names: {', '.join(extra)}",
        )

    def test_a_block_without_the_destination_fails_the_check(self):
        """The can-fail direction excises the destination from a copy."""
        real = HOST_BLOCK.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "host-block.md"
            beside.write_text(real, encoding="utf-8")
            self.assertEqual(
                [],
                _fallback_destination_gaps(beside.read_text(encoding="utf-8")),
                "the copy must start with the clause intact, or the excision "
                "below is not what the check reacted to",
            )
            excised = re.sub(_DESTINATION_CLAUSE_RE, "", real, count=1)
            self.assertNotEqual(
                real, excised,
                "the excision matched nothing, so the assertion below would "
                "prove nothing",
            )
            beside.write_text(excised, encoding="utf-8")
            self.assertEqual(
                sorted(_FALLBACK_DESTINATION),
                _fallback_destination_gaps(beside.read_text(encoding="utf-8")),
            )

    def test_a_section_one_answering_the_gap_with_a_tool_fails_the_check(self):
        """The can-fail direction splices a forbidden second logger."""
        real = IMPROVEMENT.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "improvement.md"
            beside.write_text(real, encoding="utf-8")
            self.assertEqual(
                [],
                _routes_beyond_the_one(beside.read_text(encoding="utf-8")),
                "the copy must start with one route, or the splice below is "
                "not what the check reacted to",
            )
            spliced = real.replace("\n1. ", "\n1. " + _SECOND_ROUTE_SPLICE, 1)
            self.assertNotEqual(
                real, spliced,
                "the splice matched nothing, so the assertion below would "
                "prove nothing",
            )
            beside.write_text(spliced, encoding="utf-8")
            self.assertEqual(
                ["`scripts/friction_fallback.py`", "second logger"],
                _routes_beyond_the_one(beside.read_text(encoding="utf-8")),
            )
