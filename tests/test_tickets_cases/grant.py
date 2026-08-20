"""Behavioral ticket regression cases."""

from .cli_help import *  # noqa: F401,F403

class TestGrant(unittest.TestCase):
    """`grant` is the caller-side scope widening, recorded on the ticket.

    Friction 2026-08-16T05:29: a lane found two files pinning a literal its
    objective moved, neither in `write_scope`; `amend` repairs body sections
    only and refuses a claimed ticket, so the widening was a direct sink edit
    plus a message — authority nothing at the join could read. A grant is
    bookkeeping of the `claimed_*` class (contracts/work-item.md): the caller
    who widened, when, and what — in frontmatter, never in a body section,
    and never by the ticket about itself.
    """

    def make(self, tmp: Path, body: str = CLAIMED_TICKET) -> Path:
        (tmp / ".git").mkdir()
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        path = run_dir / "T1.md"
        path.write_text(body, encoding="utf-8")
        return path

    def grant(self, tmp: Path, *args):
        return run_cmd(tmp, "grant", "testrun", "T1", *args)

    def test_a_grant_on_a_claimed_ticket_lands_in_frontmatter_bookkeeping(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.make(tmp)
            before = path.read_text(encoding="utf-8")
            payload = self.grant(
                tmp, "--write-scope", "scripts/a.py,tests/test_a.py", "--by", "main"
            )
            self.assertNotIn("error", payload)
            recorded = payload["grant"]
            self.assertEqual(["scripts/a.py", "tests/test_a.py"], recorded["granted_scope"])
            self.assertEqual("main", recorded["granted_by"])
            after = path.read_text(encoding="utf-8")
            front = tickets_mod._parse_frontmatter(after)
            self.assertEqual(["scripts/a.py", "tests/test_a.py"], front["granted_scope"])
            self.assertEqual("main", front["granted_by"])
            self.assertRegex(front["granted_at"], STAMP_RE)
            self.assertEqual(recorded["granted_at"], front["granted_at"])
            # bookkeeping, never a body section: nothing below the frontmatter
            # moved, and the cut's own `write_scope` line is untouched.
            self.assertEqual(tickets_mod._sections(before), tickets_mod._sections(after))
            self.assertIn("write_scope: scratch/t1.txt", after)

    def test_the_join_reads_the_scope_a_grant_widened(self):
        """The one reader: every consumer of a ticket's authority — this
        script's `packet`, and `workspace.py check` at the join, which reads
        the frontmatter through `_load_ticket` — sees cut scope plus grant."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.make(tmp)
            self.assertEqual(
                ["scratch/t1.txt"],
                tickets_mod.effective_write_scope(
                    tickets_mod._parse_frontmatter(path.read_text(encoding="utf-8"))
                ),
            )
            self.grant(tmp, "--write-scope", "scripts/a.py", "--by", "main")
            self.assertEqual(
                ["scratch/t1.txt", "scripts/a.py"],
                tickets_mod._load_ticket(path)["write_scope"],
            )

    def test_a_second_grant_appends_and_never_drops_the_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.make(tmp)
            self.grant(tmp, "--write-scope", "scripts/a.py", "--by", "main")
            payload = self.grant(
                tmp, "--write-scope", "scripts/a.py,docs/b.md", "--by", "other"
            )
            self.assertEqual(
                ["scripts/a.py", "docs/b.md"], payload["grant"]["granted_scope"]
            )
            front = tickets_mod._parse_frontmatter(path.read_text(encoding="utf-8"))
            # the path granted twice is carried once, and the second granter
            # is the one on record for the widening that just landed
            self.assertEqual(["scripts/a.py", "docs/b.md"], front["granted_scope"])
            self.assertEqual("other", front["granted_by"])

    def test_a_grant_on_an_unclaimed_ticket_is_refused_and_the_file_is_untouched(self):
        for status in ("ready", "pending", "complete"):
            with self.subTest(status), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                path = self.make(
                    Path(tmp), CLAIMED_TICKET.replace("status: claimed", f"status: {status}")
                )
                before = path.read_text(encoding="utf-8")
                payload = self.grant(tmp, "--write-scope", "scripts/a.py", "--by", "main")
                self.assertIn("error", payload)
                self.assertIn(status, payload["error"])
                self.assertEqual(before, path.read_text(encoding="utf-8"))

    def test_a_suspended_ticket_is_still_claimed_and_grantable(self):
        """contracts/work-item.md: a suspended ticket stays claimed, resumable
        from its `## Handoff` — and a handoff that names missing scope is the
        case a grant answers."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, CLAIMED_TICKET.replace("status: claimed", "status: suspended"))
            payload = self.grant(tmp, "--write-scope", "scripts/a.py", "--by", "main")
            self.assertNotIn("error", payload)

    def test_a_planned_v1_grant_refuses_to_invent_an_operation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            planned = CLAIMED_TICKET.replace(
                "status: claimed\n",
                "status: claimed\nadmission: v1:git:sha256:" + "a" * 64 + "\ncohort: v1:ticket:T1\nmutations: [change:scratch/t1.txt]\n",
            )
            path = self.make(tmp, planned)
            before = path.read_bytes()
            payload = self.grant(tmp, "--write-scope", "scripts/new.py", "--by", "main")
            self.assertIn("explicit mutation", payload["error"])
            self.assertIn("suspend", payload["error"].lower())
            self.assertIn("recut", payload["error"])
            self.assertEqual(before, path.read_bytes())

    def test_the_granting_caller_and_the_scope_are_both_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.make(tmp)
            missing_by = self.grant(tmp, "--write-scope", "scripts/a.py")
            self.assertIn("--by", missing_by["error"])
            missing_scope = self.grant(tmp, "--by", "main")
            self.assertIn("--write-scope", missing_scope["error"])
            self.assertNotIn("granted_scope", path.read_text(encoding="utf-8"))

    def test_a_grant_on_an_unknown_ticket_is_an_error_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            payload = self.grant(
                Path(tmp), "--write-scope", "scripts/a.py", "--by", "main"
            )
            self.assertNotIn("error", payload)
            missing = run_cmd(
                tmp, "grant", "testrun", "T9", "--write-scope", "a.py", "--by", "main"
            )
            self.assertIn("ticket not found", missing["error"])

    def test_grant_is_on_every_surface_a_reader_meets(self):
        self.assertIn("grant <run> <id>", tickets_mod.__doc__ or "")
        self.assertIn("grant", tickets_mod.SUBCOMMAND_USAGE)
        self.assertIn("grant", tickets_mod.SUBCOMMAND_SUMMARY)
        self.assertIn("grant", tickets_mod._dispatch([])["error"])


@unittest.skipUnless(git_available(), "git is not on PATH")
class TestGrantedScopeAtTheJoin(unittest.TestCase):
    """The grant is not read, it is graded: `workspace.py check` is what the
    join runs before a merge, and a path only the grant covers must pass it."""

    def test_check_passes_a_path_the_grant_covers_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as tmp:
            main, worktree, ticket, base = make_isolated_fixture(Path(tmp), ISOLATED_TICKET)
            started = run_argv(
                [sys.executable, str(WORKSPACE_PY), "start", "testrun", "T1"], worktree
            )
            self.assertEqual(0, started.returncode, started.stderr)
            check_argv = [
                sys.executable, str(WORKSPACE_PY), "check", "testrun", "T1",
                "--base", base,
            ]
            (worktree / "granted.txt").write_text("out of scope\n", encoding="utf-8")
            git_run(worktree, "add", "granted.txt")
            git_run(worktree, "commit", "--quiet", "-m", "not yet granted")
            breached = run_argv(check_argv, main)
            self.assertEqual(4, breached.returncode, breached.stdout + breached.stderr)
            self.assertEqual(["granted.txt"], json.loads(breached.stdout)["breaches"])

            granted = run_json(
                worktree, "grant", "testrun", "T1", "--write-scope", "granted.txt",
                "--by", "main",
            )
            self.assertNotIn("error", granted)
            passed = run_argv(check_argv, main)
            self.assertEqual(0, passed.returncode, passed.stdout + passed.stderr)
            self.assertEqual("pass", json.loads(passed.stdout)["check"]["verdict"])


class TestCheckedByVerb(unittest.TestCase):
    """`check` is the producer for contracts/work-item.md's `checked_by`.

    rules/verification.md §10's checker pass was read by three consumers --
    the contract's field, orch-critique's body and orch-integrate's name
    check -- and written by nothing, so the join could not tell a real
    checker pass from an executor's claim of one.
    """

    def make(self, tmp: Path, status: str = "claimed") -> Path:
        (tmp / ".git").mkdir()
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        path = run_dir / "T1.md"
        body = FULL_TICKET.replace("status: claimed", f"status: {status}")
        if status in ("claimed", "suspended"):
            body = body.replace(
                f"status: {status}\n", f"status: {status}\nclaimed_by: agent-a\n"
            )
        path.write_text(body, encoding="utf-8")
        return path

    def test_check_writes_checked_by_on_a_claimed_ticket(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.make(tmp)
            payload = run_cmd(tmp, "check", "testrun", "T1", "--by", "checker-a")
            self.assertNotIn("error", payload)
            self.assertEqual("checker-a", payload["check"]["checked_by"])
            self.assertEqual("T1", payload["check"]["id"])
            self.assertIn("checked_by: checker-a", path.read_text(encoding="utf-8"))

    def test_one_checker_identity_and_unique_gate_lenses(self):
        """A ticket has one checker identity; another review belongs to a
        distinctly named gate lens rather than overwriting that identity."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.make(tmp)
            first = run_cmd(tmp, "check", "testrun", "T1", "--by", "checker-a")
            self.assertNotIn("error", first)
            before = path.read_bytes()
            repeated = run_cmd(tmp, "check", "testrun", "T1", "--by", "checker-b")
            self.assertIn("already checked", repeated["error"])
            self.assertIn("checker-a", repeated["error"])
            self.assertEqual(before, path.read_bytes())

        self.assertEqual(
            ["code", "security"],
            tickets_mod._distinct_gate_lenses(["code", "security"]),
        )
        with self.assertRaisesRegex(ValueError, "distinct"):
            tickets_mod._distinct_gate_lenses(["code", "code"])
        with self.assertRaisesRegex(ValueError, "distinct"):
            tickets_mod._distinct_gate_lenses(["code", "Code"])

    def test_concurrent_checkers_cannot_replace_the_first_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.make(tmp)
            processes = [
                subprocess.Popen(
                    [sys.executable, str(TICKETS_PY), "check", "testrun", "T1",
                     "--by", checker],
                    cwd=str(tmp), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace",
                )
                for checker in ("checker-a", "checker-b")
            ]
            results = [process.communicate(timeout=20) + (process.returncode,)
                       for process in processes]
            self.assertEqual([0, 1], sorted(result[2] for result in results), results)
            data = tickets_mod._parse_frontmatter(path.read_text(encoding="utf-8"))
            self.assertIn(data["checked_by"], ("checker-a", "checker-b"))

    def test_check_is_refused_on_a_ticket_that_is_not_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            path = self.make(tmp, status="ready")
            payload = run_cmd(tmp, "check", "testrun", "T1", "--by", "checker-a")
            self.assertIn("not claimed", payload["error"])
            self.assertNotIn("checked_by", path.read_text(encoding="utf-8"))

    def test_check_requires_a_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            payload = run_cmd(tmp, "check", "testrun", "T1")
            self.assertIn("--by", payload["error"])

    def test_check_refuses_a_ticket_that_is_not_there(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            payload = run_cmd(tmp, "check", "testrun", "T9", "--by", "checker-a")
            self.assertIn("ticket not found", payload["error"])

    def test_check_is_reachable_and_documented_like_every_other_verb(self):
        self.assertIn("check", tickets_mod.SUBCOMMAND_USAGE)
        self.assertIn("check", tickets_mod.SUBCOMMAND_SUMMARY)
        self.assertIn("check", tickets_mod._dispatch([])["error"])


CLAIMED_ISOLATED_TICKET = ISOLATED_TICKET.replace(
    "claimed_by: legacy-agent", "claimed_by: agent-a"
)
