"""Behavioral cases imported by the ``tests.test_tickets_issue`` seam."""

from .common import *  # noqa: F401,F403

def new_args(*extra) -> list:
    """`new` with the three parts every ticket needs, plus ``extra``."""

    return [
        "new", "testrun", "T1",
        "--executor", "orch-verify",
        "--objective", "the suite is green",
        "--criterion", GOOD_CRITERION,
        *extra,
    ]


class NewTest(unittest.TestCase):
    """`new` issues one ticket into the sink, in contract shape, refusing
    anything `ticket_defects` reports before it writes."""

    def ticket_path(self, sink: Path, ticket_id: str = "T1") -> Path:
        return sink / "tickets" / "testrun" / f"{ticket_id}.md"

    def test_a_criterion_naming_no_class_is_refused_and_nothing_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            payload = run_cmd(
                "new", "testrun", "T1", "--executor", "orch-verify",
                "--objective", "o", "--criterion", "x",
            )
            self.assertIn("error", payload)
            self.assertIn("oracle_class", payload["error"])
            self.assertFalse(self.ticket_path(sink).exists(), "a refused cut wrote")
            self.assertFalse((sink / "tickets" / "testrun").exists())

    def test_a_complete_cut_is_written_ready_and_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            payload = run_cmd(*new_args())
            self.assertNotIn("error", payload)
            written = self.ticket_path(sink)
            self.assertEqual(str(written), payload["new"]["path"])
            self.assertTrue(written.is_file())
            listed = run_cmd("list", "--run", "testrun")["tickets"]
            self.assertEqual(1, len(listed), listed)
            self.assertEqual("ready", listed[0]["status"])
            self.assertEqual("T1", listed[0]["id"])

    def test_what_new_writes_has_no_defects_of_its_own(self):
        """The cut is graded by the same function that grades every other
        ticket, so its own output cannot be off contract."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args("--write-scope", "scratch/a.txt", "--bound", "30m"))
            text = self.ticket_path(sink).read_text(encoding="utf-8")
            self.assertEqual([], tickets_mod.ticket_defects(text))

    def test_the_body_sections_are_in_the_contract_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args())
            text = self.ticket_path(sink).read_text(encoding="utf-8")
            found = [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]
            self.assertEqual(list(tickets_mod.REQUIRED_SECTIONS), found)

    def test_a_section_body_is_separated_from_its_heading(self):
        """The house shape every ticket in the sink is written in, and the one
        `result --section` writes back: a blank line under the heading."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args())
            text = self.ticket_path(sink).read_text(encoding="utf-8")
            self.assertIn("## Objective\n\nthe suite is green\n", text)
            self.assertIn("## Feedback\n\n[]\n", text)

    def test_feedback_and_risks_are_pre_filled_and_the_executor_sections_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args())
            body = tickets_mod._sections(self.ticket_path(sink).read_text(encoding="utf-8"))
            self.assertEqual("[]", body["Feedback"])
            self.assertEqual("[]", body["Risks"])
            self.assertEqual("", body["Result"])
            self.assertEqual("", body["Verification"])

    def test_a_dependency_makes_the_cut_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            payload = run_cmd(*new_args("--depends-on", "T0,T00"))
            self.assertEqual("pending", payload["new"]["status"])
            data = tickets_mod._parse_frontmatter(
                self.ticket_path(sink).read_text(encoding="utf-8")
            )
            self.assertEqual(["T0", "T00"], data["depends_on"])
            self.assertEqual("pending", data["status"])

    def test_the_optional_parts_land_where_the_contract_puts_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args(
                "--pack", "orch-code-pack",
                "--write-scope", "scripts/a.py,tests/test_a.py",
                "--bound", "40m",
                "--input", "contracts/work-item.md",
                "--input", "SPEC.md",
                "--excluded", "pushing, or forcing a push",
                "--profile", "orch-worker",
                "--independence", "gate",
                "--isolation", "required",
                "--return-fields", "status; the branch name",
            ))
            text = self.ticket_path(sink).read_text(encoding="utf-8")
            data = tickets_mod._parse_frontmatter(text)
            self.assertEqual("orch-code-pack", data["pack"])
            self.assertEqual(["scripts/a.py", "tests/test_a.py"], data["write_scope"])
            self.assertEqual("40m", data["bound"])
            self.assertEqual("orch-worker", data["profile"])
            self.assertEqual("gate", data["independence"])
            self.assertEqual("required", data["isolation"])
            # an excluded action carrying a comma is one action, not two
            self.assertEqual(["pushing, or forcing a push"], data["excluded_actions"])
            sections = tickets_mod._sections(text)
            self.assertIn("contracts/work-item.md", sections["Fixed inputs"])
            self.assertIn("SPEC.md", sections["Fixed inputs"])
            self.assertEqual("status; the branch name", sections["Return fields"])

    def test_the_cut_is_claimable_and_dispatchable(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            run_cmd(*new_args("--write-scope", "scratch/a.txt", "--bound", "30m"))
            ready = run_cmd("ready", "--run", "testrun")["ready"]
            self.assertEqual(["T1"], [item["id"] for item in ready])
            packet = run_cmd("packet", "testrun", "T1", "--reply-to", "main")
            self.assertNotIn("error", packet)
            self.assertEqual("orch-verify", packet["packet"]["executor"])
            claimed = run_cmd("claim", "testrun", "T1", "--by", "agent-a")
            self.assertEqual("agent-a", claimed["claimed"]["claimed_by"])

    def test_an_id_already_issued_is_refused_and_the_first_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_cmd(*new_args())
            before = self.ticket_path(sink).read_text(encoding="utf-8")
            payload = run_cmd(
                "new", "testrun", "T1", "--executor", "orch-tdd",
                "--objective", "something else", "--criterion", GOOD_CRITERION,
            )
            self.assertIn("error", payload)
            self.assertIn("T1", payload["error"])
            self.assertEqual(before, self.ticket_path(sink).read_text(encoding="utf-8"))

    def test_second_root_is_an_atomic_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            first = run_cmd(
                "new", "testrun", "R1", "--executor", "orch-decompose",
                "--objective", "deliver the first kind", "--criterion", GOOD_CRITERION,
                "--write-scope", "scratch/first.txt",
            )
            self.assertNotIn("error", first)
            run_dir = sink / "tickets" / "testrun"
            before = {path.name: path.read_bytes() for path in run_dir.glob("*.md")}
            second = run_cmd(
                "new", "testrun", "R2", "--executor", "orch-decompose",
                "--objective", "deliver another kind", "--criterion", GOOD_CRITERION,
                "--write-scope", "scratch/second.txt",
            )
            self.assertIn("one root", second["error"])
            self.assertIn("R1", second["error"])
            self.assertEqual(before, {
                path.name: path.read_bytes() for path in run_dir.glob("*.md")
            })

    def test_concurrent_root_creators_leave_exactly_one_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / ".git").mkdir()
            sink = use_sink(tmp)
            common = [
                "--executor", "orch-decompose", "--objective", "one kind",
                "--criterion", GOOD_CRITERION, "--write-scope", "scratch/out.txt",
            ]
            processes = [
                subprocess.Popen(
                    [sys.executable, str(TICKETS_PY), "new", "race-run", root, *common],
                    cwd=str(tmp), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace",
                )
                for root in ("R1", "R2")
            ]
            results = [process.communicate(timeout=20) + (process.returncode,)
                       for process in processes]
            self.assertEqual([0, 1], sorted(result[2] for result in results), results)
            run_dir = sink / "tickets" / "race-run"
            roots = [
                path for path in run_dir.glob("*.md")
                if tickets_mod._executor_of(tickets_mod._parse_frontmatter(
                    path.read_text(encoding="utf-8")
                )) == tickets_mod.ROOT_EXECUTOR
            ]
            self.assertEqual(1, len(roots), results)

    def test_new_reserves_every_gate_family_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            payload = run_cmd(
                "new", "testrun", "R.gate.repair", "--executor", "orch-repair",
                "--objective", "forge a gate", "--criterion", GOOD_CRITERION,
            )
            self.assertIn("reserved", payload["error"])
            self.assertFalse((sink / "tickets" / "testrun" / "R.gate.repair.md").exists())

    def test_new_and_instantiate_share_immutable_run_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            commit = "b" * 40
            (sink.parent / "receipt.json").write_text(
                json.dumps({"version": 4, "source_commit": commit}),
                encoding="utf-8",
            )
            self.assertNotIn("error", run_cmd(*new_args()))
            identity_path = sink / "runs" / "testrun" / "run.json"
            opened = identity_path.read_bytes()
            (sink.parent / "receipt.json").write_text(
                json.dumps({"version": 99, "source_commit": "c" * 40}),
                encoding="utf-8",
            )
            directory = make_template(tmp, {"A": stub("A"), "B": stub("B", "[A]")})
            appended = run_cmd(
                "instantiate", str(directory), "--run", "testrun",
                "--set", "target=scratch/x.txt",
            )
            self.assertNotIn("error", appended)
            self.assertEqual(opened, identity_path.read_bytes())
            (sink.parent / "receipt.json").write_text(
                json.dumps({"version": 4, "source_commit": commit}),
                encoding="utf-8",
            )

            separate = run_cmd(
                "instantiate", str(directory), "--run", "template-run",
                "--set", "target=scratch/x.txt",
            )
            self.assertNotIn("error", separate)
            instantiated = json.loads(
                (sink / "runs" / "template-run" / "run.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                {"receipt_version": 4, "source_commit": commit},
                instantiated["orchflows"],
            )

    def test_each_required_part_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            for flag in ("--executor", "--objective", "--criterion"):
                with self.subTest(flag):
                    args = [a for a in new_args()]
                    index = args.index(flag)
                    del args[index:index + 2]
                    payload = run_cmd(*args)
                    self.assertIn("error", payload)
                    self.assertIn(flag, payload["error"])

    def test_an_off_enum_independence_or_isolation_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            for flag, value in (("--independence", "solo"), ("--isolation", "maybe")):
                with self.subTest(flag):
                    payload = run_cmd(*new_args(flag, value))
                    self.assertIn("error", payload)
                    self.assertIn(value, payload["error"])

    def test_a_run_or_id_that_is_not_one_path_segment_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            use_sink(Path(tmp))
            for run, ticket_id in (("../escape", "T1"), ("testrun", "a/b")):
                with self.subTest(ticket_id):
                    payload = run_cmd(
                        "new", run, ticket_id, "--executor", "orch-verify",
                        "--objective", "o", "--criterion", GOOD_CRITERION,
                    )
                    self.assertIn("error", payload)

    def test_a_written_ticket_is_placed_by_file_after_the_same_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(GOOD_TICKET, encoding="utf-8")
            payload = run_cmd("new", "testrun", "--file", str(source))
            self.assertNotIn("error", payload)
            self.assertEqual(
                GOOD_TICKET, self.ticket_path(sink).read_text(encoding="utf-8")
            )

    def test_a_defective_file_is_refused_and_placed_nowhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(
                GOOD_TICKET.replace(" | oracle_class: deterministic", ""),
                encoding="utf-8",
            )
            payload = run_cmd("new", "testrun", "--file", str(source))
            self.assertIn("error", payload)
            self.assertIn("oracle_class", payload["error"])
            self.assertFalse(self.ticket_path(sink).exists())

    def test_a_file_whose_run_disagrees_with_the_argument_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(GOOD_TICKET, encoding="utf-8")
            payload = run_cmd("new", "otherrun", "--file", str(source))
            self.assertIn("error", payload)
            self.assertIn("testrun", payload["error"])
            self.assertFalse((sink / "tickets" / "otherrun" / "T1.md").exists())

    def test_the_id_may_be_stated_beside_the_file_when_the_two_agree(self):
        """`new <run> <id> --file <path>` is what a cutter reaches for.

        The id is in the file and in the dispatch that told the cutter to
        write it, and stating it twice is the ordinary spelling; refusing that
        line sent a cutter looking for a subcommand that does not exist.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(GOOD_TICKET, encoding="utf-8")
            payload = run_cmd("new", "testrun", "T1", "--file", str(source))
            self.assertNotIn("error", payload)
            self.assertEqual("T1", payload["new"]["id"])
            self.assertEqual(
                GOOD_TICKET, self.ticket_path(sink).read_text(encoding="utf-8")
            )

    def test_an_id_disagreeing_with_the_file_is_refused_and_placed_nowhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            source = tmp / "T1.md"
            source.write_text(GOOD_TICKET, encoding="utf-8")
            payload = run_cmd("new", "testrun", "T9", "--file", str(source))
            self.assertIn("error", payload)
            self.assertIn("T9", payload["error"])
            self.assertIn("T1", payload["error"])
            self.assertFalse(self.ticket_path(sink).exists())

    def test_the_exit_codes_are_the_script_s_own(self):
        """The process boundary: a payload carrying `error` exits 1, the cut
        exits 0, and both print one JSON document."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            good = run_full(tmp, *new_args())
            self.assertEqual(0, good.returncode, good.stdout)
            self.assertNotIn("error", json.loads(good.stdout))
            bad = run_full(
                tmp, "new", "testrun", "T2", "--executor", "orch-verify",
                "--objective", "o", "--criterion", "x",
            )
            self.assertEqual(1, bad.returncode, bad.stdout)
            self.assertIn("error", json.loads(bad.stdout))
