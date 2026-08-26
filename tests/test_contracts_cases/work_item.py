"""Cases for the work-item contract and its citation laws."""

import hashlib
import json
import unittest
from pathlib import Path

from tests.test_contracts_cases.support import (
    read,
    read_at_flat,
    read_bullet_flat,
    read_flat,
)

ROOT = Path(__file__).resolve().parents[2]


class TestWorkItemContract(unittest.TestCase):
    def test_lists_the_frontmatter_keys(self):
        text = read("work-item.md")
        for key in (
            "id", "run", "status", "executor", "depends_on", "write_scope",
            "bound", "claimed_by", "claimed_at",
        ):
            self.assertIn(
                f"`{key}`", text,
                f"work-item.md is missing frontmatter key {key!r}",
            )

    def test_lists_all_body_section_headers(self):
        text = read("work-item.md")
        for header in (
            "Objective", "Fixed inputs", "Completion test", "Return fields",
            "Result", "Verification", "Feedback", "Risks",
        ):
            self.assertIn(
                f"## {header}", text,
                f"work-item.md is missing body section '## {header}'",
            )

    def test_body_sections_are_listed_in_contract_order(self):
        full = read("work-item.md")
        text = full[full.index("- `## Objective`"):].split("\n## Dispatch", 1)[0]
        order = [
            "Objective", "Fixed inputs", "Completion test", "Return fields",
            "Result", "Verification", "Feedback", "Risks", "Carry", "Handoff",
        ]
        seen = [text.index(f"`## {h}`") for h in order]
        self.assertEqual(
            seen, sorted(seen),
            "work-item.md lists the body sections out of contract order",
        )

    def test_status_enum_is_the_nine_ticket_statuses(self):
        text = read("work-item.md")
        for status in (
            "pending", "ready", "claimed", "suspended", "complete",
            "blocked", "stalled", "failed", "limited",
        ):
            self.assertIn(
                f"`{status}`", text,
                f"work-item.md is missing the `{status}` status",
            )
        self.assertIn(
            "orch-frontier", text,
            "work-item.md does not name orch-frontier as the pending->ready owner",
        )
        self.assertIn(
            "`orch-integrate`", text,
            "work-item.md does not name the join as the terminal-status writer",
        )

    def test_absorbs_the_four_supersession_sections(self):
        text = read("work-item.md")
        for heading in (
            "## Dispatch", "## Root ticket", "## Template and stub",
            "## Executor form",
        ):
            self.assertIn(
                f"\n{heading}\n", text,
                f"work-item.md is missing the '{heading}' section the "
                "spec.md/delegation.md absorption adds",
            )

    def test_dispatch_section_names_the_six_packet_parts(self):
        text = read("work-item.md")
        for part in (
            "`objective`", "`inputs`", "`authority`", "`bounds`",
            "`return_contract`", "`reply_to`",
        ):
            self.assertIn(
                part, text,
                f"work-item.md does not name the packet part {part}",
            )

    def test_root_ticket_names_its_stamp_and_its_gate_subtree(self):
        text = read("work-item.md")
        for token in (
            "`orch-decompose`", "`required_spec_fields`", "`<id>.NN`",
            "`<id>.gate.critique.<lens>`", "`<id>.gate.repair`",
            "`<id>.gate.verify`", "`plan_gate`",
        ):
            self.assertIn(
                token, text,
                f"work-item.md's root ticket does not name {token}",
            )

    def test_verify_gate_inputs_pin_the_canonical_mutation_plan_contract(self):
        text = read_flat("work-item.md")
        for token in (
            "`mutation-plan-paths`",
            "sorted unique repository-relative POSIX paths",
            "canonical UTF-8 JSON",
            # The record shape itself, not a loose `sha256:...` token: the
            # identity's form is only pinned where the field carrying it is.
            '`{"identity":"sha256:<64 lowercase hex>","paths":["<path>"]}`',
            "refusing gate creation",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_template_and_stub_names_its_shape_and_its_owner(self):
        text = read("work-item.md")
        for token in (
            "`template.md`", "`{{placeholder}}`", "terminal stub",
            "tickets.py instantiate", "`template_defects`",
        ):
            self.assertIn(
                token, text,
                f"work-item.md's template register does not name {token}",
            )

    def test_executor_form_admits_a_tested_script(self):
        text = read("work-item.md")
        self.assertIn(
            "`script:<repo-relative path>`", text,
            "work-item.md does not admit the `script:` executor form",
        )

    def test_the_lease_timer_belongs_to_the_script_that_implements_it(self):
        """Shape here, the timer at its code owner -- and only there.

        The contract used to state the 60-minute substitution and the
        artifact-motion rule itself. `scripts/tickets_bound.py` is what
        substitutes and what measures motion, so the contract now names it
        and states neither number nor rule.
        """
        contract = read_flat("work-item.md")
        self.assertIn(
            "`scripts/tickets_bound.py`", contract,
            "work-item.md's lease does not name the owner of its timer",
        )
        for token in ("wall clock", "60 minutes", "staleness"):
            with self.subTest(token=token):
                self.assertNotIn(
                    token, contract,
                    f"work-item.md still states the timer's {token!r}",
                )
        owner = (ROOT / "scripts" / "tickets_bound.py").read_text(
            encoding="utf-8"
        )
        for token in ("60 minutes", "wall clock", "`## Result`"):
            with self.subTest(owner_token=token):
                self.assertIn(
                    token, owner,
                    f"scripts/tickets_bound.py does not carry {token!r}, so "
                    "the relocated lease rule reached no owner",
                )

    def test_the_relocated_timer_prose_says_what_its_module_computes(self):
        """Markers are not meaning: bind the sentence to the substitution.

        The marker check above passed a docstring that said the default is
        substituted "when the bound is not [a duration]" -- the pre-widening
        behavior `parse_bound` exists to end. Three assertions over the code
        the prose describes, so the same false sentence cannot return: the
        number the prose names is the constant, the constant is reached only
        by a bound the grammar cannot read, and a countable non-duration
        bound is aged at its own conversion rather than at the default.
        """
        from scripts import tickets_bound as bound

        self.assertEqual(
            60, bound.DEFAULT_BOUND_MINUTES,
            "the docstring's '60 minutes' is no longer the constant it names",
        )
        self.assertEqual(
            (60, "other"), bound.parse_bound("banana"),
            "an unreadable bound no longer reaches the stated default",
        )
        self.assertNotEqual(
            bound.DEFAULT_BOUND_MINUTES, bound.parse_bound("40 tool calls")[0],
            "a tool-call bound ages at the default again, so any prose "
            "saying the default covers every non-duration bound is true "
            "only because the grammar regressed",
        )

    def test_carries_no_compatibility_floor(self):
        self.assertNotIn(
            "Compatibility floor", read("work-item.md"),
            "work-item.md still carries the changelog the supersession deletes",
        )

    def test_no_reference_to_the_dead_contracts(self):
        for name in (
            "work-item.md", "pack-signature.md", "worklog.md", "verdict.md",
            "result.md",
        ):
            text = read(name)
            for dead in (
                "task-result.md", "handoff.md", "(spec.md)", "(delegation.md)",
                "contracts/spec.md", "contracts/delegation.md",
                "(composition.md)", "contracts/composition.md",
            ):
                self.assertNotIn(
                    dead, text,
                    f"{name} still references deleted {dead}",
                )


class TestWorkItemCitationLaws(unittest.TestCase):
    """Placement-sensitive laws owned by work-item.md bullets."""

    def bullet(self, marker):
        return read_bullet_flat("work-item.md", marker)

    def test_return_fields_status_is_the_result_envelopes(self):
        text = self.bullet("`## Return fields` — packet `return_contract`")
        for token in ("`status`", "result envelope"):
            self.assertIn(
                token, text,
                f"work-item.md's `## Return fields` bullet does not name "
                f"{token!r}, so it does not say a `status` named there is the "
                "result envelope's",
            )
        self.assertIn(
            "[result.md](result.md)", text,
            "work-item.md's `## Return fields` bullet does not cite result.md "
            "as the envelope owning that `status`",
        )
        for token in ("never", "frontmatter key"):
            self.assertIn(
                token, text,
                f"work-item.md's `## Return fields` bullet does not name "
                f"{token!r}, so it does not exclude the ticket frontmatter key",
            )

    def test_isolation_names_its_only_setter_and_the_grading_order(self):
        text = self.bullet("`isolation` — packet `authority`")
        for token, why in (
            (
                "decomposer",
                "work-item.md's `isolation` bullet does not name the decomposer "
                "as the field's only setter",
            ),
            (
                "only setter",
                "work-item.md's `isolation` bullet does not make the decomposer "
                "the field's only setter",
            ),
            (
                "`scripts/workspace.py check`",
                "work-item.md's `isolation` bullet no longer names "
                "`scripts/workspace.py check` as what grades the declaration",
            ),
            (
                "before assembly",
                "work-item.md's `isolation` bullet does not order "
                "`scripts/workspace.py check` before assembly",
            ),
        ):
            with self.subTest(token=token):
                self.assertIn(token, text, why)


class TestV1AdmissionContract(unittest.TestCase):
    def bullet(self, marker):
        return read_bullet_flat("work-item.md", marker)

    def test_frontmatter_owns_admission_cohort_and_mutation_plan(self):
        text = read("work-item.md")
        for token in ("`admission`", "`cohort`", "`mutations`", "v1:pending", "create", "change", "delete", "write"):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_fixed_inputs_and_return_size_have_canonical_grammars(self):
        text = read("work-item.md")
        for token in (
            '- input: {"identity":{...},"name":"baseline","type":"identity"}',
            '- input: {"name":"question","type":"literal","value":"exact value"}',
            'return-size: {"counter":"words-v1","maximum":3000,"minimum-complete":"return-fixture","target":"result"}',
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_work_item_keeps_generic_authority_while_tdd_owns_its_procedure(self):
        contract = read("work-item.md")
        procedure = (ROOT / "skills" / "instances" / "orch-tdd" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("`orch-tdd`", contract)
        for token in ("verified slice", "ticket workspace", "join", "integration"):
            with self.subTest(token=token):
                self.assertIn(token, procedure)

    def test_architecture_and_pack_signature_own_lower_adapters(self):
        architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
        signature = read("pack-signature.md")
        for token in ("tickets_admission.py", "tickets_inputs.py", "tickets_scope.py", "tickets_format.py"):
            self.assertIn(token, architecture)
        for token in ("stable mechanism key", "adapter", "packs remain data"):
            self.assertIn(token, signature)
        format_source = (ROOT / "scripts" / "tickets_format.py").read_text(encoding="utf-8")
        admission_source = (ROOT / "scripts" / "tickets_admission.py").read_text(encoding="utf-8")
        cutcheck_source = (ROOT / "scripts" / "cutcheck_ticket.py").read_text(encoding="utf-8")
        for owner in ("parse_mutations", "parse_return_size", "parse_result_identity", "count_return_text"):
            self.assertIn(f"def {owner}", format_source)
            self.assertNotIn(f"def {owner}", admission_source)
        self.assertNotIn("tickets_admission", cutcheck_source)

    def test_decomposer_cuts_one_cohort_with_typed_inputs_and_mutations(self):
        text = (ROOT / "skills" / "kernel" / "orch-decompose" / "SKILL.md").read_text(encoding="utf-8")
        for token in ("--cohort", "--input", "--mutation", "canonical JSON", "stamped workspace cell"):
            with self.subTest(token=token):
                self.assertIn(token, text)
        self.assertNotIn("--mutation create|change|delete|write", text)

    def test_decomposer_names_version_aware_v1_and_v2_member_emission(self):
        lines = (ROOT / "skills" / "kernel" / "orch-decompose" / "SKILL.md").read_text(
            encoding="utf-8"
        ).splitlines()
        rows = {}
        for line in lines:
            if line.startswith(("| `mandatory-v2` |", "| `legacy-v1` |")):
                cells = [cell.strip() for cell in line.strip("|").split("|")]
                rows[cells[0].strip("`")] = cells[1:]
        self.assertEqual(
            {
                "mandatory-v2": [
                    "candidate file",
                    "exact inherited",
                    "absent",
                    "`tickets.py new <run> --file <candidate>`",
                ],
                "legacy-v1": [
                    "arguments",
                    "absent",
                    "`v1:root:<root>`",
                    "`tickets.py new <run> <id> --cohort v1:root:<root>`",
                ],
            },
            rows,
        )

    def test_result_clause_shape_and_actual_enforcement_have_distinct_owners(self):
        work_item = read("work-item.md")
        result = read("result.md")
        self.assertIn("return-size:", work_item)
        self.assertNotIn("set-status complete", work_item)
        self.assertIn("result: <canonical JSON identity payload>", result)
        self.assertIn("set-status complete", result)

    def test_pack_workspace_cells_are_declarative_records(self):
        for relative in ("packs/orch-code-pack/SKILL.md", "packs/orch-design-pack/SKILL.md"):
            cell = next(line for line in (ROOT / relative).read_text(encoding="utf-8").splitlines() if line.startswith("| workspace |"))
            for control in (" when ", " if ", "refuse", "stop", "join grades", "merge refuses"):
                with self.subTest(relative=relative, control=control):
                    self.assertNotIn(control, cell.lower())

    def test_integrate_assigns_result_grade_defects_to_their_owner(self):
        text = (ROOT / "skills" / "kernel" / "orch-integrate" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("reject(caller)", text)
        self.assertIn("reject(child)", text)

    def test_fixed_inputs_forbid_an_unpinned_coordinate_by_citing_identity(self):
        text = self.bullet("`## Fixed inputs` — packet `inputs`")
        for token, why in (
            (
                "never prose copies",
                "work-item.md's `## Fixed inputs` bullet lost its existing "
                "prohibition on a prose copy",
            ),
            (
                "unpinned coordinate",
                "work-item.md's `## Fixed inputs` bullet does not forbid citing "
                "a fixed input by an unpinned coordinate",
            ),
            (
                "`identity` entry",
                "work-item.md's `## Fixed inputs` bullet does not resolve the "
                "line-number prohibition against the `identity` entry that owns "
                "it; the citation is the property, never a restatement",
            ),
        ):
            with self.subTest(token=token):
                self.assertIn(token, text, why)


class WorkItemV2ContractTest(unittest.TestCase):
    def test_v2_frontmatter_exposes_generation_region_and_seal_fields(self):
        text = read("work-item.md")
        for field in (
            "root_generation",
            "cut_generation",
            "ownership_regions",
            "assignment_seal",
        ):
            with self.subTest(field=field):
                self.assertIn(f"`{field}`", text)

    def test_the_contract_states_the_v2_shapes_and_defers_their_law(self):
        """Shape here, law at rules/topology.md §8-§11.

        The contract used to restate topology's digest boundaries, selector
        list, seal timing and migration clauses almost verbatim -- the
        near-duplicates `tools/validate.py` reports at 0.96 and 1.00. What
        it owns is the form each field takes; the rest is cited.
        """
        text = read("work-item.md")
        for token in (
            "`v2:root:<root-id>:<ordinal>:sha256:<digest>`",
            "`v2:cut:<root-id>:<ordinal>:sha256:<digest>`",
            '"artifact"',
            '"owner"',
            '"selector"',
            '"kind"',
            '"value"',
            '"merge_oracle"',
            "`sha256:<digest>`",
            "`objective`",
            "`inputs`",
            "`authority`",
            "`dependencies`",
            "`acceptance`",
            "`executor`",
            "[rules/topology.md](../rules/topology.md) §8–§11",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)
        for restated in (
            "coverage-map digest",
            "self-referential generation fields",
            "`json-pointer`",
            "string inequality",
        ):
            with self.subTest(restated=restated):
                self.assertNotIn(
                    restated, text,
                    f"work-item.md restates topology's {restated!r}",
                )
        topology = read_at_flat("rules/topology.md")
        for token in (
            "coverage-map digest",
            "self-referential generation fields",
            "JSON Pointer",
            "string inequality",
        ):
            with self.subTest(owner_token=token):
                self.assertIn(token, topology)

    def test_executor_owned_sections_stay_append_only_under_v2(self):
        text = read("work-item.md")
        for token in (
            "`## Result`",
            "`## Verification`",
            "`## Feedback`",
            "`## Risks`",
            "`## Handoff`",
            "append-only",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_absent_v2_fields_preserve_v1_without_reinterpretation(self):
        text = read_flat("work-item.md")
        for token in (
            "absence of all four v2 fields",
            "v1",
            "no v1 value is reinterpreted",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)
        topology = read_at_flat("rules/topology.md")
        for token in (
            "claimed or terminal v1",
            "pending or ready v1",
            "successor or new v2 root",
        ):
            with self.subTest(owner_token=token):
                self.assertIn(token, topology)

    def test_t0_supersession_is_explicit_and_contract_bytes_are_pinned(self):
        work_item = read("work-item.md")
        signature = read("pack-signature.md")
        for name, text in (
            ("work-item.md", work_item),
            ("pack-signature.md", signature),
        ):
            with self.subTest(contract=name):
                self.assertIn("## T0 supersession", text)
                self.assertIn("tests/pins.json", text)

        pins = json.loads((ROOT / "tests" / "pins.json").read_text(encoding="utf-8"))
        for name, text in (
            ("work-item.md", work_item),
            ("pack-signature.md", signature),
        ):
            with self.subTest(pin=name):
                self.assertEqual(
                    pins[name],
                    hashlib.sha256(text.encode("utf-8")).hexdigest(),
                )
