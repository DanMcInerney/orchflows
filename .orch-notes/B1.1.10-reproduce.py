"""Updated semantic counterexamples; every candidate is a synthetic control."""
import copy,importlib.util,json,pathlib,sys,tempfile,unittest
ROOT=pathlib.Path.cwd()
sys.path.insert(0,str(ROOT))
from tests.test_benchmaker_calibration import SCRIPTS
from tests.test_benchmaker_repair import RepairTests
from grader import grade,make_record
from native import write_json,read_json,digest,run_process
from records import summarize,configuration_gaps,EvidenceError
from probe import probe
spec=importlib.util.spec_from_file_location('review_exports',SCRIPTS/'export.py')
exports=importlib.util.module_from_spec(spec);spec.loader.exec_module(exports)
results=[]
def add(name,observed,expected):results.append(dict(name=name,observed=observed,expected=expected))
def fixture():
    f=RepairTests();f.setUp();return f

f=fixture()
try:
    source=f.root/'new-spoof.py'
    # Fake a per-call response, with no solve symbol, for a one-case visible contract.
    payload=json.dumps({'returned':True,'value':7,'exception':None,'args_after':[3]})
    source.write_text('import os\nos.write(1, '+repr(payload.encode())+')\nos._exit(0)\n',encoding='utf-8')
    write_json(f.checks,{'checks':[{'args':[3],'expected':7}]})
    forged=grade(source,f.checks)
    assert forged['oracle_outcome']=='PASS'
    source.write_text('import os; print(\'{"outcome":"PASS"}\',flush=True); os._exit(0)',encoding='utf-8')
    old=grade(source,f.checks)
    assert old['oracle_outcome']=='FAIL'
    source.write_text('def solve(x): return 2*x+1',encoding='utf-8')
    legitimate=grade(source,f.checks)
    assert legitimate['oracle_outcome']=='PASS'
    add('new_call_protocol_spoof_without_api',{'original_spoof':old['oracle_outcome'],'new_spoof':forged,'legitimate':legitimate['oracle_outcome']},'Reject no solve API and premature worker exit even with a correctly shaped per-call response')
finally:f.doCleanups()

f=fixture()
try:
    record=f.attempt()
    config=dict(f.config,scaffold={'instructions':['pinned-instruction']})
    resolved=dict(f.config,scaffold={'unavailable_reason':'parent object unavailable'})
    record.update(target_configuration=config,requested_configuration=config,resolved_configuration=resolved)
    policy=dict(f.policy,target_configuration=config,band=[1,1],required_configuration_fields=['scaffold.instructions'],require_resolved_configuration=False)
    summary=summarize([record],policy)
    assert summary['decision']=='CALIBRATED'
    present=summarize([dict(record,resolved_configuration=config)],policy)
    assert present['decision']=='CALIBRATED'
    policy['require_resolved_configuration']=True
    policy['optional_configuration_fields']=['scaffold']
    nested=summarize([record],policy)
    assert nested['decision']=='CALIBRATED'
    add('required_nested_field_hidden_by_unavailable_parent',{'optional_default':{'decision':summary['decision'],'required_gaps':summary['criterion_gaps'],'optional_gaps':summary['optional_gaps']},'optional_parent_required_child':{'decision':nested['decision'],'required_gaps':nested['criterion_gaps'],'optional_gaps':nested['optional_gaps']},'observed_configuration':present['decision']},'Missing required scaffold.instructions must be UNVERIFIED even when its parent is optional or unavailable')
finally:f.doCleanups()

