"""Authoring network opt-in must not alter other native launch profiles."""
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests/e2e'))
from catalog import discover
from common import read_json, write_json
from hosts.claude import Claude
from hosts.codex import Codex


class HostProfileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='orchflows-profiles-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_catalog_accepts_explicit_authoring_and_rejects_audit_as_target(self):
        case = self.root / 'authoring-case'
        write_json(case / 'case.json', {'packages': ['orchflows'], 'profile': 'authoring'})
        (case / 'request.md').write_text('Author a reusable workflow with local fake effects.')
        (case / 'expected-behavior.md').write_text('Complete the authoring and trial requirements.')
        selected = discover([self.root])[self.root.name + '/authoring-case']
        self.assertEqual(selected.config['profile'], 'authoring')
        write_json(case / 'case.json', {'packages': ['orchflows'], 'profile': 'audit'})
        with self.assertRaisesRegex(ValueError, 'unsupported profile'):
            discover([self.root])

    def test_codex_authoring_changes_network_only_and_does_not_leak(self):
        host = Codex.__new__(Codex)
        host.launcher, host.settings, host.disabled_skills = ['codex-native'], {}, []
        baseline = None
        for profile in ('local', 'authoring', 'audit', 'no-review', 'local'):
            with self.subTest(profile=profile):
                stage = self.root / (profile + ('-after' if profile == 'local' and baseline else ''))
                stage.mkdir()
                command = host.command({}, profile, allowed_root=self.root, directory=stage)
                values = [command[i + 1] for i, token in enumerate(command) if token == '-c']
                settings = tomllib.loads('\n'.join(values))
                self.assertEqual(settings['sandbox_workspace_write']['network_access'], profile == 'authoring')
                self.assertEqual(settings['features']['multi_agent'], profile in {'local', 'authoring'})
                self.assertEqual(settings['agents']['enabled'], profile in {'local', 'authoring'})
                self.assertEqual(settings['features']['shell_tool'], profile != 'no-review')
                self.assertEqual(settings['web_search'], 'disabled')
                self.assertEqual(settings['mcp_servers'], {})
                self.assertEqual(command[command.index('--sandbox') + 1], 'read-only' if profile == 'audit' else 'workspace-write')
                self.assertNotIn('--add-dir', command)
                self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', command)
                metadata = read_json(stage / 'codex-launch.json')
                self.assertEqual(metadata['workspace_shell_network_access'], profile == 'authoring')
                if profile == 'local':
                    if baseline is None:
                        baseline = settings
                    else:
                        self.assertEqual(settings, baseline)
                elif profile == 'authoring':
                    settings['sandbox_workspace_write']['network_access'] = False
                    self.assertEqual(settings, baseline)

    def test_claude_authoring_keeps_local_tools_and_audit_remains_restricted(self):
        host = Claude.__new__(Claude)
        host.executable, host.settings = 'claude-native', {'disableAllHooks': True}
        toolsets = {}
        for profile in ('authoring', 'audit', 'no-review', 'local'):
            command = host.command({}, profile, allowed_root=self.root, directory=self.root / profile)
            toolsets[profile] = set(command[command.index('--tools') + 1].split(','))
            self.assertEqual(toolsets[profile], set(command[command.index('--allowedTools') + 1].split(',')))
            self.assertEqual(json.loads(command[command.index('--settings') + 1]), {'disableAllHooks': True})
            self.assertEqual(read_json(self.root / profile / 'claude-launch.json')['profile'], profile)
            self.assertEqual('--restricted' in command, profile == 'audit')
        self.assertEqual(toolsets['authoring'], toolsets['local'])
        self.assertEqual(toolsets['audit'], {'Read', 'Glob', 'Grep'})
        self.assertFalse({'Agent', 'Bash'} & toolsets['no-review'])

    def test_requested_model_and_effort_replace_user_configuration(self):
        home = self.root / 'codex-home'
        home.mkdir()
        (home / 'config.toml').write_text('model = "expensive"\nmodel_reasoning_effort = "xhigh"\n')
        with mock.patch('hosts.codex.launcher', return_value=['codex-native']), \
                mock.patch('hosts.codex.subprocess.check_output', return_value='codex 1.0'), \
                mock.patch('hosts.codex.native_logs.native_home', return_value=home):
            codex = Codex(None, 'cheap', 'low')
        values = [v for i, v in enumerate(codex.options('local')) if i % 2]
        settings = tomllib.loads('\n'.join(values))
        self.assertEqual((settings['model'], settings['model_reasoning_effort']), ('cheap', 'low'))
        claude = Claude.__new__(Claude)
        claude.executable, claude.settings = 'claude-native', {'model': 'expensive'}
        claude.model, claude.effort = 'haiku', 'low'
        command = claude.command({}, 'local', directory=self.root / 'claude-override')
        self.assertEqual(command[command.index('--model') + 1], 'haiku')
        self.assertEqual(command[command.index('--effort') + 1], 'low')
        self.assertEqual(read_json(self.root / 'claude-override' / 'claude-launch.json')['requested_effort']['--effort'], 'low')

    def test_trials_default_to_cheap_models(self):
        import hosts
        with mock.patch('hosts.codex.Codex', side_effect=lambda *a: a), mock.patch('hosts.claude.Claude', side_effect=lambda *a: a):
            self.assertEqual(hosts.get_host('codex'), (None, 'gpt-5.6-luna', 'xhigh'))
            self.assertEqual(hosts.get_host('claude'), (None, 'claude-sonnet-5', 'high'))
            self.assertEqual(hosts.get_host('codex', None, 'gpt-5.5'), (None, 'gpt-5.5', None))
            self.assertEqual(hosts.get_host('codex', None, None, 'medium'), (None, 'gpt-5.6-luna', 'medium'))


if __name__ == '__main__':
    unittest.main()
