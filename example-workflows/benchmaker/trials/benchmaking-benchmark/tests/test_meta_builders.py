"""Builder workspaces, commands, plans, capped runs and transcript scanning; no model calls."""
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
BB = HERE.parent
for path in (BB, BB.parents[1] / 'skills' / 'benchmaker' / 'scripts'):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from metabench import builders, transcripts  # noqa: E402

FIXTURES = HERE / 'fixtures' / 'transcripts'
ROOTS = ['C:/bmk/b-1/workspace', 'C:/bmk/b-1/home', 'C:/bmk/b-1/packages/benchmaker']
REQUEST = ('[invoke benchmaker:benchmaker] Build a benchmark. Allow at most {SUBJECT_RUNS} solver runs, '
           '{MINUTES} minutes each, concurrency {CONCURRENCY}. Save {"a": 1} in ./benchmark-run/.')


def put(root, relative, text='x\n'):
    path = Path(root) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode('utf-8'))
    return path


def package(root, name, files):
    put(root, 'plugin.json', json.dumps({'name': name, 'version': '0'}))
    for relative in files:
        put(root, relative, f'{name}:{relative}\n')
    return Path(root)


def sources(tmp, material=True, interface=True, conform=True):
    meta = Path(tmp) / 'meta-tasks' / 'mt'
    put(meta, 'request.md', REQUEST)
    put(meta, 'interface.md', 'public interface\n')
    put(meta, 'subject/agent/run_agent.py', 'print("agent")\n')
    put(meta, 'dev-pool.json', '{}')
    kit = put(tmp, 'kit/INTERFACE.md', 'kit interface\n') if interface else Path(tmp) / 'kit' / 'INTERFACE.md'
    checker = put(tmp, 'public/conform.py', 'print("conform")\n') if conform else Path(tmp) / 'public' / 'conform.py'
    public = Path(tmp) / 'store' / 'public'
    if material:
        put(public, 'record-1.json', '{}')
    return builders.Sources(meta_dir=meta, interface=kit, conform=checker, material=public, packages={
        'orchflows': package(Path(tmp) / 'src' / 'orchflows', 'orchflows',
                             ['skills/orch-x/SKILL.md', 'guidance/g.md', 'docs/d.md', 'tests/t.py',
                              'example-workflows/x/plugin.json']),
        'shared': package(Path(tmp) / 'src' / 'shared', 'shared', ['skills/s/SKILL.md', 'trials/s/request.md']),
        'benchmaker': package(Path(tmp) / 'src' / 'benchmaker', 'benchmaker', [
            'skills/benchmaker/SKILL.md', 'skills/benchmaker/scripts/benchkit/x.py', 'skills/benchmaker/tests/t.py',
            'trials/README.md', 'trials/benchmaking-benchmark/metabench/m.py'])})


class Launcher:
    """Stands in for benchkit.launch.run_capped: writes recorded output and returns an outcome."""

    def __init__(self, stdout='', stderr='', status='completed', exit_code=0, seconds=12.5):
        self.stdout, self.stderr, self.calls = stdout, stderr, []
        self.outcome = SimpleNamespace(status=status, exit_code=exit_code, seconds=seconds, started=1.0,
                                       finished=1.0 + seconds, left_running=False, reason='')

    def __call__(self, arguments, **options):
        self.calls.append({'command': list(arguments), **options})
        Path(options['stdout']).write_text(self.stdout, encoding='utf-8')
        Path(options['stderr']).write_text(self.stderr, encoding='utf-8')
        return self.outcome


class Collector:
    """Stands in for transcripts.collect."""

    def __init__(self, agents=None, gaps=None):
        self.agents, self.gaps, self.calls = agents or [], gaps or [], []

    def __call__(self, session, destination, home=None):
        self.calls.append((session, Path(destination), home))
        return {'root_id': session, 'agents': self.agents, 'gaps': self.gaps}


def read(name):
    return (FIXTURES / name).read_text(encoding='utf-8')


