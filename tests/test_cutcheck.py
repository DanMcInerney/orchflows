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
import scripts.cutcheck_ticket as cutcheck_ticket  # noqa: E402  the screens' owner
import scripts.state_root as state_root  # noqa: E402
import scripts.tickets as tickets  # noqa: E402
from tests.baseline_pin import (  # noqa: E402  the invocation's one owner
    BASELINE,
    run_cutcheck,
    run_cutcheck_subprocess,
    shared_root,
)
from tests.tree_removal import remove_repo_tree  # noqa: E402  the removal's one owner


class RuntimeInterpreterBoundaryTests(unittest.TestCase):
    """Cut checks execute ticket oracles in the caller's project context."""

    def test_oracle_subprocesses_inherit_the_caller_environment(self):
        caller = {
            "PATH": "cutcheck-oracle-path",
            "VIRTUAL_ENV": "cutcheck-oracle-venv",
        }
        observed = []

        def run_in_caller(*args, **kwargs):
            observed.append((dict(os.environ), kwargs))
            return subprocess.CompletedProcess(args[0], 0, b"", b"")

        with mock.patch.dict(os.environ, caller, clear=False):
            with mock.patch.object(cutcheck.subprocess, "run", side_effect=run_in_caller):
                with mock.patch.object(
                    cutcheck._execute_module, "_mutations", return_value=[]
                ):
                    self.assertEqual(0, cutcheck._run_once("git status --short", ROOT))
                self.assertEqual(0, cutcheck._git(["status"], ROOT).returncode)

        self.assertEqual(2, len(observed))
        for environment, kwargs in observed:
            self.assertEqual(caller, {name: environment[name] for name in caller})
            self.assertNotIn("env", kwargs)


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


