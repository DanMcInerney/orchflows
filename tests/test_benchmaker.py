"""Contract checks for the project-scoped benchmaker workflow."""

import re
import unittest
from pathlib import Path, PureWindowsPath


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".orchflows" / "skills" / "benchmaker" / "SKILL.md"
PROTOCOL = SKILL.parent / "references" / "protocol.md"
ADAPTER = ROOT / ".claude" / "skills" / "benchmaker" / "SKILL.md"


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse the flat frontmatter shape used by orchflows skill files."""
    opening, frontmatter, body = text.split("---", 2)
    if opening:
        raise AssertionError("frontmatter must start at byte zero")
    fields = {}
    for line in frontmatter.strip().splitlines():
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, body.lstrip("\r\n")


def markdown_section(text: str, heading: str) -> str:
    start = text.index(f"## {heading}")
    end = text.find("\n## ", start + len(heading) + 3)
    return text[start:] if end == -1 else text[start:end]


def squashed(text: str) -> str:
    return " ".join(text.split())


class TestBenchmakerSurface(unittest.TestCase):
    def test_project_scoped_entrypoints_are_discoverable_and_well_formed(self):
        for path in (SKILL, PROTOCOL, ADAPTER):
            self.assertTrue(path.is_file(), f"missing project entrypoint: {path}")

        fields, body = split_frontmatter(SKILL.read_text(encoding="utf-8"))
        self.assertEqual("benchmaker", fields["name"])
        self.assertEqual("none", fields["role"])
        self.assertLessEqual(len(fields["description"]), 140)
        self.assertLess(body.index("Require:"), body.index("Never:"))
        self.assertLess(body.index("Never:"), body.index("Return:"))
        self.assertLessEqual(len([line for line in body.splitlines() if line.strip()]), 40)
        self.assertEqual(
            {"orch-bench", "orch-deliver", "orch-spec"},
            set(re.findall(r"`(orch-[a-z0-9-]+)`", body)),
        )
        self.assertEqual(1, body.count("[references/protocol.md](references/protocol.md)"))

        adapter_fields, adapter_body = split_frontmatter(ADAPTER.read_text(encoding="utf-8"))
        self.assertEqual({"name", "description"}, set(adapter_fields))
        self.assertEqual("benchmaker", adapter_fields["name"])
        owner_include = adapter_body.strip()
        self.assertTrue(owner_include.startswith("@"))
        owner_path = PureWindowsPath(owner_include[1:])
        self.assertTrue(owner_path.is_absolute())
        self.assertEqual(
            (".orchflows", "skills", "benchmaker", "SKILL.md"),
            owner_path.parts[-4:],
        )

        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        routing_line = (
            "- `benchmaker`: build and qualify one benchmark suite; "
            "read `.orchflows/skills/benchmaker/SKILL.md`."
        )
        self.assertEqual(1, agents.count(routing_line))

    def test_callable_stages_are_strictly_ordered_and_fail_closed(self):
        _, body = split_frontmatter(SKILL.read_text(encoding="utf-8"))
        body_words = squashed(body)
        stages = (
            "Through `orch-spec`, freeze the research spec",
            "Through `orch-deliver`, deliver the frozen research spec",
            "If research is non-complete, has a `decision_gap`, or leaves a remainder, return partial evidence",
            "Through the admitted carrier, call `orch-bench`",
            "If the design is invalid or UNVERIFIED, return partial evidence",
            "Through the same spec owner, freeze the construction spec",
            "Through the same delivery owner, deliver the construction spec",
        )
        positions = [body_words.index(stage) for stage in stages]
        self.assertEqual(sorted(positions), positions)
        self.assertIn(
            "If `evidence` does not name the admitted carrier, fail closed before work",
            body_words,
        )
        self.assertIn(
            "failure, the same fields populated by partial evidence, with `decision_gap` and uncovered remainder",
            body_words,
        )


class TestBenchmakerProtocol(unittest.TestCase):
    def test_research_converges_before_bench_design(self):
        protocol = PROTOCOL.read_text(encoding="utf-8")
        intake = markdown_section(protocol, "Intake boundary")
        research = markdown_section(protocol, "Research delivery")
        design = markdown_section(protocol, "Bench design")
        research_words = squashed(research)
        design_words = squashed(design)
        self.assertLess(protocol.index("## Intake boundary"), protocol.index("## Research delivery"))
        self.assertLess(protocol.index("## Research delivery"), protocol.index("## Bench design"))

        for boundary_term in (
            "target identity",
            "intended outcome",
            "target pack",
            "evidence access",
            "execution bound",
            "judgment permission",
            "population",
            "inputs",
            "states",
            "outputs",
            "exclusions",
        ):
            self.assertIn(boundary_term, intake)

        self.assertIn("one research-pack delivery", research)
        self.assertIn("orch-research-pack", research)
        self.assertIn("independent", research)
        self.assertIn("bounded", research)
        for concern in (
            "prior art",
            "real failure modes",
            "edge cases",
            "authoritative semantics",
            "oracle options",
        ):
            self.assertIn(concern, research_words)
        for evidence_property in (
            "claim-to-source trace",
            "disagreement register",
            "gaps",
            "frozen result identity",
            "development seeds",
            "source and license",
        ):
            self.assertIn(evidence_property, research_words)

        self.assertIn("[`orch-bench`]", design_words)
        self.assertIn("admitted carrier", design_words)
        self.assertIn("existing Require field", design_words)
        self.assertIn("bench owner selects the task set", design_words)
        self.assertIn("returns the generation brief", design_words)
        self.assertIn("invalid identity, missing field, or UNVERIFIED design", design_words)
        self.assertIn("do not freeze construction", design_words)

    def test_one_bound_is_partitioned_once_and_carries_forward(self):
        intake = squashed(
            markdown_section(
                PROTOCOL.read_text(encoding="utf-8"), "Intake boundary"
            )
        )
        self.assertIn("Before any work, partition the single caller bound", intake)
        for allocation in (
            "research",
            "bench-design",
            "construction",
            "qualification",
        ):
            self.assertIn(allocation, intake)
        self.assertIn("whose total cannot exceed it", intake)
        self.assertIn(
            "unused budget carried forward from completed earlier stages", intake
        )
        self.assertIn("Never copy the caller bound", intake)
        self.assertIn("return the result fields as partial evidence", intake)
        self.assertIn("missing carrier as a `decision_gap`", intake)

    def test_cases_are_independently_qualified_deterministic_first(self):
        protocol = PROTOCOL.read_text(encoding="utf-8")
        construction = markdown_section(protocol, "Case construction")
        qualification = markdown_section(protocol, "Qualification")
        returned = markdown_section(protocol, "Return")
        construction_words = " ".join(construction.split())
        qualification_words = " ".join(qualification.split())
        returned_words = " ".join(returned.split())
        self.assertLess(protocol.index("## Bench design"), protocol.index("## Case construction"))
        self.assertLess(protocol.index("## Case construction"), protocol.index("## Qualification"))
        self.assertLess(protocol.index("## Qualification"), protocol.index("## Return"))

        for construction_term in (
            "one target-pack construction delivery",
            "stamped target pack",
            "frozen research synthesis",
            "frozen bench",
            "exact materialization of the frozen task set",
            "exact generation brief",
            "only disjoint execution and write scopes",
            "provenance",
        ):
            self.assertIn(construction_term, construction_words)
        self.assertIn(
            "never selects, adds, removes, ranks, rewrites, or substitutes a case",
            construction_words,
        )
        self.assertIn(
            "selection change returns partial construction evidence and remainder to the bench owner",
            construction_words,
        )
        self.assertNotIn("Suite selection maximizes", construction)
        self.assertIn("independent context", qualification_words)
        self.assertIn("Case authors never qualify", qualification_words)
        for criterion in (
            "oracle validity",
            "coverage",
            "discrimination",
            "reproducibility",
            "redundancy",
            "provenance",
            "runtime bound",
        ):
            self.assertIn(criterion, qualification_words)
        for policy in (
            "Prefer deterministic oracles",
            "Deterministic failure is non-compensable",
            "caller granted judgment permission",
            "recorded deterministic-coverage gap",
            "anchors",
            "secondary",
            "expected cost",
        ):
            self.assertIn(policy, qualification_words)
        self.assertIn(
            "No weight, aggregation result, judged score, or secondary criterion can offset it",
            qualification_words,
        )

        expected_fields = (
            "runnable suite",
            "execution instructions",
            "coverage map",
            "research provenance",
            "qualification verdicts and expected cost",
            "explicit gaps",
        )
        for field in expected_fields:
            self.assertIn(field, returned_words)
        self.assertIn("Success returns only", returned_words)
        self.assertIn("Failure preserves partial evidence", returned_words)


class TestBenchmakerDocumentation(unittest.TestCase):
    def test_docs_describe_only_project_scoped_construction_and_qualification(self):
        docs = (ROOT / "docs" / "benchmaker.md").read_text(encoding="utf-8")
        headings = re.findall(r"^#{1,2} (.+)$", docs, re.MULTILINE)
        self.assertEqual(
            ["BenchMaker", "Project scope", "Construction", "Qualification", "Result"],
            headings,
        )
        self.assertIn("project-scoped custom workflow", docs)
        self.assertIn("../.orchflows/skills/benchmaker/SKILL.md", docs)
        self.assertIn("one declared target and intended outcome", docs)
        self.assertIn("[`orch-bench`]", docs)
        self.assertIn("has not admitted a T0 carrier", docs)
        self.assertIn("returns partial evidence and a `decision_gap`", docs)
        self.assertIn("canonical bench owner is unchanged", docs)
        self.assertIn("slicing cuts only disjoint execution and write scopes", docs)
        for forbidden in ("recursive", "self-improv", "evolv", "promot", "activat"):
            self.assertNotIn(forbidden, docs.lower())

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        benchmaker_lines = [
            line for line in readme.splitlines() if "BenchMaker" in line
        ]
        self.assertEqual(1, len(benchmaker_lines))
        self.assertIn("project-scoped", benchmaker_lines[0])
        self.assertIn("[BenchMaker workflow](docs/benchmaker.md)", benchmaker_lines[0])
        self.assertNotIn("proposal", benchmaker_lines[0].lower())


if __name__ == "__main__":
    unittest.main()
