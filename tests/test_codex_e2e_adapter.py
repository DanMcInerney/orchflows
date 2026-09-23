"""Offline Codex adapter contract tests; no native model calls."""
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from common import read_json, snapshot, write_json
from hosts.codex import Codex, launcher, toml


class CodexAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='orchflows-codex-offline-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / 'stage'
        self.workspace = self.stage / 'workspace'
        self.workspace.mkdir(parents=True)
        self.host = Codex.__new__(Codex)
        self.host.launcher = ['codex-native']
        self.host.home = self.root / 'native-home'
        self.host.settings = {'model': 'configured-model', 'model_reasoning_effort': 'high'}
        self.host.disabled_skills = [{'path': '/ambient/SKILL.md', 'enabled': False}]
        self.source = self.root / 'source'
        write_json(self.source / 'plugin.json', {'name': 'sample', 'version': '1.0.0'})
        skill = self.source / 'skills/do-work/SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_text('---\nname: do-work\ndescription: Test\n---\nRead ../../guidance/code.md.\n')
        guide = self.source / 'guidance/code.md'
        guide.parent.mkdir()
        guide.write_text('Preserve observable behavior.')
        self.packages = {'sample': self.source}

    def discovered(self):
        skill = self.workspace / '.agents/skills/sample/skills/do-work/SKILL.md'
        return {'data': [{'skills': [{'name': 'sample:do-work', 'enabled': True, 'path': str(skill)}], 'errors': []}]}

    def options(self, command):
        values = [command[i + 1] for i, token in enumerate(command) if token == '-c']
        return tomllib.loads('\n'.join(values))

    def test_runtime_package_is_complete_and_snapshotted_before_launch(self):
        before = snapshot(self.source)
        self.host.prepare(self.workspace, self.packages)
        loaded = self.workspace / '.agents/skills/sample'
        self.assertEqual(snapshot(loaded), before)
        self.assertEqual((loaded / 'skills/do-work/../../guidance/code.md').read_text(),
                         'Preserve observable behavior.')
        self.assertTrue(all(not p.is_symlink() for p in loaded.rglob('*')))
        with patch('hosts.codex.inventory', return_value=self.discovered()):
            command = self.host.command(self.packages, directory=self.stage)
        self.assertEqual(snapshot(self.source), before)
        self.assertIn('--ignore-user-config', command)
        self.assertEqual(command[-1], '-')
        metadata = read_json(self.stage / 'codex-launch.json')
        self.assertEqual(self.host.registration_gaps({'registration': metadata}, self.packages), [])
        (loaded / 'guidance/code.md').write_text('Changed by a worker')
        self.assertEqual(self.host.registration_gaps({'registration': metadata}, self.packages),
                         ['sample (runtime package changed)'])

    def test_missing_native_discovery_is_not_fake_registration(self):
        self.host.prepare(self.workspace, self.packages)
        with patch('hosts.codex.inventory', side_effect=ValueError('unavailable')):
            self.host.command(self.packages, directory=self.stage)
        native = {'registration': read_json(self.stage / 'codex-launch.json')}
        self.assertEqual(self.host.registration_gaps(native, self.packages), ['sample'])
        self.assertIn('unavailable', native['registration']['gaps'][0])

    def test_prepare_is_required_and_never_overwrites_existing_packages(self):
        with self.assertRaisesRegex(ValueError, 'prepare'):
            self.host.command(self.packages, directory=self.stage)
        self.host.prepare(self.workspace, self.packages)
        with self.assertRaises(FileExistsError):
            self.host.prepare(self.workspace, self.packages)

    def test_audit_requests_enforced_readonly_and_no_native_delegation(self):
        command = self.host.command({}, 'audit', {'type': 'object'}, self.root, self.stage)
        self.assertEqual(command[command.index('--sandbox') + 1], 'read-only')
        options = self.options(command)
        self.assertEqual(options['approval_policy'], 'never')
        self.assertFalse(options['features']['multi_agent'])
        self.assertFalse(options['features']['hooks'])
        self.assertFalse(options['features']['plugins'])
        self.assertFalse(options['features']['apps'])
        self.assertEqual(options['mcp_servers'], {})
        self.assertEqual(options['model'], 'configured-model')
        self.assertEqual(options['model_reasoning_effort'], 'high')
        self.assertNotIn('--add-dir', command)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', command)
        self.assertTrue((self.stage / 'output-schema.json').is_file())

    def test_no_review_removes_native_delegation_and_shell(self):
        options = self.options(self.host.command({}, 'no-review', directory=self.stage))
        self.assertFalse(options['features']['multi_agent'])
        self.assertFalse(options['features']['shell_tool'])
        self.assertEqual(self.host.invocation('sample:do-work', 'Request'), '$sample:do-work\n\nRequest')

    def result(self, records, context=None, structured=False):
        (self.stage / 'events.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in records))
        raw = self.root / 'native.jsonl'
        raw.write_text(json.dumps({'type': 'turn_context', 'payload': context or {
            'model': 'configured-model', 'effort': 'high', 'sandbox_policy': {'type': 'workspace-write'}}}) + '\n')
        if structured:
            write_json(self.stage / 'output-schema.json', {'type': 'object'})
        with patch('hosts.codex.native_logs._locate', return_value=({'native-thread': {'path': str(raw)}}, [])):
            return self.host.result(self.stage)

    def test_result_uses_exact_native_id_final_metadata_and_usage(self):
        answer = {'assessment': 'acceptable'}
        native = self.result([
            {'type': 'thread.started', 'thread_id': 'native-thread'},
            {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': json.dumps(answer)}},
            {'type': 'turn.completed', 'usage': {'input_tokens': 100, 'output_tokens': 20}}
        ], structured=True)
        self.assertEqual(native['session_id'], 'native-thread')
        self.assertEqual(native['structured_output'], answer)
        self.assertEqual(native['usage']['output_tokens'], 20)
        self.assertEqual(native['model'], 'configured-model')
        self.assertEqual(native['effort'], 'high')
        self.assertEqual(native['gaps'], [])
        self.assertIsNone(native['cost_usd'])

    def test_failed_or_partial_native_turn_is_not_success(self):
        native = self.result([
            {'type': 'thread.started', 'thread_id': 'native-thread'},
            {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'partial'}},
            {'type': 'turn.failed', 'error': {'message': 'failed'}}
        ])
        self.assertFalse(native['terminal_success'])
        self.assertEqual(native['final'], 'partial')
        self.assertIsNone(native['usage'])
        self.assertTrue(native['gaps'])

    def test_audit_rejects_native_metadata_without_readonly(self):
        write_json(self.stage / 'codex-launch.json', {'profile': 'audit'})
        native = self.result([{'type': 'thread.started', 'thread_id': 'native-thread'},
                              {'type': 'turn.completed'}])
        self.assertIn('Read-only audit sandbox not established', ' '.join(native['gaps']))

    def test_launch_records_the_windows_sandbox_mode(self):
        self.host.settings = {**self.host.settings, 'windows': {'sandbox': 'elevated'}}
        command = self.host.command({}, 'local', directory=self.stage)
        self.assertEqual(self.options(command)['windows'], {'sandbox': 'elevated'})
        self.assertEqual(read_json(self.stage / 'codex-launch.json')['windows_sandbox'], 'elevated')
        native = self.result([{'type': 'thread.started', 'thread_id': 'native-thread'}, {'type': 'turn.completed'}])
        self.assertIn('Requested windows.sandbox: elevated.', native['conditions'])
        self.assertEqual(native['gaps'], [])

    def test_every_invocation_requests_the_unelevated_windows_sandbox(self):
        home = self.root / 'codex-home'
        home.mkdir()
        (home / 'config.toml').write_text('[windows]\nsandbox = "elevated"\nother = 1\n')
        with patch('hosts.codex.launcher', return_value=['codex-native']), \
                patch('hosts.codex.subprocess.check_output', return_value='codex 1.0'), \
                patch('hosts.codex.native_logs.native_home', return_value=home):
            host = Codex()
        for profile in ('local', 'audit'):
            with self.subTest(profile=profile):
                stage = self.root / profile
                command = host.command({}, profile, {'type': 'object'} if profile == 'audit' else None, self.root, stage)
                self.assertEqual(self.options(command)['windows'], {'sandbox': 'unelevated', 'other': 1})
                self.assertEqual(read_json(stage / 'codex-launch.json')['windows_sandbox'], 'unelevated')
        self.assertEqual(tomllib.loads((home / 'config.toml').read_text())['windows']['sandbox'], 'elevated')

    def test_toml_nested_values_preserve_literal_paths_and_quotes(self):
        value = {'path': 'C:\\space dir\\a"b', 'enabled': False, 'nested': [1, {'a': 'b'}]}
        self.assertEqual(tomllib.loads('value=' + toml(value))['value'], value)

    def test_npm_launcher_avoids_shell_requoting(self):
        shim = self.root / 'codex.ps1'
        script = self.root / 'node_modules/@openai/codex/bin/codex.js'
        script.parent.mkdir(parents=True)
        script.write_text('')
        with patch('hosts.codex.shutil.which', side_effect=[str(shim), 'node-native']):
            self.assertEqual(launcher(str(shim)), ['node-native', str(script)])


if __name__ == '__main__':
    unittest.main()
