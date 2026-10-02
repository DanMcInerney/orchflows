"""Builder sessions for the benchmarking benchmark.

A build is a workspace of public material, a private ORCHFLOWS_HOME and, for the Benchmaker arm, frozen copies
of the orchflows, shared and benchmaker packages. The Claude command mirrors tests/e2e/hosts/claude.py: explicit
packages, settings that disable hooks, auto-memory and ambient plugins, and the same tools for both arms.
`plan` shows everything and launches nothing; `run` launches under a wall cap and records what the session read."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

from . import transcripts

ARMS = ('benchmaker', 'plain')
PACKAGES = ('orchflows', 'shared', 'benchmaker')
ENTRYPOINT = 'benchmaker:benchmaker'
TOOLS = 'Read,Write,Edit,Bash,Agent,Skill,Glob,Grep,WebSearch,WebFetch'
RESUME_PROMPT = ('Continue the build from the current state on disk. Launches already made, including interrupted '
                 'ones, still count toward the limits in the request.')
# Sessions inherit nothing else from the caller. The last five name where Claude finds its credentials.
ENV_KEEP = {'PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'TMPDIR', 'USERPROFILE', 'USERNAME',
            'HOME', 'HOMEDRIVE', 'HOMEPATH', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA', 'PROGRAMFILES',
            'PROGRAMFILES(X86)', 'SHELL', 'LANG', 'LC_ALL', 'TERM', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN',
            'ANTHROPIC_BASE_URL', 'CLAUDE_CONFIG_DIR', 'CLAUDE_CODE_OAUTH_TOKEN'}
# Names that must never reach a builder workspace.
PRIVATE_NAMES = {'held-out', 'split.json', 'ORDER.json', 'private_members', 'reference-packages', 'slices', 'pools'}
PLACEHOLDER = re.compile(r'\{([A-Z_]+)\}')
INVOKE = re.compile(r'\[invoke [^\]]+\]\s*')

# Subject runs, minutes per run, concurrency and the builder session wall cap, by profile.
PROFILES = {'standard': {'runs': 120, 'minutes': 2, 'concurrency': 8, 'wall_minutes': 90},
            'small': {'runs': 60, 'minutes': 2, 'concurrency': 8, 'wall_minutes': 60}}
OVERRIDES = {'logtriage-llm': {'standard': {'runs': 150}},
             'calendar-skill': {'standard': {'minutes': 5, 'concurrency': 6, 'wall_minutes': 120},
                                'small': {'minutes': 5, 'concurrency': 6}}}


def budget(meta_task, name):
    if name not in PROFILES:
        raise ValueError(f'Unknown budget {name!r}; use one of {sorted(PROFILES)}')
    return {**PROFILES[name], **OVERRIDES.get(meta_task, {}).get(name, {})}


def fill_request(text, sizes):
    """Fill the budget placeholders of a request; any other all-caps placeholder is an error."""
    values = {'SUBJECT_RUNS': sizes['runs'], 'MINUTES': sizes['minutes'], 'CONCURRENCY': sizes['concurrency'],
              'WALL_MINUTES': sizes['wall_minutes']}
    unknown = sorted({name for name in PLACEHOLDER.findall(text) if name not in values})
    if unknown:
        raise ValueError('Unfilled request placeholders: ' + ', '.join(unknown))
    return PLACEHOLDER.sub(lambda match: str(values[match.group(1)]), text)


PLAIN_NOTE = ("interface/package.md describes a runner kit that is not in your workspace: its layout and record formats "
              "still apply, and the package's own run.py and records are yours to write.")


def prompt(arm, request):
    """The same request for both arms; the Benchmaker arm starts with the explicit skill invocation and has the kit, the
    plain arm is told the kit the interface page describes is not there."""
    request = INVOKE.sub('', request).lstrip()
    return f'/{ENTRYPOINT}\n\n{request}' if arm == 'benchmaker' else f'{request}\n\n{PLAIN_NOTE}'


def claude_config_dir(env=None):
    env = os.environ if env is None else env
    return Path(env.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude').expanduser()


def claude_settings(config_dir=None):
    """Disable hooks, auto-memory, synced claude.ai skills and every plugin the user's settings enable."""
    path = Path(config_dir or claude_config_dir()) / 'settings.json'
    try:
        plugins = json.loads(path.read_text(encoding='utf-8')).get('enabledPlugins', {})
    except (OSError, ValueError, AttributeError):
        plugins = {}
    return {'disableAllHooks': True, 'syncClaudeAiSkills': False, 'syncClaudeAiPlugins': False,
            'autoMemoryEnabled': False, 'enabledPlugins': {name: False for name in plugins}}


