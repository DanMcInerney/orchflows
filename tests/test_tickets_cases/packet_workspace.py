"""Behavioral ticket regression cases."""

from .run_state_resolution import *  # noqa: F401,F403

def git_run(cwd: Path, *args) -> str:
    completed = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd), env=GIT_ENV,
    )
    if completed.returncode != 0:
        raise unittest.SkipTest(f"git {args[0]} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def establishment_lines(prompt: str) -> list:
    """Every emitted establishment line, found the way a child finds it: by
    the tokens themselves, never by position and never by a literal path."""

    found = []
    for line in prompt.splitlines():
        tokens = line.split()
        if (
            len(tokens) > 2
            and Path(tokens[1]).name == "workspace.py"
            and tokens[2] == "start"
        ):
            found.append(line)
    return found


def make_packet_repo(tmp: Path, body: str, run: str = "testrun", tid: str = "T1") -> Path:
    (tmp / ".git").mkdir()
    run_dir = use_sink(tmp) / "tickets" / run
    run_dir.mkdir(parents=True)
    path = run_dir / f"{tid}.md"
    path.write_text(body, encoding="utf-8")
    return path


def make_isolated_fixture(tmp: Path, body: str = None):
    """A real `git init` main checkout, a ticket at its root, and a linked
    `git worktree add` tree on its own branch — the shape the emitted line is
    meant to be run in."""

    use_sink(tmp)
    main = tmp / "main"
    main.mkdir()
    git_run(main, "init", "--quiet")
    (main / "README.md").write_text("baseline\n", encoding="utf-8")
    git_run(main, "add", "README.md")
    git_run(main, "commit", "--quiet", "-m", "init")
    base = git_run(main, "rev-parse", "HEAD")
    run_dir = sink_root() / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    ticket = run_dir / "T1.md"
    ticket.write_text(ISOLATED_TICKET if body is None else body, encoding="utf-8")
    worktree = tmp / "wt"
    git_run(main, "worktree", "add", "--quiet", "-b", "item-branch", str(worktree))
    return main, worktree, ticket, base


def run_argv(argv: list, cwd: Path):
    return subprocess.run(
        argv, capture_output=True, text=True, encoding="utf-8",
        errors="replace", cwd=str(cwd),
    )


class TestPacketEmitsTheEstablishmentCommand(unittest.TestCase):
    """contracts/work-item.md's `isolation` is what `packet` conditions on:
    an isolated item is told how to establish its workspace, and a read-only
    lane is told nothing it must not run."""

    def packet_for(self, tmp: Path, body: str, run: str = "testrun", tid: str = "T1"):
        make_packet_repo(tmp, body, run, tid)
        return run_cmd(tmp, "packet", run, tid, "--reply-to", "main")["packet"]

    def test_required_emits_the_line_and_none_or_absent_omit_it(self):
        for body, expected in (
            (ISOLATED_TICKET, 1), (UNISOLATED_TICKET, 0), (FULL_TICKET, 0)
        ):
            with tempfile.TemporaryDirectory() as tmp:
                packet = self.packet_for(Path(tmp), body)
                prompt = packet["prompt"]
                self.assertEqual(expected, len(establishment_lines(prompt)), prompt)
                if not expected:
                    # omitted entirely: not the command, not a mention of it
                    self.assertNotIn("workspace.py", prompt)

    def test_run_and_id_are_interpolated_from_the_ticket(self):
        for run, tid in (("testrun", "T1"), ("otherrun", "Z9")):
            body = ISOLATED_TICKET.replace("id: T1", f"id: {tid}").replace(
                "run: testrun", f"run: {run}"
            )
            with tempfile.TemporaryDirectory() as tmp:
                packet = self.packet_for(Path(tmp), body, run, tid)
                (line,) = establishment_lines(packet["prompt"])
                self.assertEqual([run, tid], line.split()[3:5], line)

    def test_isolation_rides_the_packet_dict_beside_pack_and_independence(self):
        for body, expected in (
            (ISOLATED_TICKET, "required"),
            (UNISOLATED_TICKET, "none"),
            (FULL_TICKET, "none"),  # contracts/work-item.md: absent reads `none`
        ):
            with tempfile.TemporaryDirectory() as tmp:
                packet = self.packet_for(Path(tmp), body)
                self.assertLessEqual(
                    {"pack", "independence", "isolation"}, set(packet), sorted(packet)
                )
                self.assertEqual(expected, packet["isolation"])
                self.assertEqual("orch-code-pack", packet["pack"])

    def test_the_line_is_absolute_one_token_per_argument_and_shell_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.packet_for(Path(tmp), ISOLATED_TICKET)
            (line,) = establishment_lines(packet["prompt"])
            for forbidden in ("|", ">", "<", "&&", "$(", '"', "'"):
                self.assertNotIn(forbidden, line, line)
            tokens = line.split()
            self.assertEqual(5, len(tokens), line)
            self.assertEqual(sys.executable, tokens[0])
            self.assertTrue(Path(tokens[0]).is_absolute(), tokens[0])
            self.assertEqual(str((TICKETS_PY.parent / "workspace.py").resolve()), tokens[1])
            self.assertTrue(Path(tokens[1]).is_absolute(), tokens[1])
            self.assertEqual(["start", "testrun", "T1"], tokens[2:])

    def test_the_interpreter_and_script_path_are_derived_not_literal(self):
        """Run a copy of both scripts from somewhere else entirely: a
        hardcoded interpreter or a literal script path emits the same line
        from either layout, and installed scripts do not sit in `scripts/`."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, ISOLATED_TICKET)
            elsewhere = tmp / "elsewhere"
            elsewhere.mkdir()
            for name in (
                "state_root.py", "tickets.py", "workspace.py", *TICKETS_SUPPORT_NAMES
            ):
                (elsewhere / name).write_text(
                    (TICKETS_PY.parent / name).read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            completed = run_argv(
                [sys.executable, str(elsewhere / "tickets.py"), "packet",
                 "testrun", "T1", "--reply-to", "main"],
                tmp,
            )
            packet = json.loads(completed.stdout)["packet"]
            (line,) = establishment_lines(packet["prompt"])
            self.assertEqual(str((elsewhere / "workspace.py").resolve()), line.split()[1])
            self.assertNotIn(str(TICKETS_PY.parent.resolve()), line)

    def test_the_emitting_code_holds_no_literal_interpreter_or_script_path(self):
        source = " ".join((
            inspect.getsource(tickets_mod._cmd_packet)
            + inspect.getsource(tickets_mod._packet_under_run_lock)
        ).split())
        self.assertNotIn("python3", source)
        self.assertNotIn("scripts/workspace.py", source)
        self.assertIn("sys.executable", source)
        self.assertIn("with_name", source)


def repacked(pack: str, body: str = ISOLATED_TICKET) -> str:
    """`body` restamped onto another pack. Every fixture below differs from
    the next in that one field, so nothing else can be what moved."""

    restamped = body.replace("pack: orch-code-pack", f"pack: {pack}")
    assert restamped != body or pack == "orch-code-pack", pack
    return restamped


class PackWorkspaceTest(unittest.TestCase):
    """`isolation: required` says this item works alone; the pack's
    `workspace` cell says what working alone is made of. Only a git mechanism
    has a workspace `scripts/workspace.py start` can establish — it branches
    and adds a worktree — so under a document-tree or evidence-store pack the
    emitted command is an instruction to do something the run's mechanism has
    no meaning for. `packet` conditions on both, never on `isolation` alone."""

    def lines_for(self, body: str) -> list:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, body)
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("packet", packet, packet)
            return establishment_lines(packet["packet"]["prompt"])

    def prompt_for(self, body: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, body)
            return run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")[
                "packet"
            ]["prompt"]

    def test_a_git_cell_pack_that_is_required_carries_the_invocation(self):
        for pack in ("orch-code-pack", "orch-design-pack"):
            lines = self.lines_for(repacked(pack))
            self.assertEqual(1, len(lines), (pack, lines))
            self.assertEqual(["start", "testrun", "T1"], lines[0].split()[2:], pack)

    def test_a_non_git_cell_pack_that_is_required_carries_none(self):
        for pack in ("orch-content-pack", "orch-research-pack"):
            prompt = self.prompt_for(repacked(pack))
            self.assertEqual([], establishment_lines(prompt), (pack, prompt))
            # omitted entirely: not the command, not a mention of it
            self.assertNotIn("workspace.py", prompt, pack)

    def test_the_declaration_is_still_reported_faithfully(self):
        """Suppressing the step never rewrites what the item declared: the
        packet still reads `required`, so a join grading isolation sees the
        item's own value and not this script's opinion of it."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(tmp, repacked("orch-content-pack"))
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")[
                "packet"
            ]
            self.assertEqual("required", packet["isolation"])
            self.assertEqual("orch-content-pack", packet["pack"])

    def test_a_content_pack_with_the_field_absent_carries_none(self):
        """Coverage of the item shape a decomposer emits for a content lane —
        no `isolation` at all — not discrimination: `packet` omitted the
        command for an absent field before this table existed."""

        prompt = self.prompt_for(repacked("orch-content-pack", FULL_TICKET))
        self.assertNotIn("isolation:", prompt)
        self.assertEqual([], establishment_lines(prompt), prompt)
        self.assertNotIn("workspace.py", prompt)

    def test_the_git_half_needs_the_declaration_too(self):
        """The pack is a second condition, never a replacement for the first:
        a git-cell pack that never declared isolation is still told nothing."""

        prompt = self.prompt_for(FULL_TICKET)
        self.assertEqual([], establishment_lines(prompt), prompt)
        self.assertNotIn("workspace.py", prompt)

    def test_a_pack_absent_from_the_table_still_gets_the_command(self):
        """The table can only be as current as the last sync. An unknown pack
        resolves toward emitting: a child handed a step its mechanism cannot
        use fails at its first act, in the open, while an omitted step leaves
        an isolated item working in the shared tree and losing it at the
        join, with nothing to see."""

        for pack in ("orch-widget-pack", ""):
            prompt = self.prompt_for(repacked(pack))
            self.assertEqual(1, len(establishment_lines(prompt)), (pack, prompt))

    def test_the_table_is_hardcoded_beside_the_engine_list(self):
        """A module-level literal, not a tree read, because an installed copy
        of this script runs against a target repository that carries no
        `packs/` at all."""

        table = tickets_mod.PACK_WORKSPACE_MECHANISMS
        self.assertIsInstance(table, dict)
        self.assertTrue(all(isinstance(v, str) and v for v in table.values()), table)
        lines = TICKETS_FORMAT_PY.read_text(encoding="utf-8").splitlines()
        index = next(
            i for i, line in enumerate(lines)
            if line.startswith("PACK_WORKSPACE_MECHANISMS = ")
        )
        comment = []
        while index and lines[index - 1].lstrip().startswith("#"):
            index -= 1
            comment.insert(0, lines[index])
        comment = "\n".join(comment)
        for token in ("packs/", "tests/test_validate.py", "workspace"):
            self.assertIn(token, comment, comment)


