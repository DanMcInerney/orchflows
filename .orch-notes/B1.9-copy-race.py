"""Force the observed cleanup interleaving with the actual copy ignore policy."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from tests.test_tiktok_video_package import VideoPackageTests
from tests.test_validate_cases.validator_ownership import FrictionLocationSyncTest
case = VideoPackageTests('test_contained_links_and_escape_control')
case.setUp()
case.copy()
notes = ROOT / '.orch-notes'
assert '.orch-notes' not in FrictionLocationSyncTest.COPY_SKIPS(str(ROOT), ['.orch-notes'])
visited = []
def interleave_cleanup(directory, names):
    ignored = FrictionLocationSyncTest.COPY_SKIPS(directory, names)
    if Path(directory) == notes:
        assert case.root.name in names and case.root.name not in ignored
        visited.append(str(case.root))
        case.doCleanups()
    return ignored
caught = None
try:
    with tempfile.TemporaryDirectory(prefix='orch-B1.9-copy-control-', dir=ROOT.parent) as dest:
        try:
            shutil.copytree(notes, Path(dest) / 'copy/.orch-notes', ignore=interleave_cleanup, symlinks=True)
        except shutil.Error as error:
            caught = str(error)
finally:
    case.doCleanups()
assert visited and caught and case.root.name in caught
assert not case.root.exists() and not Path(dest).exists()
log = Path('C:/Users/danhm/AppData/Local/Temp/video-fixture-fixed-ci-windows.log')
record = {'assigned_name': 'B1.9', 'dispatch_id': 'B1.9:d1',
          'assignment_seal': 'sha256:d0248ed1b363d3318780b1014c9dbd3a29711fa2ca0373bc79592d584751bc2a',
          'copy_policy_ignores_notes': False, 'visited_fixture': visited,
          'shutil_error': caught, 'all_temporary_roots_removed': True,
          'method': 'Actual VideoPackageTests fixture and actual COPY_SKIPS callback; deterministic cleanup after copytree enumerates notes and before descent. Copies only notes subtree, not full repository; this isolates the hosted interleaving without schedule luck.',
          'hosted_log': str(log), 'hosted_log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
          'hosted_excerpt': [line for line in log.read_text().splitlines() if any(term in line for term in
           ('test_tiktok_video_package', 'FrictionLocationSyncTest', 'shutil.copytree(ROOT', 'shutil.Error:', 'HEAD is now at', '54 modules, 1287', 'Process completed with exit code'))]}
(ROOT / '.orch-notes/B1.9-copy-race.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(json.dumps(record, indent=2))
