import sys, json, hashlib, subprocess, runpy, os
from pathlib import Path
from datetime import datetime, timezone
P=Path.cwd().resolve(); A=P.parent/'artifacts'; R=A/'release'
ROOT=Path('C:/Users/danhm/.orchflows/artifacts/software-factory-comparison-20260916-01')
TOOL=ROOT/'tools/release_simulator.py'; POLICY=ROOT/'tools/RELEASE_POLICY.md'; STATE=A/'release-state.json'
DIGEST='431ec53dea8ab857e9aad7b298934d90fa6db497e693e9bb893e074ec69ce4cf'
COMMIT='a685f46be6b9b755f8fe806556626bf34530d4b9'
BASELINE='1b62d83a0698b1ccd7a1595e44092a137ecd5cef1cc8efa5fd29e119425b5710'
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,x): p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def identity(): return runpy.run_path(str(TOOL))['identity'](P)
def journal(x):
    with (R/'operations.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps(x)+'\n'); f.flush(); os.fsync(f.fileno())
def verify():
    ident=identity(); manifest=read(A/'pass2-candidate-manifest.json'); evidence=read(A/'pass2-check-evidence.json')
    assert ident['sha256']==DIGEST and ident['files']==manifest['files']
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip()
    status=subprocess.check_output(['git','status','--porcelain=v1'],cwd=P,text=True).strip()
    assert commit==COMMIT and status=='?? caller-note.txt'
    assert evidence['candidate_sha256']==DIGEST and evidence['candidate_commit']==COMMIT
    assert all(sha(A/n)==h for n,h in evidence['evidence_sha256'].items())
    assert all(c['exit_code']==0 for c in evidence['required_checks'])
    b=read(A/'pass2-final-benchmark.json')
    assert b['all_timed_answers_equal'] and b['target_met'] and b['throughput_ratio']>=5
    assert all(sha(P/n)==h for n,h in b['source_sha256'].items())
    assert sha(Path(b['archive']))==b['archive_sha256']
    bound=[POLICY,TOOL,A/'joined-pass2.md',A/'pass2-candidate-manifest.json',A/'pass2-check-evidence.json',A/'pass2-final-tests.txt',A/'pass2-final-benchmark.json']
    bound += [A/f'review-{lens}-p2/REPORT.md' for lens in ('correctness','data','infrastructure')]
    hashes={str(p):sha(p) for p in bound}
    return {'time':now(),'commit':commit,'source_identity':ident,'git_status':status,'bound_input_hashes':hashes,'verified_evidence_files':len(evidence['evidence_sha256']),'all_checks_exit_zero':True,'benchmark_ratio':b['throughput_ratio']}
def run(label,args):
    argv=[sys.executable,'-B',str(TOOL),'--state',str(STATE)]+args
    current=verify()
    if (R/'preflight.json').exists(): assert current['bound_input_hashes']==read(R/'preflight.json')['bound_input_hashes']
    journal({'event':'intent','time':now(),'label':label,'intended_operation':args[0],'exact_argv':argv,'cwd':str(P),'state':str(STATE),'artifact_sha256':DIGEST,'artifact_commit':COMMIT,'authority':str(A/'joined-pass2.md'),'policy':str(POLICY),'bound_input_hashes':current['bound_input_hashes']})
    result=subprocess.run(argv,cwd=P,capture_output=True)
    (R/(label+'.stdout.json')).write_bytes(result.stdout); (R/(label+'.stderr.txt')).write_bytes(result.stderr)
    try: value=json.loads(result.stdout)
    except Exception: value=None
    op=value.get('operation',{}).get('operation_id') if isinstance(value,dict) else None
    info={'event':'result','time':now(),'label':label,'exit_code':result.returncode,'actual_operation_id':op,'stdout':str(R/(label+'.stdout.json')),'stderr':str(R/(label+'.stderr.txt')),'result':value}
    save(R/(label+'.result.json'),info); journal(info)
    if result.returncode or value is None:
        rec=subprocess.run([sys.executable,'-B',str(TOOL),'--state',str(STATE),'status'],cwd=P,capture_output=True)
        (R/(label+'.reconcile.stdout.json')).write_bytes(rec.stdout); (R/(label+'.reconcile.stderr.txt')).write_bytes(rec.stderr)
        journal({'event':'reconcile','time':now(),'label':label,'exit_code':rec.returncode,'stdout':str(R/(label+'.reconcile.stdout.json'))})
        raise RuntimeError('Uncertain or failed operation reconciled; HOLD, no retry')
    print(json.dumps(value,indent=2)); return value
if sys.argv[1]=='preflight':
    v=verify(); s=run('00-baseline-status',['status'])
    assert s['phase']=='baseline' and s['exposure']==0 and s['candidate'] is None and not s['samples'] and len(s['events'])==1
    assert s['baseline']['sha256']==BASELINE
    assert sha(STATE)==read(A/'pass2-check-evidence.json')['release_state_sha256']
    v.update(baseline_status=s,baseline_measured_sample=None,supplied_simulator_healthy_reference={'error_rate':0.001,'p95_ms':80,'requests':1000,'synthetic_window_seconds':10,'is_observation':False},thresholds={'error_rate_max':0.01,'p95_ms_max':200},rollback_argv=[sys.executable,'-B',str(TOOL),'--state',str(STATE),'rollback','--reason','ACTUAL observed values and exposure'],readiness='checks, reviews, low-risk scoped acceptance, artifact freeze, local target, baseline status, observation capability and authorized rollback verified')
    save(R/'preflight.json',v)
else:
    label=sys.argv[1]; args=sys.argv[2:]; s=read(STATE)
    if args[0]=='deploy':
        target=int(args[args.index('--exposure')+1])
        assert s['phase'] not in ('rolled-back','breached')
        assert target=={0:10,10:50,50:100}[s['exposure']]
        if s['exposure']:
            assert len(s['samples'])>=3 and all(x['healthy'] and x['error_rate']<=0.01 and x['p95_ms']<=200 for x in s['samples'][-3:])
    elif args[0]=='observe': assert s['phase'] in ('observing','rolled-back')
    elif args[0]=='rollback': assert s['phase']=='breached'
    run(label,args)
