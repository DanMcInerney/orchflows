"""Every issue producer enters the admission boundary as pending.

Every ticket these cases issue is a v1 one, so v1's sentinel is what each
carries -- named through the table rather than spelled, because
`v1:pending` is what a producer writes for a v1 ticket, not what a
producer writes. The rule that makes that distinction, and its v2 half,
are `StampingTest`'s in `tests/test_lifecycle_table.py`.
"""

from unittest import mock

from .common import *  # noqa: F401,F403
from scripts import tickets_issue, tickets_transitions
from scripts.tickets_admission import ADMISSION_V2_PENDING, is_v2
from scripts.tickets_transitions import pending_admission

#: What a v1 ticket's producer stamps, from the table that owns the value.
V1_PENDING = f"admission: {pending_admission(1)}"

#: The same ticket with the one field that opts it into v2. `is_v2` reads
#: the four public fields and nothing else, so this line is the entire
#: difference a producer can see -- which is how a site that never asks
#: stamps v1's sentinel onto a v2 file while every other byte looks right.
V2_TICKET = tickets_mod._set_frontmatter_field(GOOD_TICKET, "ownership_regions", "[]")


class ProducerStampingTest(unittest.TestCase):
    """Each producer path, live, against the table entry it stamps through.

    `tests/test_lifecycle_table.py`'s `StampingTest` inherits these, so the
    table's entries and the sites consuming them are graded in one place
    without a second copy of either. The paths are
    `scripts/tickets_issue.py`'s three: the flag form, `_place_ticket`
    behind `new --file`, and `_recut_under_run_lock`.
    """

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temporary.name)
        self.sink = use_sink(self.tmp)

    def tearDown(self):
        self.temporary.cleanup()

    def written(self, name: str, text: str) -> Path:
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def assert_stamped_at(self, path, version: int) -> None:
        """One written ticket, against the table's entry for a version.

        The version is read back off the ticket rather than assumed, so a
        case that stopped producing the version it names fails here instead
        of quietly grading the wrong half of the boundary.
        """

        data = tickets_mod._parse_frontmatter(Path(path).read_text(encoding="utf-8"))
        entry = tickets_transitions.stamp("stamp", version)
        self.assertEqual(version == 2, is_v2(data))
        self.assertEqual(entry.admission, data.get("admission"))
        self.assertEqual(entry.status, data.get("status"))
        for field in entry.blanks:
            with self.subTest(field=field):
                self.assertEqual("", str(data.get(field) or ""))

    def test_new_file_stamps_the_sentinel_the_placed_files_own_version_names(self):
        """`new --file` places a ticket somebody else wrote, and a v2 file
        is one it may be handed. The version is the file's, so the sentinel
        is that version's -- not the one the site happens to spell."""

        for version, text in ((1, GOOD_TICKET), (2, V2_TICKET)):
            with self.subTest(version=version):
                run = f"place{version}"
                placed = run_cmd(
                    "new", run, "--file",
                    self.written(f"{run}.md", text.replace("run: testrun", f"run: {run}")),
                )
                self.assertNotIn("error", placed, placed)
                self.assert_stamped_at(placed["new"]["path"], version)

    def test_recut_stamps_the_candidates_version_in_the_file_and_the_payload(self):
        """`recut` replaces the cut with a candidate, and the candidate is
        what decides -- the new cohort already keys off it. The payload
        states the admission it wrote, so the two have to be one value."""

        target = place(
            self.sink, "testrun", "T1",
            GOOD_TICKET.replace("status: ready", "status: pending"),
        )
        for version, text in ((1, GOOD_TICKET), (2, V2_TICKET)):
            with self.subTest(version=version):
                payload = run_cmd(
                    "recut", "testrun", "T1", "--file",
                    self.written(f"candidate{version}.md", text),
                )
                self.assertNotIn("error", payload, payload)
                self.assert_stamped_at(target, version)
                self.assertEqual(
                    pending_admission(version), payload["recut"]["admission"]
                )

    def issue_by_flags(self, run: str):
        """The flag form, spelled the way this module's other cases spell it."""

        return run_cmd(
            "new", run, "T1", "--executor", "orch-tdd",
            "--objective", "Change one artifact.", "--criterion", GOOD_CRITERION,
            "--pack", "orch-code-pack", "--isolation", "required",
        )

    def test_the_flag_form_takes_its_sentinel_from_the_table(self):
        """The flag form writes no v2 field, so v1 is the version-correct
        stamp -- and the value alone would pass against a spelled constant.
        So the table's own function is moved instead: a site that reads it
        follows the move, and a site that spells `v1:pending` does not."""

        issued = self.issue_by_flags("flagrun")
        self.assertNotIn("error", issued, issued)
        self.assert_stamped_at(issued["new"]["path"], 1)
        with mock.patch.object(
            tickets_issue, "pending_admission", lambda version=1: ADMISSION_V2_PENDING
        ):
            moved = self.issue_by_flags("movedrun")
        self.assertNotIn("error", moved, moved)
        self.assertIn(
            f"admission: {ADMISSION_V2_PENDING}",
            Path(moved["new"]["path"]).read_text(encoding="utf-8"),
        )


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
        self.assertIn(V1_PENDING, first)
        self.assertIn("cohort: v1:ticket:T1", first)

        source = self.tmp / "T2.md"
        source.write_text(GOOD_TICKET.replace("id: T1", "id: T2"), encoding="utf-8")
        placed = run_cmd("new", "testrun", "--file", source)
        second = Path(placed["new"]["path"]).read_text(encoding="utf-8")
        self.assertIn("status: pending", second)
        self.assertIn(V1_PENDING, second)
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
            self.assertIn(V1_PENDING, text)
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
            self.assertIn(V1_PENDING, text)
            self.assertIn("cohort: v1:root:R", text)
            inputs = tickets_mod._sections(text)["Fixed inputs"]
            for line in inputs.splitlines():
                if line.strip():
                    self.assertRegex(line, r"^- input: \{.*\}$")
