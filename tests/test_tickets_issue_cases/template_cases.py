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
            self.assertEqual({"A": "pending", "B": "pending", "C": "pending"}, listed)

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
            self.assertEqual("pending", data["status"])
            self.assertEqual([], tickets_mod.ticket_defects(text))

    def test_inputs_render_json_safely_and_receive_run_dependency_and_baseline_identities(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = three_stubs()
            stubs["A"] = stubs["A"].replace(
                '- input: {"name":"none","type":"literal","value":null}',
                '- input: {"name":"question","type":"literal","value":"{{target}}"}',
            )
            directory = make_template(tmp, stubs)
            exact = 'a "quoted" value'
            payload = self.instantiate(directory, "--set", f"target={exact}")
            self.assertNotIn("error", payload)
            first = (self.run_dir(sink) / "A.md").read_text(encoding="utf-8")
            second = (self.run_dir(sink) / "B.md").read_text(encoding="utf-8")
            first_inputs = [
                json.loads(line[len("- input: "):])
                for line in tickets_mod._sections(first)["Fixed inputs"].splitlines()
            ]
            second_inputs = [
                json.loads(line[len("- input: "):])
                for line in tickets_mod._sections(second)["Fixed inputs"].splitlines()
            ]
            self.assertEqual(exact, next(x["value"] for x in first_inputs if x["name"] == "question"))
            baseline = next(x for x in first_inputs if x["name"] == "baseline")
            self.assertEqual("git-tree", baseline["identity"]["kind"])
            self.assertRegex(baseline["identity"]["revision"], r"^[0-9a-f]{40,64}$")
            dependency = next(x for x in second_inputs if x["name"] == "a-result")
            self.assertEqual(
                {"kind": "ticket-section", "run": "testrun", "section": "Result", "ticket": "A"},
                dependency["identity"],
            )

    def test_a_numeric_dependency_id_receives_a_valid_input_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            stubs = {
                "00-first": stub("00-first", executor="orch-investigate"),
                "01-second": stub(
                    "01-second", "[00-first]", executor="orch-verify"
                ),
            }
            directory = make_template(tmp, stubs)
            payload = self.instantiate(directory, "--set", "target=scratch/a.py")
            self.assertNotIn("error", payload)
            second = (self.run_dir(sink) / "01-second.md").read_text(encoding="utf-8")
            records = [
                json.loads(line[len("- input: "):])
                for line in tickets_mod._sections(second)["Fixed inputs"].splitlines()
            ]
            dependency = next(
                item for item in records
                if (item.get("identity") or {}).get("ticket") == "00-first"
            )
            self.assertEqual("ticket-00-first-result", dependency["name"])

    def test_template_canonical_input_remains_a_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            payload = self.instantiate(directory, "--set", "target=scripts/a.py")
            self.assertNotIn("error", payload)
            text = (self.run_dir(sink) / "A.md").read_text(encoding="utf-8")
            lines = tickets_mod._sections(text)["Fixed inputs"].splitlines()
            self.assertTrue(all(line.startswith("- input: {") for line in lines))
            records = [json.loads(line[len("- input: "):]) for line in lines]
            self.assertIn(None, [record.get("value") for record in records])

    def test_an_instantiated_ticket_is_claimable_and_dispatchable(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            directory = make_template(tmp, three_stubs())
            self.instantiate(directory, "--set", "target=scripts/a.py")
            claimed = run_cmd("claim", "testrun", "A", "--by", "agent-a")
            self.assertEqual("agent-a", claimed["claimed"]["claimed_by"])
            packet = run_cmd("packet", "testrun", "A", "--reply-to", "main")
            self.assertNotIn("error", packet)

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
