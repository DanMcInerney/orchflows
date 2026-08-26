"""Behavioral ticket regression cases."""

from .packet_core import *  # noqa: F401,F403

class TestResultWorktreeCrossing(unittest.TestCase):
    """contracts/work-item.md: one run's tickets have one path, identical
    from every executor workspace. The executor files its result there from
    inside its own worktree, reading its body from that worktree."""

    def test_result_from_a_worktree_lands_in_the_main_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            body = worktree / "result-body.md"
            body.write_text("Landed at the main root.\n", encoding="utf-8")
            payload = run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "Result", "--file", str(body),
            )
            self.assertEqual("Result", payload["result"]["section"])
            self.assertEqual(
                str((run_dir / "T1.md").resolve()), payload["result"]["path"]
            )
            self.assertIn(
                "## Result\n\nLanded at the main root.\n",
                (run_dir / "T1.md").read_text(encoding="utf-8"),
            )
            # nothing was created in the worktree: the ticket tree is the
            # main checkout's alone
            self.assertFalse((worktree / ".orch").exists())

    def test_text_form_writes_the_same_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "verification", "--text", "1. PASS.",
            )
            self.assertEqual("Verification", payload["result"]["section"])
            self.assertIn(
                "## Verification\n\n1. PASS.\n",
                (run_dir / "T1.md").read_text(encoding="utf-8"),
            )


def frontmatter_of(path: Path) -> str:
    return path.read_text(encoding="utf-8").split("---\n", 2)[1]


class TestResultClosedSet(unittest.TestCase):
    """contracts/work-item.md names exactly what an executor writes."""

    def test_the_writable_set_is_the_contracts_five(self):
        # six including optional Context; the method name is pinned by
        # tests/serial_compat_manifest.json, which the join regenerates once
        self.assertEqual(
            ("Result", "Verification", "Feedback", "Risks", "Context", "Handoff"),
            tickets_mod.EXECUTOR_SECTIONS,
        )

    def test_every_reserved_section_round_trips(self):
        for name in tickets_mod.EXECUTOR_SECTIONS:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
                payload = run_cmd(
                    worktree, "result", "testrun", "T1",
                    "--section", name, "--text",
                    "- state: body for Context" if name == "Context" else f"body for {name}",
                )
                self.assertEqual(name, payload["result"]["section"], name)
                text = (run_dir / "T1.md").read_text(encoding="utf-8")
                expected = "- state: body for Context" if name == "Context" else f"body for {name}"
                self.assertEqual(expected, tickets_mod._sections(text)[name])

    def test_a_cut_time_section_is_refused_and_the_set_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            payload = run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "Objective", "--text", "hijacked",
            )
            self.assertIn("Objective", payload["error"])
            for name in tickets_mod.EXECUTOR_SECTIONS:
                self.assertIn(name, payload["error"])
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))


class TestContextFilingContract(unittest.TestCase):
    def test_context_accepts_one_to_five_state_or_watch_bullets(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            body = "\n".join((
                "- state: the decision is settled",
                "- watch: rerun the exact check after a schema change",
                "- state: artifact sha256:abc is the landed identity",
                "- watch: upstream may invalidate the identity",
                "- state: callers may rely on omission when absent",
            ))
            payload = run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "Context", "--text", body,
            )
            self.assertEqual("Context", payload["result"]["section"])
            self.assertEqual(body, tickets_mod._sections(
                (run_dir / "T1.md").read_text(encoding="utf-8")
            )["Context"])

    def test_every_malformed_context_is_refused_without_changing_bytes(self):
        malformed = (
            "",
            "- state:",
            "- watch:   ",
            "- State: wrong case",
            "- note: wrong label",
            "  - state: nested",
            "state: not a bullet",
            "- state: one\ncontinuation prose",
            "- state: one\n\n- watch: two",
            "\n".join(f"- state: conclusion {number}" for number in range(6)),
        )
        for body in malformed:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
                ticket = run_dir / "T1.md"
                before = ticket.read_bytes()
                payload = run_cmd(
                    worktree, "result", "testrun", "T1",
                    "--section", "Context", "--text", body,
                )
                self.assertIn("Context", payload["error"])
                self.assertEqual(before, ticket.read_bytes())

    def test_append_validates_the_combined_context_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            first = "\n".join(f"- state: conclusion {number}" for number in range(4))
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Context", "--text", first)
            accepted = run_cmd(
                worktree, "result", "testrun", "T1", "--section", "Context",
                "--text", "- watch: fifth conclusion", "--append",
            )
            self.assertEqual("append", accepted["result"]["mode"])
            before = ticket.read_bytes()
            refused = run_cmd(
                worktree, "result", "testrun", "T1", "--section", "Context",
                "--text", "- state: sixth conclusion", "--append",
            )
            self.assertIn("one to five", refused["error"])
            self.assertEqual(before, ticket.read_bytes())

    def test_context_is_the_only_successor_digest_filing_channel(self):
        self.assertFalse(hasattr(tickets_mod, "LEGACY_EXECUTOR_SECTIONS"))
        self.assertFalse(hasattr(tickets_mod, "FILEABLE_EXECUTOR_SECTIONS"))
        self.assertNotIn("Carry", tickets_mod.EXECUTOR_SECTIONS_BY_KEY.values())
        self.assertNotIn("Carry", tickets_mod.SECTION_ORDER)
        self.assertNotIn("Carry", tickets_mod.OPTIONAL_SECTIONS)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            before = ticket.read_bytes()
            refused = run_cmd(
                worktree, "result", "testrun", "T1", "--section", "Carry",
                "--text", "not a successor digest",
            )
            self.assertIn("not one of", refused["error"])
            self.assertEqual(before, ticket.read_bytes())


