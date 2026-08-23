"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403

try:
    del load_tests
except NameError:
    pass

class RootGateLayoutTest(unittest.TestCase):
    """The layout every honest root cut has, graded as the contract writes it.

    A root ticket sits in the run directory beside its own `<root>.NN` units
    and its `<root>.gate.*` stubs. Read as issued items they convict every
    honest cut: the root is named by no criterion of the map it is the source
    of, each gate stub is named by the keyword `gate` and never by its id, and
    the root and the repair both hold the run's scope with no edge between
    them. `rules/verification.md` §11 makes the cut's verdict this tool re-run
    to exit 0, and the skill orders the gate step next, so a verdict that
    cannot survive the gate is a verdict read once and never again.
    """

    def setUp(self):
        self.result = run_cutcheck("cutcheck-root-gate")

    @staticmethod
    def _root(root):
        return {
            "id": root,
            "executor": tickets.ROOT_EXECUTOR,
            "depends_on": [],
            "write_scope": ["scripts/{}.py".format(root.lower())],
        }

    @staticmethod
    def _unit(root, number, path, **extra):
        ticket = {
            "id": "{}.{}".format(root, number),
            "executor": "orch-tdd",
            "independence": "gate",
            "depends_on": [],
            "write_scope": [path],
        }
        ticket.update(extra)
        return ticket

    @staticmethod
    def _gate(root, units, lenses=("code",)):
        gate = {}
        critiques = []
        for lens in lenses:
            ticket_id = "{}.gate.critique.{}".format(root, lens)
            critiques.append(ticket_id)
            gate[ticket_id] = {
                "id": ticket_id,
                "executor": tickets.GATE_EXECUTORS["critique"],
                "depends_on": list(units),
                "write_scope": [],
            }
        repair = "{}.gate.repair".format(root)
        verify = "{}.gate.verify".format(root)
        gate[repair] = {
            "id": repair,
            "executor": tickets.GATE_EXECUTORS["repair"],
            "depends_on": critiques,
            "write_scope": ["scripts/{}.py".format(root.lower())],
        }
        gate[verify] = {
            "id": verify,
            "executor": tickets.GATE_EXECUTORS["verify"],
            "depends_on": [repair],
            "write_scope": [],
        }
        return gate

    def test_two_roots_and_two_gate_systems_fail(self):
        """A hand-built set gets the same refusals as the runtime writers.

        The runtime now refuses the second root and the second gate before it
        writes either one. Cutcheck reads legacy and manually assembled state,
        so the same contradiction must still be a cut defect when both systems
        are already present on disk.
        """

        siblings = {}
        for root, path in (("R1", "scripts/one.py"), ("R2", "scripts/two.py")):
            unit = self._unit(root, "01", path)
            siblings[root] = self._root(root)
            siblings[unit["id"]] = unit
            siblings.update(self._gate(root, [unit["id"]]))

        findings = cutcheck._root_gate_layout(siblings)
        classes = [finding[2] for finding in findings]
        self.assertEqual(classes.count(cutcheck.MULTIPLE_ROOTS), 1, findings)
        self.assertEqual(classes.count(cutcheck.MULTIPLE_GATE_SYSTEMS), 1, findings)
        self.assertTrue(all(klass not in cutcheck.ADVISORY for klass in classes))

    def test_two_unrelated_roots_fail_before_either_has_a_gate(self):
        siblings = {"R1": self._root("R1"), "R2": self._root("R2")}
        findings = cutcheck._root_gate_layout(siblings)
        self.assertEqual(
            [cutcheck.MULTIPLE_ROOTS], [finding[2] for finding in findings], findings
        )

        # Canonical template decomposers are stages of one top-level graph,
        # and remain the explicit compatibility exception.
        siblings["R2"]["depends_on"] = ["R1"]
        self.assertEqual([], cutcheck._root_gate_layout(siblings))

    def test_a_partial_or_wrongly_edged_gate_is_malformed(self):
        unit = self._unit("R", "01", "scripts/one.py")
        critique = "R.gate.critique.code"
        siblings = {
            "R": self._root("R"),
            unit["id"]: unit,
            critique: {
                "id": critique,
                "executor": tickets.GATE_EXECUTORS["critique"],
                "depends_on": [unit["id"]],
                "write_scope": [],
            },
        }
        findings = cutcheck._root_gate_layout(siblings)
        self.assertIn(cutcheck.MALFORMED_GATE, [finding[2] for finding in findings])

    def test_command_rejects_the_independent_roots_and_partial_gate(self):
        """The public command, not only the helper, owns both refusals."""

        def body(ticket_id, executor, depends_on="[]"):
            return tickets._render_ticket(
                {
                    "id": ticket_id, "run": "layout-command", "status": "ready",
                    "executor": executor, "depends_on": depends_on,
                    "write_scope": ["install.py"], "bound": "10m",
                },
                [
                    ("Objective", "exercise the command layout"),
                    ("Fixed inputs", "- fixed baseline"),
                    ("Completion test", "- installer remains valid | oracle: "
                     "`python install.py --dry-run` | oracle_class: deterministic | "
                     "provenance: pre-existing"),
                    ("Return fields", "status; result"),
                    ("Result", ""), ("Verification", ""),
                    ("Feedback", "[]"), ("Risks", "[]"),
                ],
            )

        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "state"
            run_dir = sink / "tickets" / "layout-command"
            run_dir.mkdir(parents=True)
            (run_dir / "R1.md").write_text(
                body("R1", tickets.ROOT_EXECUTOR), encoding="utf-8"
            )
            (run_dir / "R2.md").write_text(
                body("R2", tickets.ROOT_EXECUTOR), encoding="utf-8"
            )
            (run_dir / "R1.gate.critique.code.md").write_text(
                body("R1.gate.critique.code", tickets.GATE_EXECUTORS["critique"]),
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ, {"ORCHFLOWS_STATE_HOME": str(sink)}
            ):
                result = run_cutcheck_subprocess(
                    ["layout-command", "--baseline", "HEAD", "--lib", str(ROOT)]
                )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn(cutcheck.MULTIPLE_ROOTS, result.stdout)
        self.assertIn(cutcheck.MALFORMED_GATE, result.stdout)

    def test_checker_plus_gate_and_uncovered_criteria_fail(self):
        """One ticket gets one independence path, even in the smallest cut.

        The second half preserves acceptance coverage as the counterexample:
        naming only the gate does not cover the unit that delegated its
        authored acceptance. Neither defect needs a ticket-count profile or a
        second gate to become true.
        """

        unit = self._unit("R", "01", "scripts/one.py", checked_by="checker-a")
        siblings = {"R": self._root("R"), unit["id"]: unit}
        siblings.update(self._gate("R", [unit["id"]]))
        layout = cutcheck._root_gate_layout(siblings)
        self.assertEqual(
            [finding[2] for finding in layout],
            [cutcheck.MIXED_INDEPENDENCE],
            layout,
        )

        with tempfile.TemporaryDirectory() as tmp:
            coverage = Path(tmp) / cutcheck.COVERAGE_FILE
            coverage.write_text(
                "| criterion | owner |\n|---|---|\n"
                "| 1 | gate |\n| 2 | R.02 |\n",
                encoding="utf-8",
            )
            uncovered = cutcheck._coverage(
                "R", coverage, [unit["id"]], (Path(tmp),)
            )
        self.assertEqual(
            [finding[2] for finding in uncovered],
            [cutcheck.ORPHAN_CRITERION, cutcheck.ORPHAN_ITEM],
            uncovered,
        )
        self.assertEqual(cutcheck._gate_owners(siblings), ["R"])
        self.assertNotIn("profile", unit)

    def test_gate_independence_counts_every_authored_here_criterion(self):
        unit = self._unit("R", "01", "scripts/one.py")
        unit["__completion_test"] = (
            "- first | oracle: first command | oracle_class: deterministic | "
            "provenance: authored-here\n"
            "- second | oracle: second command | oracle_class: judged | "
            "provenance: authored-here\n"
        )
        root = self._root("R")
        root["__completion_test"] = (
            "- final | oracle: final command | oracle_class: deterministic | "
            "provenance: pre-existing\n"
        )
        siblings = {"R": root, unit["id"]: unit}
        with tempfile.TemporaryDirectory() as tmp:
            coverage = Path(tmp) / cutcheck.COVERAGE_FILE
            coverage.write_text(
                "| criterion | owner |\n|---|---|\n| 1 | R.01 |\n",
                encoding="utf-8",
            )
            findings = cutcheck._coverage(
                "R", coverage, ["R.01"], (Path(tmp),),
                siblings=siblings, root="R",
            )
        self.assertIn(
            cutcheck.UNCOVERED_GATE_CRITERION,
            [finding[2] for finding in findings],
            findings,
        )

    def test_single_root_distinct_lenses_and_sole_owner_graph_pass(self):
        """The runtime's accepted one-root shape remains the lawful cut.

        Two named lenses feed one repair and verify, while disjoint unit scopes
        keep sole ownership. The constants come from the accepted predecessor
        runtime result rather than a second cutcheck-only gate vocabulary.
        """

        left = self._unit("R", "01", "scripts/one.py")
        right = self._unit("R", "02", "scripts/two.py")
        siblings = {"R": self._root("R"), left["id"]: left, right["id"]: right}
        siblings.update(
            self._gate("R", [left["id"], right["id"]], lenses=("code", "security"))
        )

        self.assertEqual(cutcheck._root_gate_layout(siblings), [])
        self.assertEqual(cutcheck._pairwise(siblings, {}), [])
        self.assertEqual(cutcheck._root_ids(siblings), ["R"])
        self.assertEqual(cutcheck._gate_owners(siblings), ["R"])
        self.assertEqual(
            sorted(
                ticket_id.rsplit(".", 1)[-1]
                for ticket_id in siblings
                if ".gate.critique." in ticket_id
            ),
            ["code", "security"],
        )

    def test_the_whole_layout_exits_zero(self):
        self.assertEqual(self.result.returncode, 0, self.result.stdout)

    def test_no_finding_stands_outside_the_advisory_set(self):
        violations, _, affirmed = report(self.result)
        self.assertEqual(violations, [], self.result.stdout)
        self.assertTrue(affirmed, self.result.stdout)

    def test_neither_the_root_nor_a_gate_stub_is_an_orphan_item(self):
        for line in self.result.stdout.splitlines():
            self.assertNotIn(cutcheck.ORPHAN_ITEM, line, self.result.stdout)

    def test_the_root_and_the_repair_sharing_the_run_scope_is_no_collision(self):
        self.assertNotIn(cutcheck.SCOPE_COLLISION, self.result.stdout)
        self.assertNotIn(cutcheck.STAGED_INVALIDATION, self.result.stdout)

    def test_the_structural_executors_are_legal_under_the_stamped_pack(self):
        """The pack's executor cell names `orch-tdd` and nothing else.

        Graded against that cell, the decomposer and the gate's three
        executors are all illegal, which would fail the cut for carrying the
        shape the contract requires of it. They are the library's own nodes,
        so they are graded against the library's own names.
        """

        self.assertNotIn(cutcheck.ILLEGAL_EXECUTOR, self.result.stdout)

    def test_a_unit_ticket_is_still_graded_against_the_packs_cell(self):
        self.assertIn(
            cutcheck.ILLEGAL_EXECUTOR, run_cutcheck("cutcheck-f6-executor").stdout
        )

    def test_a_gate_stub_naming_an_executor_the_gate_never_writes_is_reported(self):
        siblings = {
            "00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR},
            "00-root.gate.repair": {
                "id": "00-root.gate.repair", "executor": "orch-tdd"
            },
        }
        findings = cutcheck._executor_legality(siblings, ROOT)
        self.assertEqual(1, len(findings), findings)
        self.assertEqual("00-root.gate.repair", findings[0][0])
        self.assertEqual(cutcheck.ILLEGAL_EXECUTOR, findings[0][2])


