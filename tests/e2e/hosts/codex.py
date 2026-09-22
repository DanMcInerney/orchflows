"""Native Codex exec with disposable repo skills and retained native history.

No plugin installation or user configuration writes. Native skills/list verifies
the complete package copies discovered beneath the stage's .agents/skills root.
"""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time
import tomllib

from common import copy_package, read_json, snapshot, write_json
from evidence import stream
import native_logs


def launcher(executable=None):
    found = str(Path(executable).resolve()) if executable and Path(executable).is_file() else shutil.which(executable or 'codex')
    if not found:
        raise ValueError('Codex CLI is unavailable')
    path = Path(found)
    # Invoke the selected npm package without cmd.exe or PowerShell re-quoting.
    script = path.parent / 'node_modules/@openai/codex/bin/codex.js'
    if path.suffix.lower() in {'.cmd', '.ps1', '.bat'} and script.is_file():
        node = shutil.which('node')
        if not node:
            raise ValueError('The selected Codex npm launcher requires Node.js')
        return [node, str(script)]
    if path.suffix.lower() in {'.cmd', '.ps1', '.bat'}:
        raise ValueError('Supply the native Codex executable or its npm launcher')
    return [str(path)]


def toml(value):
    if isinstance(value, dict):
        return '{' + ', '.join(json.dumps(k) + ' = ' + toml(v) for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ', '.join(map(toml, value)) + ']'
    return json.dumps(value)


def inventory(command, cwd, timeout=12):
    """Read native discovery without starting a thread or making a model call."""
    messages = queue.Queue()
    process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, text=True, encoding='utf-8')
    def read():
        for line in process.stdout:
            messages.put(line)
        messages.put(None)
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    end = time.monotonic() + timeout
    def request(value):
        process.stdin.write(json.dumps(value) + '\n')
        process.stdin.flush()
    def response(identifier):
        while True:
            line = messages.get(timeout=max(.001, end - time.monotonic()))
            if line is None:
                raise ValueError('Codex inventory exited without a response')
            message = json.loads(line)
            if message.get('id') == identifier:
                if 'error' in message:
                    raise ValueError('Codex inventory: ' + str(message['error']))
                return message['result']
    try:
        request({'id': 1, 'method': 'initialize', 'params': {
            'clientInfo': {'name': 'orchflows-e2e', 'version': '1'}}})
        response(1)
        request({'method': 'initialized', 'params': {}})
        request({'id': 2, 'method': 'skills/list', 'params': {'cwds': [str(cwd)], 'forceReload': True}})
        return response(2)
    except queue.Empty as error:
        raise ValueError('Codex inventory timed out') from error
    finally:
        process.terminate()
        process.wait(timeout=5)
        reader.join(timeout=2)
        process.stdin.close()
        process.stdout.close()


