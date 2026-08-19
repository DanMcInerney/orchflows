"""Behavioral ticket regression cases."""

from .packet_workspace import *  # noqa: F401,F403

RUNTIME_CLAIMED_TICKET = ISOLATED_TICKET.replace(
    "status: ready", "status: claimed\nclaimed_by: agent-a"
)
RUNTIME_ROOT_TICKET = (
    FULL_TICKET.replace("id: T1", "id: R1")
    .replace("executor: orch-tdd", "executor: orch-decompose")
    .replace("status: ready", "status: claimed\nclaimed_by: cutter-a")
)


class RuntimeInterpreterBoundaryTests(unittest.TestCase):
    """Built-ins stay in their runtime while caller environment stays local."""

    def test_internal_builtin_commands_use_the_current_interpreter(self):
        runtime = "ORCHFLOWS_RUNTIME_INTERPRETER"
        prompts = []
        with mock.patch.object(tickets_mod._tickets_packet_module.sys, "executable", runtime):
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                make_packet_repo(tmp, RUNTIME_CLAIMED_TICKET)
                for extra in ((), ("--executor", "orch-critique")):
                    prompts.append(
                        run_cmd(
                            tmp, "packet", "testrun", "T1", "--reply-to", "main", *extra
                        )["packet"]["prompt"]
                    )
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                path = make_packet_repo(tmp, RUNTIME_ROOT_TICKET, tid="R1")
                make_tickets(path.parent, {"R1.01": ("pending", "[]")})
                for executor in ("orch-critique", "orch-verify"):
                    prompts.append(
                        run_cmd(
                            tmp,
                            "packet",
                            "testrun",
                            "R1",
                            "--reply-to",
                            "main",
                            "--executor",
                            executor,
                        )["packet"]["prompt"]
                    )

        builtins = {"cutcheck.py", "tickets.py", "workspace.py"}
        rendered = []
        for prompt in prompts:
            for line in prompt.splitlines():
                tokens = line.split()
                if len(tokens) > 1 and Path(tokens[1]).name in builtins:
                    rendered.append(tokens)
        self.assertEqual(builtins, {Path(tokens[1]).name for tokens in rendered})
        for tokens in rendered:
            self.assertEqual(runtime, tokens[0], tokens)

    def test_ticket_commands_inherit_the_caller_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "caller state"
            caller = {
                STATE_HOME_ENV_VAR: str(sink),
                "VIRTUAL_ENV": str(Path(tmp) / "project venv"),
            }
            with mock.patch.dict(os.environ, caller, clear=False):
                completed = run_full(ROOT, "run-state", "inheritance", "--note", "from caller")
            self.assertEqual(0, completed.returncode, completed.stderr)
            payload = json.loads(completed.stdout)
            notes = sink / "runs" / "inheritance" / "notes.md"
            self.assertEqual(str(notes), payload["run_state"]["path"])
            self.assertEqual("from caller\n", notes.read_text(encoding="utf-8"))

    def test_rendered_builtin_command_executes_from_a_spaced_install_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, RUNTIME_CLAIMED_TICKET)
            installed = tmp / "installed bin with spaces"
            installed.mkdir()
            source = TICKETS_PY.parent
            names = {"state_root.py", "cutcheck.py"}
            names.update(path.name for path in source.glob("tickets*.py"))
            names.update(path.name for path in source.glob("workspace*.py"))
            for name in names:
                (installed / name).write_text(
                    (source / name).read_text(encoding="utf-8"), encoding="utf-8"
                )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(installed / "tickets.py"),
                    "packet",
                    "testrun",
                    "T1",
                    "--reply-to",
                    "main",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(tmp),
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            prompt = json.loads(completed.stdout)["packet"]["prompt"]
            command = next(
                line
                for line in prompt.splitlines()
                if "run-state" in line and "--note" in line
            ).replace("TEXT", "spaced-ok")
            if os.name == "nt":
                invoked = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", command],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=str(tmp),
                )
            else:
                invoked = subprocess.run(
                    ["/bin/sh", "-c", command],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=str(tmp),
                )
            self.assertEqual(0, invoked.returncode, invoked.stderr)
            self.assertEqual(
                "spaced-ok\n",
                (sink_root() / "runs" / "testrun" / "notes.md").read_text(
                    encoding="utf-8"
                ),
            )

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
