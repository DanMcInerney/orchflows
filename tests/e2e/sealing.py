"""Detect changes to frozen execution evidence; audits are append-only additions."""
from common import read_json, snapshot, write_json


def execution_files(root):
    return {name: value for name, value in snapshot(root).items()
            if not name.startswith('audits/') and name not in {'report.json', 'seal.json'}}


def seal(root):
    path = root / 'seal.json'
    if path.exists():
        raise ValueError('Execution evidence is already sealed')
    write_json(path, {'files': execution_files(root)})


def verify(root):
    path = root / 'seal.json'
    if not path.is_file():
        return ['Execution evidence has no frozen identity']
    expected, actual = read_json(path)['files'], execution_files(root)
    changed = sorted(name for name in expected.keys() | actual.keys() if expected.get(name) != actual.get(name))
    return ['Execution evidence changed: ' + name for name in changed]
