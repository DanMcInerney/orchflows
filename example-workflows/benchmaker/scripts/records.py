"""Finite-suite estimates over declared cases; no orchestration or population claim."""
import math
from pathlib import Path


class EvidenceError(ValueError):
    """An evidence contract is absent or inconsistent."""


REQUIRED = {
    'case_id', 'split', 'round', 'trial', 'target_configuration', 'case_binding',
    'benchmark_revision', 'candidate_kind', 'requested_command',
    'resolved_command', 'requested_configuration', 'resolved_configuration',
    'prompt_locator', 'raw_transcript_locator', 'result_artifact_locator',
    'launch_receipt_locator', 'grader_observation_locator', 'classification',
    'exit_code', 'elapsed_seconds', 'token_usage', 'oracle_outcome',
    'failure_class', 'valid_for_estimate', 'exclusion_reason', 'evaluator_classification', 'retry_of',
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
    configuration_gaps(record['resolved_configuration'], config, policy)
    require(record['requested_command'] and record['resolved_command'], 'missing native command')
    require(record['classification'] in INFRA | TARGET, 'unknown classification')
    require(type(record['valid_for_estimate']) is bool, 'validity must be boolean')
    require(record['oracle_outcome'] in {'PASS', 'FAIL', 'UNVERIFIED'}, 'unknown oracle outcome')
    require(isinstance(record['elapsed_seconds'], (int, float)) and math.isfinite(record['elapsed_seconds'])
            and record['elapsed_seconds'] >= 0, 'invalid elapsed time')
    if record['classification'] in INFRA:
        require(not record['valid_for_estimate'] and record['oracle_outcome'] == 'UNVERIFIED',
                'infrastructure counted as target outcome')
    require(record['evaluator_classification'] in {'completed', 'environment_failure', 'unsupported'}, 'unknown evaluator classification')
    if record['evaluator_classification'] == 'unsupported':
        require(not record['valid_for_estimate'] and record['oracle_outcome'] == 'UNVERIFIED'
                and record['failure_class'] == 'unsupported_source_capabilities', 'unsupported source counted')
    if record['evaluator_classification'] == 'environment_failure':
        require(not record['valid_for_estimate'] and record['oracle_outcome'] == 'UNVERIFIED'
                and record['failure_class'] == 'grader_environment_failure', 'grader infrastructure counted')
    if record['valid_for_estimate']:
        require(not record['exclusion_reason'] and record['oracle_outcome'] in {'PASS', 'FAIL'},
                'counted attempt lacks outcome or carries exclusion')
    else:
        require(bool(record['exclusion_reason']), 'unexplained exclusion')
    if record['classification'] in {'candidate_failure', 'task_timeout'}:
        require(record['valid_for_estimate'] and record['oracle_outcome'] == 'FAIL',
                'genuine candidate failure excluded')


def configuration_gaps(resolved, requested, policy):
    require(isinstance(resolved, dict) and resolved, 'missing resolved configuration evidence')
    optional = set(policy.get('optional_configuration_fields', []))
    required = set(policy.get('required_configuration_fields', []))
    require(not optional & required, 'ambiguous configuration metadata policy')
    gaps, optional_gaps = [], []

    def walk(wanted, actual, path):
        if actual is None or (isinstance(actual, dict) and 'unavailable_reason' in actual):
            reason = 'not observed' if actual is None else actual['unavailable_reason']
            require(bool(reason), 'empty configuration gap')
            is_required = any(path == field or path.startswith(field + '.') for field in required)
            is_optional = any(path == field or path.startswith(field + '.') for field in optional)
            destination = optional_gaps if not is_required and (is_optional or
                not policy.get('require_resolved_configuration', True)) else gaps
            destination.append('resolved_configuration.' + path + ': ' + str(reason))
            return
        if isinstance(wanted, dict) and 'unavailable_reason' in wanted:
            # A requested placeholder is not an observation, even when copied verbatim.
            walk(None, {'unavailable_reason': wanted['unavailable_reason']}, path)
        elif isinstance(wanted, dict):
            require(isinstance(actual, dict), 'wrong resolved configuration: ' + path)
            for key, value in wanted.items():
                walk(value, actual.get(key), (path + '.' + key).strip('.'))
        elif isinstance(wanted, list):
            require(isinstance(actual, list) and len(actual) == len(wanted), 'wrong resolved configuration: ' + path)
            for index, value in enumerate(wanted):
                walk(value, actual[index], path + '.' + str(index))
        else:
            require(actual == wanted, 'wrong resolved configuration: ' + path)

    if 'unavailable_reason' in resolved:
        for key in requested:
            walk(requested[key], resolved.get(key, {'unavailable_reason': resolved['unavailable_reason']}), key)
    else:
        walk(requested, resolved, '')
    for path in required:
        actual, wanted = resolved, requested
        reason = None
        for key in path.split('.'):
            if isinstance(actual, dict) and 'unavailable_reason' in actual:
                reason = actual['unavailable_reason']
            actual = actual.get(key) if isinstance(actual, dict) else None
            wanted = wanted.get(key) if isinstance(wanted, dict) else None
        if wanted is None:
            reason = 'required field absent from pinned configuration'
        elif actual is None:
            reason = reason or 'required field not observed'
        elif isinstance(actual, dict) and 'unavailable_reason' in actual:
            reason = actual['unavailable_reason']
        if reason:
            gaps.append('resolved_configuration.' + path + ': ' + str(reason))
    return gaps, optional_gaps


def check_retries(records, policy):
    count = policy['trials_per_case']
    retries = 0
    for case in policy['case_ids']:
        attempts = sorted((r for r in records if r['case_id'] == case and r['candidate_kind'] == 'agent_attempt'),
                          key=lambda r: r['trial'])
        prior, replaced = {}, set()
        for record in attempts:
            predecessor = record['retry_of']
            if record['trial'] <= count:
                require(predecessor is None, 'primary sample cannot be a retry')
            else:
                require(type(predecessor) is int and predecessor in prior and predecessor not in replaced,
                        'extra attempt lacks unique infrastructure predecessor')
                original = prior[predecessor]
                require(not original['valid_for_estimate'] and (original['classification'] in INFRA or
                        original['evaluator_classification'] == 'environment_failure'), 'retry predecessor is not infrastructure')
                replaced.add(predecessor)
                retries += 1
            prior[record['trial']] = record
        require(sum(r['valid_for_estimate'] for r in attempts) <= count, 'undeclared extra valid trials')
    require(retries <= policy.get('infrastructure_retry_budget', 0), 'global infrastructure retry budget exceeded')


def wilson(passes, count):
    if not count:
        return None
    z = 1.959963984540054
    p = passes / count
    denominator = 1 + z * z / count
    center = (p + z * z / (2 * count)) / denominator
    radius = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / denominator
    return [center - radius, center + radius]


def summarize(records, policy, *, criterion_gaps=(), validity='VALID'):
    require(validity in {'VALID', 'INVALID', 'UNVERIFIED'}, 'unknown qualification validity')
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
        required_gaps, available_gaps = configuration_gaps(record['resolved_configuration'], policy['target_configuration'], policy)
        gaps.extend(required_gaps)
        optional_gaps.extend(available_gaps)
    check_retries(records, policy)
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
    decision = ('INVALID' if validity == 'INVALID' else 'UNVERIFIED' if validity == 'UNVERIFIED' or gaps or estimate is None
                else 'OUT_OF_BAND' if band == 'OUT_OF_BAND' else 'CALIBRATED')
    return dict(validity=validity, benchmark_revision=next(iter(revisions)), target_configuration=policy['target_configuration'],
                split=policy['split'], round=policy['round'], policy=policy,
                attempt_locators=[str(Path(record['launch_receipt_locator']).with_name('attempt.json')) for record in records],
                estimator='weighted mean of per-case isolated-trial success rates (pass@1)',
                weights=weights, independent_unit='case; repeated trials are conditional observations',
                per_case=per_case, distinct_cases=len(ids), total_attempts=attempted,
                estimate=estimate, interval=None,
                interval_unavailable_reason='Purposively selected finite suite; no population sampling model',
                band_observation=band, decision=decision, criterion_gaps=sorted(set(gaps)),
                optional_gaps=sorted(set(optional_gaps)),
                snapshot_kind='immutable-round-observation')
