"""Behavioral ticket regression cases."""

from .identity_terminal import *  # noqa: F401,F403
from .run_state_artifacts import *  # noqa: F401,F403

def improvement_of() -> Path:
    """The sink's improvement tree, wherever ``use_sink`` last pointed."""

    return sink_root() / "improvement"


def coverage_of() -> Path:
    return improvement_of() / "covered.jsonl"


def function_def(name: str):
    """One top-level function of the improvement/dispatch owner, as its AST."""

    tree = ast.parse(TICKETS_DISPATCH_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"scripts/tickets_dispatch.py declares no {name}")


def open_modes(node) -> list:
    """The mode every ``open(...)`` under ``node`` is called with."""

    modes = []
    for child in ast.walk(node):
        if not (isinstance(child, ast.Call) and isinstance(child.func, ast.Name)):
            continue
        if child.func.id != "open":
            continue
        mode = None
        if len(child.args) > 1 and isinstance(child.args[1], ast.Constant):
            mode = child.args[1].value
        for keyword in child.keywords:
            if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
                mode = keyword.value.value
        modes.append(mode)
    return modes


def coverage_branch():
    """The statements of ``_cmd_improvement`` that write the coverage record.

    Found by the constant that names the record, never by position, so
    rearranging the function cannot quietly move what the case below reads.
    """

    smallest = None
    for node in ast.walk(function_def("_cmd_improvement")):
        if not isinstance(node, ast.If):
            continue
        for branch in (node.body, node.orelse):
            names_it = any(
                isinstance(sub, ast.Name) and sub.id == "COVERAGE_RECORD_NAME"
                for stmt in branch
                for sub in ast.walk(stmt)
            )
            if names_it and (smallest is None or len(branch) < len(smallest)):
                smallest = branch
    return smallest


