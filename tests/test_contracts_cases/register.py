"""Cases for the T0 register and its envelope contracts."""

import unittest

from tests.test_contracts_cases.support import CONTRACTS, ROOT, read, read_flat


class TestContractRegister(unittest.TestCase):
    """The surviving T0 files and the names removed by supersession."""

    ABSORBED = ("contracts/spec.md", "contracts/delegation.md")
    LIVE_SURFACES = (
        "rules", "skills", "packs", "compositions", "docs", "templates",
        "README.md", "ARCHITECTURE.md", "DESIGN.md", "AGENTS.md",
    )
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
        for token in (
            "PASS", "FAIL", "UNVERIFIED", "oracle_class",
            "deterministic", "judged", "evidence",
        ):
            self.assertIn(token, text, f"verdict.md is missing {token!r}")


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
        for value in (
            "`complete`", "`blocked`", "`stalled`", "`limited`", "`failed`",
        ):
            self.assertIn(value, text, f"worklog.md's terminal set is missing {value}")


class TestTemplateAndStub(unittest.TestCase):
    """The composition template shape now owned by work-item.md."""

    def test_work_item_owns_the_template_shape(self):
        text = read_flat("work-item.md")
        self.assertIn("## Template and stub", read("work-item.md"))
        for token in (
            "`template.md`", "`compositions/<name>/`", "`{{placeholder}}`",
        ):
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
