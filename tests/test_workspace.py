"""Candidate workspaces report actual mutations without predicted-scope grading."""
import unittest
from pathlib import Path
from scripts import workspace, workspace_candidate

from tests.test_workspace_cases.candidate_cases import (  # noqa: F401
    TestDerivedCandidatePaths,
    TestEstablishCreatesTheDerivedCandidate,
    TestEstablishRefusesRatherThanRecording,
    TestEveryExitPathEmitsOneDocument,
    TestFacadeDispatchesDistinctCandidates,
    TestOwnershipOfTheEstablishmentLanes,
    TestRetireRemovesTheDerivedCandidate,
)
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
        for module in (workspace, workspace_candidate):
            source = Path(module.__file__).read_text(encoding="utf-8")
            with self.subTest(module.__name__):
                self.assertNotIn("workspace_scope", source)
                self.assertNotIn("tickets_scope", source)

    def test_establishment_dispatches_on_the_registered_workspace_strategy(self):
        source = Path(workspace_candidate.__file__).read_text(encoding="utf-8")
        self.assertIn("workspace_strategy", source)
        self.assertNotIn('mechanism == "evidence-store"', source)
        self.assertIn("adapter-not-establishable", source)