class CutScopeScreenTest(unittest.TestCase):
    """The four cut-time screens family 3 gained, each refusing and each silent.

    Graded through `_check_ticket`, which is what the report calls, rather than
    through the judgment alone: a screen wired nowhere reports nothing, and the
    friction each of these repairs was a cut that passed.
    """

    SIBLINGS = {
        "00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR},
        "00-root.01": {"id": "00-root.01", "executor": "orch-tdd"},
    }
    JUDGED = "1. **A reviewer reads it.** oracle_class: judged. provenance: authored-here."

    def _ticket(self, inputs="", objective="Change one module.", completion=None,
                scope="scripts/allowed.py"):
        return (
            "---\nid: 00-root.01\nexecutor: orch-tdd\ndepends_on: []\n"
            "write_scope: [{}]\n---\n\n## Objective\n\n{}\n\n"
            "## Fixed inputs\n\n{}\n\n## Completion test\n\n{}\n"
        ).format(scope, objective, inputs, completion or self.JUDGED)

    def _findings(self, tree=None, **kwargs):
        """Grade one built ticket and return its (class, detail) pairs."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "00-root.01.md"
            path.write_text(self._ticket(**kwargs), encoding="utf-8")
            found = cutcheck._check_ticket(
                path, tree if tree is not None else ROOT, None, self.SIBLINGS)
        return [(klass, detail) for _, _, klass, detail in found]

    def _classes(self, **kwargs):
        return [klass for klass, _ in self._findings(**kwargs)]

    # Screen 1: a fixed-input policy ordering a write the grant does not cover.

    MANIFEST_POLICY = (
        '- input: {"name":"manifest-policy","type":"literal","value":"Every unit'
        " that adds or removes a test module regenerates the serial-compat"
        ' manifest with tools/run_serial_compat.py --write-manifest."}'
    )

    def test_a_policy_input_ordering_a_write_outside_the_grant_is_reported(self):
        """`00-root.04` carried this policy while its grant forbade the write.

        Nothing in family 3 read the Fixed inputs, so the cut graded clean and
        the contradiction was resolved by hand, once per unit that carried it.
        """

        self.assertIn(cutcheck_ticket.POLICY_OUTSIDE_SCOPE,
                      self._classes(inputs=self.MANIFEST_POLICY))

    def test_the_same_policy_is_silent_where_the_grant_carries_the_artifact(self):
        self.assertNotIn(cutcheck_ticket.POLICY_OUTSIDE_SCOPE,
                         self._classes(inputs=self.MANIFEST_POLICY, scope="tools"))

    def test_a_policy_write_another_actor_performs_commits_this_item_to_nothing(self):
        """"The join appends" and "no unit appends" name somebody else.

        Reading every write verb in a Fixed inputs section as this item's would
        report nine of this run's own units for the covered-line policy alone.
        """

        for policy in (
            '- input: {"name":"covered","type":"literal","value":"The join'
            ' appends one line through scripts/tickets.py improvement."}',
            '- input: {"name":"covered","type":"literal","value":"No unit'
            ' appends to the sink covered.jsonl."}',
        ):
            with self.subTest(policy=policy):
                self.assertNotIn(cutcheck_ticket.POLICY_OUTSIDE_SCOPE,
                                 self._classes(inputs=policy))

    # Screen 2: the consumers of a phrase the objective orders deleted.

    PHRASE = "the staleness timer stops at the first claim"

    def _tree_pinning(self, phrase):
        tmp = Path(tempfile.mkdtemp(prefix="cutcheck-census-"))
        self.addCleanup(shutil.rmtree, str(tmp), True)
        (tmp / "tests").mkdir()
        (tmp / "tests" / "test_pin.py").write_text(
            'def test_it():\n    assert "{}" in text\n'.format(phrase), encoding="utf-8")
        (tmp / "tests" / "test_quiet.py").write_text(
            "def test_other():\n    assert True\n", encoding="utf-8")
        return tmp

    def test_a_deleted_phrase_a_test_asserts_verbatim_names_that_test(self):
        """`00-root.07` was ordered to delete prose three ungranted tests held.

        It could not land without breaking them and could not repair them.
        """

        found = self._findings(
            tree=self._tree_pinning(self.PHRASE),
            objective='The item deletes the passage "{}" from it.'.format(self.PHRASE))
        census = [d for k, d in found if k == cutcheck_ticket.UNGRANTED_CONSUMER]
        self.assertEqual(len(census), 1, found)
        self.assertIn("tests/test_pin.py", census[0])
        self.assertNotIn("test_quiet.py", census[0])

    def test_the_census_is_silent_where_nothing_ungranted_holds_the_phrase(self):
        """Both can-fail directions: the grant carries it, or nothing deletes it."""

        for scope, objective in (
            ("tests/test_pin.py", 'The item deletes the passage "{}".'),
            ("scripts/allowed.py", 'The item documents the passage "{}".'),
        ):
            with self.subTest(scope=scope):
                self.assertNotIn(cutcheck_ticket.UNGRANTED_CONSUMER, self._classes(
                    tree=self._tree_pinning(self.PHRASE), scope=scope,
                    objective=objective.format(self.PHRASE)))

    # Screen 3: a removal argued from reachability, with no probe behind it.

    UNREACHABLE = ("No v0-legacy branch survives in scripts/legacy.py: the lines"
                   " unreachable from every CLI write path are gone.")

    def test_a_removal_argued_from_reachability_needs_a_probe(self):
        """Plan item 10's premise, which the executor's own probes refuted.

        Write-path-unreachable is not dead: the branches the plan called dead
        were the live read path, and 12/9/9/2 hits said so once somebody looked.
        """

        self.assertIn(cutcheck_ticket.UNPROBED_REMOVAL,
                      self._classes(objective=self.UNREACHABLE))

    def test_a_recorded_probe_discharges_the_removal(self):
        self.assertNotIn(cutcheck_ticket.UNPROBED_REMOVAL, self._classes(
            objective=self.UNREACHABLE,
            inputs='- input: {"name":"reachability-probe","type":"literal",'
                   '"value":"12/9/9/2 hits over the suite."}'))

    def test_a_removal_claiming_no_reachability_is_asked_for_no_probe(self):
        """The screen grades the argument, never the deletion.

        Asking every removal for a probe would report both `cutcheck-scope-open`
        fixtures, whose objectives make no reachability claim at all.
        """

        self.assertNotIn(cutcheck_ticket.UNPROBED_REMOVAL, self._classes(
            objective="The item deletes the skill `skills/engines/orch-compose`."))

    # Screen 4: a relocation graded by substring markers alone.

    MARKERS = ('1. **The passage arrived.** `grep -n "claim-CAS" scripts/target.py`'
               " returns a line. oracle_class: deterministic. provenance: authored-here.")
    MOVED = "The item moves the claim-CAS protocol to scripts/target.py."

    def test_a_relocation_graded_by_markers_alone_is_flagged(self):
        """Markers cannot see the right words arriving with the wrong meaning.

        The relocated claim-CAS docstring asserted a call relationship that does
        not exist, cut to fit under a line cap precisely to green the marker.
        """

        self.assertTrue(cutcheck_ticket._marker_only_relocation(self.MOVED, self.MARKERS))

    def test_a_relocation_asserting_meaning_or_relocating_nothing_is_not_flagged(self):
        self.assertFalse(cutcheck_ticket._marker_only_relocation(
            self.MOVED, "1. **The described call happens.** A reviewer confirms the"
            " function behaves as the moved text describes. oracle_class: judged."))
        self.assertFalse(
            cutcheck_ticket._marker_only_relocation("The item adds a screen.", self.MARKERS))


class CutScopeScreenRegistrationTest(unittest.TestCase):
    """Each new class is family 3's, three move the status, none reads as a summary."""

    SCREENS = ("POLICY_OUTSIDE_SCOPE", "UNGRANTED_CONSUMER", "UNPROBED_REMOVAL")

    def test_the_three_refusing_screens_lie_outside_the_advisory_set(self):
        for name in self.SCREENS:
            klass = getattr(cutcheck_ticket, name)
            with self.subTest(klass=klass):
                self.assertEqual(cutcheck.FAMILY_OF[klass], cutcheck.FAMILY_3)
                self.assertNotIn(klass, cutcheck.ADVISORY)

    def test_screen_four_is_family_three_and_advisory(self):
        """The complement of the case above, and the objective's own
        requirement: wired while outside `ADVISORY`, screen 4 would refuse
        cuts, because family 3 is what `main` partitions on to set the status.
        """

        klass = cutcheck_ticket.MARKER_ONLY_RELOCATION
        self.assertEqual(cutcheck.FAMILY_3, cutcheck.FAMILY_OF[klass])
        self.assertIn(klass, cutcheck.ADVISORY)

    def test_no_screen_name_can_be_read_off_a_summary_line(self):
        """The rule every finding class answers to, asked of the new four."""

        for name in self.SCREENS + ("MARKER_ONLY_RELOCATION",):
            for line in (cutcheck.ADVISORY_HEADING, cutcheck.GRAPH_HEADING,
                         cutcheck.NO_FINDING_OUTSIDE):
                self.assertNotIn(getattr(cutcheck_ticket, name), line)


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
    "fixed_input_oracle",
    "shared_test_module",
)

