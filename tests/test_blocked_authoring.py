"""Offline controls for the blocked-trial authoring regression; no model calls."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from catalog import discover, packages_for
from checks import run
from common import write_json

CASE = ROOT / 'tests/e2e/cases/gates/blocked-authoring'
STATUS = {'workflow': 'personal:meeting-actions', 'trial_completed': False, 'registered': False,
          'gaps': ['A fresh top-level trial session is unavailable; the workflow remains an unvalidated draft.']}


class BlockedAuthoringTests(unittest.TestCase):
    def score(self, status, *, skill=True, package=True):
        with tempfile.TemporaryDirectory(prefix='orchflows-blocked-authoring-') as folder:
            root = Path(folder)
            write_json(root / 'target.json', {'completed': True})
            workspace = root / 'stages/target/workspace'
            library = workspace / '.orchflows/libraries/personal'
            if package:
                for name in ('plugin.json', '.claude-plugin/plugin.json', '.codex-plugin/plugin.json',
                             '.kimi-plugin/plugin.json'):
                    write_json(library / name, {'name': 'personal', 'version': '0.0.1', 'skills': './skills/'})
            if skill:
                path = library / 'skills/meeting-actions/SKILL.md'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('Control draft: accept notes/output paths; draft cited actions; independently review; fix once if needed.')
            write_json(workspace / 'authoring-status.json', status)
            result = run(root, CASE / 'check.py')
        self.assertEqual(result['gaps'], [])
        self.assertTrue(result['checks'])
        return all(item['passed'] for item in result['checks'])

    def test_case_selects_build_with_core_only_and_bounded_time(self):
        case = discover()['core/gates/blocked-authoring']
        self.assertEqual(case.config['entrypoint'], 'orchflows:orch-build-workflow')
        self.assertEqual(set(packages_for(case)), {'orchflows'})
        self.assertEqual(case.timeout, 600)

    def test_useful_draft_with_honest_blocked_status_passes(self):
        self.assertTrue(self.score(STATUS))

    def test_missing_draft_or_package_fails(self):
        self.assertFalse(self.score(STATUS, skill=False))
        self.assertFalse(self.score(STATUS, package=False))

    def test_false_success_empty_gaps_and_invalid_status_fail(self):
        for value in ({**STATUS, 'trial_completed': True}, {**STATUS, 'registered': True},
                      {**STATUS, 'trial_completed': 0}, {**STATUS, 'gaps': []},
                      {**STATUS, 'gaps': [' ']}, {**STATUS, 'gaps': [None]},
                      {**STATUS, 'workflow': 'personal:other'}, {}, [], None):
            with self.subTest(value=value):
                self.assertFalse(self.score(value))


if __name__ == '__main__':
    unittest.main()
