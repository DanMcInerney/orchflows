import subprocess
import sys

from common import read_json

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
    # Supplied inputs, including Codex's package copies under .agents/, are in the pre-run snapshot.
    before = read_json(c.stage().parent / 'before.json')['inputs']
    created = sorted(path.relative_to(c.stage()).as_posix() for path in c.stage().rglob('SKILL.md')
                     if path.is_file() and path.relative_to(c.stage()).as_posix() not in before)
    c.require(not created, 'Task does not create a reusable workflow',
              '; '.join(created) or 'stages/target/before.json: no new SKILL.md files')