# Case modules deliberately share this facade's helpers through ``import *``.
# TestCase classes are loader-owned instead: exporting one would bind the same
# class into every case module and make discovery execute it once per binding.
__all__ = tuple(
    name
    for name, value in globals().items()
    if not name.startswith("_")
    and not (
        isinstance(value, type)
        and issubclass(value, unittest.TestCase)
    )
)


def load_tests(loader, standard_tests, pattern):
    # The explicit loader keeps every case in this module's child process.

    suite = unittest.TestSuite()
    for name in CASE_MODULES:
        module = importlib.import_module("tests.test_cutcheck_cases." + name)
        suite.addTests(loader.loadTestsFromModule(module))
    # This module's own cases, named rather than inherited: `standard_tests` is
    # what the loader built before asking, and returning a suite built from
    # `CASE_MODULES` alone discards it. A class defined here therefore runs only
    # where something names it -- until now that was one case module importing
    # `RuntimeInterpreterBoundaryTests` by hand from outside, which puts this
    # module's collection in a file this module does not own.
    for case in (CutScopeScreenTest, CutScopeScreenRegistrationTest):
        suite.addTests(loader.loadTestsFromTestCase(case))
    return suite


if __name__ == "__main__":
    if "--record" in sys.argv:
        record_verdicts()
    else:
        unittest.main()
