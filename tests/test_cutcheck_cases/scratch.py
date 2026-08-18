"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403

try:
    del load_tests
except NameError:
    pass

def rmtree_calls(tree):
    """Every ``shutil.rmtree`` in a parsed module, with its ``ignore_errors``.

    Three spellings, because they silence the same thing: the call itself, and
    the call deferred through ``addCleanup`` or ``addClassCleanup``, where the
    third positional is ``ignore_errors`` and reads as a bare ``True`` at the
    call site. The class-scoped spelling is here because it was missing: two
    swallowing removals reached the tree behind it, one of them over a full
    clone of this repository.
    """

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "rmtree":
            yield node, node.args[1:], node.keywords
        elif (
            node.func.attr in ("addCleanup", "addClassCleanup")
            and node.args
            and isinstance(node.args[0], ast.Attribute)
            and node.args[0].attr == "rmtree"
        ):
            yield node, node.args[2:], node.keywords


def swallows(rest, keywords):
    """Does this call ask ``rmtree`` to discard the errors it raises?"""

    given = list(rest) + [k.value for k in keywords if k.arg == "ignore_errors"]
    return any(
        not (isinstance(node, ast.Constant) and node.value is False) for node in given
    )


class ScratchCleanupReportingTest(unittest.TestCase):
    """The root an invocation makes is removed, and a failure to remove it is said.

    The removal itself is not new -- `mkdtemp` and `try:` are adjacent and the
    `finally` covers the exception path and the early `NO_TICKET_SET` alike.
    What is new is that anything checks it. `ignore_errors=True` in the tool
    whose subject is swallowed errors leaves a 12M copy on disk and says
    nothing, which is how seven roots accumulated unnoticed.
    """

    # A revision that resolves nowhere, so `main` returns at the early
    # `NO_TICKET_SET` its `finally` also covers: no clone, no oracle, and the
    # cleanup under test reached in milliseconds rather than minutes.
    UNRESOLVABLE = "cutcheck-no-such-revision"

    def setUp(self):
        here = Path.cwd()
        self.addCleanup(os.chdir, str(here))
        os.chdir(str(ROOT))
        self.addCleanup(cutcheck._EXIT_CACHE.clear)
        self.addCleanup(cutcheck._TREE_STATE.clear)
        self.addCleanup(cutcheck._MUTATED.clear)

    def _main_naming_its_scratch_root(self):
        """Run `main` to its `finally`, holding the exact root that run created.

        `_scratch_root` is wrapped rather than the filesystem searched. A
        `.cutcheck-*` glob would also match this suite's own roots and, worse,
        a concurrently running cut's live tree; a directory listing is flaky
        the moment two cuts overlap, which on this machine they do.
        """

        created = []
        real = cutcheck._scratch_root

        def recording(worktree_root):
            root = real(worktree_root)
            # Non-vacuity, asserted where it is still true: "the root is gone"
            # passes for the wrong reason over a root that was never made.
            self.assertIsNotNone(root, "no scratch root was created")
            self.assertTrue(root.is_dir(), "{} was never a directory".format(root))
            created.append(root)
            return root

        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(cutcheck, "_scratch_root", recording):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = cutcheck.main(
                    ["cutcheck-clean", "--baseline", self.UNRESOLVABLE]
                )
        self.assertEqual(len(created), 1, created)
        return code, out.getvalue(), err.getvalue(), created[0]

    def test_main_removes_the_root_it_created(self):
        code, _, _, root = self._main_naming_its_scratch_root()
        self.assertEqual(code, cutcheck.NO_TICKET_SET)
        self.assertFalse(root.exists(), "{} outlived the run that made it".format(root))

    def test_a_failing_removal_is_reported(self):
        with mock.patch.object(
            cutcheck.shutil, "rmtree", side_effect=OSError(13, "Permission denied")
        ):
            code, _, err, root = self._main_naming_its_scratch_root()
        self.addCleanup(shutil.rmtree, root)
        # The failure was a real one: said or swallowed, the root is still on
        # disk, and that state is what the report exists to make visible.
        self.assertTrue(root.is_dir(), "the removal did not actually fail")
        self.assertIn(cutcheck.SCRATCH_NOT_REMOVED, err)
        self.assertIn(str(root), err)
        self.assertIn("Permission denied", err)
        # Reported, not re-graded: a leaked root is the tool's own hygiene and
        # never a finding against the ticket set it was reading.
        self.assertEqual(code, cutcheck.NO_TICKET_SET)

    def test_a_failing_removal_stays_out_of_the_graded_report(self):
        """The diagnostic may not disturb the report it is a diagnostic about.

        `RecordedVerdictTest` compares each of 27 fixture sets' stdout whole, and
        the `finally` runs before a single finding is printed. A leak report on
        stdout would therefore prepend a line to every pinned verdict on any
        host where a removal really fails -- and one does: git writes objects
        `0o444`, and Windows refuses to unlink a file with no write bit. The
        report belongs on the stream that is not the report.
        """

        with mock.patch.object(
            cutcheck.shutil, "rmtree", side_effect=OSError(13, "Permission denied")
        ):
            _, out, err, root = self._main_naming_its_scratch_root()
        self.addCleanup(shutil.rmtree, root)
        self.assertIn(cutcheck.SCRATCH_NOT_REMOVED, err)
        self.assertNotIn(cutcheck.SCRATCH_NOT_REMOVED, out)

    def test_a_root_git_left_read_only_is_still_removed(self):
        """The removal survives the mode git puts on every object it writes.

        Git writes loose objects and packs `0o444` and hardlinks that mode into
        each clone, so a strict removal meets it on every platform; on Windows
        a file carrying no write bit cannot be unlinked at all, which would
        turn this ticket's own removal assertion red there and leak 12M per
        run. The probe is the POSIX shape of the same refusal -- a directory
        whose write bit is off will not give up its children -- because that is
        the refusal this host can be made to exhibit.
        """

        if not self._refuses_unlink_under_a_read_only_directory():
            self.skipTest(
                "this host unlinks inside a write-protected directory, so the "
                "retry cannot be made to discriminate here"
            )
        root = Path(tempfile.mkdtemp(prefix="cutcheck-readonly-"))
        self.addCleanup(self._force_remove, root)
        held = root / "objects" / "0d"
        held.mkdir(parents=True)
        (held / "8a474fc6797").write_text("object", encoding="utf-8")
        held.chmod(0o500)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            cutcheck._remove_scratch_root(root)
        self.assertFalse(root.exists(), "{} survived its removal".format(root))
        self.assertEqual(err.getvalue(), "")

    def _refuses_unlink_under_a_read_only_directory(self):
        probe = Path(tempfile.mkdtemp(prefix="cutcheck-probe-mode-"))
        self.addCleanup(self._force_remove, probe)
        sub = probe / "sub"
        sub.mkdir()
        (sub / "f").write_text("x", encoding="utf-8")
        sub.chmod(0o500)
        try:
            (sub / "f").unlink()
        except OSError:
            return True
        return False

    @staticmethod
    def _force_remove(root):
        """Undo the modes this test set, then remove strictly like the rest.

        Absence is the success case here and never an error to discard: the
        test under it removes the root itself.
        """

        if not root.exists():
            return
        for path in [root] + sorted(root.rglob("*")):
            try:
                path.chmod(0o700)
            except OSError:
                pass
        shutil.rmtree(str(root))

    def test_a_removal_that_succeeds_says_nothing(self):
        # The can-fail direction for the lines above: a report printed
        # unconditionally would carry no information about the removal.
        _, out, err, _ = self._main_naming_its_scratch_root()
        self.assertNotIn(cutcheck.SCRATCH_NOT_REMOVED, out + err)

    def test_suite_cleanups_do_not_swallow(self):
        """The instrument may not silence what the subject is on trial for.

        Read from source across every test module, so it covers every removal
        the suite performs rather than the two a search happened to name. This
        module alone was the earlier scope, and three swallowing removals sat
        in two others -- one over a full clone of this repository -- where the
        reading could not reach them.
        """

        modules = sorted(Path(__file__).resolve().parent.glob("*.py"))
        self.assertTrue(modules, "no test module was found to read")
        swallowing, checked = [], 0
        for source in modules:
            calls = list(rmtree_calls(ast.parse(source.read_text(encoding="utf-8"))))
            checked += len(calls)
            swallowing.extend(
                "{}:{}".format(source.name, node.lineno)
                for node, rest, keywords in calls
                if swallows(rest, keywords)
            )
        self.assertTrue(checked, "no shutil.rmtree call was found to check")
        self.assertEqual(
            swallowing, [], "these removals discard the failure they should report"
        )


