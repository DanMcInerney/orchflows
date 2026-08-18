"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403

try:
    del load_tests
except NameError:
    pass

class ScopeContainmentTest(unittest.TestCase):
    """A grant covers what is under it, never the directory that holds it."""

    def test_a_grant_of_one_file_is_no_grant_over_its_parent(self):
        self.assertFalse(cutcheck._covered("scripts", ["scripts/cutcheck.py"]))

    def test_a_directory_grant_does_not_cover_a_filename_it_never_names(self):
        self.assertFalse(cutcheck._covered("pins.json", ["tests/fixtures/cutcheck/"]))

    def test_a_grants_own_basename_is_the_file_it_granted(self):
        self.assertTrue(cutcheck._covered("cutcheck.py", ["scripts/cutcheck.py"]))

    def test_a_path_under_a_granted_directory_is_covered(self):
        self.assertTrue(
            cutcheck._covered(
                "tests/fixtures/cutcheck/cutcheck-evalhead/01-evalhead.md",
                ["tests/fixtures/cutcheck/"],
            )
        )


# Item 05's five readers. Every one of them resolved run state under the
# repository before this item; every one of them reaches the sink now, and
# the last two entries prove it for the whole set at once.
READERS = (
    "scripts/cutcheck.py",
    "scripts/ui.py",
    "scripts/isolate.py",
    "scripts/trace.py",
    "tools/live_sweep_e2e.py",
)

# Every non-docstring string literal in those files that still names `.orch`,
# with the reason it is allowed to. Anything else is a reader left behind.
ALLOWED_STATE_LITERALS = {
    # The canary is a git-tracked golden fixture under the repository, not
    # run state, and the item's `excluded_actions` forbid moving it.
    "scripts/cutcheck.py": {".orch"},
    # Where a run snapshot lands inside an isolated tree. A copy of the
    # sink's layout, not a state root: `state_root.py` still owns that.
    "scripts/isolate.py": {".orchflows-state"},
    # Item 05 criterion 4: a trace may cover a session that predates the
    # migration, so the harvester matches the repository shape as well as
    # the sink's. This matches a path in someone else's transcript; it
    # composes no path this host reads.
    "scripts/trace.py": {
        r"(?:\.orch|\.orchflows[/\\]state)",
    },
    "scripts/ui.py": set(),
    "tools/live_sweep_e2e.py": set(),
}


def state_literals(relative: str) -> set:
    """Every string literal in one reader that names `.orch`, docstrings
    excluded: prose is item 07's, and a comment is not a path."""

    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and ".orch" in node.value
        and id(node) not in docstrings
    }


