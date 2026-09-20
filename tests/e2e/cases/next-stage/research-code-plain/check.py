"""Exercise current exports independently of generated candidate tests."""
import re
import subprocess
import sys


PROGRAM = r'''
from copy import deepcopy
import sys
sys.path.insert(0, '.')
from atlas import normalize as a
from beacon import normalize as b
count = 0
def expect(fn, record, identifier, elapsed, outcome):
    global count
    before = deepcopy(record)
    actual = fn(record)
    assert actual == dict(id=identifier, elapsed_ms=elapsed, outcome=outcome), actual
    assert type(actual['elapsed_ms']) is int and type(actual['id']) is str, actual
    assert record == before, ('input mutated', before, record)
    count += 1
for identifier in ('0017', '  spaced  ', 'éclair'):
    for duration, milliseconds in [('1.250', 1250), ('0', 0), ('1e-3', 1),
                                   ('9007199254740.993', 9007199254740993)]:
        for result, outcome in [('passed', 'success'), ('failed', 'failure')]:
            expect(a, dict(ref=identifier, timing={'seconds': duration, 'extra': 1},
                           result=result, unused='ignored'), identifier, milliseconds, outcome)
    for duration, milliseconds in [(1250000, 1250), (0, 0), (1000, 1),
                                   (9007199254740993000, 9007199254740993)]:
        for state, outcome in [('complete', 'success'), ('error', 'failure')]:
            expect(b, dict(key=identifier, elapsed=duration, state=state, unused='ignored'),
                   identifier, milliseconds, outcome)
valid_a = dict(ref='0017', timing={'seconds': '1.250'}, result='passed')
valid_b = dict(key='0017', elapsed=1250000, state='complete')
bad = [(a, {**valid_a, 'timing': {'seconds': value}}) for value in
       ('-1', '0.0001', 'NaN', 'Infinity', '-Infinity', 'nonsense', '', None, True, 1.25)]
bad += [(a, {**valid_a, 'result': value}) for value in ('done', 'success', True, None)]
bad += [(a, {**valid_a, 'timing': value}) for value in ({}, None, [], '1.25')]
bad += [(b, {**valid_b, 'elapsed': value}) for value in
        (-1000, 999, True, False, '1000', 1000.0, None)]
bad += [(b, {**valid_b, 'state': value}) for value in ('done', 'ok', 'failed', True, None)]
for fn, valid, id_key in ((a, valid_a, 'ref'), (b, valid_b, 'key')):
    bad += [(fn, {**valid, id_key: value}) for value in ('', 17, True, None)]
    bad += [(fn, {key: value for key, value in valid.items() if key != missing}) for missing in valid]
    bad += [(fn, value) for value in (None, [], 'record')]
bad += [(a, dict(id=17, elapsed_ms=1250, ok=True)),
        (a, dict(identifier='0017', duration_ns=1250000000, result='passed')),
        (b, dict(key='0017', elapsed=1250, state='ok'))]
for fn, record in bad:
    before = deepcopy(record)
    try:
        fn(record)
    except ValueError:
        pass
    else:
        raise AssertionError(('Expected ValueError', record))
    assert record == before, ('invalid input mutated', before, record)
    count += 1
print(str(count) + ' independent adapter behavior cases passed')
'''


def execute(c, arguments, requirement):
    try:
        result = subprocess.run([sys.executable, '-I', '-B', *arguments], cwd=c.stage(),
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20)
    except subprocess.TimeoutExpired:
        c.require(False, requirement, '20 second local check timeout')
        return None
    c.require(result.returncode == 0, requirement, result.stdout + result.stderr)
    return result


def check(c):
    path = c.stage() / 'research.md'
    c.require(path.is_file() and bool(path.read_text(encoding='utf-8').strip()),
              'Deliver applicable-format research and source references', str(path))
    execute(c, ['-c', PROGRAM], 'Independent current-format and rejection behavior')
    tests = c.stage() / 'tests'
    present = tests.is_dir() and any(tests.rglob('test*.py'))
    c.require(present, 'Deliver executable candidate unittest tests', str(tests))
    if present:
        # -I excludes cwd; add it explicitly so both adapters import under any host.
        runner = "import sys,unittest; sys.path.insert(0,'.'); unittest.main(module=None, argv=['unittest','discover','-s','tests','-v'])"
        result = execute(c, ['-c', runner], 'Candidate unittest suite succeeds')
        if result is not None:
            c.require(bool(re.search(r'Ran [1-9]\d* tests?\b', result.stdout + result.stderr)),
                      'Candidate unittest discovery runs at least one test', result.stdout + result.stderr)
