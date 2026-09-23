"""Offline controls for compatibility, exact edits and isolated policy preparation."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from common import load_hook, snapshot
from catalog import discover
import next_stage

CASES = ROOT / 'tests/e2e/cases/next-stage'


class Context:
    def __init__(self, root):
        self.root, self.results = root, []

    def stage(self):
        return self.root

    def require(self, condition, requirement, evidence):
        self.results.append(bool(condition))


class NextStageControls(unittest.TestCase):
    def test_exact_edit_rejects_unrequested_changes(self):
        hook = load_hook(CASES / 'tiny-edit/check.py')
        source = b'Please bring your tickte to the workshop.\r\nDoors open at 09:45.\r\n'
        with tempfile.TemporaryDirectory(prefix='next-stage-edit-') as raw:
            root = Path(raw)
            (root / 'notice.txt').write_bytes(source)
            for output, expected in [(source.replace(b'tickte', b'ticket'), True),
                                     (source, False), (source.replace(b'\r\n', b'\n'), False),
                                     (source.replace(b'tickte', b'ticket').replace(b'09:45', b'10:00'), False)]:
                (root / 'corrected.txt').write_bytes(output)
                context = Context(root)
                hook.check(context)
                self.assertEqual(all(context.results), expected)

    def test_compatibility_checks_both_clients_and_preservation(self):
        hook = load_hook(CASES / 'api-migration/check.py')
        valid_api = "def get_profile(user):\n    return {'id': user['id'], 'name': user['name'], 'display_name': user['name']}\n"
        valid_client = "def label(profile):\n    return 'Hello, ' + profile['display_name']\n"
        with tempfile.TemporaryDirectory(prefix='next-stage-api-') as raw:
            root = Path(raw)
            (root / 'reference').mkdir()
            (root / 'reference/legacy_client.py').write_bytes((CASES / 'api-migration/fixtures/reference/legacy_client.py').read_bytes())
            (root / 'compatibility.md').write_text('Both generations remain supported.', encoding='utf-8')
            for api, client, expected in [
                (valid_api, valid_client, True),
                (valid_api.replace("'name': user['name'], ", ''), valid_client, False),
                (valid_api, valid_client.replace("['display_name']", "['name']"), False),
                (valid_api.replace("user['name']}", "user['name'].strip()}"), valid_client, False),
                (valid_api.replace('    return', "    user.pop('ignored', None)\n    return"), valid_client, False),
            ]:
                (root / 'api.py').write_text(api, encoding='utf-8')
                (root / 'client.py').write_text(client, encoding='utf-8')
                context = Context(root)
                with patch.object(sys, 'dont_write_bytecode', True):
                    hook.check(context)
                self.assertEqual(all(context.results), expected)

    def test_variant_changes_only_dynamic_and_never_source(self):
        relative = 'skills/orch-dynamic-workflow/SKILL.md'
        original = (ROOT / relative).read_bytes()
        case = discover()['core/next-stage/tiny-edit']
        with tempfile.TemporaryDirectory(prefix='next-stage-policy-') as raw:
            parent = Path(raw)
            _, current = next_stage.prepare(parent / 'current', 'current', [case])
            output, variant = next_stage.prepare(parent / 'variant', 'review-every-unit', [case])
            first, second = snapshot(current), snapshot(variant)
            changed = [name for name in first if first[name] != second.get(name)]
            self.assertEqual(changed, [relative])
            self.assertEqual(set(first), set(second))
            self.assertIn('Say why you skipped a gate', (current / relative).read_text(encoding='utf-8'))
            self.assertNotIn('Say why you skipped a gate', (variant / relative).read_text(encoding='utf-8'))
            self.assertIn('At each gate', (variant / relative).read_text(encoding='utf-8'))
            metadata = json.loads((output / 'preparation.json').read_text(encoding='utf-8'))
            self.assertEqual(metadata['native_executions_at_preparation'], 0)
            self.assertEqual(metadata['record_type'], 'immutable_preparation_receipt')
            frozen = output / metadata['cases'][0]['frozen_path']
            self.assertEqual(snapshot(frozen), snapshot(case.path))
            self.assertFalse((output / 'execution').exists())
        self.assertEqual((ROOT / relative).read_bytes(), original)

    def test_api_execution_without_key_stops_before_preparation_or_launch(self):
        with tempfile.TemporaryDirectory(prefix='next-stage-auth-') as raw:
            output = Path(raw) / 'never-created'
            args = ['next_stage.py', '--case', 'core/next-stage/tiny-edit', '--output', str(output), '--execute']
            with patch.object(sys, 'argv', args), patch.dict(os.environ, {'CODEX_API_KEY': '', 'OPENAI_API_KEY': ''}), \
                    patch('next_stage.execute') as execute, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as stopped:
                    next_stage.main()
                self.assertEqual(stopped.exception.code, 2)
                execute.assert_not_called()
            self.assertFalse(output.exists())

    def test_api_launcher_uses_frozen_cases_and_core_without_recording_key(self):
        with tempfile.TemporaryDirectory(prefix='next-stage-launch-') as raw:
            output = Path(raw) / 'prepared'
            args = ['next_stage.py', '--case', 'core/next-stage/tiny-edit', '--output', str(output), '--execute']
            calls = []

            async def execute(launch, selected, sources):
                calls.append((launch, selected, sources))
                self.assertEqual(os.environ['CODEX_API_KEY'], 'offline-key-sentinel')
                return 0

            with patch.object(sys, 'argv', args), patch.dict(os.environ, {
                    'CODEX_API_KEY': '', 'OPENAI_API_KEY': 'offline-key-sentinel'}), \
                    patch('next_stage.execute', side_effect=execute):
                self.assertEqual(next_stage.main(), 0)
            launch, selected, sources = calls[0]
            self.assertEqual(launch.host, 'codex')
            self.assertEqual(launch.output, output / 'execution')
            self.assertEqual(selected[0].path, output / 'cases/core/next-stage/tiny-edit')
            self.assertEqual(sources[selected[0].id], {'orchflows': output / 'core'})
            self.assertNotIn('offline-key-sentinel', (output / 'preparation.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
