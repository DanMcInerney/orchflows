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


class TestContractRegister(unittest.TestCase):
    """The T0 register itself is shape: `spec.md` and `delegation.md` are
    absorbed into `work-item.md`, so neither the directory nor any prose
    in the tree may still name them. `scripts/`, `tools/` and their tests
    are repointed at their own sites, not here."""

    ABSORBED = ("contracts/spec.md", "contracts/delegation.md")

    # The library surfaces a live name has to resolve in. REVIEW-* are the records that ordered the deletions and name what
    # they buried; `benchmarks/` is frozen fixture data.
    LIVE_SURFACES = (
        "rules", "skills", "packs", "compositions", "docs", "templates",
        "README.md", "ARCHITECTURE.md", "DESIGN.md", "AGENTS.md",
    )
    # Deleted at P4-3 with the composition-file grammar: the contract that
    # specified it (its shape is `work-item.md`'s Template and stub section
    # now), the engine that executed one, the engine whose blind lanes are
    # `orch-verify` packets, and the workflow the fix template absorbed.
    DELETED_AT_P4 = (
        "contracts/composition.md", "orch-compose", "orch-panel", "orch-diagnose",
    )

    def test_the_register_is_the_surviving_t0_files(self):
        names = sorted(p.name for p in CONTRACTS.glob("*.md"))
        self.assertEqual(
            names,
            [
                "pack-signature.md", "result.md",
                "verdict.md", "work-item.md", "worklog.md",
            ],
            "contracts/ is not the T0 register after the supersession",
        )

    def test_no_live_library_surface_names_a_thing_p4_deleted(self):
        """A name that resolves nowhere is worse than no name: a reader
        follows it, an agent routes at it, and neither finds anything.
        `validate_names` catches the backticked half in four directories;
        this catches every spelling across every surface a caller reads."""
        offenders = []
        for surface in self.LIVE_SURFACES:
            node = ROOT / surface
            paths = sorted(node.rglob("*.md")) if node.is_dir() else [node]
            for path in paths:
                if not path.is_file():
                    continue
                text = path.read_text(encoding="utf-8")
                for dead in self.DELETED_AT_P4:
                    if dead in text:
                        offenders.append(
                            f"{path.relative_to(ROOT).as_posix()}: {dead}"
                        )
        self.assertEqual(
            [], sorted(offenders),
            "these live surfaces still name something P4 deleted",
        )

    def test_no_prose_in_the_tree_still_links_the_absorbed_contracts(self):
        offenders = []
        for path in sorted(ROOT.rglob("*.md")):
            relative = path.relative_to(ROOT)
            if any(part.startswith(".") for part in relative.parts):
                continue
            if relative.parts[0] == "benchmarks" or relative.name.startswith("REVIEW-"):
                continue
            text = path.read_text(encoding="utf-8")
            if any(dead in text for dead in self.ABSORBED):
                offenders.append(relative.as_posix())
        self.assertEqual(
            offenders, [],
            "these files still link a contract work-item.md absorbed",
        )


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
        # The register runs from its first bullet to the next `## ` heading:
        # two anchors, so no reword of the list's own introduction moves it.
        full = read("work-item.md")
        text = full[full.index("- `## Objective`"):].split("\n## Dispatch", 1)[0]
        order = [
            "Objective", "Fixed inputs", "Completion test", "Return fields",
            "Result", "Verification", "Feedback", "Risks", "Handoff",
        ]
        seen = [text.index(f"`## {h}`") for h in order]
        self.assertEqual(seen, sorted(seen), "work-item.md lists the body sections out of contract order")

    def test_status_enum_is_the_nine_ticket_statuses(self):
        """`stalled` is one of them: a loop ticket carries a stalled exit,
        and the ticket terminal set is the set a run's `terminal` and a
        result envelope's `status` are read in."""

        text = read("work-item.md")
        for status in (
            "pending", "ready", "claimed", "suspended", "complete",
            "blocked", "stalled", "failed", "limited",
        ):
            self.assertIn(f"`{status}`", text, f"work-item.md is missing the `{status}` status")
        self.assertIn("orch-frontier", text, "work-item.md does not name orch-frontier as the pending->ready owner")
        self.assertIn("`orch-integrate`", text, "work-item.md does not name the join as the terminal-status writer")

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

    def test_template_and_stub_names_its_shape_and_its_owner(self):
        """What a stub *is* has one owner — `scripts/tickets.py`'s
        `template_defects`, which grades every issued ticket and every
        instantiated stub and reports it in its own words. The contract
        names the shape and that owner; a second statement of the stub law
        here is how a template the compiler admits fails at
        instantiation."""

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
            "result.md",
        ):
            text = read(name)
            for dead in (
                "task-result.md", "handoff.md", "(spec.md)", "(delegation.md)",
                "contracts/spec.md", "contracts/delegation.md",
                "(composition.md)", "contracts/composition.md",
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
        self.assertIn(
            "every dispatchable unit", text,
            "result.md binds no class at all",
        )
        self.assertNotIn(
            "rule 10", text,
            "result.md restates rules/composition.md rule 10, which already "
            "states the binding and points here for the fields",
        )


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


class TestTemplateAndStub(unittest.TestCase):
    """What `contracts/composition.md` used to specify, in the one place
    that specifies it now. A composition is a template directory, so its
    shape is a ticket's shape — and `work-item.md` states it by naming the
    two owners that grade it rather than restating their law."""

    def test_work_item_owns_the_template_shape(self):
        text = read_flat("work-item.md")
        self.assertIn("## Template and stub", read("work-item.md"))
        for token in ("`template.md`", "`compositions/<name>/`", "`{{placeholder}}`"):
            self.assertIn(token, text, f"work-item.md is missing {token!r}")

    def test_the_graders_are_named_and_not_restated(self):
        text = read_flat("work-item.md")
        self.assertIn(
            "`scripts/tickets.py`'s `template_defects`", text,
            "work-item.md does not name the owner that grades a stub",
        )
        self.assertIn(
            "`tools/validate.py`", text,
            "work-item.md does not name the owner that grades the manifest",
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
        for token in ("field", "enum"):
            self.assertIn(
                token, entry,
                f"the shape change entry does not name {token!r} as what moves",
            )
        self.assertIn(
            "T0", entry,
            "the shape change entry does not scope the term to T0",
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
    """`rules/visibility.md` §6 owns the two-channel law. Its content
    channel must hold for all four packs, whose workspace cells are a git
    tree, a git-plus-render tree, a document tree and an evidence store —
    only the first two merge. Its scope is all of `.orch/`."""

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
        for clause in ("two channels", "never cross", "file tools", "installed scripts"):
            self.assertIn(
                clause, text,
                f"visibility.md §6 lost {clause!r}: the merge clause is "
                "re-expressed, never deleted",
            )


class TestVerificationHomelessLaws(unittest.TestCase):
    """`rules/verification.md` owns one law no other file states: §7's
    reuse precondition for a gate that returns findings. (§1's truncation
    prohibition left this file: `scripts/cutcheck.py` states the how in its
    module docstring and enforces it in `SWALLOW_RE`, so the rule no longer
    restates the shell form.) It is not hash-pinned, so this is the only
    mechanical guard; it asserts the clause's load-bearing terms, never a
    sentence."""

    def law(self, number):
        return read_clause_flat("rules/verification.md", number)

    def test_a_gate_returning_findings_moves_the_result_identity(self):
        text = self.law(7)
        for token in ("gate", "findings", "result identity"):
            self.assertIn(
                token, text,
                f"verification.md §7 does not name {token!r}, so it does not "
                "state that a gate returning findings moves the result "
                "identity",
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
            ("decomposer",
             "work-item.md's `isolation` bullet does not name the decomposer "
             "as the field's only setter"),
            ("only setter",
             "work-item.md's `isolation` bullet does not make the decomposer "
             "the field's only setter"),
            ("`scripts/workspace.py check`",
             "work-item.md's `isolation` bullet no longer names "
             "`scripts/workspace.py check` as what grades the declaration"),
            ("before the merge",
             "work-item.md's `isolation` bullet does not order "
             "`scripts/workspace.py check` before the merge"),
        ):
            with self.subTest(token=token):
                self.assertIn(token, text, why)

    def test_fixed_inputs_forbid_an_unpinned_coordinate_by_citing_identity(self):
        text = self.bullet("`## Fixed inputs` — packet `inputs`")
        for token, why in (
            ("never prose copies",
             "work-item.md's `## Fixed inputs` bullet lost its existing "
             "prohibition on a prose copy"),
            ("unpinned coordinate",
             "work-item.md's `## Fixed inputs` bullet does not forbid citing "
             "a fixed input by an unpinned coordinate"),
            ("`identity` entry",
             "work-item.md's `## Fixed inputs` bullet does not resolve the "
             "line-number prohibition against the `identity` entry that owns "
             "it; the citation is the property, never a restatement"),
        ):
            with self.subTest(token=token):
                self.assertIn(token, text, why)


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