class TestImprovementWriter(unittest.TestCase):
    """The improvement streams reach the sink through the installed script,
    the way run state does: `rules/visibility.md` §6 covers the coverage
    record and every proposal, and neither has any other channel."""

    def test_a_proposal_lands_whole_under_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            body = "# proposal\n\nthe amendment, verbatim\n"
            self.assertFalse(improvement_of().exists())
            payload = run_cmd(tmp, "improvement", "--proposal", "amend-x.md", "--text", body)
            landed = improvement_of() / "proposals" / "amend-x.md"
            # assert the marker, then read past it: a script without the
            # subcommand reads as a failure here, never as a KeyError
            self.assertIn("improvement", payload, payload.get("error"))
            self.assertEqual("proposal", payload["improvement"]["mode"])
            self.assertEqual("amend-x.md", payload["improvement"]["name"])
            self.assertEqual(str(landed), payload["improvement"]["path"])
            self.assertTrue(Path(payload["improvement"]["path"]).is_absolute())
            # the parents did not exist a moment ago
            self.assertEqual(body, landed.read_text(encoding="utf-8"))
            self.assertEqual(body.encode("utf-8"), landed.read_bytes())

    def test_the_proposal_body_can_come_from_a_file_in_the_callers_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            workspace = tmp / "workspace"
            workspace.mkdir()
            source = workspace / "draft.md"
            source.write_text("read inside, written outside\n", encoding="utf-8")
            payload = run_cmd(
                workspace, "improvement", "--proposal", "draft.md", "--file", str(source)
            )
            self.assertIn("improvement", payload, payload.get("error"))
            self.assertEqual(
                "read inside, written outside\n",
                (improvement_of() / "proposals" / "draft.md").read_text(encoding="utf-8"),
            )
            # the workspace holds its own draft and nothing else
            self.assertEqual([source], sorted(workspace.rglob("*")))

    def test_a_covered_line_is_appended_and_every_earlier_line_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            payload = run_cmd(tmp, "improvement", "--covered", '{"id": "f-1"}')
            self.assertIn("improvement", payload, payload.get("error"))
            self.assertEqual("covered", payload["improvement"]["mode"])
            self.assertIsNone(payload["improvement"]["name"])
            self.assertEqual(str(coverage_of()), payload["improvement"]["path"])
            before = coverage_of().read_bytes()
            with open(coverage_of(), "a", encoding="utf-8", newline="\n") as handle:
                handle.write('{"id": "f-2"}\n')
            run_cmd(tmp, "improvement", "--covered", '{"id": "f-3"}')
            self.assertEqual(
                ['{"id": "f-1"}', '{"id": "f-2"}', '{"id": "f-3"}'],
                coverage_of().read_text(encoding="utf-8").splitlines(),
            )
            self.assertEqual(before, coverage_of().read_bytes()[: len(before)])

    def test_ten_concurrent_writers_each_land_one_whole_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            lines = [f'{{"writer": {i}, "pad": "' + "x" * 2000 + '"}' for i in range(10)]
            with ThreadPoolExecutor(max_workers=10) as pool:
                payloads = list(
                    pool.map(
                        lambda line: run_cmd(tmp, "improvement", "--covered", line), lines
                    )
                )
            # A writer that reported an error and a writer whose line was lost
            # are two different defects, and the file check below reports the
            # second for both -- the payloads are the only place the first is
            # visible.
            self.assertEqual([], [p["error"] for p in payloads if "error" in p])
            self.assertTrue(coverage_of().is_file(), "no coverage record was written")
            self.assertEqual(
                sorted(lines), sorted(coverage_of().read_text(encoding="utf-8").splitlines())
            )

    def test_the_coverage_record_is_written_through_the_serialised_appender(self):
        """The guard against a lost line and against a later
        read-modify-write, read off the module itself.

        The branch opens nothing of its own. Every workspace on the machine
        appends to this one record, and a bare ``open(..., "a")`` is a seek
        and a write on Windows -- two writers take one offset and a whole
        line vanishes, which reads like a writer that never ran. So the
        branch calls ``_append_one_line``, the one place that append is
        serialised, and the mechanism is graded there by the instrument that
        grades the worklog's."""

        branch = coverage_branch()
        self.assertIsNotNone(
            branch, "no branch of _cmd_improvement names COVERAGE_RECORD_NAME"
        )
        self.assertEqual([], [mode for stmt in branch for mode in open_modes(stmt)])
        self.assertEqual(
            ["_append_one_line"],
            [
                sub.func.id
                for stmt in branch
                for sub in ast.walk(stmt)
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
            ],
            "the coverage record is appended through the serialised writer",
        )
        assert_one_append_open_and_no_read(
            self, inspect.getsource(tickets_mod._append_one_line), "_append_one_line"
        )
        # and that branch is the only place the record's path is composed
        loads = [
            node
            for node in ast.walk(ast.parse(TICKETS_DISPATCH_PY.read_text(encoding="utf-8")))
            if isinstance(node, ast.Name)
            and node.id == "COVERAGE_RECORD_NAME"
            and isinstance(node.ctx, ast.Load)
        ]
        self.assertEqual(1, len(loads))

    def test_an_unsafe_proposal_name_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            for bad in ("../escape.md", "a/b.md", "a\\b.md", "..", "."):
                with self.subTest(bad):
                    payload = run_cmd(tmp, "improvement", "--proposal", bad, "--text", "x")
                    self.assertIn("unsafe proposal name", payload.get("error", ""))
                    self.assertIn(f"'{bad}'", payload.get("error", ""))
                    self.assertNotIn("improvement", payload)
            self.assertFalse(improvement_of().exists())

    def test_a_malformed_invocation_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            cases = {
                "both modes": (
                    ("improvement", "--proposal", "p.md", "--covered", "line"),
                    "one of --proposal",
                ),
                "neither mode": (("improvement",), "one of --proposal"),
                "no body": (("improvement", "--proposal", "p.md"), "one of --file"),
                "both bodies": (
                    ("improvement", "--proposal", "p.md", "--text", "x", "--file", "f"),
                    "one of --file",
                ),
                "a body for a covered line": (
                    ("improvement", "--covered", "line", "--text", "x"),
                    "--covered carries its own line",
                ),
                "an unreadable body file": (
                    ("improvement", "--proposal", "p.md", "--file", str(tmp / "absent.md")),
                    "unreadable body file",
                ),
                "a positional argument": (
                    ("improvement", "stray", "--covered", "line"),
                    "no positional argument",
                ),
                "an unknown flag": (
                    ("improvement", "--covered", "line", "--force"),
                    "does not accept --force",
                ),
            }
            for label, (args, expected) in cases.items():
                with self.subTest(label):
                    completed = run_full(tmp, *args)
                    self.assertEqual(1, completed.returncode, completed.stderr)
                    payload = json.loads(completed.stdout)
                    self.assertIn(expected, payload.get("error", ""))
                    self.assertNotIn("improvement", payload)
            self.assertFalse(improvement_of().exists())

    def test_neither_mode_falls_back_into_the_callers_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            workspace = tmp / "workspace"
            workspace.mkdir()
            (workspace / "work.txt").write_text("payload\n", encoding="utf-8")
            blocker = TestNoFallback.block_the_sink(tmp)
            before = TestNoFallback.listing(workspace)
            for args in (
                ("improvement", "--proposal", "p.md", "--text", "a body"),
                ("improvement", "--covered", '{"id": "f-1"}'),
            ):
                with self.subTest(args[1]):
                    completed = run_full(workspace, *args)
                    # the script's convention: an error payload, and a
                    # nonzero exit carrying it out to the caller
                    self.assertEqual(1, completed.returncode, completed.stderr)
                    payload = json.loads(completed.stdout)
                    # the refusal is about the sink it could not reach, so a
                    # script that simply has no such subcommand fails here
                    self.assertIn("unwritable improvement record", payload.get("error", ""))
                    self.assertNotIn("improvement", payload)
            self.assertEqual(before, TestNoFallback.listing(workspace))
            self.assertFalse((workspace / ".orch").exists())
            self.assertTrue(blocker.is_file())

    def test_the_subcommand_is_named_where_a_caller_looks(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            payload = run_cmd(Path(tmp))
            self.assertIn("improvement", payload["error"])
        # `--help` owns the live command list (the module docstring says so),
        # so the usage table is where the spelling is graded, not the prose.
        usage = tickets_mod.SUBCOMMAND_USAGE["improvement"]
        self.assertIn("--proposal <name> (--file <path> | --text <string>)", usage)
        self.assertIn("--covered <line>", usage)
class ExitConventionTest(unittest.TestCase):
    """Pin the exit convention: exit 1 when JSON has 'error', exit 0 otherwise."""

    def test_error_exits_1(self):
        """An error path exits with code 1."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {})
            result = run_full(tmp, "result", "no-run", "no-id", "--text", "x")
            self.assertIn("error", result.stdout)
            self.assertEqual(1, result.returncode)

    def test_success_exits_0_list(self):
        """A success path exits with code 0: list subcommand."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            result = run_full(tmp, "list")
            payload = json.loads(result.stdout)
            self.assertNotIn("error", payload)
            self.assertEqual(0, result.returncode)

    def test_success_exits_0_ready(self):
        """A success path exits with code 0: ready subcommand."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            result = run_full(tmp, "ready")
            payload = json.loads(result.stdout)
            self.assertNotIn("error", payload)
            self.assertEqual(0, result.returncode)

    def test_error_exits_1_missing_ticket(self):
        """An error path exits with code 1: a ticket the run does not hold."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("complete", "[]")})
            result = run_full(tmp, "show", "testrun", "T-absent")
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)
            self.assertEqual(1, result.returncode)

    def test_error_exits_1_set_status_invalid(self):
        """An error path exits with code 1: invalid status."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            result = run_full(tmp, "set-status", "testrun", "T1", "invalid-status")
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)
            self.assertEqual(1, result.returncode)

    def test_error_exits_1_missing_subcommand(self):
        """An error path exits with code 1: missing subcommand."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {})
            result = run_full(tmp)
            payload = json.loads(result.stdout)
            self.assertIn("error", payload)
            self.assertEqual(1, result.returncode)


