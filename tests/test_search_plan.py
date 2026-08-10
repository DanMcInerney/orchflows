"""Public-seam checks for deterministic search planning."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVOLVE = ROOT / "compositions" / "evolve.md"
EVOLVE_GENERATION = ROOT / "compositions" / "references" / "evolve-generation.md"
TOURNAMENT = ROOT / "compositions" / "skill-tournament.md"
SEARCH_SKILL = ROOT / "skills" / "utilities" / "orch-search-plan" / "SKILL.md"
SEARCH_SCRIPT = (
    ROOT
    / "skills"
    / "utilities"
    / "orch-search-plan"
    / "scripts"
    / "search_plan.py"
)

CALL_EDGE_RE = re.compile(r"`(orch-[a-z0-9-]+)`")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


def architecture_errors(evolve: str, generation: str, tournament: str, leaf: str):
    errors = []
    combined_evolve = evolve + generation
    evolve_calls = set(CALL_EDGE_RE.findall(combined_evolve))
    required = {
        "orch-delegate",
        "orch-integrate",
        "orch-judge",
        "orch-loop",
        "orch-panel",
        "orch-search-plan",
        "orch-verify",
        "orch-worklog",
    }
    if not required <= evolve_calls:
        errors.append("evolve-call-graph")
    if re.search(r"^-\s*closing\b", evolve, re.IGNORECASE | re.MULTILINE):
        errors.append("closing-wrapper")
    if normalized(combined_evolve).count("`orch-judge`") != 1:
        errors.append("judge-owner")

    tournament_calls = set(CALL_EDGE_RE.findall(tournament))
    if tournament_calls:
        errors.append("tournament-internal-call")
    if "writer binding orch-build" not in normalized(tournament):
        errors.append("tournament-writer-binding")
    if "promotion" in normalized(tournament):
        errors.append("tournament-promotion")

    leaf_calls = set(CALL_EDGE_RE.findall(leaf)) - {"orch-search-plan"}
    if leaf_calls:
        errors.append("leaf-call")
    return errors


class TestArchitecture(unittest.TestCase):
    def test_thin_evolve_owns_one_campaign_call_graph(self):
        for path in (EVOLVE, EVOLVE_GENERATION, TOURNAMENT, SEARCH_SKILL, SEARCH_SCRIPT):
            self.assertTrue(path.is_file(), f"missing search-planning surface: {path}")

        evolve = read(EVOLVE)
        generation = read(EVOLVE_GENERATION)
        tournament = read(TOURNAMENT)
        leaf = read(SEARCH_SKILL)
        self.assertEqual([], architecture_errors(evolve, generation, tournament, leaf))
        self.assertIn("role: none", leaf)
        command = "python skills/utilities/orch-search-plan/scripts/search_plan.py advance"
        self.assertEqual(1, leaf.count(command))
        self.assertNotIn("operation registry", normalized(leaf))

    def test_known_wrong_ownership_fixtures_are_rejected(self):
        evolve = read(EVOLVE)
        generation = read(EVOLVE_GENERATION)
        tournament = read(TOURNAMENT)
        leaf = read(SEARCH_SKILL)

        closing = evolve + "\n- closing — a fresh `orch-judge` wrapper.\n"
        self.assertIn(
            "closing-wrapper",
            architecture_errors(closing, generation, tournament, leaf),
        )
        direct_panel = tournament + "\nDirectly call `orch-panel`.\n"
        self.assertIn(
            "tournament-internal-call",
            architecture_errors(evolve, generation, direct_panel, leaf),
        )
        extra_leaf_call = leaf + "\nCall `orch-verify`.\n"
        self.assertIn(
            "leaf-call",
            architecture_errors(evolve, generation, tournament, extra_leaf_call),
        )


if __name__ == "__main__":
    unittest.main()
