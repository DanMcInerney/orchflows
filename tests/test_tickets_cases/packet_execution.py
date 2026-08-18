"""Behavioral ticket regression cases."""

from .packet_workspace import *  # noqa: F401,F403

@unittest.skipUnless(git_available(), "git is not on PATH")
class TestExecutedPacketSeam(unittest.TestCase):
    """The establishment line is not read, it is run: lifted verbatim out of
    the rendered packet, split to argv, executed against the shipped scripts
    in a real linked worktree, and graded by what it did to the repository."""

    def test_the_emitted_line_runs_from_inside_and_check_grades_the_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree, ticket, base = make_isolated_fixture(Path(tmp))
            packet = run_json(worktree, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            (line,) = establishment_lines(packet["prompt"])
            argv = line.split()

            started = run_argv(argv, worktree)
            self.assertEqual(0, started.returncode, started.stderr)
            recorded = json.loads(started.stdout)["start"]
            self.assertEqual(str(main.resolve()), str(Path(recorded["main_root"]).resolve()))
            self.assertTrue(recorded["isolated"])

            front = tickets_mod._parse_frontmatter(ticket.read_text(encoding="utf-8"))
            self.assertEqual("item-branch", front.get("workspace_branch"))
            self.assertEqual(f"{base} clean", front.get("workspace_baseline"))
            # the run tree is the sink's alone
            self.assertFalse((worktree / ".orch").exists())
            self.assertFalse((main / ".orch").exists())

            # `check` reuses every token the packet supplied but the subcommand
            check_argv = [*argv[:2], "check", *argv[3:], "--base", base]
            (worktree / "scratch").mkdir()
            (worktree / "scratch" / "t1.txt").write_text("in scope\n", encoding="utf-8")
            git_run(worktree, "add", "scratch/t1.txt")
            git_run(worktree, "commit", "--quiet", "-m", "in scope")
            clean = run_argv(check_argv, main)
            self.assertEqual(0, clean.returncode, clean.stdout + clean.stderr)
            graded = json.loads(clean.stdout)["check"]
            self.assertEqual("pass", graded["verdict"])
            self.assertEqual("item-branch", graded["workspace_branch"])

            # a deliberate scope breach, committed in the fixture
            (worktree / "secrets.txt").write_text("out of scope\n", encoding="utf-8")
            git_run(worktree, "add", "secrets.txt")
            git_run(worktree, "commit", "--quiet", "-m", "breach")
            breached = run_argv(check_argv, main)
            self.assertEqual(4, breached.returncode, breached.stdout + breached.stderr)
            payload = json.loads(breached.stdout)
            self.assertEqual("scope-breach", payload["verdict"])
            self.assertEqual(["secrets.txt"], payload["breaches"])


@unittest.skipUnless(git_available(), "git is not on PATH")
class TestExecutedRunStateSeam(unittest.TestCase):
    """The same execution against the run-state line every packet carries:
    run from inside the linked tree, the bytes land at the main root."""

    def test_the_emitted_run_state_lines_run_from_inside_the_linked_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree, _, _ = make_isolated_fixture(Path(tmp))
            packet = run_json(worktree, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            note_line, artifact_line = run_state_lines(packet["prompt"])

            note_argv = note_line.split()
            self.assertEqual("TEXT", note_argv[-1])  # the one placeholder
            note_argv[-1] = "seam-note-from-the-linked-tree"
            noted = run_argv(note_argv, worktree)
            self.assertEqual(0, noted.returncode, noted.stderr)
            payload = json.loads(noted.stdout)
            # exit 0 and an error-free payload are one fact, asserted as two
            self.assertNotIn("error", payload)
            self.assertEqual(str(notes_of().resolve()), payload["run_state"]["path"])
            self.assertEqual(
                "seam-note-from-the-linked-tree\n",
                notes_of().read_text(encoding="utf-8"),
            )

            artifact_argv = artifact_line.split()
            self.assertEqual(["NAME", "--text", "TEXT"], artifact_argv[-3:])
            artifact_argv[-3] = "seam-evidence.md"
            artifact_argv[-1] = "seam-bytes-at-the-main-root"
            wrote = run_argv(artifact_argv, worktree)
            self.assertEqual(0, wrote.returncode, wrote.stderr)
            artifact = json.loads(wrote.stdout)
            self.assertNotIn("error", artifact)
            landed = run_dir_of() / "seam-evidence.md"
            self.assertEqual(str(landed.resolve()), artifact["run_state"]["path"])
            self.assertEqual("seam-bytes-at-the-main-root", landed.read_text(encoding="utf-8"))
            self.assertFalse((worktree / ".orch").exists())


# --- run identity -----------------------------------------------------------

GIT_CONFIG = (
    "[core]\n\trepositoryformatversion = 0\n"
    '[remote "{remote}"]\n\turl = {url}\n'
    "\tfetch = +refs/heads/*:refs/remotes/{remote}/*\n"
)
ALPHA = "https://example.invalid/acme/alpha.git"
BETA = "https://example.invalid/other/beta.git"
STAMP_RE = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"


