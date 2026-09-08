import json, shutil, subprocess, sys, tempfile
from pathlib import Path
root=Path.cwd()
sys.path.insert(0,str(root))
from tests.test_cell_linter_cases.standard_cells import CLONE_SKIPS, CROSS_TIER, warning_lines
prior='1256584e51c7a4d7068a7d5d555bb5fd7f07bf48'
paths=['example-workflows/tiktok-video/SKILL.md','example-workflows/tiktok-video/references/admission.md','example-workflows/tiktok-video/references/inventory.md','tests/test_tiktok_video_package.py']
record={'prior_revision':prior,'restored_paths':paths,'git_show_exits':[]}
with tempfile.TemporaryDirectory() as temp:
    clone=Path(temp)/'clone'
    shutil.copytree(root,clone,ignore=CLONE_SKIPS,symlinks=True)
    for path in paths:
        result=subprocess.run(['git','show',prior+':'+path],capture_output=True,timeout=30)
        record['git_show_exits'].append({'path':path,'exit':result.returncode})
        result.check_returncode()
        (clone/path).write_bytes(result.stdout)
    argv=[sys.executable,str(clone/'tools/validate.py')]
    result=subprocess.run(argv,cwd=clone,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    baseline=warning_lines(result.stdout,CROSS_TIER)
    current=warning_lines(Path('.orch-notes/B1.5-required.log').read_text(encoding='utf-8').split('--- tools/run_tests.py')[0],CROSS_TIER)
    record.update({'argv':argv,'timeout_seconds':180,'validator_exit':result.returncode,'baseline_warnings':baseline,'baseline_count':len(baseline),'current_count':len(current),'added':sorted(set(current)-set(baseline)),'removed':sorted(set(baseline)-set(current)),'stdout':result.stdout,'stderr':result.stderr})
Path('.orch-notes/B1.5-baseline-control.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k in ['validator_exit','baseline_count','current_count','added','removed']},indent=2))
sys.exit(0 if record['validator_exit']==0 and len(baseline)==29 and len(current)==30 and len(record['added'])==1 and not record['removed'] else 1)