SCRIPTS = ROOT / "scripts"
PACKS_SEGMENT = "packs"
# scripts/cutcheck.py reads `<worktree_root>/packs/<pack>/SKILL.md`, where the
# root is the cut's own tree, handed in by the caller. That is a read of the
# repository under grading, not of the tree the script was installed from, and
# it already tolerates the tree's absence.
#
# scripts/tickets.py joined it for the same reason and under the same terms:
# `template_defects` and `instantiate` grade a root stub against the
# `required_spec_fields` of the pack it stamps (contracts/work-item.md), and
# `_packs_root` walks up from the *template directory the caller named* --
# never from `__file__` -- returning None when no `packs/` stands beside it,
# which is the ordinary answer for an installed copy. That is the discrimination
# the test below keeps: a tree read anchored on the caller's argument is
# allowed here; one anchored on the script's own location is not, and no
# module resolves a pack-to-mechanism binding by reading anything.
#
# scripts/cutcheck_pricing.py joined on cutcheck.py's own terms, not on a
# narrower licence: it carries the same `PACKS_DIR = "packs"` literal, and the
# tree it reads through it is the orchflows library's, never the target
# repository's -- family 6's one resolution, `cutcheck_executor._lib_root`,
# says so in its own docstring. Recorded precisely because the shorter reason
# offered for it -- that it anchors on a caller-supplied root and never on
# `__file__` -- is not true: it calls that resolution with `declared=None`, so
# it reaches the `__file__`-anchored candidate every time. What licenses it is
# which tree it reads, not what it anchors on.
TREE_READING_SCRIPTS = {"cutcheck.py", "cutcheck_pricing.py", "tickets_worklog.py"}


