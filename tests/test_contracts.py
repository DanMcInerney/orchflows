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


def read_at(relative):
    """Any repository file, by repository-relative path."""
    return (ROOT / relative).read_text(encoding="utf-8")


def read_at_flat(relative):
    """Any repository file, whitespace collapsed, so wrapped clauses match."""
    return re.sub(r"\s+", " ", read_at(relative))


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

    def test_checker_correction_authority_rides_the_write_scope(self):
        text = read_flat("work-item.md")
        self.assertIn(
            "A §10 checker corrects inside this same `write_scope`", text,
            "work-item.md does not carry the §10 checker's correction authority",
        )

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
        for name in (
            "work-item.md", "delegation.md", "pack-signature.md", "spec.md",
            "worklog.md", "verdict.md", "composition.md", "result.md",
        ):
            text = read(name)
            self.assertNotIn("task-result.md", text, f"{name} still references deleted task-result.md")
            self.assertNotIn("handoff.md", text, f"{name} still references deleted handoff.md")


class TestResultContract(unittest.TestCase):
    def test_contains_the_envelope_grammar(self):
        text = read("result.md")
        for token in (
            "`status`", "`result`", "`verification`",
            "complete", "blocked", "stalled", "limited", "failed",
        ):
            self.assertIn(token, text, f"result.md is missing {token!r}")

    def test_binds_the_dispatchable_units_and_exempts_evaluators(self):
        text = read_flat("result.md")
        for unit in (
            "orch-deliver", "orch-task", "orch-investigate", "orch-loop",
            "orch-frontier", "orch-compose",
        ):
            self.assertIn(f"`{unit}`", text, f"result.md does not bind {unit}")
        self.assertIn("every composition", text, "result.md does not bind compositions")
        self.assertIn(
            "Evaluators and utilities are exempt", text,
            "result.md is missing the evaluator/utility exemption",
        )


class TestWorklogContract(unittest.TestCase):
    def test_parked_only_is_open_and_distinct_from_in_progress(self):
        text = read_flat("worklog.md")
        self.assertIn(
            "A parked-only pause is not an exit: `terminal` stays empty", text,
            "worklog.md does not keep a parked-only pause off the terminal set",
        )
        self.assertIn(
            "Parked is not in progress: no item is under way", text,
            "worklog.md does not distinguish parked-only from in progress",
        )


class TestCompositionContract(unittest.TestCase):
    def test_contains_the_composition_fields(self):
        text = read("composition.md")
        for token in ("`name`", "`description`", "`entry`", "`steps`", "`edges`", "`invariants`", "`done_check`"):
            self.assertIn(token, text, f"composition.md is missing {token!r}")
        for entry in ("`routed`", "`named`", "`scheduled`"):
            self.assertIn(entry, text, f"composition.md is missing entry value {entry!r}")
        for combinator in ("`seq`", "`par`", "`loop`"):
            self.assertIn(combinator, text, f"composition.md is missing combinator {combinator!r}")

    def test_admission_rejects_missing_invariants_or_done_check(self):
        text = read_flat("composition.md")
        self.assertIn(
            "rejects a composition missing `invariants` or `done_check`", text,
            "composition.md is missing the admission-rejection sentence",
        )


class TestSpecContract(unittest.TestCase):
    def test_single_editor_and_partial_gap(self):
        text = read_flat("spec.md")
        self.assertIn(
            "`orch-spec` is the spec's only editor", text,
            "spec.md does not name orch-spec as the spec's only editor",
        )
        self.assertNotIn(
            "orch-decompose` repairs it in place", text,
            "spec.md still names orch-decompose as a spec editor",
        )
        self.assertIn(
            "a decision gap naming exactly those criteria", text,
            "spec.md does not state that a defect or uncoverable criterion "
            "returns a decision gap naming exactly those criteria",
        )
        self.assertIn(
            "the covered remainder is still cut and still executed", text,
            "spec.md does not state that the covered remainder is still cut and executed",
        )


class TestDelegationContract(unittest.TestCase):
    def test_ticket_path_supplies_the_six_parts_by_reference(self):
        text = read_flat("delegation.md")
        self.assertIn(
            "may supply the six parts by reference to the ticket path", text,
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


class TestVocabularyDefinesShapeChange(unittest.TestCase):
    """`docs/vocabulary.md` owns the term the T0 supersession gate in
    `AGENTS.md` and `ARCHITECTURE.md` invokes. The subject is the entry,
    never a corpus count of the words."""

    TERM = "**shape change**"

    def entry(self):
        flat = read_at_flat("docs/vocabulary.md")
        self.assertEqual(
            flat.count(self.TERM), 1,
            f"docs/vocabulary.md must carry the {self.TERM} entry exactly once",
        )
        return flat.split(self.TERM, 1)[1].split(" - **", 1)[0]

    def test_defines_the_term(self):
        entry = self.entry()
        self.assertIn(
            "a change to a named field or enum", entry,
            "the shape change entry does not state what moves",
        )
        self.assertIn(
            "T0", entry,
            "the shape change entry does not scope the term to T0",
        )

    def test_states_the_converse_a_prose_only_edit_needs(self):
        self.assertIn(
            "without a supersession PR", self.entry(),
            "the shape change entry does not state the converse: a T0 edit "
            "moving no field or enum re-pins without a supersession PR",
        )

    def test_lands_beside_contract_under_structure(self):
        flat = read_at_flat("docs/vocabulary.md")
        structure = flat.split("## Structure", 1)[1].split("## Work", 1)[0]
        self.assertIn(
            self.TERM, structure,
            "the shape change entry must sit under ## Structure, where a "
            "reader of the `contract` entry finds it",
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
