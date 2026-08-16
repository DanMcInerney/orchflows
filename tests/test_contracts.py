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


def read_clause_flat(relative, number):
    """One numbered clause of a rules file, whitespace collapsed. Scopes an
    assertion to the clause that owns the law, so a sentence landing in a
    neighbouring clause cannot satisfy it."""
    match = re.search(
        rf"(?m)^{number}\. (.*?)(?=^\d+\. |\Z)", read_at(relative), re.S
    )
    if match is None:
        raise AssertionError(f"{relative} has no clause {number}")
    return re.sub(r"\s+", " ", match.group(1))


def read_bullet_flat(name, marker):
    """One top-level bullet of a contract, whitespace collapsed. Scopes an
    assertion to the bullet the criterion names, so a sentence landing in a
    neighbouring bullet cannot satisfy it."""
    flat = read_flat(name)
    if marker not in flat:
        raise AssertionError(f"contracts/{name} has no bullet {marker}")
    return flat.split(marker, 1)[1].split(" - `", 1)[0]


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

    def test_body_sections_are_listed_in_contract_order(self):
        text = read("work-item.md").split("## Body sections", 1)[-1].split("\n## Dispatch", 1)[0]
        order = [
            "Objective", "Fixed inputs", "Completion test", "Return fields",
            "Result", "Verification", "Feedback", "Risks", "Handoff",
        ]
        seen = [text.index(f"`## {h}`") for h in order]
        self.assertEqual(seen, sorted(seen), "work-item.md lists the body sections out of contract order")

    def test_status_enum_is_the_eight_ticket_statuses(self):
        text = read("work-item.md")
        for status in (
            "pending", "ready", "claimed", "suspended", "complete",
            "blocked", "failed", "limited",
        ):
            self.assertIn(f"`{status}`", text, f"work-item.md is missing the `{status}` status")
        self.assertIn("orch-frontier", text, "work-item.md does not name orch-frontier as the pending->ready owner")
        self.assertIn("`orch-integrate`", text, "work-item.md does not name the join as the terminal-status writer")

    def test_ticket_result_write_is_outside_write_scope(self):
        text = read("work-item.md")
        self.assertIn("outside `write_scope`", text, "work-item.md does not state the ticket write is outside write_scope")

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
            self.assertIn(part, text, f"work-item.md does not name the packet part {part}")

    def test_root_ticket_names_its_stamp_and_its_gate_subtree(self):
        text = read("work-item.md")
        for token in (
            "`orch-decompose`", "`required_spec_fields`", "`<id>.NN`",
            "`<id>.gate.critique.<lens>`", "`<id>.gate.repair`",
            "`<id>.gate.verify`", "`plan_gate`",
        ):
            self.assertIn(token, text, f"work-item.md's root ticket does not name {token}")

    def test_template_and_stub_key_set(self):
        text = read("work-item.md")
        for token in (
            "`template.md`", "`name`", "`description`", "`entry`",
            "`placeholders`", "`{{placeholder}}`", "terminal stub",
            "tickets.py instantiate",
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
            "never rests on wall clock alone", text,
            "work-item.md's lease does not negate wall clock as the staleness test",
        )
        self.assertIn("60 minutes", text, "work-item.md's lease drops its default duration")

    def test_carries_no_compatibility_floor(self):
        self.assertNotIn(
            "Compatibility floor", read("work-item.md"),
            "work-item.md still carries the changelog the supersession deletes",
        )

    def test_no_reference_to_the_dead_contracts(self):
        """The dead T0 names, each as it would appear in a sibling link or a
        repository-relative citation. `rules/delegation.md` is a live T1 file
        and is not this list's subject."""
        for name in (
            "work-item.md", "pack-signature.md", "worklog.md", "verdict.md",
            "composition.md", "result.md",
        ):
            text = read(name)
            for dead in (
                "task-result.md", "handoff.md", "(spec.md)", "(delegation.md)",
                "contracts/spec.md", "contracts/delegation.md",
            ):
                self.assertNotIn(dead, text, f"{name} still references deleted {dead}")


