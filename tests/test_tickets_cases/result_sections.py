"""Behavioral ticket regression cases."""

from .result_crossing import *  # noqa: F401,F403
from scripts import tickets_format, tickets_markdown, tickets_packet, tickets_result
from scripts.tickets_dispatch import _dispatch
from tests.test_tickets_issue_cases.generation_lifecycle import snapshot

CRITERION = "holds | oracle: `true` | oracle_class: deterministic | provenance: authored-here"

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


class SentinelIsNotContentTest(unittest.TestCase):
    """The placeholder a generator writes into a section it then protects.

    Five refusal round-trips across three projects in one cycle, all one
    shape: the generator prefills `## Risks` with the empty-collection
    marker, the sealed (v2) filing law makes an executor-owned section
    append-only, and the executor's first real content is then refused --
    `--replace` outright, and `--append` by succeeding and leaving a
    section that reads `[]` above the risk it just listed. The packet said
    the marker fills only an *empty* section while the API declined to
    treat its own marker as empty.

    One sentence removes both faces: the sentinel is not content, so the
    first real write consumes it whatever flag carries it. `result_sections
    .ResultOverwriteTest` already held exactly that for the bare write; the
    law here is that same one, told to the two flags that carry a write
    past that guard. The comparison is byte equality against the single
    constant, so a near miss is content and keeps every protection -- which
    is what makes the trap unconstructible rather than merely narrower.
    """

    CONTENT = "a real risk the executor found"

    def sealed(self, directory):
        """One sealed, claimed v2 ticket in `directory`'s sink."""

        run_dir = Path(directory) / "tickets" / "run"
        run_dir.mkdir(parents=True)
        for ticket_id, value in snapshot().items():
            (run_dir / f"{ticket_id}.md").write_text(value, encoding="utf-8")
        drafted = _dispatch(["draft-validate", "run", "00-root"])
        _dispatch(["seal", "run", "00-root", "--cut-generation",
                   drafted["draft_validation"]["cut_generation"]])
        _dispatch(["claim", "run", "00-root.01", "--by", "worker"])
        return run_dir / "00-root.01.md"

    def body(self, ticket, section="Risks"):
        return tickets_format._sections(ticket.read_text(encoding="utf-8"))[section]

    def test_the_generator_prefills_the_one_sentinel_the_filing_law_names(self):
        """The two ends of the trap, pinned to one constant.

        The generators are not this module's to change, so nothing but this
        stops `new` from prefilling a marker the filing law would go back to
        reading as content -- which is the trap, rebuilt from the other end.

        The executor is stated with the pack and isolation its admission
        requires, so the case fails on the prefill it grades rather than on
        an emission `new` declined for an unrelated reason.
        """

        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                self.assertNotIn("error", _dispatch([
                    "new", "run", "T1", "--executor", "orch-tdd",
                    "--pack", "orch-code-pack", "--isolation", "required",
                    "--objective", "deliver", "--criterion", CRITERION,
                ]))
                sections = tickets_format._sections(
                    (Path(directory) / "tickets" / "run" / "T1.md").read_text(encoding="utf-8")
                )
                for name in ("Feedback", "Risks"):
                    with self.subTest(name):
                        self.assertEqual(tickets_markdown.SECTION_SENTINEL, sections[name])

    def test_the_first_real_write_consumes_the_sentinel_under_every_flag(self):
        """No flag, `--append`, `--replace`: one law, and no round-trip.

        `--append` is the flag the packet recommends and the one that used
        to succeed dishonestly, so the assertion is equality rather than
        membership: nothing of the marker survives above the content. The
        reported mode is `write` throughout, because that is what happened
        -- there was nothing to append to and nothing real to replace.
        """

        for flag in ((), ("--append",), ("--replace",)):
            with self.subTest(flag=" ".join(flag) or "no flag"):
                with tempfile.TemporaryDirectory() as directory:
                    with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                        ticket = self.sealed(directory)
                        written = _dispatch([
                            "result", "run", "00-root.01", "--section", "Risks",
                            "--text", self.CONTENT, *flag,
                        ])
                        self.assertNotIn("error", written)
                        self.assertEqual("write", written["result"]["mode"])
                        self.assertEqual(self.CONTENT, self.body(ticket))

    def test_a_section_holding_real_content_keeps_every_protection(self):
        """The exception composes with the guards rather than widening them.

        checker-c06 proved both directions live: `--append` is lawful, and
        a non-append write onto existing content is refused. Under a seal
        `--replace` is refused too. All three still hold once the section
        is real, which is the half a looser sentinel test cannot see.
        """

        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                ticket = self.sealed(directory)
                _dispatch(["result", "run", "00-root.01", "--section", "Risks",
                           "--text", self.CONTENT])
                refused = _dispatch(["result", "run", "00-root.01", "--section", "Risks",
                                     "--text", "second", "--replace"])
                self.assertIn("append-only", refused["error"])
                bare = _dispatch(["result", "run", "00-root.01", "--section", "Risks",
                                  "--text", "second"])
                self.assertIn("already carries content", bare["error"])
                appended = _dispatch(["result", "run", "00-root.01", "--section", "Risks",
                                      "--text", "second", "--append"])
                self.assertNotIn("error", appended)
                self.assertEqual(f"{self.CONTENT}\n\nsecond", self.body(ticket))

    def test_an_empty_section_is_not_the_sentinel_and_stays_append_only(self):
        """`exactly when`: the exception is the marker, not emptiness.

        A guard that asked "is there anything worth protecting" rather than
        "are these the sentinel's bytes" would open `--replace` on every
        section a cut leaves blank. `--append` is the lawful path there,
        so closing this costs the caller nothing.
        """

        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                ticket = self.sealed(directory)
                self.assertEqual("", self.body(ticket, "Verification"))
                refused = _dispatch(["result", "run", "00-root.01", "--section",
                                     "Verification", "--text", "a pass", "--replace"])
                self.assertIn("append-only", refused["error"])
                self.assertNotIn("error", _dispatch([
                    "result", "run", "00-root.01", "--section", "Verification",
                    "--text", "a pass", "--append",
                ]))
                self.assertEqual("a pass", self.body(ticket, "Verification"))

    def test_only_the_exact_sentinel_bytes_are_the_exception(self):
        """A near miss is content, and a guard that fuzzed would hand
        `--replace` a section a writer had already written.

        Each body here is installed through the public verb -- the bare
        write the sentinel makes lawful -- so the panel proves the two
        halves in one pass: the marker is consumed, and what replaced it
        is protected immediately.
        """

        for near in ("[ ]", "[]]", "[[]]", "- []", "[] and one more", "None"):
            with self.subTest(body=near):
                with tempfile.TemporaryDirectory() as directory:
                    with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                        ticket = self.sealed(directory)
                        self.assertNotIn("error", _dispatch([
                            "result", "run", "00-root.01", "--section", "Risks",
                            "--text", near,
                        ]))
                        self.assertEqual(near, self.body(ticket))
                        refused = _dispatch(["result", "run", "00-root.01", "--section",
                                             "Risks", "--text", "later", "--replace"])
                        self.assertIn("append-only", refused["error"])
                        self.assertEqual(near, self.body(ticket))

    def test_the_help_states_the_append_only_law_the_command_enforces(self):
        """The usage line a refusal prints says what the refusal will do.

        The recorded round-trips read a usage line that named the two flags
        and neither the law governing them nor the marker that law excepts,
        so a caller learned both by being refused. The second half is the
        one that matters: the law has to travel on the refusals.
        """

        for phrase in ("append-only", tickets_markdown.SECTION_SENTINEL):
            with self.subTest(phrase):
                self.assertIn(phrase, tickets_result.RESULT_USAGE)
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                self.sealed(directory)
                refused = _dispatch(["result", "run", "00-root.01",
                                     "--section", "Risks"])["error"]
                self.assertIn(tickets_result.RESULT_USAGE, refused)

    def test_the_gate_emitter_prefills_that_same_one_constant(self):
        """The second emitter, which the live case above cannot reach.

        `GATE_EXECUTOR_SECTIONS` is the table every gate stub is built from,
        and `gate` refuses a sealed root, so the live seal the case above
        needs cannot be built over one. Unpinned, that table is the end the
        trap gets rebuilt from with no test watching. The cardinality is
        asserted too, so dropping a prefilled section fails here rather than
        passing on the survivor.
        """

        prefilled = {name: body
                     for name, body in tickets_packet.GATE_EXECUTOR_SECTIONS if body}
        self.assertEqual({"Feedback", "Risks"}, set(prefilled))
        for name, body in prefilled.items():
            with self.subTest(name):
                self.assertEqual(tickets_markdown.SECTION_SENTINEL, body)

    def test_a_writer_whose_own_content_is_the_sentinel_is_not_told_apart(self):
        """The boundary the byte comparison cannot see, graded not assumed.

        `[]` is the likeliest thing an executor with nothing to report
        writes into `## Feedback` itself. The guard compares bytes and not
        provenance, so that section reads as the cut's marker again: the
        write is taken as real (`append`), and the append-only seal then
        does not hold over it. Closing that needs provenance the ticket does
        not record, which is its own scope; pinned so it stays deliberate.
        """

        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                ticket = self.sealed(directory)
                written = _dispatch([
                    "result", "run", "00-root.01", "--section", "Verification",
                    "--text", tickets_markdown.SECTION_SENTINEL, "--append",
                ])
                self.assertEqual("append", written["result"]["mode"])
                self.assertEqual(tickets_markdown.SECTION_SENTINEL,
                                 self.body(ticket, "Verification"))
                again = _dispatch(["result", "run", "00-root.01", "--section",
                                   "Verification", "--text", "later", "--replace"])
                self.assertNotIn("error", again)
                self.assertEqual("write", again["result"]["mode"])
                self.assertEqual("later", self.body(ticket, "Verification"))

    def test_a_refusal_describes_the_section_it_actually_refused(self):
        """A refusal that misdescribes its section costs the round-trip it
        exists to save -- this module's subject, told to these flags.

        Two were live when the checker probed. The usage line and the seal's
        refusal both read "append-only once it carries content", telling a
        caller an empty section may be replaced; it may not. And the
        bare-write refusal offered `--replace` while, under a seal, the next
        guard prohibits exactly that -- a refusal naming a transition the
        table refuses, which is what `remedy_path` exists to prevent.
        """

        self.assertNotIn("once it carries content", tickets_result.RESULT_USAGE)
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                ticket = self.sealed(directory)
                self.assertEqual("", self.body(ticket, "Verification"))
                empty = _dispatch(["result", "run", "00-root.01", "--section",
                                   "Verification", "--text", "a pass",
                                   "--replace"])["error"]
                for untrue in ("once it carries content", "past it"):
                    with self.subTest(untrue):
                        self.assertNotIn(untrue, empty)
                _dispatch(["result", "run", "00-root.01", "--section", "Risks",
                           "--text", self.CONTENT])
                bare = _dispatch(["result", "run", "00-root.01", "--section",
                                  "Risks", "--text", "second"])["error"]
                self.assertIn("--append", bare)
                self.assertNotIn("--replace", bare)


# --- the run-state channel ---------------------------------------------------
