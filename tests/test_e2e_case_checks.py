"""Case checks hold precise, host-neutral requirements on synthetic evidence."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from checks import run
from common import write_json

CORRUPT_EXPORT = ROOT / 'example-workflows/short-video/trials/corrupt-export'
EXPORT_SIZE = (CORRUPT_EXPORT / 'fixtures/export.mp4').stat().st_size


class CaseCheckTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix='orchflows-case-check-')
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.workspace = self.root / 'stages/target/workspace'
        self.workspace.mkdir(parents=True)
        write_json(self.root / 'target.json', {'completed': True})

    def results(self, hook):
        result = run(self.root, hook)
        self.assertEqual(result['gaps'], [])
        return {c['requirement']: c['passed'] for c in result['checks']}


class CorruptExportIdentityTests(CaseCheckTests):
    IDENTITY = f'State the inspected export path and byte size ({EXPORT_SIZE} bytes) together as its identity'

    def review(self, text, export=None):
        shutil.copy2(CORRUPT_EXPORT / 'fixtures/export.mp4', self.workspace / 'export.mp4')
        if export is not None:
            (self.workspace / 'export.mp4').write_bytes(export)
        (self.workspace / 'review.md').write_text(text.format(size=EXPORT_SIZE), encoding='utf-8')
        return self.results(CORRUPT_EXPORT / 'check.py')

    def test_path_and_size_stated_together_pass(self):
        for form in ('## Examined identity\n\n- File: `C:\\w\\export.mp4`\n- Size: {size} bytes\n',
                     '`export.mp4` is a {size}-byte plain-text placeholder.\n',
                     '## export.mp4\n\nSize: {size} B; SHA-256 recorded below.\n',
                     '| Path | Size (bytes) |\n|---|---|\n| /w/export.mp4 | {size} |\n'):
            with self.subTest(form=form):
                results = self.review('# Review\n\n' + form + '\nNot encoded video.\n')
                self.assertTrue(all(results.values()), results)

    def test_size_missing_or_apart_from_path_fails(self):
        for form in ('- File: export.mp4\n- SHA-256: ab{size}cd\n',
                     '- File: export.mp4\n\nThe payload measured {size} bytes.\n',
                     '- File: export.mp4.bak\n- Size: {size} bytes\n',
                     '- File: export.mp4\n- Header: 1{size} bytes; {size}0 frames\n'):
            with self.subTest(form=form):
                self.assertFalse(self.review(form)[self.IDENTITY])

    def test_mutated_export_fails_even_with_identity(self):
        results = self.review('- export.mp4, {size} bytes\n', export=b'replaced')
        self.assertFalse(results['Preserve the supplied export byte-for-byte'])
        self.assertTrue(results[self.IDENTITY])


if __name__ == '__main__':
    unittest.main()
