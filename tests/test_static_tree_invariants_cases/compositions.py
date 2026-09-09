"""Static invariants owned by the library's workflow skills."""
import re
import unittest

from scripts.tickets_registry import CALLABLE_EXECUTORS, SUPERSEDED_EXECUTORS

from ._support import (
    COMPOSITIONS,
    LINK_RE,
    WORKFLOW_FILE,
    split_document,
    validate,
    workflow_directories,
)


class TestCompositionLinks(unittest.TestCase):
    """Every local markdown link from a workflow resolves."""

    def test_every_composition_link_resolves(self):
        checked = 0
        for path in validate.owned_markdown_files(COMPOSITIONS):
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
    """Every library workflow is one manual-only skill calling callables."""

    def calls_or_nests(self, body, name):
        public = {path.parent.name for home in
                  (COMPOSITIONS, COMPOSITIONS.parent / "skills" / "workflows")
                  for path in home.glob("*/SKILL.md")}
        calls = set(re.findall(r"`([a-z][a-z0-9-]*)`", body))
        return ("--standard " in body or bool(re.search(r"(?m)^\s*tickets\.py\s+frame-open\s+<run>\s+[^\n]*--parent\s+<frame>(?:\s|$)", body))
                or bool(calls & (public - {name})))

    def test_every_workflow_directory_holds_exactly_one_body(self):
        directories = workflow_directories()

        expected = sorted(
            path.name for path in COMPOSITIONS.iterdir()
            if path.is_dir() and path.name != "references"
        )
        self.assertTrue(expected)
        self.assertEqual(expected, [directory.name for directory in directories])
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

    def test_public_call_must_resolve_and_cannot_call_itself(self):
        self.assertTrue(self.calls_or_nests("Invoke `checkpointed-build`.", "builder"))
        self.assertFalse(self.calls_or_nests("Invoke `missing-workflow`.", "builder"))
        self.assertFalse(self.calls_or_nests("Invoke `checkpointed-build`.", "checkpointed-build"))

    def test_every_workflow_opens_a_frame_calls_or_nests_and_closes(self):
        """A workflow either stamps a standard on a callable call of its own, or
        invokes a resolved public workflow or nests its frame. Standards
        bind per callable, never per workflow."""

        registered = set(CALLABLE_EXECUTORS)
        for directory in workflow_directories():
            with self.subTest(workflow=directory.name):
                body = (directory / WORKFLOW_FILE).read_text(encoding="utf-8")
                self.assertIn("tickets.py frame-open", body)
                self.assertIn("tickets.py frame-close", body)
                self.assertTrue(
                    self.calls_or_nests(body, directory.name),
                    f"{directory.name} neither calls a callable nor nests a frame",
                )
                # No retired callable survives the conversion: every name
                # the registry knows as superseded, not a hand-picked
                # subset of it (report P6; a subset is how a name the
                # registry already tracks slips back in unnoticed).
                for retired in SUPERSEDED_EXECUTORS:
                    self.assertNotIn(retired, body)
                for token in ("orch-do", "orch-judge"):
                    self.assertIn(token, registered)
