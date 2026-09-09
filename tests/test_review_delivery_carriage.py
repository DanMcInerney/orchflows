"""Literal review recipes retain caller evidence and workspace semantics."""
from __future__ import annotations

import re
import shlex
import unittest
from pathlib import Path
from unittest import mock

from scripts import rings, tickets
from scripts.tickets_format import _parse_frontmatter, _sections
from tests import test_ticket_review, test_ticket_frames
from tests._repo_root import ROOT
from tools.validate_support.workflows import _commands


class ReviewCarriageTest(unittest.TestCase):
    def setUp(self):
        self.fixture = test_ticket_review.ReviewPolicyTest()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.ring = Path(self.fixture.temporary.name) / 'ring'
        self.ring.mkdir()
        for name, value in [('home_ring', self.ring), ('project_ring', None)]:
            patch = mock.patch.object(rings, name, return_value=value)
            patch.start()
            self.addCleanup(patch.stop)
        item = test_ticket_frames.FramePackageScopeTest._item
        package = item(self.ring, 'workflow', 'packet-flow')
        item(package, 'standard', 'private-quality')
        item(package, 'skill', 'repair-method')
        self.context = self.ring / 'context.md'
        self.marker = 'Standards owner: frozen-owner.md\nPreserve customer export formats.'
        self.context.write_text(self.marker, encoding='utf-8')

    def invoke(self, command, values):
        command = command.replace('[--standard <narrowing> ...]', '--standard private-quality')
        command = command.replace('[', '').replace(']', '')
        for key, value in values.items():
            command = command.replace('<' + key + '>', shlex.quote(str(value)))
        self.assertNotRegex(command, r'<[a-z][a-z-]*>')
        with self.fixture._stubbed_establishment():
            answer = tickets._dispatch(shlex.split(command)[1:])
        self.assertNotIn('error', answer, answer)
        return answer

    def test_recipe_preserves_context_adapter_method_and_private_pins(self):
        f = self.fixture
        recipe = (ROOT / 'skills/workflows/review-delivery/SKILL.md').read_text(encoding='utf-8')
        commands = [c for c in _commands(recipe) if re.match(r'tickets.py (do|judge) ', c)]
        self.assertEqual(3, len(commands))
        for adapter, standard, artifact in [('evidence-store', 'orch-research', 'evidence:packet-one'),
                                            ('document-tree', 'orch-content', 'doc:direction-one'),
                                            ('git', 'orch-code', 'git:' + 'a' * 40)]:
            with self.subTest(adapter=adapter):
                frame = f.callable('frame-open', '--workflow', 'packet-flow',
                                   '--context-file', str(self.context))['frame_open']['id']
                document = f.candidate / adapter
                document.mkdir()
                values = dict(run=f.RUN, frame=frame, standard=standard, workspace=document,
                              bound='5m', isolation='required' if adapter == 'git' else 'none', **{'workspace-adapter': adapter,
                              'context-file': self.context, 'repair-skill': 'repair-method',
                              'critique-goal': f.goal_file, 'repair-goal': f.goal_file,
                              'verification-goal': f.goal_file, 'typed-identity': artifact,
                              'repaired-identity': artifact})
                rows = []
                for command in commands:
                    answer = self.invoke(command, values)
                    verb = 'judge' if 'judge' in answer else 'do'
                    ticket_id = answer[verb]['id']
                    text = f.ticket_text(ticket_id)
                    data = _parse_frontmatter(text)
                    rows.append(data)
                    self.assertIn(self.marker, _sections(text)['Context'])
                    self.assertEqual(adapter, data['workspace_adapter'])
                    self.assertEqual('packet-flow', data['workflow'])
                    self.assertEqual(values['isolation'], data['isolation'])
                    self.assertIn('`### ' + artifact.split(':')[0] + '`', answer[verb]['launch']['prompt'])
                    self.assertIn('private-quality@sha256:', str(data['standards']))
                    if verb == 'do':
                        self.assertEqual('repair-method', data['skill'])
                    else:
                        self.assertIn(artifact, _sections(text)['Context'])
                    values['critique-ticket'] = values.get('critique-ticket', ticket_id)
                    f.finish_fixture(ticket_id)
                self.assertEqual(['critique', 'repair', 'verify'], [r['review_phase'] for r in rows])
                self.assertEqual(1, len({str(r['standards']) for r in rows}))
                self.assertEqual(1, len({r['workflow_digest'] for r in rows}))
                # Same command without caller carriage reproduces the original
                # wrong adapter/Context, proving these observations can fail.
                other = f.callable('frame-open', '--workflow', 'packet-flow')['frame_open']['id']
                stripped = re.sub(r'--context-file <context-file>|--workspace-adapter <workspace-adapter>', '', commands[0])
                bad = self.invoke(stripped, dict(values, frame=other))['judge']['id']
                self.assertNotIn(self.marker, _sections(f.ticket_text(bad))['Context'])
                self.assertEqual('git', _parse_frontmatter(f.ticket_text(bad))['workspace_adapter'])

    def test_independent_game_and_video_stage_commands_forward_effective_rounds(self):
        f = self.fixture
        for name in ('3d-browser-game', 'orchflows-videos'):
            body = (ROOT / 'example-workflows' / name / 'SKILL.md').read_text(encoding='utf-8')
            stages = [c for c in _commands(body) if '--review-new-work' in c]
            self.assertEqual(3 if name == '3d-browser-game' else 2, len(stages))
            for setting in ('1', '2', 'until_pass'):
                owner = f.owner('--review-rounds', setting)
                for command in stages:
                    # Package fixtures test resolution separately; preserve the
                    # literal policy carriers while substituting a local stage.
                    command = re.sub(r'--workflow [a-z-]+', '--workflow packet-flow', command)
                    values = {key: f.goal_file for key in re.findall(r'<([^>]+)>', command)}
                    values.update(run=f.RUN, frame=owner, rounds=setting,
                                  **{'direction-context': self.context, 'production-context': self.context})
                    stage = self.invoke(command, values)['frame_open']['id']
                    self.assertEqual(setting, str(_parse_frontmatter(f.ticket_text(stage))['review_rounds']))
                if setting == '2':
                    stripped = re.sub(r'--review-rounds <rounds>', '', command)
                    stage = self.invoke(stripped, values)['frame_open']['id']
                    self.assertEqual('1', str(_parse_frontmatter(f.ticket_text(stage))['review_rounds']))
