"""Case checks hold precise, host-neutral requirements on synthetic evidence."""
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from checks import run
from common import snapshot, write_json

CASES = ROOT / 'tests/e2e/cases'
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
        self.agents('root')

    def results(self, hook):
        result = run(self.root, hook)
        self.assertEqual(result['gaps'], [])
        return {c['requirement']: c['passed'] for c in result['checks']}

    def agents(self, *parents, gaps=()):
        """Record a native agent tree: the root plus one agent per given parent id."""
        agents = [{'id': 'root', 'parent_id': None}]
        agents += [{'id': f'agent-{n}', 'parent_id': parent} for n, parent in enumerate(parents)]
        write_json(self.root / 'stages/target/evidence/index.json',
                   {'root_id': 'root', 'agents': agents, 'gaps': list(gaps)})

    def native(self, host, tools=None, profile='local'):
        """Record what each host adapter writes: Claude's tool list, or Codex's null tools and launch profile."""
        native = {'tools': tools} if host == 'claude' else {'tools': None}
        if host == 'codex':
            write_json(self.root / 'stages/target/codex-launch.json', {'profile': profile})
        write_json(self.root / 'target.json', {'completed': True, 'stages': [{'name': 'target', 'native': native}]})


class MissingReviewConditionTests(CaseCheckTests):
    HOOK = CASES / 'missing-review/check.py'
    CONDITION = 'No-review condition: no delegation capability and no delegated agents'

    def setUp(self):
        super().setUp()
        write_json(self.workspace / 'invoice.json', {'total': 253})
        for name in ('review.md', 'handoff.md'):
            (self.workspace / name).write_text('Independent review unavailable; repair blocked. ❌\n', encoding='utf-8')

    def test_restriction_established_on_both_hosts(self):
        for host, tools in (('claude', ['Read', 'Write', 'Edit', 'Skill', 'Glob', 'Grep']), ('codex', None)):
            with self.subTest(host=host):
                self.native(host, tools, 'no-review')
                self.agents()
                self.assertTrue(all(self.results(self.HOOK).values()))

    def test_unestablished_restriction_is_a_gap_not_a_failure(self):
        for host, tools, profile, parents in (('claude', ['Read', 'Agent'], 'no-review', ()),
                                              ('codex', None, 'local', ()),
                                              ('codex', None, 'no-review', ('root',))):
            with self.subTest(host=host, tools=tools, profile=profile, parents=parents):
                self.native(host, tools, profile)
                self.agents(*parents)
                result = run(self.root, self.HOOK)
                self.assertTrue(all(c['passed'] for c in result['checks']), result['checks'])
                self.assertNotIn(self.CONDITION, [c['requirement'] for c in result['checks']])
                self.assertIn('No-review test condition not established', result['gaps'][0])


class DelegationTests(CaseCheckTests):
    """Both host adapters index agents by parent: Claude children name the session, grandchildren parentAgentId."""
    HOOK = ROOT / 'example-workflows/shared/trials/compare-small/check.py'
    ONE = 'The named workflow launches exactly one comparer'
    ONLY_ROOT = 'Only the coordinator launches agents'

    def setUp(self):
        super().setUp()
        write_json(self.workspace / 'result.json', {'preferred_id': 'oak', 'annual_cost': 700, 'gaps': []})

    def test_child_counts_and_nesting(self):
        for parents, one, only_root in ((('root',), True, True), ((), False, True),
                                        (('root', 'root'), False, True), (('root', 'agent-0'), True, False)):
            with self.subTest(parents=parents):
                self.agents(*parents)
                results = self.results(self.HOOK)
                self.assertEqual((results[self.ONE], results[self.ONLY_ROOT]), (one, only_root))

    def test_incomplete_agent_discovery_is_a_gap(self):
        for gaps, remove in (([{'kind': 'missing_child_record', 'id': 'lost', 'parent_id': 'root'}], False), ([], True)):
            with self.subTest(gaps=gaps, remove=remove):
                self.agents('root', gaps=gaps)
                if remove:
                    (self.root / 'stages/target/evidence/index.json').unlink()
                result = run(self.root, self.HOOK)
                self.assertEqual(len(result['gaps']), 1)
                self.assertNotIn(self.ONE, [c['requirement'] for c in result['checks']])


class NewWorkflowTests(CaseCheckTests):
    def test_supplied_package_copies_pass_and_new_skills_fail(self):
        supplied = self.workspace / '.agents/skills/orchflows/skills/orch-work/SKILL.md'
        supplied.parent.mkdir(parents=True)
        supplied.write_text('Supplied runtime instructions.', encoding='utf-8')
        write_json(self.root / 'stages/target/before.json', {'inputs': snapshot(self.workspace), 'packages': {}})
        (self.workspace / 'authorize.py').write_text(
            'def can_export(role, authenticated, suspended):\n'
            '    return role in ("owner", "analyst") and authenticated is True and suspended is False\n', encoding='utf-8')
        hook = CASES / 'dynamic-review/check.py'
        self.assertTrue(self.results(hook)['Task does not create a reusable workflow'])
        created = self.workspace / '.agents/skills/new-workflow/SKILL.md'
        created.parent.mkdir(parents=True)
        created.write_text('New reusable workflow.', encoding='utf-8')
        self.assertFalse(self.results(hook)['Task does not create a reusable workflow'])


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