def clean_env(base=None, **extra):
    base = os.environ if base is None else base
    env = {key: value for key, value in base.items() if key.upper() in ENV_KEEP}
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env.update(extra)
    return env


def command(arm, packages, model, effort, *, session_id=None, resume=None, executable=None, config_dir=None):
    """The builder session command; the prompt goes to stdin. The plain arm never gets a plugin directory."""
    session = ['--resume', resume] if resume else ['--session-id', session_id or str(uuid.uuid4())]
    result = [executable or shutil.which('claude') or 'claude', '-p', '--verbose', '--output-format', 'stream-json',
              '--forward-subagent-text', *session, '--permission-mode', 'dontAsk', '--tools', TOOLS,
              '--allowedTools', TOOLS, '--strict-mcp-config', '--setting-sources', 'user',
              '--settings', json.dumps(claude_settings(config_dir)), '--model', model, '--effort', effort]
    for path in packages.values() if arm == 'benchmaker' else ():
        result += ['--plugin-dir', str(path)]
    return result


def render_command(arguments):
    return subprocess.list2cmdline(arguments) if os.name == 'nt' else shlex.join(arguments)


@dataclass
class Sources:
    """Where a build's public inputs come from; every field can be replaced for tests."""
    meta_dir: Path
    interface: Path
    conform: Path
    material: Path | None = None
    packages: dict = field(default_factory=dict)


def default_store(env=None):
    env = os.environ if env is None else env
    return Path(env.get('METABENCH_STORE') or Path.home() / '.bmk-eval' / 'meta')


def default_sources(meta_task, store=None):
    here = Path(__file__).resolve()
    bb, bm, repo = here.parents[1], here.parents[3], here.parents[5]
    kit = bm / 'skills' / 'benchmaker' / 'scripts' / 'benchkit'
    store = Path(store) if store else default_store()
    return Sources(meta_dir=bb / 'meta-tasks' / meta_task, interface=kit / 'INTERFACE.md',
                   conform=bb / 'public' / 'conform.py', material=store / 'material' / meta_task / 'public',
                   packages={'orchflows': repo, 'shared': repo / 'example-workflows' / 'shared', 'benchmaker': bm})


def _core(*names):
    scripts = str(transcripts.scripts_dir())
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    modules = [__import__(name) for name in names]
    return modules[0] if len(modules) == 1 else modules


def layout(sources):
    """The workspace as {relative path: source file} and the gaps where a public input is missing.

    The request is the prompt and stays out of the workspace; the interface text is a byte copy."""
    package_files = _core('package_files')
    entries, gaps = {}, []

    def add(prefix, root):
        for path in package_files.files(root):
            relative = path.relative_to(root).as_posix()
            if PRIVATE_NAMES & set(relative.split('/')):
                raise ValueError(f'Private material would enter the workspace: {path}')
            entries[prefix + relative] = path

    for name, source in (('interface.md', sources.meta_dir / 'interface.md'), ('interface/package.md', sources.interface),
                         ('conform.py', sources.conform)):
        if Path(source).is_file():
            entries[name] = Path(source)
        else:
            gaps.append(f'{name}: source {source} not found')
    for prefix, root in (('material/', sources.material), ('subject/', sources.meta_dir / 'subject')):
        if root is not None and Path(root).is_dir():
            add(prefix, Path(root))
        elif prefix == 'material/':
            gaps.append(f'material/: public material {root} not found')
    return dict(sorted(entries.items())), gaps


