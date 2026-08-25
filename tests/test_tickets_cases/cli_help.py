"""Behavioral ticket regression cases."""

from .improvement import *  # noqa: F401,F403

def dispatch_subcommands() -> list:
    """Every name ``_dispatch`` accepts, read off its own comparisons.

    The loop below has to be total over the subcommands that exist, not
    over a list a reader kept in step by hand: a subcommand added to the
    dispatcher and forgotten here would be exactly the one whose ``--help``
    still errors.
    """

    found = []
    for node in ast.walk(ast.parse(inspect.getsource(tickets_mod._dispatch))):
        if not isinstance(node, ast.Compare):
            continue
        if not (isinstance(node.left, ast.Name) and node.left.id == "command"):
            continue
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                found.append(comparator.value)
            elif isinstance(comparator, (ast.Tuple, ast.List, ast.Set)):
                found.extend(
                    element.value
                    for element in comparator.elts
                    if isinstance(element, ast.Constant)
                    and isinstance(element.value, str)
                )
    return found


class HelpTest(unittest.TestCase):
    """`--help` is a request this script answers, never an unhandled case it
    renders as the ordinary error path: exit 0 and usage on stdout, at the
    top level and for every subcommand the dispatcher accepts."""

    def test_the_subcommand_list_is_not_empty_and_excludes_help_flags(self):
        subcommands = dispatch_subcommands()
        self.assertGreaterEqual(len(subcommands), 7, subcommands)
        for flag in ("--help", "-h"):
            self.assertNotIn(flag, subcommands)

    def test_bare_help_exits_0_with_usage_on_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {})
            for flag in ("--help", "-h", "help"):
                result = run_full(tmp, flag)
                self.assertEqual(0, result.returncode, f"{flag}: {result.stdout}")
                self.assertTrue(result.stdout.strip(), flag)
                payload = json.loads(result.stdout)
                self.assertNotIn("error", payload)
                # the top-level answer names every subcommand it dispatches
                for subcommand in dispatch_subcommands():
                    self.assertIn(subcommand, result.stdout, f"{flag}: {subcommand}")

    def test_every_subcommand_help_exits_0_with_non_empty_stdout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, {})
            for subcommand in dispatch_subcommands():
                for flag in ("--help", "-h"):
                    result = run_full(tmp, subcommand, flag)
                    self.assertEqual(
                        0, result.returncode, f"{subcommand} {flag}: {result.stdout}"
                    )
                    self.assertTrue(result.stdout.strip(), f"{subcommand} {flag}")
                    payload = json.loads(result.stdout)
                    self.assertNotIn("error", payload, f"{subcommand} {flag}")
                    self.assertIn(subcommand, result.stdout, f"{subcommand} {flag}")

    def test_help_never_touches_the_repository(self):
        """Usage is answered before any argument is resolved: `--help` on a
        subcommand whose required arguments are absent still answers, and
        outside a repository entirely it answers the same way."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)  # deliberately no .git anywhere under this tempdir
            for argv in (["--help"], ["claim", "--help"], ["run-state", "--help"]):
                result = run_full(tmp, *argv)
                self.assertEqual(0, result.returncode, f"{argv}: {result.stdout}")
                self.assertNotIn("error", json.loads(result.stdout), argv)

    def test_a_help_flag_taken_as_a_flag_value_is_not_a_help_request(self):
        """`--note --help` writes the note `--help`; only a help flag standing
        as its own token asks for usage. A run-state note whose text happens to
        be a help flag must not be silently swallowed into a usage answer."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            result = run_main(worktree, "run-state", "testrun", "--note", "--help")
            self.assertEqual(0, result.returncode, result.stdout)
            payload = json.loads(result.stdout)
            self.assertNotIn("help", payload)
            self.assertEqual("note", payload["run_state"]["mode"])
            self.assertEqual("--help\n", notes_of().read_text(encoding="utf-8"))

    def test_the_usage_table_covers_exactly_the_dispatched_subcommands(self):
        self.assertEqual(
            sorted(dispatch_subcommands()),
            sorted(tickets_mod.SUBCOMMAND_USAGE),
        )