class NestedRootTest(unittest.TestCase):
    """A root is the set's own source, never a unit inside another root's.

    `rules/topology.md` §7: mixed decomposition inside one graph is
    undefined. Reading every `orch-decompose` ticket as a root made a
    `<root>.NN` unit issued with that executor legal, and exempted anything
    it carried under `.gate.` from families 4 and 5 -- the cut defect hiding
    behind the exemption written for the honest layout.
    """

    def test_a_nested_root_is_reported_as_a_nested_root(self):
        siblings = {
            "00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR},
            "00-root.01": {"id": "00-root.01", "executor": cutcheck.ROOT_EXECUTOR},
        }
        findings = cutcheck._executor_legality(siblings, ROOT)
        self.assertEqual(1, len(findings), findings)
        self.assertEqual("00-root.01", findings[0][0])
        self.assertEqual(cutcheck.ILLEGAL_EXECUTOR, findings[0][2])
        self.assertIn("nested root", findings[0][3])

    def test_a_nested_roots_gate_stub_is_no_longer_exempt(self):
        siblings = {
            "00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR},
            "00-root.01": {"id": "00-root.01", "executor": cutcheck.ROOT_EXECUTOR},
            "00-root.01.gate.repair": {
                "id": "00-root.01.gate.repair", "executor": "orch-repair"
            },
        }
        roots = cutcheck._root_ids(siblings)
        self.assertEqual(["00-root"], roots)
        self.assertIsNone(cutcheck._gate_stub_of("00-root.01.gate.repair", roots))
        self.assertIn("00-root.01.gate.repair", cutcheck._issued_items(siblings, roots))

    def test_a_top_level_decompose_stub_beside_others_is_still_a_root(self):
        """`compositions/self-improve/01-deliver` is exactly this shape.

        A template's terminal-ish stub carries `orch-decompose` beside stubs
        no root owns; no other root's id prefixes it, so it is a root of its
        own and nothing about it is reported.
        """

        siblings = {
            "00-mine": {"id": "00-mine", "executor": "orch-self-improve"},
            "01-deliver": {"id": "01-deliver", "executor": cutcheck.ROOT_EXECUTOR},
            "02-close": {"id": "02-close", "executor": "orch-integrate"},
        }
        self.assertEqual(["01-deliver"], cutcheck._root_ids(siblings))
        self.assertEqual([], cutcheck._executor_legality(siblings, ROOT))