def freeze(source, destination):
    """Copy a package without its trials and tests, as the E2E harness does; returns what was left out."""
    orchflows, package_files = _core('orchflows', 'package_files')
    source, destination = Path(source), Path(destination)
    manifest = orchflows._manifest(source)
    destination.mkdir(parents=True, exist_ok=False)
    excluded = []
    # Libraries are enumerated whole so that withheld trials and tests are recorded as excluded.
    core = manifest['name'] == 'orchflows'
    for path in orchflows._files(source, core=True) if core else package_files.files(source):
        relative = path.relative_to(source)
        if {'trials', 'tests'} & set(relative.parts):
            excluded.append(relative.as_posix())
            continue
        (destination / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination / relative)
    return {'name': manifest['name'], 'source': str(source), 'path': str(destination), 'excluded': excluded}


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _request(meta_task, arm, budget_name, sources):
    if arm not in ARMS:
        raise ValueError(f'Unknown arm {arm!r}; use one of {list(ARMS)}')
    sizes = budget(meta_task, budget_name)
    return sizes, prompt(arm, fill_request((sources.meta_dir / 'request.md').read_text(encoding='utf-8'), sizes))


def prepare(meta_task, arm, budget_name, work_root, *, sources=None, build_id=None):
    """Create <work_root>/<build-id>/ with workspace/, home/, request.txt, build.json and, for the Benchmaker
    arm, packages/; returns the build directory. Missing public inputs are recorded as gaps, not guessed."""
    sources = sources or default_sources(meta_task)
    sizes, text = _request(meta_task, arm, budget_name, sources)
    entries, gaps = layout(sources)
    build_dir = Path(work_root) / (build_id or 'b-' + secrets.token_hex(3))
    build_dir.mkdir(parents=True, exist_ok=False)
    workspace = build_dir / 'workspace'
    workspace.mkdir()
    for relative, source in entries.items():
        (workspace / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, workspace / relative)
    (build_dir / 'home').mkdir()
    packages = {name: freeze(sources.packages[name], build_dir / 'packages' / name)
                for name in PACKAGES} if arm == 'benchmaker' else {}
    (build_dir / 'request.txt').write_text(text, encoding='utf-8', newline='\n')
    _write_json(build_dir / 'build.json', {
        'meta_task': meta_task, 'arm': arm, 'budget_name': budget_name, 'budget': sizes,
        'created': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'workspace': str(workspace),
        'home': str(build_dir / 'home'), 'files': list(entries), 'packages': packages, 'gaps': gaps, 'runs': []})
    return build_dir


def plan(meta_task, arm, model, effort, budget_name, work_root, *, sources=None, executable=None, config_dir=None):
    """Everything `prepare` and `run` would do, as data; creates and launches nothing."""
    sources = sources or default_sources(meta_task)
    sizes, text = _request(meta_task, arm, budget_name, sources)
    entries, gaps = layout(sources)
    build_dir = Path(work_root) / '<build-id>'
    packages = {name: build_dir / 'packages' / name for name in PACKAGES}
    if arm == 'benchmaker':
        gaps += [f'packages/{name}: source {sources.packages.get(name)} not found'
                 for name in PACKAGES if not (sources.packages.get(name) and Path(sources.packages[name]).is_dir())]
    if not (executable or shutil.which('claude')):
        gaps.append('Claude CLI not found on PATH')
    arguments = command(arm, packages, model, effort, session_id='<new uuid at launch>', executable=executable,
                        config_dir=config_dir)
    return {'meta_task': meta_task, 'arm': arm, 'model': model, 'effort': effort, 'budget_name': budget_name,
            'budget': sizes, 'wall_seconds': sizes['wall_minutes'] * 60, 'build_dir': str(build_dir),
            'cwd': str(build_dir / 'workspace'), 'command': arguments, 'prompt': text,
            'env': {'ORCHFLOWS_HOME': str(build_dir / 'home'), 'CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS': '0',
                    'PYTHONDONTWRITEBYTECODE': '1', 'inherited': sorted(k for k in os.environ if k.upper() in ENV_KEEP)},
            'workspace': list(entries), 'packages': {name: str(path) for name, path in packages.items()}
            if arm == 'benchmaker' else {}, 'gaps': gaps, 'launches': 0}


