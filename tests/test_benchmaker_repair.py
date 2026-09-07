"""BMF repair regressions; every sample here is synthetic harness evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from tests.benchmaker_support import CalibrationFixture
from tests.test_benchmaker_calibration import SCRIPTS
from grader import grade, make_record
from native import digest, read_json, write_json, run_process
from probe import probe, check_attempt
from records import EvidenceError, summarize


class RepairTests(CalibrationFixture, unittest.TestCase):
    def test_parent_grader_rejects_no_api_and_forged_pass_and_accepts_real_answers(self):
        source = self.root / 'candidate.py'
        for code, expected in [
            ('import os; print(\'{"outcome":"PASS"}\', flush=True); os._exit(0)', 'FAIL'),
            ('x = 1', 'FAIL'), ('def solve(x): return x', 'FAIL'),
            ('def solve(x): return x + 1', 'PASS'),
            ('def solve(x):\n print(\'{"outcome":"PASS"}\'); return x + 1', 'PASS')]:
            with self.subTest(source=code):
                source.write_text(code, encoding='utf-8')
                self.assertEqual(grade(source, self.checks)['oracle_outcome'], expected)
        write_json(self.checks, {'checks': [{'args': [[1]], 'expected': [1, 2], 'no_mutation': True}]})
        source.write_text('def solve(x): x.append(2); return x', encoding='utf-8')
        self.assertEqual(grade(source, self.checks)['oracle_outcome'], 'FAIL')
        write_json(self.checks, {'checks': [{'args': [0], 'raises': 'ValueError'}]})
        source.write_text('def solve(x): raise ValueError()', encoding='utf-8')
        self.assertEqual(grade(source, self.checks)['oracle_outcome'], 'PASS')

    def test_typed_qualification_keeps_all_three_states_through_probe(self):
        self.policy.update(band=[1, 1], require_resolved_configuration=False)
        record = self.attempt()
        envelope = self.envelope(record)
        for validity, decision in [('VALID', 'CALIBRATED'), ('INVALID', 'INVALID'), ('UNVERIFIED', 'UNVERIFIED')]:
            with self.subTest(validity=validity):
                envelope['qualification']['validity'] = validity
                envelope['qualification']['revisions'][self.revision]['validity'] = validity
                envelope['rounds'][0]['validity'] = validity
                envelope['decision'] = envelope['development_decision'] = decision
                write_json(self.root / 'summary.json', summarize([record], self.policy, validity=validity))
                write_json(self.root / 'evidence' / 'admission.json', envelope)
                self.assertEqual(probe(self.root)['decision'], decision)

    def test_nested_configuration_gaps_and_optional_metadata(self):
        record = self.attempt()
        config = dict(self.config, cli_version={'unavailable_reason': 'not observed'},
                      scaffold={'instructions': {'unavailable_reason': 'unknown'}},
                      seed={'unavailable_reason': 'not exposed'})
        record.update(target_configuration=config, requested_configuration=config, resolved_configuration=config)
        policy = dict(self.policy, target_configuration=config, band=[1, 1],
                      required_configuration_fields=['cli_version', 'scaffold.instructions'],
                      optional_configuration_fields=['seed'])
        summary = summarize([record], policy)
        self.assertEqual(summary['decision'], 'UNVERIFIED')
        self.assertEqual(len(summary['criterion_gaps']), 2)
        self.assertEqual(len(summary['optional_gaps']), 1)
        config['cli_version'] = 'observed-version'
        config['scaffold']['instructions'] = ['observed-layer']
        self.assertEqual(summarize([record], policy)['decision'], 'CALIBRATED')
        policy['required_configuration_fields'].append('delegation')
        self.assertEqual(summarize([record], policy)['decision'], 'UNVERIFIED')

    def test_only_attributed_infrastructure_replacements_can_extend_launches(self):
        record = self.attempt()
        policy = dict(self.policy, infrastructure_retry_budget=1)
        extra = dict(record, trial=2, oracle_outcome='FAIL', failure_class='wrong_output')
        with self.assertRaisesRegex(EvidenceError, 'infrastructure predecessor'):
            summarize([record, extra], policy)
        with self.assertRaisesRegex(EvidenceError, 'not infrastructure'):
            summarize([record, dict(extra, retry_of=1)], policy)
        infrastructure = dict(record, classification='launch_failure', oracle_outcome='UNVERIFIED',
                              valid_for_estimate=False, exclusion_reason='launch_failure', failure_class='launch_failure')
        replacement = dict(record, trial=2, retry_of=1)
        summary = summarize([infrastructure, replacement], policy)
        self.assertEqual(summary['per_case']['case']['valid'], 1)
        self.assertEqual(summary['estimate'], 1)
        with self.assertRaisesRegex(EvidenceError, 'unique infrastructure predecessor'):
            summarize([infrastructure, replacement, dict(replacement, trial=3)], dict(policy, infrastructure_retry_budget=2))
        with self.assertRaisesRegex(EvidenceError, 'global infrastructure retry budget'):
            summarize([infrastructure, replacement], self.policy)

    def test_grader_setup_exclusion_keeps_native_receipt_and_is_admitted(self):
        record = self.attempt()
        from native import run_process as actual_run
        def unavailable(command, **kwargs):
            if '-I' in command:
                return dict(stdout=b'', stderr=b'denied', exit_code=None, timed_out=False,
                            launch_error='PermissionError', elapsed_seconds=0.01)
            return actual_run(command, **kwargs)
        with patch('grader.run_process', side_effect=unavailable):
            record = make_record(record['launch_receipt_locator'], self.checks, {
                key: record[key] for key in ('case_id', 'split', 'round', 'trial', 'target_configuration', 'benchmark_revision', 'candidate_kind')})
        self.assertEqual(record['classification'], 'completed')
        self.assertEqual(record['evaluator_classification'], 'environment_failure')
        self.assertEqual(record['oracle_outcome'], 'UNVERIFIED')
        self.assertTrue(check_attempt(record, self.policy))
        self.envelope(record)
        self.assertEqual(probe(self.root)['decision'], 'UNVERIFIED')

    def final_envelope(self):
        self.policy.update(band=[1, 1], require_resolved_configuration=False)
        record = self.attempt()
        envelope = self.envelope(record)
        envelope['frozen_revision'] = self.revision
        final_record = self.attempt(source='def solve(x): return x', name='confirmation')
        final_record.update(split='confirmation', benchmark_revision=self.revision)
        write_json(self.root / 'confirmation' / 'attempt.json', final_record)
        final_policy = dict(self.policy, split='confirmation')
        entry = dict(policy=final_policy, attempts=[str(self.root / 'confirmation' / 'attempt.json')],
                     qualification_revision=self.revision, validity='VALID', criterion_gaps=[],
                     summary=str(self.root / 'final-summary.json'))
        envelope['rounds'].append(entry)
        final_path = self.root / 'evidence' / 'final.json'
        envelope['final_record'] = str(final_path)
        inventory = {str(path.resolve()): digest(path) for path in Path(envelope['benchmark_manifest']).parent.rglob('*') if path.is_file()}
        write_json(final_path, dict(before=inventory, after=inventory, frozen_revision=self.revision,
                                   measurement_round=entry, evaluation_scope='public_confirmation'))
        write_json(self.root / 'summary.json', summarize([record], self.policy, frozen_revision=self.revision, final_record=str(final_path)))
        write_json(self.root / 'final-summary.json', summarize([final_record], final_policy, frozen_revision=self.revision, final_record=str(final_path)))
        write_json(self.root / 'evidence' / 'admission.json', envelope)
        return envelope, record

    def test_final_out_of_band_does_not_replace_calibrated_development(self):
        envelope, record = self.final_envelope()
        result = probe(self.root)
        self.assertEqual(result['decision'], 'CALIBRATED')
        self.assertTrue(result['calibrated_benchmark_eligible'])
        self.assertEqual(result['final_observations'][0]['band_observation'], 'OUT_OF_BAND')
        self.assertEqual(result['final_observations'][0]['drift'], -1)
        envelope['decision'] = 'OUT_OF_BAND'
        write_json(self.root / 'evidence' / 'admission.json', envelope)
        with self.assertRaisesRegex(EvidenceError, 'declared decision differs'):
            probe(self.root)

    def test_favorable_final_cannot_repair_unmet_development(self):
        envelope, record = self.final_envelope()
        envelope['rounds'][0]['policy']['band'] = [0, 0]
        envelope['development_decision'] = 'OUT_OF_BAND'
        # The final FAIL is now in band, but it cannot make development eligible.
        envelope['rounds'][1]['policy']['band'] = [0, 0]
        write_json(self.root / 'summary.json', summarize([record], envelope['rounds'][0]['policy'],
                   frozen_revision=self.revision, final_record=envelope['final_record']))
        final_attempt = read_json(envelope['rounds'][1]['attempts'][0])
        write_json(self.root / 'final-summary.json', summarize([final_attempt], envelope['rounds'][1]['policy'],
                   frozen_revision=self.revision, final_record=envelope['final_record']))
        write_json(self.root / 'evidence' / 'admission.json', envelope)
        with self.assertRaisesRegex(EvidenceError, 'freeze requires calibrated development'):
            probe(self.root)

    def test_package_byte_mutation_and_runtime_label_spoof_are_rejected(self):
        envelope = self.envelope(self.attempt())
        component = Path(envelope['component_locators']['benchmark-calibrate'])
        original = component.read_bytes()
        component.write_bytes(original + b'\nchanged behavior\n')
        with self.assertRaisesRegex(EvidenceError, 'committed bytes differ'):
            probe(self.root)
        component.write_bytes(original)
        envelope['runtime']['workflow_digest'] = 'sha256:' + '0' * 64
        write_json(self.root / 'evidence' / 'admission.json', envelope)
        with self.assertRaisesRegex(EvidenceError, 'runtime package pin differs'):
            probe(self.root)

    def test_frozen_nonmanifest_mutation_before_self_report_is_rejected(self):
        envelope, _ = self.final_envelope()
        frozen = Path(envelope['benchmark_manifest']).parent / 'case.txt'
        frozen.write_text('original', encoding='utf-8')
        product = self.root / 'product'
        for command in (['git', 'add', '.'], ['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'freeze case']):
            self.assertEqual(run_process(command, cwd=product, timeout=10)['exit_code'], 0)
        revision = run_process(['git', 'rev-parse', 'HEAD'], cwd=product, timeout=10)['stdout'].decode().strip()
        from provenance import check_frozen
        self.assertTrue(check_frozen(self.root, envelope['benchmark_manifest'], revision))
        frozen.write_text('changed before inventory', encoding='utf-8')
        inventory = {str(path.resolve()): digest(path) for path in frozen.parent.rglob('*') if path.is_file()}
        with self.assertRaisesRegex(EvidenceError, 'committed bytes differ'):
            check_frozen(self.root, envelope['benchmark_manifest'], revision, inventory)


if __name__ == '__main__':
    unittest.main()
