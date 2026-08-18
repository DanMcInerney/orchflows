"""Shared fixtures and readers for the carriage regression cases."""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VALIDATE = ROOT / "tools" / "validate.py"
CONTRACTS = ROOT / "contracts"
PINS = ROOT / "tests" / "pins.json"

from tools import validate  # noqa: E402  (needs the sys.path insert above)


class IsolatedTree(unittest.TestCase):
    """A synthetic tree containing only the validator's required inputs."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        shutil.copytree(CONTRACTS, self.tmp_path / "contracts")
        (self.tmp_path / "tools").mkdir()
        shutil.copy(VALIDATE, self.tmp_path / "tools" / "validate.py")
        # The compiler is two files (ARCHITECTURE.md): a tree that runs the
        # copy carries `scripts/doclint.py`, which it asks whether a link
        # resolves and whether two clauses are one clause.
        (self.tmp_path / "scripts").mkdir()
        shutil.copy(ROOT / "scripts" / "doclint.py", self.tmp_path / "scripts" / "doclint.py")
        # Matching pins, so only the synthetic packages can fail. The
        # committed pins.json already matches these very contract bytes --
        # test_validator.py's test_pin_matches_committed_pins_json is what
        # proves it -- so copy it instead of spawning `--pin` per test.
        (self.tmp_path / "tests").mkdir()
        shutil.copy(PINS, self.tmp_path / "tests" / "pins.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(self.tmp_path / "tools" / "validate.py"), *args],
            capture_output=True,
            text=True,
        )

    def _write_skill(self, name: str, content: str, tier: str = "instances"):
        skill_dir = self.tmp_path / "skills" / tier / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    def _write_pack(self, name: str, content: str):
        pack_dir = self.tmp_path / "packs" / name
        pack_dir.mkdir(parents=True)
        (pack_dir / "SKILL.md").write_text(content, encoding="utf-8")


def clause(text, number):
    """Return one numbered clause from a flat-numbered rules file."""
    match = re.search(rf"(?m)^{number}\. (.*?)(?=^\d+\. |\Z)", text, re.S)
    if match is None:
        raise AssertionError(f"no clause {number}")
    return re.sub(r"\s+", " ", match.group(1))


def clause_gaps(text, required):
    """Return the named requirements whose phrases are absent from text."""
    flat = re.sub(r"\s+", " ", text)
    return sorted(
        name for name, phrases in required.items()
        if not all(phrase in flat for phrase in phrases)
    )


def section(text, heading):
    """Return one ``##``-delimited section of a markdown file."""
    match = re.search(
        rf"(?ms)^## {re.escape(heading)}\s*$(.*?)(?=^## |\Z)", text
    )
    if match is None:
        raise AssertionError(f"no section '{heading}'")
    return match.group(1)
