"""B1.9 independent fixed-source Windows drive controls; no source edits."""
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest

ROOT = Path.cwd()
NOTES = ROOT / '.orch-notes'
sys.path.insert(0, str(ROOT))
BASE = 'ac22b24b^'
TARGET = '10565acdfa35f4a768a4dc803c9d9b5c5c66744d'
TEST = 'tests/test_tiktok_video_package.py'

if len(sys.argv) > 1:
    mode = sys.argv[1]
    commands = []
    if mode == 'before':
        argv = ['git', 'show', BASE + ':' + TEST]
        cp = subprocess.run(argv, capture_output=True, timeout=30)
        commands.append({'argv': argv, 'exit': cp.returncode})
        cp.check_returncode()
        source = cp.stdout.decode('utf-8')
    else:
        source = (ROOT / TEST).read_text(encoding='utf-8')
    module = types.ModuleType('fixture_control')
    module.__file__ = str(ROOT / TEST)
    exec(compile(source, str(ROOT / TEST), 'exec'), module.__dict__)
    roots = []
    class Result(unittest.TextTestResult):
        def stopTest(self, test):
            path = getattr(test, 'root', None)
            roots.append({'test': test.id(), 'fixture': str(path),
                          'drive': path.drive if path else None,
                          'cleaned': path is not None and not path.exists()})
            super().stopTest(test)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(module.VideoPackageTests))
    record = {'mode': mode, 'repository': str(ROOT), 'temp_default': tempfile.gettempdir(),
              'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
              'roots': roots, 'commands': commands, 'stderr': stream.getvalue(),
              'source_sha256_utf8': hashlib.sha256(source.encode()).hexdigest()}
    (NOTES / ('B1.9-' + mode + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(stream.getvalue(), end='')
    raise SystemExit(0 if result.wasSuccessful() else 1)

commands = []
def run(argv, **kwargs):
    cp = subprocess.run(argv, capture_output=True, timeout=180, **kwargs)
    commands.append({'argv': argv, 'exit': cp.returncode, 'stdout': cp.stdout.decode('utf-8', 'replace'),
                     'stderr': cp.stderr.decode('utf-8', 'replace')})
    return cp

assert ROOT.drive.upper() == 'C:'
with tempfile.TemporaryDirectory(prefix='orch-B1.9-cross-drive-', dir='D:/') as alternate:
    alternate_path = Path(alternate)
    env = dict(os.environ, TMP=alternate, TEMP=alternate, TMPDIR=alternate, PYTHONIOENCODING='utf-8')
    assert alternate_path.drive.upper() != ROOT.drive.upper()
    before = run([sys.executable, str(Path(__file__).resolve()), 'before'], env=env)
    after = run([sys.executable, str(Path(__file__).resolve()), 'after'], env=env)
    assert before.returncode == 1 and after.returncode == 0
    records = [json.loads((NOTES / ('B1.9-' + name + '.json')).read_text()) for name in ('before', 'after')]
    assert records[0]['tests'] == records[1]['tests'] == 5
    assert records[0]['errors'] == 2 and records[0]['failures'] == 0
    assert records[1]['errors'] == records[1]['failures'] == 0
    assert records[0]['stderr'].count('ValueError:') == 2
    assert 'not in the subpath' in records[0]['stderr']
    assert all(row['drive'].upper() == 'D:' and row['cleaned'] for row in records[0]['roots'])
    assert all(row['drive'].upper() == 'C:' and row['cleaned'] for row in records[1]['roots'])
    scoped = run([sys.executable, 'tools/run_tests.py', 'tests.test_tiktok_video_package',
                  'tests.test_tiktok_video_probe', '--no-cache', '-j', '2',
                  '--timing-file', '.orch-notes/B1.9-scoped-timing.json'], env=env)
    assert scoped.returncode == 0
    assert not list(alternate_path.iterdir()), list(alternate_path.iterdir())
assert not alternate_path.exists()

from scripts import tickets_pins
from tests.test_tiktok_video_package import VideoPackageTests
from tools.validate_support import vocabulary, lint
from tools import validate
case = VideoPackageTests('test_contained_links_and_escape_control')
case.setUp()
try:
    copied = case.copy()
    sentinel = copied / 'B1.9-fixture-scan-sentinel.md'
    sentinel.write_text('[deliberately missing](missing.md)\n', encoding='utf-8')
    scans = {'vocabulary': list(vocabulary._consumer_sources(ROOT)),
             'markdown_links': list(lint._linked_markdown_files()),
             'documented_paths': list(validate._documented_path_sources(ROOT))}
    scan_record = {name: {'files': len(paths), 'fixture_included': any(p.is_relative_to(case.root) for p in paths)}
                   for name, paths in scans.items()}
    assert all(not record['fixture_included'] for record in scan_record.values())
finally:
    case.doCleanups()
assert not case.root.exists()

package = tickets_pins.tree_digest('workflow', ROOT / 'example-workflows/tiktok-video')
standard = tickets_pins.tree_digest('standard', Path('C:/Users/danhm/.orchflows/lib/standards/orch-code'))
assert package == 'sha256:d13322cae66f674b0b9bd19d92fc9fbd40ff2139cc3c9ebb95d28884edc1eb42'
assert standard == 'sha256:8049030d7cef517e5d6dbc09a1ece092c43841521cd76665022132bded12ddf6'
unchanged = run(['git', 'diff', '--exit-code', '05290a079127759f6ae1307dbcda4e6d3e800a6c', TARGET,
                 '--', 'example-workflows/tiktok-video'])
assert unchanged.returncode == 0
old = run(['git', 'show', BASE + ':' + TEST])
old.check_returncode()
new_tree = ast.parse((ROOT / TEST).read_text())
old_tree = ast.parse(old.stdout.decode())
for tree in (new_tree, old_tree):
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    cls.body = [node for node in cls.body if not isinstance(node, ast.FunctionDef) or node.name != 'setUp']
assert ast.dump(new_tree) == ast.dump(old_tree)
summary = {'assigned_name': 'B1.9', 'dispatch_id': 'B1.9:d1',
           'assignment_seal': 'sha256:d0248ed1b363d3318780b1014c9dbd3a29711fa2ca0373bc79592d584751bc2a',
           'reviewed_artifact': 'git:' + TARGET, 'controls': records,
           'temporary_base_removed': not alternate_path.exists(), 'scanner_fixture_removed': not case.root.exists(),
           'scan_exclusion': scan_record, 'package_digest': package, 'standard_digest': standard,
           'all_methods_except_setup_ast_identical': True, 'commands': commands}
(NOTES / 'B1.9-controls.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: v for k, v in summary.items() if k not in ('controls', 'commands')}, indent=2))
print('before exit1: 5 tests, 2 expected cross-drive errors; after exit0: 5 tests; scoped exit0: 11 tests')
