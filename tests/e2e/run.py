"""Opt-in native trials and independent process audits; --plan launches no agents."""
import argparse
import asyncio
import json
import math
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
from catalog import discover, overrides, packages_for, select
from common import HERE, ROOT, read_json, write_json
from hosts import JOBS, get_host, requested
from judging import aggregate, audit_run
from scheduler import Scheduler
from sealing import seal
from trial import Trial, observed


async def run_case(case, number, root, host, scheduler, sources, audit_seconds):
    path = root / case.id / str(number)
    if time.monotonic() >= scheduler.end:
        result = {'case': case.id, 'attempt': number, 'started': False, 'completed': False, 'audited': False,
                  'assessment': 'inconclusive', 'findings': [], 'observations': [], 'gaps': ['Suite deadline before admission']}
        write_json(path / 'report.json', result)
        return result
    target = {'completed': False, 'gaps': []}
    checks = {'checks': [], 'gaps': []}
    audit = {'assessment': 'inconclusive', 'findings': [], 'observations': [], 'gaps': ['Audit not run']}
    try:
        missing = set(case.config.get('requires', [])) - host.capabilities
        if missing:
            raise ValueError('Unsupported capabilities: ' + ', '.join(sorted(missing)))
        trial = Trial(case, path, host, scheduler, sources)
        target = await trial.execute()
        checks['checks'] = [v for stage in target['stages'] for v in stage['violations']]
        hook = path / 'evaluation/check.py'
        if hook.exists():
            execution = await scheduler.process([sys.executable, '-B', str(HERE / 'checks.py'), str(path), str(hook)],
                cwd=path, directory=path / 'checking', timeout=20, native=False, label=f'checks:{case.id}#{number}')
            if (path / 'checks.json').exists():
                observed = read_json(path / 'checks.json')
                checks['checks'] += observed['checks']
                checks['gaps'] += observed['gaps']
            else:
                checks['gaps'].append('Checks did not finish: ' + execution['status'])
        write_json(path / 'checks.json', checks)
        seal(path)
        audit = await audit_run(path, host, scheduler, audit_seconds)
    except Exception as error:
        target['gaps'].append(f'{type(error).__name__}: {error}')
    stages = target.get('stages', [])
    result = {'case': case.id, 'attempt': number, 'started': any(s['execution']['status'] != 'not_started' for s in stages),
              'completed': target['completed'], 'audited': audit.get('audit_complete', False),
              'covers': case.config.get('covers', []), 'audit_path': audit.get('audit_path'),
              'observed': target.get('observed', {}), 'conditions': [c for s in stages for c in s.get('conditions', [])],
              **aggregate(target, checks, audit)}
    write_json(path / 'report.json', result)
    print(json.dumps(result), flush=True)
    return result


ASSESSMENTS = ('acceptable', 'material_failure', 'inconclusive')
# Per-attempt time outside the case and audit budgets: preparation, native inventory, evidence
# collection (15s per stage), checks (20s) and process-tree cleanup (up to 15s per session).
ATTEMPT_OVERHEAD = 60


def attempts(selected, repeat):
    """Longest case budgets first with all their repeats, so shorter attempts fill the tail."""
    return [(case, n) for case in selected for n in range(1, repeat + 1)]


def suite_deadline(selected, jobs, audit_seconds, repeat):
    """A suite deadline that a normal run reaches only after admitting every attempt.

    An admitted attempt ends within its budget. While any attempt waits, every slot is busy, so the
    last admission comes by sum/jobs and ends within the largest budget after that. Driver stages
    running in parallel take extra native slots and can exceed this bound.
    """
    budgets = [case.timeout + audit_seconds + ATTEMPT_OVERHEAD for case, _ in attempts(selected, repeat)]
    return math.ceil(sum(budgets) / jobs + max(budgets))


