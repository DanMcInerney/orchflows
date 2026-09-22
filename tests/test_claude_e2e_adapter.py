"""Offline Claude adapter result tests; no native model calls. Fixtures contain no user data."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from common import read_json, write_json
from hosts.claude import Claude

SESSION = 'session-1'


def lines(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')


class ClaudeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='orchflows-claude-offline-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / 'stage'
        self.host = Claude.__new__(Claude)
        self.host.executable, self.host.home = 'claude-native', self.root / 'native-home'
        self.host.settings = {'disableAllHooks': True}

    def stream(self, *records):
        lines(self.stage / 'events.jsonl', records)

    def transcript(self, *efforts, model='claude-opus-5-5'):
        lines(self.host.home / 'projects/project' / (SESSION + '.jsonl'),
              [{'type': 'assistant', **({'effort': e} if e else {}), 'message': {'model': model, 'content': []}}
               for e in efforts])

    def launch(self, requested):
        write_json(self.stage / 'claude-launch.json', {'profile': 'local', 'requested_effort': requested})

    def result(self):
        return self.host.result(self.stage)

    def test_success_records_init_model_and_transcript_tallies(self):
        self.transcript('high', 'high', model='claude-opus-5-5')
        self.stream({'type': 'system', 'subtype': 'init', 'session_id': SESSION, 'model': 'claude-opus-5-5[1m]'},
                    {'type': 'result', 'result': 'done'})
        result = self.result()
        self.assertEqual(result['gaps'], [])
        self.assertTrue(result['terminal_success'])
        self.assertEqual(result['model'], 'claude-opus-5-5[1m]')
        self.assertEqual(result['observed'], {'models': {'claude-opus-5-5': 2}, 'efforts': {'high': 2}})

    def test_missing_init_is_error_and_missing_terminal_are_gaps(self):
        self.stream({'type': 'result', 'is_error': True, 'result': 'failed'})
        result = self.result()
        self.assertFalse(result['terminal_success'])
        self.assertEqual(result['observed'], {})
        self.assertEqual(result['gaps'], ['Missing native initialization record',
                                          'Missing successful native terminal record'])
        self.stream({'type': 'system', 'subtype': 'init', 'session_id': SESSION})
        self.transcript('high')
        result = self.result()
        self.assertFalse(result['terminal_success'])
        self.assertEqual(result['gaps'], ['Missing successful native terminal record'])
        (self.stage / 'events.jsonl').unlink()
        self.assertIn('No native event stream', self.result()['gaps'])

    def test_unreadable_transcript_is_a_gap_not_a_tally(self):
        self.stream({'type': 'system', 'subtype': 'init', 'session_id': SESSION}, {'type': 'result'})
        result = self.result()
        self.assertEqual(result['observed'], {})
        self.assertTrue(any(g.startswith('Native transcript unavailable') for g in result['gaps']))

    def test_effort_mismatch_uses_the_applicable_request(self):
        self.stream({'type': 'system', 'subtype': 'init', 'session_id': SESSION}, {'type': 'result'})
        self.transcript('high', None)
        cases = [({'effortLevel': 'xhigh'}, 'requested xhigh'),
                 ({'effortLevel': 'high'}, None),
                 ({'effortLevel': 'high', 'CLAUDE_CODE_EFFORT_LEVEL': 'max'}, 'requested max'),
                 ({'effortLevel': 'xhigh', 'modelSettings': {'any': 'shape'}}, None),
                 ({}, None)]
        for requested, expected in cases:
            with self.subTest(requested=requested):
                self.launch(requested)
                result = self.result()
                self.assertEqual(result['requested_effort'], requested)
                mismatches = [g for g in result['gaps'] if 'effort mismatch' in g]
                self.assertEqual(bool(mismatches), expected is not None)
                if expected:
                    self.assertIn(expected, mismatches[0])
                    self.assertIn("['high']", mismatches[0])

    def test_command_records_requested_effort_without_changing_settings(self):
        self.host.settings = {'disableAllHooks': True, 'effortLevel': 'xhigh'}
        self.host.model_settings = {'opus': {'effort': 'high'}}
        with patch.dict(os.environ, {'CLAUDE_CODE_EFFORT_LEVEL': 'max'}):
            command = self.host.command({}, 'local', directory=self.stage)
        self.assertEqual(json.loads(command[command.index('--settings') + 1]),
                         {'disableAllHooks': True, 'effortLevel': 'xhigh'})
        self.assertNotIn('--effort', command)
        self.assertEqual(read_json(self.stage / 'claude-launch.json')['requested_effort'],
                         {'effortLevel': 'xhigh', 'modelSettings': {'opus': {'effort': 'high'}},
                          'CLAUDE_CODE_EFFORT_LEVEL': 'max'})


if __name__ == '__main__':
    unittest.main()