def render_plan(plan_):
    sizes = plan_['budget']
    lines = [f"Build plan: {plan_['meta_task']}, {plan_['arm']} arm (nothing is launched)",
             f"  model {plan_['model']}, effort {plan_['effort']}",
             f"  budget {plan_['budget_name']}: {sizes['runs']} subject runs, {sizes['minutes']} min each, "
             f"concurrency {sizes['concurrency']}, builder wall cap {sizes['wall_minutes']} min",
             f"  build dir {plan_['build_dir']}", f"  cwd {plan_['cwd']}", '  command:',
             '    ' + render_command(plan_['command']), '  prompt on stdin:',
             *('    ' + line for line in plan_['prompt'].splitlines()),
             '  environment: ' + ', '.join(f'{k}={v}' for k, v in plan_['env'].items() if k != 'inherited'),
             '  inherited from caller: ' + ', '.join(plan_['env']['inherited']),
             '  packages: ' + (', '.join(plan_['packages']) or 'none'), '  workspace:',
             *('    ' + name for name in plan_['workspace'])]
    if plan_['gaps']:
        lines += ['  gaps:', *('    ' + gap for gap in plan_['gaps'])]
    return '\n'.join(lines)


def default_launcher():
    try:
        from benchkit.launch import run_capped
    except ImportError:
        for parent in Path(__file__).resolve().parents:
            if (parent / 'skills' / 'benchmaker' / 'scripts' / 'benchkit').is_dir():
                sys.path.insert(0, str(parent / 'skills' / 'benchmaker' / 'scripts'))
                break
        from benchkit.launch import run_capped
    return run_capped


def allowed_roots(build, executable=None, config_dir=None):
    """Where a builder may read: its workspace, private home, own packages, interpreters, the CLI and its scratch,
    including the harness's persisted tool results for this workspace."""
    slug = re.sub(r'[^A-Za-z0-9]', '-', build['workspace'])
    roots = [build['workspace'], build['home'], *(p['path'] for p in build['packages'].values()),
             sys.prefix, sys.base_prefix, Path(sys.executable).parent, Path(tempfile.gettempdir()) / 'claude',
             Path(config_dir or claude_config_dir()) / 'projects' / slug, '/tmp', '/var/tmp']
    cli = executable or shutil.which('claude')
    if cli:
        roots += [Path(cli).parent, Path(os.path.realpath(cli)).parent]
    return list(dict.fromkeys(str(root) for root in roots))


def _check_models(root, model, effort):
    gaps = []
    efforts = set(root.get('efforts', {})) - {'unknown'}
    models = {name for name in root.get('models', {}) if name != 'unknown' and not name.startswith('<')}
    if efforts and efforts != {effort}:
        gaps.append(f'Native effort mismatch: requested {effort}, observed {sorted(efforts)}')
    if models and not all(name.startswith(model) for name in models):
        gaps.append(f'Native model mismatch: requested {model}, observed {sorted(models)}')
    return gaps