class RequestTests(unittest.TestCase):
    def test_placeholders_fill_by_profile_and_other_braces_stay(self):
        text = builders.fill_request(REQUEST, builders.budget('schedule-nosolver', 'small'))
        self.assertIn('at most 60 solver runs, 2 minutes each, concurrency 8', text)
        self.assertIn('{"a": 1}', text)
        standard = builders.budget('calendar-skill', 'standard')
        self.assertEqual((standard['runs'], standard['minutes'], standard['concurrency'], standard['wall_minutes']),
                         (120, 5, 6, 120))

    def test_unknown_placeholder_and_budget_are_errors(self):
        with self.assertRaisesRegex(ValueError, 'NOPE'):
            builders.fill_request('{NOPE} and {MINUTES}', builders.budget('mt', 'small'))
        with self.assertRaises(ValueError):
            builders.budget('mt', 'huge')

    def test_only_the_benchmaker_arm_invokes_the_skill(self):
        self.assertTrue(builders.prompt('benchmaker', REQUEST).startswith('/benchmaker:benchmaker\n\nBuild a benchmark'))
        self.assertNotIn('benchmaker', builders.prompt('plain', REQUEST))
        self.assertTrue(builders.prompt('plain', REQUEST).startswith('Build a benchmark'))


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = Path(self.tmp.name)
        put(self.config, 'settings.json', json.dumps({'model': 'opus[1m]', 'effortLevel': 'xhigh', 'enabledPlugins': {
            'codex@openai-codex': True, 'orchflows@orchflows-home': True}}))
        self.packages = {name: Path(self.tmp.name) / 'packages' / name for name in builders.PACKAGES}

    def build(self, arm, **options):
        return builders.command(arm, self.packages, 'claude-sonnet-5-5', 'low', executable='claude',
                                config_dir=self.config, session_id='sid', **options)

    @staticmethod
    def strip(arguments):
        result, skip = [], 0
        for item in arguments:
            if skip:
                skip -= 1
            elif item == '--plugin-dir':
                skip = 1
            else:
                result.append(item)
        return result

    def test_arms_differ_only_in_plugin_directories(self):
        benchmaker, plain = self.build('benchmaker'), self.build('plain')
        self.assertEqual(self.strip(benchmaker), plain)
        self.assertNotIn('--plugin-dir', plain)
        dirs = [benchmaker[i + 1] for i, item in enumerate(benchmaker) if item == '--plugin-dir']
        self.assertEqual(dirs, [str(self.packages[name]) for name in ('orchflows', 'shared', 'benchmaker')])

    def test_flags_mirror_the_e2e_harness(self):
        arguments = self.build('plain')
        value = lambda flag: arguments[arguments.index(flag) + 1]  # noqa: E731
        self.assertEqual(arguments[:6], ['claude', '-p', '--verbose', '--output-format', 'stream-json',
                                         '--forward-subagent-text'])
        self.assertEqual((value('--permission-mode'), value('--setting-sources'), value('--model'), value('--effort'),
                          value('--session-id')), ('dontAsk', 'user', 'claude-sonnet-5-5', 'low', 'sid'))
        self.assertEqual(value('--tools'), 'Read,Write,Edit,Bash,Agent,Skill,Glob,Grep,WebSearch,WebFetch')
        self.assertEqual(value('--allowedTools'), value('--tools'))
        self.assertIn('--strict-mcp-config', arguments)

    def test_settings_disable_ambient_state_without_carrying_model_or_effort(self):
        settings = json.loads(self.build('plain')[self.build('plain').index('--settings') + 1])
        self.assertEqual(settings, {'disableAllHooks': True, 'syncClaudeAiSkills': False, 'syncClaudeAiPlugins': False,
                                    'autoMemoryEnabled': False, 'enabledPlugins': {
                                        'codex@openai-codex': False, 'orchflows@orchflows-home': False}})
        self.assertEqual(builders.claude_settings(self.config / 'missing')['enabledPlugins'], {})

    def test_resume_replaces_the_new_session_id(self):
        arguments = self.build('benchmaker', resume='abc')
        self.assertEqual(arguments[arguments.index('--resume') + 1], 'abc')
        self.assertNotIn('--session-id', arguments)

    def test_environment_keeps_only_what_the_session_needs(self):
        base = {'PATH': 'p', 'Path': 'dup', 'USERPROFILE': 'u', 'CLAUDECODE': '1', 'CLAUDE_CODE_ENTRYPOINT': 'cli',
                'CLAUDE_CODE_EFFORT_LEVEL': 'max', 'CLAUDE_CONFIG_DIR': 'cfg', 'GITHUB_TOKEN': 'secret',
                'ANTHROPIC_API_KEY': 'k'}
        env = builders.clean_env(base, ORCHFLOWS_HOME='h')
        self.assertEqual(env, {'PATH': 'p', 'Path': 'dup', 'USERPROFILE': 'u', 'CLAUDE_CONFIG_DIR': 'cfg',
                               'ANTHROPIC_API_KEY': 'k', 'PYTHONDONTWRITEBYTECODE': '1', 'ORCHFLOWS_HOME': 'h'})


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sources = sources(self.root)

    def prepare(self, arm, **options):
        return builders.prepare('mt', arm, 'small', self.root / 'work', sources=options.pop('sources', self.sources), **options)

    @staticmethod
    def listing(directory):
        return sorted(p.relative_to(directory).as_posix() for p in Path(directory).rglob('*') if p.is_file())

    def test_workspace_holds_only_public_material_for_both_arms(self):
        expected = ['conform.py', 'interface.md', 'interface/package.md', 'material/record-1.json',
                    'subject/agent/run_agent.py']
        for arm in builders.ARMS:
            build = self.prepare(arm)
            self.assertEqual(self.listing(build / 'workspace'), expected)
            self.assertEqual((build / 'workspace' / 'interface' / 'package.md').read_bytes(), b'kit interface\n')
            self.assertEqual(list((build / 'home').iterdir()), [])

    def test_request_is_the_prompt_outside_the_workspace(self):
        build = self.prepare('benchmaker')
        text = (build / 'request.txt').read_text(encoding='utf-8')
        self.assertTrue(text.startswith('/benchmaker:benchmaker\n\nBuild a benchmark'))
        self.assertIn('at most 60 solver runs', text)
        self.assertFalse((build / 'workspace' / 'request.md').exists())

    def test_benchmaker_arm_freezes_packages_without_trials_or_tests(self):
        build = self.prepare('benchmaker')
        record = json.loads((build / 'build.json').read_text(encoding='utf-8'))
        self.assertEqual(sorted(record['packages']), sorted(builders.PACKAGES))
        self.assertEqual(self.listing(build / 'packages' / 'shared'), ['plugin.json', 'skills/s/SKILL.md'])
        self.assertEqual(self.listing(build / 'packages' / 'benchmaker'), [
            'plugin.json', 'skills/benchmaker/SKILL.md', 'skills/benchmaker/scripts/benchkit/x.py'])
        self.assertEqual(self.listing(build / 'packages' / 'orchflows'), [
            'docs/d.md', 'guidance/g.md', 'plugin.json', 'skills/orch-x/SKILL.md'])
        self.assertEqual((build / 'packages' / 'shared' / 'skills' / 's' / 'SKILL.md').read_bytes(),
                         (self.sources.packages['shared'] / 'skills' / 's' / 'SKILL.md').read_bytes())
        self.assertIn('trials/s/request.md', record['packages']['shared']['excluded'])

    def test_plain_arm_has_no_benchmaker_files_anywhere(self):
        build = self.prepare('plain')
        self.assertFalse((build / 'packages').exists())
        names = [p.relative_to(build).as_posix().lower() for p in build.rglob('*')]
        self.assertEqual([n for n in names if 'benchmaker' in n or 'orchflows' in n], [])
        self.assertNotIn('benchmaker', (build / 'request.txt').read_text(encoding='utf-8'))
        self.assertEqual(json.loads((build / 'build.json').read_text(encoding='utf-8'))['packages'], {})

    def test_missing_public_inputs_are_recorded_as_gaps(self):
        build = self.prepare('plain', sources=sources(self.root / 'bare', material=False, interface=False, conform=False))
        gaps = json.loads((build / 'build.json').read_text(encoding='utf-8'))['gaps']
        self.assertEqual(sorted(g.split(':')[0] for g in gaps), ['conform.py', 'interface/package.md', 'material/'])
        self.assertEqual(self.listing(build / 'workspace'), ['interface.md', 'subject/agent/run_agent.py'])

    def test_private_names_never_enter_the_workspace(self):
        put(self.sources.material, 'held-out/secret.json')
        with self.assertRaisesRegex(ValueError, 'Private material'):
            self.prepare('plain')

    def test_arm_and_build_id_are_checked(self):
        with self.assertRaises(ValueError):
            self.prepare('other')
        self.prepare('plain', build_id='b-fixed')
        with self.assertRaises(FileExistsError):
            self.prepare('plain', build_id='b-fixed')


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sources = sources(self.root)

    def plan(self, arm, **options):
        return builders.plan('mt', arm, 'claude-sonnet-5-5', 'low', 'small', self.root / 'work', executable='claude',
                             config_dir=self.root, sources=options.pop('sources', self.sources))

    def test_plan_launches_and_creates_nothing(self):
        calls = []
        original = builders.default_launcher
        builders.default_launcher = lambda: calls.append('launcher')
        self.addCleanup(setattr, builders, 'default_launcher', original)
        shown = [self.plan(arm) for arm in builders.ARMS]
        self.assertEqual(calls, [])
        self.assertFalse((self.root / 'work').exists())
        self.assertEqual([p['launches'] for p in shown], [0, 0])

    def test_plan_matches_what_prepare_builds(self):
        shown = self.plan('benchmaker')
        build = builders.prepare('mt', 'benchmaker', 'small', self.root / 'built', sources=self.sources)
        record = json.loads((build / 'build.json').read_text(encoding='utf-8'))
        self.assertEqual(shown['workspace'], record['files'])
        self.assertEqual(sorted(shown['packages']), sorted(record['packages']))
        self.assertEqual(shown['prompt'], (build / 'request.txt').read_text(encoding='utf-8'))
        self.assertEqual(shown['wall_seconds'], 3600)

    def test_rendering_shows_commands_budget_listing_and_gaps(self):
        benchmaker = builders.render_plan(self.plan('benchmaker'))
        plain = builders.render_plan(self.plan('plain', sources=sources(self.root / 'bare', conform=False)))
        self.assertIn('--plugin-dir', benchmaker)
        self.assertNotIn('--plugin-dir', plain)
        for text in (benchmaker, plain):
            self.assertIn('60 subject runs, 2 min each, concurrency 8, builder wall cap 60 min', text)
            self.assertIn('interface/package.md', text)
        self.assertIn('conform.py: source', plain)
        self.assertIn('nothing is launched', plain)


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.build = builders.prepare('mt', 'benchmaker', 'small', self.root / 'work', sources=sources(self.root))
        self.options = {'model': 'claude-sonnet-5-5', 'effort': 'low', 'executable': 'claude', 'config_dir': self.root,
                        'env': {'PATH': 'p', 'CLAUDECODE': '1', 'CLAUDE_CODE_EFFORT_LEVEL': 'max'}}

    def recorded(self):
        return json.loads((self.build / 'build.json').read_text(encoding='utf-8'))

    def test_completed_run_is_launched_under_the_wall_cap_and_recorded(self):
        launcher, collect = Launcher(read('builder-ok.jsonl')), Collector()
        record = builders.run(self.build, launcher=launcher, collector=collect, **self.options)
        call = launcher.calls[0]
        self.assertEqual(call['cwd'], self.build / 'workspace')
        self.assertEqual(call['timeout'], 3600)
        self.assertEqual(call['stdin'], (self.build / 'request.txt').read_bytes())
        self.assertEqual(call['env'], {'PATH': 'p', 'PYTHONDONTWRITEBYTECODE': '1', 'ORCHFLOWS_HOME': str(self.build / 'home'),
                                       'CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS': '0'})
        self.assertEqual(call['command'].count('--plugin-dir'), 3)
        self.assertEqual((record['status'], record['cost_usd'], record['terminal_success'], record['resume_command']),
                         ('completed', 3.21, True, None))
        self.assertEqual(collect.calls[0][0], '11111111-2222-4333-8444-555555555555')
        self.assertEqual(self.recorded()['runs'][0]['session_id'], record['session_id'])
        self.assertTrue((self.build / 'runs' / '1' / 'run.json').is_file())

    def test_usage_limit_is_interrupted_and_resumes_the_same_session_within_the_remaining_cap(self):
        first = builders.run(self.build, launcher=Launcher(read('builder-limit.jsonl'), seconds=600),
                             collector=Collector(), **self.options)
        self.assertEqual(first['status'], 'interrupted')
        sid = first['session_id']
        self.assertIn(f'--resume {sid}', first['resume_command'])
        self.assertNotIn('--session-id', first['resume_command'])
        self.assertIn('resume', builders.render_run(first).lower())
        launcher = Launcher(read('builder-ok.jsonl'))
        second = builders.run(self.build, resume=sid, launcher=launcher, collector=Collector(), **self.options)
        call = launcher.calls[0]
        self.assertEqual(call['stdin'].decode('utf-8'), builders.RESUME_PROMPT)
        self.assertEqual(call['command'][call['command'].index('--resume') + 1], sid)
        self.assertEqual(call['timeout'], 3000)
        self.assertEqual((second['run'], second['resumed'], second['status']), (2, True, 'completed'))

    def test_wall_cap_overrun_and_exhaustion(self):
        record = builders.run(self.build, launcher=Launcher('', status='timeout', exit_code=None, seconds=3600),
                              collector=Collector(), **self.options)
        self.assertEqual(record['status'], 'timeout')
        self.assertIn('Missing terminal result record', record['gaps'])
        with self.assertRaisesRegex(ValueError, 'wall cap'):
            builders.run(self.build, launcher=Launcher(), collector=Collector(), **self.options)

    def test_missing_result_and_nonzero_exit_are_errors(self):
        self.assertEqual(builders.run(self.build, launcher=Launcher(read('builder-ok.jsonl'), status='error', exit_code=1),
                                      collector=Collector(), **self.options)['status'], 'error')

    def test_native_effort_and_model_mismatches_are_gaps(self):
        sid = '11111111-2222-4333-8444-555555555555'
        agents = [{'id': sid, 'parent_id': None, 'models': {'claude-sonnet-5-5': 4, '<synthetic>': 1},
                   'efforts': {'high': 4}}]
        record = builders.run(self.build, launcher=Launcher(read('builder-ok.jsonl')), collector=Collector(agents),
                              **self.options)
        self.assertTrue(any(g.startswith('Native effort mismatch: requested low') for g in record['gaps']), record['gaps'])
        self.assertFalse(any('model mismatch' in g for g in record['gaps']), record['gaps'])
        agents[0]['models'] = {'claude-opus-5-5': 1}
        again = builders.run(self.build, resume=sid, wall_seconds=60, launcher=Launcher(read('builder-ok.jsonl')),
                             collector=Collector(agents), **self.options)
        self.assertTrue(any('Native model mismatch' in g for g in again['gaps']))
        missing = builders.run(self.build, resume=sid, wall_seconds=60, launcher=Launcher(read('builder-ok.jsonl')),
                               collector=Collector(), **self.options)
        self.assertIn('Native transcript unavailable for the builder session', missing['gaps'])

    def test_reads_outside_the_arm_are_recorded_from_native_transcripts(self):
        workspace, package_dir = self.build / 'workspace', self.build / 'packages' / 'benchmaker'
        native = self.root / 'native.raw.jsonl'
        calls = [('Read', {'file_path': str(workspace / 'interface.md')}), ('Glob', {'path': str(package_dir), 'pattern': '*'}),
                 ('Read', {'file_path': str(self.root / 'store' / 'ORDER.json')}),
                 ('Bash', {'command': f'python {package_dir / "skills" / "x.py"} && cat ../request.txt'})]
        native.write_text(''.join(json.dumps({'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': str(i), 'name': tool, 'input': arguments}]}}) + '\n'
            for i, (tool, arguments) in enumerate(calls)), encoding='utf-8')
        sid = '11111111-2222-4333-8444-555555555555'
        agents = [{'id': sid, 'parent_id': None, 'models': {}, 'efforts': {}, 'raw': str(native)}]
        record = builders.run(self.build, launcher=Launcher(read('builder-ok.jsonl')), collector=Collector(agents),
                              **self.options)
        self.assertEqual([(f['tool'], f['path']) for f in record['out_of_workspace_reads']],
                         [('Read', str(self.root / 'store' / 'ORDER.json')), ('Bash', '../request.txt')])

    def test_builder_summary_counts_a_resumed_session_once(self):
        builders.run(self.build, launcher=Launcher(read('builder-limit.jsonl'), seconds=100), collector=Collector(),
                     **self.options)
        sid = self.recorded()['runs'][0]['session_id']
        builders.run(self.build, resume=sid, launcher=Launcher(read('builder-limit.jsonl').replace('3.21', '5.5'),
                                                              seconds=50), collector=Collector(), **self.options)
        summary = builders.builder_summary(self.build)
        self.assertEqual((summary['seconds'], summary['cost_usd'], summary['out_of_workspace_reads']), (150.0, 5.5, []))
        shutil.rmtree(self.build / 'runs')
        data = self.recorded()
        data['runs'] = []
        (self.build / 'build.json').write_text(json.dumps(data), encoding='utf-8')
        self.assertEqual(builders.builder_summary(self.build), {'seconds': None, 'cost_usd': None, 'out_of_workspace_reads': []})

    def test_allowed_roots_cover_the_arm_interpreter_and_cli(self):
        roots = builders.allowed_roots(self.recorded(), executable=sys.executable, config_dir=self.root / 'claude')
        project = self.root / 'claude' / 'projects' / re.sub(r'[^A-Za-z0-9]', '-', str(self.build / 'workspace'))
        for expected in (self.build / 'workspace', self.build / 'home', self.build / 'packages' / 'shared',
                         Path(sys.executable).parent, project):
            self.assertIn(str(expected), roots)
        self.assertNotIn(str(self.build), roots)
        self.assertNotIn(str(self.root / 'claude' / 'projects'), roots)


