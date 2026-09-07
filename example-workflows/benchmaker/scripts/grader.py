"""Independent deterministic outcome process for JSON-compatible solve APIs.

The subprocess is a fault boundary, not a security sandbox. Protected-evaluation
claims require external access isolation. This JSON profile executes only the
explicit capability-limited Python subset; unsupported source is UNVERIFIED.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time

from native import digest, read_json, run_process, write_json
from records import INFRA, require
from python_boundary import inspect_source, UnsupportedSource
from case_inputs import check_binding

RUNNER = '''import contextlib, importlib.util, json, pathlib, sys
source, boundary = sys.argv[1:]
spec = importlib.util.spec_from_file_location("trusted_boundary", boundary)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
args = json.load(sys.stdin)
try:
    with contextlib.redirect_stdout(sys.stderr):
        namespace = module.load_source(pathlib.Path(source).read_text(encoding="utf-8-sig"))
        solve = namespace.get("solve")
        if not callable(solve):
            raise RuntimeError("missing solve API")
        try:
            value = solve(*args)
            response = {"returned": True, "value": value, "exception": None, "args_after": args}
        except Exception as error:
            response = {"returned": False, "value": None, "exception": type(error).__name__, "args_after": args}
    print(json.dumps(response))
except BaseException:
    sys.exit(1)
'''


def grade(source, checks, *, timeout=5):
    """Expected values and the aggregate decision never enter the candidate process."""
    require(timeout > 0, 'grader timeout must be positive')
    specification = read_json(checks)
    require(isinstance(specification.get('checks'), list) and specification['checks'], 'empty grader checks')
    for check in specification['checks']:
        require('args' in check and ('expected' in check) != ('raises' in check), 'invalid outcome check')
    boundary = Path(__file__).with_name('python_boundary.py')
    try:
        inspect_source(Path(source).read_text(encoding='utf-8-sig'))
    except UnsupportedSource as error:
        return dict(oracle_outcome='UNVERIFIED', failure_class='unsupported_source_capabilities',
                    unsupported_reason=str(error), source_sha256=digest(source), checks_sha256=digest(checks),
                    grader_sha256=digest(__file__), boundary_sha256=digest(boundary),
                    checks_locator=str(Path(checks).resolve()), calls=[], failed_checks=[],
                    elapsed_seconds=0, exit_code=None, timed_out=False, stdout='', stderr='')
    except SyntaxError:
        pass  # Syntax errors are an ordinary candidate failure in the child.
    calls, failures = [], []
    outcome, failure = 'PASS', None
    with tempfile.TemporaryDirectory(prefix='benchmaker-grade-') as folder:
        root = Path(folder)
        (root / 'solution.py').write_bytes(Path(source).read_bytes())
        (root / 'runner.py').write_text(RUNNER, encoding='utf-8')
        deadline = time.monotonic() + timeout
        for index, check in enumerate(specification['checks']):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failures.extend(range(index, len(specification['checks'])))
                break
            result = run_process([sys.executable, '-I', str(root / 'runner.py'),
                                  str(root / 'solution.py'), str(boundary)], cwd=root,
                                 stdin=json.dumps(check['args']), timeout=remaining)
            calls.append(dict(result, stdout=result['stdout'].decode('utf-8', errors='replace'),
                              stderr=result['stderr'].decode('utf-8', errors='replace')))
            if result['launch_error']:
                outcome, failure = 'UNVERIFIED', 'grader_environment_failure'
                break
            passed = False
            if not result['timed_out'] and result['exit_code'] == 0:
                try:
                    response = json.loads(result['stdout'])
                    require(set(response) == {'returned', 'value', 'exception', 'args_after'}
                            and type(response['returned']) is bool, 'invalid call response')
                    passed = (response['returned'] and 'expected' in check and response['value'] == check['expected']) or (
                        not response['returned'] and 'raises' in check and response['exception'] == check['raises'])
                    if check.get('no_mutation') and response['args_after'] != check['args']:
                        passed = False
                except (ValueError, KeyError, TypeError):
                    pass
            if not passed:
                failures.append(index)
        if outcome != 'UNVERIFIED' and failures:
            outcome, failure = 'FAIL', 'wrong_output'
    return dict(oracle_outcome=outcome, failure_class=failure, source_sha256=digest(source),
                checks_sha256=digest(checks), grader_sha256=digest(__file__), boundary_sha256=digest(boundary),
                checks_locator=str(Path(checks).resolve()), calls=calls, failed_checks=failures,
                elapsed_seconds=sum(call['elapsed_seconds'] for call in calls),
                exit_code=calls[-1]['exit_code'], timed_out=any(call['timed_out'] for call in calls),
                stdout=calls[-1]['stdout'], stderr=calls[-1]['stderr'])


def make_record(receipt_path, checks, identity):
    receipt_path = Path(receipt_path).resolve()
    receipt = read_json(receipt_path)
    identity = dict(identity, case_binding=receipt['case_binding'], prompt_locator=receipt['prompt_locator'])
    check_binding(identity, receipt, checks)
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

    observation_path = receipt_path.parent / 'grader.json'
    write_json(observation_path, observation)
    record = dict(identity)
    record.setdefault('retry_of', None)
    for field in ('requested_command', 'resolved_command', 'requested_configuration',
                  'resolved_configuration', 'prompt_locator', 'raw_transcript_locator',
                  'result_artifact_locator', 'exit_code', 'elapsed_seconds', 'token_usage'):
        record[field] = receipt[field]
    valid = classification not in INFRA and observation['oracle_outcome'] != 'UNVERIFIED'
    record.update(classification=classification, evaluator_classification=(
                      'environment_failure' if observation['failure_class'] == 'grader_environment_failure' else
                      'unsupported' if observation['failure_class'] == 'unsupported_source_capabilities' else 'completed'), launch_receipt_locator=str(receipt_path),
                  grader_observation_locator=str(observation_path), oracle_outcome=observation['oracle_outcome'],
                  failure_class=observation['failure_class'], valid_for_estimate=valid,
                  exclusion_reason=None if valid else observation['failure_class'])
    write_json(receipt_path.parent / 'attempt.json', record)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--checks', required=True)
    parser.add_argument('--identity', required=True)
    args = parser.parse_args()
    print(json.dumps(make_record(args.receipt, args.checks, read_json(args.identity)), indent=2))
