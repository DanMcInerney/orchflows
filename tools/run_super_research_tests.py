#!/usr/bin/env python3
"""Run the project-scope super-research offline unittest suite."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = ROOT / ".orchflows" / "skills" / "super-research"
TESTS_DIR = SKILL_ROOT / "tests"
SCRIPTS_DIR = SKILL_ROOT / "scripts"


def test_name(selector: str) -> str:
    """Return a selector rooted at the project-scope tests package."""

    name = selector[:-3] if selector.endswith(".py") else selector
    name = name.replace("\\", "/").replace("/", ".").strip(".")
    if name.startswith("tests."):
        return name
    return "tests." + name


def load_suite(selectors):
    """Load selected modules/classes, or discover the complete suite."""

    sys.path[:0] = [str(SKILL_ROOT), str(SCRIPTS_DIR)]
    loader = unittest.defaultTestLoader
    if selectors:
        return loader.loadTestsFromNames([test_name(name) for name in selectors])
    return loader.discover(
        start_dir=str(TESTS_DIR),
        pattern="test*.py",
        top_level_dir=str(SKILL_ROOT),
    )


def main(argv=None) -> int:
    selectors = sys.argv[1:] if argv is None else argv
    if sys.version_info[:2] != (3, 9):
        command = [
            "uv",
            "run",
            "--python",
            "3.9",
            "--no-project",
            "python",
            str(Path(__file__).resolve()),
            *selectors,
        ]
        return subprocess.call(command)
    suite = load_suite(selectors)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
