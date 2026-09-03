#!/usr/bin/env python3
"""Run the project-scope super-research offline unittest suite."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


# Run directly (`python tools/run_super_research_tests.py`), so
# `scripts/` is not yet on sys.path here; reading `scripts._bootstrap.ROOT`
# would need this same walk to seed the import first, for no fact this
# file otherwise needs from `scripts/`.
ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = ROOT / ".orchflows" / "skills" / "research-acquire"
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
    discovered = loader.discover(
        start_dir=str(TESTS_DIR),
        pattern="test*.py",
        top_level_dir=str(SKILL_ROOT),
    )
    if not selectors:
        return discovered

    def cases(suite):
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                yield from cases(item)
            else:
                yield item

    selected = unittest.TestSuite()
    all_cases = tuple(cases(discovered))
    for raw in selectors:
        target = test_name(raw)
        if target.count(".") == 1:
            selected.addTests(loader.loadTestsFromName(target))
            continue
        matched = [test for test in all_cases if test.id() == target or test.id().startswith(target + ".")]
        if matched:
            selected.addTests(matched)
        else:
            selected.addTests(loader.loadTestsFromName(target))
    return selected


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
