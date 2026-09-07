"""Second-repair counterexamples; native events and sample counts are synthetic."""
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

from tests.benchmaker_support import CalibrationFixture
from tests.test_benchmaker_calibration import SCRIPTS
from grader import grade, make_record
from native import read_json, write_json, run_process
from probe import probe
from records import EvidenceError, summarize


class SecondRepairTests(CalibrationFixture, unittest.TestCase):
    def test_fd_spoof_and_reflection_are_unsupported_while_real_calls_complete(self):
        source = self.root / 'candidate.py'
        write_json(self.checks, {'checks': [{'args': [3], 'expected': 7}]})
        payload = json.dumps({'returned': True, 'value': 7, 'exception': None, 'args_after': [3]})
        for code in ['import os\nos.write(1, ' + repr(payload.encode()) + ')\nos._exit(0)',
                     'import sys\ndef solve(x): return sys._getframe()',
                     'def solve(x): return ().__class__.__bases__',
                     'def solve(x): return getattr(x, "__class__")']:
            source.write_text(code, encoding='utf-8')
            observation = grade(source, self.checks)
            self.assertEqual(observation['oracle_outcome'], 'UNVERIFIED')
            self.assertEqual(observation['failure_class'], 'unsupported_source_capabilities')
            self.assertEqual(observation['calls'], [])
        source.write_text('print(' + repr(payload) + ')', encoding='utf-8')
        self.assertEqual(grade(source, self.checks)['oracle_outcome'], 'FAIL')
        source.write_text('from __future__ import annotations\nfrom typing import List\nimport heapq\ndef solve(x: int):\n a=[x+1,x]\n heapq.heapify(a)\n return heapq.heappop(a)+heapq.heappop(a)', encoding='utf-8')
        self.assertEqual(grade(source, self.checks)['oracle_outcome'], 'PASS')
        source.write_text('def solve(x):\n while True: pass', encoding='utf-8')
        observation = grade(source, self.checks, timeout=0.2)
        self.assertEqual(observation['oracle_outcome'], 'FAIL')
        self.assertTrue(observation['timed_out'])

    def test_required_child_survives_every_unavailable_or_optional_ancestor(self):
        record = self.attempt()
        config = dict(self.config, scaffold={'instructions': ['pinned']}, seed={'unavailable_reason': 'not exposed'})
        for resolved_scaffold in ({'unavailable_reason': 'parent unavailable'}, {}, None):
            for default_required in (False, True):
                with self.subTest(scaffold=resolved_scaffold, default=default_required):
                    resolved = dict(config)
                    if resolved_scaffold is None:
                        del resolved['scaffold']
                    else:
                        resolved['scaffold'] = resolved_scaffold
                    row = dict(record, target_configuration=config, requested_configuration=config, resolved_configuration=resolved)
                    policy = dict(self.policy, target_configuration=config, band=[1, 1],
                        require_resolved_configuration=default_required, required_configuration_fields=['scaffold.instructions'],
                        optional_configuration_fields=['scaffold', 'seed'])
                    summary = summarize([row], policy)
                    self.assertEqual(summary['decision'], 'UNVERIFIED')
                    self.assertTrue(any('scaffold.instructions' in gap for gap in summary['criterion_gaps']))
                    self.assertTrue(any('seed' in gap for gap in summary['optional_gaps']))
                    observed = summarize([dict(row, resolved_configuration=config)], policy)
                    self.assertEqual(observed['decision'], 'CALIBRATED')

    def test_substitute_checks_and_wrong_case_inputs_are_rejected_semantically(self):
        from tests.test_benchmaker_repair import RepairTests
        envelope, _ = RepairTests.final_envelope(self)
        self.assertEqual(probe(self.root)['decision'], 'CALIBRATED')
        record = read_json(envelope['rounds'][1]['attempts'][0])
        alternative = self.root / 'alternate.json'
        write_json(alternative, {'checks': [{'args': [2], 'expected': 2}, {'args': [-1], 'expected': -1}]})
        self.assertEqual(grade(record['result_artifact_locator'], alternative)['oracle_outcome'], 'PASS')
        self.assertEqual(grade(record['result_artifact_locator'], self.checks)['oracle_outcome'], 'FAIL')
        identity = {key: record[key] for key in ('case_id', 'split', 'round', 'trial', 'target_configuration', 'benchmark_revision', 'candidate_kind')}
        with self.assertRaisesRegex(EvidenceError, 'evaluator checks differs from committed'):
            make_record(record['launch_receipt_locator'], alternative, identity)
        with self.assertRaisesRegex(EvidenceError, 'attempt differs from bound split'):
            make_record(record['launch_receipt_locator'], self.checks, dict(identity, split='development'))
        self.prompt.write_text('substitute prompt', encoding='utf-8')
        with self.assertRaisesRegex(EvidenceError, 'native prompt differs from committed'):
            self.attempt(name='changed-input')

    def test_finalization_call_is_after_all_terminal_branches(self):
        text = (SCRIPTS.parent / 'workflows' / 'benchmark-calibrate' / 'SKILL.md').read_text(encoding='utf-8')
        section = text.split('## Finalize', 1)[1]
        call = re.findall(r'tickets.py do .*--workspace <workspace> --goal-file <finalize-records>', section)
        self.assertEqual(len(call), 1)
        self.assertLess(section.index('<finalize-records>'), section.index('Return:'))
        changed = section.replace('--goal-file <finalize-records>', '--goal-file <attempts>')
        self.assertFalse(re.findall(r'tickets.py do .*--goal-file <finalize-records>', changed))


class PublicationSequenceTests(unittest.TestCase):
    def test_published_rounds_survive_landed_partial_and_final_indexes(self):
        result = subprocess.run([sys.executable, '-m', 'tests.benchmaker_publication_probe'],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True,
                                text=True, timeout=240)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
