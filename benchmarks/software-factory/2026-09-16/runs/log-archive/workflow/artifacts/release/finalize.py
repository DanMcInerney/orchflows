import json,hashlib,runpy,subprocess
from pathlib import Path
from datetime import datetime,timezone
P=Path.cwd(); A=P.parent/'artifacts'; R=A/'release'
pre=json.loads((R/'preflight.json').read_text(encoding='utf-8'))
state=json.loads((R/'09-final-status.stdout.json').read_text(encoding='utf-8'))
tool=Path('C:/Users/danhm/.orchflows/artifacts/software-factory-comparison-20260916-01/tools/release_simulator.py')
ident=runpy.run_path(str(tool))['identity'](P)
assert ident==pre['source_identity']
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pre['bound_input_hashes'].items())
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip()
status=subprocess.check_output(['git','status','--porcelain=v1'],cwd=P,text=True).strip()
assert commit==pre['commit'] and status=='?? caller-note.txt'
assert state==json.loads((A/'release-state.json').read_text(encoding='utf-8'))
assert state['phase']=='rolled-back' and state['exposure']==0 and state['samples'][0]['recovery_verified']
assert state['events'][-2]['operation']=='rollback' and state['events'][-2]['restored']==pre['baseline_status']['baseline']['sha256']
entries=[json.loads(x) for x in (R/'operations.jsonl').read_text(encoding='utf-8').splitlines()]
assert len(entries)==20
assert all(entries[i]['event']=='intent' and entries[i+1]['event']=='result' and entries[i]['label']==entries[i+1]['label'] and entries[i+1]['exit_code']==0 for i in range(0,20,2))
assert [x['actual_operation_id'] for x in entries if x['event']=='result' and x['actual_operation_id'] is not None]==list(range(2,10))
post={'time':datetime.now(timezone.utc).isoformat(),'source_identity':ident,'commit':commit,'git_status':status,'all_bound_inputs_unchanged':True,'journal_intent_result_pairs':10,'all_commands_exit_zero':True,'all_stderr_empty':all(p.stat().st_size==0 for p in R.glob('*.stderr.txt')),'final_phase':state['phase'],'final_exposure':state['exposure'],'recovery_verified':True}
(R/'postflight.json').write_text(json.dumps(post,indent=2)+'\n',encoding='utf-8')
summary={'status':'rolled_back_recovery_verified','release_exercise_completed':True,'fully_released':False,'environment':'simulated-staging','candidate_path':str(P),'candidate_commit':commit,'source_sha256':ident['sha256'],'source_unchanged':True,'baseline_sha256':state['baseline']['sha256'],'intended_exposures':[10,50,100],'actual_deployments':[e for e in state['events'] if e['operation']=='deploy'],'actual_observations':[e for e in state['events'] if e['operation']=='observe'],'rollback':state['events'][-2],'final_phase':'rolled-back','final_exposure':0,'recovery_verified':True,'remaining_watch_window':None,'remaining_decisions':[],'not_attempted_exposures':[100],'journal':str(R/'operations.jsonl'),'raw_final_status':str(R/'09-final-status.stdout.json'),'baseline_measured_sample':None,'signals_are_synthetic':True,'child_agents_spawned':0}
(R/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
report='''# Release worker report

Disposition: **local synthetic rollout completed with rollback and verified recovery**. The candidate was not fully released. Final simulator phase is `rolled-back`, candidate exposure is **0%**, and no 100% deployment was attempted.

## Frozen artifact and authority

Candidate: C:/Users/danhm/.orchflows/artifacts/software-factory-comparison-20260916-01/runs/log-archive/workflow/project

Commit: `a685f46be6b9b755f8fe806556626bf34530d4b9`.
Source SHA-256: `431ec53dea8ab857e9aad7b298934d90fa6db497e693e9bb893e074ec69ce4cf`.

Read and applied the supplied orch-work assignment and software-factory release-worker section, with Make guidance in order: workflow-source/guidance/code.md then workflow-source/example-workflows/software-factory/guidance/software-delivery.md. The supplied core root directly contains skills/ and guidance/; initial redundant core/ lookups were corrected. Architecture, library/run contracts, RUN_CONTEXT.md, shared policy/tool, operations plan, builder report, manifest, check evidence, final tests/benchmark, all three pass-two review reports and the coordinator's joined gate were read.

The exact low-risk automatic review acceptance and separate local release/rollback authority are in ../joined-pass2.md and the shared RELEASE_POLICY.md. All 14 candidate files, Git commit/status, all 21 bound evidence files, benchmark sources/archive, passing command exits and benchmark acceptance were verified before mutation. Deploy used the actual ../pass2-final-tests.txt, SHA-256 `4d80430921d42782bd40125a80726e76285cc8155a95c8d55353a9f5fada32f9`. The tests report 17 passing tests; the retained benchmark reports all 96 answers equal and 262.473429x throughput. No check was replaced by simulator telemetry.

## Preflight

Read-only status showed case log-archive, environment simulated-staging, phase baseline, exposure 0, no candidate, no samples and only initialization operation 1. State bytes matched the frozen baseline-status evidence. Stored recovery identity was `1b62d83a0698b1ccd7a1595e44092a137ecd5cef1cc8efa5fd29e119425b5710`.

There was **no measured baseline traffic sample**. The simulator implementation supplies a healthy reference of error rate 0.001 and p95 80 ms; this was recorded as a reference, not an observation. The tool supports observation after deployment or rollback; unsupported baseline observation was never invoked. Rollback path and stopping rules were checked before deployment. Missing telemetry would hold; uncertain actions would reconcile status before any retry. Neither condition occurred.

## Actual operations and individually inspected samples

| Operation ID | Action | Exposure | Error rate | p95 ms | Outcome |
| --- | --- | ---: | ---: | ---: | --- |
| 2 | Deploy | 10% | — | — | Observing |
| 3 | Observe sample 1 | 10% | 0.001 | 80 | Healthy |
| 4 | Observe sample 2 | 10% | 0.001 | 80 | Healthy |
| 5 | Observe sample 3 | 10% | 0.001 | 80 | Healthy; advancement eligible |
| 6 | Deploy | 50% | — | — | Observing |
| 7 | Observe sample 1 | 50% | 0.04 | 340 | Both guardrails breached; advancement stopped |
| 8 | Rollback | 0% | — | — | Stored pristine baseline restored |
| 9 | Observe recovery | 0% | 0.001 | 80 | Healthy; recovery_verified=true |

Each observed sample contains 1,000 synthetic requests and represents a synthetic ten-second window. No live traffic, elapsed production monitoring, or background monitoring is claimed. The three consecutive 10% samples each satisfied error_rate <= 0.01 and p95_ms <= 200 before operation 6. Operation 7 was the first failure; the next state mutation was rollback. Its exact reason records 50% exposure, operation 7, error_rate=0.04 > 0.01 and p95_ms=340 > 200. Final read-only status confirms phase rolled-back, exposure 0, restored baseline event, candidate identity and the recovery sample. The candidate remains recorded in state for audit, with zero exposure.

## Evidence and remaining work

[operations.jsonl](operations.jsonl) contains a durable intent record before each command, with exact argv, cwd, candidate/authority/policy/evidence hashes and intended operation, followed by the actual exit, operation ID and raw result paths before advancement. Every command has separate raw stdout, stderr and result JSON; all ten commands exited 0 and stderr was empty. [preflight.json](preflight.json), [09-final-status.stdout.json](09-final-status.stdout.json), [postflight.json](postflight.json), and [summary.json](summary.json) retain the machine-readable evidence. The local driver is retained as driver.py.

Postflight independently reverified the exact source identity, commit, intentionally untracked caller-note.txt, policy/tool, approval/review/check inputs, journal pairing and final state. No source, policy, shared tool or release-state JSON was edited directly; state changed only through the shared simulator. No delegates, external services, publication, communications, other build arms or evaluation files were used. No further source edits will follow this report.

No remaining release decision or watch window is required for this scoped exercise. The stopped run must not advance to 100%. Any future release would need separately authorized work; the coordinator owns final checkpoint and RESULT.json/HANDOFF.md. Existing runtime/capacity limitations remain those documented in the validated builder/review evidence.
'''
(R/'REPORT.md').write_text(report,encoding='utf-8')
print(json.dumps({'report':str(R/'REPORT.md'),'summary':str(R/'summary.json'),'postflight':post},indent=2))
