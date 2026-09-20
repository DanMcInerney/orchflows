"""Check both delivered modules; the native audit establishes review/fix order."""
import subprocess
import sys

PROGRAM = '''
import sys
sys.path.insert(0, 'repaired')
from fees import annual_cost
from eligibility import eligible
assert annual_cost(10, None) is None
assert annual_cost(10, 0) == 120
assert annual_cost(10, 5) == 125
assert annual_cost(0, 5) == 5
assert eligible(None, 100, False) is False
assert eligible(None, 100, True) is None
assert eligible(100, 100, True) is True
assert eligible(101, 100, True) is False
assert eligible(99, 100, False) is False
print('Both repaired modules passed')
'''


def check(c):
    try:
        result = subprocess.run([sys.executable, '-I', '-B', '-c', PROGRAM], cwd=c.stage(),
                                capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        c.require(False, 'Repaired behavior finishes within the check budget', '15 second timeout')
        return
    c.require(result.returncode == 0, 'Repair all specified behavior across both modules',
              result.stdout + result.stderr)
    path = c.stage() / 'checks.md'
    c.require(path.is_file() and bool(path.read_text(encoding='utf-8').strip()),
              'Deliver affected-check evidence', str(path))
