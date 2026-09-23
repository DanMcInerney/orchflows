"""Case checks hold precise, host-neutral requirements on synthetic evidence."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests/e2e'))
from checks import run
from common import digest, snapshot, write_json

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

    def test_child_counts_leave_nesting_to_the_harness(self):
        for parents, one in ((('root',), True), ((), False), (('root', 'root'), False), (('root', 'agent-0'), True)):
            with self.subTest(parents=parents):
                self.agents(*parents)
                results = self.results(self.HOOK)
                self.assertEqual(results[self.ONE], one)
                self.assertNotIn(self.ONLY_ROOT, results)

    def test_incomplete_agent_discovery_is_a_gap(self):
        for gaps, remove in (([{'kind': 'missing_child_record', 'id': 'lost', 'parent_id': 'root'}], False), ([], True)):
            with self.subTest(gaps=gaps, remove=remove):
                self.agents('root', gaps=gaps)
                if remove:
                    (self.root / 'stages/target/evidence/index.json').unlink()
                result = run(self.root, self.HOOK)
                self.assertEqual(len(result['gaps']), 1)
                self.assertNotIn(self.ONE, [c['requirement'] for c in result['checks']])


class ResearchGuidanceTests(CaseCheckTests):
    HOOK = CASES / 'research-code/check.py'
    GUIDANCE = 'Applicable core guidance reaches children: each assignment names or quotes code or research guidance'
    SENTENCE = 'Give each behavior one owner and test observable behavior rather than implementation structure.'

    def setUp(self):
        super().setUp()
        guidance = self.root / 'packages/orchflows/guidance'
        guidance.mkdir(parents=True)
        (guidance / 'code.md').write_text('# Code\n\n' + self.SENTENCE + ' Short.\n', encoding='utf-8')
        (guidance / 'writing.md').write_text('Prefer the plain word over the fancy one in every sentence.\n', encoding='utf-8')
        (self.workspace / 'research.md').write_text('Vendor formats.', encoding='utf-8')
        write_json(self.root / 'stages/target/before.json', {'inputs': {}, 'packages': {}})

    def child(self, *messages):
        """One child whose transcript opens with these user messages (plain or Codex content-list data)."""
        events = self.root / 'stages/target/evidence/child.events.jsonl'
        records = [{'kind': 'message', 'role': 'user', 'data': m} for m in messages]
        records += [{'kind': 'tool_call', 'tool': 'Read', 'data': {'file_path': 'guidance/code.md'}}]
        events.write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')
        write_json(self.root / 'stages/target/evidence/index.json', {'root_id': 'root', 'gaps': [], 'agents': [
            {'id': 'root', 'parent_id': None}, {'id': 'child', 'parent_id': 'root', 'events_path': 'C:/elsewhere/child.events.jsonl'}]})
        return self.results(self.HOOK)[self.GUIDANCE]

    def test_guidance_paths_names_and_pasted_text_count(self):
        codex_context = [{'type': 'input_text', 'text': '<environment_context><cwd>W</cwd></environment_context>'}]
        for messages in (('Build vendor_a.py. Apply C:\\run\\packages\\orchflows\\guidance\\code.md (Make).',),
                         ('Review against .agents/skills/orchflows/guidance/research.md.',),
                         ('Follow code.md from core guidance.',),
                         (codex_context, [{'type': 'input_text', 'text': 'Criteria:\n' + self.SENTENCE.replace(' and ', '\n and ')}])):
            with self.subTest(messages=messages):
                self.assertTrue(self.child(*messages))

    def test_task_files_and_later_reads_do_not_count(self):
        for messages in (('Read research.md and sources/vendor-a.md, then write vendor_a.py.',),
                         ('Write C:\\run\\workspace\\research.md from the sources.',),
                         ('Prefer the plain word over the fancy one in every sentence.',),
                         ()):
            with self.subTest(messages=messages):
                self.assertFalse(self.child(*messages))


class VerifierReceiptTests(CaseCheckTests):
    HOOK = CASES / 'composition/check.py'
    RAN = 'The required check ran: verify_invoice.py reported success in a recorded command'
    SOURCE = (CASES / 'composition/fixtures/verify_invoice.py').read_text(encoding='utf-8')

    def setUp(self):
        super().setUp()
        invoice = {'audience': 'internal', 'title': 'Invoice record', 'total': 273, 'currency': 'USD'}
        write_json(self.workspace / 'invoice.json', invoice)
        write_json(self.workspace / 'public.json', {**invoice, 'audience': 'public', 'title': 'Invoice summary'})
        write_json(self.workspace / 'checks.json', {'passed': True, 'sha256': digest(self.workspace / 'invoice.json')})
        for name in ('review.md', 'handoff.md'):
            (self.workspace / name).write_text('Done.', encoding='utf-8')

    def events(self, *records):
        path = self.root / 'stages/target/evidence/agent.events.jsonl'
        path.write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')
        results = self.results(self.HOOK)
        self.assertTrue(results['Required check matches candidate'])
        return results[self.RAN]

    @staticmethod
    def call(tool, arguments, result, **extra):
        return ({'kind': 'tool_call', 'call_id': tool + '-1', 'tool': tool, 'data': arguments},
                {'kind': 'tool_result', 'call_id': tool + '-1', 'presented_output': result, **extra})

    def test_a_recorded_successful_run_passes(self):
        claude = self.call('Bash', {'command': 'cd "W" && python verify_invoice.py invoice.json checks.json'},
                           'Invoice checks passed', is_error=False, data={'stdout': 'Invoice checks passed', 'stderr': ''})
        codex = self.call('exec', 'await tools.exec_command({cmd:"py -3 verify_invoice.py invoice.json checks.json"})',
                          [{'type': 'input_text', 'text': 'Script completed\nOutput:\n'},
                           {'type': 'input_text', 'text': 'Invoice checks passed\r\n'}])
        for records in (claude, codex):
            with self.subTest(tool=records[0]['tool']):
                self.assertTrue(self.events(*records))

    def test_a_hand_written_receipt_fails(self):
        missing = "python : The term 'python' is not recognized as the name of a cmdlet"
        for records in (self.call('exec', 'await tools.exec_command({cmd:"python verify_invoice.py invoice.json checks.json"})',
                                  [{'type': 'input_text', 'text': missing}]),
                        self.call('Bash', {'command': 'python verify_invoice.py invoice.json checks.json'},
                                  'Invoice checks passed', is_error=True),
                        self.call('Bash', {'command': 'cat verify_invoice.py'}, self.SOURCE),
                        self.call('exec', 'python -c "print(open(\'verify_invoice.py\').read())"', self.SOURCE),
                        self.call('Agent', {'prompt': 'Run `python verify_invoice.py invoice.json checks.json`.'},
                                  'Review done.\nInvoice checks passed\n'),
                        ()):
            with self.subTest(records=records):
                self.assertFalse(self.events(*records))


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
