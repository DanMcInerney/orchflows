"""Discover cases and resolve their explicit package dependencies."""
from dataclasses import dataclass
from pathlib import Path
import re

from common import HERE, ROOT, orchflows, read_json

FIELDS = {'entrypoint', 'packages', 'covers', 'requires', 'timeout_seconds', 'profile', 'writable_inputs'}


@dataclass(frozen=True)
class Case:
    id: str
    path: Path
    config: dict

    @property
    def timeout(self):
        return self.config.get('timeout_seconds', 150)


def discover(extra_roots=()):
    roots = [('core', HERE / 'cases')]
    roots += [(p.name, p / 'trials') for p in sorted((ROOT / 'example-workflows').iterdir()) if p.is_dir()]
    roots += [(Path(p).name, Path(p).resolve()) for p in extra_roots]
    cases = {}
    for prefix, root in roots:
        for manifest in sorted(root.rglob('case.json')):
            config = read_json(manifest)
            if not isinstance(config, dict) or set(config) - FIELDS:
                raise ValueError(f'Unknown case fields: {manifest}')
            suffix = manifest.parent.relative_to(root).as_posix()
            identifier = prefix + (('/' + suffix) if suffix != '.' else '')
            if identifier in cases or not re.fullmatch(r'[a-zA-Z0-9_/-]+', identifier):
                raise ValueError(f'Duplicate or invalid case ID: {identifier}')
            for key in ('packages', 'covers', 'requires', 'writable_inputs'):
                values = config.get(key, [])
                if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
                    raise ValueError(f'{identifier}: {key} must be a list of strings')
                if len(values) != len(set(values)):
                    raise ValueError(f'{identifier}: duplicate {key}')
            if not config.get('packages'):
                raise ValueError(f'{identifier}: declare packages explicitly')
            seconds = config.get('timeout_seconds', 150)
            if type(seconds) not in (int, float) or not 0 < seconds <= 3600:
                raise ValueError(f'{identifier}: invalid timeout_seconds')
            if config.get('profile', 'local') not in ('local', 'authoring', 'no-review'):
                raise ValueError(f'{identifier}: unsupported profile')
            if 'entrypoint' in config and (not isinstance(config['entrypoint'], str) or
                    not re.fullmatch(r'[\w-]+:[\w-]+', config['entrypoint'])):
                raise ValueError(f'{identifier}: invalid entrypoint')
            for required in ('request.md', 'expected-behavior.md'):
                if not (manifest.parent / required).is_file():
                    raise ValueError(f'{identifier}: missing {required}')
            cases[identifier] = Case(identifier, manifest.parent, config)
    return cases


def select(cases, suite=None, identifiers=()):
    names = list(identifiers)
    if suite or not names:
        suite = suite or 'smoke'
        if not re.fullmatch(r'[\w-]+', suite):
            raise ValueError('Invalid suite name')
        for line in (HERE / 'suites' / (suite + '.txt')).read_text().splitlines():
            line = line.partition('#')[0].strip()
            if line:
                names.append(line)
    unknown = set(names) - cases.keys()
    if unknown:
        raise ValueError('Unknown cases: ' + ', '.join(sorted(unknown)))
    return sorted((cases[n] for n in dict.fromkeys(names)), key=lambda c: (-c.timeout, c.id))


def _named(paths, sources=None):
    sources = {} if sources is None else sources
    for path in paths:
        if path.is_dir() and (path / 'plugin.json').is_file():
            name = orchflows._manifest(path)['name']
            if name in sources and sources[name] != path.resolve():
                raise ValueError(f'Duplicate package source: {name}')
            sources[name] = path.resolve()
    return sources


def _defaults():
    return _named([ROOT, *sorted((ROOT / 'example-workflows').iterdir())])


def overrides(extra_roots=()):
    """Default package roots that an explicit --package-root with the same name replaces."""
    defaults = _defaults()
    return {name: {'default': str(defaults[name]), 'explicit': str(path)}
            for name, path in _named(map(Path, extra_roots)).items() if name in defaults and defaults[name] != path}


def packages_for(case, extra_roots=()):
    # Explicit roots win over defaults so matched trials can run old and new packages from one harness.
    sources = {**_defaults(), **_named(map(Path, extra_roots))}
    if (case.path / 'packages').is_dir():
        _named(sorted((case.path / 'packages').iterdir()), sources)
    missing = set(case.config['packages']) - sources.keys()
    if missing:
        raise ValueError('Missing package roots: ' + ', '.join(sorted(missing)))
    return {name: sources[name] for name in case.config['packages']}