class RootArtifactParsingTest(unittest.TestCase):
    """A root's acceptance prose is policy input, not a unit artifact."""

    @staticmethod
    def _ticket(ticket_id):
        return """---
id: {ticket_id}
executor: orch-decompose
depends_on: []
write_scope: []
---

## Objective

Freeze the read-only acceptance without changing the checkout.

## Fixed inputs

## Completion test

- the read-only HTTP surface accepts only GET/HEAD requests | oracle: `rg -n read-only scripts/ui.py` | oracle_class: deterministic | provenance: pre-existing
- the read-only fixture export creates no derived files beneath codex/ | oracle: `rg -n malformed tests/fixtures/README.md` | oracle_class: deterministic | provenance: pre-existing
- the untracked HANDOFF.md invariant remains absent | oracle: `git status --porcelain -- HANDOFF.md` | oracle_class: deterministic | provenance: pre-existing
""".format(ticket_id=ticket_id)

    def test_only_a_top_level_root_skips_unit_artifact_extraction(self):
        siblings = {
            "00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR},
            "00-root.01": {
                "id": "00-root.01", "executor": cutcheck.ROOT_EXECUTOR
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            ticket_dir = Path(tmp)
            root = ticket_dir / "00-root.md"
            nested = ticket_dir / "00-root.01.md"
            root.write_text(self._ticket("00-root"), encoding="utf-8")
            nested.write_text(self._ticket("00-root.01"), encoding="utf-8")
            root_findings = cutcheck._check_ticket(root, ROOT, None, siblings)
            nested_findings = cutcheck._check_ticket(nested, ROOT, None, siblings)

        root_classes = [finding[2] for finding in root_findings]
        self.assertNotIn(cutcheck.MISSING_PATH, root_classes)
        self.assertNotIn(cutcheck.UNSCOPED_WRITE, root_classes)
        self.assertIn(cutcheck.MISSING_PATH, [finding[2] for finding in nested_findings])
        self.assertIn(cutcheck.UNSCOPED_WRITE, [finding[2] for finding in nested_findings])

    def test_a_top_level_root_keeps_acceptance_and_authority_diagnostics(self):
        ticket_text = """---
id: 00-root
executor: orch-decompose
depends_on: []
write_scope: [scripts/allowed.py]
excluded_actions: [never write scripts/allowed.py]
---

## Objective

Create one composite code gate at artifacts/gate.json; preserve caller
HANDOFF.md exactly invariant and the contract cited at docs/absent-proof.md:1.

## Fixed inputs

## Completion test

- the cumulative result writes scripts/outside_scope.py | oracle: `git diff baseline..HEAD -- scripts/tool.py` | oracle_class: deterministic | provenance: pre-existing
"""
        siblings = {
            "00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR},
        }
        with tempfile.TemporaryDirectory() as tmp:
            ticket = Path(tmp) / "00-root.md"
            ticket.write_text(ticket_text, encoding="utf-8")
            findings = cutcheck._check_ticket(ticket, ROOT, None, siblings)

        classes = [finding[2] for finding in findings]
        unscoped = {
            finding[3]
            for finding in findings
            if finding[2] == cutcheck.UNSCOPED_WRITE
        }
        self.assertIn(cutcheck.CUMULATIVE_RANGE, classes)
        self.assertIn(cutcheck.UNRESOLVED_CITATION, classes)
        self.assertIn(cutcheck.UNSCOPED_WRITE, classes)
        self.assertIn(cutcheck.SCOPE_CONTRADICTION, classes)
        self.assertIn("artifacts/gate.json", unscoped)
        # The root's own Objective still commits it; its acceptance describes
        # what the units write and commits it to nothing -- see
        # `FrozenAuthorityProseTest`.
        self.assertNotIn("scripts/outside_scope.py", unscoped)
        self.assertNotIn("HANDOFF.md", unscoped)


class ExecutorLegalityTest(unittest.TestCase):
    def setUp(self):
        self.result = run_cutcheck("cutcheck-f6-executor")
        self.lines = reported(self.result, cutcheck.FAMILY_6)

    def test_executor_set_exits_nonzero(self):
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)

    def test_an_executor_no_cell_of_the_pack_names_is_reported(self):
        lines = [line for line in self.lines if "03-alien" in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn(cutcheck.ILLEGAL_EXECUTOR, lines[0])
        self.assertIn("orch-render", lines[0])
        self.assertIn("orch-code-pack", lines[0])

    def test_the_packs_own_executor_cell_is_not_reported(self):
        self.assertNotIn("02-legal", "\n".join(finding_lines(self.result)))

    def test_the_surviving_engines_are_lawful_executors(self):
        """P4-3 deleted the engine prohibition with the two engines it named.
        Both survivors are lawful ticket executors, and neither script keeps a
        list of them: with nothing left to refuse, no code path branches on
        membership, so the library tree is the only statement of the set."""
        engines = {
            path.name
            for path in (ROOT / "skills" / "engines").iterdir()
            if path.is_dir()
        }
        self.assertEqual({"orch-frontier", "orch-loop"}, engines)
        self.assertFalse(hasattr(cutcheck, "ENGINE_EXECUTORS"))
        self.assertFalse(hasattr(tickets, "TICKET_EXECUTOR_ENGINES"))


class FrozenAuthorityProseTest(unittest.TestCase):
    """Whose Completion test can commit its item to a write.

    A root freezes the cumulative acceptance its units deliver and a
    `gate.verify` stub re-runs that acceptance; neither writes what its
    criteria describe, and both carry the frontmatter grant that says so. A
    criterion reading "records required-check-run/v1" therefore names the
    unit's artifact, and grading it against the frozen item's own grant
    convicts every honest cut of `unscoped-write`. A unit's Completion test
    still commits the unit, because a unit is what writes.
    """

    CRITERION = (
        "- the runner records required-check-run/v1 and maps exits 0/1/2"
        " | oracle: `git status --short`"
        " | oracle_class: deterministic | provenance: pre-existing"
    )

    def _ticket(self, ticket_id, executor):
        return """---
id: {ticket_id}
executor: {executor}
depends_on: []
write_scope: [scripts/allowed.py]
---

## Objective

Freeze the cumulative acceptance without changing the checkout.

## Fixed inputs

## Completion test

{criterion}
""".format(ticket_id=ticket_id, executor=executor, criterion=self.CRITERION)

    def _unscoped(self, ticket_id, executor, siblings):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / (ticket_id + ".md")
            path.write_text(self._ticket(ticket_id, executor), encoding="utf-8")
            findings = cutcheck._check_ticket(path, ROOT, None, siblings)
        return sorted(
            finding[3]
            for finding in findings
            if finding[2] == cutcheck.UNSCOPED_WRITE
        )

    SIBLINGS = {
        "00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR},
        "00-root.01": {"id": "00-root.01", "executor": "orch-tdd"},
        "00-root.gate.verify": {
            "id": "00-root.gate.verify", "executor": "orch-verify"
        },
    }

    def test_a_root_completion_test_commits_the_root_to_no_write(self):
        self.assertEqual([], self._unscoped("00-root", cutcheck.ROOT_EXECUTOR, self.SIBLINGS))

    def test_a_gate_verify_stub_completion_test_commits_it_to_no_write(self):
        self.assertEqual(
            [], self._unscoped("00-root.gate.verify", "orch-verify", self.SIBLINGS)
        )

    def test_the_same_criterion_on_a_unit_still_commits_the_unit(self):
        self.assertEqual(
            ["0/1/2", "required-check-run/v1"],
            self._unscoped("00-root.01", "orch-tdd", self.SIBLINGS),
        )
