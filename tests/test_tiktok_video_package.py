"""Public video composition at discovery, resolution and integrity seams.

These are static admission checks with mutated disposable controls, never
claims that prose ran or that endpoint creative/audio quality was judged.
"""
from __future__ import annotations

import re
import hashlib
import shlex
import subprocess
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_IMPORT_PATH = sys.path[:]

import install
from scripts import doclint, rings, tickets_frame, tickets_pins
from tools.validate_support import packages, workflows
from tests._repo_root import ROOT

# Imported runtime entry points can add their installed library to sys.path.
sys.path[:] = _IMPORT_PATH

PACKAGE = ROOT / 'example-workflows/tiktok-video'
PRIVATE = {'video-direction', 'video-production', 'render-video',
           'video-script-quality', 'video-quality'}


class VideoPackageTests(unittest.TestCase):
    def setUp(self):
        original_path = sys.path[:]
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), original_path))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.options = {'project': self.root / 'project',
                        'home': self.root / 'home', 'lib': ROOT}

    def grade(self, package=PACKAGE, options=None):
        diag = packages.Diagnostics()
        with patch.object(packages, 'ROOT', Path(ROOT.anchor)):
            workflows.validate_workflow_packages(
                ROOT, [(package, package / 'SKILL.md')], diag,
                standard_roots=[ROOT / 'standards'],
                overrides=options or self.options)
        return diag

    def copy(self):
        target = self.root / 'project/.orchflows/workflows/tiktok-video'
        shutil.copytree(PACKAGE, target)
        return target

    def test_canonical_discovery_exposes_only_public_owner(self):
        found = {p.name for p, _, _ in install.discover_workflow_skills(ROOT)}
        self.assertIn('tiktok-video', found)
        self.assertFalse(PRIVATE & found)
        records = rings.inventory(**self.options)
        names = {r['name'] for r in records}
        self.assertIn('tiktok-video', names)
        self.assertFalse(PRIVATE & names)
        for name in ('video-direction', 'video-production'):
            with self.assertRaises(rings.RingError):
                rings.resolve('workflow', name, trust=False, **self.options)

    def test_literal_sequence_resolves_in_correct_public_scope(self):
        text = (PACKAGE / 'SKILL.md').read_text(encoding='utf-8')
        calls = [name for command in workflows._commands(text)
                 for kind, name in workflows.NAME_FLAG_RE.findall(command)
                 if kind == 'workflow']
        self.assertEqual(['tiktok-video', 'video-direction',
                          'video-production'], calls)
        commands = list(workflows._commands(text))
        research = [command for command in commands
                    if ('standard', 'orch-research') in workflows.NAME_FLAG_RE.findall(command)]
        self.assertEqual(3, len(research))
        self.assertEqual(2, sum('tickets.py do ' in command for command in research))
        self.assertEqual(1, sum('tickets.py judge ' in command for command in research))
        for command in research:
            self.assertIn('--parent <frame>', command)
            self.assertIn('--goal-file', command)
            self.assertIn('--context-file', command)
        for path in [PACKAGE / 'SKILL.md', PACKAGE / 'references/admission.md',
                     PACKAGE / 'references/inventory.md']:
            body = path.read_text(encoding='utf-8')
            self.assertFalse({'super-research', 'research-acquire', 'html-dossier'}
                             & set(re.findall(r'[a-z]+(?:-[a-z]+)+', body)), path)
        self.assertFalse(self.grade().has_errors)
        for kind, name in [('workflow', 'video-direction'),
                           ('workflow', 'video-production'),
                           ('skill', 'render-video'),
                           ('standard', 'video-quality'),
                           ('standard', 'video-script-quality')]:
            record = rings.resolve(kind, name, owner='tiktok-video',
                                   trust=False, **self.options)
            self.assertTrue(record['private'])
        with self.assertRaises(rings.RingError):
            rings.resolve('standard', 'video-quality', owner='super-research',
                          trust=False, **self.options)
        copied = self.copy()
        (copied / 'workflows/video-direction/SKILL.md').unlink()
        self.assertTrue(self.grade(copied).has_errors)

    def test_contained_links_and_escape_control(self):
        for path in PACKAGE.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                resolved = doclint.resolve_link(path, target)
                if resolved is not None:
                    self.assertTrue(resolved.is_file(), (path, target))
                    self.assertTrue(resolved.resolve().is_relative_to(PACKAGE.resolve()),
                                    (path, target))
        copied = self.copy()
        with (copied / 'SKILL.md').open('a', encoding='utf-8') as out:
            out.write('\n[escape](../../../../outside.md)\n')
        self.assertTrue(self.grade(copied).has_errors)

    def test_stale_package_cannot_authorize_existing_frame(self):
        copied = self.copy()
        expected = tickets_pins.tree_digest('workflow', copied)
        parent = self.root / 'B1.md'
        parent.write_text('---\nworkflow: tiktok-video\nworkflow_digest: ' + expected
                          + '\nworkflow_entry: SKILL.md\n---\n', encoding='utf-8')
        def resolved(*args):
            return {'dir': str(copied), 'ring': 'project',
                    'digest': tickets_pins.tree_digest('workflow', copied)}
        with patch.object(tickets_pins, 'resolved', side_effect=resolved):
            self.assertIsNone(tickets_frame.workflow_context(self.root, 'B1')[1])
            with (copied / 'references/admission.md').open('a', encoding='utf-8') as out:
                out.write('\nChanged admission evidence.\n')
            self.assertIsNotNone(tickets_frame.workflow_context(self.root, 'B1')[1])
            (copied / 'SKILL.md').unlink()
            self.assertIsNotNone(tickets_frame.workflow_context(self.root, 'B1')[1])

    def test_document_verifier_rejects_absent_and_stale_output(self):
        text = (PACKAGE / 'references/creative.md').read_text(encoding='utf-8')
        command = next(line.strip() for line in text.splitlines()
                       if line.strip().startswith('<verified-python> -c '))
        argv = shlex.split(command)
        document, review = self.root / 'script.md', self.root / 'review.md'
        fixed = [b'Original script', b'Independent review of fixed script']
        digests = [hashlib.sha256(data).hexdigest() for data in fixed]
        command = [sys.executable, '-c', argv[2], str(document), digests[0],
                   str(review), digests[1]]
        def reading():
            return subprocess.run(command, capture_output=True, timeout=10).returncode
        self.assertNotEqual(0, reading())
        document.write_bytes(fixed[0])
        review.write_bytes(fixed[1])
        self.assertEqual(0, reading())
        document.write_bytes(b'Unreviewed revision')
        self.assertNotEqual(0, reading())
        document.write_bytes(fixed[0])
        review.write_bytes(b'Changed review')
        self.assertNotEqual(0, reading())


if __name__ == '__main__':
    unittest.main()
