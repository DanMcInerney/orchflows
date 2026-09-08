"""Observable workspace return, raw evidence custody, and bounded operation seams."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from scripts import (state_root, tickets, tickets_adapters, tickets_dispatch_facade,
                     tickets_land, tickets_store, workspace, workspace_custody, workspace_git,
                     workspace_process, workspace_return)
from tests.test_workspace_cases.common import (make_repo, make_ticket, run_workspace,
                                               git, commit_in)
from tests.test_workspace_cases.integration_cases import baseline_of


class ReliabilityWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name).resolve()
        self.environment = mock.patch.dict(os.environ, dict(os.environ))
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.main, self.run_dir = make_repo(self.tmp)

    def candidate(self, tid='T1', executor='orch-do'):
        ticket = make_ticket(self.run_dir, tid, executor=executor)
        answer = run_workspace(self.tmp, 'establish', 'testrun', tid, '--repo', str(self.main))
        self.assertEqual(0, answer.returncode, answer.stdout + answer.stderr)
        return ticket, state_root.candidate_paths('testrun', tid)

    def report(self, ticket, body):
        with ticket.open('a', encoding='utf-8') as handle:
            handle.write('\n## Report\n\n' + body + '\n')

    def command(self, *args):
        answer = tickets._dispatch(list(args))
        self.assertNotIn('error', answer, answer)
        return answer

    def test_standalone_judge_mints_returns_and_lands_without_maker_target(self):
        goal = self.tmp / 'goal.md'
        goal.write_text('Review the fixed repository artifact and return findings.\n')
        base = git(self.main, 'rev-parse', 'HEAD').strip()
        minted = self.command('judge', 'standalone', '--standard', 'orch-code',
                              '--goal-file', str(goal), '--workspace', str(self.main),
                              '--artifacts', 'git:' + base)
        tid = minted['judge']['id']
        ticket = state_root.tickets_root() / 'standalone' / (tid + '.md')
        data = tickets._parse_frontmatter(ticket.read_text(encoding='utf-8'))
        attempt = json.loads(data['dispatch_v1'])['attempts'][0]
        tree = Path(attempt['workspace_path'])
        evidence = tree / '.orch-notes' / 'findings.json'
        evidence.parent.mkdir()
        raw = b'{"findings":[]}\r\n'
        evidence.write_bytes(raw)
        envelope = {
            'protocol': 'orchflows.dispatch.v1', 'run': 'standalone', 'id': tid,
            'assignment_seal': data['assignment_seal'], 'dispatch_id': attempt['dispatch_id'],
            'outcome_record_id': 'outcome', 'by': attempt['owner'],
            'evidence': f'artifact: git:{base}\nfindings: {evidence}\n',
        }
        close = self.tmp / 'outcome.json'
        close.write_text(json.dumps(envelope, sort_keys=True, separators=(',', ':')), encoding='utf-8')
        self.command('dispatch-outcome', 'standalone', tid, '--file', str(close))
        identity = ['standalone', tid, '--assignment-seal', data['assignment_seal'],
                    '--dispatch-id', attempt['dispatch_id'], '--outcome-record-id', 'outcome', '--by', 'review-join']
        refused = tickets._dispatch(['land', *identity])
        self.assertIn('error', refused)
        self.assertIsNone(tickets_store.integration_target('standalone'))
        self.assertEqual(base, git(self.main, 'rev-parse', 'HEAD').strip())
        landed = self.command('land', *identity, '--status', 'complete')
        self.assertEqual('complete', landed['land']['status'])
        steps = {step['step']: step for step in landed['land']['steps']}
        self.assertEqual('evidence-returned', steps['workspace-integrate']['outcome'])
        self.assertEqual('removed', steps['workspace-retire']['outcome'], steps)
        self.assertFalse(tree.exists())
        self.assertEqual(raw, workspace_custody.archived_path('standalone', tid, evidence).read_bytes())
        self.assertIsNone(tickets_store.integration_target('standalone'))
        self.assertEqual(base, git(self.main, 'rev-parse', 'HEAD').strip())
        replayed = self.command('land', *identity, '--status', 'complete')
        self.assertEqual('absent', {s['step']: s for s in replayed['land']['steps']}['workspace-retire']['outcome'])

    def test_judge_return_cannot_change_existing_maker_target(self):
        self.candidate('Maker')
        target = tickets_store.integration_target('testrun')
        ticket, candidate = self.candidate('Judge', 'orch-judge')
        evidence = candidate['path'] / 'findings.md'
        tip = commit_in(candidate['path'], {'findings.md': 'No blockers.\n'}, 'findings')
        self.report(ticket, f'artifact: git:{tip}\nfindings: {evidence}')
        data = tickets._parse_frontmatter(ticket.read_text())
        result = tickets_land._integrate_workspace('testrun', 'Judge', data, 'complete', ticket, 'judge-join')
        self.assertEqual('evidence-returned', result['outcome'])
        self.assertEqual(target, tickets_store.integration_target('testrun'))
        self.assertFalse((self.main / 'findings.md').exists())
        self.assertEqual(evidence.read_bytes(), workspace_custody.archived_path('testrun', 'Judge', evidence).read_bytes())

    def test_raw_scratch_bytes_survive_retirement_and_tampering_refuses_replay(self):
        ticket, candidate = self.candidate()
        evidence = candidate['path'] / '.orch-notes' / 'raw.dat'
        evidence.parent.mkdir()
        raw = b'\x00raw\xff\r\nLF\n'
        evidence.write_bytes(raw)
        self.report(ticket, f'Raw evidence: {evidence}')
        result, code = workspace_return.retire('testrun', 'T1')
        self.assertEqual((0, 'removed'), (code, result['retire']['outcome']))
        self.assertFalse(candidate['path'].exists())
        archived = workspace_custody.archived_path('testrun', 'T1', evidence, sha256=hashlib.sha256(raw).hexdigest())
        self.assertEqual(raw, archived.read_bytes())
        manifest = json.loads(Path(result['retire']['custody']['manifest']).read_text())
        self.assertEqual(str(evidence.resolve()), manifest['files'][0]['source'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest['files'][0]['sha256'])
        archived.write_bytes(b'changed')
        with self.assertRaises(workspace_git.Refused):
            workspace_custody.archived_path('testrun', 'T1', evidence)

    def test_unknown_scratch_and_ignored_runtime_are_retained(self):
        ticket, candidate = self.candidate()
        tree = candidate['path']
        commit_in(tree, {'.gitignore': '.orch/\nruntime/\n'}, 'ignore runtime')
        scratch = tree / '.orch-notes'
        scratch.mkdir()
        known = scratch / 'known.log'
        known.write_bytes(b'known')
        unknown = scratch / 'user.txt'
        unknown.write_bytes(b'unknown user content')
        runtime = tree / 'runtime'
        runtime.mkdir()
        (runtime / 'input.bin').write_bytes(b'opaque runtime')
        self.report(ticket, str(known))
        with self.assertRaises(workspace_git.Refused) as raised:
            workspace_return.retire('testrun', 'T1')
        self.assertEqual(b'unknown user content', unknown.read_bytes())
        self.assertEqual(b'opaque runtime', (runtime / 'input.bin').read_bytes())
        self.assertIn('.orch-notes/user.txt', raised.exception.detail['unknown'])
        self.assertEqual(b'known', workspace_custody.archived_path('testrun', 'T1', known).read_bytes())
        self.assertTrue(tree.exists())

    def test_tracked_dirt_and_lock_refuse_without_false_retirement(self):
        ticket, candidate = self.candidate()
        tree = candidate['path']
        (tree / 'README.md').write_text('user edit')
        with self.assertRaises(workspace_git.Refused):
            workspace_return.retire('testrun', 'T1')
        self.assertEqual('user edit', (tree / 'README.md').read_text())
        git(tree, 'restore', 'README.md')
        git(self.main, 'worktree', 'lock', str(tree), '--reason', 'fixture active handle')
        with self.assertRaises(workspace_git.Refused):
            workspace_return.retire('testrun', 'T1')
        self.assertTrue(tree.exists())
        git(self.main, 'worktree', 'unlock', str(tree))
        self.assertEqual('removed', workspace_return.retire('testrun', 'T1')[0]['retire']['outcome'])

    def test_checkout_conversion_does_not_redefine_producer_evidence_bytes(self):
        git(self.main, 'config', 'core.autocrlf', 'false')
        commit_in(self.main, {'.gitattributes': '*.txt text eol=crlf\n', 'pinned.txt': 'one\ntwo\n'}, 'byte policy')
        ticket, candidate = self.candidate()
        checkout = (candidate['path'] / 'pinned.txt').read_bytes()
        blob = subprocess.run(['git', 'show', 'HEAD:pinned.txt'], cwd=self.main, capture_output=True, check=True, timeout=30).stdout
        self.assertNotEqual(blob, checkout)
        self.assertEqual(b'one\ntwo\n', blob)
        self.assertEqual(b'one\r\ntwo\r\n', checkout)
        note = candidate['path'] / '.orch-notes' / 'producer.bin'
        note.parent.mkdir()
        note.write_bytes(checkout)
        self.report(ticket, str(note))
        result = workspace_custody.archive('testrun', 'T1', candidate['path'])
        self.assertEqual(hashlib.sha256(checkout).hexdigest(), result['files'][0]['sha256'])
        self.assertEqual(checkout, workspace_custody.archived_path('testrun', 'T1', note).read_bytes())

    def test_relative_overrides_refuse_in_two_working_directories(self):
        original = Path.cwd()
        self.addCleanup(os.chdir, original)
        for name, resolver in ((state_root.ENV_VAR, state_root.state_root),
                               (state_root.WORKTREES_ENV_VAR, state_root.worktrees_root)):
            with mock.patch.dict(os.environ, {name: 'relative-location'}):
                for cwd in (self.tmp, self.main):
                    os.chdir(cwd)
                    with self.assertRaises(ValueError):
                        resolver()
            with mock.patch.dict(os.environ, {name: str(self.tmp / 'absolute')}):
                for cwd in (self.tmp, self.main):
                    os.chdir(cwd)
                    self.assertEqual(self.tmp / 'absolute', resolver())

    def test_timeout_leaves_an_explicit_recoverable_git_refusal(self):
        failure = subprocess.TimeoutExpired(['git', 'merge'], 120)
        with mock.patch.object(workspace_process, 'run', side_effect=failure):
            with self.assertRaises(workspace_git.Refused) as raised:
                workspace_git._git(str(self.main), 'merge', 'candidate')
            self.assertEqual(120, raised.exception.detail['timeout'])
            self.assertEqual(str(self.main), raised.exception.detail['cwd'])
            result, refusal = tickets_dispatch_facade._workspace(self.main, 'establish', [])
            self.assertIsNone(result)
            self.assertIn('error', refusal)
            with self.assertRaises(tickets_adapters.AdapterError):
                tickets_adapters.infer_adapter(self.main)
        with self.assertRaises(subprocess.TimeoutExpired):
            workspace_process.run([sys.executable, '-c', 'import time; time.sleep(30)'], capture_output=True, timeout=0.2)

    def test_post_merge_retry_does_not_duplicate_integration(self):
        ticket, candidate = self.candidate()
        commit_in(candidate['path'], {'delivery.txt': 'work'}, 'delivery')
        arguments = ('testrun', 'T1', candidate['path'], candidate['branch'], baseline_of(ticket))
        first, code = workspace_return.integrate(*arguments)
        self.assertEqual((0, 'merged'), (code, first['integrate']['outcome']))
        revision = git(self.main, 'rev-parse', 'HEAD').strip()
        # An interruption before done/join leaves the candidate and merged
        # revision. The retry reads Git ancestry instead of replaying a write.
        second, code = workspace_return.integrate(*arguments)
        self.assertEqual((0, 'replayed'), (code, second['integrate']['outcome']))
        self.assertEqual(revision, git(self.main, 'rev-parse', 'HEAD').strip())
        self.assertTrue(candidate['path'].exists())

    def test_two_runs_share_the_resolved_target_lock_with_bounded_wait(self):
        ticket, candidate = self.candidate()
        commit_in(candidate['path'], {'delivery.txt': 'work'}, 'delivery')
        target = tickets_store.integration_target('testrun')
        tickets_store.record_integration_target('another-run', target['root'], target['branch'])
        program = (
            'import sys; from scripts.workspace_return import integration_lock\n'
            'with integration_lock(sys.argv[1]):\n'
            ' print("locked", flush=True)\n'
            ' sys.stdin.readline()\n'
        )
        child = subprocess.Popen([sys.executable, '-c', program, str(self.main / '.')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            # The event is observed through a bounded reader, never a timing guess.
            observed = []
            reader = threading.Thread(target=lambda: observed.append(child.stdout.readline()), daemon=True)
            reader.start()
            reader.join(10)
            self.assertEqual(['locked\n'], observed)
            with mock.patch.object(workspace_return, 'INTEGRATION_WAIT_SECONDS', 0.1):
                with self.assertRaises(workspace_git.Refused) as raised:
                    workspace_return.integrate('another-run', 'T1', candidate['path'], candidate['branch'], baseline_of(ticket))
            self.assertEqual(str(self.main).lower(), raised.exception.detail['target'].lower())
            self.assertFalse((self.main / 'delivery.txt').exists())
        finally:
            if child.poll() is None:
                child.communicate('\n', timeout=10)
            else:
                child.communicate(timeout=10)
        self.assertEqual(0, child.returncode)
        result, code = workspace_return.integrate('another-run', 'T1', candidate['path'], candidate['branch'], baseline_of(ticket))
        self.assertEqual((0, 'merged'), (code, result['integrate']['outcome']))


    def test_prepare_cli_preserves_explicit_relative_declarations(self):
        with mock.patch.object(workspace.workspace_candidate, 'prepare', return_value=({}, 0)) as prepare:
            workspace._cmd_prepare(['testrun', 'T1', '--package', 'apps/client', '--package', 'tools/compiler', '--tool-directory', 'tools/browser'])
            prepare.assert_called_once_with('testrun', 'T1', packages=('apps/client', 'tools/compiler'), tools=('tools/browser',))
        with self.assertRaises(workspace_git.Refused):
            workspace._cmd_prepare(['testrun', 'T1', '--package'])

    def test_archive_cli_releases_only_referenced_unchanged_scratch(self):
        ticket, candidate = self.candidate()
        source = candidate['path'] / '.orch-notes' / 'check.log'
        source.parent.mkdir()
        source.write_bytes(b'outside check evidence')
        self.report(ticket, str(source))
        answer = run_workspace(self.tmp, 'archive', 'testrun', 'T1', '--release-scratch')
        self.assertEqual(0, answer.returncode, answer.stdout + answer.stderr)
        self.assertFalse(source.exists())
        self.assertEqual(b'outside check evidence', workspace_custody.archived_path('testrun', 'T1', source).read_bytes())
        self.assertTrue(candidate['path'].exists())
        self.assertEqual('removed', workspace_return.retire('testrun', 'T1')[0]['retire']['outcome'])
