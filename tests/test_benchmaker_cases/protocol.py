"""Protocol and composition checks for benchmaker."""

import re
import unittest

from .retirement import (
    BenchmakerRetirementCases,
    PROTOCOL_LINE_CEILING,
    RETIRED_FROM_PROTOCOL,
)
from .shared import (
    AUDIT_STAGES,
    COMPONENT_FIELDS,
    CONTEXT_AXES,
    DECLARATION_FIELDS,
    DONE_CHECK_FIELDS,
    EVAL_DESIGN,
    MANIFEST_CONTRACT,
    MOVED_OUT_OF_PROTOCOL,
    NOT_RE_DERIVABLE,
    POST_QUALIFICATION_FIELDS,
    PROTOCOL,
    ROOT,
    SHARED_INVARIANTS,
    STAGE_RECORD_SUBSTANCE,
    STUB_CHAIN,
    STUB_INVARIANTS,
    TEMPLATE,
    TEMPLATE_MANIFEST,
    TERMINAL_STUB,
    contract_bullet,
    markdown_section,
    markdown_subsection,
    split_frontmatter,
    squashed,
    ticket_law,
)


class TestCanonicalBenchmaker(BenchmakerRetirementCases, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields, _ = split_frontmatter(
            TEMPLATE_MANIFEST.read_text(encoding="utf-8")
        )
        cls.stubs = {
            path.stem: path.read_text(encoding="utf-8")
            for path in sorted(TEMPLATE.glob("*.md"))
            if path.name != TEMPLATE_MANIFEST.name
        }
        tickets = ticket_law()
        cls.stub_fields = {
            stub: tickets._parse_frontmatter(text)
            for stub, text in cls.stubs.items()
        }
        cls.protocol = PROTOCOL.read_text(encoding="utf-8")
        cls.manifest_contract = MANIFEST_CONTRACT.read_text(encoding="utf-8")

    def test_template_manifest_declares_the_shape_instantiation_fills(self):
        self.assertEqual("benchmaker", self.fields["name"])
        # Manual-only survives both conversions as entry: named.
        self.assertEqual("named", self.fields["entry"])
        self.assertLessEqual(len(self.fields["description"]), 140)
        declared = self.fields["placeholders"]
        # The set a caller must fill, not the line rendering it: the field is
        # a list, and its spelling is `template.md`'s.
        names = {item.strip() for item in declared[1:-1].split(",")}
        self.assertEqual(
            {"target", "outcome", "sources", "rigor", "pack", "package"}, names
        )
        # Every declared placeholder reaches a stub. `validate.py` warns here;
        # a warning is not what a caller who filled a dead `--set` needs.
        used = set(re.findall(r"\{\{([a-z_]+)\}\}", "".join(self.stubs.values())))
        self.assertEqual(names, used)

    def test_every_stub_is_a_ticket_this_template_can_instantiate(self):
        """The shape law is `scripts/tickets.py`'s, and it is the same law
        `instantiate` applies -- so a stub this passes is a ticket the moment
        a run fills it, and no stub in this template needs its own spelling of
        the contract."""
        tickets = ticket_law()
        self.assertEqual(
            [], [(str(path), message) for path, message in tickets.template_defects(TEMPLATE)]
        )

    def test_the_chain_binds_one_executor_per_step_and_one_terminal(self):
        self.assertEqual(
            [stub for stub, _, _ in STUB_CHAIN], sorted(self.stub_fields)
        )
        for stub, executor, depends_on in STUB_CHAIN:
            with self.subTest(stub=stub):
                self.assertEqual(executor, self.stub_fields[stub]["executor"])
                self.assertEqual(depends_on, self.stub_fields[stub]["depends_on"])
        depended = {
            edge
            for fields in self.stub_fields.values()
            for edge in fields["depends_on"]
        }
        self.assertEqual({TERMINAL_STUB}, set(self.stub_fields) - depended)
        # The terminal stub's completion test is the composition's done check:
        # that is what makes the template's promise checkable at all, and what
        # it must read is the manifest's own fields.
        done_check = squashed(
            markdown_section(self.stubs[TERMINAL_STUB], "Completion test")
        ).partition("|")[0]
        for field in DONE_CHECK_FIELDS:
            self.assertIn(field, done_check, field)

    def test_each_invariant_rides_the_stub_it_binds_and_no_other(self):
        for stub, clauses in STUB_INVARIANTS.items():
            for clause in clauses:
                with self.subTest(stub=stub, clause=clause):
                    carriers = {
                        other
                        for other, fields in self.stub_fields.items()
                        if any(
                            clause in action
                            for action in fields.get("excluded_actions", [])
                        )
                    }
                    self.assertEqual(
                        SHARED_INVARIANTS.get(clause, {stub}), carriers
                    )

    def test_the_stages_that_stop_the_chain_say_what_they_return(self):
        """Acquisition and design are the two stages that can end the run
        early. Both return what they have rather than closing over it, and a
        stub that dropped the clause would look complete while stopping."""
        for stub in ("00-acquire", "01-design"):
            with self.subTest(stub=stub):
                self.assertIn("partial evidence", squashed(self.stubs[stub]))
        # The terminal stub said the same thing in its own Return fields until
        # 2026-08-16 (thread T34): every failure path returning partial results
        # is `rules/composition.md` §8's, and a stub that cannot stop early
        # bought nothing by restating it. The two stages above keep their
        # clauses because each says what partial means for that stage.

    def test_protocol_is_domain_blind_and_keeps_only_unowned_craft(self):
        """What survives is benchmark craft for a domain with no pack. The
        restatements went to the owner each already had: the packet to the
        work-item contract, the coverage floor to `orch-eval-design`, and the
        stage rules to the stub that carries out the stage."""
        headings = re.findall(r"^## (.+)$", self.protocol, re.MULTILINE)
        self.assertEqual(
            [
                "Licensed oracle material",
                "Qualification",
                "Audit and measurement",
                "Scoring",
            ],
            headings,
        )
        self.assertLessEqual(
            len(self.protocol.splitlines()), PROTOCOL_LINE_CEILING
        )
        for phrase, owner, owner_phrase in MOVED_OUT_OF_PROTOCOL:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, squashed(self.protocol))
                self.assertIn(
                    owner_phrase, squashed(owner.read_text(encoding="utf-8"))
                )
        template = squashed(
            "".join(
                path.read_text(encoding="utf-8")
                for path in sorted(TEMPLATE.glob("*.md"))
            )
        )
        for phrase, stub_phrase in RETIRED_FROM_PROTOCOL:
            with self.subTest(retired=phrase):
                self.assertNotIn(phrase, squashed(self.protocol))
                self.assertNotIn(stub_phrase, template)
        self.assertIn(
            "licensed oracle material", squashed(self.protocol)
        )

        known_pack_names = [
            path.name for path in (ROOT / "packs").iterdir() if path.is_dir()
        ]
        for pack_name in known_pack_names:
            self.assertNotIn(pack_name, self.protocol)
        for forbidden_owner in ("`orch-bench`", "`orch-evolve`"):
            self.assertNotIn(forbidden_owner, self.protocol)

    def test_protocol_qualifies_required_failures_and_protected_evidence(self):
        qualification = squashed(markdown_section(self.protocol, "Qualification"))
        for check in (
            "oracle failability",
            "coverage",
            "discrimination",
            "reproducibility",
            "redundancy",
            "provenance",
            "execution cost",
        ):
            self.assertIn(check, qualification)
        for policy in (
            "known-bad",
            "blocks qualification",
            "anchors",
            "secondary",
            "cannot compensate",
            "release policy",
            "candidate-inaccessible check",
            "UNVERIFIED",
        ):
            self.assertIn(policy, qualification)

    def test_the_coverage_floor_law_has_one_owner_and_one_carrier(self):
        """`orch-eval-design` states the law -- it is the skill that fixes
        tiers -- and 01-design's excluded actions are what bind this
        template's design step to it. Three owners was the finding; two
        statements of one law would be the same finding again."""
        owner = squashed(EVAL_DESIGN.read_text(encoding="utf-8"))
        for anchor in ("coverage floor", "not tradable", "Buy difficulty"):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, owner)
        # Squashed, like every other absence pin on the protocol: a phrase
        # that survives only across a line wrap is still present.
        for phrase in ("coverage floor", "Difficulty is built", "execution tier"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, squashed(self.protocol))

    def test_protocol_orders_and_bounds_the_three_audit_stages(self):
        stages = squashed(markdown_section(self.protocol, "Audit and measurement"))
        for ordered in (
            "triage measurement",
            "reference audit",
            "attack pass",
            "recorded measurement",
        ):
            self.assertIn(ordered, stages)
        self.assertLess(stages.index("reference audit"), stages.index("attack pass"))
        # The audit's third context, and its count-not-rate output. Each fact
        # is named by its own term, in the subsection that owns it: the
        # `###` headings are the protocol's anchors, and a fact that moved
        # between them is a different law.
        reference = squashed(markdown_subsection(self.protocol, "Reference audit"))
        for anchor in (
            "disjoint",
            "qualifying context",
            "fatal-flaw",
            "defect count",
            "never a rate",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, reference)
        # The attack pass's three outcomes and its declared-hole failure path.
        attack = squashed(markdown_subsection(self.protocol, "Attack pass"))
        for outcome in ("`SUCCEEDED`", "`FAILED`", "`BLOCKED`"):
            self.assertIn(outcome, attack)
        self.assertIn("**dated** checklist", attack)
        self.assertIn("undeclared hole", attack)
        # The measurement pass records; it never renders a verdict.
        measurement = squashed(markdown_subsection(self.protocol, "Measurement pass"))
        self.assertIn("Recording only", measurement)
        self.assertIn("cannot fail", measurement)
        self.assertIn("intake gap", measurement)
        self.assertIn("failure signatures", measurement)
        for status in ("`both-pass`", "`split`", "`both-fail`", "`inversion`"):
            self.assertIn(status, stages)
        # The instrument's resolution is the manifest's `resolution` field and
        # was stated twice until 2026-08-16 (thread T35);
        # `test_manifest_owner_carries_every_post_qualification_field` is where
        # the surviving statement is checked.
        self.assertNotIn("rerun spread", stages)
        self.assertIn("outside the package", stages)
        # The revision-durability rule that replaces the seal's guarantee: a
        # revision only resolves while it is reachable, and a squash merge
        # strands every branch commit.
        for anchor in ("default branch", "ancestor", "identical measured bytes", "squash"):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, stages)

    def test_protocol_scoring_reports_distributions_not_points(self):
        """What §Scoring still owns, and where the rest of it went at the
        2026-08-16 review (thread T35). The reporting rules moved into
        §Measurement pass -- the stage that records is their only reader, and
        no stub links `#scoring`. Two laws left the protocol for owners it was
        restating: the per-angle vector is `orch-eval-design`'s, and the
        identity boundary a score does not cross is the manifest's
        `incomparability`. Absence here plus presence there is the pair: a
        law deleted from both places is lost, not trimmed."""
        scoring = squashed(markdown_section(self.protocol, "Scoring"))
        self.assertIn("harness offset", scoring)
        self.assertIn("sign flips", scoring)

        stages = squashed(markdown_section(self.protocol, "Audit and measurement"))
        self.assertIn("`(score, cost)` pairs", stages)
        self.assertIn("`pass^k` beside `pass@1`", stages)
        for oracle_kind in ("deterministic oracle", "judged oracle"):
            with self.subTest(oracle_kind=oracle_kind):
                self.assertIn(oracle_kind, stages)

        self.assertNotIn("per-angle vector is the artifact", scoring)
        # The pinned phrase was "per-angle vector primary and any scalar
        # derived" until R4 (6b5cafa) trimmed the trailing half out of the
        # body while this guard was being retargeted at it (R6a, 4e7031a):
        # each green alone, red merged. What this half of the pair protects
        # is that the vector is what scoring reports -- a body that drops
        # the vector drops these three words -- so the pin follows the
        # surviving statement rather than asking for the trim back.
        self.assertIn(
            "per-angle vector primary",
            squashed(EVAL_DESIGN.read_text(encoding="utf-8")),
        )
        self.assertNotIn("target × model × harness × benchmark", scoring)
        boundary = contract_bullet(
            squashed(self.manifest_contract).partition(NOT_RE_DERIVABLE)[2],
            "incomparability",
        )
        for axis in ("model id", "effort level", "host binding", "scaffold"):
            self.assertIn(axis, boundary)

    def test_manifest_owner_lists_every_field_and_rule(self):
        manifest = squashed(self.manifest_contract)
        components, _, values = manifest.partition(NOT_RE_DERIVABLE)
        for field in COMPONENT_FIELDS:
            self.assertIn(f"- `{field}` — locator", components, field)
            self.assertNotIn(f"`{field}`", values, field)
        for field in DECLARATION_FIELDS:
            self.assertIn(f"`{field}`", components)
        for field, substance in STAGE_RECORD_SUBSTANCE.items():
            bullet = contract_bullet(components, field)
            for phrase in substance:
                self.assertIn(phrase, bullet, field)
        for rule in (
            "locator",
            "oracle_class",
            "evidence",
            "covers",
        ):
            self.assertIn(rule, manifest)

    def test_manifest_owner_carries_every_post_qualification_field(self):
        manifest = squashed(self.manifest_contract)
        values = manifest.partition(NOT_RE_DERIVABLE)[2]
        for field in POST_QUALIFICATION_FIELDS:
            self.assertIn(f"- `{field}` — ", values, field)
        for field in ("builders", "qualifier", "attacker"):
            bullet = contract_bullet(values, field)
            for axis in CONTEXT_AXES:
                self.assertIn(axis, bullet, field)
        # Three rules that ride a field rather than the contract at large,
        # each read out of the bullet that owns it: an undeclared anchor is
        # not a `none`, the instrument's resolution is the rerun spread, and
        # a fired trigger is recorded outside the package.
        for field, anchors in (
            ("anchors", ("`none`", "silence")),
            ("resolution", ("rerun spread",)),
            ("retirement_trigger", ("declaration only", "outside the package")),
        ):
            bullet = contract_bullet(values, field)
            for anchor in anchors:
                with self.subTest(field=field, anchor=anchor):
                    self.assertIn(anchor, bullet)

    def test_the_audit_and_measure_stages_are_split_across_two_stubs(self):
        """The three stages the protocol orders sit in two stubs: the two that
        repair or declare are `04-audit`'s, and the one that only records is
        `05-measure`'s, behind it. Collapsing them into one stub would put the
        recording pass in a context that may still repair, which is the
        difficulty gate the protocol refuses."""
        audit = squashed(self.stubs["04-audit"])
        measure = squashed(self.stubs[TERMINAL_STUB])
        for stage in AUDIT_STAGES[:2]:
            with self.subTest(stage=stage):
                self.assertIn(stage, audit)
        self.assertIn("measurement pass", measure)
        self.assertEqual(
            ["04-audit"], self.stub_fields[TERMINAL_STUB]["depends_on"]
        )
        # 04-audit repairs or declares and renders no verdict; 05-measure
        # records the manifest. Neither one does the other's job. Both halves
        # ride 04-audit's `excluded_actions`, which is where the stub is
        # accountable for them.
        excluded = self.stub_fields["04-audit"]["excluded_actions"]
        for anchor in ("pass/fail verdict", "undeclared"):
            with self.subTest(anchor=anchor):
                self.assertTrue(
                    any(anchor in action for action in excluded), excluded
                )
        # What recording-only means is the protocol's one statement of it; the
        # stub carries the link, not a fifth copy of the rationale.
        self.assertIn("benchmaker-protocol.md#measurement-pass", measure)
        # Triage is the measurement stage's own first pass, never a fourth
        # stage, so no stub may name it as one.
        self.assertEqual([], re.findall(r"triage(?! pass| measurement)", audit))



