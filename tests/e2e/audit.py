"""Append independent assessments of frozen runs; never resume target sessions."""
import argparse
import asyncio
from pathlib import Path

from common import read_json, write_json
from hosts import EFFORT_HELP, MODEL_HELP, get_host
from judging import aggregate, audit_run
from scheduler import Scheduler


async def execute(args):
    roots = [args.root] if (args.root / 'target.json').exists() else sorted(p.parent for p in args.root.rglob('target.json'))
    host = get_host(args.host, args.executable, args.model, args.effort)
    scheduler = Scheduler(args.jobs, args.deadline)
    async def one(root):
        audit = await audit_run(root, host, scheduler, args.audit_seconds)
        result = aggregate(read_json(root / 'target.json'), read_json(root / 'checks.json'), audit)
        write_json(Path(audit['audit_path']) / 'report.json', result)
        print(root, result['assessment'], flush=True)
        return result
    results = await asyncio.gather(*(one(root) for root in roots))
    return int(not results or any(r['assessment'] != 'acceptable' for r in results))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path)
    p.add_argument('--host', default='claude', choices=['claude', 'codex'])
    p.add_argument('--executable')
    p.add_argument('--model', help=MODEL_HELP)
    p.add_argument('--effort', help=EFFORT_HELP)
    p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--deadline', type=float, default=120)
    p.add_argument('--audit-seconds', type=float, default=60)
    args = p.parse_args()
    if min(args.jobs, args.deadline, args.audit_seconds) <= 0:
        p.error('Positive budgets required')
    raise SystemExit(asyncio.run(execute(args)))
