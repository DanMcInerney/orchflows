"""Behavioral ticket regression cases."""

from .run_state_terminal import *  # noqa: F401,F403

class TestRunStateRootResolution(unittest.TestCase):
    def test_the_root_comes_from_the_one_resolver_with_no_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            calls = []
            original = tickets_mod.state_root.runs_root

            def spy():
                calls.append(True)
                return original()

            cwd = os.getcwd()
            tickets_mod.state_root.runs_root = spy
            try:
                os.chdir(worktree)
                payload = tickets_mod._dispatch(
                    ["run-state", "testrun", "--note", "resolved in process"]
                )
            finally:
                os.chdir(cwd)
                tickets_mod.state_root.runs_root = original
            self.assertIn("run_state", payload)
            self.assertEqual(1, len(calls))
            self.assertEqual(
                "resolved in process\n", notes_of().read_text(encoding="utf-8")
            )
            # The state-root read still stays in process (the spy above is
            # the mechanism oracle). The lower identity producer/resolver may
            # probe Git for immutable ticket inputs, so it owns subprocess.
            imported = set()
            for path in TICKETS_MODULES:
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                    if isinstance(node, ast.Import):
                        imported.update(alias.name.split(".")[0] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and not node.level:
                        imported.add((node.module or "").split(".")[0])
            # `tempfile` is here for `run.json`: the identity document is
            # written beside itself and moved over, so a concurrent reader
            # never meets a half-written one. It opens no process either.
            self.assertNotIn("os", imported)
            # msvcrt is absent on POSIX and imported under try/except for the
            # one lock _append_one_line takes; it reaches no subprocess.
            # `time` is the retry budget `_replace_atomically` waits out a
            # Windows refusal against, and it too starts nothing.
            # `TICKETS_MODULES` is the discovered family — `scripts/tickets.py`
            # plus `scripts/tickets_*.py`, globbed at call time — so the side
            # being censused never ages. The expected set below is kept BY HAND
            # and does age: a new sibling module, or a new import inside any
            # existing one, lands here as a failure naming the token to add.
            # That failure is the point; do not widen this to a subset check.
            self.assertEqual(
                {"__future__", "collections", "contextlib", "datetime", "fcntl",
                 "fnmatch", "hashlib",
                 "importlib", "json",
                 "msvcrt", "pathlib", "re", "scripts", "shlex", "state_root", "sys",
                 "subprocess", "tempfile", "time", "tickets_format", "tickets_markdown", "tickets_store",
                 "tickets_commands", "tickets_lint",
                 "tickets_issue", "tickets_lifecycle", "tickets_packet",
                 "tickets_result", "tickets_worklog", "tickets_dispatch",
                 "tickets_gate_mutations", "tickets_admission", "tickets_inputs",
                 "tickets_input_producers", "tickets_context", "tickets_scope",
                 "tickets_transitions", "tickets"},
                imported,
            )

    @unittest.skipUnless(git_available(), "git is not on PATH")
    def test_inside_a_real_git_worktree_the_bytes_land_in_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree = make_real_worktree(Path(tmp))
            payload = run_json(worktree, "run-state", "testrun", "--note", "from a real worktree")
            self.assertEqual(
                str(notes_of().resolve()), payload["run_state"]["path"]
            )
            self.assertEqual(
                "from a real worktree\n", notes_of().read_text(encoding="utf-8")
            )
            self.assertFalse((worktree / ".orch").exists())
            self.assertFalse((main / ".orch").exists())


class TestRunStateRefusesUnsafeNames(unittest.TestCase):
    """A run id or artifact name is one path segment. Anything that could
    climb out of the sink's `runs/` is refused by name, never sanitized
    silently."""

    def test_an_unsafe_run_id_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for bad in ("../escape", "a/b", "a\\b", ".."):
                payload = run_cmd(worktree, "run-state", bad, "--note", "x")
                self.assertIn(bad, payload.get("error", ""), bad)
                self.assertNotIn("run_state", payload)
            self.assertFalse((sink_root() / "runs").exists())

    def test_an_unsafe_artifact_name_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for bad in ("../escape.md", "a/b.md", "a\\b.md", ".."):
                payload = run_cmd(
                    worktree, "run-state", "testrun", "--artifact", bad, "--text", "x"
                )
                self.assertIn(bad, payload.get("error", ""), bad)
                self.assertNotIn("run_state", payload)
            self.assertFalse((sink_root() / "runs").exists())


class TestPacketCarriesTheRunStateCommand(unittest.TestCase):
    """Every dispatched child gets the channel in its own packet: no sibling
    reads another ticket to learn how to write run state."""

    def make(self, tmp: Path) -> Path:
        (tmp / ".git").mkdir()
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        path = run_dir / "T1.md"
        path.write_text(FULL_TICKET, encoding="utf-8")
        return path

    def test_every_packet_carries_it_workspace_or_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            bare = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            with_ws = run_cmd(
                tmp, "packet", "testrun", "T1", "--reply-to", "main", "--workspace", "/wt/a"
            )["packet"]
            for packet in (bare, with_ws):
                lines = run_state_lines(packet["prompt"])
                self.assertEqual(2, len(lines), packet["prompt"])
                for line in lines:
                    # `run` is interpolated from the ticket, not left a placeholder
                    self.assertIn(" run-state testrun ", line)

    def test_the_line_is_absolute_one_token_per_argument_and_shell_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            note_line, artifact_line = run_state_lines(packet["prompt"])
            for line in (note_line, artifact_line):
                for forbidden in ("|", ">", "<", "&&", "$("):
                    self.assertNotIn(forbidden, line, line)
                tokens = line.split()
                self.assertEqual(sys.executable, tokens[0])
                self.assertTrue(Path(tokens[0]).is_absolute(), tokens[0])
                self.assertEqual(str(TICKETS_PY.resolve()), tokens[1])
                self.assertTrue(Path(tokens[1]).is_absolute(), tokens[1])
                self.assertEqual("tickets.py", Path(tokens[1]).name)
                self.assertEqual(["run-state", "testrun"], tokens[2:4])
            self.assertEqual(["--note", "TEXT"], note_line.split()[4:])
            self.assertEqual(
                ["--artifact", "NAME", "--text", "TEXT"], artifact_line.split()[4:]
            )

    def test_the_interpreter_and_script_path_are_derived_not_literal(self):
        """Run a copy of the script from somewhere else entirely: a literal
        `python3 scripts/tickets.py` would emit the same line from both."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            elsewhere = tmp / "elsewhere"
            elsewhere.mkdir()
            copy = elsewhere / "tickets.py"
            copy.write_text(TICKETS_PY.read_text(encoding="utf-8"), encoding="utf-8")
            for name in TICKETS_SUPPORT_NAMES:
                (elsewhere / name).write_text(
                    (TICKETS_PY.parent / name).read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            # the installed layout: the resolver sits flat beside it, and the
            # copy reaches it by the second arm of its two-arm import
            (elsewhere / "state_root.py").write_text(
                STATE_ROOT_PY.read_text(encoding="utf-8"), encoding="utf-8"
            )
            completed = subprocess.run(
                [sys.executable, str(copy), "packet", "testrun", "T1", "--reply-to", "main"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", cwd=str(tmp),
            )
            packet = json.loads(completed.stdout)["packet"]
            lines = run_state_lines(packet["prompt"])
            self.assertEqual(2, len(lines))
            for line in lines:
                self.assertEqual(str(copy.resolve()), line.split()[1])
                self.assertNotIn(str(TICKETS_PY.resolve()), line)


class TestRelativeGitdirPointer(unittest.TestCase):
    """`make_worktree` writes an absolute pointer; git writes a relative one
    whenever the worktree was added with a relative path.

    The bodies moved to `scripts/state_root.py`; these two names survive
    here as re-exports, because `scripts/cutcheck.py` and `scripts/ui.py`
    still import them from this module. What is graded is that the
    re-export is the owner's function and not a second copy of it.
    """

    def test_a_relative_pointer_resolves_against_the_pointer_files_own_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main = tmp / "main"
            (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
            worktree = tmp / "wt"
            worktree.mkdir()
            pointer = worktree / ".git"
            pointer.write_text("gitdir: ../main/.git/worktrees/wt\n", encoding="utf-8")
            self.assertEqual(main.resolve(), tickets_mod._main_checkout_root(pointer))
            self.assertEqual(main.resolve(), tickets_mod._find_repo_root(worktree))

    def test_the_two_names_are_the_resolvers_own_functions(self):
        self.assertIs(
            tickets_mod.state_root.main_checkout_root, tickets_mod._main_checkout_root
        )
        self.assertIs(
            tickets_mod.state_root.find_repo_root, tickets_mod._find_repo_root
        )


FENCE_TICKET_TAIL = (
    "\n## Result\n\nOLD BODY\n\n"
    "```markdown\n## Objective\nquoted heading\n```\n\n"
    "## Feedback\n\n[]\n"
)


def fence_broken(worktree_pair, tail: str) -> Path:
    """Append `tail` to the fixture ticket and hand back its path."""

    _main, _worktree, run_dir = worktree_pair
    ticket = run_dir / "T1.md"
    ticket.write_text(ticket.read_text(encoding="utf-8") + tail, encoding="utf-8")
    return ticket


class TestUnterminatedFenceIsReported(unittest.TestCase):
    """A fence that never closes hides every heading below it from
    `_heading_lines`, so the writer used to conclude the section was absent
    and create a second one -- leaving two `## Result` headings that
    `_sections` resolves to neither, since the fence swallows both. The file
    is corrupt input at that point: the only safe write is none, reported."""

    def test_an_unterminated_fence_in_an_earlier_section_is_reported_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(
                pair,
                "\n## Verification\n\n```text\nRan 1 test\nOK\n\n"  # never closed
                "## Result\n\nOLD BODY\n",
            )
            before = ticket.read_text(encoding="utf-8")
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED",
            )
            self.assertIn("unterminated fence", payload.get("error", ""), payload)
            self.assertNotIn("result", payload)
            after = ticket.read_text(encoding="utf-8")
            self.assertEqual(before, after)
            self.assertEqual(1, after.count("\n## Result"), after)
            self.assertNotIn("REPLACED", after)

    def test_the_refusal_covers_append_a_tilde_fence_and_a_fence_below_the_target(self):
        tails = {
            "tilde opener": "\n## Verification\n\n~~~\nRan 1 test\n\n## Result\n\nOLD\n",
            "opened below the target": "\n## Result\n\nOLD\n\n## Feedback\n\n```\nopen\n",
        }
        for name, tail in tails.items():
            for mode in ([], ["--append"]):
                with self.subTest(tail=name, mode=mode or ["replace"]):
                    with tempfile.TemporaryDirectory() as tmp:
                        pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
                        ticket = fence_broken(pair, tail)
                        before = ticket.read_text(encoding="utf-8")
                        payload = run_cmd(
                            pair[1], "result", "testrun", "T1", "--section", "Result",
                            "--text", "REPLACED", *mode,
                        )
                        self.assertIn("unterminated fence", payload.get("error", ""), payload)
                        self.assertEqual(before, ticket.read_text(encoding="utf-8"))


class TestIndentedFenceIsNotAFence(unittest.TestCase):
    """CommonMark 4.4-4.5: at four columns of indentation a ``` line is
    indented-code content, not a fence. Opening a block there is how a
    ticket that merely quotes an indented snippet became unwritable."""

    def test_a_four_space_indented_fence_is_not_a_fence(self):
        self.assertEqual(
            [0, 5],
            tickets_mod._heading_lines([
                "## Objective",
                "",
                "    ```",
                "    ## quoted inside an indented block",
                "",
                "## Result",
            ]),
        )
        # up to three columns it is still a fence, and so is an unindented one
        self.assertEqual([0], tickets_mod._heading_lines(["## A", "   ```", "## B", "```"]))
        self.assertEqual([0], tickets_mod._heading_lines(["## A", "```", "## B", "```"]))

    def test_a_section_below_an_indented_fence_is_replaced_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(
                pair,
                "\n## Verification\n\n    ```\n    ## quoted\n\n## Result\n\nOLD BODY\n",
            )
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED", "--replace",
            )
            self.assertIn("result", payload)
            text = ticket.read_text(encoding="utf-8")
            self.assertEqual(1, text.count("\n## Result"), text)
            sections = tickets_mod._sections(text)
            self.assertEqual("REPLACED", sections["Result"])
            self.assertIn("## quoted", sections["Verification"])


