import subprocess
import sys

PROGRAM = """
from itertools import product
from authorize import can_export

cases = 0
for role, authenticated, suspended in product(
        ('owner', 'analyst', 'viewer', 'admin', '', None, [], {}), (True, False, 1, None), (True, False, 0, None)):
    expected = role in ('owner', 'analyst') and authenticated is True and suspended is False
    actual = can_export(role, authenticated, suspended)
    assert type(actual) is bool and actual == expected, (role, authenticated, suspended, actual)
    cases += 1
print(f'{cases} independent authorization cases passed')
"""

def check(c):
    checked = subprocess.run([sys.executable, '-B', '-c', PROGRAM], cwd=c.stage(), capture_output=True, text=True, timeout=20)
    c.require(checked.returncode == 0, 'Independent behavior cases', checked.stdout + checked.stderr)
    c.require(not list(c.stage().rglob('SKILL.md')), 'Task does not create a reusable workflow', 'workspace')
