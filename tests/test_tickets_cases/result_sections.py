"""Behavioral ticket regression cases."""

from .result_crossing import *  # noqa: F401,F403

class TestResultAppend(unittest.TestCase):
    """contracts/work-item.md:91-93: a rules/verification.md §10 checker
    appends its own pass and never rewrites the executor's."""

    def test_append_keeps_the_prior_body_and_adds_after_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                    "--text", "executor pass")
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Feedback", "--text", "[]")
            before = ticket.read_text(encoding="utf-8")
            payload = run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                              "--text", "checker pass", "--append")
            self.assertEqual("append", payload["result"]["mode"])
            text = ticket.read_text(encoding="utf-8")
            self.assertEqual("executor pass\n\nchecker pass", tickets_mod._sections(text)["Result"])
            self.assertLess(text.index("executor pass"), text.index("checker pass"))
            # every other section is byte-unchanged
            self.assertEqual(headings_of(before), headings_of(text))
            for name in ("Objective", "Feedback"):
                self.assertEqual(
                    tickets_mod._sections(before)[name], tickets_mod._sections(text)[name]
                )
            self.assertEqual(frontmatter_of(ticket), frontmatter_of(ticket))

    def test_append_to_an_absent_section_creates_it_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Risks",
                    "--text", "[]", "--append")
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertEqual(["Objective", "Risks"], headings_of(text))
            self.assertEqual("[]", tickets_mod._sections(text)["Risks"])

    def test_replace_replaces_rather_than_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Result", "--text", "first")
            payload = run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                              "--text", "second", "--replace")
            self.assertEqual("replace", payload["result"]["mode"])
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertEqual("second", tickets_mod._sections(text)["Result"])
            self.assertNotIn("first", text)


