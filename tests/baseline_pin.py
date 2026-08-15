"""The revision the cutcheck tests cut their scratch copies from.

One owner, read by ``tests/test_cutcheck.py`` and ``tests/test_canary_host.py``
alike. A copy in either of them moves independently of the other, and the two
readers fail asymmetrically when it does: the sibling goes loudly red where
this module's own guard, reading a report a run resolved nothing to write,
goes silently green.

Not a test module, and holding nothing but the pin, so that reading it is not
one test module's verdict depending on another's state -- the objection the
copy in ``tests/test_canary_host.py`` was made to honour.
"""

# cutcheck clones this revision to build the tree it grades oracles in, so
# every clone that runs these tests must be able to reach it. Two invariants
# make a candidate legal, and both are load-bearing: it is an ancestor of
# `main`, so a fresh clone has it (the predecessor pinned an unpushed local
# branch tip, which passed here and failed every CI leg with "cannot clone
# baseline"); and `install.py:101` there opens `SCRIPT_NAMES` without
# `cutcheck.py`, which is what makes the fixtures' `grep -n "cutcheck.py"
# install.py` fail at the baseline and pass at HEAD -- the discrimination the
# family 1 fixtures exist to exercise. Reachability also needs
# `fetch-depth: 0` in .github/workflows/checks.yml; a depth-1 checkout has one
# commit and no ancestor is archivable.
BASELINE = "462ef52aab37655260bdc9f9f98be4ed2601af2d"
