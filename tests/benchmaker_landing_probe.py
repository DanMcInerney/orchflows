"""Supported same-repository record landing and durable export, using synthetic bytes."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tests.test_benchmaker_calibration import SCRIPTS
from records import EvidenceError
from tests._repo_root import ROOT
from tests.test_workspace_cases import common
from tests.test_workspace_cases.integration_cases import baseline_of
from scripts import state_root, workspace_return

spec = importlib.util.spec_from_file_location('benchmaker_export', SCRIPTS / 'export.py')
exports = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exports)


class RecordLandingTests(unittest.TestCase):
    def test_same_repository_attempt_lands_and_exports_after_candidate_retirement(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
            root = Path(folder)
            product, run_dir = common.make_repo(root)
            common.make_ticket(run_dir, 'T1')
            first = common.run_workspace(ROOT, 'establish', 'testrun', 'T1', '--repo', str(product))
            self.assertEqual(first.returncode, 0, first.stderr)
            ticket = common.make_ticket(run_dir, 'T2', scope=('records',))
            second = common.run_workspace(ROOT, 'establish', 'testrun', 'T2', '--repo', str(product))
            self.assertEqual(second.returncode, 0, second.stderr)
            candidate = state_root.candidate_paths('testrun', 'T2')
            commit = common.commit_in(candidate['path'], {'records/.gitattributes': '* -text\n',
                'records/attempt.json': '{"kind":"synthetic-test-only"}\n'}, 'record evidence')
            result, code = workspace_return.integrate('testrun', 'T2', candidate['path'], candidate['branch'], baseline_of(ticket))
            self.assertEqual(code, 0, result)
            self.assertNotEqual(result['integrate']['outcome'], 'absent')
            self.assertTrue((product / 'records' / 'attempt.json').is_file())
            external = root / 'external'
            receipt = exports.export_records(product, commit, 'records', external)
            self.assertEqual(receipt['artifact'], 'git:' + commit)
            self.assertEqual((external / 'attempt.json').read_bytes(), (product / 'records' / 'attempt.json').read_bytes())
            # Export reads only the committed integration repository, never the ticket tree.
            self.assertTrue(Path(candidate['path']).resolve().is_relative_to(root.resolve()))
            common.git(product, 'worktree', 'remove', '--force', str(candidate['path']))
            self.assertEqual(exports.export_records(product, commit, 'records', external), receipt)
            (external / 'attempt.json').write_text('corrupt', encoding='utf-8')
            with self.assertRaisesRegex(EvidenceError, 'external export differs'):
                exports.export_records(product, commit, 'records', external)
            with self.assertRaisesRegex(EvidenceError, 'repository-relative'):
                exports.export_records(product, commit, '../records', external)


if __name__ == '__main__':
    unittest.main()
