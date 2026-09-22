"""Recorded child launch context reaches stage violations, gaps, verdicts and the audit packet without a judge."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests/e2e'))
from catalog import Case
from common import read_json, write_json
from judging import aggregate, packet
from run import run_case
from scheduler import Scheduler
from trial import launch_checks

FORK_CALL = {'source': 'spawn_call', 'api': 'codex-v1', 'tool': 'exec', 'call_id': 'call-1', 'line': 36,
             'arguments': [{'fork_context': True}], 'indicates': 'inherited'}
AGENTS = [
    {'id': 'coordinator', 'parent_id': None, 'unlinked_spawns': [dict(FORK_CALL, line=80)]},
    {'id': 'reviewer', 'parent_id': 'coordinator', 'launch_context': 'inherited',
     'launch_evidence': [{'source': 'child_record', 'forked_from_id': 'coordinator', 'indicates': 'inherited'}, FORK_CALL]},
    {'id': 'maker', 'parent_id': 'coordinator', 'launch_context': 'fresh', 'launch_evidence': []},
    {'id': 'untraced', 'parent_id': 'coordinator', 'launch_context': 'unknown', 'launch_evidence': []},
]


class LaunchChecksTests(unittest.TestCase):
    def test_inherited_is_an_invariant_violation_and_unsettled_launches_are_gaps(self):
        violations, gaps = launch_checks('target', {'agents': AGENTS})
        self.assertEqual(len(violations), 1)
        self.assertTrue(violations[0]['invariant'])
        self.assertIn('agent reviewer (parent coordinator) launch_context inherited: exec line 36 [{"fork_context": true}]',
                      violations[0]['evidence'])
        self.assertEqual(len(gaps), 2)
        self.assertTrue(any('unrecorded' in g and 'agent untraced' in g for g in gaps), gaps)
        self.assertTrue(any('no recorded child' in g and 'agent coordinator line 80' in g for g in gaps), gaps)
        self.assertEqual(launch_checks('target', {'gaps': ['Native evidence unavailable']}), ([], []))
        verdict = aggregate({'completed': False, 'gaps': gaps}, {'checks': violations}, {})
        self.assertEqual(verdict['assessment'], 'material_failure')


class FakeHost:
    """Local harness control: writes a synthetic native index and establishes no native/LLM behavior."""
    name, version, capabilities = 'fake', 'test', set()

    def invocation(self, entrypoint, request):
        return request

    def registration_gaps(self, native, packages):
        return []

    def command(self, packages, profile='local', schema=None, allowed_root=None, directory=None):
        return [sys.executable, '-c', 'print("control")']

    def result(self, directory):
        evidence = Path(directory) / 'evidence'
        agents = []
        for agent in AGENTS[:3]:
            events = evidence / (agent['id'] + '.events.jsonl')
            events.parent.mkdir(parents=True, exist_ok=True)
            events.write_text('', encoding='utf-8')
            agents.append({**agent, 'unlinked_spawns': [], 'events_path': str(events)})
        write_json(evidence / 'index.json', {'root_id': 'coordinator', 'agents': agents, 'gaps': []})
        return {'session_id': None, 'terminal_success': True, 'gaps': [],
                'structured_output': {'assessment': 'acceptable', 'findings': [], 'observations': [], 'gaps': []}}


class LaunchJourneyTests(unittest.IsolatedAsyncioTestCase):
    async def test_inherited_child_fails_the_attempt_even_when_the_audit_accepts(self):
        with tempfile.TemporaryDirectory(prefix='orchflows-launch-') as folder:
            root = Path(folder)
            source = root / 'case'
            source.mkdir()
            write_json(source / 'case.json', {'packages': []})
            (source / 'request.md').write_text('review the answer', encoding='utf-8')
            (source / 'expected-behavior.md').write_text('An independent review.', encoding='utf-8')
            case = Case('core/launch', source, {'packages': []})
            result = await run_case(case, 1, root / 'run', FakeHost(), Scheduler(1, 15), {}, 5)
            self.assertEqual(result['assessment'], 'material_failure')
            self.assertEqual([f['requirement'] for f in result['findings']],
                             ['Launch delegated children fresh, without inherited parent history'])
            attempt = root / 'run/core/launch/1'
            self.assertEqual(read_json(attempt / 'stages/target/stage.json')['violations'], result['findings'])
            evidence_packet = packet(attempt)
            self.assertIn('### Agent reviewer; parent coordinator; launch inherited;', evidence_packet)
            self.assertIn('"forked_from_id": "coordinator"', evidence_packet)
            self.assertIn('Launch delegated children fresh', evidence_packet)


if __name__ == '__main__':
    unittest.main()