class Codex:
    name = 'codex'
    capabilities = {'independent-review', 'local-exec', 'no-review', 'structured-audit'}

    def __init__(self, executable=None, model=None, effort=None):
        self.launcher = launcher(executable)
        self.version = subprocess.check_output([*self.launcher, '--version'], text=True, timeout=10).strip()
        self.home = native_logs.native_home('codex')
        config = self.home / 'config.toml'
        settings = tomllib.loads(config.read_text(encoding='utf-8')) if config.exists() else {}
        self.settings = {key: settings[key] for key in
            ('model', 'model_reasoning_effort', 'model_provider', 'model_providers', 'service_tier', 'windows')
            if key in settings}
        self.model, self.effort = model, effort
        if model:
            self.settings['model'] = model
        if effort:
            self.settings['model_reasoning_effort'] = effort
        if 'max_threads' in settings.get('agents', {}):
            self.settings['agents.max_threads'] = settings['agents']['max_threads']
        # Keep ambient skills out of the experiment; the selected package copies
        # are discovered natively as repo skills, with their invocation metadata.
        self.disabled_skills = [{'path': str(p), 'enabled': False}
                                for p in (self.home / 'skills').rglob('SKILL.md')]

    def options(self, profile):
        settings = {**self.settings, 'mcp_servers': {}, 'approval_policy': 'never',
            'features.hooks': False, 'features.plugins': False, 'features.apps': False,
            'features.memories': False, 'features.skill_mcp_dependency_install': False,
            'features.multi_agent': profile in {'local', 'authoring'}, 'agents.enabled': profile in {'local', 'authoring'},
            'features.shell_tool': profile != 'no-review',
            'sandbox_workspace_write.network_access': profile == 'authoring',
            'web_search': 'disabled', 'project_doc_max_bytes': 0,
            'skills.config': self.disabled_skills}
        return [part for key, value in settings.items() for part in ('-c', key + '=' + toml(value))]

    def prepare(self, workspace, packages):
        """Run before Trial snapshots so loaded package bytes are invariants."""
        workspace = Path(workspace)
        runtime, copies = {}, {}
        for name, source in packages.items():
            destination = workspace / '.agents/skills' / name
            copies[name] = copy_package(source, destination)
            runtime[name] = str(destination.resolve())
        write_json(workspace.parent / 'codex-preparation.json', {'packages': runtime, 'copies': copies})

    def command(self, packages, profile='local', schema=None, allowed_root=None, directory=None):
        if profile not in {'local', 'authoring', 'no-review', 'audit'} or directory is None:
            raise ValueError('Codex requires a stage directory and a supported profile')
        directory = Path(directory).resolve()
        workspace = Path(allowed_root).resolve() if profile == 'audit' else directory / 'workspace'
        preparation = {'packages': {}, 'copies': {}}
        if packages:
            prepared = directory / 'codex-preparation.json'
            if not prepared.exists():
                raise ValueError('Call Codex.prepare before taking the workspace snapshot')
            preparation = read_json(prepared)
        options = self.options(profile)
        registered, gaps = {'data': []}, []
        if packages:
            try:
                registered = inventory([*self.launcher, '-C', str(workspace), *options,
                                        'app-server', '--stdio'], workspace)
                for entry in registered.get('data', []):
                    gaps.extend('Native skill discovery error: ' + str(error) for error in entry.get('errors', []))
            except (OSError, ValueError, subprocess.SubprocessError) as error:
                gaps.append(f'Native skill discovery unavailable: {error}')
        metadata = {'profile': profile, 'workspace_shell_network_access': profile == 'authoring',
                    **preparation, 'inventory': registered,
                    'configured_model': self.settings.get('model'),
                    'configured_effort': self.settings.get('model_reasoning_effort'), 'gaps': gaps}
        write_json(directory / 'codex-launch.json', metadata)
        command = [*self.launcher, 'exec', '--json', '--ignore-user-config', '--ignore-rules',
                   '--skip-git-repo-check', '--color', 'never', '--sandbox',
                   'read-only' if profile == 'audit' else 'workspace-write',
                   '--output-last-message', str(directory / 'final.txt'), *options]
        if schema is not None:
            write_json(directory / 'output-schema.json', schema)
            command += ['--output-schema', str(directory / 'output-schema.json')]
        return [*command, '-']

    def registration_gaps(self, native, packages):
        metadata = native.get('registration', {})
        advertised = {Path(s['path']).resolve() for entry in metadata.get('inventory', {}).get('data', [])
                      for s in entry.get('skills', []) if s.get('enabled') and s.get('path')}
        gaps = []
        for name, source in packages.items():
            runtime = metadata.get('packages', {}).get(name)
            if not runtime:
                gaps.append(name)
                continue
            runtime = Path(runtime)
            expected = list((runtime / 'skills').rglob('SKILL.md'))
            if not expected or any(p.resolve() not in advertised for p in expected):
                gaps.append(name)
            elif snapshot(runtime) != metadata.get('copies', {}).get(name, {}).get('files'):
                gaps.append(name + ' (runtime package changed)')
        return gaps

    def invocation(self, entrypoint, request):
        return ('$' + entrypoint + '\n\n' if entrypoint else '') + request

    def result(self, directory):
        directory = Path(directory)
        records, gaps = stream(directory / 'events.jsonl')
        launch_path = directory / 'codex-launch.json'
        launch = read_json(launch_path) if launch_path.exists() else {}
        gaps += launch.get('gaps', [])
        started = next((e for e in records if e.get('type') == 'thread.started'), {})
        identifier = started.get('thread_id')
        terminals = [e for e in records if e.get('type') in {'turn.completed', 'turn.failed'}]
        terminal = terminals[-1] if terminals else {}
        success = terminal.get('type') == 'turn.completed'
        if not identifier:
            gaps.append('Missing native thread.started record')
        if not success:
            gaps.append('Missing successful native turn.completed record')
        messages = [e['item'].get('text', '') for e in records if e.get('type') == 'item.completed'
                    and e.get('item', {}).get('type') == 'agent_message']
        final_path = directory / 'final.txt'
        final = final_path.read_text(encoding='utf-8') if final_path.exists() else (messages[-1] if messages else '')
        structured = None
        if (directory / 'output-schema.json').exists() and success:
            try:
                structured = json.loads(final)
            except ValueError:
                gaps.append('Native final message is not structured JSON')
        context = {}
        if identifier:
            try:
                entries, _ = native_logs._locate('codex', identifier, self.home)
                with Path(entries[identifier]['path']).open(encoding='utf-8') as raw:
                    for line in raw:
                        event = json.loads(line)
                        if event.get('type') == 'turn_context':
                            context = event.get('payload', {})
            except (OSError, ValueError) as error:
                gaps.append('Native metadata unavailable: ' + str(error))
            if not context:
                gaps.append('Missing native turn_context metadata')
        for key, actual in (('configured_model', context.get('model')),
                            ('configured_effort', context.get('effort') or context.get('reasoning_effort'))):
            if launch.get(key) is not None and actual is not None and launch[key] != actual:
                gaps.append(f'Native {key} mismatch: requested {launch[key]}, observed {actual}')
        if launch.get('profile') == 'audit' and context:
            if context.get('sandbox_policy', {}).get('type') != 'read-only':
                gaps.append('Read-only audit sandbox not established in native metadata')
        network_condition = ('Authoring profile explicitly permits workspace shell network access for nested host inference; '
                             'this is general network permission, with task-facing effects constrained by the trial request. '
                             if launch.get('profile') == 'authoring' else
                             'Workspace shell network access is disabled; audit keeps read-only sandbox defaults. ')
        return {'session_id': identifier, 'model': context.get('model'),
                'effort': context.get('effort') or context.get('reasoning_effort'),
                'terminal_success': success, 'tools': None, 'plugins': [], 'slash_commands': [],
                'final': final, 'structured_output': structured, 'usage': terminal.get('usage'),
                'cost_usd': None, 'gaps': gaps, 'registration': launch,
                'conditions': 'Native repo-skill discovery from full stage-local package copies; no plugin installation. '
                    'User model/effort retained, hooks/plugins/apps and ambient skills disabled per invocation. '
                    'Native history remains in the existing Codex home; exact thread IDs drive descendant collection. '
                    'Targets request workspace-write; audits request read-only with native delegation disabled. ' + network_condition +
                    'Audit shell reads remain enabled; arbitrary subprocess delegation is not independently tool-filtered. '
                    'Sandbox enforcement requires a host-specific probe. No claim of complete credential isolation.'}
