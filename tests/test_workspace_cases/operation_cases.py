"""Workspace join enforcement of a v1 ticket's declared operations."""

from .common import *  # noqa: F401,F403


def operation_fixture(tmp, ticket_id, mutations, *, v1=True, include_plan=True,
                      status="claimed"):
    main, run_dir = make_repo(tmp)
    commit_in(main, {
        "scratch/change.txt": "before\n",
        "scratch/delete.txt": "remove\n",
    }, "operation baseline")
    base = git(main, "rev-parse", "HEAD").strip()
    tree = add_worktree(main, f"{ticket_id}-branch", tmp / f"{ticket_id}-tree")
    commit_in(tree, {
        "scratch/create.txt": "created\n",
        "scratch/change.txt": "after\n",
    }, "create and change")
    (tree / "scratch" / "delete.txt").unlink()
    git(tree, "add", "-A")
    git(tree, "commit", "--quiet", "-m", "delete")
    extra = [
        (workspace.ISOLATION_KEY, "required"),
        (workspace.BRANCH_KEY, f"{ticket_id}-branch"),
    ]
    if v1:
        extra.append(("admission", "v1:pending"))
        if include_plan:
            extra.append(("mutations", f"[{', '.join(mutations)}]"))
    path = make_ticket(run_dir, ticket_id, scope=("scratch",), extra=extra)
    if status != "claimed":
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("status: claimed", f"status: {status}", 1), encoding="utf-8")
    return main, base


@unittest.skipUnless(git_available(), "git is required for operation grading")
class TestJoinGradesActualOperations(unittest.TestCase):
    def test_exact_create_change_and_delete_plan_passes(self):
        with tempfile.TemporaryDirectory() as raw:
            main, base = operation_fixture(
                Path(raw), "T-operations",
                (
                    "create:scratch/create.txt",
                    "change:scratch/change.txt",
                    "delete:scratch/delete.txt",
                ),
            )
            done = run_workspace(main, "check", "testrun", "T-operations", "--base", base)
            self.assertEqual(0, done.returncode, done.stdout)
            self.assertEqual(
                [
                    "change:scratch/change.txt",
                    "create:scratch/create.txt",
                    "delete:scratch/delete.txt",
                ],
                payload_of(done)["check"]["mutations"],
            )

    def test_operation_mismatch_refuses_even_when_the_path_is_authorized(self):
        with tempfile.TemporaryDirectory() as raw:
            main, base = operation_fixture(
                Path(raw), "T-mismatch",
                (
                    "change:scratch/create.txt",
                    "change:scratch/change.txt",
                    "delete:scratch/delete.txt",
                ),
            )
            done = run_workspace(main, "check", "testrun", "T-mismatch", "--base", base)
            self.assertEqual(workspace.EXIT_SCOPE_BREACH, done.returncode, done.stdout)
            body = payload_of(done)
            self.assertEqual(["create:scratch/create.txt"], body["operation_breaches"])
            self.assertEqual(["scratch/create.txt"], body["breaches"])

    def test_write_prefix_covers_every_actual_operation_below_it(self):
        with tempfile.TemporaryDirectory() as raw:
            main, base = operation_fixture(Path(raw), "T-prefix", ("write:scratch/",))
            done = run_workspace(main, "check", "testrun", "T-prefix", "--base", base)
            self.assertEqual(0, done.returncode, done.stdout)

    def test_still_present_isolated_worktree_must_have_no_dirty_oracle_bytes(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            main, base = operation_fixture(tmp, "T-dirty", ("write:scratch/",))
            tree = tmp / "T-dirty-tree"
            (tree / "scratch" / "change.txt").write_text("dirty oracle influence\n", encoding="utf-8")
            done = run_workspace(main, "check", "testrun", "T-dirty", "--base", base)
            self.assertEqual(workspace.EXIT_SCOPE_BREACH, done.returncode, done.stdout)
            self.assertEqual(["scratch/change.txt"], payload_of(done)["dirty"])

    def test_v0_ticket_keeps_path_only_join_grading(self):
        with tempfile.TemporaryDirectory() as raw:
            main, base = operation_fixture(Path(raw), "T-v0", (), v1=False)
            done = run_workspace(main, "check", "testrun", "T-v0", "--base", base)
            self.assertEqual(0, done.returncode, done.stdout)
            self.assertNotIn("operation_breaches", payload_of(done)["check"])

    def test_historical_claimed_and_terminal_v1_tickets_keep_path_only_grants(self):
        for status in ("claimed", "complete"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as raw:
                ticket_id = f"T-historical-{status}"
                main, base = operation_fixture(
                    Path(raw), ticket_id, (), include_plan=False, status=status,
                )
                done = run_workspace(main, "check", "testrun", ticket_id, "--base", base)
                self.assertEqual(0, done.returncode, done.stdout)
                self.assertEqual("pass", payload_of(done)["check"]["verdict"])

    def test_pending_or_ready_v1_ticket_without_a_plan_is_not_grandfathered(self):
        for status in ("pending", "ready"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as raw:
                ticket_id = f"T-unclaimed-{status}"
                main, base = operation_fixture(
                    Path(raw), ticket_id, (), include_plan=False, status=status,
                )
                done = run_workspace(main, "check", "testrun", ticket_id, "--base", base)
                self.assertEqual(workspace.EXIT_SCOPE_BREACH, done.returncode, done.stdout)
                self.assertEqual(3, len(payload_of(done)["operation_breaches"]))
