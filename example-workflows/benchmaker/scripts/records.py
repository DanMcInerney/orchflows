"""Finite-suite estimates over declared cases; no orchestration or population claim."""
import math
from pathlib import Path


class EvidenceError(ValueError):
    """An evidence contract is absent or inconsistent."""


REQUIRED = {
    'case_id', 'split', 'round', 'trial', 'target_configuration',
    'benchmark_revision', 'candidate_kind', 'requested_command',
    'resolved_command', 'requested_configuration', 'resolved_configuration',
    'prompt_locator', 'raw_transcript_locator', 'result_artifact_locator',
    'launch_receipt_locator', 'grader_observation_locator', 'classification',
    'exit_code', 'elapsed_seconds', 'token_usage', 'oracle_outcome',
    'failure_class', 'valid_for_estimate', 'exclusion_reason',
}
INFRA = {'permission_failure', 'launch_failure', 'environment_failure', 'startup_timeout'}
TARGET = {'completed', 'candidate_failure', 'task_timeout'}


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def validate_record(record, policy):
    require(REQUIRED <= record.keys(), 'missing attempt fields: ' + str(sorted(REQUIRED - record.keys())))
    require(record['candidate_kind'] in {'agent_attempt', 'control'}, 'unknown candidate kind')
    require(record['case_id'] in policy['case_ids'], 'undeclared case')
    require(record['split'] == policy['split'] and record['round'] == policy['round'], 'wrong split/round')
    require(type(record['trial']) is int and record['trial'] >= 1, 'invalid trial')
    config = policy['target_configuration']
    require(bool(config) and record['target_configuration'] == config, 'wrong target configuration')
    require(record['requested_configuration'] == config, 'wrong requested configuration')
    resolved = record['resolved_configuration']
    require(isinstance(resolved, dict) and bool(resolved), 'missing resolved configuration evidence')
    if 'unavailable_reason' in resolved:
        require(bool(resolved['unavailable_reason']), 'empty configuration gap')
        for key in set(resolved) & set(config):
            require(resolved[key] == config[key], 'wrong partially resolved configuration')
    else:
        require(resolved == config, 'wrong resolved configuration')
    require(record['requested_command'] and record['resolved_command'], 'missing native command')
    require(record['classification'] in INFRA | TARGET, 'unknown classification')
    require(type(record['valid_for_estimate']) is bool, 'validity must be boolean')
    require(record['oracle_outcome'] in {'PASS', 'FAIL', 'UNVERIFIED'}, 'unknown oracle outcome')
    require(isinstance(record['elapsed_seconds'], (int, float)) and math.isfinite(record['elapsed_seconds'])
            and record['elapsed_seconds'] >= 0, 'invalid elapsed time')
    if record['classification'] in INFRA:
        require(not record['valid_for_estimate'] and record['oracle_outcome'] == 'UNVERIFIED',
                'infrastructure counted as target outcome')
    if record['valid_for_estimate']:
        require(not record['exclusion_reason'] and record['oracle_outcome'] in {'PASS', 'FAIL'},
                'counted attempt lacks outcome or carries exclusion')
    else:
        require(bool(record['exclusion_reason']), 'unexplained exclusion')
    if record['classification'] in {'candidate_failure', 'task_timeout'}:
        require(record['valid_for_estimate'] and record['oracle_outcome'] == 'FAIL',
                'genuine candidate failure excluded')


def wilson(passes, count):
    if not count:
        return None
    z = 1.959963984540054
    p = passes / count
    denominator = 1 + z * z / count
    center = (p + z * z / (2 * count)) / denominator
    radius = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / denominator
    return [center - radius, center + radius]


