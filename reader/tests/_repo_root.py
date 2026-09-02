"""This repository's root, derived once for the whole `reader/tests/` tree.

The reader test tree's walk depth varies with nesting -- `parents[2]` for
a file directly under `reader/tests/`, `parents[3]` once it moves under
`reader/tests/test_ui_cases/` -- so a constant collapses that variance:
every site imports this module's `ROOT` instead of re-deriving its own
depth-correct walk. This module derives the fact independently rather
than importing it from production code, matching `tests/_repo_root.py`'s
own reasoning one directory up: a test must not take "where the
repository is" from a fact a wrong answer elsewhere would let it
silently agree with instead of catching.

Every site here is reached through `reader/tests/test_reader.py`'s
absolute dotted imports (`reader.tests.test_ui_cases.<name>`), which
already requires the `reader` package -- and so the repository root on
`sys.path` -- resolved before any of those modules' top-level code runs,
this one included.
"""

from __future__ import annotations

from pathlib import Path

# This file sits in `reader/tests/`, two directories under the repository
# root, so three `.parent`s from its own resolved path -- one to leave the
# file, two to leave the directories -- is the fact every site under
# `reader/tests/` needs, at whatever depth it lives.
ROOT = Path(__file__).resolve().parent.parent.parent