class TestCutcheckResolvesSink(unittest.TestCase):
    """Item 05 criteria 1 and 6. `cutcheck.py` grades a run from wherever the
    run's tickets are, which is the sink now -- and still grades the canary,
    which is a fixture in the repository and stays there."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.sink = self.tmp / "sink"
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)

    def issue(self, root: Path, run: str, source: str = "cutcheck-clean") -> Path:
        """One fixture ticket set, copied to `root` under the name `run`."""

        dest = root / run
        dest.mkdir(parents=True)
        for src in sorted(
            (ROOT / "tests" / "fixtures" / "cutcheck" / source).glob("*.md")
        ):
            shutil.copyfile(str(src), str(dest / src.name))
        return dest

    @contextlib.contextmanager
    def launched_from(self, where: Path):
        """cwd and sink both pointed away from this repository."""

        cwd = os.getcwd()
        os.chdir(str(where))
        try:
            with mock.patch.dict(
                os.environ, {state_root.ENV_VAR: str(self.sink)}
            ):
                yield
        finally:
            os.chdir(cwd)

    # --- criterion 1 ---------------------------------------------------

    def test_a_run_living_only_in_the_sink_is_found(self):
        issued = self.issue(self.sink / "tickets", "sink-only")

        with self.launched_from(self.repo):
            found = cutcheck._run_dir("sink-only", None)

        self.assertEqual(issued, found)
        self.assertTrue(sorted(found.glob("*.md")))

    def test_a_run_living_only_in_a_repositorys_own_state_is_not_found(self):
        """The whole point of the move: a reader that still fell back here
        would keep per-repository run state alive after item 08 copies."""

        self.issue(self.repo / ".orch" / "tickets", "repo-only")
        (self.sink / "tickets").mkdir(parents=True)

        with self.launched_from(self.repo):
            self.assertIsNone(cutcheck._run_dir("repo-only", None))

    def test_the_canary_still_resolves_under_the_repository(self):
        issued = self.issue(
            self.repo / ".orch" / "canary" / "tickets", "canary", source="cutcheck-clean"
        )

        with self.launched_from(self.repo):
            found = cutcheck._run_dir("canary", None)

        # Asserted before it is dereferenced, so a candidate list that stopped
        # offering the canary reads as this case failing, not as a traceback.
        self.assertIsNotNone(found)
        self.assertEqual(issued.resolve(), found.resolve())

    def test_this_repositorys_real_canary_is_still_found(self):
        # The tracked fixture, not a copy: `CanarySetTest` grades it, and it
        # can only do that while this resolves. It lives at the main checkout
        # -- a worktree of this repository has no `.orch/canary/` of its own.
        main = state_root.find_repo_root(ROOT)
        found = cutcheck._run_dir("canary", ROOT)
        self.assertIsNotNone(found)
        self.assertEqual(
            (main / ".orch" / "canary" / "tickets" / "canary").resolve(),
            found.resolve(),
        )
        self.assertTrue(sorted(found.glob("*.md")))

    def test_the_sink_is_preferred_over_a_fixture_set_of_the_same_name(self):
        """Order matters: run state first, then the canary, then fixtures."""

        issued = self.issue(self.sink / "tickets", "cutcheck-clean")

        with self.launched_from(self.repo):
            self.assertEqual(issued, cutcheck._run_dir("cutcheck-clean", ROOT))

    def test_a_sink_resident_run_is_graded_end_to_end(self):
        self.issue(self.sink / "tickets", "sink-clean")
        scratch_root = shared_root()
        out, err = io.StringIO(), io.StringIO()
        with self.launched_from(ROOT):
            with mock.patch.object(
                cutcheck, "_scratch_root", lambda _tree: scratch_root
            ):
                with mock.patch.object(
                    cutcheck, "_remove_scratch_root", lambda _root: None
                ):
                    with contextlib.redirect_stdout(out):
                        with contextlib.redirect_stderr(err):
                            code = cutcheck.main(
                                ["sink-clean", "--baseline", BASELINE]
                            )
        done = subprocess.CompletedProcess(
            ["sink-clean", BASELINE], code, out.getvalue(), err.getvalue()
        )

        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertEqual([], reported(done), done.stdout)

    def test_a_run_nowhere_is_still_the_named_absence(self):
        (self.sink / "tickets").mkdir(parents=True)
        env = dict(os.environ)
        env[state_root.ENV_VAR] = str(self.sink)

        done = subprocess.run(
            [sys.executable, "scripts/cutcheck.py", "no-such-run",
             "--baseline", BASELINE],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(
            cutcheck.NO_TICKET_SET, done.returncode, done.stdout + done.stderr
        )

    # --- criterion 6 ---------------------------------------------------

    def test_no_reader_still_composes_a_repository_state_path(self):
        for relative in READERS:
            with self.subTest(relative):
                self.assertEqual(
                    ALLOWED_STATE_LITERALS[relative],
                    state_literals(relative),
                )

    def test_every_reader_that_resolves_the_sink_reaches_the_one_resolver(self):
        """Item 01's module, by the names its result gives -- and every name
        a reader calls is one the resolver really exports, so a reader and a
        renamed export cannot drift apart silently. `trace.py` is the one
        exception and is asserted as one: it mines transcripts written on
        other machines, where this host's sink path decides nothing, so it
        matches both shapes textually and resolves nothing."""

        called = re.compile(r"state_root\.([a-z_]+)\(")
        for relative in ("scripts/cutcheck.py", "scripts/ui.py",
                         "scripts/isolate.py", "tools/live_sweep_e2e.py"):
            with self.subTest(relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                names = sorted(set(called.findall(source)))
                self.assertTrue(names, relative)
                for name in names:
                    self.assertTrue(
                        callable(getattr(state_root, name, None)),
                        "{0} calls state_root.{1}".format(relative, name),
                    )
        # It may name the owner in a comment -- that is the one-owner law --
        # but it neither imports it nor calls it.
        trace_source = (ROOT / "scripts" / "trace.py").read_text(encoding="utf-8")
        self.assertNotIn("import state_root", trace_source)
        self.assertFalse(called.findall(trace_source))
MUTATING_TICKET = """---
id: 01-mutating
write_scope:
  - scripts/cutcheck.py
---

## Objective

A span the confinement gate permits, writing into the copy all the same.

## Completion test

