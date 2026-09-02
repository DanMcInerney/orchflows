"""This repository's root, derived once for the whole `tests/` tree.

S1 (`scripts/_bootstrap.py`) converged production code's independent
`Path(__file__).resolve().parents[N]` walks onto one owner. The test
tree's own ~90 copies of the same walk do not converge onto that
production owner: a test asserting facts about the repository must not
take "where the repository is" from the very module a wrong answer
there would then let every other test silently agree with, instead of
the one test whose job is to catch it. This module re-derives the fact
independently -- the same shape `_bootstrap.py` uses, just for `tests/`
-- so the duplication collapses to one site instead of the fact's
source becoming production code's.

`tools/run_tests.py`'s `run_child` inserts the repository root onto
`sys.path` before loading any test module (`unittest.TestLoader()
.loadTestsFromName`), and `python -m unittest discover -s tests` is run
with the repository root as the current working directory, which
Python puts on `sys.path` for `-m` on its own -- so every site under
`tests/` can import this module under both invocations without its own
bootstrap. The two sites that must still walk locally
(`tests/test_state_root.py`, `tests/test_windows_semantics.py`) need
`import tests` itself to succeed before anything in the package,
this module included, is reachable -- see their own comments.
"""

from __future__ import annotations

from pathlib import Path

# This file sits in `tests/`, one directory under the repository root, so
# two `.parent`s from its own resolved path -- one to leave the file, one
# to leave `tests/` -- is the fact every other site under `tests/` needs.
ROOT = Path(__file__).resolve().parent.parent
