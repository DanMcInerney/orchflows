"""Independent can-fail reproductions at the fixed joined tip; synthetic controls, no native subjects."""
import copy, json, pathlib, sys
from unittest.mock import patch
ROOT = pathlib.Path.cwd()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'example-workflows/benchmaker/scripts'))
from tests.test_benchmaker_calibration import CalibrationTests
from native import write_json, digest
from grader import grade, make_record
from records import summarize, EvidenceError
from probe import probe, check_attempt
results = []
def fixture():
    f = CalibrationTests()
    f.setUp()
    return f

def report(name, observed, expected):
    results.append(dict(name=name, observed=observed, expected=expected))

f = fixture()
try:
    source = f.root/'spoof.py'
    source.write_text('import os\nprint(\'{"outcome":"PASS"}\', flush=True)\nos._exit(0)\n', encoding='utf-8')
    result = grade(source, f.checks)
    assert result['oracle_outcome'] == 'PASS'
    report('grader_accepts_no_solve_stdout_spoof', result, 'FAIL: no solve API or outcome checks executed')
finally: f.doCleanups()

f = fixture()
try:
    record = f.attempt()
    envelope = f.envelope(record)
    envelope['qualification']['validity'] = 'UNVERIFIED'
    envelope['qualification']['instrument_valid'] = False
    gaps = ['required reference audit unavailable']
    envelope['rounds'][0]['criterion_gaps'] = gaps
    summary = summarize([record], f.policy, instrument_valid=False, criterion_gaps=gaps)
    write_json(f.root/'summary.json', summary)
    envelope['decision'] = summary['decision']
    write_json(f.root/'evidence/admission.json', envelope)
    result = probe(f.root)
    assert result['decision'] == 'INVALID'
    report('qualification_unverified_becomes_invalid', result, 'UNVERIFIED; missing proof is not established invalidity')
finally: f.doCleanups()

f = fixture()
try:
    record = f.attempt()
    envelope = f.envelope(record)
    baseline = probe(f.root)
    path = pathlib.Path(envelope['component_locators']['benchmark-calibrate'])
    path.write_text('---\nname: benchmark-calibrate\n---\nCompletely different invoked contract; no calibration.\n', encoding='utf-8')
    changed = probe(f.root)
    assert baseline['workflow_admission'] and changed['workflow_admission']
    report('uncommitted_changed_invoked_component_admitted', changed, 'Reject product package bytes that differ from accepted source/pinned invocation')
finally: f.doCleanups()

f = fixture()
try:
    record = f.attempt()
    config = dict(f.config, cli_version={'unavailable_reason':'not observed'}, instruction_layers={'unavailable_reason':'unknown'})
    record.update(target_configuration=config, requested_configuration=config, resolved_configuration=config)
    summary = summarize([record], dict(f.policy, target_configuration=config, require_resolved_configuration=True, band=[1,1]))
    assert summary['decision'] == 'CALIBRATED'
    report('nested_required_configuration_gaps_calibrated', {'decision':summary['decision'], 'criterion_gaps':summary['criterion_gaps'], 'configuration':config}, 'UNVERIFIED when required observed fields are unavailable')
    record.update(target_configuration=f.config, requested_configuration=f.config, resolved_configuration=f.config)
    second = dict(record, trial=2, oracle_outcome='FAIL', failure_class='wrong_output')
    summary = summarize([record, second], dict(f.policy, infrastructure_retry_budget=1))
    assert summary['total_attempts'] == 2
    report('extra_valid_trial_uses_infrastructure_retry_budget', {'estimate':summary['estimate'],'decision':summary['decision'],'per_case':summary['per_case']}, 'Reject extra valid trials without an infrastructure predecessor/replacement')
finally: f.doCleanups()