def code_strings(source: str) -> list:
    """Every string constant in `source` that is not a docstring.

    Comments never enter the AST at all, and a docstring is skipped by
    identity here, so naming the tree in prose is outside this set by
    construction -- which is the distinction a grep cannot draw.
    """

    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ) or not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                docstrings.add(id(first.value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in docstrings
    ]


def names_the_tree(source: str) -> list:
    """The code strings in `source` carrying `packs` as a whole path segment.
    `orch-code-pack` is not one; `packs`, `packs/x` and `a/packs` are."""

    return [
        value
        for value in code_strings(source)
        if PACKS_SEGMENT in value.replace("\\", "/").split("/")
    ]


class NoLibraryTreeReadTest(unittest.TestCase):
    """The installed script has no library beside it: it runs from wherever
    the installer put it, against a target repository that carries no
    `packs/`. So the pack-to-mechanism table is a literal and nothing here
    resolves a pack by reading the tree.

    Asserted in a class rather than by a recursive grep, which exits 1 on the
    no-match result that means success and so reads backwards as an oracle --
    and which cannot tell a comment naming the tree from a read of it.

    Note: the ticket's premise that `scripts/` carries no such string at the
    baseline holds only for the literal `packs/`; `scripts/cutcheck.py` has
    carried `PACKS_DIR = "packs"` and a read through it all along, of the cut's
    own tree. That module is allowlisted by name above rather than asserted
    away, so this stays a true statement about a tree that already has one.
    """

    def test_the_ticket_script_never_anchors_a_tree_read_on_its_own_location(self):
        """The one thing the installed script cannot do is look beside
        itself for a library. `_packs_root` walks up from the directory the
        caller named, so a template graded where it sits finds the packs
        beside it and an installed copy finds none — which is why the check
        it feeds returns nothing rather than refusing every stub."""

        source = TICKETS_WORKLOG_PY.read_text(encoding="utf-8")
        self.assertIn("def _packs_root", source)
        packs_root = source.split("def _packs_root", 1)[1].split("\ndef ", 1)[0]
        self.assertNotIn("__file__", packs_root)
        self.assertIn("Path(directory)", packs_root)
        # and the pack-to-mechanism table is still a literal, not a read
        self.assertIsInstance(tickets_mod.PACK_WORKSPACE_MECHANISMS, dict)

    def test_a_template_with_no_packs_beside_it_is_graded_without_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(tickets_mod._packs_root(Path(tmp)))

    def test_no_module_outside_the_named_one_names_it(self):
        naming = {
            path.name: names_the_tree(path.read_text(encoding="utf-8"))
            for path in sorted(SCRIPTS.glob("*.py"))
        }
        offenders = {name: hits for name, hits in naming.items() if hits}
        self.assertLessEqual(set(offenders), TREE_READING_SCRIPTS, offenders)

    def test_prose_naming_the_tree_is_not_a_read(self):
        """The oracle's own discrimination: it must ignore a comment and a
        docstring and still catch a path built in code, or the two assertions
        above pass for the wrong reason."""

        prose = '"""A docstring naming packs/x."""\n# a comment naming packs/x\n'
        self.assertEqual([], names_the_tree(prose))
        self.assertEqual([], names_the_tree(prose + 'PACK = "orch-code-pack"\n'))
        self.assertEqual(
            ["packs"], names_the_tree(prose + 'P = root / "packs" / pack\n')
        )
        self.assertEqual(
            ["packs/orch-code-pack"],
            names_the_tree(prose + 'P = root / "packs/orch-code-pack"\n'),
        )

    def test_a_packet_renders_where_no_library_tree_exists(self):
        """The behavioural half: a copy of the script somewhere with no
        `packs/` above it or beside it still decides every pack in the table,
        exit 0. A tree read would answer differently, or not at all."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            elsewhere = tmp / "elsewhere"
            elsewhere.mkdir()
            # state_root.py travels with it: the script imports its sibling
            # resolver, and the installer copies `scripts/` as one unit. What
            # this case removes is the *library* tree, not the sibling.
            for name in (
                "tickets.py", "workspace.py", "state_root.py", *TICKETS_SUPPORT_NAMES
            ):
                (elsewhere / name).write_text(
                    (SCRIPTS / name).read_text(encoding="utf-8"), encoding="utf-8"
                )
            self.assertFalse((elsewhere / "packs").exists())
            self.assertFalse((tmp / "packs").exists())
            for pack, mechanism in sorted(
                tickets_mod.PACK_WORKSPACE_MECHANISMS.items()
            ):
                repo = tmp / pack
                repo.mkdir()
                make_packet_repo(repo, repacked(pack))
                completed = run_argv(
                    [sys.executable, str(elsewhere / "tickets.py"), "packet",
                     "testrun", "T1", "--reply-to", "main"],
                    repo,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
                prompt = json.loads(completed.stdout)["packet"]["prompt"]
                expected = int(mechanism in tickets_mod.GIT_WORKSPACE_MECHANISMS)
                self.assertEqual(
                    expected, len(establishment_lines(prompt)), (pack, prompt)
                )


class UnboundWorkspaceTableTest(unittest.TestCase):
    """`PACK_WORKSPACE_MECHANISMS` is `None` in `tickets_format` until the
    public `scripts/tickets.py` facade binds it, and `tickets_store` takes its
    copy by `from`-import at module load. So any importer that reaches
    `establishes_a_git_workspace` without the facade imported first -- and
    `scripts/tickets_packet.py` imports the function straight from
    `tickets_store` and calls it -- used to get

        AttributeError: 'NoneType' object has no attribute 'get'

    which names neither the constant, nor the facade that owns the table, nor
    the import order that fixes it. The function's own docstring documents a
    deliberate "a pack absent from the table answers yes" fallback, and the
    unbound case bypassed that rather than degrading into it.

    Run in a child interpreter because the facade is imported process-wide by
    the time any of these suites reach here; the unbound state is only
    reachable from a fresh one.
    """

    SOURCE = (
        "import sys\n"
        "sys.path.insert(0, {scripts!r})\n"
        "import tickets_packet\n"
        "try:\n"
        "    tickets_packet.establishes_a_git_workspace('orch-code-pack')\n"
        "except Exception as error:\n"
        "    print(type(error).__name__)\n"
        "    print(error)\n"
    )

    def test_reaching_the_table_unbound_names_the_facade_that_binds_it(self):
        done = subprocess.run(
            [sys.executable, "-B", "-c",
             self.SOURCE.format(scripts=str(SCRIPTS))],
            capture_output=True, text=True, encoding="utf-8", errors="replace")

        self.assertEqual(0, done.returncode, done.stderr)
        kind, _, message = done.stdout.partition("\n")
        self.assertNotEqual("AttributeError", kind.strip(), done.stdout)
        self.assertIn("PACK_WORKSPACE_MECHANISMS", message)
        self.assertIn("scripts/tickets.py", message)