CLAIMED_TICKET = FULL_TICKET.replace(
    "claimed_by: legacy-agent", "claimed_by: agent-a"
).replace("claimed_at: 2099-01-01T00:00:00Z", "claimed_at: 2026-08-16T00:00:00Z")


def filing_lines(prompt: str) -> list:
    """Every emitted `result --section` line, found by its own tokens."""

    return [
        line
        for line in prompt.splitlines()
        if len(line.split()) > 2
        and Path(line.split()[1]).name == "tickets.py"
        and line.split()[2] == "result"
    ]


class TestPacketNamesTheFilingCommand(unittest.TestCase):
    """Friction 2026-08-16T12:00: the prompt told the child to write its
    result into the ticket's own sections and named only the run-state
    commands, so the child derived the filing law from `--help`. The channel
    a packet demands is a channel the packet states."""

    def packet_for(self, tmp: Path, body: str = CLAIMED_TICKET):
        make_packet_repo(tmp, body)
        return run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]

    def test_a_packet_names_both_filing_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.packet_for(Path(tmp))
            lines = filing_lines(packet["prompt"])
            self.assertEqual(2, len(lines), packet["prompt"])
            file_line, text_line = lines
            self.assertEqual(
                ["--section", "SECTION", "--file", "PATH", "--append"], file_line.split()[5:]
            )
            self.assertEqual(["--section", "SECTION", "--text", "TEXT"], text_line.split()[5:])
            # the placeholder is answerable from the prompt alone
            for section in tickets_mod.EXECUTOR_SECTIONS:
                self.assertIn(section, packet["prompt"])

    def test_the_packet_filing_line_is_absolute_one_token_per_argument_and_shell_free(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.packet_for(Path(tmp))
            for line in filing_lines(packet["prompt"]):
                for forbidden in ("|", ">", "<", "&&", "$(", '"', "'"):
                    self.assertNotIn(forbidden, line, line)
                tokens = line.split()
                self.assertEqual(sys.executable, tokens[0])
                self.assertEqual(str(TICKETS_PY.resolve()), tokens[1])
                self.assertTrue(Path(tokens[1]).is_absolute(), tokens[1])
                # run and id interpolated from the ticket, not left placeholders
                self.assertEqual(["result", "testrun", "T1"], tokens[2:5])

    def test_a_packet_for_a_read_only_lane_still_names_it(self):
        """A lane with no workspace authority at all still files its result:
        the ticket's own sections sit outside `write_scope`."""

        with tempfile.TemporaryDirectory() as tmp:
            packet = self.packet_for(
                Path(tmp), CLAIMED_TICKET.replace("write_scope: scratch/t1.txt", "write_scope: []")
            )
            self.assertEqual(2, len(filing_lines(packet["prompt"])))


class TestPacketNamesTheChildsOwnName(unittest.TestCase):
    """Friction 2026-08-16T09:40: an engine lane was given `reply_to: main`
    for its own return but never its own name, which is the `reply_to` of
    every packet it in turn emits; it recovered the name by reading the
    host's subagent files. contracts/work-item.md#dispatch: a child never
    infers `reply_to`, so every child is told the name it was claimed under —
    it may have to record under it — and a child that will itself dispatch is
    told the further fact that the same name is its own children's
    `reply_to`."""

    def packet_for(self, tmp: Path, body: str):
        make_packet_repo(tmp, body)
        return run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]

    def test_a_packet_for_a_dispatching_executor_states_the_name_it_was_claimed_under(self):
        # The set is read from the tree, never from the constant under test:
        # iterating `DISPATCHING_EXECUTORS` passed with no assertion at all
        # once the constant was emptied (rules/verification.md §8). The
        # executors that dispatch are the engines (rules/composition.md §3),
        # and the engines directory is the pin `TestEngineExecutorIsRejected`
        # already holds — so an engine added there without being added to
        # the constant fails here, by name.
        engines = sorted(
            path.name
            for path in (ROOT / "skills" / "engines").iterdir()
            if path.is_dir()
        )
        self.assertEqual(engines, sorted(tickets_mod.DISPATCHING_EXECUTORS))
        self.assertIn("orch-frontier", engines)  # the friction's own lane
        for executor in engines:
            with self.subTest(executor), tempfile.TemporaryDirectory() as tmp:
                packet = self.packet_for(
                    Path(tmp), CLAIMED_TICKET.replace("executor: orch-tdd", f"executor: {executor}")
                )
                self.assertEqual("agent-a", packet["assigned_name"])
                # backticked, because the fixture's own paths carry the name
                # as a substring: an assertion on the bare word passes on a
                # host whose worktree happens to be called agent-anything
                self.assertIn("assigned name is `agent-a`", packet["prompt"])
                # and the two identifiers are distinguishable in the prompt:
                # one is what this child answers to, one is who it answers
                self.assertIn("reply_to: main", packet["prompt"])

    def test_only_a_dispatching_executor_is_told_the_name_becomes_a_reply_to(self):
        # The fixture's executor is `orch-tdd`, which dispatches nothing. It is
        # still told its own name — every child may have to record under it —
        # so what separates it from the case above is the second sentence, not
        # the first: it is not told the name becomes its children's `reply_to`.
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.packet_for(Path(tmp), CLAIMED_TICKET)
            self.assertEqual("agent-a", packet["assigned_name"])
            self.assertIn("assigned name is `agent-a`", packet["prompt"])
            self.assertNotIn("as that child's `reply_to`", packet["prompt"])

    def test_an_unclaimed_packet_is_refused_before_dispatch(self):

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_packet_repo(
                tmp, FULL_TICKET.replace("status: claimed", "status: ready").replace("executor: orch-tdd", "executor: orch-frontier")
            )
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("not claimed", payload["error"])


