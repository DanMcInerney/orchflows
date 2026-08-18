"""Behavioral ticket regression cases."""

from .lifecycle_validation import *  # noqa: F401,F403

class TestPacket(unittest.TestCase):
    """`packet` is the by-reference dispatch of contracts/work-item.md: the
    dispatcher gets a path and a refusal check, never the ticket body."""

    def make(self, tmp: Path, body: str = FULL_TICKET) -> Path:
        (tmp / ".git").mkdir()
        run_dir = use_sink(tmp) / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        path = run_dir / "T1.md"
        path.write_text(body, encoding="utf-8")
        return path

    def test_complete_ticket_yields_an_absolute_path_and_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ticket_path = self.make(tmp)
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            self.assertEqual(str(ticket_path.resolve()), packet["path"])
            self.assertTrue(Path(packet["path"]).is_absolute())
            self.assertEqual("orch-tdd", packet["executor"])
            self.assertEqual("orch-code-pack", packet["pack"])
            # contracts/work-item.md: absent `independence` reads `checker`.
            self.assertEqual("checker", packet["independence"])
            self.assertIn(packet["path"], packet["prompt"])
            self.assertIn("orch-tdd", packet["prompt"])
            self.assertIn("reply_to: main", packet["prompt"])

    def test_workspace_rides_the_prompt_only_when_supplied(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            bare = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            self.assertIsNone(bare["workspace"])
            self.assertNotIn("Workspace:", bare["prompt"])
            with_ws = run_cmd(
                tmp, "packet", "testrun", "T1", "--reply-to", "main", "--workspace", "/wt/a"
            )["packet"]
            self.assertEqual("/wt/a", with_ws["workspace"])
            self.assertIn("Workspace: /wt/a", with_ws["prompt"])

    def test_missing_body_section_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            trimmed = FULL_TICKET.split("## Return fields")[0]
            self.make(tmp, trimmed)
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("return_contract (## Return fields)", payload["error"])
            self.assertNotIn("packet", payload)

    def test_missing_frontmatter_part_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace("bound: 30m\n", ""))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("bounds (bound)", payload["error"])

    def test_reply_to_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            payload = run_cmd(tmp, "packet", "testrun", "T1")
            self.assertIn("reply_to (--reply-to)", payload["error"])

    def test_empty_write_scope_is_complete_authority(self):
        """A read-only lane's grant is exactly nothing outside its own
        ticket sections: `write_scope: []` is a complete packet, and only
        an absent key leaves authority missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace("write_scope: scratch/t1.txt\n", "write_scope: []\n"))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("packet", payload)
            self.assertNotIn("error", payload)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace("write_scope: scratch/t1.txt\n", ""))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("authority (write_scope)", payload["error"])

    def test_criterion_without_oracle_class_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace(" oracle_class: deterministic.", ""))
            payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("oracle_class", payload["error"])

    def test_a_script_executor_is_run_rather_than_applied(self):
        """contracts/work-item.md Executor form: `executor: script:<path>` names a tested
        script -- the ladder's floor as a node. The packet says to run it,
        never to apply a skill: a node with no model in it is the cheapest
        rung there is, and reading it as a skill name would spend one."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ticket_path = self.make(
                tmp, FULL_TICKET.replace("executor: orch-tdd", "executor: script:tools/measure.py")
            )
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            self.assertEqual("script:tools/measure.py", packet["executor"])
            self.assertEqual("tools/measure.py", packet["script"])
            self.assertNotIn("Apply skill", packet["prompt"])
            self.assertIn("tools/measure.py", packet["prompt"])
            # the ticket path is the argument, and stdout is the result
            self.assertIn(str(ticket_path.resolve()), packet["prompt"])
            self.assertIn("## Result", packet["prompt"])

    def test_a_skill_executor_still_reads_as_a_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            self.assertIsNone(packet["script"])
            self.assertIn("Apply skill orch-tdd", packet["prompt"])

    def test_a_loop_packet_carries_its_body_done_check_and_bound(self):
        """docs/vocabulary.md `combinator`: a loop is a ticket whose sections hold the
        body, the done-check and the bound. The packet has to name all
        three, because a loop dispatched without its done-check runs until
        its bound however early it was actually done."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp, FULL_TICKET.replace("executor: orch-tdd", "executor: orch-loop"))
            packet = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main")["packet"]
            prompt = packet["prompt"]
            self.assertIn("Apply skill orch-loop", prompt)
            # The sentence itself, not the two headings: a prompt that
            # merely names `## Objective` and `## Completion test` carries
            # them as words, and only this clause binds each to its role.
            self.assertIn(
                "This is a loop ticket: the body of each fresh-context pass "
                "is `## Objective`, the done-check every pass is graded "
                "against is `## Completion test`, and the bound on the "
                "iterations is 30m.",
                prompt,
            )
            self.assertIn("whichever comes first", prompt)

    def test_a_ticket_that_appears_after_an_earlier_read_is_ordinary(self):
        """orch-frontier's event rule: a new ticket file is an event, and the
        support for it is that every call rescans. Nothing is cached
        between calls, so the second `ready` sees what the first could
        not."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            first = run_cmd(tmp, "ready", "--run", "testrun")["ready"]
            self.assertEqual(["T1"], [item["id"] for item in first])
            newcomer = sink_root() / "tickets" / "testrun" / "T2.md"
            newcomer.write_text(FULL_TICKET.replace("id: T1", "id: T2"), encoding="utf-8")
            second = run_cmd(tmp, "ready", "--run", "testrun")["ready"]
            self.assertEqual(["T1", "T2"], sorted(item["id"] for item in second))
            packet = run_cmd(tmp, "packet", "testrun", "T2", "--reply-to", "main")
            self.assertNotIn("error", packet)
            self.assertEqual("T2", packet["packet"]["id"])

    def test_unknown_ticket_and_an_empty_sink_are_errors_not_crashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.make(tmp)
            self.assertIn("ticket not found", run_cmd(tmp, "packet", "testrun", "T9", "--reply-to", "main")["error"])
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            result = run_full(tmp, "packet", "testrun", "T1", "--reply-to", "main")
            # an error payload, carried out to the caller's exit code
            self.assertEqual(1, result.returncode)
            self.assertIn("ticket not found", json.loads(result.stdout)["error"])


