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

    def test_enabled_auto_memory_is_a_gap(self):
        self.transcript('high')
        memory = {'auto': 'C:\\Users\\someone\\.claude\\projects\\repo\\memory\\'}
        for paths, gap in (({}, False), (memory, True)):
            with self.subTest(paths=paths):
                self.stream({'type': 'system', 'subtype': 'init', 'session_id': SESSION, **({'memory_paths': paths} if paths else {})},
                            {'type': 'result', 'result': 'done'})
                gaps = self.result()['gaps']
                self.assertEqual(gaps, ['Native auto-memory enabled: ' + json.dumps(memory)] if gap else [])

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

    def test_print_mode_waits_for_background_subagents(self):
        """Print mode otherwise ends background subagents 600 s after the main turn (observed 2.1.280)."""
        self.assertEqual(Claude.environment, {'CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS': '0'})

    def test_default_command_line_per_profile(self):
        """The whole launch line: a change here changes every Claude trial."""
        import hosts
        self.enterContext(patch.dict(os.environ))
        os.environ.pop('CLAUDE_CODE_EFFORT_LEVEL', None)
        home = self.root / 'user-home'
        write_json(home / 'settings.json', {'enabledPlugins': {'orchflows@local': True, 'other@market': True},
                                            'model': 'opus', 'effortLevel': 'xhigh', 'hooks': {'Stop': []},
                                            'modelSettings': {'opus': {'effort': 'high'}}})
        with patch('hosts.claude.shutil.which', return_value='claude-native'), \
                patch('hosts.claude.subprocess.check_output', return_value='2.1.280 (Claude Code)\n'), \
                patch('hosts.claude.native_logs.native_home', return_value=home):
            host = hosts.get_host('claude')
        self.assertEqual((host.version, host.model, host.effort), ('2.1.280 (Claude Code)', 'claude-sonnet-5', 'high'))
        settings = {'disableAllHooks': True, 'syncClaudeAiSkills': False, 'syncClaudeAiPlugins': False,
                    'autoMemoryEnabled': False, 'enabledPlugins': {'orchflows@local': False, 'other@market': False},
                    'model': 'opus', 'effortLevel': 'xhigh'}
        packages = {'orchflows': self.root / 'packages/orchflows', 'shared': self.root / 'packages/shared'}
        schema = {'type': 'object'}
        tools = {'local': 'Read,Write,Edit,Bash,Agent,Skill,Glob,Grep', 'authoring': 'Read,Write,Edit,Bash,Agent,Skill,Glob,Grep',
                 'no-review': 'Read,Write,Edit,Skill,Glob,Grep', 'audit': 'Read,Glob,Grep'}
        for profile, toolset in tools.items():
            with self.subTest(profile=profile):
                audit = profile == 'audit'
                command = host.command({} if audit else packages, profile, schema if audit else None,
                                       self.root if audit else None, directory=self.stage / profile)
                session = command[command.index('--session-id') + 1]
                self.assertEqual(json.loads(command[command.index('--settings') + 1]), settings)
                expected = ['claude-native', '-p', '--verbose', '--output-format', 'stream-json',
                            '--forward-subagent-text', '--session-id', session, '--permission-mode', 'dontAsk',
                            '--tools', toolset, '--allowedTools', toolset, '--strict-mcp-config',
                            '--setting-sources', 'user', '--settings', json.dumps(settings),
                            '--model', 'claude-sonnet-5', '--effort', 'high']
                if audit:
                    expected += ['--restricted', '--add-dir', str(self.root), '--json-schema', json.dumps(schema)]
                else:
                    expected += ['--plugin-dir', str(packages['orchflows']), '--plugin-dir', str(packages['shared'])]
                self.assertEqual(command, expected)
                self.assertEqual(read_json(self.stage / profile / 'claude-launch.json'),
                                 {'profile': profile, 'requested_effort': {'effortLevel': 'xhigh', '--effort': 'high',
                                                                           'modelSettings': {'opus': {'effort': 'high'}}}})

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
