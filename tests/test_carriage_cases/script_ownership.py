"""Repository script ownership checks."""

import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from ._support import CONTRACTS, PINS, ROOT

SCRIPTS = ROOT / "scripts"
ARCHITECTURE = ROOT / "ARCHITECTURE.md"

# The form ARCHITECTURE.md's script clauses already take:
# `scripts/<name>.py` owns <responsibility>. A bare mention names no owner.
_OWNERSHIP_CLAUSE = re.compile(r"`scripts/([^`/]+\.py)`\s+owns\s+([^;.]+)")


def _scripts_without_owners(scripts_dir, architecture_text):
    """Every script whose responsibility the architecture never states."""
    flat = re.sub(r"\s+", " ", architecture_text)
    owned = {m.group(1): m.group(2).strip() for m in _OWNERSHIP_CLAUSE.finditer(flat)}
    return sorted(p.name for p in scripts_dir.glob("*.py") if not owned.get(p.name))


class ScriptOwnershipTest(unittest.TestCase):
    """ARCHITECTURE.md names the responsibility of every repository script."""

    def test_every_script_is_named_with_the_responsibility_it_owns(self):
        unowned = _scripts_without_owners(
            SCRIPTS, ARCHITECTURE.read_text(encoding="utf-8")
        )
        self.assertEqual(
            [],
            unowned,
            "ARCHITECTURE.md states no '`scripts/<name>` owns <responsibility>' "
            f"clause for: {', '.join(unowned)}",
        )

    def test_a_script_with_no_owner_fails_the_check(self):
        """The can-fail direction uses a copy beside the tree."""
        architecture_text = ARCHITECTURE.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "scripts"
            beside.mkdir()
            for script in SCRIPTS.glob("*.py"):
                (beside / script.name).write_text("", encoding="utf-8")
            self.assertEqual(
                [],
                _scripts_without_owners(beside, architecture_text),
                "the copy must start fully owned, or the newcomer below is "
                "not what the check reacted to",
            )
            (beside / "unowned_newcomer.py").write_text("", encoding="utf-8")
            self.assertEqual(
                ["unowned_newcomer.py"],
                _scripts_without_owners(beside, architecture_text),
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