class TestPacketUsageHasOneOwner(unittest.TestCase):
    """`tickets.py help` and the `packet` error path advertise one flag set.

    They diverged by `[--by <name>]` for a whole run: the error path took the
    new flag and the help table, a hand-built copy of the same sentence, did
    not. Nothing failed, because nothing compared them.
    """

    def test_the_help_table_takes_the_packet_usage_by_reference(self):
        from scripts import tickets_commands, tickets_packet

        self.assertIn("[--by <name>]", tickets_packet.PACKET_USAGE)
        self.assertEqual(
            tickets_packet.PACKET_USAGE, tickets_commands.SUBCOMMAND_USAGE["packet"]
        )


class TestPacketOmitsTheWorkspaceStepForATicketThatWritesOnlyTickets(unittest.TestCase):
    """Friction 2026-08-16T09:40: a packet told a read-only lane to run
    `workspace.py start` as its first act, so a worktree was created that
    nothing writes to. An item whose scope is empty writes only its own
    ticket sections, which live in the sink — no workspace holds them."""

    def packet_for(self, tmp: Path, body: str):
        make_packet_repo(tmp, body)
        return run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]

    def test_an_empty_scope_omits_the_packet_establishment_step_entirely(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.packet_for(
                Path(tmp), ISOLATED_TICKET.replace("write_scope: scratch/t1.txt", "write_scope: []")
            )
            self.assertEqual([], establishment_lines(packet["prompt"]))
            self.assertNotIn("workspace.py", packet["prompt"])
            # the declaration itself is not rewritten: what the cut said
            # stands, and `workspace.py check` grades the same field
            self.assertEqual("required", packet["isolation"])

    def test_isolation_none_omits_the_packet_establishment_step(self):
        """The other half of the same condition, pinned under this oracle:
        an item that declares no workspace of its own is never told to
        establish one. `test_a_scope_a_grant_widened...` below is what shows
        the check can fail — same class, same call, one line emitted."""

        with tempfile.TemporaryDirectory() as tmp:
            packet = self.packet_for(Path(tmp), UNISOLATED_TICKET)
            self.assertEqual([], establishment_lines(packet["prompt"]))
            self.assertNotIn("workspace.py", packet["prompt"])

    def test_a_scope_a_grant_widened_earns_the_packet_establishment_step_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = self.packet_for(
                Path(tmp),
                ISOLATED_TICKET.replace(
                    "write_scope: scratch/t1.txt",
                    "write_scope: []\ngranted_scope: [scripts/a.py]",
                ),
            )
            self.assertEqual(1, len(establishment_lines(packet["prompt"])))
