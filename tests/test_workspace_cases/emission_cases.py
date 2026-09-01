"""The baseline stamp is written once, and oracle-emitted bytecode is
emission rather than a scope breach.

Both behaviors are the mechanical arm of one law in ``rules/verification.md``:
an identity or cleanliness assertion that never says which bytes it means
passes or fails by host accident.
"""

from .common import *  # noqa: F401,F403


def _isolated(tmp: Path):
    """A repository whose ``wt-branch`` is one commit ahead in its own tree.

    Built inline rather than taken from ``graded_repository``: every case
    here dirties a working tree or moves a branch, which that shared
    fixture forbids.
    """

    main, run_dir = make_repo(tmp)
    base = git(main, "rev-parse", "HEAD").strip()
    worktree = add_worktree(main, "wt-branch", tmp / "wt")
    commit_in(worktree, {"scratch/a.txt": "one\n"}, "item work")
    # the caller moves on, so the item's tip is not an ancestor of HEAD and
    # the grade reaches the cleanliness check rather than stopping short
    commit_in(main, {"README.md": "advanced\n"}, "caller moves on")
    return main, run_dir, base, worktree


def _graded_check(main: Path, base: str, tid: str = "T1"):
    return run_workspace(main, "check", "testrun", tid, "--base", base)


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestBaselineIsWrittenOnce(unittest.TestCase):
    """``workspace_baseline`` names the revision the item was cut from.

    ``scripts/tickets_packet.py`` feeds that field to ``cutcheck.py
    --baseline``, so whatever rewrites it decides what a later cut check
    compares against. ``start`` used to stamp whatever tree it happened to
    observe: a second executor turn, or the establishment step a read-only
    verifier is itself required to run, overwrote the record with a moved --
    and in the observed instance a dirty -- tree, on a unit that had already
    completed. The observation is still reported, under its own key, because
    suppressing it would trade one silent rewrite for one silent discard.
    """

    def test_re_establishment_preserves_the_stamp_and_reports_what_it_saw(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir, _base, worktree = _isolated(tmp)
            ticket = make_ticket(run_dir, "T1")
            first_head = git(worktree, "rev-parse", "HEAD").strip()

            self.assertEqual(0, run_workspace(worktree, "start", "testrun", "T1").returncode)
            self.assertIn(f"workspace_baseline: {first_head} clean\n",
                          ticket.read_text(encoding="utf-8"))

            moved = commit_in(worktree, {"scratch/b.txt": "two\n"}, "second turn")
            (worktree / "scratch" / "loose.txt").write_text("loose\n", encoding="utf-8")
            again = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, again.returncode, again.stderr)
            after = ticket.read_text(encoding="utf-8")
            self.assertIn(f"workspace_baseline: {first_head} clean\n", after)
            self.assertNotIn(moved, after)
            body = payload_of(again)["start"]
            self.assertEqual(f"{first_head} clean", body["workspace_baseline"])
            # recorded distinctly: the key is absent on a first establishment,
            # so its presence alone says this call re-established
            self.assertEqual(f"{moved} dirty: scratch/loose.txt", body["reestablished"])

    def test_a_first_establishment_still_records_what_it_observed(self):
        """The write-once guard must not turn ``start`` into a no-op: with no
        prior stamp the observed tree is the record, and no re-establishment
        is claimed."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir, _base, worktree = _isolated(tmp)
            ticket = make_ticket(run_dir, "T1")
            head = git(worktree, "rev-parse", "HEAD").strip()

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            self.assertIn(f"workspace_baseline: {head} clean\n",
                          ticket.read_text(encoding="utf-8"))
            self.assertNotIn("reestablished", payload_of(done)["start"])

    def test_an_empty_stamp_is_no_stamp(self):
        """A key present with no value has recorded nothing. Reading it as a
        record would leave the item permanently unstamped -- the failure the
        write-once guard is most likely to introduce."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir, _base, worktree = _isolated(tmp)
            ticket = make_ticket(run_dir, "T1", extra=((workspace.BASELINE_KEY, ""),))
            head = git(worktree, "rev-parse", "HEAD").strip()

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            self.assertEqual(f"{head} clean", payload_of(done)["start"]["workspace_baseline"])


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestBytecodeIsEmissionNotBreach(unittest.TestCase):
    """An acceptance oracle imports the tree it grades, and CPython writes
    bytecode beside what it imports. A cleanliness check that reads those
    bytes as uncommitted work fails the item for having been verified --
    observed against a frozen baseline that tracked the bytecode itself, so
    the classification cannot key on tracked-versus-untracked and has to key
    on the path's shape.
    """

    def _ticket(self, run_dir, tid, **kwargs):
        return make_ticket(
            run_dir, tid, scope=("scratch",),
            extra=((workspace.ISOLATION_KEY, "required"),
                   (workspace.BRANCH_KEY, "wt-branch")),
            **kwargs,
        )

    def test_untracked_bytecode_does_not_fail_the_grade(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir, base, worktree = _isolated(tmp)
            self._ticket(run_dir, "T1")
            cache = worktree / "scratch" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "a.cpython-313.pyc").write_bytes(b"\x00\x01")

            done = _graded_check(main, base)

            body = payload_of(done)
            self.assertEqual(0, done.returncode, f"{done.stdout}{done.stderr}")
            self.assertEqual("pass", body["check"]["verdict"])
            # Membership, not existence: a truthy check passes just as well on
            # a report that named the wrong path or swept in a real breach.
            # The value pins git's own granularity too -- a wholly untracked
            # directory is one porcelain entry, so the report names the
            # directory and not the bytes inside it.
            self.assertEqual(["scratch/__pycache__/"], body["check"]["emission"],
                             "the emitted bytes were classified but not reported")

    def test_the_reserved_notes_directory_is_emission(self):
        """The launch prompt hands every child ``.orch-notes/`` for the note
        files its filing and closing commands read. Before it was reserved,
        each worker improvised its own note names in the workspace root, and
        the leftovers graded as uncommitted work."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir, base, worktree = _isolated(tmp)
            self._ticket(run_dir, "T1")
            notes = worktree / workspace_git.NOTES_DIR
            notes.mkdir()
            (notes / "outcome.md").write_text("closing note\n", encoding="utf-8")

            done = _graded_check(main, base)

            body = payload_of(done)
            self.assertEqual(0, done.returncode, f"{done.stdout}{done.stderr}")
            self.assertEqual("pass", body["check"]["verdict"])
            self.assertEqual([workspace_git.NOTES_DIR + "/"],
                             body["check"]["emission"])

    def test_bytecode_outside_a_pycache_directory_is_still_emission(self):
        """Carrier census: every other case here is caught by the
        ``__pycache__`` segment *and* by the extension, so deleting the
        extension arm survives all of them and the arm reads as dead. It is
        not: ``compileall -b`` and legacy layouts write ``a.pyc`` beside
        ``a.py`` with no cache directory at all, and only this case fails
        when that arm is dropped."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir, base, worktree = _isolated(tmp)
            self._ticket(run_dir, "T1")
            (worktree / "scratch" / "a.pyc").write_bytes(b"\x00\x01")

            done = _graded_check(main, base)

            body = payload_of(done)
            self.assertEqual(0, done.returncode, f"{done.stdout}{done.stderr}")
            self.assertEqual("pass", body["check"]["verdict"])
            self.assertEqual(["scratch/a.pyc"], body["check"]["emission"])

    def test_bytecode_the_baseline_itself_tracks_is_still_emission(self):
        """The wild instance: the pinned verifier failed on bytecode the
        frozen baseline tracks, which an untracked-only rule cannot see."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir, base, worktree = _isolated(tmp)
            self._ticket(run_dir, "T1")
            commit_in(
                worktree,
                {"scratch/__pycache__/a.cpython-313.pyc": "stale\n"},
                "baseline tracks bytecode",
            )
            (worktree / "scratch" / "__pycache__" / "a.cpython-313.pyc").write_text(
                "rebuilt by the oracle\n", encoding="utf-8")

            done = _graded_check(main, base)

            self.assertEqual(0, done.returncode, f"{done.stdout}{done.stderr}")
            self.assertEqual("pass", payload_of(done)["check"]["verdict"])


    def test_bytecode_beside_real_dirt_leaves_only_the_dirt_in_the_refusal(self):
        """Membership, not existence: a refusal that still names the emitted
        bytes sends the item back to clean what its own verification wrote."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir, base, worktree = _isolated(tmp)
            self._ticket(run_dir, "T1")
            cache = worktree / "scratch" / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "a.cpython-313.pyc").write_bytes(b"\x00\x01")
            (worktree / "scratch" / "loose.txt").write_text("loose\n", encoding="utf-8")

            done = _graded_check(main, base)

            self.assertEqual(4, done.returncode, f"{done.stdout}{done.stderr}")
            body = payload_of(done)
            self.assertEqual(["scratch/loose.txt"], body["dirty"])
            self.assertNotIn("__pycache__", body["error"])