def summarize(records, policy, *, criterion_gaps=(), instrument_valid=True,
              revision_ledger=(), frozen_revision=None, final_record=None):
    ids = policy['case_ids']
    require(ids and len(ids) == len(set(ids)), 'empty or duplicate declared cases')
    require(type(policy['trials_per_case']) is int and policy['trials_per_case'] > 0, 'invalid trial count')
    weights = policy.get('weights', {case: 1 / len(ids) for case in ids})
    require(set(weights) == set(ids) and all(v > 0 for v in weights.values())
            and math.isclose(sum(weights.values()), 1), 'invalid case weights')
    seen, gaps = set(), list(criterion_gaps)
    optional_gaps = []
    per_case = {case: dict(attempted=0, valid=0, passed=0, failed=0, invalid=0,
                           unverified=0, controls=0, failure_classes={}) for case in ids}
    revisions = set()
    for record in records:
        validate_record(record, policy)
        key = (record['benchmark_revision'], record['split'], record['round'], record['case_id'], record['trial'])
        require(key not in seen, 'duplicate trial identity')
        seen.add(key)
        row = per_case[record['case_id']]
        if record['candidate_kind'] == 'control':
            row['controls'] += 1
            continue
        revisions.add(record['benchmark_revision'])
        row['attempted'] += 1
        row['valid'] += int(record['valid_for_estimate'])
        row['passed'] += int(record['valid_for_estimate'] and record['oracle_outcome'] == 'PASS')
        row['failed'] += int(record['valid_for_estimate'] and record['oracle_outcome'] == 'FAIL')
        row['invalid'] += int(not record['valid_for_estimate'])
        row['unverified'] += int(record['oracle_outcome'] == 'UNVERIFIED')
        failure = record['failure_class']
        if failure:
            row['failure_classes'][failure] = row['failure_classes'].get(failure, 0) + 1
        if 'unavailable_reason' in record['resolved_configuration']:
            destination = gaps if policy.get('require_resolved_configuration', True) else optional_gaps
            destination.append('resolved_configuration: ' + str(record['resolved_configuration']['unavailable_reason']))
    require(len(revisions) == 1 and next(iter(revisions)), 'missing or mixed benchmark revisions')
    for case, row in per_case.items():
        require(row['attempted'] >= policy['trials_per_case'], 'missing attempts for ' + case)
        require(row['attempted'] <= policy['trials_per_case'] + policy.get('infrastructure_retry_budget', 0),
                'undeclared extra attempts for ' + case)
        indices = sorted(record['trial'] for record in records if record['case_id'] == case and record['candidate_kind'] == 'agent_attempt')
        require(indices == list(range(1, row['attempted'] + 1)), 'missing trial index for ' + case)
        if row['valid'] != policy['trials_per_case']:
            gaps.append('incomplete valid sample: ' + case)
        row['estimate'] = row['passed'] / row['valid'] if row['valid'] else None
        row['interval'] = wilson(row['passed'], row['valid'])
        row['interval_assumption'] = '95% Wilson, independent isolated trials conditional on this fixed case'
    attempted = sum(row['attempted'] for row in per_case.values())
    require(attempted <= len(ids) * policy['trials_per_case'] + policy.get('infrastructure_retry_budget', 0),
            'global infrastructure retry budget exceeded')
    estimate = None if any(row['estimate'] is None for row in per_case.values()) else sum(
        weights[case] * row['estimate'] for case, row in per_case.items())
    low, high = policy.get('band', [0.30, 0.50])
    require(0 <= low <= high <= 1, 'invalid band')
    band = 'UNVERIFIED' if estimate is None else ('IN_BAND' if low <= estimate <= high else 'OUT_OF_BAND')
    decision = ('INVALID' if not instrument_valid else 'UNVERIFIED' if gaps or estimate is None
                else 'OUT_OF_BAND' if band == 'OUT_OF_BAND' else 'CALIBRATED')
    return dict(benchmark_revision=next(iter(revisions)), target_configuration=policy['target_configuration'],
                split=policy['split'], round=policy['round'], policy=policy,
                attempt_locators=[str(Path(record['launch_receipt_locator']).with_name('attempt.json')) for record in records],
                estimator='weighted mean of per-case isolated-trial success rates (pass@1)',
                weights=weights, independent_unit='case; repeated trials are conditional observations',
                per_case=per_case, distinct_cases=len(ids), total_attempts=attempted,
                estimate=estimate, interval=None,
                interval_unavailable_reason='Purposively selected finite suite; no population sampling model',
                band_observation=band, decision=decision, criterion_gaps=sorted(set(gaps)),
                optional_gaps=sorted(set(optional_gaps)),
                revision_ledger=list(revision_ledger), frozen_revision=frozen_revision,
                final_record=final_record,
                frozen_revision_unavailable_reason=None if frozen_revision else 'Not frozen',
                final_record_unavailable_reason=None if final_record else 'Final measurement not performed')