class TestFenceRepairHoldsBothDirections(unittest.TestCase):
    """The repair `d8af1c4` made -- a balanced fenced heading is quoted
    content, not a boundary -- and the refusal this item adds are one
    behavior read two ways. Pinning them in one case is what keeps a later
    change from buying either direction with the other."""

    def test_the_repair_holds_in_both_directions(self):
        # balanced: the quotation stays quoted and the span is replaced
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(pair, FENCE_TICKET_TAIL)
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED", "--replace",
            )
            self.assertIn("result", payload)
            text = ticket.read_text(encoding="utf-8")
            sections = tickets_mod._sections(text)
            self.assertEqual("REPLACED", sections["Result"])
            self.assertEqual("Test ticket.", sections["Objective"])
            self.assertEqual("[]", sections["Feedback"])
            self.assertNotIn("quoted heading", text)

        # the same ticket with the closing fence gone: refused, bytes intact
        with tempfile.TemporaryDirectory() as tmp:
            pair = make_worktree(Path(tmp), {"T1": ("claimed", "[]")})
            ticket = fence_broken(
                pair, FENCE_TICKET_TAIL.replace("quoted heading\n```\n", "quoted heading\n")
            )
            before = ticket.read_text(encoding="utf-8")
            payload = run_cmd(
                pair[1], "result", "testrun", "T1", "--section", "Result",
                "--text", "REPLACED",
            )
            self.assertIn("unterminated fence", payload.get("error", ""), payload)
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))


ISOLATED_TICKET = FULL_TICKET.replace(
    "write_scope:", "isolation: required\nwrite_scope:"
)
UNISOLATED_TICKET = FULL_TICKET.replace(
    "write_scope:", "isolation: none\nwrite_scope:"
)

GIT_ENV = dict(
    os.environ,
    GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
    GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
)
