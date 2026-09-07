"""Fixed artifact and journal linkage for the package's disposable admission probe."""
from pathlib import Path
import re

from native import run_process
from records import require


def git_revision(repository, revision='HEAD'):
    result = run_process(['git', 'rev-parse', '--verify', revision + '^{commit}'],
                         cwd=repository, timeout=10)
    require(result['exit_code'] == 0 and not result['timed_out'], 'unresolved git revision')
    return result['stdout'].decode('ascii').strip()


def check_runtime(root, runtime, components):
    for key in ('run', 'frame', 'tickets', 'standard_pins', 'artifacts', 'findings',
                'package_revision', 'journal_locators'):
        require(runtime.get(key), 'missing runtime provenance: ' + key)
    require({'maker', 'judge'} <= runtime['standard_pins'].keys(), 'missing shared maker/judge pins')
    require(runtime['standard_pins']['maker'] == runtime['standard_pins']['judge'], 'maker/judge pins differ')
    require(re.fullmatch(r'[0-9a-f]{40}', runtime['package_revision']) is not None, 'package revision must be full git commit')
    require(git_revision(root / 'source') == runtime['package_revision'], 'source checkout differs from package revision')
    journals = '\n'.join(Path(path).read_text(encoding='utf-8-sig') for path in runtime['journal_locators'])
    for identity in [runtime['run'], runtime['frame'], *runtime['tickets']]:
        require(str(identity) in journals, 'runtime identity absent from journals: ' + str(identity))
    for pin in runtime['standard_pins']['maker']:
        require(pin in journals, 'standard pin absent from journals')
    required = {'benchmark-construct', 'benchmark-qualify', 'benchmark-calibrate',
                'benchmark-quality', 'benchmark-evidence'}
    require(set(components) >= required, 'missing package components')
    for name in required:
        path = Path(components[name]).resolve()
        require(path.is_relative_to(root / 'product') and path.is_file(), 'unresolved package component')
        text = path.read_text(encoding='utf-8-sig')
        require(re.search(r'^name:\s*' + re.escape(name) + r'\s*$', text, re.MULTILINE), 'component name does not resolve')


def check_revision(root, revision):
    require(isinstance(revision, str) and re.fullmatch(r'[0-9a-f]{40}', revision), 'benchmark revision must be full git commit')
    require(git_revision(root / 'product', revision) == revision, 'benchmark revision unavailable in product')


def check_manifest_revision(root, manifest, revision):
    relative = Path(manifest).resolve().relative_to(root / 'product').as_posix()
    committed = run_process(['git', 'rev-parse', revision + ':' + relative], cwd=root / 'product', timeout=10)
    current = run_process(['git', 'hash-object', '--path', relative, str(manifest)], cwd=root / 'product', timeout=10)
    require(committed['exit_code'] == current['exit_code'] == 0 and committed['stdout'] == current['stdout'],
            'landed manifest differs from measured git revision')
