"""Detached integration stays in its recorded checkout while HEAD advances."""
from .common import *  # noqa: F401,F403
from .integration_cases import baseline_of
from scripts import tickets_store, workspace_return


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestDetachedIntegrationContinuity(unittest.TestCase):
    def fixture(self, tmp):
        main, run_dir = make_repo(tmp)
        old = git(main, "rev-parse", "HEAD").strip()
        anchor = commit_in(main, {"README.md": "anchor\n"}, "anchor")
        destination = tmp / "destination"
        git(main, "worktree", "add", "--quiet", "--detach", str(destination), anchor)
        candidates = []
        for tid in ("T1", "T2"):
            ticket = make_ticket(run_dir, tid)
            result = run_workspace(tmp, "establish", "testrun", tid, "--repo", str(destination))
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            candidate = state_root.candidate_paths("testrun", tid)
            commit_in(candidate["path"], {f"scratch/{tid}.txt": tid}, tid)
            candidates.append((tid, candidate, baseline_of(ticket)))
        return main, destination, old, anchor, candidates

    def integrate(self, item):
        tid, candidate, baseline = item
        return workspace_return.integrate("testrun", tid, candidate["path"], candidate["branch"], baseline)

    def test_two_sequential_merges_and_replay_keep_the_exact_detached_checkout(self):
        with tempfile.TemporaryDirectory() as folder:
            main, destination, old, anchor, candidates = self.fixture(Path(folder))
            recorded = tickets_store.integration_target("testrun")
            other = Path(folder) / "other"
            git(main, "worktree", "add", "--quiet", "--detach", str(other), anchor)
            for item in candidates:
                body, code = self.integrate(item)
                self.assertEqual((0, "merged"), (code, body["integrate"]["outcome"]))
                self.assertEqual(str(destination.resolve()), body["integrate"]["main_root"])
            body, code = self.integrate(candidates[1])
            self.assertEqual((0, "replayed"), (code, body["integrate"]["outcome"]))
            self.assertEqual(recorded, tickets_store.integration_target("testrun"))
            self.assertEqual(anchor, git(other, "rev-parse", "HEAD").strip())
            self.assertEqual(anchor, git(main, "rev-parse", "HEAD").strip())
            for tid in ("T1", "T2"):
                self.assertEqual(tid, (destination / "scratch" / f"{tid}.txt").read_text())

    def test_rewind_divergence_and_named_branch_changes_refuse_without_merging(self):
        with tempfile.TemporaryDirectory() as folder:
            main, destination, old, anchor, candidates = self.fixture(Path(folder))
            git(destination, "checkout", "--quiet", "--detach", old)
            divergent = commit_in(destination, {"divergent.txt": "side\n"}, "divergent")
            for revision in (old, divergent):
                with self.subTest(revision=revision):
                    git(destination, "checkout", "--quiet", "--detach", revision)
                    with self.assertRaises(workspace_return.Refused):
                        self.integrate(candidates[0])
                    self.assertEqual(revision, git(destination, "rev-parse", "HEAD").strip())
            git(destination, "checkout", "--quiet", "-b", "different", anchor)
            with self.assertRaises(workspace_return.Refused):
                self.integrate(candidates[0])
            self.assertEqual(anchor, git(destination, "rev-parse", "HEAD").strip())

    def test_missing_recorded_checkout_never_redirects_to_another_detached_tree(self):
        with tempfile.TemporaryDirectory() as folder:
            main, destination, old, anchor, candidates = self.fixture(Path(folder))
            other = Path(folder) / "other"
            git(main, "worktree", "add", "--quiet", "--detach", str(other), anchor)
            git(main, "worktree", "remove", str(destination))
            with self.assertRaises(workspace_return.Refused):
                self.integrate(candidates[0])
            self.assertEqual(anchor, git(other, "rev-parse", "HEAD").strip())
