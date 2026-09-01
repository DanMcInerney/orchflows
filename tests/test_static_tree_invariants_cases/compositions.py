"""Static invariants owned by the library's workflow skills."""
import unittest

from scripts.tickets_registry import CALLABLE_EXECUTORS, SUPERSEDED_EXECUTORS

from ._support import (
    COMPOSITIONS,
    LINK_RE,
    WORKFLOW_FILE,
    split_document,
    workflow_directories,
)


class TestCompositionLinks(unittest.TestCase):
    """Every local markdown link from a workflow resolves."""

    def test_every_composition_link_resolves(self):
        checked = 0
        for path in sorted(COMPOSITIONS.rglob("*.md")):
            for target in LINK_RE.findall(path.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                checked += 1
                resolved = (path.parent / target.split("#")[0]).resolve()
                with self.subTest(source=path.name, target=target):
                    self.assertTrue(
                        resolved.is_file(),
                        f"{path} cites {target}, which does not exist",
                    )
        self.assertTrue(checked, "found no composition links to resolve")


class TestWorkflowSkills(unittest.TestCase):
    """Every library workflow is one manual-only skill calling bricks."""

    WORKFLOWS = (
        "benchmaker", "browser-game", "drift-canary", "evolve", "renovate",
        "self-improve", "skill-tournament", "super-research",
    )

    def test_every_workflow_directory_holds_exactly_one_body(self):
        directories = workflow_directories()

        self.assertEqual(
            list(self.WORKFLOWS), [directory.name for directory in directories]
        )
        for directory in directories:
            with self.subTest(workflow=directory.name):
                self.assertEqual(
                    [WORKFLOW_FILE],
                    sorted(path.name for path in directory.glob("*.md")),
                )

    def test_every_workflow_declares_its_name_and_manual_invocation(self):
        for directory in workflow_directories():
            with self.subTest(workflow=directory.name):
                fields, _ = split_document(directory / WORKFLOW_FILE)
                self.assertEqual(directory.name, fields.get("name"))
                self.assertTrue(fields.get("description"))
                self.assertEqual("true", fields.get("disable-model-invocation"))
                self.assertNotIn("entry", fields)
                self.assertNotIn("placeholders", fields)

    def test_every_workflow_opens_a_frame_calls_or_nests_and_closes(self):
        """A workflow either stamps a pack on a brick call of its own, or
        nests another workflow's frame under its own; `skill-tournament` is
        the second shape, and packs bind per brick, never per workflow."""

        registered = set(CALLABLE_EXECUTORS)
        for directory in workflow_directories():
            with self.subTest(workflow=directory.name):
                body = (directory / WORKFLOW_FILE).read_text(encoding="utf-8")
                self.assertIn("tickets.py frame-open", body)
                self.assertIn("tickets.py frame-close", body)
                self.assertTrue(
                    "--pack " in body or "frame-open <run> --parent" in body,
                    f"{directory.name} neither calls a brick nor nests a frame",
                )
                # No retired callable survives the conversion: every name
                # the registry knows as superseded, not a hand-picked
                # subset of it (report P6; a subset is how a name the
                # registry already tracks slips back in unnoticed).
                for retired in SUPERSEDED_EXECUTORS:
                    self.assertNotIn(retired, body)
                for token in ("orch-do", "orch-judge"):
                    self.assertIn(token, registered)
