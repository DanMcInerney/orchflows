"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403

try:
    del load_tests
except NameError:
    pass

SYMLINK_SKIP_PREFIX = "symlink creation unavailable, so the escape cannot be built here"


def _symlink_capability(directory):
    """Why no symlink can be created under `directory`, or None if one can.

    Probed, never inferred from `os.name`: `os.symlink` exists on Windows and
    raises without SeCreateSymbolicLinkPrivilege, so a platform test would skip
    a capable runner and -- the defect that matters -- would have to guess for
    an incapable one. The probe answers for the filesystem the escape is built
    on, and leaves it as it found it.
    """

    probe = Path(directory) / ".cutcheck-symlink-probe"
    try:
        os.symlink(str(Path(directory) / "no-such-target"), str(probe))
    except (OSError, NotImplementedError, ValueError) as exc:
        return "{}: {}".format(SYMLINK_SKIP_PREFIX, exc)
    os.unlink(str(probe))
    return None


def require_symlinks(case, directory):
    """Skip `case` with a recorded reason where the escape cannot be built."""

    reason = _symlink_capability(directory)
    if reason is not None:
        case.skipTest(reason)


def _symlink_source(case):
    """A source tree committing a symlink that points outside itself.

    Two commits, so `HEAD~1` names a range a diff can be asked for, and an
    `outside/` directory beside the tree that nothing inside it may reach.
    Built in a temporary directory of its own: the wrong result this pair of
    tests needs is built beside the tree under test, never in it.
    """

    root = Path(tempfile.mkdtemp(prefix="cutcheck-symlink-"))
    case.addCleanup(remove_repo_tree, root)
    require_symlinks(case, root)
    outside = root / "outside"
    outside.mkdir()
    src = root / "src"
    (src / "sub").mkdir(parents=True)
    for args in (
        ["init", "-q", "."],
        ["config", "user.email", "cutcheck@example.invalid"],
        ["config", "user.name", "cutcheck"],
    ):
        cutcheck._git(args, src)
    (src / "sub" / "a.txt").write_text("one\n", encoding="utf-8")
    os.symlink(str(outside), str(src / "link"))
    cutcheck._git(["add", "-A"], src)
    cutcheck._git(["commit", "-qm", "one"], src)
    (src / "sub" / "a.txt").write_text("one\ntwo\n", encoding="utf-8")
    cutcheck._git(["add", "-A"], src)
    cutcheck._git(["commit", "-qm", "two"], src)
    return root, src, outside


def _symlink_copy(case):
    """The copy `_scratch_tree` builds from that source, and what lies outside.

    The real function, not a re-spelling of it: what is under test is whether
    the copy this module grades oracles in confines them, so any other clone
    would grade a different tree than the one cutcheck builds.
    """

    root, src, outside = _symlink_source(case)
    scratch_root = root / "scratch"
    scratch_root.mkdir()
    tree = cutcheck._scratch_tree("HEAD", src, scratch_root)
    case.assertIsNotNone(tree, "no scratch copy was built from the symlink source")
    return tree, outside


