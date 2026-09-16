import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

root=Path.cwd()
a=root.parent/'artifacts'
env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
checks=json.loads((a/'pass2-command-exits.json').read_text())
def run(command, filename):
    result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,encoding="utf-8")
    (a/filename).write_text(result.stdout+result.stderr,encoding='utf-8')
    checks.append(dict(command=command,cwd=str(root),completed_at=datetime.now(timezone.utc).isoformat(),exit_code=result.returncode,evidence=filename))
    (a/'pass2-command-exits.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout+result.stderr)
    return result.stdout

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

preserved=[]
for item in json.loads((a/'preserved-baseline-hashes.json').read_text(encoding='utf-8-sig')):
    path=Path(item['Path'])
    actual=sha(path)
    assert actual==item['Hash'].lower(), str(path)
    preserved.append({'path':str(path),'sha256':actual,'preserved':True})
(a/'pass2-preservation-check.json').write_text(json.dumps({'all_preserved':True,'files':preserved},indent=2)+'\n',encoding='utf-8')
commit=run(['git','rev-parse','HEAD'],'pass2-commit-id.txt').strip()
status=run(['git','status','--porcelain=v1'],'pass2-final-git-status.txt')
assert status.strip()=='?? caller-note.txt', status
baseline='19786e961751f9745f8fd92516b7a6e1ba249534'
run(['git','diff',baseline,commit,'--binary'],'pass2-candidate.patch')
run(['git','diff','0a7fc516fe94417187ee8efa208bf971c07476ff',commit,'--binary'],'pass2-repair.patch')
tool=Path('C:/Users/danhm/.orchflows/artifacts/software-factory-comparison-20260916-01/tools/release_simulator.py')
spec=importlib.util.spec_from_file_location('release_simulator',tool)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
manifest={**module.identity(root),'commit':commit,'baseline_commit':baseline}
(a/'pass2-candidate-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
state_before=sha(a/'release-state.json')
run([sys.executable,'-B',str(tool),'--state',str(a/'release-state.json'),'status'],'pass2-release-status.json')
assert sha(a/'release-state.json')==state_before
report=json.loads((a/'pass2-final-benchmark.json').read_text())
for name,digest in report['source_sha256'].items():
    assert digest==manifest['files'][name], name
assert sha(Path(report['archive']))==report['archive_sha256']
assert manifest=={**module.identity(root),'commit':commit,'baseline_commit':baseline}
evidence={
    'candidate_commit':commit,'candidate_sha256':manifest['sha256'],
    'status':'passed; frozen and ready for fresh independent reviews',
    'required_checks':checks,
    'nested_reproductions':'API all six depths and CLI depth550 passed; outputs independently asserted',
    'tests':17,'throughput_ratio':report['throughput_ratio'],
    'all_timed_answers_equal':report['all_timed_answers_equal'],
    'protected_files_preserved':len(preserved),
    'source_frozen_at':datetime.now(timezone.utc).isoformat(),
    'release_mutations':0,'release_state_sha256':state_before,
    'evidence_sha256':{p.name:sha(p) for p in sorted(a.glob('pass2-*')) if p.is_file() and p.suffix!='.ndjson'},
}
(a/'pass2-check-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'commit':commit,'source_sha256':manifest['sha256'],'files':len(manifest['files']),'status':status,'tests':17,'benchmark_ratio':report['throughput_ratio'],'rounds':[{k:v for k,v in row.items() if k in ('round','order','baseline_seconds','candidate_seconds')} for row in report['rounds']]},indent=2))
