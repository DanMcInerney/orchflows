"""Local evidence and package operations; no native execution."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import orchflows


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def snapshot(root):
    root = Path(root)
    result = {}
    for path in sorted(root.rglob('*')):
        if orchflows._is_link(path):
            raise ValueError(f'Evidence must not follow links: {path}')
        if path.is_file() and '__pycache__' not in path.parts:
            result[path.relative_to(root).as_posix()] = digest(path)
    return result


def copy_package(source, destination):
    source, destination = Path(source), Path(destination)
    identity = orchflows._manifest(source)
    destination.mkdir(parents=True, exist_ok=False)
    excluded = []
    for path in orchflows._files(source, core=identity['name'] == 'orchflows'):
        relative = path.relative_to(source)
        if any(part in {'trials', 'tests', 'node_modules', '.venv'} for part in relative.parts):
            excluded.append(relative.as_posix())
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return {**identity, 'source': str(source), 'path': str(destination), 'excluded': excluded,
            'files': snapshot(destination)}


def load_hook(path):
    path = Path(path)
    name = 'e2e_hook_' + hashlib.sha256(str(path).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def files_under(root):
    """Copyable fixtures: reject links before shutil traverses them."""
    snapshot(root)
    return Path(root)