class GitConfinementGateTest(unittest.TestCase):
    """Which git spans the gate runs, decided from the command text alone."""

    def test_every_escape_the_head_used_to_carry_is_refused(self):
        for command in GIT_ESCAPES:
            self.assertTrue(cutcheck._unconfined_git(command), command)
            self.assertIn(cutcheck.UNCONFINED_ORACLE, cutcheck._shape(command), command)

    def test_a_confined_subcommand_reaching_out_is_refused_too(self):
        # The subcommand is in the set and the span is still not confined: an
        # option standing after it named somewhere the copy does not hold.
        for command in GIT_REACHES_OUT:
            self.assertIn(command.split()[1], cutcheck.GIT_CONFINED_SUBCOMMANDS, command)
            self.assertTrue(cutcheck._unconfined_git(command), command)
            self.assertIn(cutcheck.UNCONFINED_ORACLE, cutcheck._shape(command), command)

    def test_the_oracles_the_graded_set_states_still_run(self):
        for command in (
            "git log -1 --format=%H",
            "git diff ac8791a -- install.py",
            "git merge-base --is-ancestor ac8791a HEAD",
            "git rev-list --count HEAD",
            "git status --porcelain",
            # What the copy holds it may reach: the rule is about the location
            # named, never about the flag naming it. A `..` between revisions
            # is a range and stays one; only a whole path component reads as a
            # climb, whatever slashes stand beside it.
            "git log --oneline ac8791a..462ef52 -- scripts/cutcheck.py",
            "git show ac8791a:install.py",
            "git diff --no-index install.py tools/validate.py",
        ):
            self.assertFalse(cutcheck._unconfined_git(command), command)
            self.assertEqual(cutcheck._shape(command), [], command)

    def test_a_head_that_is_not_git_is_judged_by_no_git_rule(self):
        for command in ("grep -n SCRIPT_NAMES install.py", "python3 tools/validate.py"):
            self.assertFalse(cutcheck._unconfined_git(command), command)

    def test_the_gate_reads_the_argv_that_would_run(self):
        # Split the way `_run_once` splits, or the gate grades one command and
        # execution runs another. Quoting that resolves to a confined
        # subcommand is confined; quoting that resolves to anything else is not.
        self.assertFalse(cutcheck._unconfined_git("git 'log' -1 --format=%H"))
        self.assertTrue(cutcheck._unconfined_git("git 'log x' -1"))

    def test_a_span_no_split_parses_is_claimed_by_nothing_and_runs_nowhere(self):
        unparsed = 'git log "'
        self.assertFalse(cutcheck._unconfined_git(unparsed))
        self.assertIsNone(cutcheck._run_once(unparsed, ROOT))

    def test_committed_symlink_cannot_escape_the_copy(self):
        """The third route `_names_outside_the_copy` names and cannot close.

        `link/PAYLOAD` is neither rooted nor climbing, so the text gate reads
        it as confined and is right about the token and wrong about the file.
        Measured at the baseline: 121 bytes landed outside the copy. Only the
        copy can answer this, so the copy is what has to refuse it.
        """

        tree, outside = _symlink_copy(self)
        span = "git diff --output=link/PAYLOAD HEAD~1"
        self.assertFalse(cutcheck._unconfined_git(span), "the text gate permits it")
        proc = cutcheck._git(["diff", "--output=link/PAYLOAD", "HEAD~1"], tree)
        self.assertEqual(
            sorted(path.name for path in outside.iterdir()),
            [],
            "the copy wrote through a committed symlink: {}".format(proc.stderr),
        )

    def test_a_committed_symlink_cannot_be_read_through_by_an_orderfile(self):
        """The same route, read rather than written: `-O` opens what it names."""

        tree, outside = _symlink_copy(self)
        (outside / "orderfile").write_text("sub/a.txt\n", encoding="utf-8")
        span = "git diff -Olink/orderfile HEAD~1"
        self.assertFalse(cutcheck._unconfined_git(span), "the text gate permits it")
        proc = cutcheck._git(["diff", "-Olink/orderfile", "HEAD~1"], tree)
        self.assertNotEqual(
            proc.returncode,
            0,
            "the copy read an orderfile lying outside it",
        )
        self.assertIn("orderfile", proc.stderr)


class SymlinkCapabilityGuardTest(unittest.TestCase):
    """Neither escape test may pass where the escape cannot be built.

    A check that cannot fail decides nothing, and on a platform with no
    symlink privilege neither confinement test can construct the wrong result
    it exists to refuse. Passing there would report a guarantee nothing
    checked -- on the three `windows-latest` matrix legs, every leg of it. So
    they skip, and the reason is recorded rather than inferred from the count.
    """

    ESCAPE_TESTS = (
        "test_committed_symlink_cannot_escape_the_copy",
        "test_a_committed_symlink_cannot_be_read_through_by_an_orderfile",
    )

    def _incapable(self):
        # What a Windows runner without SeCreateSymbolicLinkPrivilege raises.
        return mock.patch.object(
            os,
            "symlink",
            side_effect=OSError(1, "A required privilege is not held by the client"),
        )

    def test_each_escape_test_skips_with_a_reason_rather_than_passing(self):
        for name in self.ESCAPE_TESTS:
            with self.subTest(test=name):
                result = unittest.TestResult()
                with self._incapable():
                    GitConfinementGateTest(name).run(result)
                self.assertEqual(result.errors, [], "the guard never ran")
                self.assertEqual(result.failures, [])
                self.assertEqual(len(result.skipped), 1, "it passed vacuously")
                self.assertEqual(
                    result.skipped[0][1],
                    SYMLINK_SKIP_PREFIX
                    + ": [Errno 1] A required privilege is not held by the client",
                )

    def test_the_probe_answers_what_the_platform_actually_does(self):
        """A guard that always skips is the same vacuity facing the other way.

        No skip of its own: whichever way this host answers, the probe has to
        agree with it, so the assertion is total on every platform.
        """

        root = Path(tempfile.mkdtemp(prefix="cutcheck-probe-"))
        self.addCleanup(shutil.rmtree, root)
        direct = root / "direct"
        try:
            os.symlink(str(root / "no-such-target"), str(direct))
        except (OSError, NotImplementedError, ValueError):
            capable = False
        else:
            capable = True
            os.unlink(str(direct))
        self.assertEqual(_symlink_capability(root) is None, capable)

    def test_the_probe_leaves_the_directory_as_it_found_it(self):
        root = Path(tempfile.mkdtemp(prefix="cutcheck-probe-"))
        self.addCleanup(shutil.rmtree, root)
        _symlink_capability(root)
        self.assertEqual(sorted(path.name for path in root.iterdir()), [])