class DocstringHonestyTest(unittest.TestCase):
    """Assert the module docstring does not claim exit 0 on failure."""

    def test_docstring_does_not_claim_exit_0_on_failure(self):
        """The docstring should not claim 'never as a non-zero exit'."""
        docstring = tickets_mod.__doc__ or ""
        self.assertNotIn("never as a non-zero exit", docstring)


class RunIdentitySpecificationTest(unittest.TestCase):
    """REVIEW-2026-08-15.md T3: `run.json` is this script's format, so its
    specification is stated where the writer is rather than in a T0
    contract that owns nothing else about it. The document written is
    unchanged — the spec moved, the bytes did not."""

    def test_the_docstring_states_every_field_of_the_document(self):
        docstring = tickets_mod.__doc__ or ""
        self.assertIn(tickets_mod.RUN_IDENTITY_NAME, docstring)
        for field in ("run", "sink_convention", "opened_at", "project.root",
                      "project.origin", "project.name", "workspaces[].path",
                      "workspaces[].first_seen", "orchflows.receipt_version",
                      "orchflows.source_commit", "terminal_at",
                      "terminal_ticket_id", "terminal_status", "elapsed_ms"):
            with self.subTest(field):
                self.assertIn(field, docstring)

    def test_the_document_written_carries_exactly_those_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {"T1": ("ready", "[]")})
            run_main(tmp, "run-state", "testrun", "--note", "opened")
            identity = json.loads(
                (sink_root() / "runs" / "testrun" / tickets_mod.RUN_IDENTITY_NAME)
                .read_text(encoding="utf-8")
            )
            self.assertEqual(
                ["opened_at", "orchflows", "project", "run", "sink_convention", "workspaces"],
                sorted(identity),
            )
            self.assertEqual(
                ["receipt_version", "source_commit"], sorted(identity["orchflows"])
            )
            self.assertEqual(["name", "origin", "root"], sorted(identity["project"]))
            self.assertEqual(
                ["first_seen", "path"], sorted(identity["workspaces"][0])
            )
            self.assertEqual(tickets_mod.SINK_CONVENTION, identity["sink_convention"])
