"""Whether the tree ``start`` stands in is this item's alone.

``start`` used to decide isolation with one line, ``top != root``: true from
any linked worktree at all. Every sibling of a run dispatched into one shared
worktree therefore heard ``isolated: true``, and the field said only that the
caller was not standing in the main checkout. These cases are the third
position that line cannot tell apart from the second -- a caller inside a
linked worktree that another claimed item of the same run already recorded.
"""

from .common import *  # noqa: F401,F403


def restatus(ticket: Path, status: str) -> None:
    """A fixture ticket at some status other than ``make_ticket``'s claimed."""

    ticket.write_text(
        ticket.read_text(encoding="utf-8").replace(
            "status: claimed", f"status: {status}"
        ),
        encoding="utf-8",
    )


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestStartSeesWhoElseRecordedThisTree(unittest.TestCase):
    """Both directions of the isolation claim, from one shared worktree."""

    def _start_in_a_worktree(self, tmp: Path, siblings=()):
        """One repository, one linked worktree, and the siblings named.

        Each sibling is ``(id, branch, status)``: the branch it recorded, so a
        sibling standing in this same tree is one whose ``workspace_branch``
        is ``wt-branch``. The item under start is always ``T-self``.
        """

        main, run_dir = make_repo(tmp)
        for tid, branch, status in siblings:
            stamps = ((workspace.BRANCH_KEY, branch),) if branch else ()
            path = make_ticket(run_dir, tid, extra=stamps)
            if status != "claimed":
                restatus(path, status)
        mine = make_ticket(run_dir, "T-self")
        worktree = add_worktree(main, "wt-branch", tmp / "wt")
        return run_workspace(worktree, "start", "testrun", "T-self"), mine

    def test_a_tree_another_claimed_item_recorded_is_not_isolated(self):
        """The case the shipped line could not see, and the run's reason."""

        with tempfile.TemporaryDirectory() as tmp:
            done, mine = self._start_in_a_worktree(
                Path(tmp), siblings=(("T-sibling", "wt-branch", "claimed"),)
            )

            body = payload_of(done)["start"]
            self.assertFalse(
                body["isolated"],
                "a tree another claimed item of the run recorded is not this "
                "item's alone",
            )
            self.assertEqual(["T-sibling"], body["shared_with"])
            self.assertEqual(
                workspace.EXIT_SHARED_WORKSPACE, done.returncode, done.stdout
            )
            # flagged, not refused: the join still has to be able to read what
            # this item was executed in, so the stamps land before the flag
            self.assertIn(
                "workspace_branch: wt-branch\n", mine.read_text(encoding="utf-8")
            )

    def test_a_tree_no_other_claimed_item_recorded_is_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            done, _ = self._start_in_a_worktree(Path(tmp))

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            body = payload_of(done)["start"]
            self.assertTrue(body["isolated"])
            self.assertEqual([], body["shared_with"])

    def test_a_sibling_on_another_branch_is_not_sharing_this_tree(self):
        """Git checks a branch out in at most one tree, so a different
        recorded branch is a different tree, whatever else it shares."""

        with tempfile.TemporaryDirectory() as tmp:
            done, _ = self._start_in_a_worktree(
                Path(tmp), siblings=(("T-elsewhere", "other-branch", "claimed"),)
            )

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertTrue(payload_of(done)["start"]["isolated"])

    def test_a_sibling_that_recorded_nothing_is_not_sharing_this_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            done, _ = self._start_in_a_worktree(
                Path(tmp), siblings=(("T-unstarted", None, "claimed"),)
            )

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertTrue(payload_of(done)["start"]["isolated"])

    def test_a_sibling_no_longer_claimed_has_left_the_tree(self):
        """A finished item is not a live sharer. Were every terminal sibling
        counted, a long run's last item would be flagged for the trees its
        predecessors have already left, and the flag would mean nothing."""

        with tempfile.TemporaryDirectory() as tmp:
            done, _ = self._start_in_a_worktree(
                Path(tmp), siblings=(("T-finished", "wt-branch", "complete"),)
            )

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertTrue(payload_of(done)["start"]["isolated"])

    def test_every_claimed_sharer_is_named_not_only_the_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            done, _ = self._start_in_a_worktree(
                Path(tmp),
                siblings=(
                    ("T-b", "wt-branch", "claimed"),
                    ("T-a", "wt-branch", "claimed"),
                    ("T-away", "other-branch", "claimed"),
                ),
            )

            self.assertEqual(
                workspace.EXIT_SHARED_WORKSPACE, done.returncode, done.stdout
            )
            self.assertEqual(["T-a", "T-b"], payload_of(done)["start"]["shared_with"])

    def test_two_detached_workspaces_at_one_revision_are_not_sharing_a_tree(self):
        """The limit of the branch proxy, pinned as a limit.

        A branch identifies a tree because git checks it out in at most one.
        A detached record identifies no tree at all: it names the revision
        ``start`` read, and two workspaces materialized at the same revision
        record the identical string while standing in different directories --
        the same ambiguity ``_detached_tip`` already refuses to resolve. So
        equality of two detached records is not evidence of sharing, and
        reading it as evidence flags two genuinely isolated workspaces.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            payloads = []
            for tid in ("T-first", "T-second"):
                make_ticket(run_dir, tid)
                worktree = tmp / f"wt-{tid}"
                git(main, "worktree", "add", "--quiet", "--detach", str(worktree), "HEAD")
                done = run_workspace(worktree, "start", "testrun", tid)
                self.assertEqual(0, done.returncode, done.stdout + done.stderr)
                payloads.append(payload_of(done)["start"])

            # both recorded the same detached identity, and both are isolated
            self.assertEqual(
                payloads[0][workspace.BRANCH_KEY], payloads[1][workspace.BRANCH_KEY]
            )
            for body in payloads:
                self.assertTrue(body["isolated"], body)
                self.assertEqual([], body["shared_with"])

    def test_two_claimed_items_in_one_shared_detached_worktree_are_flagged(self):
        """The other side of that limit, which is not a limit.

        A detached record is ambiguous only where more than one worktree could
        have written it. One shared detached tree is this run's own situation
        with the branch left off -- two claimed items standing in one
        directory -- and git names that directory outright: a single standing
        detached worktree at or past the recorded revision is the only place
        the record can have come from. Going silent here reports `isolated`
        for the very shape `isolated` was made to see.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            shared = tmp / "wt-shared"
            git(main, "worktree", "add", "--quiet", "--detach", str(shared), "HEAD")
            for tid in ("T-first", "T-second"):
                make_ticket(run_dir, tid)
            first = run_workspace(shared, "start", "testrun", "T-first")
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)

            done = run_workspace(shared, "start", "testrun", "T-second")

            body = payload_of(done)["start"]
            self.assertFalse(
                body["isolated"],
                "a claimed sibling recorded this very directory; a detached "
                "HEAD does not make the tree this item's alone",
            )
            self.assertEqual(["T-first"], body["shared_with"])
            self.assertEqual(
                workspace.EXIT_SHARED_WORKSPACE, done.returncode, done.stdout
            )

    def test_starting_the_same_item_twice_never_flags_it_against_itself(self):
        """``start`` records this item's own branch, so the second run reads a
        sink already carrying it. The item's own id is skipped, or every
        re-established workspace would report itself as its own sharer."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T-self")
            worktree = add_worktree(main, "wt-branch", tmp / "wt")

            first = run_workspace(worktree, "start", "testrun", "T-self")
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            again = run_workspace(worktree, "start", "testrun", "T-self")

            self.assertEqual(0, again.returncode, again.stdout + again.stderr)
            self.assertTrue(payload_of(again)["start"]["isolated"])

    def test_the_main_checkout_stays_unisolated_and_still_exits_zero(self):
        """The second position, unchanged. ``isolated`` is a conjunction now,
        and the main checkout fails the first half of it for the reason it
        always did -- standing where the repository is checked out, which is
        not news and must not earn the new code by itself."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T-self")

            done = run_workspace(main, "start", "testrun", "T-self")

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertFalse(payload_of(done)["start"]["isolated"])

    def test_the_main_checkout_that_shares_is_flagged_like_any_other(self):
        """The pair to the case above, and what tells the two apart.

        ``isolated`` is false in the main checkout either way, so nothing in
        that field distinguishes standing where the repository is checked out
        from standing where a claimed sibling is also working. Only the code
        and ``shared_with`` can, which is why the flag is decided on the
        sharing alone and not under the linked-tree half of the conjunction.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            here = git(main, "rev-parse", "--abbrev-ref", "HEAD").strip()
            make_ticket(run_dir, "T-sibling", extra=((workspace.BRANCH_KEY, here),))
            make_ticket(run_dir, "T-self")

            done = run_workspace(main, "start", "testrun", "T-self")

            body = payload_of(done)["start"]
            self.assertFalse(body["isolated"])
            self.assertEqual(["T-sibling"], body["shared_with"])
            self.assertEqual(
                workspace.EXIT_SHARED_WORKSPACE, done.returncode, done.stdout
            )


class TestTheSharedTreeCodeIsItsOwnAndDocumented(unittest.TestCase):
    """Exit codes are this script's public verdicts. A new failure mode that
    reused 1, or 2, would be read by an integrator as the meaning that code
    already carries."""

    def test_the_code_collides_with_no_existing_meaning(self):
        existing = {
            workspace.EXIT_OK, workspace.EXIT_ERROR,
            workspace.EXIT_ISOLATION_MISSING, workspace.EXIT_WRONG_BRANCH_POINT,
            workspace.EXIT_SCOPE_BREACH, workspace.EXIT_NO_RECORD,
            workspace.EXIT_WRONG_VANTAGE,
        }
        self.assertEqual({0, 1, 2, 3, 4, 5, 6}, existing, "an existing code moved")
        self.assertNotIn(workspace.EXIT_SHARED_WORKSPACE, existing)
        self.assertIn(workspace.EXIT_SHARED_WORKSPACE, workspace.VERDICTS)

    def test_the_docstring_exit_code_table_carries_the_new_code(self):
        """The table a caller reads to learn what a code means. ``--help``
        prints from ``VERDICTS``; this is the prose row beside it."""

        docstring = ast.get_docstring(ast.parse(WORKSPACE_PY.read_text(encoding="utf-8")))
        table = (docstring or "").partition("Exit codes:")[2]
        self.assertIn(str(workspace.EXIT_SHARED_WORKSPACE), table)
        self.assertIn(workspace.VERDICTS[workspace.EXIT_SHARED_WORKSPACE], table)
