"""Semantic Context reaches sealed callable and frame tickets before dispatch."""
from pathlib import Path
from scripts import tickets
from scripts.tickets_format import _parse_frontmatter, _sections
from scripts.tickets_generations import assignment_digest
from tests.test_ticket_callables import CallableSinkTest, CODE_STANDARD

class CallableContextTest(CallableSinkTest):
    def test_context_survives_builder_frame_planner_maker_and_judge(self):
        context = Path(self.temporary.name) / 'context.md'
        owner = '- authoring-owner: C:/source/docs/custom-workflow-authoring.md'
        context.write_text(owner, encoding='utf-8')
        frame = self.callable('frame-open', '--workflow', 'orch-build-workflow',
                              '--context-file', str(context))['frame_open']
        nested = self.callable('frame-open', '--workflow', 'checkpointed-build',
                               '--parent', frame['id'], '--context-file', str(context))['frame_open']
        ids = [frame['id'], nested['id']]
        for verb, extra in (('do', ('--makes', 'cut')), ('do', ()),
                            ('judge', ('--artifacts', 'git:' + '1' * 40))):
            answer = self.callable(verb, '--standard', CODE_STANDARD,
                '--parent', nested['id'], '--context-file', str(context), *extra)[verb]
            ids.append(answer['id'])
            content = _sections(self.ticket_text(answer['id']))['Context']
            self.assertIn('- parent: ' + nested['id'], content)
            if verb == 'judge':
                self.assertIn('- artifact: git:' + '1' * 40, content)
        for ticket_id in ids:
            text = self.ticket_text(ticket_id)
            self.assertIn(owner, _sections(text)['Context'])
            self.assertEqual(_parse_frontmatter(text)['assignment_seal'],
                             assignment_digest(ticket_id, text))
            self.assertNotEqual(assignment_digest(ticket_id, text),
                               assignment_digest(ticket_id, text.replace(owner, '- omitted')))

    def test_unreadable_context_refuses_before_ticket_creation(self):
        for verb, extra in (('do', ('--standard', CODE_STANDARD)),
                            ('judge', ('--standard', CODE_STANDARD, '--artifacts', 'git:abc')),
                            ('frame-open', ('--workflow', 'checkpointed-build'))):
            answer = self.callable(verb, '--context-file', str(Path(self.temporary.name) / 'absent'),
                                   *extra, expect_error=True)
            self.assertIn('context file', answer['error'])
            self.assertFalse(self.run_dir().exists())