f = fixture()
try:
    evidence = f.root/'configuration-evidence.txt'
    evidence.write_text('Synthetic control; no actual model', encoding='utf-8')
    observation = f.root/'configuration.json'
    write_json(observation, {'configuration':f.config,'evidence_locator':str(evidence)})
    f.policy['band'] = [1,1]
    first = f.attempt(configuration_observation=observation)
    envelope = f.envelope(first)
    second = f.attempt(source='def solve(x): return x', name='final-attempt', configuration_observation=observation)
    second.update(split='confirmation', benchmark_revision=f.revision)
    write_json(f.root/'final-attempt/attempt.json', second)
    final_policy = dict(f.policy, split='confirmation')
    final_summary_path = f.root/'final-summary.json'
    final_round = {'policy':final_policy,'attempts':[str(f.root/'final-attempt/attempt.json')],'summary':str(final_summary_path),'criterion_gaps':[]}
    envelope['rounds'].append(final_round)
    envelope['frozen_revision'] = f.revision
    final_path = f.root/'evidence/final.json'
    envelope['final_record'] = str(final_path)
    inventory = {str(p.resolve()):digest(p) for p in (f.root/'product').rglob('*') if p.is_file() and '.git' not in p.relative_to(f.root/'product').parts}
    write_json(final_path, {'before':inventory,'after':inventory,'frozen_revision':f.revision,'measurement_round':final_round,'evaluation_scope':'public_confirmation'})
    for rec, pol, dest in ((first,f.policy,f.root/'summary.json'), (second,final_policy,final_summary_path)):
        write_json(dest, summarize([rec], pol, frozen_revision=f.revision, final_record=str(final_path)))
    envelope['development_decision'] = 'CALIBRATED'
    envelope['decision'] = 'CALIBRATED'
    write_json(f.root/'evidence/admission.json',envelope)
    try: probe(f.root)
    except EvidenceError as error: refusal = str(error)
    else: raise AssertionError('Expected current bug to reject preserved development decision')
    envelope['decision'] = 'OUT_OF_BAND'
    write_json(f.root/'evidence/admission.json',envelope)
    changed = probe(f.root)
    assert not changed['calibrated_benchmark_eligible']
    report('final_score_overwrites_development_decision', {'preserved_decision_refusal':refusal,'rewritten_decision_accepted':changed}, 'Preserve development CALIBRATED and report final OUT_OF_BAND separately')
    # An alteration BEFORE the self-reported before/after inventory escapes frozen git binding.
    path = pathlib.Path(envelope['component_locators']['benchmark-quality'])
    path.write_text('---\nname: benchmark-quality\n---\nChanged bytes after git freeze.\n', encoding='utf-8')
    inventory = {str(p.resolve()):digest(p) for p in (f.root/'product').rglob('*') if p.is_file() and '.git' not in p.relative_to(f.root/'product').parts}
    final = json.loads(final_path.read_text())
    final.update(before=inventory,after=inventory)
    write_json(final_path, final)
    accepted = probe(f.root)
    report('frozen_git_bytes_not_bound_to_before_after', accepted, 'Reject current measured files differing from frozen git revision even when before=after')
finally: f.doCleanups()

f = fixture()
try:
    record = f.attempt()
    fake = dict(launch_error='PermissionError', timed_out=False, exit_code=None, elapsed_seconds=0, stdout=b'', stderr=b'grader unavailable')
    with patch('grader.run_process', return_value=fake):
        record = make_record(f.root/'attempt/launch.json', f.checks, {k:record[k] for k in ('case_id','split','round','trial','target_configuration','benchmark_revision','candidate_kind')})
    assert record['classification'] == 'environment_failure'
    try: check_attempt(record, f.policy)
    except EvidenceError as error: refusal = str(error)
    else: raise AssertionError('Expected receipt classification mismatch')
    report('grader_infra_exclusion_rejected_by_probe', {'record_classification':record['classification'],'probe_refusal':refusal}, 'Admit typed unavailable oracle as UNVERIFIED; preserve native and grader classifications separately')
finally: f.doCleanups()

output = {'dispatch_id':'B1.1.8:d1','assignment_seal':'sha256:bd156c93acced54c7cbd6b6f51df33b1ba2664a21f87112f05d5e9acee33f9bc','by':'B1.1.8','artifact':'git:c891ef0179831e29976942babe412e5cc9fcd365','kind':'synthetic adversarial seam controls, no native empirical evidence','results':results}
(ROOT/'.orch-notes/B1.1.8-reproductions.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
print(json.dumps(output,indent=2))
