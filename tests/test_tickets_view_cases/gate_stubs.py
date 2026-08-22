"""Gate-stub behavior cases loaded through :mod:`tests.test_tickets_view`."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_tickets_view import make_run, run_cmd, ticket, tickets_mod, use_sink
from scripts import tickets_dispatch

class GateStubsTest(unittest.TestCase):
    """`gate <run> <root>` writes work-item.md Root ticket's three stubs:
    critique per lens (read-only, parallel, over every unit ticket), one
    repair behind them all, one verify carrying the root's acceptance."""

    def make(self, sink: Path, units=("R.01", "R.02"), pack: str = "") -> Path:
        tickets = {
            "R": ticket(
                "R", status="claimed", executor="orch-decompose",
                objective="the whole delivery lands",
                criterion="the suite exits 0 | oracle: `python tools/run_tests.py` "
                "| oracle_class: deterministic | provenance: pre-existing",
                pack=pack,
            )
        }
        for unit in units:
            tickets[unit] = ticket(unit, deps="[R]", objective=f"unit {unit}")
        return make_run(sink, tickets)

    def gate(self, *extra):
        return run_cmd(
            "gate", "testrun", "R", "--lens", "cut-lens",
            "--write-scope", "scripts/one.py", *extra
        )

    def stub(self, run_dir: Path, tid: str) -> str:
        return (run_dir / f"{tid}.md").read_text(encoding="utf-8")

    def test_exactly_the_three_stubs_are_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            payload = self.gate()
            self.assertNotIn("error", payload)
            self.assertEqual(
                ["R.gate.critique.cut-lens", "R.gate.repair", "R.gate.verify"],
                payload["gate"]["ids"],
            )
            self.assertEqual(
                {"R", "R.01", "R.02", "R.gate.critique.cut-lens", "R.gate.repair",
                 "R.gate.verify"},
                {path.stem for path in run_dir.glob("*.md")},
            )

    def test_every_gate_sibling_uses_one_sealed_head_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            self.make(sink, pack="orch-code-pack")
            baseline = "a" * 40
            with mock.patch.object(tickets_dispatch, "git_head", return_value=baseline) as probe:
                payload = run_cmd(
                    "gate", "testrun", "R", "--lens", "cut-lens,second-lens",
                    "--write-scope", "scripts/one.py",
                )
            self.assertNotIn("error", payload)
            self.assertEqual(1, probe.call_count)
            for path in payload["gate"]["paths"]:
                self.assertIn('"revision":"' + baseline + '"', Path(path).read_text(encoding="utf-8"))

    def test_the_edges_run_units_to_critiques_to_repair_to_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            edges = {
                item["id"]: item["depends_on"]
                for item in run_cmd("list", "--run", "testrun")["tickets"]
            }
            self.assertEqual(["R.01", "R.02"], edges["R.gate.critique.cut-lens"])
            self.assertEqual(["R.gate.critique.cut-lens"], edges["R.gate.repair"])
            self.assertEqual(["R.gate.repair"], edges["R.gate.verify"])
            self.assertIn("status: pending", self.stub(run_dir, "R.gate.verify"))

    def test_the_critique_is_read_only_and_names_its_lens_and_the_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            text = self.stub(run_dir, "R.gate.critique.cut-lens")
            self.assertIn("executor: orch-critique", text)
            self.assertIn("write_scope: []", text)
            inputs = tickets_mod._sections(text)["Fixed inputs"]
            self.assertIn('"name":"lens","type":"literal","value":"cut-lens"', inputs)
            self.assertIn('"section":"Completion test","ticket":"R"', inputs)

    def test_the_repair_carries_the_given_write_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            text = self.stub(run_dir, "R.gate.repair")
            self.assertIn("executor: orch-repair", text)
            self.assertIn("write_scope: [scripts/one.py]", text)

    def test_the_repairs_mutation_plan_states_its_scope_as_posix_paths(self):

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            payload = run_cmd(
                "gate", "testrun", "R", "--lens", "cut-lens",
                "--write-scope", "scripts\\one.py,docs/two.md",
            )
            self.assertNotIn("error", payload)
            data = tickets_mod._parse_frontmatter(self.stub(run_dir, "R.gate.repair"))
            self.assertEqual(
                ["change:scripts/one.py", "change:docs/two.md"],
                data["mutations"],
            )

    def test_the_critique_states_the_units_it_reads_as_a_list_of_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            inputs = tickets_mod._sections(
                self.stub(run_dir, "R.gate.critique.cut-lens")
            )["Fixed inputs"]
            self.assertIn('"section":"Result","ticket":"R.01"', inputs)
            self.assertIn('"section":"Result","ticket":"R.02"', inputs)
            self.assertNotIn("['", inputs)

    def test_the_verify_carries_the_roots_completion_test_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            text = self.stub(run_dir, "R.gate.verify")
            self.assertIn("executor: orch-verify", text)
            self.assertEqual(
                tickets_mod._sections(self.stub(run_dir, "R"))["Completion test"],
                tickets_mod._sections(text)["Completion test"],
            )

    def test_the_verify_carries_the_canonical_root_mutation_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            root = run_dir / "R.md"
            root.write_text(
                root.read_text(encoding="utf-8").replace(
                    "write_scope: []",
                    "write_scope: []\nmutations: [change:z.py, create:a.py]",
                ),
                encoding="utf-8",
            )
            self.gate()
            inputs = tickets_mod._sections(
                self.stub(run_dir, "R.gate.verify")
            )["Fixed inputs"]
            records = [
                json.loads(line.removeprefix("- input: "))
                for line in inputs.splitlines()
            ]
            record = next(
                item for item in records if item["name"] == "mutation-plan-paths"
            )
            paths = ["a.py", "z.py"]
            canonical = json.dumps(
                paths, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
            self.assertEqual(
                {
                    "identity": "sha256:" + hashlib.sha256(canonical).hexdigest(),
                    "paths": paths,
                },
                record["value"],
            )

    def test_a_malformed_root_mutation_refuses_the_whole_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            root = run_dir / "R.md"
            root.write_text(
                root.read_text(encoding="utf-8").replace(
                    "write_scope: []",
                    "write_scope: []\nmutations: [change:/outside.py]",
                ),
                encoding="utf-8",
            )
            payload = self.gate()
            self.assertIn("mutation plan", payload["error"])
            self.assertEqual([], list(run_dir.glob("R.gate.*.md")))

    def test_acceptance_can_be_taken_from_another_ticket(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate("--acceptance-from", "R.01")
            self.assertEqual(
                tickets_mod._sections(self.stub(run_dir, "R.01"))["Completion test"],
                tickets_mod._sections(self.stub(run_dir, "R.gate.verify"))["Completion test"],
            )

    def test_two_lenses_are_two_critiques_and_one_repair_behind_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            payload = run_cmd(
                "gate", "testrun", "R", "--lens", "cut-lens,craft",
                "--write-scope", "scripts/one.py",
            )
            self.assertNotIn("error", payload)
            self.assertEqual(
                ["R.gate.critique.craft", "R.gate.critique.cut-lens",
                 "R.gate.repair", "R.gate.verify"],
                sorted(payload["gate"]["ids"]),
            )
            edges = tickets_mod._parse_frontmatter(
                self.stub(run_dir, "R.gate.repair")
            )["depends_on"]
            self.assertEqual(
                ["R.gate.critique.craft", "R.gate.critique.cut-lens"], sorted(edges)
            )

    def test_one_root_owns_gate_files_and_distinct_lenses(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            duplicate = run_cmd(
                "gate", "testrun", "R", "--lens", "code,code",
                "--write-scope", "scripts/one.py",
            )
            self.assertIn("distinct", duplicate["error"])
            self.assertEqual([], list(run_dir.glob("R.gate.*.md")))

            created = run_cmd(
                "gate", "testrun", "R", "--lens", "code,security",
                "--write-scope", "scripts/one.py",
            )
            self.assertNotIn("error", created)
            self.assertEqual(["code", "security"], created["gate"]["lenses"])
            before = {
                path.name: path.read_bytes() for path in run_dir.glob("R.gate.*.md")
            }

            (run_dir / "Q.md").write_text(
                ticket(
                    "Q", status="claimed", executor="orch-decompose",
                    objective="a legacy second kind",
                ),
                encoding="utf-8",
            )
            (run_dir / "Q.01.md").write_text(
                ticket("Q.01", deps="[Q]", objective="legacy unit"),
                encoding="utf-8",
            )
            second = run_cmd(
                "gate", "testrun", "Q", "--lens", "content",
                "--write-scope", "docs/one.md",
            )
            self.assertIn("one gate", second["error"])
            self.assertIn("R", second["error"])
            self.assertEqual(before, {
                path.name: path.read_bytes() for path in run_dir.glob("R.gate.*.md")
            })
            self.assertEqual([], list(run_dir.glob("Q.gate.*.md")))

    def test_lens_identity_is_case_insensitive_on_every_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            payload = run_cmd(
                "gate", "testrun", "R", "--lens", "code,Code",
                "--write-scope", "scripts/one.py",
            )
            self.assertIn("distinct", payload["error"])
            self.assertEqual([], list(run_dir.glob("R.gate.*.md")))

    def test_an_ordinary_ticket_cannot_take_the_gate_before_the_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            (run_dir / "Q.md").write_text(
                ticket("Q", status="claimed", executor="orch-tdd"), encoding="utf-8"
            )
            (run_dir / "Q.01.md").write_text(
                ticket("Q.01", deps="[Q]"), encoding="utf-8"
            )
            refused = run_cmd(
                "gate", "testrun", "Q", "--lens", "code",
                "--write-scope", "scripts/one.py",
            )
            self.assertIn("sole orch-decompose root", refused["error"])
            self.assertEqual([], list(run_dir.glob("Q.gate.*.md")))
            self.assertNotIn("error", self.gate())

    def test_a_second_gate_is_refused_and_the_first_stubs_stand(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            before = self.stub(run_dir, "R.gate.repair")
            payload = self.gate()
            self.assertIn("error", payload)
            self.assertIn("R.gate.critique.cut-lens", payload["error"])
            self.assertEqual(before, self.stub(run_dir, "R.gate.repair"))

    def test_a_root_with_no_unit_tickets_is_refused_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink, units=())
            payload = self.gate()
            self.assertIn("error", payload)
            self.assertIn("R.` subtree", payload["error"])
            self.assertEqual({"R"}, {path.stem for path in run_dir.glob("*.md")})

    def test_the_critique_depends_on_an_assembly_item_outside_the_nn_shape(self):
        """orch-decompose emits a terminal assembly item depending on every
        unit; no id shape is fixed for it. A critique that does not depend
        on it can complete -- taking the root with it -- while assembly is
        still running."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            (run_dir / "R.assembly.md").write_text(
                ticket("R.assembly", status="pending", deps="[R.01,R.02]",
                       objective="the units become one deliverable"),
                encoding="utf-8",
            )
            self.gate()
            edges = {
                item["id"]: item["depends_on"]
                for item in run_cmd("list", "--run", "testrun")["tickets"]
            }
            self.assertEqual(
                ["R.01", "R.02", "R.assembly"],
                edges["R.gate.critique.cut-lens"],
            )

    def test_the_gate_stubs_are_not_their_own_dependencies(self):
        """The subtree the critique closes over excludes the gate itself:
        a critique depending on the repair that depends on it is a cycle."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            self.make(sink)
            self.gate()
            edges = {
                item["id"]: item["depends_on"]
                for item in run_cmd("list", "--run", "testrun")["tickets"]
            }
            self.assertEqual(["R.01", "R.02"], edges["R.gate.critique.cut-lens"])

    def test_the_write_scope_defaults_to_the_root_tickets_own(self):
        """contracts/work-item.md: the root's `write_scope` is the run's
        scope and the repair holds it, so the caller states it once."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            root = run_dir / "R.md"
            root.write_text(
                root.read_text(encoding="utf-8").replace(
                    "write_scope: []", "write_scope: [scripts/one.py]"
                ),
                encoding="utf-8",
            )
            payload = run_cmd("gate", "testrun", "R", "--lens", "cut-lens")
            self.assertNotIn("error", payload)
            self.assertIn(
                "write_scope: [scripts/one.py]", self.stub(run_dir, "R.gate.repair")
            )

    def test_an_unknown_root_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            self.make(sink)
            payload = run_cmd(
                "gate", "testrun", "Q", "--lens", "cut-lens",
                "--write-scope", "scripts/one.py",
            )
            self.assertIn("error", payload)
            self.assertIn("Q", payload["error"])

    def test_the_lens_is_required_and_so_is_a_scope_to_default_to(self):
        """`--lens` has no source but the caller. `--write-scope` has one
        -- the root ticket -- so it is refused only when the root declares
        none either."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            self.make(sink)
            for argv in (
                ("gate", "testrun", "R", "--write-scope", "scripts/one.py"),
                ("gate", "testrun", "R", "--lens", "cut-lens"),
            ):
                with self.subTest(argv=argv):
                    self.assertIn("error", run_cmd(*argv))

    def test_every_stub_is_a_ticket_but_lifecycle_bypass_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            run_dir = self.make(sink)
            self.gate()
            for tid in ("R.gate.critique.cut-lens", "R.gate.repair", "R.gate.verify"):
                with self.subTest(tid):
                    self.assertEqual([], tickets_mod.ticket_defects(self.stub(run_dir, tid)))
                    transition = run_cmd("set-status", "testrun", tid, "ready")
                    self.assertIn("admission", transition["error"])
                    payload = run_cmd("packet", "testrun", tid, "--reply-to", "main")
                    self.assertIn("not claimed", payload["error"])

    def test_every_stub_declares_its_independence_as_the_gate(self):
        """`rules/verification.md` §10: acceptance resting only on checks
        the executing context authored is UNVERIFIED, and the frontier's
        checker path keys on `independence: checker`. A gate lane authored
        none of these criteria and re-verification is the gate's own
        `<root>.gate.verify`, so the field says `gate` rather than reading
        `checker` by absence.
        """

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            for tid in ("R.gate.critique.cut-lens", "R.gate.repair",
                        "R.gate.verify"):
                with self.subTest(tid):
                    self.assertIn("independence: gate", self.stub(run_dir, tid))

    def test_every_criterion_the_gate_writes_is_pre_existing(self):
        """The script authored these criteria before the lane existed, so
        their provenance is the lane's, not the criterion's: `pre-existing`
        per contracts/work-item.md. The verify stub carries the root's own
        `## Completion test` verbatim and is not re-stamped here.
        """

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            for tid in ("R.gate.critique.cut-lens", "R.gate.repair"):
                with self.subTest(tid):
                    body = self.stub(run_dir, tid).split("## Completion test")[1]
                    body = body.split("## Return fields")[0]
                    self.assertNotIn("provenance: authored-here", body)
                    self.assertIn("provenance: pre-existing", body)

    def test_the_lens_defaults_to_the_stamped_packs_domain(self):
        """`--lens` names a label, and the pack's lens cell names none.

        The stamped pack's domain is that label -- the pack name without
        `orch-` and `-pack` -- so the decomposer that stamped the root has
        already said it and never has to improvise a second name.
        """

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink, pack="orch-code-pack")
            payload = run_cmd(
                "gate", "testrun", "R", "--write-scope", "scripts/one.py"
            )
            self.assertNotIn("error", payload)
            self.assertEqual(["code"], payload["gate"]["lenses"])
            self.assertIn("R.gate.critique.code", payload["gate"]["ids"])
            self.assertIn("`code`", self.stub(run_dir, "R.gate.critique.code"))

    def test_a_root_with_no_pack_still_requires_the_lens(self):
        """The default is the stamp's; a root carrying no stamp has none to
        read, and the refusal that names `--lens` stands."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            self.make(sink)
            payload = run_cmd(
                "gate", "testrun", "R", "--write-scope", "scripts/one.py"
            )
            self.assertIn("error", payload)
            self.assertIn("--lens", payload["error"])

    def test_the_gate_is_the_queued_scopes_edge_in_the_view(self):
        """The two subcommands meet: what `gate` writes is what `worklog`
        reads as scope queued behind the root subtree."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            run_dir = self.make(sink)
            self.gate()
            (run_dir / "R.04.md").write_text(
                ticket("R.04", status="pending", deps="[R.gate.verify]",
                       objective="the successor"),
                encoding="utf-8",
            )
            markdown = run_cmd("worklog", "testrun")["worklog"]["markdown"]
            queued = markdown.split("## queued scope")[1].split("## terminal")[0]
            self.assertIn("R.04", queued)
