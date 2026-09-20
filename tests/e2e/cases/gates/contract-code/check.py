"""Check the public wire protocol independently of the candidate's tests."""
import subprocess
import sys

PROGRAM = r'''
import json
import sys
sys.path.insert(0, '.')
from producer import encode
from consumer import decode
for identifier in ('plain', 'a,b|c', 'a"b', 'éclair', '☀', '  spaced  '):
    payload = encode(identifier)
    assert isinstance(payload, str)
    record = json.loads(payload)
    assert isinstance(record, dict)
    assert type(record.get('version')) is int and record['version'] == 1
    assert record.get('id') == identifier
    assert decode(payload) == identifier
def rejects(fn, value):
    try:
        fn(value)
    except ValueError:
        return
    raise AssertionError(('Expected ValueError', value))
for value in ('', None, 7, True):
    rejects(encode, value)
for payload in ('oops', '[]', 'null', '1', '{}',
                '{"id":"x"}', '{"version":1}',
                '{"version":2,"id":"x"}', '{"version":true,"id":"x"}',
                '{"version":1.0,"id":"x"}', '{"version":1,"id":""}',
                '{"version":1,"id":8}'):
    rejects(decode, payload)
print('Wire protocol behavior passed')
'''


def check(c):
    for name in ('contract.md',):
        path = c.stage() / name
        c.require(path.is_file() and bool(path.read_text(encoding='utf-8').strip()),
                  'Deliver the settled protocol contract', str(path))
    try:
        result = subprocess.run([sys.executable, '-I', '-B', '-c', PROGRAM], cwd=c.stage(),
                                capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15)
    except subprocess.TimeoutExpired:
        c.require(False, 'Protocol behavior finishes within the check budget', '15 second timeout')
        return
    c.require(result.returncode == 0, 'Independent public protocol behavior',
              result.stdout + result.stderr)
