"""Task-only output checks distinguish supplied native skills from new recipes."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from checks import run
from common import snapshot, write_json

VENDOR_A = '''from decimal import Decimal
def normalize(record):
    elapsed = Decimal(record['duration']) * 1000
    if elapsed < 0 or elapsed != elapsed.to_integral_value() or type(record['ok']) is not bool:
        raise ValueError('Invalid duration or outcome')
    return dict(id=record['id'], elapsed_ms=int(elapsed), outcome='success' if record['ok'] else 'failure')
'''
VENDOR_B = '''def normalize(record):
    elapsed = record['elapsed']
    if elapsed < 0 or elapsed % 1000 or record['state'] not in ('done', 'error'):
        raise ValueError('Invalid duration or outcome')
    return dict(id=record['key'], elapsed_ms=elapsed // 1000, outcome='success' if record['state'] == 'done' else 'failure')
'''


class ResearchCodeScoringTests(unittest.TestCase):
    def score(self, new_skill=None):
        with tempfile.TemporaryDirectory(prefix='orchflows-research-score-') as folder:
            root = Path(folder)
            stage = root / 'stages/target'
            workspace = stage / 'workspace'
            supplied = workspace / '.agents/skills/orchflows/skills/orch-work/SKILL.md'
            supplied.parent.mkdir(parents=True)
            supplied.write_text('Supplied runtime instructions.')
            write_json(stage / 'before.json', {'inputs': snapshot(workspace), 'packages': {}})
            write_json(root / 'target.json', {'completed': True})
            (workspace / 'vendor_a.py').write_text(VENDOR_A)
            (workspace / 'vendor_b.py').write_text(VENDOR_B)
            if new_skill:
                created = workspace / new_skill
                created.parent.mkdir(parents=True, exist_ok=True)
                created.write_text('New reusable workflow.')
            result = run(root, ROOT / 'tests/e2e/cases/research-code/check.py')
        self.assertEqual(result['gaps'], [])
        self.assertTrue(result['checks'][0]['passed'], result['checks'][0])
        return next(c for c in result['checks'] if c['requirement'] == 'Task does not create a reusable workflow')

    def test_preexisting_runtime_package_is_not_new_workflow_output(self):
        self.assertTrue(self.score()['passed'])

    def test_new_workflows_fail_even_inside_native_skill_directory(self):
        for path in ('SKILL.md', 'new-workflow/SKILL.md', '.agents/skills/new-workflow/SKILL.md'):
            with self.subTest(path=path):
                result = self.score(path)
                self.assertFalse(result['passed'])
                self.assertIn(path, result['evidence'])


if __name__ == '__main__':
    unittest.main()
