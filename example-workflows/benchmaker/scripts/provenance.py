"""Git-backed package, journal and frozen-tree bindings for disposable admission."""
from pathlib import Path
import re
import sys

from native import digest, run_process
from records import require


def git(repository, *arguments):
    result = run_process(['git', *arguments], cwd=repository, timeout=20)
    require(result['exit_code'] == 0 and not result['timed_out'], 'unresolved git evidence: ' + ' '.join(arguments))
    return result['stdout']


def git_revision(repository, revision='HEAD'):
    return git(repository, 'rev-parse', '--verify', revision + '^{commit}').decode('ascii').strip()


def tree_files(repository, revision, relative):
    prefix = relative.rstrip('/') + '/'
    names = git(repository, 'ls-tree', '-r', '--name-only', revision, '--', relative).decode('utf-8').splitlines()
    require(names, 'empty committed tree: ' + relative)
    return {name[len(prefix):]: git(repository, 'show', revision + ':' + name) for name in names}


def normalized(data):
    try:
        return data.decode('utf-8').replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
    except UnicodeError:
        return data


def compare_tree(directory, committed, *, caches=False):
    actual = {path.relative_to(directory).as_posix(): path for path in directory.rglob('*')
              if path.is_file() and not (caches and {'__pycache__', 'node_modules'} & set(path.relative_to(directory).parts))}
    require(set(actual) == set(committed), 'committed file inventory differs: ' + str(directory))
    for name, data in committed.items():
        require(normalized(actual[name].read_bytes()) == normalized(data), 'committed bytes differ: ' + name)
    return actual


def journal_fields(path):
    text = Path(path).read_text(encoding='utf-8-sig')
    require(text.startswith('---\n') and '## Report' in text, 'missing journal frontmatter or Report')
    header = text.split('---', 2)[1]
    fields = dict(re.findall(r'^([a-z_]+):\s*(.*?)\s*$', header, re.MULTILINE))
    return fields, text


def check_runtime(root, runtime, components):
    for key in ('run', 'frame', 'tickets', 'standard_pins', 'artifacts', 'findings',
                'package_revision', 'journal_locators', 'workflow_digest'):
        require(runtime.get(key), 'missing runtime provenance: ' + key)
    require({'maker', 'judge'} <= runtime['standard_pins'].keys(), 'missing shared maker/judge pins')
    require(runtime['standard_pins']['maker'] == runtime['standard_pins']['judge'], 'maker/judge pins differ')
    require(re.fullmatch(r'[0-9a-f]{40}', runtime['package_revision']) is not None, 'package revision must be full git commit')
    require(git_revision(root / 'source') == runtime['package_revision'], 'source checkout differs from package revision')
    git(root / 'source', 'diff', '--exit-code', 'HEAD')
    relative = 'example-workflows/benchmaker'
    committed = tree_files(root / 'source', runtime['package_revision'], relative)
    invoked = root / 'product' / '.orchflows' / 'workflows' / 'benchmaker'
    compare_tree(invoked, committed, caches=True)
    # Reuse the canonical pin owner; no package-owned competing digest scheme.
    result = run_process([sys.executable, '-c',
        'from scripts.tickets_pins import tree_digest; import sys; print(tree_digest("workflow", sys.argv[1]))',
        str(invoked)], cwd=root / 'source', timeout=20)
    require(result['exit_code'] == 0, 'canonical workflow pin unavailable')
    require(result['stdout'].decode().strip() == runtime['workflow_digest'], 'runtime package pin differs')
    journals = [journal_fields(path) for path in runtime['journal_locators']]
    for identity in [runtime['frame'], *runtime['tickets']]:
        matches = [(fields, body) for fields, body in journals if fields.get('id') == identity and fields.get('run') == runtime['run']]
        require(len(matches) == 1, 'runtime identity absent from journals: ' + identity)
        fields, _ = matches[0]
        require(fields.get('workflow') == 'benchmaker' and fields.get('workflow_digest') == runtime['workflow_digest'], 'journal package binding differs')
        if identity in runtime['tickets']:
            pins = {value.strip() for value in fields.get('standards', '').strip('[]').split(',')}
            require(set(runtime['standard_pins']['maker']) <= pins, 'standard pin absent from journal')
    lines = {line.strip() for _, body in journals for line in body.split('## Report', 1)[-1].splitlines()}
    for artifact in runtime['artifacts']:
        require(re.fullmatch(r'git:[0-9a-f]{40}', artifact), 'unresolved artifact identity')
        check_revision(root, artifact[4:])
        require('artifact: ' + artifact in lines, 'artifact absent from journal return')
    for finding in runtime['findings']:
        if isinstance(finding, dict):
            identity, locator = finding['identity'], finding['locator']
            require(digest(locator) == finding['sha256'], 'findings export changed')
        else:
            identity = locator = finding
        require(Path(locator).is_file() and 'findings: ' + identity in lines, 'unresolved findings return')
    required = {'benchmark-construct', 'benchmark-qualify', 'benchmark-calibrate',
                'benchmark-quality', 'benchmark-evidence'}
    require(set(components) >= required, 'missing package components')
    for name in required:
        kind, filename = ('standards', 'STANDARD.md') if name in {'benchmark-quality', 'benchmark-evidence'} else ('workflows', 'SKILL.md')
        expected = invoked / kind / name / filename
        require(Path(components[name]).resolve() == expected.resolve() and expected.is_file(), 'unresolved package component')
        require(re.search(r'^name:\s*' + re.escape(name) + r'\s*$', expected.read_text(encoding='utf-8-sig'), re.MULTILINE), 'component name does not resolve')


def check_revision(root, revision):
    require(isinstance(revision, str) and re.fullmatch(r'[0-9a-f]{40}', revision), 'benchmark revision must be full git commit')
    require(git_revision(root / 'product', revision) == revision, 'benchmark revision unavailable in product')


def check_manifest_revision(root, manifest, revision):
    product = (Path(root) / 'product').resolve()
    relative = Path(manifest).resolve().relative_to(product).as_posix()
    require(normalized(git(product, 'show', revision + ':' + relative)) == normalized(Path(manifest).read_bytes()),
            'landed manifest differs from measured git revision')


def check_frozen(root, manifest, revision, observations=None):
    product = (Path(root) / 'product').resolve()
    directory = Path(manifest).resolve().parent
    relative = directory.relative_to(product).as_posix()
    require(relative != '.', 'benchmark must have a dedicated frozen subtree')
    files = compare_tree(directory, tree_files(product, revision, relative))
    inventory = {str(path.resolve()): digest(path) for path in files.values()}
    if observations is not None:
        require(observations == inventory, 'frozen observations differ from committed inventory')
    return inventory
