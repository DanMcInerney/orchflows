"""Canonical witnesses for the accepted ticket/dispatch/gate discrepancy register."""

import importlib
import io
import unittest
from pathlib import Path

from tools import run_tests


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def witness(carrier, identity):
    return carrier, identity


# One row per active discrepancy. A row leaves the register when its
# discrepancy is dissolved rather than fixed, and the receipt handshake
# dissolved four: the ephemeral downgrade an inline packet could attempt,
# the inline snapshot's sink authority, the accepted-receipt fence before
# execution records, and the receiver identity/profile/authority family.
# What replaced the fence -- one committed launch before any execution
# record, and the writer identity every record carries -- keeps its row.
COVERAGE = {
    "A1": (
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_noncanonical_persisted_state_is_a_byte_preserving_refusal"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_forged_stored_success_is_refused_instead_of_replayed"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_forged_outcome_success_cannot_drive_join"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_orphan_replacement_edge_is_a_byte_preserving_refusal"),
    ),
    "A2": (witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_open_requires_the_current_stored_admission_before_mutation"),),
    "A3": (
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_expiry_cannot_implicitly_open_a_successor"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_expired_attempt_can_cross_the_explicit_atomic_replacement"),
    ),
    "A4": (witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_suspended_join_retires_the_attempt_but_retains_claimant_observations"),),
    "A5": (
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_all_dispatch_state_operations_refuse_path_aliased_origins"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_dispatch_operations_refuse_a_ticket_frontmatter_origin_mismatch"),
    ),
    "A6": (witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_outcome_materializes_only_unstreamed_evidence_once"),),
    "A7": (witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_complete_code_cut_keeps_one_root_generation_before_and_after_seal"),),
    "B1": (witness("tests.test_dispatch_launch_record", "tests.test_dispatch_launch_record.DispatchCarriageTest.test_dispatch_emits_codepage_independent_canonical_ascii"),),
    "B2": (
        witness("tests.test_dispatch_launch_record", "tests.test_dispatch_launch_record.DispatchLaunchRecordTest.test_the_first_filed_record_is_the_acceptance"),
        witness("tests.test_dispatch_launch_record", "tests.test_dispatch_launch_record.DispatchLaunchRecordTest.test_an_execution_record_without_a_committed_launch_refuses"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_persisted_execution_without_a_launch_is_a_byte_preserving_refusal"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_persisted_launch_after_outcome_is_a_byte_preserving_refusal"),
    ),
    "B3": (witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_result_refuses_attempt_identity_and_writer_mismatches_without_mutation"),),
    "C1": (witness("tests.test_ticket_protocol", "tests.test_ticket_protocol.TicketProtocolTest.test_public_documents_project_the_current_dispatch_and_gate_model"),),
    "C2": (witness("tests.test_ticket_protocol", "tests.test_ticket_protocol.TicketProtocolTest.test_public_documents_project_the_current_dispatch_and_gate_model"),),
    "C3": (
        witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_preissue_lint_and_new_grade_the_same_projected_file_candidate"),
        witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_preissue_lint_and_new_refuse_the_same_file_identity_mismatch"),
    ),
    "C4": (witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_show_inspects_one_ticket_without_mutating_the_sink"),),
    "D1": (
        witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_clean_gate_uses_attributed_join_noop_and_opens_verification"),
        witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_review_schemas_reject_field_deletion_and_noop_bypass"),
    ),
    "D2": (witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_clean_gate_uses_attributed_join_noop_and_opens_verification"),),
    "D3": (witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_clean_gate_uses_attributed_join_noop_and_opens_verification"),),
    "D4": (witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_gate_stubs_freeze_pack_isolation_and_lens_order"),),
    "D5": (witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_gate_stubs_freeze_pack_isolation_and_lens_order"),),
    "D6": (witness("tests.test_ticket_protocol", "tests.test_ticket_protocol.TicketProtocolTest.test_public_documents_project_the_current_dispatch_and_gate_model"),),
    "D7": (witness("tests.test_ticket_protocol", "tests.test_ticket_protocol.TicketProtocolTest.test_public_documents_project_the_current_dispatch_and_gate_model"),),
    "D8": (witness("tests.test_ticket_dispatch_gate_coverage", "tests.test_ticket_dispatch_gate_coverage.TicketDispatchGateCoverageTest.test_obsolete_gate_fossils_are_absent"),),
    "D9": (witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_gate_stubs_freeze_pack_isolation_and_lens_order"),),
    "E1": (witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_distinct_checker_records_the_same_immutable_adjudication_carrier"),),
    "E2": (
        witness("tests.test_workspace", "tests.test_workspace_cases.start_cases.TestStartRecordsWhatItObserved.test_from_a_linked_worktree_it_writes_the_main_root_ticket_only"),
        witness("tests.test_workspace", "tests.test_workspace_cases.start_cases.TestCheckUsesTheEstablishedCandidate.test_relocated_branch_does_not_replace_the_recorded_workspace"),
    ),
    "E3": (witness("tests.test_workspace", "tests.test_workspace_cases.start_cases.TestStartEstablishesEvidenceStore.test_research_pack_creates_and_records_the_canonical_run_store"),),
}
# The active count per family, declared rather than derived from a range,
# so a row that leaves the register has to leave here too.
FAMILIES = {"A": 7, "B": 3, "C": 4, "D": 9, "E": 3}


class TicketDispatchGateCoverageTest(unittest.TestCase):
    def test_obsolete_gate_fossils_are_absent(self):
        fossils = (
            TESTS / "test_tickets_cases" / "gate_blocking.py",
            TESTS / "test_tickets_view_cases" / "gate_stubs.py",
            # The whole package went with the drivers commit 932706a3 deleted;
            # ReviewBundleContractTest lived here and is gone with it.
            TESTS / "test_contracts_cases" / "rules.py",
        )
        self.assertEqual([], [str(path.relative_to(ROOT)) for path in fossils if path.exists()])
        manifest = (TESTS / "serial_compat_manifest.json").read_text(encoding="utf-8")
        for module in (
            "tests.test_tickets_cases.gate_blocking",
            "tests.test_tickets_view_cases.gate_stubs",
        ):
            self.assertNotIn(module, manifest)

    def test_every_active_discrepancy_has_a_routine_canonical_witness(self):
        expected = {
            letter + str(number)
            for letter, count in FAMILIES.items()
            for number in range(1, count + 1)
        }
        self.assertEqual(expected, set(COVERAGE))
        canonical_modules = set(run_tests.discover(TESTS)[2])
        loaded = {}
        selected = {}
        for discrepancy, witnesses in COVERAGE.items():
            self.assertTrue(witnesses, discrepancy)
            for carrier, identity in witnesses:
                self.assertIn(carrier, canonical_modules, discrepancy)
                if carrier not in loaded:
                    suite = unittest.defaultTestLoader.loadTestsFromModule(
                        importlib.import_module(carrier)
                    )
                    loaded[carrier] = {case.id(): case for case in self._cases(suite)}
                self.assertIn(identity, loaded[carrier], discrepancy)
                selected.setdefault(identity, loaded[carrier][identity])
        stream = io.StringIO()
        result = unittest.TextTestRunner(stream=stream, verbosity=0).run(
            unittest.TestSuite(selected.values())
        )
        self.assertTrue(result.wasSuccessful(), stream.getvalue())

    @classmethod
    def _cases(cls, suite):
        for item in suite:
            if isinstance(item, unittest.TestSuite):
                yield from cls._cases(item)
            else:
                yield item