class TestResultContract(unittest.TestCase):
    def test_contains_the_envelope_grammar(self):
        text = read("result.md")
        for token in (
            "`status`", "`result`", "`verification`",
            "complete", "blocked", "stalled", "limited", "failed",
        ):
            self.assertIn(token, text, f"result.md is missing {token!r}")

    def test_binds_the_class_and_not_a_roster_of_skills(self):
        text = read_flat("result.md")
        self.assertNotIn(
            "orch-", text,
            "result.md names a T1 skill; a T0 contract binds the class "
            "(every dispatchable unit), never a roster that goes stale",
        )
        for token in ("every dispatchable unit", "rule 10", "exempt"):
            self.assertIn(token, text, f"result.md's binding does not name {token!r}")


class TestWorklogContract(unittest.TestCase):
    def test_is_the_view_the_ticket_directory_renders(self):
        text = read("worklog.md")
        self.assertIn(
            "tickets.py worklog", text,
            "worklog.md does not name the command that renders the run view",
        )
        self.assertNotIn(
            "run.json", text,
            "worklog.md still specifies the sink record `scripts/tickets.py` owns",
        )

    def test_names_the_five_view_fields(self):
        text = read("worklog.md")
        for field in (
            "`goal`", "`iterations`", "`failed_approaches`",
            "`queued_scope`", "`terminal`",
        ):
            self.assertIn(field, text, f"worklog.md's run view is missing {field}")

    def test_terminal_carries_the_run_level_enum(self):
        text = read("worklog.md")
        for value in ("`complete`", "`blocked`", "`stalled`", "`limited`", "`failed`"):
            self.assertIn(value, text, f"worklog.md's terminal set is missing {value}")


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
        return read_clause_flat("rules/visibility.md", 6)

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
    truncation prohibition, which `scripts/cutcheck.py` enforces; §7's
    reuse precondition for a gate that returns findings; and
    §11's two cross-step sentences, frozen byte-for-byte against the copy
    `S-CUT`'s spec carries. The last two are never reworded here."""

    def law(self, number=None):
        if number is None:
            return read_at_flat("rules/verification.md")
        return read_clause_flat("rules/verification.md", number)

    def test_a_truncated_transcript_is_not_the_oracles_output(self):
        text = self.law(1)
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
        text = self.law(7)
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
    cite. Each is read from the bullet that owns it, never from the file
    around it: placement is what these criteria assert."""

    def bullet(self, marker):
        return read_bullet_flat("work-item.md", marker)

    def test_return_fields_status_is_the_result_envelopes(self):
        text = self.bullet("`## Return fields` — packet `return_contract`")
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
            "never the ticket frontmatter key above", text,
            "work-item.md's `## Return fields` bullet does not exclude the "
            "ticket frontmatter key",
        )

    def test_isolation_names_its_only_setter_and_the_grading_order(self):
        text = self.bullet("`isolation` — packet `authority`")
        for clause, why in (
            ("The decomposer is the field's only setter",
             "work-item.md's `isolation` bullet does not name the decomposer "
             "as the field's only setter"),
            ("`scripts/workspace.py check`",
             "work-item.md's `isolation` bullet no longer names "
             "`scripts/workspace.py check` as what grades the declaration"),
            ("before the merge, because afterwards the item's tip is already "
             "an ancestor of the run tip and a stamped item exits clean by "
             "design",
             "work-item.md's `isolation` bullet does not order "
             "`scripts/workspace.py check` before the merge, nor give the "
             "reason the check decides nothing after it"),
        ):
            with self.subTest(clause=clause):
                self.assertIn(clause, text, why)

    def test_fixed_inputs_forbid_an_unpinned_coordinate_by_citing_identity(self):
        text = self.bullet("`## Fixed inputs` — packet `inputs`")
        self.assertIn(
            "never prose copies", text,
            "work-item.md's `## Fixed inputs` bullet lost its existing "
            "prohibition on a prose copy",
        )
        self.assertIn(
            "never an unpinned coordinate", text,
            "work-item.md's `## Fixed inputs` bullet does not forbid citing a "
            "fixed input by an unpinned coordinate",
        )
        self.assertIn(
            "[docs/vocabulary.md](../docs/vocabulary.md)'s `identity` entry",
            text,
            "work-item.md's `## Fixed inputs` bullet does not resolve the "
            "line-number prohibition against the `identity` entry that owns "
            "it; the citation is the property, never a restatement",
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
