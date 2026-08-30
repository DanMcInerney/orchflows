"""Behavioral ticket regression cases."""

from .common import *  # noqa: F401,F403

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
            for argv in (["--help"], ["set-status", "--help"], ["run-state", "--help"]):
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
