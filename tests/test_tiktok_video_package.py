"""Public video composition at discovery, resolution and integrity seams.

These are static admission checks with mutated disposable controls, never
claims that prose ran or that endpoint creative/audio quality was judged.
"""
from __future__ import annotations

import re
import hashlib
import json
import subprocess
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_IMPORT_PATH = sys.path[:]

import install
from scripts import doclint, rings, orchflows_adapters, standards, tickets_frame, tickets_pins
from tools.validate_support import packages, workflows
from tests._repo_root import ROOT

# Imported runtime entry points can add their installed library to sys.path.
sys.path[:] = _IMPORT_PATH

PACKAGE = ROOT / 'example-workflows/orchflows-videos'
PRIVATE = {'video-direction', 'video-production', 'render-video',
           'orchflows-marketing-videos'}


class VideoPackageTests(unittest.TestCase):
    def setUp(self):
        original_path = sys.path[:]
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), original_path))
        # Diagnostics need the repository drive; stay outside repository copies.
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT.parent)
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
        target = self.root / 'project/.orchflows/workflows/orchflows-videos'
        shutil.copytree(PACKAGE, target)
        return target

    def test_canonical_discovery_exposes_only_public_owner(self):
        found = {p.name for p, _, _ in install.discover_workflow_skills(ROOT)}
        self.assertIn('orchflows-videos', found)
        self.assertFalse(PRIVATE & found)
        records = rings.inventory(**self.options)
        names = {r['name'] for r in records}
        self.assertIn('orchflows-videos', names)
        self.assertFalse(PRIVATE & names)
        for name in ('video-direction', 'video-production'):
            with self.assertRaises(rings.RingError):
                rings.resolve('workflow', name, trust=False, **self.options)

    def test_generated_public_adapters_and_fixed_foundation(self):
        records = orchflows_adapters.host_records()
        for name in ('orchflows-videos', 'tiktok-video'):
            item = ROOT / 'example-workflows' / name / 'SKILL.md'
            for host in ('codex', 'claude', 'grok'):
                body = orchflows_adapters.render('workflow', name, item, records[host])
                self.assertIn(str(item), body)
                self.assertNotIn('role:', body)
        expected = {'package.json': '40dfbc8a05addb4fa604caf1f81ef63905fe07b4fd5c980fe33ef2d228696b04',
                    'package-lock.json': 'c3d6b8beb19a8748e68e7356a76183c74b552f02739784c640bbf2200e26b1f0'}
        for name, digest in expected.items():
            self.assertEqual(digest, hashlib.sha256(
                (PACKAGE / 'references/scaffold' / name).read_bytes()).hexdigest())

    def test_literal_sequence_resolves_in_correct_public_scope(self):
        text = (PACKAGE / 'SKILL.md').read_text(encoding='utf-8')
        calls = [name for command in workflows._commands(text)
                 for kind, name in workflows.NAME_FLAG_RE.findall(command)
                 if kind == 'workflow']
        self.assertEqual(['orchflows-videos', 'video-direction',
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
                           ('standard', 'orchflows-marketing-videos')]:
            record = rings.resolve(kind, name, owner='orchflows-videos',
                                   trust=False, **self.options)
            self.assertTrue(record['private'])
        with self.assertRaises(rings.RingError):
            rings.resolve('standard', 'orchflows-marketing-videos', owner='tiktok-video',
                          trust=False, **self.options)
        generic = standards.resolve_chain(['short-videos'], trust=False, **self.options)
        self.assertEqual(['orch-code', 'short-videos'], [x['name'] for x in generic])
        for helper in ('video-direction', 'video-production'):
            body = (PACKAGE / f'workflows/{helper}/SKILL.md').read_text(encoding='utf-8')
            calls = [c for c in workflows._commands(body) if '--standard' in c]
            self.assertEqual(2, len(calls))
            for command in calls:
                self.assertIn('--workspace-adapter git', command)
                self.assertIn('--isolation required', command)
                self.assertIn('--workspace <workspace>', command)
                stamps = [n for k, n in workflows.NAME_FLAG_RE.findall(command) if k == 'standard']
                self.assertEqual(['orchflows-marketing-videos'], stamps)
                chain = standards.resolve_chain(stamps, owner='orchflows-videos',
                                                trust=False, **self.options)
                self.assertEqual(['orch-code', 'short-videos', 'orchflows-marketing-videos'],
                                 [x['name'] for x in chain])
            self.assertNotIn('doc:', body)
            self.assertNotIn('document-tree', body)
        copied = self.copy()
        narrowing = copied / 'standards/orchflows-marketing-videos/STANDARD.md'
        original = narrowing.read_text(encoding='utf-8')
        narrowing.write_text(original.replace('narrows: short-videos',
                                             'narrows: missing-video-parent'), encoding='utf-8')
        self.assertTrue(self.grade(copied).has_errors)
        narrowing.write_text(original, encoding='utf-8')
        self.assertFalse(self.grade(copied).has_errors)
        (copied / 'workflows/video-direction/SKILL.md').unlink()
        self.assertTrue(self.grade(copied).has_errors)

    def test_missing_external_base_and_compatibility_public_scope(self):
        lib = self.root / 'minimal-lib'
        shutil.copytree(ROOT / 'standards/orch-code', lib / 'standards/orch-code')
        shutil.copytree(PACKAGE, lib / 'example-workflows/orchflows-videos')
        options = dict(self.options, lib=lib)
        with self.assertRaises(standards.StandardError):
            standards.resolve_chain(['orchflows-marketing-videos'], owner='orchflows-videos',
                                    trust=False, **options)
        shutil.copytree(ROOT / 'standards/short-videos', lib / 'standards/short-videos')
        chain = standards.resolve_chain(['orchflows-marketing-videos'], owner='orchflows-videos',
                                        trust=False, **options)
        self.assertEqual(3, len(chain))
        legacy = ROOT / 'example-workflows/tiktok-video'
        self.assertEqual(['SKILL.md'], [p.name for p in legacy.iterdir()])
        self.assertFalse(self.grade(legacy).has_errors)
        commands = list(workflows._commands((legacy / 'SKILL.md').read_text()))
        self.assertEqual(['tiktok-video', 'orchflows-videos'],
                         [n for c in commands for k, n in workflows.NAME_FLAG_RE.findall(c)
                          if k == 'workflow'])

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
        parent.write_text('---\nworkflow: orchflows-videos\nworkflow_digest: ' + expected
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

    def test_direction_verifier_rejects_absent_stale_and_wrong_review(self):
        project = self.root / 'git-project'
        project.mkdir()
        def git(*args):
            return subprocess.run(['git', '-C', str(project), *args], check=True,
                                  capture_output=True, timeout=20).stdout.decode().strip()
        git('init')
        document, review = project / 'direction.md', self.root / 'review.json'
        document.write_bytes(b'Original direction')
        git('add', 'direction.md')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            'commit', '-m', 'direction')
        commit = git('rev-parse', 'HEAD')
        names = ['orch-code', 'short-videos', 'orchflows-marketing-videos']
        pins = ['sha256:' + str(i) * 64 for i in range(3)]
        snapshot = {'artifact': 'git:' + commit, 'standards':
                    [dict(name=n, digest=d) for n, d in zip(names, pins)],
                    'blockers': [], 'review_identity': 'fixture/independent-review'}
        raw = json.dumps(snapshot).encode()
        command = [sys.executable, str(PACKAGE / 'scripts/verify_direction.py'),
                   '--project', str(project), '--commit', commit, '--path', 'direction.md',
                   '--sha256', hashlib.sha256(document.read_bytes()).hexdigest(),
                   '--review', str(review), '--review-sha256', hashlib.sha256(raw).hexdigest(),
                   '--digests', *pins]
        def reading():
            return subprocess.run(command, capture_output=True, timeout=40).returncode
        self.assertNotEqual(0, reading())
        review.write_bytes(raw)
        self.assertEqual(0, reading())
        review.write_bytes(b'corrupt')
        self.assertNotEqual(0, reading())
        for key, value in [('artifact', 'git:' + 'f' * 40), ('standards', []),
                           ('blockers', ['unresolved'])]:
            changed = dict(snapshot, **{key: value})
            data = json.dumps(changed).encode()
            review.write_bytes(data)
            command[command.index('--review-sha256') + 1] = hashlib.sha256(data).hexdigest()
            self.assertNotEqual(0, reading())
        review.write_bytes(raw)
        command[command.index('--review-sha256') + 1] = hashlib.sha256(raw).hexdigest()
        command[command.index('--sha256') + 1] = '0' * 64
        self.assertNotEqual(0, reading())


if __name__ == '__main__':
    unittest.main()
