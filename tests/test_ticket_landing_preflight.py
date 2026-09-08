"""Return and reopening guards at public ticket seams."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import state_root, tickets, tickets_land
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
