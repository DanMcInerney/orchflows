import subprocess
import sys

PROGRAM = """
from vendor_a import normalize as a
from vendor_b import normalize as b
def expect(fn, record, milliseconds, outcome):
    actual = fn(record)
    assert actual == dict(id='0017', elapsed_ms=milliseconds, outcome=outcome), actual
    assert type(actual['elapsed_ms']) is int, actual
for duration, milliseconds in [('1.250', 1250), ('0', 0), ('0.001', 1)]:
    for ok in (True, False):
        expect(a, dict(id='0017', duration=duration, ok=ok), milliseconds, 'success' if ok else 'failure')
for duration, milliseconds in [(1250000, 1250), (0, 0), (1000, 1)]:
    for state in ('done', 'error'):
        expect(b, dict(key='0017', elapsed=duration, state=state), milliseconds, 'success' if state == 'done' else 'failure')
bad = [(a, dict(id='0017', duration=value, ok=True)) for value in ('-1', '0.0001')]
bad += [(a, dict(id='0017', duration='1', ok='yes'))]
bad += [(b, dict(key='0017', elapsed=value, state='done')) for value in (-1000, 999)]
bad += [(b, dict(key='0017', elapsed=1000, state=value)) for value in ('ok', 'failed')]
for fn, record in bad:
    try:
        fn(record)
    except ValueError:
        pass
    else:
        raise AssertionError(('Expected ValueError', record))
print('19 independent adapter cases passed')
"""

def check(c):
    checked = subprocess.run([sys.executable, '-B', '-c', PROGRAM], cwd=c.stage(), capture_output=True, text=True, timeout=20)
    c.require(checked.returncode == 0, 'Independent behavior cases', checked.stdout + checked.stderr)
    before = c.json(c.root / 'stages/target/before.json')['inputs']
    created = sorted(path.relative_to(c.stage()).as_posix() for path in c.stage().rglob('SKILL.md')
                     if path.is_file() and path.relative_to(c.stage()).as_posix() not in before)
    c.require(not created, 'Task does not create a reusable workflow',
              '; '.join(created) or 'stages/target/before.json: no new SKILL.md files')