1. The diff is produced. Oracle: `git diff --output=inside.txt HEAD~1 HEAD`.
2. The revision is read. Oracle: `git log -1 --format=%H`.
"""


class InCopyMutationTest(unittest.TestCase):
    """A span that writes into the shared copy is reported, never obeyed quietly.

    One copy is cloned per invocation and every ticket's oracles are graded in
    it, so a span that writes there changes what a sibling ticket's oracle
    reads. `_names_outside_the_copy` names this hole in its own docstring and
    cannot close it: where a write lands is a fact about the tree, not about
    the token, so only the tree answers it.
    """

    @classmethod
    def setUpClass(cls):
        cls.scratch_root = Path(tempfile.mkdtemp(prefix=".cutcheck-mutation-"))
        cls.tree = cutcheck._scratch_tree(BASELINE, ROOT, cls.scratch_root)

    @classmethod
    def tearDownClass(cls):
        remove_repo_tree(cls.scratch_root)

    def setUp(self):
        if self.tree is None:
            self.skipTest("no scratch tree was built for the baseline")
        cutcheck._EXIT_CACHE.clear()
        self.addCleanup(cutcheck._EXIT_CACHE.clear)
        self.addCleanup(self._restore)

    def _restore(self):
        """Leave the copy as this test found it, and resync the recorded state.

        The copy outlives one test here exactly as it outlives one ticket in a
        run: a test leaving its writes behind would convict the next one.
        """

        for name in ("inside.txt", "probe_dir", ".pytest_cache"):
            path = self.tree / name
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        cutcheck._mutations(self.tree)
        del cutcheck._MUTATED[:]

    def _wrote(self, command):
        """What this span wrote into the copy, as `_run_once` measures it."""

        del cutcheck._MUTATED[:]
        cutcheck._run_once(command, self.tree)
        return sorted(set(cutcheck._MUTATED))

    def _unconfined(self, path):
        findings = cutcheck._check_ticket(path, self.tree, None, {})
        return [f for f in findings if f[2] == cutcheck.UNCONFINED_ORACLE]

    def test_a_permitted_span_that_writes_into_the_copy_is_reported(self):
        ticket = Path(self.scratch_root) / "01-mutating.md"
        ticket.write_text(MUTATING_TICKET, encoding="utf-8")
        self.addCleanup(ticket.unlink)
        findings = self._unconfined(ticket)
        self.assertEqual(len(findings), 1, findings)
        ticket_id, number, _, detail = findings[0]
        self.assertEqual((ticket_id, number), ("01-mutating", 1))
        self.assertIn("inside.txt", detail)

    def test_a_span_writing_nothing_is_not_reported(self):
        # The can-fail direction: the same ticket's second criterion reads the
        # revision and writes nothing, and criterion 1 above proves this
        # assertion is reachable rather than vacuous.
        self.assertEqual(self._wrote("git log -1 --format=%H"), [])

    def test_an_untracked_unignored_directory_in_the_copy_is_reported(self):
        """A directory a span leaves behind, written by git rather than by pytest.

        The shape it stands for is a runner emitting a report directory --
        `python3 -m pytest --junitxml=probe_dir/r.xml ...` was the spelling
        here, and it wrote `probe_dir/` only on a host with pytest installed.
        No CI leg installs anything, so that span wrote nothing on all nine of
        them and this node failed there while passing here. `checkout-index`
        writes an indexed file under a prefix it creates, and needs nothing
        the copy does not already need: the copy is a git clone.
        """

        wrote = self._wrote("git checkout-index --prefix=probe_dir/ LICENSE")
        self.assertIn("probe_dir/", wrote)

    def test_an_ignored_path_is_reported_and_the_bare_spelling_would_miss_it(self):
        """`.pytest_cache/` is the shape found on disk, and it is ignored here.

        The guard against anyone shortening the reading back to a bare `git
        status --porcelain`: that spelling returns nothing with the directory
        sitting in the copy, so it is silently vacuous against the one leak
        that motivated the check.

        The directory is the one pytest leaves; the span that makes it is git,
        for the reason the node above states. The name has to stay an ignored
        one -- an unignored path here would leave both nodes reading the same
        thing, and the bare-spelling assertion below would pass vacuously
        against a status that is empty for no reason at all.
        """

        wrote = self._wrote("git checkout-index --prefix=.pytest_cache/ LICENSE")
        self.assertIn(".pytest_cache/", wrote)
        bare = cutcheck._git(["status", "--porcelain"], self.tree)
        # Anything else standing in this reading is the copy arriving short of
        # the revision, which is a fact about the checkout and not about the
        # spelling. The copy's own path is named because the host that showed
        # this is one nobody here can run: a `D` line under a path length no
        # other entry reaches is the checkout hitting a limit of that host's.
        self.assertEqual(
            bare.stdout,
            "",
            "the bare spelling would have missed it; copy at {} chars: {}".format(
                len(str(self.tree)), self.tree
            ),
        )

    def test_the_next_span_is_not_blamed_for_the_previous_spans_write(self):
        first = self._wrote("git diff --output=inside.txt HEAD~1 HEAD")
        self.assertEqual(first, ["inside.txt"])
        self.assertEqual(self._wrote("git log -1 --format=%H"), [])

    def test_the_clone_primes_its_own_arrival_state_and_reads_clean(self):
        # A checkout an eol rule or a filter left dirty is the copy's arrival
        # state, not the first span's doing.
        self.assertIn(str(self.tree), cutcheck._TREE_STATE)
        self.assertEqual(cutcheck._mutations(self.tree), [])
