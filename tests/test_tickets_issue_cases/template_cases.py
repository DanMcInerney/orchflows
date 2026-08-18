"""Behavioral cases imported by the ``tests.test_tickets_issue`` seam."""

from .common import *  # noqa: F401,F403

class InstantiateTest(unittest.TestCase):
    """`instantiate` turns one template into one run's tickets: substituted,
    graded, ordered, and written all or not at all."""

    def instantiate(self, directory: Path, *extra):
        return run_cmd("instantiate", str(directory), "--run", "testrun", *extra)

    def run_dir(self, sink: Path) -> Path:
        return sink / "tickets" / "testrun"

    def test_every_stub_lands_with_its_status_and_the_ids_are_ordered(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertNotIn("error", payload)
            self.assertEqual(["A", "B", "C"], payload["instantiate"]["ids"])
            listed = {item["id"]: item["status"] for item in run_cmd("list", "--run", "testrun")["tickets"]}
            self.assertEqual({"A": "ready", "B": "pending", "C": "pending"}, listed)

    def test_the_edgeless_stub_is_the_only_one_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            self.instantiate(directory, "--set", "target=scripts/a.py")
            ready = run_cmd("ready", "--run", "testrun")["ready"]
            self.assertEqual(["A"], [item["id"] for item in ready])

    def test_the_placeholder_is_substituted_and_the_run_stamped(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            self.instantiate(directory, "--set", "target=scripts/a.py")
            text = (self.run_dir(sink) / "A.md").read_text(encoding="utf-8")
            self.assertNotIn("{{", text)
            data = tickets_mod._parse_frontmatter(text)
            self.assertEqual(["scripts/a.py"], data["write_scope"])
            self.assertEqual("testrun", data["run"])
            self.assertEqual("ready", data["status"])
            self.assertEqual([], tickets_mod.ticket_defects(text))

    def test_an_instantiated_ticket_is_claimable_and_dispatchable(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            self.instantiate(directory, "--set", "target=scripts/a.py")
            packet = run_cmd("packet", "testrun", "A", "--reply-to", "main")
            self.assertNotIn("error", packet)
            claimed = run_cmd("claim", "testrun", "A", "--by", "agent-a")
            self.assertEqual("agent-a", claimed["claimed"]["claimed_by"])

    def test_a_declared_placeholder_no_set_supplies_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            payload = self.instantiate(directory)
            self.assertIn("error", payload)
            self.assertIn("target", payload["error"])
            self.assertFalse(self.run_dir(sink).exists(), "a refused template wrote")

    def test_an_unfilled_placeholder_is_refused_naming_it_and_its_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = three_stubs()
            stubs["B"] = stub("B", "[A]", objective="fix {{undeclared}}")
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("undeclared", payload["error"])
            self.assertIn("B", payload["error"])
            self.assertFalse(self.run_dir(sink).exists())

    def test_a_cyclic_template_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = three_stubs()
            stubs["A"] = stub("A", "[C]", scope="{{target}}")
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("cyclic", payload["error"])
            self.assertFalse(self.run_dir(sink).exists())

    def test_two_terminal_stubs_are_refused_by_name(self):
        """Exactly one stub is terminal: its completion test is the
        template's done check, and two of them is two done checks."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = three_stubs()
            stubs["C"] = stub("C", "[A]")  # B is now terminal too
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("B", payload["error"])
            self.assertIn("C", payload["error"])
            self.assertFalse(self.run_dir(sink).exists())

    def test_a_stub_whose_criterion_names_no_class_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = three_stubs()
            stubs["C"] = stub("C", "[A, B]", criterion="it looks right | oracle: a glance")
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("oracle_class", payload["error"])
            self.assertIn("C", payload["error"])
            self.assertFalse(self.run_dir(sink).exists(), "one bad stub let two land")

    def test_a_dependency_that_is_not_a_stub_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = three_stubs()
            stubs["B"] = stub("B", "[A, elsewhere]")
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("elsewhere", payload["error"])
            self.assertFalse(self.run_dir(sink).exists())

    def test_an_id_already_issued_in_the_run_is_refused_and_nothing_lands(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            place(sink, "testrun", "B", GOOD_TICKET.replace("id: T1", "id: B"))
            directory = make_template(tmp, three_stubs())
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("B", payload["error"])
            self.assertEqual(["B.md"], sorted(p.name for p in self.run_dir(sink).iterdir()))

    def test_a_directory_with_no_template_md_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs(), template_md=None)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("template.md", payload["error"])

    def test_a_missing_template_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            payload = self.instantiate(tmp / "compositions" / "absent")
            self.assertIn("error", payload)

    def test_a_template_with_no_stub_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, {})
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("stub", payload["error"])

    def test_a_set_without_a_value_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            payload = self.instantiate(directory, "--set", "target")
            self.assertIn("error", payload)
            self.assertIn("target", payload["error"])

    def test_a_stub_whose_id_is_not_its_file_stem_is_refused(self):
        """`depends_on` names stub ids and the run names files by stem; two
        answers to which stub this is would resolve an edge to neither."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            stubs = three_stubs()
            stubs["C"] = stub("D", "[A, B]")
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertIn("error", payload)
            self.assertIn("D", payload["error"])

    def test_the_run_argument_is_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            payload = run_cmd("instantiate", str(directory), "--set", "target=x")
            self.assertIn("error", payload)
            self.assertIn("--run", payload["error"])
