"""Exercise the harness with real local processes and a deliberately fake agent."""
import asyncio
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests/e2e'))
from catalog import Case
from checks import run as check_outputs
from common import read_json, write_json
from judging import aggregate, audit_run
from run import execute, run_case
from scheduler import Scheduler
from sealing import seal, verify
from trial import Trial


class FakeHost:
    """Local harness control: establishes no native/LLM behavior."""
    name, version, capabilities = 'fake', 'test', set()

    def invocation(self, entrypoint, request):
        return request

    def registration_gaps(self, native, packages):
        return []

    def command(self, packages, profile='local', schema=None, allowed_root=None, directory=None):
        if profile == 'audit':
            script = 'print("audit control")'
        else:
            script = ('from pathlib import Path; import sys,time; '
                      'request=sys.stdin.read(); time.sleep(.03); '
                      'Path("answer.txt").write_text(request)')
        return [sys.executable, '-c', script]

    def result(self, directory):
        write_json(Path(directory)/'evidence/index.json', {'root_id': 'fake', 'agents': [], 'gaps': []})
        return {'session_id': None, 'terminal_success': True, 'gaps': [],
                'structured_output': {'assessment': 'acceptable', 'findings': [], 'observations': [], 'gaps': []}}


class JourneyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='orchflows-harness-')
        self.root = Path(self.temporary.name)
        source = self.root/'case'
        source.mkdir()
        write_json(source/'case.json', {'packages': ['example']})
        (source/'request.md').write_text('frozen request')
        (source/'expected-behavior.md').write_text('The request is copied.')
        (source/'check.py').write_text('def check(c):\n    c.require((c.stage()/"answer.txt").read_text() == "frozen request", "Exact output", "answer.txt")\n')
        package = self.root/'package'
        write_json(package/'plugin.json', {'name': 'example', 'version': '1'})
        self.case = Case('core/control', source, {'packages': ['example']})
        self.sources = {'example': package}

    async def asyncTearDown(self):
        self.temporary.cleanup()

    async def test_target_checks_audit_seal_and_report_as_one_pipeline(self):
        scheduler = Scheduler(1, 15)
        result = await run_case(self.case, 1, self.root/'run', FakeHost(), scheduler, self.sources, 5)
        self.assertEqual(result['assessment'], 'acceptable')
        self.assertTrue(result['started'] and result['completed'] and result['audited'])
        evidence = self.root/'run/core/control/1'
        self.assertEqual(verify(evidence), [])
        (evidence/'stages/target/workspace/answer.txt').write_text('changed')
        audit = await audit_run(evidence, FakeHost(), scheduler, 5)
        self.assertFalse(audit['audit_complete'])
        self.assertEqual(audit['assessment'], 'inconclusive')
        self.assertIn('Execution evidence changed', audit['gaps'][0])
        self.assertFalse((Path(audit['audit_path'])/'execution.json').exists())

    async def test_frozen_request_and_parallel_dependent_stages(self):
        (self.case.path/'driver.py').write_text('''import asyncio
async def run(t):
    first = await t.invoke('first')
    assert (first/'answer.txt').read_text() == 'frozen request'
    await asyncio.gather(t.invoke('second'), t.invoke('third'))
''')
        scheduler = Scheduler(2, 15, self.root/'schedule.jsonl')
        trial = Trial(self.case, self.root/'journey', FakeHost(), scheduler, self.sources)
        (self.case.path/'request.md').write_text('source changed after freezing')
        (self.case.path/'driver.py').write_text('raise RuntimeError("live driver must not run")')
        result = await trial.execute()
        self.assertTrue(result['completed'], result['gaps'])
        self.assertEqual([s['name'] for s in result['stages']][0], 'first')
        self.assertEqual({s['name'] for s in result['stages']}, {'first', 'second', 'third'})
        self.assertEqual(scheduler.peak, 2)
        for stage in result['stages']:
            self.assertEqual((Path(stage['workspace'])/'answer.txt').read_text(), 'frozen request')

    async def test_missing_output_vs_checker_bug(self):
        write_json(self.root/'target.json', {'completed': True})
        hook = self.root/'check.py'
        hook.write_text('def check(c):\n    c.json(c.root/"missing.json")\n')
        result = check_outputs(self.root, hook)
        self.assertEqual(result['gaps'], [])
        self.assertEqual(aggregate({'completed': True}, result, {})['assessment'], 'material_failure')
        self.assertEqual(aggregate({'completed': False}, result, {})['assessment'], 'inconclusive')
        hook.write_text('def check(c):\n    raise RuntimeError("broken checker")\n')
        result = check_outputs(self.root, hook)
        self.assertEqual(result['checks'], [])
        self.assertIn('broken checker', result['gaps'][0])

    async def test_repeat_reports_each_case_across_attempts_with_observed_models(self):
        class FlakyHost(FakeHost):
            targets = 0
            def command(self, packages, profile='local', *args, **kwargs):
                if profile != 'audit':
                    self.targets += 1
                    if self.targets == 2:
                        return [sys.executable, '-c', 'from pathlib import Path; Path("answer.txt").write_text("wrong")']
                return super().command(packages, profile, *args, **kwargs)
            def result(self, directory):
                native = super().result(directory)
                events = Path(directory)/'evidence/agent.events.jsonl'
                events.write_text('')
                write_json(Path(directory)/'evidence/index.json', {'root_id': 'fake', 'gaps': [], 'agents': [
                    {'id': 'agent', 'events_path': str(events), 'models': {'model-a': 2}, 'efforts': {'high': 2}}]})
                return native
        output = self.root/'repeated'
        args = SimpleNamespace(output=output, host='fake', executable=None, jobs=1,
                               deadline=30, audit_seconds=5, repeat=2)
        with patch('run.get_host', return_value=FlakyHost()):
            self.assertEqual(await execute(args, [self.case], {self.case.id: self.sources}), 1)
        summary = read_json(output/'summary.json')
        self.assertEqual(summary['cases'], {'core/control': {
            'attempts': 2, 'acceptable': 1, 'material_failure': 1, 'inconclusive': 0, 'all_acceptable': False,
            'observed': {'models': {'model-a': 4}, 'efforts': {'high': 4}}}})
        self.assertEqual([r['observed']['models'] for r in summary['results']], [{'model-a': 2}] * 2)
        self.assertEqual(read_json(output/'core/control/1/report.json')['observed']['efforts'], {'high': 2})
        self.assertIn('| core/control | 2 | 1 | 1 | 0 | no | model-a |', (output/'README.md').read_text())

    async def test_suite_interrupt_keeps_selected_denominator_and_partial_records(self):
        class SlowHost(FakeHost):
            def command(self, *args, **kwargs):
                return [sys.executable, '-u', '-c', 'import time; print("partial", flush=True); time.sleep(30)']
        output = self.root/'interrupted'
        args = SimpleNamespace(output=output, host='fake', executable=None, jobs=1,
                               deadline=15, audit_seconds=5, repeat=2)
        with patch('run.get_host', return_value=SlowHost()):
            task = asyncio.create_task(execute(args, [self.case], {self.case.id: self.sources}))
            while not (output/'schedule.jsonl').exists():
                await asyncio.sleep(.01)
            task.cancel()
            self.assertEqual(await task, 1)
        summary = read_json(output/'summary.json')
        self.assertTrue(summary['interrupted'])
        self.assertEqual(summary['counts']['selected'], 2)
        self.assertEqual(summary['counts']['acceptable'], 0)
        self.assertEqual(summary['counts']['not_started'], 1)
        self.assertEqual(read_json(output/'core/control/1/stages/target/execution.json')['status'], 'canceled')


class IntegrityTests(unittest.TestCase):
    def test_seal_detects_additions_deletions_but_allows_appended_audits(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'record.txt').write_text('evidence')
            seal(root)
            write_json(root/'audits/new/assessment.json', {})
            write_json(root/'report.json', {})
            self.assertEqual(verify(root), [])
            (root/'record.txt').unlink()
            (root/'unexpected.txt').write_text('new')
            self.assertEqual(len(verify(root)), 2)


if __name__ == '__main__':
    unittest.main()
