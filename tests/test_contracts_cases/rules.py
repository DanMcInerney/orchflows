"""Cases for vocabulary and cross-cutting contract laws."""

import re
import unittest

from tests.test_contracts_cases.support import (
    SKILLS,
    read,
    read_at_flat,
    read_bullet_flat,
    read_clause_flat,
    read_flat,
)


class TestVocabularyDefinesShapeChange(unittest.TestCase):
    """The vocabulary owns the term used by the T0 supersession gate."""

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
        for token in ("field", "enum"):
            self.assertIn(
                token, entry,
                f"the shape change entry does not name {token!r} as what moves",
            )
        self.assertIn(
            "T0 contract", entry,
            "the shape change entry does not define the term as a change to "
            "a T0 contract",
        )

    def test_states_the_converse_a_prose_only_edit_needs(self):
        entry = self.entry()
        for token in ("prose edit", "re-pinned"):
            self.assertIn(
                token, entry,
                f"the shape change entry does not name {token!r}, so it does "
                "not state the converse: a T0 edit moving no field or enum is "
                "a prose edit, re-pinned with no supersession PR",
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
    """The two-channel law owned by rules/visibility.md section 6."""

    def section(self):
        return read_clause_flat("rules/visibility.md", 6)

    def test_content_channel_is_the_packs_workspace_cell(self):
        text = self.section()
        self.assertIn(
            "workspace cell", text,
            "visibility.md §6 does not name the pack's workspace cell as what "
            "content leaves the workspace by; a merge-only channel is false "
            "for the content and research packs",
        )

    def test_governs_all_of_orch(self):
        text = self.section()
        for token in ("every directory", "`runs/`", "`tickets/`"):
            self.assertIn(
                token, text,
                f"visibility.md §6 does not name {token!r}, so it does not "
                "state that it governs all of `.orch/` rather than the two "
                "directories a reader meets first",
            )

    def test_the_two_channel_law_survives_the_rewrite(self):
        text = self.section()
        for clause in (
            "two channels", "never cross", "file tools", "installed scripts",
        ):
            self.assertIn(
                clause, text,
                f"visibility.md §6 lost {clause!r}: the merge clause is "
                "re-expressed, never deleted",
            )


class TestVerificationHomelessLaws(unittest.TestCase):
    """Verification laws whose mechanical guard lives in this collection."""

    def law(self, number):
        return read_clause_flat("rules/verification.md", number)

    def test_a_gate_returning_findings_moves_the_result_identity(self):
        text = self.law(7)
        for token in ("gate", "findings", "result identity"):
            self.assertIn(
                token, text,
                f"verification.md §7 does not name {token!r}, so it does not "
                "state that a gate returning findings moves the result identity",
            )

    def test_one_independence_path_unique_lenses_and_one_root_gate(self):
        work_item = read_flat("work-item.md")
        independence = read_bullet_flat("work-item.md", "`independence`")
        checked_by = read_bullet_flat("work-item.md", "`checked_by`")
        root = work_item.split("## Root ticket", 1)[1].split(
            "## Template and stub", 1
        )[0]
        for token in (
            "all authored-here criteria", "regardless of oracle class",
            "exactly one outside-independence path",
        ):
            self.assertIn(token, independence, f"independence omits {token!r}")
        for token in ("single", "immutable", "non-root", "`gate`"):
            self.assertIn(token, checked_by, f"checked_by omits {token!r}")
        # The composite-gate shape and the successor plan have one owner
        # each -- rules/topology.md §5 and §7, asserted below, plus
        # skills/workflows/orch-spec for `successors.md`. The contract keeps
        # the root's own independence bookkeeping and points at the rest.
        for token in (
            "`independence: gate`", "`checked_by`", "cut reader",
            "never satisfies", "composite gate", "`orch-spec`",
        ):
            self.assertIn(token, root, f"Root ticket omits {token!r}")
        for token in ("`successors.md`", "sole writer", "completed frontier"):
            self.assertNotIn(
                token, root,
                f"Root ticket restates {token!r}; orch-spec owns it",
            )

        verification = self.law(10)
        for token in (
            "exactly one", "mutually exclusive", "pre-existing", "checker",
            "downstream gate", "unique named", "root-gate critique lens",
        ):
            self.assertIn(
                token, verification,
                f"verification.md §10 omits {token!r}",
            )

        topology_gate = read_clause_flat("rules/topology.md", 5)
        for token in (
            "one root ticket", "one composite gate", "physical run",
            "unique", "lens", "one repair", "one verification",
        ):
            self.assertIn(
                token, topology_gate,
                f"topology.md §5 omits {token!r}",
            )
        topology_successor = read_clause_flat("rules/topology.md", 7)
        for token in (
            "successor run", "result identity", "resolved", "cited",
            "`successors.md`", "sole writer", "materialization owner",
            "durable trigger",
        ):
            self.assertIn(
                token, topology_successor,
                f"topology.md §7 omits {token!r}",
            )

        vocabulary = read_at_flat("docs/vocabulary.md")

        def entry(term):
            self.assertEqual(
                1, vocabulary.count(term), f"expected one {term} entry"
            )
            return vocabulary.split(term, 1)[1].split(" - **", 1)[0]

        for token in (
            "physical execution", "one root ticket", "one composite gate",
        ):
            self.assertIn(token, entry("**run**"), f"run entry omits {token!r}")
        for token in ("exactly one", "path"):
            self.assertIn(
                token, entry("**independence**"),
                f"independence entry omits {token!r}",
            )
        for token in ("unique", "named", "additional"):
            self.assertIn(
                token, entry("**lens**"), f"lens entry omits {token!r}"
            )
        for token in ("composite", "one repair", "one verification"):
            self.assertIn(
                token, entry("**gate**"), f"gate entry omits {token!r}"
            )

        architecture = read_at_flat("ARCHITECTURE.md")
        for token in (
            "one root/gate family", "installed version", "source commit",
            "`opened_at`", "`terminal_at`", "`elapsed_ms`",
        ):
            self.assertIn(
                token, architecture, f"ARCHITECTURE.md omits {token!r}"
            )

        worklog = read_flat("worklog.md")
        for token in ("one physical run", "one root", "composite gate"):
            self.assertIn(token, worklog, f"worklog.md omits {token!r}")
        for token in (
            "`successors.md`", "durable successor plan", "not a transcript",
            "sole writer", "drained `orch-frontier`", "accepted result identity",
        ):
            self.assertIn(token, worklog, f"worklog.md omits {token!r}")


class VocabularyCutTermsTest(unittest.TestCase):
    """The atom and critical-path entries in docs/vocabulary.md."""

    def entry(self, term):
        flat = read_at_flat("docs/vocabulary.md")
        self.assertEqual(
            flat.count(term), 1,
            f"docs/vocabulary.md must carry the {term} entry exactly once",
        )
        return flat.split(term, 1)[1].split(" - **", 1)[0]

    def under(self, heading, next_heading):
        flat = read_at_flat("docs/vocabulary.md")
        return flat.split(heading, 1)[1].split(next_heading, 1)[0]

    def test_atom_and_critical_path_are_defined_once(self):
        atom = self.entry("**atom**")
        for token, why in (
            ("end state", "does not name the one observable end state"),
            ("completion test", "does not name the discriminating completion test"),
            ("write scope", "does not name the closed write scope"),
            ("sibling", "does not name the sibling-read bound"),
            ("ceiling", "does not name the instruction ceiling, the atom's mechanical bound"),
            ("`rules/topology.md`", "does not name the owner of the law it summarises"),
        ):
            with self.subTest(term="atom", token=token):
                self.assertIn(token, atom, f"the atom entry {why}")
        path = self.entry("**critical path**")
        for token, why in (
            ("`depends_on`", "does not name the edge the chain runs over"),
            ("gate", "does not exclude the gate stubs from the chain"),
            ("`scripts/cutcheck.py`", "does not name what reports it"),
            ("`critical-path`", "does not name the class carrying the length"),
            ("`level-width`", "does not name the class carrying each level's width"),
        ):
            with self.subTest(term="critical path", token=token):
                self.assertIn(token, path, f"the critical path entry {why}")
        self.assertIn(
            "**atom**", self.under("## Work", "## Verification"),
            "the atom entry must sit under ## Work, beside the work item it is a property of",
        )
        self.assertIn(
            "**critical path**", self.under("## Iteration", "## Improvement"),
            "the critical path entry must sit under ## Iteration, beside the frontier it is measured over",
        )


class TestSkillDescriptions(unittest.TestCase):
    def test_every_skill_description_is_at_most_140_chars(self):
        skill_files = sorted(SKILLS.glob("*/*/SKILL.md"))
        self.assertTrue(skill_files, "expected at least one skills/*/*/SKILL.md")
        for skill_md in skill_files:
            text = skill_md.read_text(encoding="utf-8")
            match = re.search(r"^description:\s*(.*)$", text, re.MULTILINE)
            self.assertIsNotNone(
                match, f"{skill_md} has no 'description:' in frontmatter"
            )
            desc = match.group(1).strip()
            self.assertLessEqual(
                len(desc), 140,
                f"{skill_md} description is {len(desc)} chars (>140): {desc!r}",
            )


class V2LifecycleRuleContractTest(unittest.TestCase):
    """Caller authority, sealed assignment, and amendment ownership."""

    def vocabulary_entry(self, term):
        flat = read_at_flat("docs/vocabulary.md")
        self.assertEqual(
            flat.count(term), 1,
            f"docs/vocabulary.md must define {term} exactly once",
        )
        return flat.split(term, 1)[1].split(" - **", 1)[0]

    def test_vocabulary_owns_the_v2_lifecycle_terms(self):
        expected = {
            "**semantic root**": (
                "executable delivery contract", "caller", "deterministic",
                "semantic", "suspends",
            ),
            "**assignment generation**": (
                "`root_generation`", "`cut_generation`", "content digest",
            ),
            "**assignment seal**": (
                "validated", "assignment digest", "immutable", "generation",
            ),
            "**amendment request**": (
                "canonical", "`## Handoff`", "worker", "caller",
            ),
        }
        for term, tokens in expected.items():
            entry = self.vocabulary_entry(term)
            for token in tokens:
                with self.subTest(term=term, token=token):
                    self.assertIn(token, entry)

    def test_delegation_owns_semantic_authority_and_bounded_correction(self):
        boundary = read_clause_flat("rules/delegation.md", 12)
        for token in (
            "semantic root", "objective", "oracle set", "total authority",
            "fixed evidence", "exclusions", "bounds", "return contract",
            "deliverable kind", "pack", "deterministic equivalence oracle",
            "suspends for the caller",
        ):
            self.assertIn(token, boundary, f"delegation.md §12 omits {token!r}")

        correction = read_clause_flat("rules/delegation.md", 13)
        for token in (
            "mechanical correction", "one generation", "finite positive",
            "normalized validation-failure identity", "suspends immediately",
        ):
            self.assertIn(token, correction, f"delegation.md §13 omits {token!r}")

    def test_delegation_owns_worker_amendment_and_caller_dispositions(self):
        amendment = read_clause_flat("rules/delegation.md", 14)
        for token in (
            "`request-id`", "`requester-ticket`", "`parent-ticket`",
            "`root-generation`", "`cut-generation`", "`change-kind`",
            "`target-fields`", "`reason`", "`evidence-identities`",
            "`bound-state`", "canonical JSON", "`## Handoff`", "park",
            "never edits a parent ticket", "once per dispatch", "continue",
            "amend-and-reseal", "recut-remaining", "successor-or-new-root",
        ):
            self.assertIn(token, amendment, f"delegation.md §14 omits {token!r}")

    def test_delegation_owns_sealed_assignment_immutability(self):
        seal = read_clause_flat("rules/delegation.md", 15)
        for token in (
            "exact validated assignment digest", "ready", "claim", "packet",
            "new generation", "`Result`", "`Verification`", "`Feedback`",
            "`Risks`", "`Handoff`", "append-only", "objective", "inputs",
            "authority", "dependencies", "acceptance", "executor",
        ):
            self.assertIn(token, seal, f"delegation.md §15 omits {token!r}")
