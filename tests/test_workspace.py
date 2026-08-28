"""Candidate workspaces report actual mutations without predicted-scope grading."""
import unittest
from pathlib import Path
from scripts import workspace

from tests.test_workspace_cases.start_cases import (  # noqa: F401
    TestCheckDisambiguatesItsRevisionRanges,
    TestCheckUsesTheEstablishedCandidate,
    TestStartEstablishesEvidenceStore,
    TestStartFailureBehavior,
    TestStartRecordsWhatItObserved,
    TestTicketsPayloadIsGradedNotItsExitStatus,
    TestTheStampPreservesTheTicketsByteDomain,
)


class WorkspaceTest(unittest.TestCase):
    def test_actual_mutations_include_every_changed_and_new_path(self):
        self.assertEqual([("change", "a.py"), ("create", "new.py")], workspace._actual_mutations("M\0a.py\0A\0new.py\0"))

    def test_workspace_does_not_import_scope_authority(self):
        source = Path(workspace.__file__).read_text(encoding="utf-8")
        self.assertNotIn("workspace_scope", source)
        self.assertNotIn("tickets_scope", source)
