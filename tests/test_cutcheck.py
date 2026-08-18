"""Tests for scripts/cutcheck.py: family 1, oracle discrimination and shape."""

import ast
import contextlib
import importlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import install  # noqa: E402
import scripts.cutcheck as cutcheck  # noqa: E402
import scripts.state_root as state_root  # noqa: E402
import scripts.tickets as tickets  # noqa: E402
from tests.baseline_pin import (  # noqa: E402  the invocation's one owner
    BASELINE,
    run_cutcheck,
    run_cutcheck_subprocess,
    shared_root,
)
from tests.tree_removal import remove_repo_tree  # noqa: E402  the removal's one owner


def reported(result, family=cutcheck.FAMILY):
    return [line for line in result.stdout.splitlines() if family in line]


def report(result):
    """The report split where its own summary lines split it.

    Findings outside the advisory set first, then the advisory findings under
    the heading, then whether the affirmative line closed the report. The shape
    reading is split off and returned by none of the three: it is a reading of
    the cut and not a finding of it, so a caller counting findings must never
    have to subtract it.
    """

    lines = result.stdout.splitlines()
    affirmed = bool(lines) and lines[-1] == cutcheck.NO_FINDING_OUTSIDE
    if affirmed:
        lines = lines[:-1]
    if cutcheck.GRAPH_HEADING in lines:
        lines = lines[:lines.index(cutcheck.GRAPH_HEADING)]
    if cutcheck.ADVISORY_HEADING in lines:
        cut = lines.index(cutcheck.ADVISORY_HEADING)
        return lines[:cut], lines[cut + 1:], affirmed
    return lines, [], affirmed


def graph_block(result):
    """The shape reading's own lines, under its own heading.

    The half `report` drops. Nothing but the affirmative line follows the
    block, so the block is what stands between its heading and that line.
    """

    lines = result.stdout.splitlines()
    if cutcheck.GRAPH_HEADING not in lines:
        return []
    block = lines[lines.index(cutcheck.GRAPH_HEADING) + 1:]
    if block and block[-1] == cutcheck.NO_FINDING_OUTSIDE:
        block = block[:-1]
    return block


def finding_lines(result):
    """Every finding line the report holds, and nothing else.

    Both blocks, neither summary line, and never the shape reading. A caller
    asking what was found about an item is asking about findings, and the
    chain the shape names carries ticket ids -- a reading of those items, not
    a finding against them, and a filter that took it for one would convict a
    clean set of whatever its longest chain happened to run through.
    """

    violations, advisories, _ = report(result)
    return violations + advisories


def fixture_criteria(run, name):
    path = ROOT / "tests" / "fixtures" / "cutcheck" / run / name
    section = tickets._sections(path.read_text(encoding="utf-8"))
    return cutcheck._criteria(section[cutcheck.COMPLETION_SECTION])


def shared_baseline_tree():
    """The harness's real baseline clone, shared by read-only tree probes."""

    tree = cutcheck._scratch_tree(BASELINE, ROOT, shared_root())
    if tree is None:
        raise RuntimeError("no scratch tree was built for the baseline")
    return tree


GIT_ESCAPES = (
    "git -c core.pager=touch\\ /tmp/cutcheck-gitescape-ran log",
    "git -c alias.pwn='!touch /tmp/cutcheck-gitescape-ran' pwn",
    "git --exec-path=/tmp/cutcheck-gitescape log",
    "git --upload-pack=touch\\ /tmp/cutcheck-gitescape-ran fetch origin",
    "git --receive-pack=touch\\ /tmp/cutcheck-gitescape-ran push origin",
    "git -C /etc log",
    "git --git-dir=/tmp/cutcheck-gitescape/.git log",
    "git --work-tree=/etc status",
    "git clone https://example.invalid/x",
    "git archive HEAD",
    "git grep -O/tmp/cutcheck-gitescape-ran pattern",
)

