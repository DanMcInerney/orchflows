"""Canonical witnesses for the accepted ticket/packet/gate discrepancy register."""

import importlib
import io
import unittest
from pathlib import Path

from tools import run_tests


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def witness(carrier, identity):
    return carrier, identity


COVERAGE = {
    "A1": (
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_noncanonical_persisted_state_is_a_byte_preserving_refusal"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_forged_stored_success_is_refused_instead_of_replayed"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_forged_outcome_success_cannot_drive_join"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_orphan_replacement_edge_is_a_byte_preserving_refusal"),
    ),
    "A2": (witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_open_requires_the_current_stored_admission_before_mutation"),),
    "A3": (witness("tests.test_dispatch_packet_v1", "tests.test_dispatch_packet_v1.DispatchPacketV1Test.test_reference_ticket_packet_cannot_be_downgraded_to_ephemeral"),),
    "A4": (
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_expiry_cannot_implicitly_open_a_successor"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_expired_attempt_can_cross_the_explicit_atomic_replacement"),
    ),
    "A5": (witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_suspended_join_retires_the_attempt_but_retains_claimant_observations"),),
    "A6": (
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_all_dispatch_state_operations_refuse_path_aliased_origins"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_dispatch_operations_refuse_a_ticket_frontmatter_origin_mismatch"),
    ),
    "A7": (witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_outcome_materializes_only_unstreamed_evidence_once"),),
    "A8": (witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_complete_code_cut_keeps_one_root_generation_before_and_after_seal"),),
    "B1": (
        witness("tests.test_dispatch_packet_v1", "tests.test_dispatch_packet_v1.DispatchPacketV1Test.test_inline_snapshot_requires_the_authoritative_state_sink"),
        witness("tests.test_dispatch_packet_v1", "tests.test_dispatch_packet_v1.DispatchPacketV1Test.test_inline_tampering_and_reference_divergence_refuse"),
    ),
    "B2": (
        witness("tests.test_dispatch_packet_v1", "tests.test_dispatch_packet_v1.DispatchPacketV1Test.test_file_and_standard_input_carry_the_packet_without_shell_reconstruction"),
        witness("tests.test_dispatch_packet_v1", "tests.test_dispatch_packet_v1.DispatchPacketV1Test.test_wrapper_and_malformed_file_refuse_without_ticket_mutation"),
        witness("tests.test_dispatch_packet_v1", "tests.test_dispatch_packet_v1.DispatchPacketV1Test.test_packet_command_emits_codepage_independent_canonical_ascii"),
    ),
    "B3": (
        witness("tests.test_dispatch_packet_v1", "tests.test_dispatch_packet_v1.DispatchPacketV1Test.test_accepted_receipt_is_a_durable_replayable_attempt_record"),
        witness("tests.test_dispatch_packet_v1", "tests.test_dispatch_packet_v1.DispatchPacketV1Test.test_result_outcome_and_join_require_the_accepted_receipt"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_persisted_execution_without_the_receipt_is_a_byte_preserving_refusal"),
        witness("tests.test_dispatch_v1", "tests.test_dispatch_v1.DispatchV1Test.test_persisted_receipt_after_outcome_is_a_byte_preserving_refusal"),
    ),
    "B4": (witness("tests.test_dispatch_packet_v1", "tests.test_dispatch_packet_v1.DispatchPacketV1Test.test_receipt_refuses_identity_profile_and_authority_mismatches"),),
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
    "D8": (witness("tests.test_ticket_packet_gate_coverage", "tests.test_ticket_packet_gate_coverage.TicketPacketGateCoverageTest.test_obsolete_gate_fossils_are_absent"),),
    "D9": (witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_gate_stubs_freeze_pack_isolation_and_lens_order"),),
    "E1": (witness("tests.test_ticket_semantic_contract", "tests.test_ticket_semantic_contract.SemanticTicketContractTest.test_distinct_checker_records_the_same_immutable_adjudication_carrier"),),
    "E2": (
        witness("tests.test_workspace", "tests.test_workspace_cases.start_cases.TestStartRecordsWhatItObserved.test_from_a_linked_worktree_it_writes_the_main_root_ticket_only"),
        witness("tests.test_workspace", "tests.test_workspace_cases.start_cases.TestCheckUsesTheEstablishedCandidate.test_relocated_branch_does_not_replace_the_recorded_workspace"),
    ),
    "E3": (witness("tests.test_workspace", "tests.test_workspace_cases.start_cases.TestStartEstablishesEvidenceStore.test_research_pack_creates_and_records_the_canonical_run_store"),),
}


class TicketPacketGateCoverageTest(unittest.TestCase):
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
            *("A" + str(number) for number in range(1, 9)),
            *("B" + str(number) for number in range(1, 5)),
            *("C" + str(number) for number in range(1, 5)),
            *("D" + str(number) for number in range(1, 10)),
            *("E" + str(number) for number in range(1, 4)),
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
