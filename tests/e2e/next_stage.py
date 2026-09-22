"""Prepare isolated policy conditions; native execution is explicit and API-only."""
import argparse
import asyncio
from dataclasses import replace
from datetime import datetime, timezone
import difflib
import json
import os
from pathlib import Path
import shutil
from types import SimpleNamespace

from catalog import discover, packages_for, select
from common import ROOT, copy_package, files_under, snapshot, write_json
from run import execute

DIRECT_CHECK = (
    'Establish the result and checks. When a mistake would be cheap to undo and direct checks would catch it, '
    "do the work and check it without independent review unless requested. Checks the maker writes share the maker's reading of the requirements, so they cannot stand in for review when a misreading would be costly. If consequential uncertainty emerges, "
    'add review where useful; unavailable reviewers do not make work trivial.\n\nOtherwise briefly plan'
)


def prepare(output, condition, selected):
    if condition not in {'current', 'review-every-unit'}:
        raise ValueError('Unknown policy condition')
    if any(set(case.config['packages']) != {'orchflows'} for case in selected):
        raise ValueError('This experiment freezes core-only cases')
    output = Path(output).expanduser().resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise ValueError('Use a new experiment directory outside the checkout')
    output.mkdir(parents=True)
    core = output / 'core'
    record = copy_package(ROOT, core)
    skill = core / 'skills/orch-dynamic-workflow/SKILL.md'
    before = skill.read_text(encoding='utf-8')
    after = before
    if condition == 'review-every-unit':
        if before.count(DIRECT_CHECK) != 1:
            raise ValueError('Current exception changed; review the experimental intervention')
        after = before.replace(DIRECT_CHECK, 'Establish the result and checks. Briefly plan')
        skill.write_text(after, encoding='utf-8')
    (output / 'policy.diff').write_text(''.join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile='current', tofile=condition)), encoding='utf-8')
    scenarios = []
    for case in selected:
        destination = output / 'cases' / case.id
        shutil.copytree(files_under(case.path), destination, ignore=shutil.ignore_patterns('__pycache__'))
        scenarios.append({'id': case.id, 'source': str(case.path), 'timeout': case.timeout,
                          'frozen_path': destination.relative_to(output).as_posix(),
                          'scenario_files': snapshot(destination)})
    write_json(output / 'preparation.json', {
        'record_type': 'immutable_preparation_receipt',
        'prepared_at': datetime.now(timezone.utc).isoformat(),
        'condition': condition, 'source': record, 'runtime_files': snapshot(core),
        'cases': scenarios, 'native_executions_at_preparation': 0,
        'execution_results': 'execution/summary.json (only present after an execution)',
        'scope': 'Only the Dynamic direct-check exception changes; source checkout is unchanged.'})
    return output, core


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--condition', choices=['current', 'review-every-unit'], default='current')
    parser.add_argument('--suite', default='next-stage')
    parser.add_argument('--case', action='append', default=[])
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--executable')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--deadline', type=float, default=5400)
    parser.add_argument('--audit-seconds', type=float, default=240)
    args = parser.parse_args()
    if args.jobs < 1 or args.deadline <= 0 or args.audit_seconds <= 0:
        parser.error('Use positive jobs, deadline and audit-seconds')
    selected = select(discover(), [] if args.case else [args.suite], args.case)
    sources = {case.id: packages_for(case) for case in selected}
    key = os.environ.get('CODEX_API_KEY') or os.environ.get('OPENAI_API_KEY')
    if args.execute and not key:
        parser.error('API execution requires CODEX_API_KEY or OPENAI_API_KEY; no subscription fallback was attempted')
    output, core = prepare(args.output, args.condition, selected)
    if not args.execute:
        print(json.dumps({'status': 'prepared_only', 'condition': args.condition,
                          'cases': [case.id for case in selected], 'directory': str(output)}))
        return 0
    # Process-scoped only: never store a key in manifests, arguments or auth.json.
    os.environ['CODEX_API_KEY'] = key
    selected = [replace(case, path=output / 'cases' / case.id) for case in selected]
    for mapping in sources.values():
        mapping['orchflows'] = core
    launch = SimpleNamespace(output=output / 'execution', host='codex', executable=args.executable,
                             jobs=args.jobs, deadline=args.deadline, audit_seconds=args.audit_seconds, repeat=1)
    return asyncio.run(execute(launch, selected, sources))


if __name__ == '__main__':
    raise SystemExit(main())