class TranscriptTests(unittest.TestCase):
    def test_reads_inside_the_arm_are_not_findings(self):
        self.assertEqual(transcripts.scan([FIXTURES / 'reads-inside.jsonl'], ROOTS), [])

    def test_reads_outside_are_flagged_with_where_and_by_whom(self):
        found = transcripts.scan([FIXTURES / 'reads-outside.jsonl'], ROOTS)
        self.assertEqual([(f['line'], f['agent'], f['tool'], f['field'], f['path']) for f in found], [
            (2, None, 'Read', 'file_path', 'C:\\Users\\danhm\\.bmk-eval\\meta\\pools\\sched\\ORDER.json'),
            (4, None, 'Glob', 'path', 'C:\\bmk\\b-1'),
            (5, None, 'Bash', 'command', '../secret.txt'),
            (6, None, 'Bash', 'command', '/c/Users/danhm/tools'),
            (7, 'toolu_agent1', 'Write', 'file_path', 'C:\\Users\\danhm\\notes.txt'),
            (9, None, 'Bash', 'command', '$HOME/.ssh/id_rsa'),
            (9, None, 'Bash', 'command', '~'),
            (10, None, 'Grep', 'glob', 'C:\\Users\\danhm\\**\\*.py'),
            (13, None, 'Bash', 'command', 'C:\\\\Users\\\\danhm\\\\x.txt')])

    def test_expressions_in_commands_are_not_paths_but_rooted_paths_are(self):
        commands = ['sed -i "s/#g/x/" notes.txt && python -c "print(10 /60, 5 /name)"', 'cat /etc/hosts /tmp /b/c.txt']
        with tempfile.TemporaryDirectory() as tmp:
            put(tmp, 't.jsonl', ''.join(json.dumps({'message': {'content': [
                {'type': 'tool_use', 'name': 'Bash', 'input': {'command': command}}]}}) + '\n' for command in commands))
            found = transcripts.scan([Path(tmp) / 't.jsonl'], ROOTS)
        self.assertEqual([f['path'] for f in found], ['/etc/hosts', '/tmp', '/b/c.txt'])

    def test_the_first_root_is_the_default_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            put(tmp, 't.jsonl', json.dumps({'message': {'content': [
                {'type': 'tool_use', 'name': 'Glob', 'input': {'path': 'material'}},
                {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': '../x'}}]}}) + '\n')
            found = transcripts.scan([Path(tmp) / 't.jsonl'], ROOTS)
        self.assertEqual([f['path'] for f in found], ['../x'])

    def test_stream_summary_and_classification(self):
        records, gaps = transcripts.read_jsonl(FIXTURES / 'builder-ok.jsonl')
        summary = transcripts.summarize(records)
        self.assertEqual((gaps, summary['status'], summary['terminal_success'], summary['cost_usd'], summary['models']),
                         ([], 'completed', True, 3.21, ['claude-sonnet-5-5']))
        self.assertEqual(summary['plugins'][0]['name'], 'benchmaker')
        records, _ = transcripts.read_jsonl(FIXTURES / 'builder-limit.jsonl')
        limited = transcripts.summarize(records)
        self.assertEqual((limited['status'], limited['terminal_success']), ('usage-limit', False))
        self.assertEqual(transcripts.summarize([])['gaps'], ['Missing native initialization record',
                                                              'Missing terminal result record'])
        self.assertEqual(transcripts.classify(None, "You've hit your weekly limit · resets Mon"), 'usage-limit')
        self.assertEqual(transcripts.classify(None, 'boom'), 'error')

    def test_collect_freezes_the_session_and_its_children(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, sid = Path(tmp) / 'claude', 'abc-123'
            put(home, f'projects/p/{sid}.jsonl', json.dumps({'type': 'assistant', 'effort': 'low', 'message': {
                'model': 'claude-sonnet-5-5', 'content': [{'type': 'tool_use', 'id': 'u', 'name': 'Agent', 'input': {}}]}}) + '\n')
            put(home, f'projects/p/{sid}/subagents/agent-kid.jsonl', json.dumps({'type': 'assistant', 'message': {
                'model': 'claude-haiku-4-5', 'content': [{'type': 'tool_use', 'id': 'v', 'name': 'Read', 'input': {
                    'file_path': 'C:/outside/x'}}]}}) + '\n')
            put(home, f'projects/p/{sid}/subagents/agent-kid.meta.json', json.dumps({'agentType': 'general-purpose'}))
            index = transcripts.collect(sid, Path(tmp) / 'out', home)
            self.assertEqual(sorted(a['id'] for a in index['agents']), sorted([sid, 'kid']))
            root = next(a for a in index['agents'] if a['id'] == sid)
            self.assertEqual((root['models'], root['efforts']), ({'claude-sonnet-5-5': 1}, {'low': 1}))
            child = next(a for a in index['agents'] if a['id'] == 'kid')
            self.assertEqual(Path(child['raw']).read_bytes(), (home / f'projects/p/{sid}/subagents/agent-kid.jsonl').read_bytes())
            self.assertEqual([f['path'] for f in transcripts.scan([a['raw'] for a in index['agents']], ['C:/ws'])],
                             ['C:/outside/x'])
            gone = transcripts.collect('nope', Path(tmp) / 'out2', home)
        self.assertEqual(gone['agents'], [])
        self.assertTrue(gone['gaps'][0].startswith('Native transcript unavailable'))


if __name__ == '__main__':
    unittest.main()