# Each stands after a subcommand the confined set holds, where position sees
# nothing, and names a location the copy does not hold: `--output` writes it,
# `-O`, `-X`, `--exclude-from`, `--no-index` and `--resolve-git-dir` read it.
# Climbing reaches as far as rooting does -- the other revision's scratch copy
# is one `..` away, and planting a file there rewrites the half of the
# discrimination reading it was not asked about.
GIT_REACHES_OUT = (
    "git log --output=/tmp/cutcheck-gitescape-wrote",
    "git diff --output /tmp/cutcheck-gitescape-wrote",
    "git rev-list HEAD --output=/tmp/cutcheck-gitescape-wrote",
    "git show --output=../cutcheck-gitescape-wrote",
    "git diff -O/tmp/cutcheck-gitescape-ran HEAD~1",
    "git ls-files -X /etc/hosts",
    "git ls-files --exclude-from=/etc/hosts",
    "git diff --no-index /etc/hosts /etc/passwd",
    "git rev-parse --resolve-git-dir /etc",
)

FIXTURES = ROOT / "tests" / "fixtures" / "cutcheck"
VERDICTS = FIXTURES / "verdicts.json"


def fixture_sets():
    return sorted(path.name for path in FIXTURES.iterdir() if path.is_dir())


def verdict(run):
    result = run_cutcheck(run)
    return {"exit": result.returncode, "lines": result.stdout.splitlines()}


def record_verdicts():
    """Rewrite the pinned verdicts from this revision's own report.

    Run as ``python3 tests/test_cutcheck.py --record``, and only when a
    completion test names the change: an unexplained diff here is a
    suppression nobody asked for.
    """

    recorded = {run: verdict(run) for run in fixture_sets()}
    # Bytes with LF: a text-mode write on Windows would land CRLF and
    # differ from every other host's recording.
    VERDICTS.write_bytes(
        (json.dumps(recorded, indent=1, sort_keys=True) + "\n").encode("utf-8")
    )

SPAN_PROGRAMS = frozenset({"git", "python3"} | set(cutcheck.SEARCH_HEADS))


def _graded_with(test, argv, failing_clone=None):
    """Run one grading against shared copies for cases with custom argv."""

    root = shared_root()
    real = cutcheck._scratch_tree

    def clone(rev, worktree_root, scratch_root):
        if rev == failing_clone:
            return None
        return real(rev, worktree_root, scratch_root)

    out, err = io.StringIO(), io.StringIO()
    here = Path.cwd()
    os.chdir(str(ROOT))
    try:
        with mock.patch.object(cutcheck, "_scratch_root", lambda _tree: root):
            with mock.patch.object(cutcheck, "_remove_scratch_root", lambda _root: None):
                with mock.patch.object(cutcheck, "_scratch_tree", clone):
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        code = cutcheck.main(argv)
    finally:
        os.chdir(str(here))
    return code, out.getvalue()


def must_git(case, args, cwd):
    proc = cutcheck._git(args, cwd)
    case.assertIsNotNone(proc, "git could not be run: {}".format(args))
    case.assertEqual(
        proc.returncode, 0, "git {}: {}".format(" ".join(args), proc.stderr)
    )
    return proc


def span_requirements(command):
    """Return the program and interpreter-module requirements of a span."""

    try:
        argv = shlex.split(command)
    except ValueError:
        return []
    if not argv:
        return []
    needs = [("program", Path(argv[0]).name)]
    for index in range(1, len(argv)):
        token = argv[index]
        if token == "-m":
            if index + 1 < len(argv):
                needs.append(("module", argv[index + 1]))
            break
        if not token.startswith("-"):
            break
    return needs


CASE_MODULES = (
    "summary",
    "discrimination",
    "layout",
    "coverage",
    "execution",
    "confinement",
    "extraction",
    "evaluation",
    "decidability",
    "state",
    "spans",
    "scratch",
    "scope",
)


def load_tests(loader, standard_tests, pattern):
    # The explicit loader keeps every case in this module's child process.

    suite = unittest.TestSuite()
    for name in CASE_MODULES:
        module = importlib.import_module("tests.test_cutcheck_cases." + name)
        suite.addTests(loader.loadTestsFromModule(module))
    return suite


if __name__ == "__main__":
    if "--record" in sys.argv:
        record_verdicts()
    else:
        unittest.main()
