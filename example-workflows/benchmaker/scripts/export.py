"""Export an already committed record subtree without changing its absolute locators."""
import argparse
from pathlib import Path

from native import write_json
from provenance import git_revision, tree_files
from records import require


def export_records(repository, revision, records, destination):
    repository, destination = Path(repository).resolve(), Path(destination).resolve()
    relative = Path(records)
    require(not relative.is_absolute() and '..' not in relative.parts and relative.parts,
            'records must name one repository-relative subtree')
    require(not destination.is_relative_to(repository), 'export must be outside integration repository')
    revision = git_revision(repository, revision)
    files = tree_files(repository, revision, relative.as_posix())
    # Preflight every existing byte before publishing anything; exports are immutable.
    for name, data in files.items():
        target = (destination / name).resolve()
        require(target.is_relative_to(destination), 'record path escapes export')
        require(not target.exists() or target.read_bytes() == data, 'external export differs: ' + name)
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(data)
    return dict(artifact='git:' + revision, records=relative.as_posix(), locator=str(destination), files=len(files))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repository', 'revision', 'records', 'destination'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    import json
    print(json.dumps(export_records(args.repository, args.revision, args.records, args.destination), indent=2))
