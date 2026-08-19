"""Repository script ownership checks."""

import hashlib
import json
import re
import unittest

from ._support import CONTRACTS, PINS, ROOT

ARCHITECTURE = ROOT / "ARCHITECTURE.md"

_OWNERSHIP_CLAUSE = re.compile(r"`scripts/([^`/]+\.py)`\s+owns\s+([^;.]+)")
_FAMILY_ROUTE_PINS = (
    "unprefixed family module is the public command and import facade",
    "same-family helpers own internal concerns",
    "from code, not inventoried here",
)


def _missing_family_route_pins(architecture_text):
    """Stable routing facts absent from the scripts-family owner."""
    flat = re.sub(r"\s+", " ", architecture_text)
    return [pin for pin in _FAMILY_ROUTE_PINS if pin not in flat]


class ScriptOwnershipTest(unittest.TestCase):
    """ARCHITECTURE.md routes script families and pins exceptional owners."""

    def test_architecture_routes_script_families_without_a_helper_inventory(self):
        self.assertEqual(
            [],
            _missing_family_route_pins(ARCHITECTURE.read_text(encoding="utf-8")),
        )

    def test_each_missing_family_route_fact_fails_the_check(self):
        """The can-fail direction excises each fact from a copy."""
        architecture_text = re.sub(
            r"\s+", " ", ARCHITECTURE.read_text(encoding="utf-8")
        )
        for pin in _FAMILY_ROUTE_PINS:
            with self.subTest(pin=pin):
                wrong = architecture_text.replace(pin, "")
                self.assertNotEqual(architecture_text, wrong)
                self.assertEqual(
                    [pin],
                    _missing_family_route_pins(wrong),
                )

    def test_verification_guardrail_owner_paths_are_pinned(self):
        """Pin the complete contract/workflow surface."""
        semantic_pins = {
            "ARCHITECTURE.md": (
                "one root/gate family", "immutable run identity",
                "immutable terminal timing",
            ),
            "contracts/work-item.md": (
                "exactly one outside-independence path", "one composite gate",
            ),
            "contracts/worklog.md": ("one physical run", "one composite gate"),
            "docs/vocabulary.md": (
                "one composite gate", "exactly one ordinary path",
                "unique named lens",
            ),
            "rules/topology.md": ("successor run", "one composite gate"),
            "rules/verification.md": (
                "mutually exclusive ordinary path", "unique named root-gate critique lens",
            ),
            "skills/engines/orch-frontier/SKILL.md": (
                "checker packet", "root cut reader",
            ),
            "skills/kernel/orch-critique/SKILL.md": (
                "gate-deferred", "unique named root-gate critique lens",
            ),
            "skills/kernel/orch-decompose/SKILL.md": (
                "regardless of oracle class", "one composite gate",
            ),
            "skills/kernel/orch-integrate/SKILL.md": (
                "one outside-independence path", "`independence: gate`",
            ),
            "skills/workflows/orch-spec/SKILL.md": (
                "successor run", "second root in the same run",
            ),
        }
        expected = {
            "ARCHITECTURE.md", "contracts/work-item.md", "contracts/worklog.md",
            "docs/vocabulary.md", "rules/topology.md", "rules/verification.md",
            "skills/engines/orch-frontier/SKILL.md",
            "skills/kernel/orch-critique/SKILL.md",
            "skills/kernel/orch-decompose/SKILL.md",
            "skills/kernel/orch-integrate/SKILL.md",
            "skills/workflows/orch-spec/SKILL.md",
        }
        self.assertEqual(expected, set(semantic_pins), "guardrail owner roster drifted")
        self.assertTrue(
            {"scripts/tickets.py", "scripts/cutcheck.py"}.isdisjoint(semantic_pins),
            "this contract slice took predecessor runtime or cutcheck ownership",
        )
        for relative, phrases in semantic_pins.items():
            text = re.sub(r"\s+", " ", (ROOT / relative).read_text(encoding="utf-8"))
            for phrase in phrases:
                self.assertIn(phrase, text, f"{relative} lost semantic pin {phrase!r}")

        pins = json.loads(PINS.read_text(encoding="utf-8"))
        for name in ("work-item.md", "worklog.md"):
            actual = hashlib.sha256((CONTRACTS / name).read_bytes()).hexdigest()
            self.assertEqual(actual, pins.get(name), f"{name} has no current T0 pin")

        flat_architecture = re.sub(
            r"\s+", " ", ARCHITECTURE.read_text(encoding="utf-8")
        )
        ownership = {
            name: responsibility
            for name, responsibility in _OWNERSHIP_CLAUSE.findall(flat_architecture)
        }
        self.assertIn("one root/gate family", ownership["tickets.py"])
        self.assertIn("cut-defect detection", ownership["cutcheck.py"])
