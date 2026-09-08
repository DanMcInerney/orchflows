"""Return and reopening guards at public ticket seams."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from scripts import state_root, tickets, tickets_land
from installer import application, publication
from installer.models import Plan
from tests.test_workspace_cases.common import make_repo, git, commit_in


class LandingPreflightTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        environment = mock.patch.dict(os.environ, dict(os.environ))
        environment.start()
        self.addCleanup(environment.stop)
        os.environ['ORCHFLOWS_WORKTREES_HOME'] = str(self.root / 'worktrees')
        self.main, _ = make_repo(self.root)

    def fixture(self, label, outcome=True):
        goal = self.root / (label + '.md')
        goal.write_text('Deliver one file into the target.')
        minted = tickets._dispatch(['do', label, '--standard', 'orch-code', '--goal-file', str(goal), '--workspace', str(self.main)])
        self.assertNotIn('error', minted, minted)
        tid = minted['do']['id']
        path = state_root.tickets_root() / label / (tid + '.md')
        data = tickets._parse_frontmatter(path.read_text())
        attempt = json.loads(data['dispatch_v1'])['attempts'][-1]
        tree = Path(attempt['workspace_path'])
        tip = commit_in(tree, {label + '.txt': 'work'}, 'delivery')
        if outcome:
            result = tickets._dispatch(['dispatch-outcome', label, tid, '--assignment-seal', data['assignment_seal'], '--dispatch-id', attempt['dispatch_id'], '--by', attempt['owner'], '--note', 'artifact: git:' + tip])
            self.assertNotIn('error', result, result)
        args = ['land', label, tid, '--assignment-seal', data['assignment_seal'], '--dispatch-id', attempt['dispatch_id'], '--outcome-record-id', 'outcome', '--by', 'join', '--status', 'complete']
        return path, args

    def test_wrong_seal_and_missing_outcome_leave_target_and_done_untouched(self):
        for label, code in [('wrong-seal', 'assignment-mismatch'), ('missing-outcome', 'outcome-record-mismatch')]:
            with self.subTest(label=label):
                path, args = self.fixture(label, outcome=label != 'missing-outcome')
                if label == 'wrong-seal':
                    args[args.index('--assignment-seal') + 1] = 'sha256:' + 'f' * 64
                before = git(self.main, 'rev-parse', 'HEAD').strip()
                ticket_before = path.read_bytes()
                with mock.patch.object(tickets_land.tickets_done, 'resolve', wraps=tickets_land.tickets_done.resolve) as done:
                    answer = tickets._dispatch(args)
                self.assertEqual(code, answer.get('code'), answer)
                self.assertEqual(before, git(self.main, 'rev-parse', 'HEAD').strip())
                self.assertFalse((self.main / (label + '.txt')).exists())
                self.assertEqual(ticket_before, path.read_bytes())
                done.assert_not_called()

    def test_stale_attempt_and_conflicting_join_cannot_run_done(self):
        path, args = self.fixture('stale')
        answer = tickets._dispatch(['dispatch-retire', args[1], args[2], '--assignment-seal', args[4], '--dispatch-id', args[6], '--record-id', 'lifecycle:stop'])
        self.assertNotIn('error', answer, answer)
        with mock.patch.object(tickets_land.tickets_done, 'resolve', wraps=tickets_land.tickets_done.resolve) as done:
            refused = tickets._dispatch(args)
        self.assertEqual('stale-attempt', refused.get('code'), refused)
        done.assert_not_called()
        self.assertFalse((self.main / 'stale.txt').exists())
        path, args = self.fixture('conflict')
        joined = tickets._dispatch(['dispatch-join', *args[1:]])
        self.assertNotIn('error', joined, joined)
        args[-1] = 'limited'
        before = git(self.main, 'rev-parse', 'HEAD').strip()
        with mock.patch.object(tickets_land.tickets_done, 'resolve', wraps=tickets_land.tickets_done.resolve) as done:
            refused = tickets._dispatch(args)
        self.assertEqual('idempotency-conflict', refused.get('code'), refused)
        done.assert_not_called()
        self.assertEqual(before, git(self.main, 'rev-parse', 'HEAD').strip())
        self.assertFalse((self.main / 'conflict.txt').exists())


class LifecyclePublicationTests(unittest.TestCase):
    def test_public_reopening_waits_for_publication_and_cancellation_does_not(self):
        with tempfile.TemporaryDirectory() as raw, mock.patch.dict(os.environ, dict(os.environ)):
            root = Path(raw).resolve()
            home = root / 'home'
            os.environ[state_root.ENV_VAR] = str(home / 'state')
            source = root / 'source.py'
            source.write_text('VALUE=1\n')
            plan = Plan(lib_home=home / 'lib', scope_home=home, bin_dir=home / 'bin', receipt_path=home / 'receipt.json', lib_copies=[(source, home / 'lib/module.py')], scripts=[(source, home / 'bin/module.py')])
            application.apply_plan(plan, 'old')
            created = tickets._dispatch(['new', 'resume', 'B1', '--executor', 'orch-do', '--goal', 'Keep pinned work.', '--context', 'Disposable fixture.', '--standard', 'orch-code'])
            self.assertNotIn('error', created, created)
            self.assertNotIn('error', tickets._dispatch(['set-status', 'resume', 'B1', 'failed']))
            ready = root / 'ready'
            script = "from pathlib import Path; import sys; from scripts import tickets; Path(sys.argv[1]).write_text('ready'); result=tickets._dispatch(['set-status','resume','B1','suspended']); print(result); sys.exit('error' in result)"
            processes = []
            real_active = publication._active
            def competing(current, old):
                census = real_active(current, old)
                self.assertEqual([], census)
                process = subprocess.Popen([sys.executable, '-c', script, str(ready)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                processes.append(process)
                deadline = time.monotonic() + 10
                while not ready.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(ready.exists())
                with self.assertRaises(subprocess.TimeoutExpired):
                    process.wait(timeout=0.3)
                cancellation = subprocess.run([sys.executable, 'scripts/tickets.py', 'set-status', 'resume', 'B1', 'failed'], capture_output=True, text=True, timeout=10)
                self.assertEqual(0, cancellation.returncode, cancellation.stdout + cancellation.stderr)
                self.assertEqual([], real_active(current, old))
                return census
            source.write_text('VALUE=2\n')
            try:
                with mock.patch.object(publication, '_active', side_effect=competing):
                    application.apply_plan(plan, 'new')
                output, error = processes[0].communicate(timeout=10)
                self.assertEqual(0, processes[0].returncode, output + error)
                self.assertTrue(real_active(plan, True))
                self.assertEqual('VALUE=2\n', (plan.lib_home / 'module.py').read_text())
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                    process.communicate(timeout=10)
