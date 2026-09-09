"""Frame declaration and literal invocation evidence at workflow admission."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests._repo_root import ROOT
from tools.validate_support import workflows
from tools.validate_support.packages import Diagnostics


class AuthoringAdmissionTests(unittest.TestCase):
    def _check(self, bodies):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory)
            manifests = {}
            for name, body in bodies.items():
                manifest = package / name / 'SKILL.md'
                manifest.parent.mkdir()
                manifest.write_text(body, encoding='utf-8')
                manifests[name] = manifest
            def resolve(kind, name, **kwargs):
                return {'path': str(manifests[name])}
            diag = Diagnostics()
            with patch.object(workflows.rings, 'resolve', side_effect=resolve), patch.object(workflows.packages, 'ROOT', package):
                workflows._validate_commands(
                    [('public', path) for path in manifests.values()],
                    list(manifests.values()), diag, {},
                )
            return list(diag.lines())

    def test_parented_self_frame_is_a_declaration(self):
        lines = self._check({'helper':
            'tickets.py frame-open run --workflow helper --parent outer\n'})
        self.assertFalse(any(line.startswith('ERROR') for line in lines), lines)
        self.assertTrue(any('unchecked' in line for line in lines), lines)

    def test_second_self_frame_is_recursive(self):
        lines = self._check({'helper':
            'tickets.py frame-open run --workflow helper --parent outer\n'
            'tickets.py frame-open run --workflow helper --parent own\n'})
        self.assertTrue(any('call cycle' in line for line in lines), lines)

    def test_mutual_private_calls_are_recursive(self):
        lines = self._check({
            'left': 'tickets.py frame-open run --workflow right --parent own\n',
            'right': 'tickets.py frame-open run --workflow left --parent own\n',
        })
        self.assertTrue(any('call cycle' in line for line in lines), lines)

    def test_checkpointed_judge_carries_workspace(self):
        body = (ROOT / 'skills/workflows/checkpointed-build/SKILL.md').read_text(encoding='utf-8')
        review = (ROOT / 'skills/workflows/review-delivery/SKILL.md').read_text(encoding='utf-8')

        def assert_carriage(caller, delegated):
            handoff = caller.split('**Review.**', 1)[1].split('\n\n', 1)[0]
            self.assertIn('`review-delivery`', handoff)
            self.assertIn('`workspace`', handoff)
            calls = [command for command in workflows._commands(delegated)
                     if workflows._command_verb(command) in {'judge', 'do'}]
            self.assertEqual(['judge', 'do', 'judge'],
                             [workflows._command_verb(command) for command in calls])
            for command in calls:
                self.assertIn('--workspace <workspace>', command)

        assert_carriage(body, review)
        with self.assertRaises(AssertionError):
            assert_carriage(body.replace('`workspace`', '`lost-workspace`'), review)
        for index in range(3):
            pieces = review.split('--workspace <workspace>')
            pieces[index] += pieces.pop(index + 1)
            with self.subTest(missing_workspace_call=index), self.assertRaises(AssertionError):
                assert_carriage(body, '--workspace <workspace>'.join(pieces))


if __name__ == '__main__':
    unittest.main()
