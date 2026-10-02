"""LLM pool members: command lines, harness defects and recorded-result parsing; no model calls."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
BB = HERE.parent
for path in (BB, BB.parents[1] / 'skills' / 'benchmaker' / 'scripts'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from metabench.members import llm  # noqa: E402

FIXTURES = HERE / 'fixtures' / 'transcripts'
INSTRUCTION = 'Book the meeting described in input.json.\n'
ANSWER = {'start': '2026-10-05T10:00+02:00', 'end': '2026-10-05T10:30+02:00', 'room': 'r1'}
SKILL_MD = ('---\nname: booking-rules\ndescription: >\n  Apply the team booking policy\n  when booking meetings.\n'
            'allowed-tools: Read\n---\nBody text.\n')


def put(root, relative, text):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode('utf-8'))
    return path


def spec(**fields):
    return {'kind': 'llm', 'mode': 'single-call', 'model': 'claude-haiku-4-5', 'effort': 'low', 'harness_defect': None,
            **fields}


class Launcher:
    """Stands in for benchkit.launch.run_capped, replaying a recorded result file."""

    def __init__(self, fixture='llm-ok.jsonl', status='completed', exit_code=0, stderr='', seen=None):
        self.output = (FIXTURES / fixture).read_text(encoding='utf-8') if fixture else ''
        self.stderr, self.seen, self.calls = stderr, seen, []
        self.outcome = SimpleNamespace(status=status, exit_code=exit_code, seconds=1.234, started=1.0, finished=2.2,
                                       left_running=False, reason='')

    def __call__(self, arguments, **options):
        self.calls.append({'command': list(arguments), **options})
        if self.seen:
            self.seen(list(arguments))
        Path(options['stdout']).write_text(self.output, encoding='utf-8')
        Path(options['stderr']).write_text(self.stderr, encoding='utf-8')
        return self.outcome


class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / 'ws'
        self.workspace.mkdir()


class CommandTests(unittest.TestCase):
    def test_single_call_is_safe_mode_without_tools(self):
        self.assertEqual(llm.command(spec(), executable='claude'), [
            'claude', '-p', '--safe-mode', '--model', 'claude-haiku-4-5', '--effort', 'low', '--permission-mode',
            'dontAsk', '--tools', '', '--no-session-persistence', '--output-format', 'json'])
        sonnet = llm.command(spec(model='claude-sonnet-5-5'), executable='claude')
        self.assertEqual(sonnet[sonnet.index('--model') + 1], 'claude-sonnet-5-5')

    def test_agent_without_a_skill_is_safe_mode_with_the_agent_tools(self):
        tools = 'Read,Write,Edit,Bash,Glob,Grep'
        self.assertEqual(llm.command(spec(mode='agent'), executable='claude'), [
            'claude', '-p', '--safe-mode', '--model', 'claude-haiku-4-5', '--effort', 'low', '--permission-mode',
            'dontAsk', '--tools', tools, '--allowedTools', tools, '--no-session-persistence', '--output-format', 'json'])

    def test_agent_with_a_skill_loads_the_plugin_and_disables_ambient_state(self):
        with tempfile.TemporaryDirectory() as config:
            put(config, 'settings.json', json.dumps({'enabledPlugins': {'codex@openai-codex': True}}))
            arguments = llm.command(spec(mode='agent'), skill='C:\\skills\\booking', executable='claude',
                                    config_dir=config)
        self.assertNotIn('--safe-mode', arguments)
        self.assertEqual(arguments[arguments.index('--plugin-dir') + 1], 'C:\\skills\\booking')
        self.assertEqual(arguments[arguments.index('--tools') + 1], 'Read,Write,Edit,Bash,Glob,Grep,Skill')
        self.assertEqual(arguments[arguments.index('--setting-sources') + 1], 'user')
        self.assertIn('--strict-mcp-config', arguments)
        settings = json.loads(arguments[arguments.index('--settings') + 1])
        self.assertEqual((settings['disableAllHooks'], settings['autoMemoryEnabled'], settings['enabledPlugins']),
                         (True, False, {'codex@openai-codex': False}))

    def test_skill_defect_names_the_plugin_and_defects_must_match_the_mode(self):
        self.assertEqual(llm.skill_of(spec(mode='agent', harness_defect='skill:C:\\x\\harmful')), 'C:\\x\\harmful')
        self.assertEqual(llm.skill_of(spec(mode='agent', skill='s', harness_defect='skill_hidden')), 's')
        self.assertIsNone(llm.skill_of(spec(mode='agent')))
        with self.assertRaises(ValueError):
            llm.defect_of(spec(harness_defect='skill_hidden'))
        with self.assertRaises(ValueError):
            llm.defect_of(spec(mode='agent', harness_defect='last_chars:10'))
        with self.assertRaises(ValueError):
            llm.defect_of(spec(harness_defect='bogus'))
        with self.assertRaises(ValueError):
            llm.defect_of(spec(mode='workflow'))


class PromptTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        participants = [{'id': 'ana', 'busy': [{'start': str(i)} for i in range(5)]},
                        {'id': 'bo', 'busy': [{'start': 'x'}]}, {'id': 'cy', 'busy': []}]
        put(self.workspace, 'input.json', json.dumps({'participants': participants, 'preference': 'earliest'}))
        put(self.workspace, 'output.json', 'old answer')
        put(self.workspace, '.git/config', 'ignored')

    @staticmethod
    def busy(prompt):
        data = json.loads(prompt.split('=== input.json ===\n')[1].split('\n\nReply with')[0])
        return [len(p['busy']) for p in data['participants']]

    def test_prompt_is_the_instruction_the_inputs_and_the_reply_format(self):
        prompt, applied = llm.single_call_prompt(spec(), INSTRUCTION, self.workspace)
        self.assertTrue(prompt.startswith(INSTRUCTION.rstrip()))
        self.assertEqual(self.busy(prompt), [5, 1, 0])
        self.assertTrue(prompt.endswith(
            'Reply with the complete content of output.json as a single JSON value and nothing else.'))
        self.assertNotIn('old answer', prompt)
        self.assertNotIn('ignored', prompt)
        self.assertFalse(applied)

    def test_truncate_busy_keeps_the_first_share_of_each_list(self):
        prompt, applied = llm.single_call_prompt(spec(harness_defect='truncate_busy:0.6'), INSTRUCTION, self.workspace)
        self.assertEqual(self.busy(prompt), [3, 0, 0])
        self.assertTrue(applied)
        self.assertIn('"preference": "earliest"', prompt)
        self.assertFalse(llm.single_call_prompt(spec(harness_defect='truncate_busy:1.0'), INSTRUCTION,
                                                self.workspace)[1])

    def test_last_chars_keeps_the_tail_and_the_original_line_numbers(self):
        put(self.workspace, 'build.log', ''.join(f'line {n}\n' for n in range(1, 201)))
        numbered = {'inputs': ['build.log'], 'number_lines': True, 'output': 'triage.json'}
        full, applied = llm.single_call_prompt(spec(io=numbered), INSTRUCTION, self.workspace)
        self.assertEqual((full.count('\n1: line 1\n'), '200: line 200' in full, applied), (1, True, False))
        tail, applied = llm.single_call_prompt(spec(io=numbered, harness_defect='last_chars:60'), INSTRUCTION,
                                               self.workspace)
        shown = tail.split('=== build.log ===\n')[1].split('\n\nReply with')[0].splitlines()
        self.assertTrue(applied)
        self.assertEqual(shown[-1], '200: line 200')
        self.assertEqual([int(line.split(':')[0]) for line in shown], list(range(200 - len(shown) + 1, 201)))
        self.assertLessEqual(sum(len(line.split(': ', 1)[1]) + 1 for line in shown), 61)
        self.assertNotIn('1: line 1\n', tail)
        self.assertFalse(llm.single_call_prompt(spec(io=numbered, harness_defect='last_chars:99999'), INSTRUCTION,
                                                self.workspace)[1])

    def test_unnumbered_lines_drops_the_prefixes_only_where_numbering_applies(self):
        put(self.workspace, 'build.log', 'alpha\nbeta\n')
        io = {'inputs': ['build.log'], 'number_lines': True, 'output': 'triage.json'}
        prompt, applied = llm.single_call_prompt(spec(io=io, harness_defect='unnumbered_lines'), INSTRUCTION,
                                                 self.workspace)
        self.assertIn('=== build.log ===\nalpha\nbeta\n', prompt)
        self.assertTrue(applied)
        self.assertIn('1: alpha\n2: beta', llm.single_call_prompt(spec(io=io), INSTRUCTION, self.workspace)[0])
        self.assertFalse(llm.single_call_prompt(spec(harness_defect='unnumbered_lines'), INSTRUCTION,
                                                self.workspace)[1])

    def test_text_output_asks_for_plain_text(self):
        prompt, _ = llm.single_call_prompt(spec(io={'inputs': ['input.json'], 'output': 'answer.txt'}), INSTRUCTION,
                                           self.workspace)
        self.assertTrue(prompt.endswith('Reply with the complete content of answer.txt as plain text and nothing else.'))


class ReplyTests(unittest.TestCase):
    def test_json_is_found_bare_fenced_or_embedded(self):
        self.assertEqual(llm.extract_json(' {"a": 1} '), {'a': 1})
        self.assertEqual(llm.extract_json('Sure:\n```json\n{"a": [1, 2]}\n```\nbye'), {'a': [1, 2]})
        self.assertEqual(llm.extract_json('The answer is {"a": {"b": 2}} as asked, not {broken'), {'a': {'b': 2}})
        self.assertEqual(llm.extract_json('[1, 2]'), [1, 2])
        with self.assertRaises(ValueError):
            llm.extract_json('no structured answer here')

    def test_text_output_loses_only_a_surrounding_fence(self):
        self.assertEqual(llm.deliver('```\nhello\nworld\n```', 'a.txt'), b'hello\nworld')
        self.assertEqual(llm.deliver(' plain ', 'a.txt'), b'plain')
        self.assertEqual(llm.deliver('{"b": 1,\n "a": "\u00e9"}', 'a.json'), '{"b": 1, "a": "\u00e9"}'.encode('utf-8'))


class SkillTests(WorkspaceCase):
    def test_hidden_descriptions_replace_folded_and_plain_ones_and_keep_the_rest(self):
        self.assertEqual(llm.hide_description(SKILL_MD), '---\nname: booking-rules\nallowed-tools: Read\n'
                         f'description: {llm.HIDDEN_DESCRIPTION}\n---\nBody text.\n')
        self.assertIn('description: ' + llm.HIDDEN_DESCRIPTION, llm.hide_description('---\ndescription: Use me.\n---\nx'))
        with self.assertRaises(ValueError):
            llm.hide_description('no frontmatter')

    def test_hidden_copy_leaves_the_source_alone(self):
        source = self.root / 'plugin'
        put(source, '.claude-plugin/plugin.json', '{"name": "booking-rules"}')
        put(source, 'skills/booking-rules/SKILL.md', SKILL_MD)
        put(source, 'skills/booking-rules/scripts/free_slots.py', 'print(1)\n')
        copy = llm.hidden_copy(source, self.root / 'copy')
        self.assertEqual((source / 'skills/booking-rules/SKILL.md').read_text(encoding='utf-8'), SKILL_MD)
        self.assertEqual((copy / 'skills/booking-rules/scripts/free_slots.py').read_bytes(), b'print(1)\n')
        self.assertIn(llm.HIDDEN_DESCRIPTION, (copy / 'skills/booking-rules/SKILL.md').read_text(encoding='utf-8'))


class RunTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        put(self.workspace, 'input.json', '{"participants": []}')
        self.env = {'PATH': 'p', 'CLAUDECODE': '1', 'CLAUDE_CODE_EFFORT_LEVEL': 'max', 'GITHUB_TOKEN': 's'}

    def run_member(self, launcher, member=None):
        return llm.run(member or spec(), workspace=self.workspace, prompt=INSTRUCTION, timeout=120, launcher=launcher,
                       executable='claude', env=self.env)

    def output(self):
        return json.loads((self.workspace / 'output.json').read_text(encoding='utf-8'))

    def test_single_call_writes_the_reply_as_the_output_file(self):
        launcher = Launcher('llm-ok.jsonl')
        result = self.run_member(launcher)
        call = launcher.calls[0]
        self.assertEqual((call['cwd'], call['timeout'], call['env']),
                         (self.workspace, 120, {'PATH': 'p', 'PYTHONDONTWRITEBYTECODE': '1'}))
        self.assertIn('=== input.json ===', call['stdin'].decode('utf-8'))
        self.assertEqual(self.output(), ANSWER)
        self.assertEqual((result['status'], result['exit_code'], result['model'], result['cost_usd'], result['wrote']),
                         ('completed', 0, 'claude-haiku-4-5-20251001', 0.0187, ['output.json']))
        self.assertEqual(result['behavior_draw'], 'llm:single-call:claude-haiku-4-5:low')
        self.assertEqual((result['findings'], llm.EXIT_CODES[result['status']]), ([], 0))
        self.assertEqual(sorted(p.name for p in self.workspace.iterdir()), ['input.json', 'output.json'])

    def test_embedded_and_array_results_parse(self):
        self.run_member(Launcher('llm-embedded.jsonl'))
        self.assertTrue(self.output()['infeasible'])
        self.assertEqual(self.run_member(Launcher('llm-array.jsonl'))['cost_usd'], 0.0101)
        self.assertEqual(self.output(), ANSWER)

    def test_a_reply_without_json_leaves_no_output(self):
        result = self.run_member(Launcher('llm-prose.jsonl'))
        self.assertEqual(result['status'], 'completed')
        self.assertFalse((self.workspace / 'output.json').exists())
        self.assertIn('No output.json written', result['note'])

    def test_recorded_failures_map_to_protocol_statuses(self):
        expected = {'llm-limit.jsonl': ('usage-limit', 3), 'llm-error.jsonl': ('error', 1),
                    'llm-refusal.jsonl': ('refused', 0), 'llm-cutoff.jsonl': ('cut-off', 0)}
        for fixture, (status, code) in expected.items():
            with self.subTest(fixture):
                result = self.run_member(Launcher(fixture))
                self.assertEqual((result['status'], llm.EXIT_CODES[result['status']]), (status, code))
                self.assertEqual(result['wrote'], [])
        self.assertFalse((self.workspace / 'output.json').exists())

    def test_limit_text_on_stderr_without_a_result_is_a_usage_limit(self):
        result = self.run_member(Launcher(None, status='error', exit_code=1, stderr="You've hit your weekly limit"))
        self.assertEqual(result['status'], 'usage-limit')
        self.assertEqual(self.run_member(Launcher(None, status='error', exit_code=1, stderr='boom'))['stderr'], 'boom')

    def test_timeout_and_crash_outcomes_win_over_a_clean_record(self):
        timed_out = self.run_member(Launcher('llm-ok.jsonl', status='timeout', exit_code=None))
        self.assertEqual((timed_out['status'], llm.EXIT_CODES[timed_out['status']]), ('timeout', 2))
        self.assertEqual(self.run_member(Launcher('llm-ok.jsonl', status='error', exit_code=1))['status'], 'error')

    def test_harness_defect_is_recorded_in_the_draw_and_changes_the_prompt(self):
        put(self.workspace, 'input.json', json.dumps({'participants': [{'busy': [1, 2, 3, 4, 5]}]}))
        launcher = Launcher('llm-ok.jsonl')
        result = self.run_member(launcher, spec(harness_defect='truncate_busy:0.6'))
        self.assertIn('"busy": [\n        1,\n        2,\n        3\n      ]', launcher.calls[0]['stdin'].decode('utf-8'))
        self.assertEqual(result['behavior_draw'], 'llm:single-call:claude-haiku-4-5:low:truncate_busy:applied=true')

    def test_agent_member_leaves_the_workspace_to_the_agent(self):
        launcher = Launcher('llm-ok.jsonl')
        result = self.run_member(launcher, spec(mode='agent'))
        self.assertEqual(launcher.calls[0]['stdin'], INSTRUCTION.encode('utf-8'))
        self.assertIn('--safe-mode', launcher.calls[0]['command'])
        self.assertEqual((result['status'], result['wrote']), ('completed', []))
        self.assertFalse((self.workspace / 'output.json').exists())

    def test_hidden_skill_loads_a_copy_that_never_matches_and_is_removed_afterwards(self):
        source = self.root / 'plugin'
        put(source, 'skills/booking-rules/SKILL.md', SKILL_MD)
        seen = {}

        def look(arguments):
            plugin = Path(arguments[arguments.index('--plugin-dir') + 1])
            seen['plugin'] = plugin
            seen['text'] = (plugin / 'skills/booking-rules/SKILL.md').read_text(encoding='utf-8')

        result = self.run_member(Launcher('llm-ok.jsonl', seen=look),
                                 spec(mode='agent', skill=str(source), harness_defect='skill_hidden'))
        self.assertIn(llm.HIDDEN_DESCRIPTION, seen['text'])
        self.assertNotEqual(seen['plugin'], source)
        self.assertFalse(seen['plugin'].exists())
        self.assertEqual((source / 'skills/booking-rules/SKILL.md').read_text(encoding='utf-8'), SKILL_MD)
        self.assertEqual(result['behavior_draw'], 'llm:agent:claude-haiku-4-5:low:skill_hidden:applied=true')
        with self.assertRaises(ValueError):
            self.run_member(Launcher(), spec(mode='agent', harness_defect='skill_hidden'))

    def test_a_loaded_skill_passes_the_plugin_directory_itself(self):
        source = self.root / 'plugin'
        put(source, 'skills/booking-rules/SKILL.md', SKILL_MD)
        launcher = Launcher('llm-ok.jsonl')
        self.run_member(launcher, spec(mode='agent', harness_defect=f'skill:{source}'))
        command = launcher.calls[0]['command']
        self.assertEqual(command[command.index('--plugin-dir') + 1], str(source))
        self.assertNotIn('--safe-mode', command)

    def test_several_models_in_one_result_report_the_requested_model(self):
        launcher = Launcher('llm-ok.jsonl')
        record = json.loads(launcher.output)
        record['modelUsage']['claude-haiku-4-5-20251001-helper'] = {}
        launcher.output = json.dumps(record)
        result = self.run_member(launcher)
        self.assertEqual((result['model'], len(result['models'])), ('claude-haiku-4-5', 2))


if __name__ == '__main__':
    unittest.main()
