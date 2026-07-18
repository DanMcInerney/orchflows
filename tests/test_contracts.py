"""Freezes the load-bearing shape of the T0 contracts and the
description budget every skill must respect."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "contracts"
SKILLS = ROOT / "skills"


def read(name):
    return (CONTRACTS / name).read_text(encoding="utf-8")


def read_flat(name):
    """Contract text with whitespace collapsed, so wrapped clauses match."""
    return re.sub(r"\s+", " ", read(name))


class TestVerdictContract(unittest.TestCase):
    def test_contains_the_verdict_grammar(self):
        text = read("verdict.md")
        for token in ("PASS", "FAIL", "UNVERIFIED", "oracle_class", "deterministic", "judged", "evidence"):
            self.assertIn(token, text, f"verdict.md is missing {token!r}")


class TestWorkItemContract(unittest.TestCase):
    def test_lists_the_frontmatter_keys(self):
        text = read("work-item.md")
        for key in (
            "id", "run", "status", "executor", "depends_on", "write_scope",
            "bound", "claimed_by", "claimed_at",
        ):
            self.assertIn(f"`{key}`", text, f"work-item.md is missing frontmatter key {key!r}")

    def test_lists_all_body_section_headers(self):
        text = read("work-item.md")
        for header in (
            "Objective", "Fixed inputs", "Completion test", "Return fields",
            "Result", "Verification", "Feedback", "Risks",
        ):
            self.assertIn(f"## {header}", text, f"work-item.md is missing body section '## {header}'")

    def test_status_enum_includes_pending_as_non_terminal(self):
        text = read("work-item.md")
        self.assertIn("`pending`", text, "work-item.md is missing the `pending` status")
        self.assertIn("orch-frontier", text, "work-item.md does not name orch-frontier as the pending->ready owner")

    def test_ticket_result_write_is_outside_write_scope(self):
        text = read("work-item.md")
        self.assertIn("outside `write_scope`", text, "work-item.md does not state the ticket write is outside write_scope")

    def test_status_enum_includes_suspended_as_non_terminal(self):
        text = read_flat("work-item.md")
        self.assertIn("`suspended`", text, "work-item.md is missing the `suspended` status")
        self.assertIn(
            "the ticket stays claimed, resumable from its `## Handoff`", text,
            "work-item.md does not define suspended as the resumable non-terminal wait",
        )

    def test_join_alone_writes_terminal_status(self):
        text = read_flat("work-item.md")
        self.assertIn(
            "the join alone sets terminal `status`", text,
            "work-item.md does not reserve terminal status to the join",
        )
        self.assertIn(
            "is set only by the join (`orch-integrate`), never by the executor", text,
            "work-item.md does not name the join as the sole terminal-status writer",
        )

    def test_handoff_section_carries_the_three_verbatim_clauses(self):
        text = read_flat("work-item.md")
        self.assertIn("`## Handoff`", text, "work-item.md is missing the optional ## Handoff section")
        for clause in (
            "A handoff is complete when a fresh agent can resume from it "
            "without reading the suspended agent's transcript.",
            "Suspension and escalation each happen at most once per "
            "ticket; a second is a terminal `blocked`.",
            "Compact to identities and verdicts; redact transcript prose.",
        ):
            self.assertIn(clause, text, f"work-item.md ## Handoff is missing the verbatim clause {clause!r}")

    def test_handoff_resumption_reuses_accepted_evidence(self):
        text = read_flat("work-item.md")
        self.assertIn(
            "On resumption, accepted evidence stays accepted — re-verify "
            "only entries the handoff marks unverified or invalidated.",
            text, "work-item.md ## Handoff is missing the resumption-reuse sentence",
        )

    def test_filing_law_lands_at_artifact_primacy_strength(self):
        text = read_flat("work-item.md")
        self.assertIn(
            "results land as cited artifacts in the ticket", text,
            "work-item.md is missing the filing law",
        )
        self.assertIn(
            "never as extra return fields", text,
            "work-item.md filing law does not forbid extra return fields",
        )
        self.assertIn(
            "rules/delegation.md §10", text,
            "work-item.md filing law does not cite its owner rules/delegation.md §10",
        )

    def test_additive_carriage_sentence(self):
        text = read_flat("work-item.md")
        self.assertIn(
            "An item carries verbatim every spec field its executor's Require names.",
            text, "work-item.md is missing the additive carriage sentence",
        )

    def test_ticket_statuses_disambiguated_from_run_terminal_set(self):
        text = read_flat("work-item.md")
        self.assertIn(
            "`stalled` exists only at run level, `suspended` only at ticket level",
            text, "work-item.md does not disambiguate ticket statuses from the run-level terminal set",
        )

    def test_no_reference_to_the_dead_contracts(self):
        for name in ("work-item.md", "delegation.md", "pack-signature.md", "spec.md", "worklog.md", "verdict.md"):
            text = read(name)
            self.assertNotIn("task-result.md", text, f"{name} still references deleted task-result.md")
            self.assertNotIn("handoff.md", text, f"{name} still references deleted handoff.md")


class TestDelegationContract(unittest.TestCase):
    def test_ticket_path_supplies_the_five_parts_by_reference(self):
        text = read_flat("delegation.md")
        self.assertIn(
            "may supply the five parts by reference to the ticket path", text,
            "delegation.md is missing the ticket-path-by-reference sentence",
        )

    def test_non_empty_write_scope_contracts_for_changed_artifacts(self):
        text = read_flat("delegation.md")
        self.assertIn(
            "a dispatch granting a non-empty write scope contracts for `changed_artifacts` among them",
            text, "delegation.md is missing the changed_artifacts contract clause",
        )
        self.assertIn(
            "rejected at the join regardless of its verdicts", text,
            "delegation.md is missing the exceeds-scope rejection clause",
        )

    def test_packet_only_exclusion_fallback(self):
        text = read_flat("delegation.md")
        self.assertIn(
            "a packet-only child stops and returns partial results plus the exclusion hit",
            text, "delegation.md is missing the packet-only exclusion fallback",
        )
        self.assertIn(
            "rules/composition.md rule 8", text,
            "delegation.md packet-only fallback does not cite composition rule 8",
        )
        self.assertIn(
            "re-dispatches with a ticket when resume matters", text,
            "delegation.md is missing the caller's ticket re-dispatch clause",
        )

    def test_work_item_suspension_routes_through_the_ticket_handoff(self):
        text = read_flat("delegation.md")
        self.assertIn(
            "a work-item dispatch suspends through the ticket's `## Handoff`",
            text, "delegation.md does not route work-item suspension through the ticket's ## Handoff",
        )


class TestSkillDescriptions(unittest.TestCase):
    def test_every_skill_description_is_at_most_140_chars(self):
        skill_files = sorted(SKILLS.glob("*/*/SKILL.md"))
        self.assertTrue(skill_files, "expected at least one skills/*/*/SKILL.md")
        for skill_md in skill_files:
            text = skill_md.read_text(encoding="utf-8")
            match = re.search(r"^description:\s*(.*)$", text, re.MULTILINE)
            self.assertIsNotNone(match, f"{skill_md} has no 'description:' in frontmatter")
            desc = match.group(1).strip()
            self.assertLessEqual(
                len(desc), 140,
                f"{skill_md} description is {len(desc)} chars (>140): {desc!r}",
            )


if __name__ == "__main__":
    unittest.main()