def per_case(results):
    """Outcomes of every attempt of each case; all_acceptable is pass^k over its attempts."""
    cases = {}
    for r in results:
        cases.setdefault(r['case'], []).append(r)
    return {case: {'attempts': len(runs), **{key: sum(r['assessment'] == key for r in runs) for key in ASSESSMENTS},
                   'all_acceptable': all(r['assessment'] == 'acceptable' for r in runs),
                   'observed': observed(r.get('observed', {}) for r in runs)} for case, runs in cases.items()}


def summarize(results, scheduler):
    counts = {key: sum(r['assessment'] == key for r in results) for key in ASSESSMENTS}
    counts.update(selected=len(results), started=sum(r['started'] for r in results),
                  completed=sum(r['completed'] for r in results), audited=sum(r['audited'] for r in results),
                  not_started=sum(not r['started'] for r in results))
    return {'counts': counts, 'cases': per_case(results), 'seconds': round(time.monotonic() - scheduler.started, 2),
            'peak_harness_sessions': scheduler.peak, 'results': results,
            'coverage_note': 'covers are declared claims; verified scope is limited to checks and cited audit evidence. '
                             'Lifecycle counts overlap; selected attempts are the denominator.'}


async def execute(args, selected, sources):
    output = args.output.expanduser().resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise ValueError('Use a new evidence directory outside the checkout')
    output.mkdir(parents=True)
    scheduler = Scheduler(args.jobs, args.deadline, output / 'schedule.jsonl')
    host = get_host(args.host, args.executable, getattr(args, 'model', None), getattr(args, 'effort', None))
    write_json(output / 'plan.json', {'host': args.host, 'host_version': host.version, 'jobs': args.jobs,
        'deadline': args.deadline, 'deadline_source': getattr(args, 'deadline_source', 'explicit'),
        'audit_seconds': args.audit_seconds, 'repeat': args.repeat,
        'model': getattr(host, 'model', None), 'effort': getattr(host, 'effort', None),
        'package_overrides': overrides(getattr(args, 'package_root', ())), 'cases': [{'id': c.id, **c.config, 'source': str(c.path)} for c in selected]})
    # A bounded case admission pool avoids starting every case deadline while queued.
    admission = asyncio.Semaphore(args.jobs)
    async def admitted(case, number):
        async with admission:
            scheduler.emit(kind='admitted', label=f'{case.id}#{number}')
            try:
                return await run_case(case, number, output, host, scheduler, sources[case.id], args.audit_seconds)
            finally:
                scheduler.emit(kind='released', label=f'{case.id}#{number}')
    selected_attempts = attempts(selected, args.repeat)
    tasks = [asyncio.create_task(admitted(case, n)) for case, n in selected_attempts]
    group = asyncio.gather(*tasks, return_exceptions=True)
    interrupted = False
    try:
        results = await asyncio.shield(group)
    except asyncio.CancelledError:
        interrupted = True
        scheduler.end = time.monotonic()
        for task in tasks:
            if not task.done():
                task.cancel()
        results = await group
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    for index, result in enumerate(results):
        if isinstance(result, BaseException):
            case, number = selected_attempts[index]
            path = output / case.id / str(number)
            if (path / 'report.json').exists():
                results[index] = read_json(path / 'report.json')
                continue
            started = any(read_json(p).get('pid') for p in (path / 'stages').glob('*/execution.json'))
            results[index] = {'case': case.id, 'attempt': number, 'started': started,
                'completed': False, 'audited': False, 'covers': case.config.get('covers', []),
                'assessment': 'inconclusive', 'findings': [], 'observations': [],
                'gaps': ['Suite interrupted; inspect retained stage records for partial execution.' if interrupted
                         else f'{type(result).__name__}: {result}']}
            write_json(path / 'report.json', results[index])
    summary = summarize(results, scheduler)
    summary['interrupted'] = interrupted
    write_json(output / 'summary.json', summary)
    starved = sum('Suite deadline before admission' in r['gaps'] for r in results)
    lines = ['# Native trial results', '', f"{summary['seconds']} seconds; peak {scheduler.peak} harness sessions; "
             f"{starved} of {len(results)} attempts not admitted before the suite deadline.", '',
             '| Case | Attempt | Assessment |', '| --- | --- | --- |']
    lines += [f"| {r['case']} | {r['attempt']} | {r['assessment']} |" for r in results]
    lines += ['', '| Case | Attempts | Acceptable | Material failure | Inconclusive | All acceptable | Observed models |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    lines += [f"| {case} | {c['attempts']} | {c['acceptable']} | {c['material_failure']} | {c['inconclusive']} | "
              f"{'yes' if c['all_acceptable'] else 'no'} | {', '.join(sorted(c['observed']['models'])) or 'none recorded'} |"
              for case, c in summary['cases'].items()]
    lines += ['', summary['coverage_note'], '', 'See each report.json and its cited evidence for findings and gaps.']
    (output / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(summary['counts']))
    return int(interrupted or any(r['assessment'] != 'acceptable' for r in results))


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--list', action='store_true')
    p.add_argument('--plan', action='store_true')
    p.add_argument('--suite', action='append', default=[], help='Suite to run; repeat to combine suites (default: smoke)')
    p.add_argument('--case', action='append', default=[])
    p.add_argument('--case-root', type=Path, action='append', default=[])
    p.add_argument('--package-root', type=Path, action='append', default=[])
    p.add_argument('--host', default='claude', choices=['claude', 'codex'])
    p.add_argument('--executable')
    p.add_argument('--model', help='Model for every session; default: the user host configuration')
    p.add_argument('--effort', help='Effort for every session; default: the user host configuration')
    p.add_argument('--jobs', type=int, default=JOBS, help=f'Concurrent harness sessions (default: {JOBS})')
    p.add_argument('--deadline', type=float, help='Suite seconds (default: derived so every attempt is admitted)')
    p.add_argument('--audit-seconds', type=float, default=600)
    p.add_argument('--repeat', type=int, default=1, help='Attempts per case; raise only for reliability claims')
    p.add_argument('--output', type=Path)
    return p


