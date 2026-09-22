"""Offline framework behavior; these tests make no LLM capability claims."""
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from catalog import discover, overrides, packages_for, select
from common import copy_package, read_json, snapshot, write_json
from judging import aggregate, validate
from scheduler import Scheduler


class CatalogTests(unittest.TestCase):
    def test_default_suite_is_curated_and_resolves(self):
        cases = discover()
        selected = select(cases, ['smoke'])
        self.assertEqual(len(selected), 4)
        for case in selected:
            self.assertIn('orchflows', packages_for(case))

    def test_repeated_suites_combine(self):
        from run import parser
        cases = discover()
        args = parser().parse_args(['--suite', 'smoke', '--suite', 'examples', '--plan'])
        self.assertEqual(args.suite, ['smoke', 'examples'])
        combined = {c.id for c in select(cases, args.suite)}
        self.assertEqual(combined, {c.id for c in select(cases, ['smoke'])} | {c.id for c in select(cases, ['examples'])})
        self.assertEqual(parser().parse_args([]).suite, [])

    def test_new_external_case_requires_no_registry_change(self):
        with tempfile.TemporaryDirectory(prefix='e2e-external-') as folder:
            root = Path(folder)
            case = root / 'new-case'
            case.mkdir()
            write_json(case / 'case.json', {'packages': ['orchflows'], 'covers': ['custom']})
            (case / 'request.md').write_text('Do ordinary work.')
            (case / 'expected-behavior.md').write_text('A useful result.')
            cases = discover([root])
            identifier = root.name + '/new-case'
            self.assertIn(identifier, cases)
            self.assertNotIn(identifier, [c.id for c in select(cases, ['smoke'])])
            self.assertEqual(select(cases, identifiers=[identifier])[0].id, identifier)
            write_json(case / 'case.json', {'packages': ['orchflows'], 'steps': []})
            with self.assertRaises(ValueError):
                discover([root])

    def test_missing_package_and_unknown_case_fail_clearly(self):
        from dataclasses import replace
        case = next(iter(discover().values()))
        bad = replace(case, config={**case.config, 'packages': ['not-installed']})
        with self.assertRaisesRegex(ValueError, 'Missing package'):
            packages_for(bad)
        with self.assertRaisesRegex(ValueError, 'Unknown cases'):
            select(discover(), identifiers=['core/nonexistent'])

    def test_explicit_package_root_replaces_default_and_plan_shows_it(self):
        case = select(discover(), ['smoke'])[0]
        with tempfile.TemporaryDirectory(prefix='e2e-baseline-') as folder:
            copy = Path(folder) / 'orchflows'
            write_json(copy / 'plugin.json', read_json(ROOT / 'plugin.json'))
            self.assertEqual(packages_for(case, [copy])['orchflows'], copy.resolve())
            self.assertEqual(packages_for(case)['orchflows'], ROOT.resolve())
            self.assertEqual(overrides([copy]), {'orchflows': {'default': str(ROOT.resolve()), 'explicit': str(copy.resolve())}})
            self.assertEqual(overrides([ROOT]), {})
            plan = subprocess.run([sys.executable, '-B', str(ROOT / 'tests/e2e/run.py'), '--plan', '--case', case.id,
                                   '--package-root', str(copy)], capture_output=True, text=True, check=True)
            printed = json.loads(plan.stdout)
            self.assertEqual(printed['package_overrides']['orchflows']['explicit'], str(copy.resolve()))
            self.assertEqual(printed['cases'][0]['sources']['orchflows'], str(copy.resolve()))
            second = Path(folder) / 'other' / 'orchflows'
            write_json(second / 'plugin.json', read_json(ROOT / 'plugin.json'))
            with self.assertRaisesRegex(ValueError, 'Duplicate package source: orchflows'):
                packages_for(case, [copy, second])

    def test_runtime_copy_excludes_evaluator_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source'
            source.mkdir()
            write_json(source / 'plugin.json', {'name': 'sample', 'version': '1'})
            (source / 'skills').mkdir()
            (source / 'skills/SKILL.md').write_text('Instructions')
            (source / 'trials').mkdir()
            (source / 'trials/expected-behavior.md').write_text('Secret answer')
            before = snapshot(source)
            result = copy_package(source, root / 'copy')
            self.assertEqual(snapshot(source), before)
            self.assertFalse((root / 'copy/trials').exists())
            self.assertEqual((root / 'copy/skills/SKILL.md').read_text(), 'Instructions')
            self.assertIn('trials/expected-behavior.md', result['excluded'])


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.acceptable = {'assessment': 'acceptable', 'findings': [], 'observations': ['Different valid approach'], 'gaps': []}

    def test_acceptable_variation(self):
        result = aggregate({'completed': True, 'gaps': []}, {'checks': [], 'gaps': []}, validate(self.acceptable))
        self.assertEqual(result['assessment'], 'acceptable')

    def test_objective_failure_cannot_be_overruled(self):
        result = aggregate({'completed': True}, {'checks': [{'passed': False, 'requirement': 'No send', 'evidence': 'receipt'}]}, self.acceptable)
        self.assertEqual(result['assessment'], 'material_failure')

    def test_missing_execution_or_audit_is_inconclusive(self):
        self.assertEqual(aggregate({'completed': False}, {}, self.acceptable)['assessment'], 'inconclusive')
        self.assertEqual(aggregate({'completed': True}, {}, {})['assessment'], 'inconclusive')
        self.assertEqual(aggregate({'completed': True, 'gaps': ['truncated']}, {}, self.acceptable)['assessment'], 'inconclusive')

    def test_failure_survives_audit_gap(self):
        result = aggregate({'completed': False}, {'checks': [{'passed': False, 'invariant': True}]}, {'gaps': ['judge timeout']})
        self.assertEqual(result['assessment'], 'material_failure')

    def test_unfinished_output_is_not_a_confirmed_violation(self):
        result = aggregate({'completed': False}, {'checks': [{'passed': False}]}, self.acceptable)
        self.assertEqual(result['assessment'], 'inconclusive')

    def test_unsupported_findings_and_false_approval_rejected(self):
        for value in ({**self.acceptable, 'assessment': 'material_failure'},
                      {**self.acceptable, 'gaps': ['Missing review evidence']},
                      {**self.acceptable, 'findings': [{'requirement': 'Better style'}]}):
            with self.assertRaises(ValueError):
                validate(value)


class SchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='orchflows-scheduler-')
        self.root = Path(self.temporary.name)

    async def asyncTearDown(self):
        self.temporary.cleanup()

    async def job(self, scheduler, name, seconds=.2, timeout=5):
        return await scheduler.process([sys.executable, '-u', '-c',
            f'import time; print("started", flush=True); time.sleep({seconds}); print("done")'],
            cwd=self.root, directory=self.root / name, timeout=timeout, label=name)

    async def test_parallel_overlap_and_cap(self):
        scheduler = Scheduler(2, 10, self.root / 'schedule.jsonl')
        results = await asyncio.gather(*(self.job(scheduler, str(n), .3) for n in range(3)))
        self.assertTrue(all(r['status'] == 'completed' for r in results))
        events = [json.loads(line) for line in (self.root/'schedule.jsonl').read_text().splitlines()]
        self.assertEqual(scheduler.peak, 2)
        self.assertLessEqual(max(e['active'] for e in events), 2)
        self.assertEqual([e['kind'] for e in events[:2]], ['started', 'started'])

    async def test_timeout_retains_partial_output_and_releases_slot(self):
        scheduler = Scheduler(1, 10)
        result = await self.job(scheduler, 'slow', 30, .25)
        self.assertEqual(result['status'], 'timeout')
        self.assertIn('started', (self.root/'slow/events.jsonl').read_text())
        self.assertNotIn('done', (self.root/'slow/events.jsonl').read_text())
        self.assertIsNotNone(result['exit_code'])
        self.assertEqual((await self.job(scheduler, 'next', .01))['status'], 'completed')

    async def test_queued_work_does_not_launch_after_deadline(self):
        scheduler = Scheduler(1, .25)
        results = await asyncio.gather(self.job(scheduler, 'slow', 30), self.job(scheduler, 'queued'))
        self.assertEqual(results[0]['status'], 'timeout')
        self.assertEqual(results[1]['status'], 'not_started')
        self.assertFalse((self.root/'queued/events.jsonl').exists())

    async def test_cancel_reaps_process_and_records_result(self):
        scheduler = Scheduler(1, 10)
        task = asyncio.create_task(self.job(scheduler, 'cancel', 30))
        while not (self.root/'cancel/events.jsonl').exists():
            await asyncio.sleep(.01)
        task.cancel()
        result = await task
        self.assertEqual(result['status'], 'canceled')
        self.assertIsNotNone(result['exit_code'])
        self.assertEqual(read_json(self.root/'cancel/execution.json')['status'], 'canceled')


if __name__ == '__main__':
    unittest.main()
