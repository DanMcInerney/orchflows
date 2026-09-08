import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from tests import test_tiktok_video_package as suite

if len(sys.argv) == 2:
    mode = sys.argv[1]
    with tempfile.TemporaryDirectory() as temp:
        package = Path(temp) / 'tiktok-video'
        shutil.copytree(suite.PACKAGE, package)
        body = package / 'SKILL.md'
        if mode == 'previous-public-route':
            result = subprocess.run(['git', 'show', '1256584e51c7a4d7068a7d5d555bb5fd7f07bf48:example-workflows/tiktok-video/SKILL.md'], capture_output=True, check=True, timeout=30)
            body.write_bytes(result.stdout)
        elif mode == 'unwanted-acquisition':
            body.write_text(body.read_text(encoding='utf-8').replace('--goal-file <market-question>', '--skill research-acquire --goal-file <market-question>'), encoding='utf-8')
        elif mode == 'missing-research-review-pin':
            body.write_text(body.read_text(encoding='utf-8').replace('tickets.py judge <run> --parent <frame> --standard orch-research', 'tickets.py judge <run> --parent <frame> --standard orch-code'), encoding='utf-8')
        with patch.object(suite, 'PACKAGE', package):
            result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([suite.VideoPackageTests('test_literal_sequence_resolves_in_correct_public_scope')]))
        sys.exit(0 if result.wasSuccessful() else 1)

records=[]
for mode, expected in [('previous-public-route',1),('unwanted-acquisition',1),('missing-research-review-pin',1),('corrected',0)]:
    argv=[sys.executable, str(Path(__file__).resolve()), mode]
    result=subprocess.run(argv,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
    records.append({'mode':mode,'argv':argv,'timeout_seconds':120,'observed_exit':result.returncode,'expected_exit':expected,'stdout':result.stdout,'stderr':result.stderr})
    print(mode, result.returncode, flush=True)
Path('.orch-notes/B1.5-route-controls.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
sys.exit(0 if all(r['observed_exit']==r['expected_exit'] for r in records) else 1)