def main():
    p = parser()
    args = p.parse_args()
    if min(args.jobs, 1 if args.deadline is None else args.deadline, args.audit_seconds, args.repeat) <= 0:
        p.error('Budgets and concurrency must be positive')
    try:
        cases = discover(args.case_root)
        if args.list:
            for case in cases.values():
                print(json.dumps({'id': case.id, **case.config}))
            return 0
        selected = select(cases, args.suite, args.case)
        derived = suite_deadline(selected, args.jobs, args.audit_seconds, args.repeat)
        args.deadline_source = 'derived' if args.deadline is None else 'explicit'
        args.deadline = derived if args.deadline is None else args.deadline
        sources = {case.id: packages_for(case, getattr(args, 'package_root', ())) for case in selected}
        if args.plan:
            model, effort = requested(args.host, args.model, args.effort)
            plan = {'host': args.host, 'model': model, 'effort': effort, 'jobs': args.jobs,
                    'attempts': len(selected) * args.repeat, 'repeat': args.repeat, 'audit_seconds': args.audit_seconds,
                    'deadline': args.deadline, 'deadline_source': args.deadline_source, 'derived_deadline': derived}
            if args.deadline < derived:
                plan['deadline_note'] = 'Below the derived deadline: some attempts may not be admitted.'
            print(json.dumps({**plan,
                'package_overrides': overrides(getattr(args, 'package_root', ())), 'cases': [{'id': c.id, **c.config, 'sources': {k: str(v) for k, v in sources[c.id].items()}}
                          for c in selected]}, indent=2))
            return 0
        if not args.output:
            p.error('--output is required for execution')
        return asyncio.run(execute(args, selected, sources))
    except (ValueError, OSError) as error:
        p.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
