"""Candidate workspaces report actual mutations without predicted-scope grading."""
import types
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from scripts import tickets_adapters, tickets_land, workspace, workspace_candidate

from tests.test_workspace_cases.candidate_cases import (  # noqa: F401
    TestDerivedCandidatePaths,
    TestEstablishCreatesTheDerivedCandidate,
    TestEstablishRefusesRatherThanRecording,
    TestEveryExitPathEmitsOneDocument,
    TestFacadeDispatchesDistinctCandidates,
    TestOwnershipOfTheEstablishmentLanes,
    TestRetireRemovesTheDerivedCandidate,
)
from tests.test_workspace_cases.cli_cases import (  # noqa: F401
    NoFormatCallsTest,
    TestHelpAndVantage,
)
from tests.test_workspace_cases.document_cases import (  # noqa: F401
    TestTheDocumentLaneObservesTheTreeItStandsIn,
    TestTheRefusalSurvivesForWhatCannotBeGiven,
    TestTheTrunkDispatchesAndLandsADocumentItem,
)
from tests.test_workspace_cases.contract_cases import (  # noqa: F401
    TestContractKeySeam,
    TestScriptShape,
)
from tests.test_workspace_cases.emission_cases import (  # noqa: F401
    TestBaselineIsWrittenOnce,
    TestBytecodeIsEmissionNotBreach,
)
from tests.test_workspace_cases.integration_cases import (  # noqa: F401
    TestARefusedRetirementNeverPrescribesForce,
    TestAnAbsentIntegrationNamesWhereItLooked,
    TestAnUncommittedDeliveryIsNotAReplay,
    TestOneSystemWrittenNotePerObservation,
    TestOnlyADeclaringEstablishmentFixesTheTarget,
    TestTheRunOwnsWhereItsWorkIsIntegrated,
)
from tests.test_workspace_cases.grade_cases import (  # noqa: F401
    RuntimeInterpreterBoundaryTests,
    TestCheckGradesFromTheCallersGit,
    TestVerdictSurvivesCleanupAndScopeIsSegmentExact,
)
from tests.test_workspace_cases.operation_cases import (  # noqa: F401
    TestJoinGradesActualOperations,
)
from tests.test_workspace_cases.prepare import (  # noqa: F401
    TestDetachedWorkspaceIsRecordedAndGraded,
    TestPrepareInstallsTheFrontendTree,
    TestPrepareReportsTheBrowserWithoutFetchingOne,
    TestPreparationIsOutsideEveryLock,
    TestTheInstallCeilingIsReal,
)
from tests.test_workspace_cases.sharing_cases import (  # noqa: F401
    TestStartSeesWhoElseRecordedThisTree,
    TestTheSharedTreeCodeIsItsOwnAndDocumented,
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


def bound_names(module) -> set:
    """Every name ``module`` bound at import, module aliases resolved.

    A check about what a module reaches is a check about its namespace, not
    about its bytes: `import x`, `from p import x` and `import p.x as x` all
    land here, and none of them needs the file read back as text.
    """

    names = set(vars(module))
    for value in vars(module).values():
        if isinstance(value, types.ModuleType):
            names.add(value.__name__.rsplit(".", 1)[-1])
    return names


class WorkspaceTest(unittest.TestCase):
    def test_actual_mutations_include_every_changed_and_new_path(self):
        self.assertEqual([("change", "a.py"), ("create", "new.py")], workspace._actual_mutations("M\0a.py\0A\0new.py\0"))

    def test_workspace_does_not_import_scope_authority(self):
        """Shape, not source text: an import binds a name in the namespace."""

        for module in (workspace, workspace_candidate):
            with self.subTest(module.__name__):
                self.assertEqual(
                    set(),
                    bound_names(module) & {"workspace_scope", "tickets_scope"},
                )

    def test_establishment_dispatches_on_the_registered_workspace_strategy(self):
        """The lane names are the registry's, not the candidate owner's.

        What the source-text form asserted -- that the branch reads a
        registered field rather than a mechanism spelled inline -- is this
        set: every strategy the candidate owner branches on is one the
        adapter registry hands out, and the registry hands out no third one
        that would reach neither lane. The refusal that guards the
        unestablishable case is graded live, by its message, in
        `tests/test_workspace_cases/document_cases.py`.
        """

        registered = {
            adapter.workspace_strategy
            for adapter in tickets_adapters.ADAPTER_REGISTRY.values()
        }
        self.assertIn(workspace_candidate.GIT_STRATEGY, registered)
        self.assertIn(workspace_candidate.EVIDENCE_STRATEGY, registered)
        for adapter in tickets_adapters.ADAPTER_REGISTRY.values():
            with self.subTest(adapter.key):
                self.assertIsInstance(adapter.workspace_strategy, str)
                self.assertIsInstance(adapter.establishes_isolation, bool)


class WorkspaceAdapterSelectionTest(unittest.TestCase):
    def test_an_empty_persisted_adapter_refuses(self):
        with self.assertRaises(tickets_adapters.AdapterError) as raised:
            tickets_adapters.adapter_for_ticket({"workspace_adapter": "   "})
        self.assertEqual("workspace-adapter-invalid", raised.exception.code)

    def test_plain_existing_directory_infers_document_tree(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(
            tickets_adapters.subprocess, "run",
            return_value=types.SimpleNamespace(returncode=128, stdout="", stderr="not a repository"),
        ):
            self.assertEqual("document-tree", tickets_adapters.infer_adapter(tmp).key)

    def test_failed_git_checkout_probe_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".git").mkdir()
            with mock.patch.object(
                tickets_adapters.subprocess, "run",
                return_value=types.SimpleNamespace(
                    returncode=128, stdout="", stderr="dubious ownership",
                ),
            ):
                with self.assertRaises(tickets_adapters.AdapterError) as raised:
                    tickets_adapters.infer_adapter(tmp)
        self.assertEqual("workspace-git-invalid", raised.exception.code)

    def test_competing_legacy_hints_refuse_before_cwd_inference(self):
        with mock.patch.object(
            tickets_adapters, "legacy_adapter_hints",
            return_value=("git", "document-tree"),
        ):
            with self.assertRaises(tickets_adapters.AdapterError) as raised:
                tickets_adapters.select_adapter(standards=("a", "b"), target=Path.cwd())
        self.assertEqual("workspace-adapter-ambiguous", raised.exception.code)

    def test_landing_refuses_an_unresolved_binding_instead_of_skipping_it(self):
        data = {"workspace_adapter": ""}

        integrated = tickets_land._integrate_workspace(
            "run", "B1", data, None, Path("ticket.md"), "driver",
        )
        retired = tickets_land._retire_workspace("run", "B1", "complete", data)

        self.assertEqual("refused", integrated["outcome"])
        self.assertEqual("workspace-adapter-invalid", integrated["code"])
        self.assertEqual("refused", retired["outcome"])
        self.assertEqual("workspace-adapter-invalid", retired["code"])