class TestResultBodySource(unittest.TestCase):
    def test_both_file_and_text_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            body = worktree / "body.md"
            body.write_text("from a file\n", encoding="utf-8")
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            result = run_main(
                worktree, "result", "testrun", "T1", "--section", "Result",
                "--file", str(body), "--text", "from a string",
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("error", json.loads(result.stdout))
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_neither_file_nor_text_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            result = run_main(worktree, "result", "testrun", "T1", "--section", "Result")
            self.assertEqual(1, result.returncode)
            self.assertIn("error", json.loads(result.stdout))
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_an_unreadable_body_file_is_an_error_not_a_traceback(self):
        """A body path that exists and cannot be read, which is what this
        test's name claims and what an absent path is not.

        The absent path this carried until now takes the same handler, so
        the case that names the handler graded only ``FileNotFoundError``:
        a body file that is there and unreadable -- the reason the read is
        wrapped at all -- was never passed. Two shapes, both portable:
        a directory where a file is expected (``IsADirectoryError`` on
        POSIX, ``PermissionError`` on Windows -- ``chmod 000`` is neither,
        and does not bite as root), and a read that raises for that path
        alone. The absent path stays as a third case, now beside the two.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            a_directory = worktree / "body-that-is-a-directory.md"
            a_directory.mkdir()
            present = worktree / "present-but-unreadable.md"
            present.write_text("bytes no reader reaches\n", encoding="utf-8")

            for label, path, raiser in (
                ("a directory where a file is expected", a_directory, None),
                ("a present file whose read raises", present, PermissionError),
                ("an absent path", worktree / "absent.md", None),
            ):
                with self.subTest(label):
                    with refusing_to_read(path, raiser):
                        result = run_main(
                            worktree, "result", "testrun", "T1",
                            "--section", "Result", "--file", str(path),
                        )
                    self.assertEqual(1, result.returncode, result.stdout)
                    error = json.loads(result.stdout)["error"]
                    # the handler's own words, not a traceback rendered by
                    # `main`'s catch-all: with the handler gone this reads
                    # the bare OSError instead
                    self.assertIn("unreadable body file", error, error)


class TestResultRefusesTerminalStatus(unittest.TestCase):
    """Criterion 4's refusal half: terminal status is the join's alone
    (contracts/work-item.md:31-33), so `result` writes no frontmatter."""

    def test_a_status_flag_is_refused_and_names_set_status_and_the_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            result = run_main(
                worktree, "result", "testrun", "T1", "--section", "Result",
                "--text", "done", "--status", "complete",
            )
            self.assertEqual(1, result.returncode)
            payload = json.loads(result.stdout)
            self.assertIn("--status", payload["error"])
            self.assertIn("set-status", payload["error"])
            self.assertIn("orch-integrate", payload["error"])
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_any_unrecognized_flag_is_refused_the_same_way(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            payload = run_cmd(
                worktree, "result", "testrun", "T1", "--section", "Result",
                "--text", "done", "--claimed-by", "someone",
            )
            self.assertIn("--claimed-by", payload["error"])
            self.assertIn("set-status", payload["error"])

    def test_frontmatter_is_byte_unchanged_after_writing_every_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            before = frontmatter_of(ticket)
            for name in tickets_mod.EXECUTOR_SECTIONS:
                run_cmd(
                    worktree, "result", "testrun", "T1",
                    "--section", name, "--text",
                    "- state: body for Context" if name == "Context" else f"body for {name}",
                )
            self.assertEqual(before, frontmatter_of(ticket))
            self.assertIn("status: claimed", ticket.read_text(encoding="utf-8"))

    def test_a_heading_shaped_frontmatter_line_is_not_a_section_boundary(self):
        # A wrapped frontmatter value can begin a line with "## ". Treating it
        # as a heading would put the writer inside frontmatter the join owns.
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
            before = frontmatter_of(ticket)
            run_cmd(
                worktree, "result", "testrun", "T1", "--section", "Risks", "--text", "[]",
            )
            self.assertEqual(before, frontmatter_of(ticket))
            self.assertEqual("[]", tickets_mod._sections(
                ticket.read_text(encoding="utf-8").split("---\n", 2)[2]
            )["Risks"])

    def test_a_fenced_heading_is_not_a_section_boundary(self):
        # Every deliverable in this repository is markdown with "## "
        # headings, and executors quote them at length. A heading inside a
        # fence is quoted content: ending the replaced span there deletes
        # the opening fence, orphans the closing one, and promotes the
        # quotation to a second heading that `_sections` then resolves
        # last-writer-wins -- silently reshaping sections the write never
        # named. Both fence characters, and an info string on the opener.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ticket = run_dir / "T1.md"
            ticket.write_text(
                ticket.read_text(encoding="utf-8")
                + "\n## Result\n\nOLD BODY\n\n"
                + "```markdown\n## Objective\nquoted heading\n```\n\n"
                + "tail prose\n\n"
                + "## Feedback\n\n~~~\n## Handoff\nfenced handoff\n~~~\n\n"
                + "## Risks\n\n[]\n",
                encoding="utf-8",
            )
            run_cmd(
                worktree, "result", "testrun", "T1",
                "--section", "Result", "--text", "REPLACED", "--replace",
            )
            text = ticket.read_text(encoding="utf-8")
            sections = tickets_mod._sections(text.split("---\n", 2)[2])
            # The quotation stayed quoted: no second Objective, no orphan.
            self.assertEqual("Test ticket.", sections["Objective"])
            self.assertNotIn("quoted heading", text)
            self.assertNotIn("```", text)
            # The replaced span ran to the next real heading, and stopped.
            self.assertEqual("REPLACED", sections["Result"])
            self.assertIn("fenced handoff", sections["Feedback"])
            self.assertNotIn("Handoff", sections)
            self.assertEqual("[]", sections["Risks"])


class TestResultScriptContract(unittest.TestCase):
    def test_success_and_failure_each_print_one_json_document(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, _run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            ok = run_full(
                worktree, "result", "testrun", "T1", "--section", "Result", "--text", "ok",
            )
            self.assertEqual(0, ok.returncode)
            self.assertIn("result", json.loads(ok.stdout))
            self.assertEqual(1, len(ok.stdout.strip().splitlines()))
            bad = run_full(
                worktree, "result", "testrun", "T9", "--section", "Result", "--text", "ok",
            )
            self.assertEqual(1, bad.returncode)
            self.assertIn("ticket not found", json.loads(bad.stdout)["error"])
            self.assertEqual(1, len(bad.stdout.strip().splitlines()))

    def test_result_outside_a_repo_still_reaches_the_sink(self):
        """A result is user-scope state, so the cwd being outside a checkout
        no longer decides anything: the ticket is found and written."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_tickets(
                use_sink(tmp) / "tickets" / "testrun", {"T1": ("claimed", "[]")}
            )
            bare = tmp / "no-repo-here"
            bare.mkdir()
            result = run_full(
                bare, "result", "testrun", "T1", "--section", "Result", "--text", "x"
            )
            self.assertEqual(0, result.returncode)
            payload = json.loads(result.stdout)
            self.assertNotIn("error", payload)
            self.assertIn(
                "## Result\n\nx\n", (run_dir / "T1.md").read_text(encoding="utf-8")
            )


def headings_of(text: str) -> list:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


class TestResultSectionOrder(unittest.TestCase):
    """A created section takes its place in the order contracts/work-item.md
    states. The sparse `TICKET` fixture is the one that can tell the
    difference: on a fuller ticket, blind appending is right by accident."""

    def test_a_created_section_lands_in_contract_order_not_append_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Feedback", "--text", "[]")
            run_cmd(worktree, "result", "testrun", "T1", "--section", "Result", "--text", "did it")
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertEqual(["Objective", "Result", "Feedback"], headings_of(text))
            self.assertEqual("did it", tickets_mod._sections(text)["Result"])
            self.assertEqual("[]", tickets_mod._sections(text)["Feedback"])

    def test_handoff_lands_last_however_the_sections_arrive(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for name in ("Handoff", "Context", "Risks", "Verification"):
                body = "- state: Context" if name == "Context" else name
                run_cmd(worktree, "result", "testrun", "T1", "--section", name, "--text", body)
            self.assertEqual(
                ["Objective", "Verification", "Risks", "Context", "Handoff"],
                headings_of((run_dir / "T1.md").read_text(encoding="utf-8")),
            )
