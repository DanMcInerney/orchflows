"""Static invariants owned by benchmark campaign architecture."""
import unittest

from ._support import (
    CALL_EDGE_RE,
    COMPOSITIONS,
    ROOT,
    bodies,
    split_document,
    workflow_files,
)

EVOLVE = COMPOSITIONS / "evolve"
EVOLVE_GENERATION = COMPOSITIONS / "references" / "evolve-generation.md"
TOURNAMENT = COMPOSITIONS / "skill-tournament"
SUPERSEDED_BODIES = (
    COMPOSITIONS / "evolve.md",
    COMPOSITIONS / "skill-tournament.md",
    COMPOSITIONS / "fix.md",
    COMPOSITIONS / "references" / "evolve-evaluation.md",
)


class TestBenchmarkArchitecture(unittest.TestCase):
    """Pin benchmark call edges, brick order, and demoted owners."""

    # (label, sources, exactly, at_least, never)
    CALL_EDGES = (
        (
            "skill-tournament", workflow_files(TOURNAMENT),
            frozenset(), frozenset(), frozenset(),
        ),
        (
            "evolve", workflow_files(EVOLVE) + (EVOLVE_GENERATION,),
            frozenset(), frozenset(), frozenset(),
        ),
    )
    # `orch-judge` was demoted here at U12 (a68eeabe): one of several rejected
    # candidate names from the seven-verb convergence, not the callable this
    # rename (W2b, verbs-rename) later minted from `orch-check`. That verb is
    # exactly what these workflows now call, so it is dropped from this list;
    # the remaining five stay dead.
    DEMOTED = (
        "orch-bench", "orch-benchmaker", "orch-delegate",
        "orch-worklog", "orch-panel",
    )

    def test_each_body_calls_exactly_the_edges_its_architecture_declares(self):
        for label, sources, exactly, at_least, never in self.CALL_EDGES:
            with self.subTest(body=label):
                calls = set(CALL_EDGE_RE.findall(bodies(*sources)))
                if exactly is not None:
                    self.assertEqual(set(exactly), calls)
                self.assertLessEqual(set(at_least), calls)
                self.assertEqual(set(), calls & set(never))

    def test_evolve_judges_before_it_generates_and_before_it_closes(self):
        body = bodies(*workflow_files(EVOLVE))
        admit = body.index("Admit the incumbent")
        generations = body.index("Generations, until")
        close = body.index("Close the campaign")

        self.assertLess(admit, generations)
        self.assertLess(generations, close)
        for anchor in (admit, close):
            self.assertIn("judge --pack orch-code-pack", body[anchor:])
        # The loop's exit is a judge verdict, never a `loop:` marker.
        self.assertIn("judge's verdict is the loop's only exit condition", body)
        self.assertNotIn("loop:", body)

    def test_the_tournament_nests_both_campaigns_as_frames(self):
        body = bodies(*workflow_files(TOURNAMENT))

        self.assertIn("tickets.py frame-open <run> --parent <frame>", body)
        self.assertIn("`benchmaker`", body)
        self.assertIn("`evolve`", body)

    def test_no_demoted_owner_reappears_in_either_campaign(self):
        for directory in (EVOLVE, TOURNAMENT):
            text = "".join(
                path.read_text(encoding="utf-8")
                for path in workflow_files(directory)
            )
            for name in self.DEMOTED:
                with self.subTest(workflow=directory.name, demoted=name):
                    self.assertNotIn(name, text)

    def test_the_superseded_campaign_bodies_stay_deleted(self):
        for path in SUPERSEDED_BODIES:
            with self.subTest(body=path.name):
                self.assertFalse(path.exists(), f"{path} is the workflow's twin")

    def test_the_campaigns_stay_manual_only_entries(self):
        for directory in (EVOLVE, TOURNAMENT):
            with self.subTest(workflow=directory.name):
                body = directory / "SKILL.md"
                self.assertEqual(
                    "true",
                    split_document(body)[0].get("disable-model-invocation"),
                )
