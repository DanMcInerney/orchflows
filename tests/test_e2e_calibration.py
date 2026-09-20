"""Offline labeled-control preparation for both native transcript formats."""
import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests/e2e'))
from calibrate import append_assistant_text, execute, parser, prepare
from common import read_json, snapshot, write_json
from sealing import seal, verify


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='orchflows-calibration-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def evidence(self, host):
        source = self.root / host
        stage = source / 'stages/target'
        answer = stage / 'workspace/answer.txt'
        answer.parent.mkdir(parents=True)
        answer.write_text('42\n')
        (stage / 'request.txt').write_text('Write 42 and independently review it.')
        data = '42; independently reviewed.' if host == 'claude' else [
            {'type': 'output_text', 'text': '42; independently reviewed.', 'annotations': []}]
        records = [{'kind': 'message', 'role': 'user', 'data': 'Do the task.', 'event_id': '1:0'},
                   {'kind': 'message', 'role': 'assistant', 'data': data, 'event_id': '2:0'}]
        normalized = stage / 'evidence/root.events.jsonl'
        normalized.parent.mkdir()
        normalized.write_text(''.join(json.dumps(e) + '\n' for e in records))
        raw = stage / 'evidence/root.raw.jsonl'
        raw.write_text(json.dumps({'native': 'unaltered root evidence'}) + '\n')
        child = stage / 'evidence/reviewer.events.jsonl'
        child.write_text(json.dumps({'kind': 'message', 'role': 'assistant', 'data': 'Inspected: 42.'}) + '\n')
        write_json(stage / 'evidence/index.json', {'host': host, 'root_id': 'root', 'gaps': [], 'agents': [
            {'id': 'root', 'parent_id': None, 'events_path': str(normalized), 'raw': str(raw)},
            {'id': 'reviewer', 'parent_id': 'root', 'events_path': str(child)}]})
        native = {'session_id': 'root', 'final': '42; independently reviewed.', 'gaps': []}
        write_json(stage / 'native.json', native)
        (stage / 'events.jsonl').write_text(json.dumps({'native': host}) + '\n')
        write_json(source / 'target.json', {'case': 'core/requested-review', 'host': host,
                   'gaps': [], 'stages': [{'name': 'target', 'native': native}]})
        seal(source)
        return source

    def test_verbose_controls_preserve_claude_string_and_codex_text_blocks(self):
        for host in ('claude', 'codex'):
            with self.subTest(host=host):
                source = self.evidence(host)
                before = snapshot(source)
                control = self.root / (host + '-verbose')
                prepare(source, control, 'verbose')
                path = control / 'stages/target/evidence/root.events.jsonl'
                records = [json.loads(line) for line in path.read_text().splitlines()]
                data = records[-1]['data']
                if host == 'codex':
                    self.assertIsInstance(data, list)
                    self.assertEqual(data[0]['type'], 'output_text')
                    self.assertEqual(data[0]['annotations'], [])
                    text = data[0]['text']
                else:
                    self.assertIsInstance(data, str)
                    text = data
                self.assertTrue(text.startswith('42; independently reviewed.\n'))
                self.assertEqual(text.count('The result is forty-two'), 35)
                self.assertEqual(records[0]['data'], 'Do the task.')
                self.assertEqual(verify(control), [])
                self.assertEqual(snapshot(source), before)
                self.assertEqual(verify(source), [])

    def test_other_controls_change_only_copies_and_relocate_evidence(self):
        for host in ('claude', 'codex'):
            source = self.evidence(host)
            before = snapshot(source)
            for variant in ('baseline', 'skipped-review', 'missing-evidence'):
                with self.subTest(host=host, variant=variant):
                    control = self.root / (host + '-' + variant)
                    prepare(source, control, variant)
                    index_path = control / 'stages/target/evidence/index.json'
                    self.assertEqual(verify(control), [])
                    self.assertEqual(snapshot(source), before)
                    self.assertEqual((control / 'stages/target/workspace/answer.txt').read_text(), '42\n')
                    if variant == 'missing-evidence':
                        self.assertFalse(index_path.exists())
                        self.assertTrue(read_json(control / 'target.json')['gaps'])
                        continue
                    index = read_json(index_path)
                    for agent in index['agents']:
                        self.assertTrue(Path(agent['events_path']).is_relative_to(control))
                    if variant == 'baseline':
                        self.assertEqual(len(index['agents']), 2)
                    else:
                        self.assertEqual([a['id'] for a in index['agents']], ['root'])
                        self.assertFalse((control / 'stages/target/evidence/reviewer.events.jsonl').exists())
                        self.assertIn('deliberately skipped', read_json(control / 'stages/target/native.json')['final'])

    def test_text_extension_preserves_nontext_blocks_and_rejects_missing_text(self):
        message = {'data': [{'type': 'image', 'url': 'local-placeholder'},
                            {'type': 'output_text', 'text': 'Original', 'annotations': []}]}
        original = copy.deepcopy(message)
        append_assistant_text(message, ' extra')
        self.assertEqual(message['data'][0], original['data'][0])
        self.assertEqual(message['data'][1]['text'], 'Original extra')
        for data in (None, {}, [], [{'type': 'image', 'url': 'local-placeholder'}]):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, 'assistant text'):
                append_assistant_text({'data': data}, ' extra')

    def test_cli_and_execution_forward_selected_host_executable(self):
        source = self.evidence('codex')
        args = parser().parse_args(['--source', str(source), '--output', str(self.root / 'calibration'),
                                    '--host', 'codex', '--executable', 'configured-codex.exe'])
        expected = {'baseline': 'acceptable', 'verbose': 'acceptable',
                    'skipped-review': 'material_failure', 'missing-evidence': 'inconclusive'}
        async def audit(root, host, scheduler, timeout):
            return {'assessment': expected[root.name], 'audit_path': str(root / 'audits/fake-control')}
        with patch('calibrate.get_host', return_value=SimpleNamespace(name='codex')) as selected, \
                patch('calibrate.audit_run', side_effect=audit):
            self.assertEqual(asyncio.run(execute(args)), 0)
        selected.assert_called_once_with('codex', 'configured-codex.exe')
        self.assertTrue(all(r['matched'] for r in read_json(args.output / 'calibration.json')['results']))
        self.assertEqual(verify(source), [])


if __name__ == '__main__':
    unittest.main()