def run(build_dir, *, model, effort, resume=None, wall_seconds=None, launcher=None, collector=None, executable=None,
        config_dir=None, env=None, cancel=None):
    """Launch the builder session under the build's wall cap and record the run.

    The cap spans resumes: a later run gets what earlier runs left. A usage limit is recorded `interrupted`
    with the command that resumes the session. After exit the native transcripts, including every child's, are
    collected and scanned for reads outside the allowed roots. `launcher` has the signature of
    benchkit.launch.run_capped and `collector` that of transcripts.collect."""
    build_dir = Path(build_dir)
    build = _read_json(build_dir / 'build.json')
    cap = wall_seconds if wall_seconds is not None else build['budget']['wall_minutes'] * 60 - sum(
        r['seconds'] for r in build['runs'])
    if cap <= 0:
        raise ValueError('The builder wall cap is already used')
    number = len(build['runs']) + 1
    directory = build_dir / 'runs' / str(number)
    directory.mkdir(parents=True)
    session = resume or str(uuid.uuid4())
    packages = {name: item['path'] for name, item in build['packages'].items()}
    arguments = command(build['arm'], packages, model, effort, session_id=session, resume=resume,
                        executable=executable, config_dir=config_dir)
    text = RESUME_PROMPT if resume else (build_dir / 'request.txt').read_text(encoding='utf-8')
    _write_json(directory / 'command.json', arguments)
    (directory / 'request.txt').write_text(text, encoding='utf-8', newline='\n')
    events, stderr = directory / 'events.jsonl', directory / 'stderr.txt'
    environment = clean_env(env, ORCHFLOWS_HOME=build['home'], CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS='0')
    outcome = (launcher or default_launcher())(arguments, cwd=Path(build['workspace']), env=environment, stdout=events,
                                               stderr=stderr, stdin=text.encode('utf-8'), timeout=cap, cancel=cancel)
    records, gaps = transcripts.read_jsonl(events)
    summary = transcripts.summarize(records)
    stderr_text = stderr.read_text(encoding='utf-8', errors='replace') if stderr.is_file() else ''
    result = summary['status'] if summary['results'] else transcripts.classify(None, stderr_text)
    session = summary['session_id'] or session
    if outcome.status in ('timeout', 'canceled'):
        status = outcome.status
    elif result == 'usage-limit':
        status = 'interrupted'
    else:
        status = 'completed' if outcome.status == 'completed' and summary['terminal_success'] else 'error'
    native = (collector or transcripts.collect)(session, directory / 'native', config_dir)
    root = next((agent for agent in native['agents'] if agent['id'] == session), None)
    gaps = [*gaps, *summary['gaps'], *native['gaps'], *(_check_models(root, model, effort) if root else [
        'Native transcript unavailable for the builder session'])]
    scanned = [Path(agent['raw']) for agent in native['agents'] if agent.get('raw')] or [events]
    findings = transcripts.scan(scanned, allowed_roots(build, executable, config_dir), cwd=build['workspace'])
    record = {'run': number, 'arm': build['arm'], 'model': model, 'effort': effort, 'session_id': session,
              'resumed': bool(resume), 'status': status, 'exit_code': outcome.exit_code,
              'seconds': round(outcome.seconds, 1), 'wall_cap_seconds': round(cap, 1), 'started': outcome.started,
              'finished': outcome.finished, 'cost_usd': summary['cost_usd'], 'left_running': outcome.left_running,
              'reason': outcome.reason, 'terminal_success': summary['terminal_success'],
              'final': summary['final'][-2000:], 'observed': {'models': root['models'], 'efforts': root['efforts']}
              if root else {}, 'out_of_workspace_reads': findings, 'gaps': gaps,
              'resume_command': render_command(command(build['arm'], packages, model, effort, resume=session,
                                                       executable=executable, config_dir=config_dir))
              if status == 'interrupted' else None}
    _write_json(directory / 'run.json', record)
    build['runs'].append(record)
    _write_json(build_dir / 'build.json', build)
    return record


def builder_summary(build_dir):
    """The report's `builder` entry: wall seconds over all runs, known cost and every out-of-workspace read.

    Cost is cumulative within a session, so a resumed session counts once at its highest reported value."""
    runs = _read_json(Path(build_dir) / 'build.json')['runs']
    cost = {}
    for item in runs:
        if item['cost_usd'] is not None:
            cost[item['session_id']] = max(cost.get(item['session_id'], 0.0), item['cost_usd'])
    return {'seconds': round(sum(item['seconds'] for item in runs), 1) if runs else None,
            'cost_usd': round(sum(cost.values()), 4) if cost else None,
            'out_of_workspace_reads': [read for item in runs for read in item['out_of_workspace_reads']]}


def render_run(record):
    lines = [f"Run {record['run']} ({record['arm']}): {record['status']} after {record['seconds']} s, "
             f"cost {record['cost_usd']}, {len(record['out_of_workspace_reads'])} out-of-workspace reads"]
    if record['resume_command']:
        lines += ['Stopped by a usage limit. Resume the same session with:', '  ' + record['resume_command'],
                  '  (prompt on stdin: ' + RESUME_PROMPT + ')']
    lines += ['Gap: ' + gap for gap in record['gaps']]
    return '\n'.join(lines)
