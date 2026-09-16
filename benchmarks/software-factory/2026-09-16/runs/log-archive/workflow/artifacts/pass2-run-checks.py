import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

root = Path.cwd()
artifacts = root.parent / 'artifacts'
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
checks = [
    ([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], 'pass2-final-tests.txt'),
    ([sys.executable, '-B', '../artifacts/review-correctness/nested_repro.py'], 'pass2-nested-repro.txt'),
    ([sys.executable, '-B', '../artifacts/review-correctness/nested_cli_repro.py'], 'pass2-nested-cli-repro.json'),
    ([sys.executable, 'benchmark.py', '--archive', '../artifacts/pass2-final-benchmark.ndjson', '--output', '../artifacts/pass2-final-benchmark.json'], 'pass2-final-benchmark-stdout.json'),
    (['git', 'diff', '--check'], 'pass2-diff-check.txt'),
]
results=[]
for command, filename in checks:
    start=datetime.now(timezone.utc).isoformat()
    result=subprocess.run(command, cwd=root, env=env, capture_output=True, text=True)
    (artifacts/filename).write_text(result.stdout + result.stderr, encoding='utf-8')
    item=dict(command=command, cwd=str(root), started_at=start, completed_at=datetime.now(timezone.utc).isoformat(), exit_code=result.returncode, evidence=filename)
    results.append(item)
    (artifacts/'pass2-command-exits.json').write_text(json.dumps(results, indent=2)+'\n',encoding='utf-8')
    print(json.dumps(item),flush=True)
    if result.returncode:
        print(result.stdout + result.stderr,flush=True)
        raise SystemExit(result.returncode)
api=[json.loads(line) for line in (artifacts/'pass2-nested-repro.txt').read_text().splitlines()]
assert all(row['baseline']==row['candidate']==1 for row in api), api
cli=json.loads((artifacts/'pass2-nested-cli-repro.json').read_text())
assert cli['returncode']==0 and not cli['stderr'],cli
assert json.loads(cli['stdout'])['total']==1
report=json.loads((artifacts/'pass2-final-benchmark.json').read_text())
assert report['all_timed_answers_equal'] and report['target_met']
print(json.dumps({'nested_reproductions':'passed','throughput_ratio':report['throughput_ratio']}))
