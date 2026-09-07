"""Independent deterministic outcome process for JSON-compatible solve APIs.

The subprocess is a fault boundary, not a security sandbox. Protected-evaluation
claims require external access isolation; arbitrary candidate code has host access.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile

from native import digest, read_json, run_process, write_json
from records import INFRA, require

RUNNER = '''import copy, json, runpy, sys
source, checks = sys.argv[1:]
spec = json.load(open(checks, encoding="utf-8-sig"))
try:
    solve = runpy.run_path(source)["solve"]
    failures = []
    for index, check in enumerate(spec["checks"]):
        args = copy.deepcopy(check["args"])
        before = copy.deepcopy(args)
        try:
            value = solve(*args)
            passed = "raises" not in check and json.loads(json.dumps(value)) == check["expected"]
        except Exception as error:
            passed = type(error).__name__ == check.get("raises")
        if check.get("no_mutation") and args != before:
            passed = False
        if not passed:
            failures.append(index)
    print(json.dumps({"outcome": "FAIL" if failures else "PASS", "failed_checks": failures}))
except BaseException as error:
    print(json.dumps({"outcome": "FAIL", "failure_class": type(error).__name__}))
'''


def grade(source, checks, *, timeout=5):
    specification = read_json(checks)
    require(isinstance(specification.get('checks'), list) and specification['checks'], 'empty grader checks')
    for check in specification['checks']:
        require('args' in check and ('expected' in check) != ('raises' in check), 'invalid outcome check')
    with tempfile.TemporaryDirectory(prefix='benchmaker-grade-') as folder:
        root = Path(folder)
        (root / 'solution.py').write_bytes(Path(source).read_bytes())
        write_json(root / 'checks.json', specification)
        (root / 'runner.py').write_text(RUNNER, encoding='utf-8')
        result = run_process([sys.executable, '-I', str(root / 'runner.py'),
                              str(root / 'solution.py'), str(root / 'checks.json')], cwd=root, timeout=timeout)
    if result['launch_error']:
        outcome, failure = 'UNVERIFIED', 'grader_environment_failure'
    elif result['timed_out']:
        outcome, failure = 'FAIL', 'grader_timeout'
    elif result['exit_code'] != 0:
        outcome, failure = 'FAIL', 'candidate_process_failure'
    else:
        try:
            parsed = json.loads(result['stdout'])
            require(parsed['outcome'] in {'PASS', 'FAIL'}, 'invalid grader output')
            outcome, failure = parsed['outcome'], parsed.get('failure_class', 'wrong_output' if parsed['outcome'] == 'FAIL' else None)
        except (ValueError, KeyError):
            outcome, failure = 'FAIL', 'candidate_output_interference'
    return dict(oracle_outcome=outcome, failure_class=failure, source_sha256=digest(source),
                checks_sha256=digest(checks), grader_sha256=digest(__file__),
                checks_locator=str(Path(checks).resolve()), elapsed_seconds=result['elapsed_seconds'],
                exit_code=result['exit_code'], timed_out=result['timed_out'],
                stdout=result['stdout'].decode('utf-8', errors='replace'),
                stderr=result['stderr'].decode('utf-8', errors='replace'))


def make_record(receipt_path, checks, identity):
    receipt_path = Path(receipt_path).resolve()
    receipt = read_json(receipt_path)
    classification = receipt['classification']
    source = receipt['result_artifact_locator']
    if classification in INFRA:
        observation = dict(oracle_outcome='UNVERIFIED', failure_class=classification,
                           checks_locator=str(Path(checks).resolve()), checks_sha256=digest(checks))
    elif classification in {'task_timeout', 'candidate_failure'}:
        observation = dict(oracle_outcome='FAIL', failure_class=classification,
                           checks_locator=str(Path(checks).resolve()), checks_sha256=digest(checks))
    else:
        observation = grade(source, checks)
        if observation['oracle_outcome'] == 'UNVERIFIED':
            classification = 'environment_failure'
    observation_path = receipt_path.parent / 'grader.json'
    write_json(observation_path, observation)
    record = dict(identity)
    for field in ('requested_command', 'resolved_command', 'requested_configuration',
                  'resolved_configuration', 'prompt_locator', 'raw_transcript_locator',
                  'result_artifact_locator', 'exit_code', 'elapsed_seconds', 'token_usage'):
        record[field] = receipt[field]
    record.update(classification=classification, launch_receipt_locator=str(receipt_path),
                  grader_observation_locator=str(observation_path), oracle_outcome=observation['oracle_outcome'],
                  failure_class=observation['failure_class'], valid_for_estimate=classification not in INFRA,
                  exclusion_reason=classification if classification in INFRA else None)
    write_json(receipt_path.parent / 'attempt.json', record)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--checks', required=True)
    parser.add_argument('--identity', required=True)
    args = parser.parse_args()
    print(json.dumps(make_record(args.receipt, args.checks, read_json(args.identity)), indent=2))