def placement_repo(case):
    """A main checkout and one linked worktree of it, under one temporary root.

    Both origins built here rather than read off this machine: the placement
    has to answer the same from either, and this repository's own 62 worktrees
    are one arrangement of one host. One temporary root also means the
    filesystem clause below compares a placement and not a mount table.
    """

    base = Path(tempfile.mkdtemp(prefix="cutcheck-placement-"))
    case.addCleanup(remove_repo_tree, base)
    main = base / "main"
    main.mkdir()
    for args in (
        ["init", "-q", "."],
        ["config", "user.email", "cutcheck@example.invalid"],
        ["config", "user.name", "cutcheck"],
        ["config", "commit.gpgsign", "false"],
    ):
        must_git(case, args, main)
    (main / "a.txt").write_text("one\n", encoding="utf-8")
    must_git(case, ["add", "-A"], main)
    must_git(case, ["commit", "-qm", "one"], main)
    linked = base / "linked"
    must_git(case, ["worktree", "add", "-q", "--detach", str(linked)], main)
    return main, linked


class ScratchRootPlacementTest(unittest.TestCase):
    """Where the copies land: the system temp directory, and nowhere the target
    decides.

    Placement inside the target's own git common dir put the copies beside the
    object store a clone hardlinks from, which is faster, and made the whole
    tool unusable on Windows: the copy's paths are the target's path plus
    `.git/cutcheck-scratch/.cutcheck-XXXXXXXX/<rev>/` plus the deepest path in
    the revision, and a 183-character worktree root took `git clone` past
    MAX_PATH on its own template copy -- which `core.longpaths=true` does not
    cover. Every invocation from that tree exited 2 before grading anything.

    So the length of a scratch path is now a fact about the host's temp
    directory rather than about the tree being graded, and speed gives way to
    running at all.
    """

    def setUp(self):
        self.main, self.linked = placement_repo(self)

    def _root(self, origin):
        root = cutcheck._scratch_root(origin)
        self.assertIsNotNone(root, "no scratch root was placed for {}".format(origin))
        self.addCleanup(remove_repo_tree, root)
        return root.resolve()

    def test_the_root_lands_under_the_system_temp_directory(self):
        for origin in (self.main, self.linked):
            with self.subTest(origin=origin.name):
                self.assertEqual(
                    self._root(origin).parent,
                    Path(tempfile.gettempdir()).resolve(),
                )

    def test_no_copy_lands_inside_the_tree_being_graded(self):
        for origin in (self.main, self.linked):
            with self.subTest(origin=origin.name):
                root = self._root(origin)
                self.assertNotIn(origin.resolve(), root.parents)

    def test_the_scratch_path_is_no_longer_the_targets_path_plus_a_suffix(self):
        """The MAX_PATH regression, stated as the length it broke on.

        A root derived from the tree grows with it; this one does not, so the
        183-character worktree that could clone nothing is the same length here
        as a two-character one.
        """

        deep = Path(tempfile.mkdtemp(prefix="cutcheck-deep-"))
        self.addCleanup(remove_repo_tree, deep)
        long_tree = deep / ("d" * 60) / ("e" * 60) / ("f" * 40)
        long_tree.mkdir(parents=True)
        # Both sides raw: the claim is that the target's path length does not
        # reach the scratch path, so both spellings must come from the same
        # mkdtemp. Resolving one side compares two spellings of the temp root
        # instead -- an 8.3 TEMP component on Windows runners and macOS's
        # /var -> /private/var symlink each made only the resolved side longer.
        near = cutcheck._scratch_root(self.main)
        self.assertIsNotNone(near, "the near tree got no scratch root")
        self.addCleanup(remove_repo_tree, near)
        far = cutcheck._scratch_root(long_tree)
        self.assertIsNotNone(far, "a deep tree got no scratch root")
        self.addCleanup(remove_repo_tree, far)
        self.assertEqual(len(str(near)), len(str(far)))

    def test_each_invocation_gets_a_root_of_its_own(self):
        # Two cuts running at once share the directory and never the tree.
        first, second = self._root(self.main), self._root(self.linked)
        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, second.parent)

    def test_a_clone_into_the_scratch_root_carries_the_revisions_history(self):
        """What the placement still has to buy: a copy that is a clone.

        Hardlinking was the old placement's argument and it is gone with it --
        the temp directory may be another volume, and a full object copy there
        is correct and slower. What may not be given up is history: an oracle
        reading a copy with no `.git` reads whichever repository encloses it.
        """

        root = self._root(self.linked)
        tree = cutcheck._scratch_tree("HEAD", self.linked, root)
        self.assertIsNotNone(tree, "no scratch tree was cloned")
        self.assertTrue((tree / ".git").exists(), "the copy carries no history")

    def test_the_module_names_no_directory_inside_the_target_any_more(self):
        source = (ROOT / "scripts" / "cutcheck.py").read_text(encoding="utf-8")
        self.assertNotIn("cutcheck-scratch", source)
        self.assertNotIn("git-common-dir", source)


