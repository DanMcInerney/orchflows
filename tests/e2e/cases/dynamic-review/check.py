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


def delegation(c):
    """Target-stage agents from the harness evidence index: the root's children, and any deeper agents."""
    index = read_json(c.stage().parent / 'evidence/index.json')
    if index.get('gaps'):
        raise RuntimeError('Native agent discovery incomplete: ' + str(index['gaps']))
    root = index['root_id']
    children = [a['id'] for a in index['agents'] if a.get('parent_id') == root]
    nested = [a['id'] for a in index['agents'] if a['id'] != root and a.get('parent_id') != root]
    return children, nested, f'stages/target/evidence/index.json: children {len(children)}, nested {nested}'


def check(c):
    checked = subprocess.run([sys.executable, '-B', '-c', PROGRAM], cwd=c.stage(), capture_output=True, text=True, timeout=20)
    c.require(checked.returncode == 0, 'Independent behavior cases', checked.stdout + checked.stderr)
    # Supplied inputs, including Codex's package copies under .agents/, are in the pre-run snapshot.
    before = read_json(c.stage().parent / 'before.json')['inputs']
    created = sorted(path.relative_to(c.stage()).as_posix() for path in c.stage().rglob('SKILL.md')
                     if path.is_file() and path.relative_to(c.stage()).as_posix() not in before)
    c.require(not created, 'Task does not create a reusable workflow',
              '; '.join(created) or 'stages/target/before.json: no new SKILL.md files')
    children, nested, evidence = delegation(c)
    c.require(1 <= len(children) <= 2, 'Launch the required reviewer within the two-child bound', evidence)
    c.require(not nested, 'Only the coordinator launches agents', evidence)
