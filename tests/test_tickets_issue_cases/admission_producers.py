"""Every issue producer enters the v1 admission boundary as pending."""

from .common import *  # noqa: F401,F403


class V1ProducerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temporary.name)
        self.sink = use_sink(self.tmp)

    def tearDown(self):
        self.temporary.cleanup()

    def test_new_and_new_file_start_pending_with_a_ticket_cohort(self):
        direct = run_cmd(
            "new", "testrun", "T1", "--executor", "orch-tdd",
            "--objective", "Change one artifact.", "--criterion", GOOD_CRITERION,
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.assertEqual("pending", direct["new"]["status"])
        first = Path(direct["new"]["path"]).read_text(encoding="utf-8")
        self.assertIn("admission: v1:pending", first)
        self.assertIn("cohort: v1:ticket:T1", first)

        source = self.tmp / "T2.md"
        source.write_text(GOOD_TICKET.replace("id: T1", "id: T2"), encoding="utf-8")
        placed = run_cmd("new", "testrun", "--file", source)
        second = Path(placed["new"]["path"]).read_text(encoding="utf-8")
        self.assertIn("status: pending", second)
        self.assertIn("admission: v1:pending", second)
        self.assertIn("cohort: v1:ticket:T2", second)

    def test_new_carries_canonical_inputs_and_mutation_plan(self):
        record = '{"name":"question","type":"literal","value":"fixed"}'
        payload = run_cmd(
            "new", "testrun", "T1", "--executor", "orch-tdd",
            "--objective", "Change one artifact.", "--criterion", GOOD_CRITERION,
            "--pack", "orch-code-pack", "--isolation", "required",
            "--input", record, "--mutation", "change:scripts/tool.py",
        )
        text = Path(payload["new"]["path"]).read_text(encoding="utf-8")
        self.assertIn(f"- input: {record}", text)
        self.assertIn("mutations: [change:scripts/tool.py]", text)

    def test_new_without_inputs_has_no_legacy_prose_sentinel(self):
        payload = run_cmd(
            "new", "testrun", "T1", "--executor", "orch-tdd",
            "--objective", "Change one artifact.", "--criterion", GOOD_CRITERION,
        )
        text = Path(payload["new"]["path"]).read_text(encoding="utf-8")
        self.assertNotIn("None.", tickets_mod._sections(text)["Fixed inputs"])

    def test_explicit_root_cohort_is_validated(self):
        refused = run_cmd(
            "new", "testrun", "T1", "--executor", "orch-tdd",
            "--objective", "Change one artifact.", "--criterion", GOOD_CRITERION,
            "--cohort", "not-a-cohort",
        )
        self.assertIn("cohort", refused["error"])
        accepted = run_cmd(
            "new", "testrun", "T1", "--executor", "orch-tdd",
            "--objective", "Change one artifact.", "--criterion", GOOD_CRITERION,
            "--cohort", "v1:root:R",
        )
        self.assertIn("cohort: v1:root:R", Path(accepted["new"]["path"]).read_text(encoding="utf-8"))

    def test_instantiate_uses_one_order_independent_batch_cohort(self):
        directory = make_template(self.tmp, three_stubs())
        payload = run_cmd("instantiate", directory, "--run", "testrun", "--set", "target=scratch/a.txt")
        expected = tickets_mod.batch_cohort(payload["instantiate"]["ids"])
        for path in payload["instantiate"]["paths"]:
            text = Path(path).read_text(encoding="utf-8")
            self.assertIn("status: pending", text)
            self.assertIn("admission: v1:pending", text)
            self.assertIn(f"cohort: {expected}", text)

    def test_the_canonical_fix_template_enters_v1_admission(self):
        directory = ROOT / "compositions" / "fix"
        payload = run_cmd(
            "instantiate", directory, "--run", "fixrun",
            "--set", "failure=the observed failure",
            "--set", "workspace=scratch",
        )
        self.assertNotIn("error", payload, payload)
        ready = run_cmd("ready", "--run", "fixrun")
        self.assertNotIn("error", ready, ready)
        self.assertEqual(["00-reproduce"], [item["id"] for item in ready["ready"]])
        self.assertEqual(
            {"01-cause", "02-repair", "03-verify"},
            {item["id"] for item in ready["skipped"]},
        )
        for item in ready["skipped"]:
            self.assertEqual(
                {"dependency-incomplete", "ticket-result-not-terminal"},
                {finding["code"] for finding in item["findings"]},
                item,
            )
        run_dir = self.sink / "tickets" / "fixrun"
        for path in sorted(run_dir.glob("*.md")):
            records = [
                json.loads(line[len("- input: "):])
                for line in tickets_mod._sections(path.read_text(encoding="utf-8"))["Fixed inputs"].splitlines()
            ]
            for record in records:
                self.assertRegex(record["name"], r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")

    def test_gate_stubs_share_the_roots_cut_cohort(self):
        run_dir = self.sink / "tickets" / "testrun"
        run_dir.mkdir(parents=True)
        root = GOOD_TICKET.replace("id: T1", "id: R").replace("executor: orch-tdd", "executor: orch-decompose")
        root = tickets_mod._set_frontmatter_field(root, "pack", "orch-code-pack")
        unit = GOOD_TICKET.replace("id: T1", "id: R.01")
        (run_dir / "R.md").write_text(root, encoding="utf-8")
        (run_dir / "R.01.md").write_text(unit, encoding="utf-8")
        payload = run_cmd("gate", "testrun", "R", "--lens", "code")
        self.assertNotIn("error", payload)
        for path in payload["gate"]["paths"]:
            text = Path(path).read_text(encoding="utf-8")
            self.assertIn("status: pending", text)
            self.assertIn("admission: v1:pending", text)
            self.assertIn("cohort: v1:root:R", text)
            inputs = tickets_mod._sections(text)["Fixed inputs"]
            for line in inputs.splitlines():
                if line.strip():
                    self.assertRegex(line, r"^- input: \{.*\}$")
