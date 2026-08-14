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


class TestVisibilityChannelLaw(unittest.TestCase):
    """`rules/visibility.md` §6 owns the two-channel law. Its content
    channel must hold for all four packs, whose workspace cells are a git
    tree, a git-plus-render tree, a document tree and an evidence store —
    only the first two merge. Its scope is all of `.orch/`."""

    def section(self):
        return read_at_flat("rules/visibility.md")

    def test_content_channel_is_the_packs_workspace_cell(self):
        text = self.section()
        self.assertIn(
            "the pack's workspace cell", text,
            "visibility.md §6 does not name the pack's workspace cell as what "
            "content leaves the workspace by; a merge-only channel is false "
            "for the content and research packs",
        )

    def test_governs_all_of_orch(self):
        self.assertIn(
            "not only `runs/` and `tickets/`", self.section(),
            "visibility.md §6 does not state that it governs all of `.orch/`, "
            "not only `runs/` and `tickets/`",
        )

    def test_the_two_channel_law_survives_the_rewrite(self):
        text = self.section()
        for clause in ("two channels", "never cross", "file tools", "installed scripts"):
            self.assertIn(
                clause, text,
                f"visibility.md §6 lost {clause!r}: the merge clause is "
                "re-expressed, never deleted",
            )


class TestVerificationHomelessLaws(unittest.TestCase):
    """`rules/verification.md` owns three laws no other file states: §1's
    truncation prohibition, which `scripts/cutcheck.py` enforces and now
    cites; §7's reuse precondition for a gate that returns findings; and
    §11's two cross-step sentences, frozen byte-for-byte against the copy
    `S-CUT`'s spec carries. The last two are never reworded here."""

    def law(self):
        return read_at_flat("rules/verification.md")

    def test_a_truncated_transcript_is_not_the_oracles_output(self):
        text = self.law()
        self.assertIn(
            "A truncated transcript is not the oracle's output", text,
            "verification.md §1 does not state that a truncated transcript "
            "is not the oracle's output",
        )
        for pipe in ("`| tail`", "`| head`"):
            self.assertIn(
                pipe, text,
                f"verification.md §1 does not name {pipe} as a reader that "
                "reports the pipe's status rather than the command's",
            )
        self.assertIn(
            "redirecting to a file and grepping it", text,
            "verification.md §1 names no method in place of the pipes it forbids",
        )

    def test_a_gate_returning_findings_moves_the_result_identity(self):
        text = self.law()
        self.assertIn(
            "A gate returning findings moves the result identity", text,
            "verification.md §7 does not state that a gate returning findings "
            "moves the result identity",
        )
        self.assertIn(
            "reusable only where the correction left the covered identity "
            "unchanged", text,
            "verification.md §7 does not qualify reuse by what the correction "
            "left unchanged",
        )

    def test_carries_the_frozen_cutcheck_exit_sentence_verbatim(self):
        self.assertIn(
            "Cutcheck's exit 0 means no finding whose class lies outside "
            "the advisory set, not that the set is clean: an advisory "
            "finding is reported and exits 0.",
            self.law(),
            "verification.md §11 lost the frozen cross-step sentence on "
            "cutcheck's exit 0; it is byte-frozen against `S-CUT`'s copy and "
            "is re-copied, never reworded",
        )

    def test_carries_the_frozen_host_portability_sentence_verbatim(self):
        self.assertIn(
            "A cut verdict is not portable between hosts. An oracle naming "
            "an interpreter one host lacks is reported there as "
            "`unrunnable-oracle` and is silent here, so a verdict is read "
            "only on the host that produced it.",
            self.law(),
            "verification.md §11 lost the frozen cross-step sentence on host "
            "portability; it is byte-frozen against `S-CUT`'s copy and is "
            "re-copied, never reworded",
        )


class TestWorkItemCitationLaws(unittest.TestCase):
    """`contracts/work-item.md` resolves three collisions no other file
    owns: whose `status` a `Return fields` list names, who sets
    `isolation` and when the join grades it, and what a fixed input may
    cite."""

    def contract(self):
        return read_flat("work-item.md")

    def test_return_fields_status_is_the_result_envelopes(self):
        text = self.contract()
        self.assertIn(
            "A `status` in this list is the result envelope's", text,
            "work-item.md's `## Return fields` bullet does not say a `status` "
            "named there is the result envelope's",
        )
        self.assertIn(
            "[result.md](result.md)", text,
            "work-item.md's `## Return fields` bullet does not cite result.md "
            "as the envelope owning that `status`",
        )
        self.assertIn(
            "never the ticket frontmatter key above, which only the join sets",
            text,
            "work-item.md's `## Return fields` bullet does not exclude the "
            "ticket frontmatter key the join alone sets",
        )

    def test_isolation_names_its_only_setter_and_the_grading_order(self):
        text = self.contract()
        self.assertIn(
            "The decomposer is the field's only setter", text,
            "work-item.md's `isolation` bullet does not name the decomposer as "
            "the field's only setter",
        )
        self.assertIn(
            "`scripts/workspace.py check`", text,
            "work-item.md's `isolation` bullet no longer names "
            "`scripts/workspace.py check` as what grades the declaration",
        )
        self.assertIn(
            "before the merge, because afterwards the item's tip is already an "
            "ancestor of the run tip and a stamped item exits clean by design",
            text,
            "work-item.md's `isolation` bullet does not order "
            "`scripts/workspace.py check` before the merge, nor give the "
            "reason the check decides nothing after it",
        )

    def test_fixed_inputs_forbid_a_line_number_by_citing_identity(self):
        text = self.contract()
        self.assertIn(
            "never prose copies", text,
            "work-item.md's `## Fixed inputs` bullet lost its existing "
            "prohibition on a prose copy",
        )
        self.assertIn(
            "never a line number", text,
            "work-item.md's `## Fixed inputs` bullet does not forbid citing a "
            "fixed input by line number",
        )
        self.assertIn(
            "[docs/vocabulary.md](../docs/vocabulary.md)'s `identity` entry",
            text,
            "work-item.md's `## Fixed inputs` bullet does not resolve the "
            "line-number prohibition against the `identity` entry that owns "
            "it; the citation is the property, never a restatement",
        )


class TestWorklogNoteLaws(unittest.TestCase):
    """`contracts/worklog.md` owns note ordering, the terminal-section
    boundary, and the refusal that keeps an artifact write from
    overwriting silently. `scripts/tickets.py` implements them."""

    def contract(self):
        return read_flat("worklog.md")

    def test_notes_append_in_occurrence_order(self):
        self.assertIn(
            "Notes append in occurrence order", self.contract(),
            "worklog.md does not state that notes append in occurrence order",
        )

    def test_no_note_is_written_past_a_terminal_section(self):
        text = self.contract()
        self.assertIn(
            "no note is written past a terminal section", text,
            "worklog.md does not close the file at its terminal section",
        )
        self.assertIn(
            "carries no terminal placeholder until it closes", text,
            "worklog.md does not draw the consequence that an open run has no "
            "terminal placeholder for a note to land past",
        )

    def test_an_existing_artifact_is_not_overwritten_silently(self):
        text = self.contract()
        self.assertIn(
            "Writing an artifact that already exists is refused by default",
            text,
            "worklog.md does not refuse a write over an existing artifact",
        )
        self.assertIn(
            "the refusal naming the existing path", text,
            "worklog.md's overwrite refusal does not name the existing path, "
            "so the refusal is not actionable",
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
