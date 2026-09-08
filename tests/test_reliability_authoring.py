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
        commands = list(workflows._commands(body))
        judges = [command for command in commands if workflows._command_verb(command) == 'judge']
        self.assertEqual(1, len(judges))
        self.assertIn('--workspace <workspace>', judges[0])


if __name__ == '__main__':
    unittest.main()