class BytecodeAdvisoryTest(unittest.TestCase):
    """Importing a package writes bytecode, and that is a spelling note.

    A python oracle that imports anything writes `__pycache__/` into the copy,
    and the delta reading convicted the first one graded as `unconfined-oracle`
    -- an exit-setting class whose repair, `-B`, is stated in no skill, no
    oracle policy and no report. What a copy writes back into itself is the
    hazard that class is for; bytecode is the interpreter's own cache, lands
    inside the copy, and is answered by a flag. So the report says the flag.
    """

    def _classes(self, mutated):
        """Graded through a ticket whose span is a process, because the delta is.

        `cutcheck-root-gate/00-root.01` was the vehicle until the search heads
        stopped being processes. `_MUTATED` is filled where a span was run, so
        a `grep` span -- answered in this interpreter now, and writing nothing
        by construction -- leaves a stubbed `_mutations` with nothing to be
        read from, and all three assertions below went quiet at once. The
        subject here is what a span wrote into the copy, so the vehicle is a
        span that can still write one.
        """

        ticket = FIXTURES / "cutcheck-git-graded" / "01-git-graded.md"
        cutcheck._EXIT_CACHE.clear()
        with mock.patch.object(cutcheck, "_mutations", lambda tree: list(mutated)):
            findings = cutcheck._check_ticket(ticket, ROOT, None, {})
        return findings, [klass for _, _, klass, _ in findings]

    def test_bytecode_alone_is_advisory_and_names_the_flag_that_answers_it(self):
        findings, classes = self._classes(["tests/__pycache__/"])
        self.assertIn(cutcheck.BYTECODE_WRITTEN, classes, findings)
        self.assertNotIn(cutcheck.UNCONFINED_ORACLE, classes, findings)
        detail = [f[3] for f in findings if f[2] == cutcheck.BYTECODE_WRITTEN][0]
        self.assertIn("tests/__pycache__/", detail)
        self.assertIn("-B", detail)

    def test_the_advisory_class_never_sets_the_exit_status(self):
        self.assertIn(cutcheck.BYTECODE_WRITTEN, cutcheck.ADVISORY)

    def test_anything_else_the_span_wrote_is_still_the_exit_setting_class(self):
        findings, classes = self._classes(["scratch.txt"])
        self.assertIn(cutcheck.UNCONFINED_ORACLE, classes, findings)
        self.assertNotIn(cutcheck.BYTECODE_WRITTEN, classes, findings)

    def test_a_span_writing_both_is_reported_for_both(self):
        findings, classes = self._classes(["tests/__pycache__/", "scratch.txt"])
        self.assertIn(cutcheck.UNCONFINED_ORACLE, classes, findings)
        self.assertIn(cutcheck.BYTECODE_WRITTEN, classes, findings)
        wrote = [f[3] for f in findings if f[2] == cutcheck.UNCONFINED_ORACLE][0]
        self.assertIn("scratch.txt", wrote)
        self.assertNotIn("__pycache__", wrote)


