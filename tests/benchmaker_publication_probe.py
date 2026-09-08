"""Real establish/commit/integrate/export order with synthetic observed trial data."""
import importlib.util
import json
from pathlib import Path
import unittest

from tests.benchmaker_support import CalibrationFixture
from tests.test_benchmaker_calibration import SCRIPTS
from tests._repo_root import ROOT
from tests.test_workspace_cases import common
from tests.test_workspace_cases.integration_cases import baseline_of
from scripts import state_root, workspace_return
from native import read_json, write_json, digest, run_process
from probe import probe
from records import summarize

spec = importlib.util.spec_from_file_location('publication_exports', SCRIPTS / 'export.py')
exports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exports)


class PublicationTests(CalibrationFixture, unittest.TestCase):
    def publish(self, tid, files):
        ticket = common.make_ticket(self.run_dir, tid, scope=('records',))
        established = common.run_workspace(ROOT, 'establish', 'testrun', tid, '--repo', str(self.root / 'product'))
        self.assertEqual(established.returncode, 0, established.stderr)
        candidate = state_root.candidate_paths('testrun', tid)
        commit = common.commit_in(candidate['path'], files, 'publish ' + tid)
        result, code = workspace_return.integrate('testrun', tid, candidate['path'], candidate['branch'], baseline_of(ticket))
        self.assertEqual(code, 0, result)
        self.assertNotEqual(result['integrate']['outcome'], 'absent')
        exports.export_records(self.root / 'product', commit, 'records', self.root / 'evidence')
        return commit

    def begin_publication(self, band):
        self.policy.update(band=band, require_resolved_configuration=False)
        record = self.attempt()
        envelope = self.envelope(record)
        (self.root / 'evidence' / 'admission.json').unlink()
        sink = common.use_sink(self.root)
        self.run_dir = sink / 'tickets' / 'testrun'
        self.run_dir.mkdir(parents=True)
        original = (self.root / 'summary.json').read_bytes()
        self.publish('T1', {'records/.gitattributes': '* -text\n',
                           'records/round0.json': (self.root / 'summary.json').read_text(encoding='utf-8')})
        envelope['rounds'][0]['summary'] = str(self.root / 'evidence' / 'round0.json')
        self.assertEqual((self.root / 'evidence' / 'round0.json').read_bytes(), original)
        return envelope, record, original

    def finalize(self, envelope, files, original):
        # This new maker receives the diagnosis only after T1's immutable export.
        files['records/admission.json'] = json.dumps(envelope, indent=2, sort_keys=True) + '\n'
        self.publish('T2', files)
        self.assertEqual((self.root / 'evidence' / 'round0.json').read_bytes(), original)
        return probe(self.root)

    def partial(self, validity, expected):
        envelope, record, original = self.begin_publication([0, 0] if expected == 'OUT_OF_BAND' else [1, 1])
        diagnosis = dict(validity=validity, criterion_gaps=['independent diagnosis unavailable'] if validity == 'UNVERIFIED' else [])
        envelope['development_evidence'] = diagnosis
        envelope['development_decision'] = envelope['decision'] = expected
        envelope['final_record'] = str(self.root / 'evidence' / 'not-performed.json')
        result = self.finalize(envelope, {
            'records/diagnosis.json': json.dumps(diagnosis) + '\n',
            'records/not-performed.json': json.dumps({'not_performed_reason': expected}) + '\n'}, original)
        self.assertEqual(result['decision'], expected)
        self.assertFalse(result['calibrated_benchmark_eligible'])
        self.assertTrue((self.root / 'evidence' / 'diagnosis.json').is_file())

    def test_post_diagnosis_unverified_index_has_ordinary_landed_owner(self):
        self.partial('UNVERIFIED', 'UNVERIFIED')

    def test_post_diagnosis_out_of_band_index_has_ordinary_landed_owner(self):
        self.partial('VALID', 'OUT_OF_BAND')

    def test_final_metadata_does_not_rewrite_published_development_snapshot(self):
        envelope, record, original = self.begin_publication([1, 1])
        envelope['frozen_revision'] = self.revision
        final_attempt = self.attempt('def solve(x): return x', name='confirmation', split='confirmation')
        final_policy = dict(self.policy, split='confirmation')
        entry = dict(policy=final_policy, attempts=[str(self.root / 'confirmation' / 'attempt.json')],
                     qualification_revision=self.revision, validity='VALID', criterion_gaps=[],
                     summary=str(self.root / 'evidence' / 'final-summary.json'))
        envelope['rounds'].append(entry)
        envelope['final_record'] = str(self.root / 'evidence' / 'final.json')
        inventory = {str(path.resolve()): digest(path) for path in (self.root / 'product' / 'benchmark').rglob('*') if path.is_file()}
        final = dict(before=inventory, after=inventory, frozen_revision=self.revision,
                     measurement_round=entry, evaluation_scope='public_confirmation')
        result = self.finalize(envelope, {
            'records/final-summary.json': json.dumps(summarize([final_attempt], final_policy), indent=2, sort_keys=True) + '\n',
            'records/final.json': json.dumps(final, indent=2, sort_keys=True) + '\n'}, original)
        self.assertEqual(result['decision'], 'CALIBRATED')
        self.assertEqual(result['final_observations'][0]['estimate'], 0)
        summary = read_json(self.root / 'evidence' / 'round0.json')
        self.assertFalse({'revision_ledger', 'frozen_revision', 'final_record'} & summary.keys())
        self.assertTrue(result['calibrated_benchmark_eligible'])


if __name__ == '__main__':
    unittest.main()
