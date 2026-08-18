"""Cases for the work-item contract and its citation laws."""

import unittest

from tests.test_contracts_cases.support import (
    read,
    read_bullet_flat,
    read_flat,
)


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
            "Result", "Verification", "Feedback", "Risks", "Handoff",
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

    def test_the_lease_runs_on_artifact_motion_not_wall_clock(self):
        text = read_flat("work-item.md")
        self.assertEqual(
            text.count("wall clock"), 1,
            "work-item.md names wall clock outside the one negating clause",
        )
        self.assertIn(
            "60 minutes", text,
            "work-item.md's lease drops its default duration",
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
                "before the merge",
                "work-item.md's `isolation` bullet does not order "
                "`scripts/workspace.py check` before the merge",
            ),
        ):
            with self.subTest(token=token):
                self.assertIn(token, text, why)

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