def _tree_with_a_symlink_entry(case):
    """A repository whose HEAD records a `120000` entry, built without one.

    `update-index --cacheinfo` writes the mode straight into the index, so the
    instrument's own test needs no symlink privilege and reads the same on
    every platform. That is the point rather than a convenience: what §5
    forbids is the recorded mode, and the checkout a platform makes of it is a
    separate question this check does not ask.
    """

    root = Path(tempfile.mkdtemp(prefix="cutcheck-mode-"))
    case.addCleanup(remove_repo_tree, root)
    for args in (
        ["init", "-q", "."],
        ["config", "user.email", "cutcheck@example.invalid"],
        ["config", "user.name", "cutcheck"],
    ):
        cutcheck._git(args, root)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    cutcheck._git(["add", "a.txt"], root)
    blob = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=str(root),
        input="../outside\n",
        capture_output=True,
        text=True,
    ).stdout.strip()
    cutcheck._git(
        ["update-index", "--add", "--cacheinfo", "120000,{},sub/link".format(blob)],
        root,
    )
    cutcheck._git(["commit", "-qm", "a symlink entry, and no symlink on disk"], root)
    return root


class SymlinkModeCheckTest(unittest.TestCase):
    """`rules/visibility.md` §5's instrument: the mode git records.

    Read from the tree and never from the checkout, so `core.symlinks=false`
    -- which is what confines the copy -- does not blind the check that says
    the tree broke the rule.
    """

    def test_an_entry_anywhere_in_the_tree_is_found_by_its_mode(self):
        tree = _tree_with_a_symlink_entry(self)
        self.assertEqual(cutcheck._symlink_entries(tree), ["sub/link"])

    def test_the_entry_is_reported_against_the_run(self):
        tree = _tree_with_a_symlink_entry(self)
        self.assertEqual(
            cutcheck._symlink_findings("some-run", (tree, None)),
            [("some-run", 0, cutcheck.SYMLINK_IN_TREE, "sub/link")],
        )

    def test_a_path_both_graded_trees_record_is_named_once(self):
        tree = _tree_with_a_symlink_entry(self)
        self.assertEqual(len(cutcheck._symlink_findings("some-run", (tree, tree))), 1)

    def test_the_class_carries_a_family_and_is_advisory(self):
        """Reported, and never deciding a cut it is not a defect of.

        `scripts/cutcheck.py` owns cut-defect detection over an issued ticket
        set (ARCHITECTURE.md). A committed symlink is a property of the
        repository, and confinement is enforced by the clone flag whether or
        not anyone reads this line -- so the report carries visibility, not
        safety, and failing a cut for it would fail every cut in every
        repository where a symlink is legal.
        """

        self.assertIn(cutcheck.SYMLINK_IN_TREE, cutcheck.FAMILY_OF)
        self.assertIn(cutcheck.SYMLINK_IN_TREE, cutcheck.ADVISORY)

    def test_this_repositorys_own_tree_carries_no_such_entry(self):
        self.assertEqual(cutcheck._symlink_entries(ROOT), [])

    def test_the_check_is_wired_into_the_report_and_not_only_defined(self):
        """A reported class nothing calls is the vacuous shape one step over."""

        source = (ROOT / "scripts" / "cutcheck.py").read_text(encoding="utf-8")
        defined = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        ]
        called = {
            node.func.id
            for node in ast.walk(defined[0])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertIn("_symlink_findings", called)


VISIBILITY = ROOT / "rules" / "visibility.md"


def _visibility_clause(number):
    """One flat numbered clause of `rules/visibility.md`."""

    match = re.search(
        r"^{}\.[ ](.*?)(?=^\d+\.[ ]|\Z)".format(number),
        VISIBILITY.read_text(encoding="utf-8"),
        re.S | re.M,
    )
    assert match is not None, "rules/visibility.md has no clause {}".format(number)
    return " ".join(match.group(1).split())


class VisibilitySymlinkClauseTest(unittest.TestCase):
    """§5 forbade symlinks and named nothing that reads a tree for one.

    A prohibition whose instrument is unnamed is one no reader can run, and
    the gap this item closes is exactly that: the rule now says what grades it.
    """

    def test_section_five_names_its_instrument(self):
        clause = _visibility_clause(5)
        for named in (
            "scripts/cutcheck.py",
            cutcheck.SYMLINK_IN_TREE,
            cutcheck.SYMLINK_MODE,
        ):
            self.assertIn(named, clause, clause)

    def test_the_clause_keeps_what_it_already_owned(self):
        """Amended, not replaced: §5 keeps the symlink fact; the scripts'
        stdlib / cross-platform / no-network fact is ARCHITECTURE.md's
        scripts bullet (moved 2026-08-16, an ownership fact under a symlink
        clause)."""

        clause = _visibility_clause(5)
        self.assertIn("No symlinks", clause, clause)
        bullet = " ".join((ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8").split())
        for kept in ("Python 3.9+", "Windows and POSIX", "no network"):
            self.assertIn(kept, bullet)
