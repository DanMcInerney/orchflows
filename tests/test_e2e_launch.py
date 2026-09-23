"""Recorded child launch context reaches stage violations, gaps, verdicts and the audit packet without a judge."""
import json
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
from trial import interpreter_conditions, launch_checks

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

    def test_an_agent_launched_by_a_child_is_an_invariant_violation(self):
        agents = [{'id': 'coordinator', 'parent_id': None}, {'id': 'maker', 'parent_id': 'coordinator'},
                  {'id': 'helper', 'parent_id': 'maker'}]
        violations, gaps = launch_checks('target', {'root_id': 'coordinator', 'agents': agents})
        self.assertEqual(gaps, [])
        self.assertEqual(violations, [{'passed': False, 'invariant': True, 'requirement': 'Only the coordinator launches agents',
                                       'evidence': 'stages/target/evidence/index.json: agent helper (parent maker) was launched by a child'}])
        self.assertEqual(launch_checks('target', {'root_id': 'coordinator', 'agents': agents[:2]}), ([], []))


MISSING = "python : The term 'python' is not recognized as the name of a cmdlet, function, script file, or operable program."
CODEX_FAILURE = {'kind': 'tool_result', 'call_id': 'call-2',
                 'presented_output': [{'type': 'input_text', 'text': 'Script completed\nOutput:\n'},
                                      {'type': 'input_text', 'text': MISSING}]}
CLAUDE_FAILURE = {'kind': 'tool_result', 'call_id': 'toolu-2', 'is_error': True,
                  'presented_output': 'Exit code 127', 'data': {'stdout': '', 'stderr': '/usr/bin/bash: line 1: python: command not found'}}
HARMLESS = [{'kind': 'tool_call', 'call_id': 'call-1', 'tool': 'exec', 'data': 'python verify.py  # ' + MISSING},
            {'kind': 'tool_result', 'call_id': 'call-1', 'presented_output': 'print("Python 3 ready")'},
            {'kind': 'message', 'role': 'assistant', 'data': 'I will check that python is available.'}]


class InterpreterConditionTests(unittest.TestCase):
    def test_failed_python_commands_become_one_condition_with_their_first_location(self):
        with tempfile.TemporaryDirectory(prefix='orchflows-interpreter-') as folder:
            stage = Path(folder)
            events = {'coordinator': [*HARMLESS, CODEX_FAILURE], 'maker': [CLAUDE_FAILURE]}
            agents = []
            for name, records in events.items():
                path = stage / 'evidence' / (name + '.events.jsonl')
                path.parent.mkdir(exist_ok=True)
                path.write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')
                agents.append({'id': name, 'events_path': str(Path('elsewhere') / path.name)})
            self.assertEqual(interpreter_conditions('target', {'agents': agents}, stage),
                             ['Target could not run python: first failed command result at '
                              'stages/target/evidence/coordinator.events.jsonl:4 (2 in all)'])
            self.assertEqual(interpreter_conditions('target', {'agents': agents[:1]}, stage / 'none'), [])
            events_path = stage / 'evidence/coordinator.events.jsonl'
            events_path.write_text(''.join(json.dumps(r) + '\n' for r in HARMLESS), encoding='utf-8')
            self.assertEqual(interpreter_conditions('target', {'agents': agents[:1]}, stage), [])


class FakeHost:
    """Local harness control: writes a synthetic native index and establishes no native/LLM behavior."""
    name, version, capabilities = 'fake', 'test', set()

    def __init__(self, agents=AGENTS[:3], events=None, seconds=0):
        self.agents, self.events, self.seconds = agents, events or {}, seconds

    def invocation(self, entrypoint, request):
        return request

    def registration_gaps(self, native, packages):
        return []

    def command(self, packages, profile='local', schema=None, allowed_root=None, directory=None):
        return [sys.executable, '-c', f'import time; time.sleep({0 if profile == "audit" else self.seconds})']

    def result(self, directory):
        evidence = Path(directory) / 'evidence'
        agents = []
        for agent in self.agents:
            events = evidence / (agent['id'] + '.events.jsonl')
            events.parent.mkdir(parents=True, exist_ok=True)
            events.write_text(''.join(json.dumps(e) + '\n' for e in self.events.get(agent['id'], [])), encoding='utf-8')
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

    async def test_a_nested_launch_fails_a_timed_out_attempt(self):
        with tempfile.TemporaryDirectory(prefix='orchflows-launch-') as folder:
            root = Path(folder)
            source = root / 'case'
            source.mkdir()
            write_json(source / 'case.json', {'packages': [], 'timeout_seconds': 1})
            (source / 'request.md').write_text('make and review the answer', encoding='utf-8')
            (source / 'expected-behavior.md').write_text('A reviewed answer.', encoding='utf-8')
            case = Case('core/nested', source, {'packages': [], 'timeout_seconds': 1})
            agents = [{'id': 'coordinator', 'parent_id': None}, {'id': 'maker', 'parent_id': 'coordinator'},
                      {'id': 'helper', 'parent_id': 'maker'}]
            result = await run_case(case, 1, root / 'run', FakeHost(agents, seconds=30), Scheduler(2, 60), {}, 5)
            self.assertFalse(result['completed'])
            self.assertEqual(result['assessment'], 'material_failure')
            self.assertEqual([f['requirement'] for f in result['findings']], ['Only the coordinator launches agents'])
            self.assertIn('Stage execution: timeout', result['gaps'])

    async def test_interpreter_condition_is_reported_without_changing_the_verdict(self):
        with tempfile.TemporaryDirectory(prefix='orchflows-launch-') as folder:
            root = Path(folder)
            source = root / 'case'
            source.mkdir()
            write_json(source / 'case.json', {'packages': []})
            (source / 'request.md').write_text('check the answer with python', encoding='utf-8')
            (source / 'expected-behavior.md').write_text('A checked answer.', encoding='utf-8')
            case = Case('core/interpreter', source, {'packages': []})
            host = FakeHost([{'id': 'coordinator', 'parent_id': None}], {'coordinator': [CODEX_FAILURE]})
            result = await run_case(case, 1, root / 'run', host, Scheduler(1, 15), {}, 5)
            self.assertEqual((result['assessment'], result['gaps']), ('acceptable', []))
            condition = 'Target could not run python: first failed command result at stages/target/evidence/coordinator.events.jsonl:1 (1 in all)'
            self.assertEqual(result['conditions'], [condition])
            self.assertIn(condition, packet(root / 'run/core/interpreter/1'))


if __name__ == '__main__':
    unittest.main()
