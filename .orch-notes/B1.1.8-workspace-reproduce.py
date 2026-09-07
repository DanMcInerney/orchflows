import json, pathlib, subprocess, sys, tempfile
from unittest.mock import patch
ROOT=pathlib.Path.cwd()
sys.path.insert(0,str(ROOT))
from tests.test_workspace_cases import common
from scripts import state_root, tickets_store, workspace_return, tickets_pins
from tests.test_workspace_cases.integration_cases import baseline_of
calls=[]
original_run=subprocess.run
def tracked(command,*args,**kwargs):
    kwargs.setdefault('timeout',30)
    result=original_run(command,*args,**kwargs)
    calls.append({'command':[str(x) for x in command],'cwd':str(kwargs.get('cwd',ROOT)),'timeout':kwargs['timeout'],'exit_code':result.returncode,'stdout':result.stdout if isinstance(result.stdout,str) else None,'stderr':result.stderr if isinstance(result.stderr,str) else None})
    return result
with tempfile.TemporaryDirectory(prefix='benchmaker-review-workspace-',ignore_cleanup_errors=True) as folder:
    tmp=pathlib.Path(folder)
    with patch.object(subprocess,'run',side_effect=tracked):
        product,run_dir=common.make_repo(tmp)
        first=common.make_ticket(run_dir,'T1')
        establish_product=common.run_workspace(ROOT,'establish','testrun','T1','--repo',str(product))
        assert establish_product.returncode==0,establish_product.stderr
        target=tickets_store.integration_target('testrun')
        evidence=tmp/'evidence'
        evidence.mkdir()
        common.git(evidence,'init','--quiet')
        common.git(evidence,'config','user.name','review-fixture')
        common.git(evidence,'config','user.email','review@example.invalid')
        common.commit_in(evidence,{'README.md':'Separate external evidence repository\n'},'evidence baseline')
        second=common.make_ticket(run_dir,'T2')
        establish_evidence=common.run_workspace(ROOT,'establish','testrun','T2','--repo',str(evidence))
        assert establish_evidence.returncode==0,establish_evidence.stderr
        derived=state_root.candidate_paths('testrun','T2')
        attempt_commit=common.commit_in(derived['path'],{'scratch/attempt.json':'{"kind":"synthetic-test-only"}\n'},'external evidence')
        result,code=workspace_return.integrate('testrun','T2',derived['path'],derived['branch'],baseline_of(second))
        assert code==0 and result['integrate']['outcome']=='absent',result
        assert not (product/'scratch/attempt.json').exists()
        output={'dispatch_id':'B1.1.8:d1','assignment_seal':'sha256:bd156c93acced54c7cbd6b6f51df33b1ba2664a21f87112f05d5e9acee33f9bc','by':'B1.1.8','artifact':'git:c891ef0179831e29976942babe412e5cc9fcd365','kind':'real workspace CLI in disposable fixture state, no dispatch or native attempt','first_target':target,'evidence_establish_exit':establish_evidence.returncode,'evidence_commit':attempt_commit,'integrate_exit':code,'integrate':result,'commands':calls}
        (ROOT/'.orch-notes/B1.1.8-workspace-reproduction.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in output.items() if k!='commands'},indent=2))
pins={name:tickets_pins.tree_digest('standard',pathlib.Path('C:/Users/danhm/.orchflows/lib/standards')/name) for name in ('orch-code','orch-workflow-authoring')}
print(json.dumps({'standard_digests':pins},indent=2))