class SharedScratchHarnessTest(unittest.TestCase):
    """What the module's own grading harness may and may not do to the tool.

    Every grading here but three runs `main` in this process against copies
    the whole module shares, which is what turns 231 clones of a 78M
    repository into 5. Three things have to stay true for that to be a
    measurement of the tool rather than of a stub: the patches are scoped to
    the call, the reports are values, and the shared root is this process's own.
    """

    def test_the_harness_leaves_the_real_scratch_lifecycle_in_place(self):
        """The two classes next door grade the real removal, so they must reach it.

        `ScratchCleanupReportingTest` and `ScratchRootPlacementTest` assert on
        `_scratch_root` and `_remove_scratch_root` themselves. A module-wide
        patch -- a `setUpModule` that starts one and never stops it -- would
        leave both of them grading a lambda and passing, so the harness patches
        inside the call it grades and nowhere else. Read after a grading, which
        is when a leaked patch would still be standing.
        """

        before = (cutcheck._scratch_root, cutcheck._remove_scratch_root)
        run_cutcheck("cutcheck-clean")
        self.assertEqual(
            (cutcheck._scratch_root, cutcheck._remove_scratch_root), before
        )
        for name, func in zip(("_scratch_root", "_remove_scratch_root"), before):
            with self.subTest(function=name):
                self.assertEqual(func.__name__, name)
                self.assertEqual(func.__module__, cutcheck.__name__)

    def test_two_readings_of_one_pair_are_one_grading_and_two_values(self):
        """A memoised report is handed out by copy, so no caller can spend it.

        The rewrite is the assertion. Two callers holding one object is a
        report the second one reads after the first edited it, and 41 call
        sites read this dictionary.
        """

        first, second = run_cutcheck("cutcheck-clean"), run_cutcheck("cutcheck-clean")
        self.assertIsNot(first, second)
        self.assertEqual(
            (first.returncode, first.stdout, first.stderr),
            (second.returncode, second.stdout, second.stderr),
        )
        first.stdout = "a caller rewrote its own copy"
        self.assertNotEqual(run_cutcheck("cutcheck-clean").stdout, first.stdout)

    def test_the_shared_root_is_this_processs_own_inside_the_tools_place(self):
        """Two suites at once share the directory and never a tree.

        The place is the host's temp directory, which every process on the
        machine shares, so a fixed name here would be two concurrent runs
        writing one tree. It is a `mkdtemp` of the tool's own making instead,
        and the neighbour built below is what says so rather than the prefix.
        """

        root = shared_root()
        self.assertEqual(shared_root(), root, "a second root is a second pair of clones")
        self.assertTrue(root.is_dir(), root)
        self.assertEqual(root.resolve().parent, Path(tempfile.gettempdir()).resolve())
        neighbour = cutcheck._scratch_root(ROOT)
        self.addCleanup(remove_repo_tree, neighbour)
        self.assertEqual(neighbour.resolve().parent, root.resolve().parent)
        self.assertNotEqual(neighbour, root)