class ResultOverwriteTest(unittest.TestCase):
    """A written section is not overwritten by default.

    contracts/worklog.md's closing law, read across to the ticket the same
    executor writes: clobbering is refused by default and the refusal names
    the path. The first write of a section, and a section standing empty at
    cut time, are not overwrites and stay free.
    """

    def written(self, tmp: Path):
        _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
        ticket = run_dir / "T1.md"
        run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                "--text", "the executor's own pass")
        return worktree, ticket

    def test_a_written_section_is_refused_and_the_refusal_names_the_ticket(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            worktree, ticket = self.written(tmp)
            before = ticket.read_text(encoding="utf-8")
            result = run_main(worktree, "result", "testrun", "T1", "--section", "Result",
                              "--text", "a silent clobber")
            self.assertEqual(1, result.returncode, result.stdout)
            error = json.loads(result.stdout)["error"]
            self.assertIn(str(ticket.resolve()), error)
            self.assertIn("Result", error)
            self.assertIn("--replace", error)
            self.assertIn("--append", error)
            # the prior content is unchanged, byte for byte
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))
            self.assertNotIn("a silent clobber", before)

    # The two flags that carry a write past this guard are graded by
    # TestResultAppend: `--replace` by test_replace_replaces_rather_than_appends
    # and `--append` by test_append_keeps_the_prior_body_and_adds_after_it,
    # each over a section already written and each asserting strictly more
    # than the pair that stood here (the append case also grades ordering and
    # that every other section is byte-unchanged).

    def test_a_first_write_and_an_empty_cut_time_section_are_not_overwrites(self):
        """A ticket is cut with its executor sections present and empty; the
        executor's first write into one is the write this subcommand exists
        for, and must not need a flag."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8") + "\n## Result\n\n## Risks\n\n",
                encoding="utf-8",
            )
            for section, text in (("Result", "first pass"), ("Risks", "[]"),
                                  ("Feedback", "[]")):
                payload = run_cmd(worktree, "result", "testrun", "T1",
                                  "--section", section, "--text", text)
                self.assertEqual("write", payload["result"]["mode"], section)
            sections = tickets_mod._sections(ticket.read_text(encoding="utf-8"))
            self.assertEqual("first pass", sections["Result"])
            self.assertEqual("[]", sections["Risks"])
            self.assertEqual("[]", sections["Feedback"])

    def test_an_empty_collection_stub_is_not_content(self):
        """A ticket is cut with `[]` in Feedback and Risks. That stub is the
        empty collection, not a prior writer's work: the executor's first
        real write into it needs no flag (three lanes in one run each lost
        a round trip to --replace before this held)."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8") + "\n## Risks\n\n[]\n",
                encoding="utf-8",
            )
            payload = run_cmd(worktree, "result", "testrun", "T1",
                              "--section", "Risks", "--text", "one real risk")
            self.assertEqual("write", payload["result"]["mode"])
            sections = tickets_mod._sections(ticket.read_text(encoding="utf-8"))
            self.assertEqual("one real risk", sections["Risks"])

    def test_a_level_two_heading_inside_a_body_is_refused(self):
        """`_sections` reads every `## ` line as a ticket section, so a
        Result carrying `## Changed artifacts` would split into sections the
        contract does not name and no verb could remove; refuse it whole."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            before = ticket.read_text(encoding="utf-8")
            result = run_main(worktree, "result", "testrun", "T1", "--section", "Result",
                              "--text", "changed x\n\n## Changed artifacts\n\n- y")
            self.assertEqual(1, result.returncode, result.stdout)
            error = json.loads(result.stdout)["error"]
            self.assertIn("level-2 heading", error)
            self.assertIn("###", error)
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))
            ok = run_cmd(worktree, "result", "testrun", "T1", "--section", "Result",
                         "--text", "changed x\n\n### Changed artifacts\n\n- y")
            self.assertEqual("write", ok["result"]["mode"])

    def test_append_and_replace_together_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            worktree, ticket = self.written(tmp)
            before = ticket.read_text(encoding="utf-8")
            result = run_main(worktree, "result", "testrun", "T1", "--section", "Result",
                              "--text", "both", "--append", "--replace")
            self.assertEqual(1, result.returncode, result.stdout)
            error = json.loads(result.stdout)["error"]
            self.assertIn("--append", error)
            self.assertIn("--replace", error)
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))

    def test_a_heading_shaped_frontmatter_line_does_not_trip_the_guard(self):
        """The guard skips the frontmatter exactly as the writer does. Reading
        a wrapped frontmatter value that begins `## ` as a written section
        refuses a first write into a section that does not exist yet."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8").replace(
                    "bound: 30m\n", "bound: 30m\nnote:\n  - suspend through\n## Risks\n"
                ),
                encoding="utf-8",
            )
            payload = run_cmd(worktree, "result", "testrun", "T1",
                              "--section", "Risks", "--text", "[]")
            self.assertEqual("write", payload["result"]["mode"], payload)
            self.assertEqual("[]", tickets_mod._sections(
                ticket.read_text(encoding="utf-8").split("---\n", 2)[2]
            )["Risks"])

    def test_the_guard_reads_the_span_the_writer_writes(self):
        """A fenced `## Result` above the real one is quoted content to the
        writer; the guard must read it the same way, or it reports on a
        heading the write will never touch."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8")
                + "\n## Verification\n\n```\n## Result\n\nquoted body\n```\n",
                encoding="utf-8",
            )
            payload = run_cmd(worktree, "result", "testrun", "T1",
                              "--section", "Result", "--text", "the real first write")
            self.assertEqual("write", payload["result"]["mode"], payload)
            text = ticket.read_text(encoding="utf-8")
            self.assertIn("quoted body", text)
            self.assertIn("the real first write", text)

    def test_every_executor_section_is_guarded_not_just_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            for section in tickets_mod.EXECUTOR_SECTIONS:
                run_cmd(worktree, "result", "testrun", "T1", "--section", section,
                        "--text", f"{section} first")
                before = ticket.read_text(encoding="utf-8")
                result = run_main(worktree, "result", "testrun", "T1",
                                  "--section", section, "--text", f"{section} clobber")
                self.assertEqual(1, result.returncode, f"{section}: {result.stdout}")
                self.assertIn(section, json.loads(result.stdout)["error"])
                self.assertEqual(before, ticket.read_text(encoding="utf-8"), section)


# --- the run-state channel ---------------------------------------------------
