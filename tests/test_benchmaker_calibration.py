"""Can-fail harness tests. The native event producer is a control, not a model run."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'example-workflows' / 'benchmaker' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from admission import prepare
from grader import grade, make_record
from native import collect, write_json, run_process
from probe import probe
from records import EvidenceError, summarize
sys.path.remove(str(SCRIPTS))


from tests.benchmaker_support import CalibrationFixture


class CalibrationTests(CalibrationFixture, unittest.TestCase):
    def test_tracer_replays_native_source_and_preserves_configuration_gap(self):
        self.envelope(self.attempt())
        result = probe(self.root)
        self.assertTrue(result['workflow_admission'])
        self.assertFalse(result['calibrated_benchmark_eligible'])
        self.assertEqual(result['decision'], 'UNVERIFIED')

    def test_probe_rejects_missing_and_corrupt_output(self):
        with self.assertRaises(OSError):
            probe(self.root)
        self.envelope(self.attempt())
        transcript = self.root / 'attempt' / 'stdout.jsonl'
        transcript.write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(EvidenceError, 'corrupt'):
            probe(self.root)
        transcript.unlink()
        with self.assertRaises(OSError):
            probe(self.root)

    def test_duplicate_missing_cases_controls_only_and_wrong_configuration(self):
        record = self.attempt()
        with self.assertRaisesRegex(EvidenceError, 'duplicate'):
            summarize([record, record], self.policy)
        policy = dict(self.policy, case_ids=['case', 'missing'])
        with self.assertRaisesRegex(EvidenceError, 'missing attempts'):
            summarize([record], policy)
        with self.assertRaisesRegex(EvidenceError, 'missing or mixed'):
            summarize([dict(record, candidate_kind='control')], self.policy)
        with self.assertRaisesRegex(EvidenceError, 'wrong resolved'):
            summarize([dict(record, resolved_configuration={'model': 'different'})], self.policy)
        with self.assertRaisesRegex(EvidenceError, 'missing resolved'):
            summarize([dict(record, resolved_configuration={})], self.policy)

    def test_infrastructure_never_counts_as_target_failure(self):
        record = self.attempt(code='raise SystemExit(1)')
        self.assertEqual(record['classification'], 'environment_failure')
        self.assertFalse(record['valid_for_estimate'])
        summary = summarize([record], self.policy)
        self.assertIsNone(summary['estimate'])
        with self.assertRaisesRegex(EvidenceError, 'infrastructure counted'):
            summarize([dict(record, valid_for_estimate=True, oracle_outcome='FAIL', exclusion_reason=None)], self.policy)

    def test_established_task_timeout_is_genuine_failure_startup_is_excluded(self):
        started = "import time\nprint('{\"type\":\"turn.started\"}', flush=True)\ntime.sleep(3)"
        record = self.attempt(code=started, timeout=0.2)
        self.assertEqual(record['classification'], 'task_timeout')
        self.assertTrue(record['valid_for_estimate'])
        self.assertEqual(record['oracle_outcome'], 'FAIL')
        startup = self.attempt(name='startup', code='import time; time.sleep(3)', timeout=0.2)
        self.assertEqual(startup['classification'], 'startup_timeout')
        self.assertFalse(startup['valid_for_estimate'])

    def test_independent_grader_discriminates_wrong_and_missing_source(self):
        record = self.attempt('def solve(x): return x')
        self.assertEqual(record['oracle_outcome'], 'FAIL')
        record = self.attempt(name='missing', code="print('{\"type\":\"turn.started\"}')")
        self.assertEqual(record['classification'], 'candidate_failure')
        self.assertTrue(record['valid_for_estimate'])

    def test_equal_case_estimator_does_not_pool_trials_or_select_best(self):
        record = self.attempt()
        second = dict(record, trial=2, oracle_outcome='FAIL', failure_class='wrong_output')
        summary = summarize([record, second], dict(self.policy, trials_per_case=2))
        self.assertEqual(summary['estimate'], 0.5)
        self.assertEqual(summary['distinct_cases'], 1)
        self.assertEqual(summary['total_attempts'], 2)
        self.assertEqual(summary['band_observation'], 'IN_BAND')
        self.assertIsNone(summary['interval'])

    def test_observed_configuration_contract_can_be_calibrated(self):
        evidence = self.root / 'configuration-evidence.txt'
        evidence.write_text('Synthetic control observation; not a live model claim', encoding='utf-8')
        observation = self.root / 'configuration.json'
        write_json(observation, dict(configuration=self.config, evidence_locator=str(evidence)))
        self.policy['band'] = [1, 1]
        record = self.attempt(configuration_observation=observation)
        envelope = self.envelope(record)
        envelope['frozen_revision'] = self.revision
        write_json(self.root / 'summary.json', summarize([record], self.policy))
        write_json(self.root / 'evidence' / 'admission.json', envelope)
        self.assertTrue(probe(self.root)['calibrated_benchmark_eligible'])
        evidence.write_text('tampered', encoding='utf-8')
        with self.assertRaisesRegex(EvidenceError, 'configuration evidence changed'):
            probe(self.root)

    def test_optional_configuration_metadata_does_not_block_declared_rigor(self):
        record = self.attempt()
        summary = summarize([record], dict(self.policy, require_resolved_configuration=False, band=[1, 1]))
        self.assertEqual(summary['decision'], 'CALIBRATED')
        self.assertTrue(summary['optional_gaps'])
        self.assertFalse(summary['criterion_gaps'])

    def test_probe_rejects_absent_journal_and_uncommitted_manifest(self):
        envelope = self.envelope(self.attempt())
        journal = self.root / 'evidence' / 'journal.md'
        original = journal.read_text(encoding='utf-8')
        journal.write_text(original.replace('id: fixture', 'id: unrelated'), encoding='utf-8')
        with self.assertRaisesRegex(EvidenceError, 'absent from journals'):
            probe(self.root)
        journal.write_text(original, encoding='utf-8')
        manifest = Path(envelope['benchmark_manifest'])
        value = json.loads(manifest.read_text())
        value['uncommitted'] = True
        write_json(manifest, value)
        with self.assertRaisesRegex(EvidenceError, 'landed manifest differs'):
            probe(self.root)

    def test_probe_detects_unlisted_frozen_file(self):
        self.policy['band'] = [1, 1]
        self.policy['require_resolved_configuration'] = False
        record = self.attempt()
        envelope = self.envelope(record)
        envelope['frozen_revision'] = self.revision
        write_json(self.root / 'summary.json', summarize([record], self.policy))
        write_json(self.root / 'evidence' / 'admission.json', envelope)
        self.assertTrue(probe(self.root)['workflow_admission'])
        (self.root / 'product' / 'benchmark' / 'hidden.txt').write_text('changed final', encoding='utf-8')
        with self.assertRaisesRegex(EvidenceError, 'committed file inventory'):
            probe(self.root)

    def test_prepare_cannot_manufacture_receipt_or_completed_benchmark(self):
        result = prepare(self.root / 'fresh')
        self.assertTrue(Path(result['semantic_goal']).is_file())
        self.assertEqual(json.loads(Path(result['schema']).read_text()), {
            'type': 'object', 'properties': {'source': {'type': 'string'}},
            'required': ['source'], 'additionalProperties': False,
        })
        self.assertEqual(list(Path(result['evidence']).iterdir()), [])
        with self.assertRaises(OSError):
            probe(self.root / 'fresh')

    def test_legacy_manifest_never_enters_empirical_admission(self):
        envelope = self.envelope(self.attempt())
        legacy = SCRIPTS.parents[2] / 'tests' / 'fixtures' / 'benchmark' / 'manifest.json'
        write_json(Path(envelope['benchmark_manifest']), json.loads(legacy.read_text()))
        with self.assertRaisesRegex(EvidenceError, 'not empirical manifest v2'):
            probe(self.root)

    def test_external_probe_rejects_forged_summary_and_audit_identity(self):
        envelope = self.envelope(self.attempt())
        summary = self.root / 'summary.json'
        value = json.loads(summary.read_text())
        value['estimate'] = 0.4
        write_json(summary, value)
        with self.assertRaisesRegex(EvidenceError, 'summary differs'):
            probe(self.root)
        envelope['qualification']['audits'][0]['auditor'] = 'builder-control'
        write_json(self.root / 'evidence' / 'admission.json', envelope)
        with self.assertRaisesRegex(EvidenceError, 'independent audit'):
            probe(self.root)


if __name__ == '__main__':
    unittest.main()
