"""Workspace join enforcement of a ticket's declared operations."""

from .common import *  # noqa: F401,F403


def operation_fixture(tmp, ticket_id, mutations, *, include_plan=True,
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
    if include_plan:
        extra.append(("mutations", f"[{', '.join(mutations)}]"))
    else:
        extra.append(("mutations", "[]"))
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