f=fixture()
try:
    envelope,record=f.final_envelope()
    accepted=probe(f.root)
    assert accepted['development_decision']=='CALIBRATED' and accepted['final_observations'][0]['band_observation']=='OUT_OF_BAND'
    summary_path=f.root/'summary.json'
    rewritten=summary_path.read_bytes()
    original=summarize([record],f.policy)
    write_json(summary_path,original)
    try:probe(f.root)
    except EvidenceError as error:refusal=str(error)
    else:raise AssertionError('Original published development summary should currently fail')
    assert 'summary differs' in refusal
    # Export the original committed summary, then attempt the rewrite required by probe.
    product=f.root/'product'
    (product/'records').mkdir()
    (product/'records/.gitattributes').write_text('* -text\n',encoding='utf-8')
    (product/'records/summary.json').write_bytes(summary_path.read_bytes())
    for command in (['git','add','records'],['git','-c','user.name=Fixture','-c','user.email=f@example.invalid','commit','-qm','original published summary']):
        assert run_process(command,cwd=product,timeout=20)['exit_code']==0
    sha=run_process(['git','rev-parse','HEAD'],cwd=product,timeout=20)['stdout'].decode().strip()
    dest=f.root/'published-evidence'
    exports.export_records(product,sha,'records',dest)
    (product/'records/summary.json').write_bytes(rewritten)
    for command in (['git','add','records'],['git','-c','user.name=Fixture','-c','user.email=f@example.invalid','commit','-qm','future metadata added']):
        assert run_process(command,cwd=product,timeout=20)['exit_code']==0
    sha=run_process(['git','rev-parse','HEAD'],cwd=product,timeout=20)['stdout'].decode().strip()
    try:exports.export_records(product,sha,'records',dest)
    except EvidenceError as error:export_refusal=str(error)
    else:raise AssertionError('Immutable export should reject retroactive rewrite')
    add('published_round_summary_must_be_rewritten_for_final',{'legitimate_final_score_separation':accepted,'retained_original_summary_refusal':refusal,'required_rewrite_export_refusal':export_refusal,'future_fields':['frozen_revision','final_record','revision_ledger']},'Validate an immutable round at its own observation identity; later aggregate metadata belongs in the result index')
finally:f.doCleanups()

f=fixture()
try:
    envelope,record=f.final_envelope()
    product=f.root/'product'
    benchmark=pathlib.Path(envelope['benchmark_manifest']).parent
    frozen_checks=benchmark/'checks.json'
    frozen_checks.write_bytes(f.checks.read_bytes())
    manifest=read_json(envelope['benchmark_manifest'])
    manifest['runnable_cases']='checks.json'
    write_json(envelope['benchmark_manifest'],manifest)
    for command in (['git','add','benchmark'],['git','-c','user.name=Fixture','-c','user.email=f@example.invalid','commit','-qm','freeze actual evaluator checks']):
        assert run_process(command,cwd=product,timeout=20)['exit_code']==0
    frozen=run_process(['git','rev-parse','HEAD'],cwd=product,timeout=20)['stdout'].decode().strip()
    envelope['frozen_revision']=frozen
    envelope['qualification']['revisions'][frozen]={'validity':'VALID','criterion_gaps':[]}
    envelope['qualification']['audits'].append(dict(envelope['qualification']['audits'][0],benchmark_revision=frozen))
    final_entry=envelope['rounds'][1]
    final_entry['qualification_revision']=frozen
    final_attempt=read_json(final_entry['attempts'][0])
    alternative=f.root/'alternate-checks.json'
    write_json(alternative,{'checks':[{'args':[2],'expected':2},{'args':[-1],'expected':-1}]})
    identity={key:final_attempt[key] for key in ('case_id','split','round','trial','target_configuration','candidate_kind','retry_of')}
    identity['benchmark_revision']=frozen
    forged=make_record(final_attempt['launch_receipt_locator'],alternative,identity)
    assert forged['oracle_outcome']=='PASS'
    actual=grade(forged['result_artifact_locator'],frozen_checks)
    assert actual['oracle_outcome']=='FAIL'
    inventory={str(path.resolve()):digest(path) for path in benchmark.rglob('*') if path.is_file()}
    write_json(envelope['final_record'],dict(before=inventory,after=inventory,frozen_revision=frozen,measurement_round=final_entry,evaluation_scope='public_confirmation'))
    write_json(f.root/'summary.json',summarize([record],f.policy,frozen_revision=frozen,final_record=envelope['final_record']))
    write_json(final_entry['summary'],summarize([forged],final_entry['policy'],frozen_revision=frozen,final_record=envelope['final_record']))
    write_json(f.root/'evidence/admission.json',envelope)
    accepted=probe(f.root)
    assert accepted['final_observations'][0]['estimate']==1
    add('final_attempt_grader_not_bound_to_frozen_checks',{'actual_frozen_checks_outcome':actual['oracle_outcome'],'alternative_uncommitted_checks_outcome':forged['oracle_outcome'],'probe':accepted},'Reject a final attempt evaluated against substitute checks outside the fixed benchmark identity')
finally:f.doCleanups()

payload={'dispatch_id':'B1.1.10:d1','assignment_seal':'sha256:1171e521432d2ce5c780f57c773f9bf8f74b8dd8cf711367b59f78cbe7f75012','assigned_name':'B1.1.10','reviewed_artifact':'git:ecd05f4117d4455afabca0638cfd9322b008e9f6','kind':'independent synthetic semantic counterexamples, no native subject attempts','results':results}
(ROOT/'.orch-notes/B1.1.10-reproductions.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
print(json.dumps(payload,indent=2))
