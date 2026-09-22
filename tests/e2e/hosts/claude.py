"""Session-local Claude packages; pass configured model/effort through and record what ran."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

from common import read_json, write_json
from evidence import stream
import native_logs


class Claude:
    name = 'claude'
    capabilities = {'independent-review', 'local-exec', 'no-review', 'structured-audit'}
    model_settings = None

    def __init__(self, executable=None):
        self.executable = shutil.which(executable or 'claude')
        if not self.executable:
            raise ValueError('Claude CLI is unavailable')
        self.version = subprocess.check_output([self.executable, '--version'], text=True, timeout=10).strip()
        self.home = native_logs.native_home('claude')
        settings = read_json(self.home / 'settings.json') if (self.home / 'settings.json').exists() else {}
        # Disable ambient plugin activation and hooks for this invocation only.
        # Account-synced claude.ai skills and plugins would join the frozen packages (probe 2026-09-22).
        self.settings = {'disableAllHooks': True, 'syncClaudeAiSkills': False, 'syncClaudeAiPlugins': False, 'enabledPlugins':
                         {name: False for name in settings.get('enabledPlugins', {})}}
        self.settings.update({key: settings[key] for key in ('model', 'effortLevel') if key in settings})
        self.model_settings = settings.get('modelSettings')

    def requested_effort(self):
        """Effort sources as found; the host decides which applies, so these are requests."""
        found = {'effortLevel': self.settings['effortLevel']} if 'effortLevel' in self.settings else {}
        if self.model_settings is not None:
            found['modelSettings'] = self.model_settings
        if os.environ.get('CLAUDE_CODE_EFFORT_LEVEL'):
            found['CLAUDE_CODE_EFFORT_LEVEL'] = os.environ['CLAUDE_CODE_EFFORT_LEVEL']
        return found

    def registration_gaps(self, native, packages):
        loaded = {p.get('name'): p.get('path') for p in native.get('plugins', [])}
        return [key for key, path in packages.items() if key not in loaded or Path(loaded[key]).resolve() != path.resolve()]

    def command(self, packages, profile='local', schema=None, allowed_root=None, directory=None):
        tools = {'local': 'Read,Write,Edit,Bash,Agent,Skill,Glob,Grep',
                 'authoring': 'Read,Write,Edit,Bash,Agent,Skill,Glob,Grep',
                 'no-review': 'Read,Write,Edit,Skill,Glob,Grep',
                 'audit': 'Read,Glob,Grep'}[profile]
        command = [self.executable, '-p', '--verbose', '--output-format', 'stream-json',
                   '--forward-subagent-text', '--session-id', str(uuid.uuid4()),
                   '--permission-mode', 'dontAsk', '--tools', tools, '--allowedTools', tools,
                   '--strict-mcp-config', '--setting-sources', 'user',
                   '--settings', json.dumps(self.settings)]
        for path in packages.values():
            command += ['--plugin-dir', str(path)]
        if profile == 'audit':
            command += ['--restricted', '--add-dir', str(allowed_root)]
        if schema:
            command += ['--json-schema', json.dumps(schema)]
        if directory is not None:
            write_json(Path(directory) / 'claude-launch.json', {'profile': profile, 'requested_effort': self.requested_effort()})
        return command

    def invocation(self, entrypoint, request):
        return ('/' + entrypoint + '\n\n' if entrypoint else '') + request

    def result(self, directory):
        records, gaps = stream(Path(directory) / 'events.jsonl')
        init = next((e for e in records if e.get('subtype') == 'init'), {})
        finals = [e for e in records if e.get('type') == 'result']
        final = finals[-1] if finals else {}
        launch_path = Path(directory) / 'claude-launch.json'
        launch = read_json(launch_path) if launch_path.exists() else {}
        if not init:
            gaps.append('Missing native initialization record')
        if not final or final.get('is_error'):
            gaps.append('Missing successful native terminal record')
        observed = {}
        if init.get('session_id'):
            try:
                root = native_logs.inspect('claude', init['session_id'], self.home, limit=1)['agents'][0]
                observed = {'models': root['models'], 'efforts': root['efforts']}
            except (OSError, ValueError) as error:
                gaps.append('Native transcript unavailable: ' + str(error))
        requested = launch.get('requested_effort', {})
        # The environment variable outranks settings; per-model modelSettings shapes are not interpreted.
        wanted = requested.get('CLAUDE_CODE_EFFORT_LEVEL') or (
            requested.get('effortLevel') if 'modelSettings' not in requested else None)
        ran = set(observed.get('efforts', {})) - {'unknown'}
        if wanted and ran and ran != {wanted}:
            gaps.append(f'Native effort mismatch: requested {wanted}, observed {sorted(ran)}')
        return {'session_id': init.get('session_id'), 'model': init.get('model'),
                'observed': observed, 'requested_effort': requested,
                'terminal_success': bool(final) and not final.get('is_error', False),
                'tools': init.get('tools', []), 'plugins': init.get('plugins', []),
                'slash_commands': init.get('slash_commands', []), 'final': final.get('result', ''),
                'structured_output': final.get('structured_output'), 'usage': final.get('usage'),
                'cost_usd': final.get('total_cost_usd'), 'gaps': gaps, 'launch_profile': launch.get('profile'),
                'conditions': 'Session-local packages; user model and effort settings passed through, which the host may not apply; '
                              'observed model/effort are tallied from native transcript records. '
                              'User-configured plugin activations and hooks disabled. '
                              'Host built-in skills may remain advertised in native inventory. '
                              'Local and authoring targets have the same tools; their shell/filesystem and network are not sandboxed by this harness. '
                              'Authoring permits nested host inference; trial requests still constrain task-facing effects to local fakes. '
                              'Audits have read tools only, without shell or delegation. '
                              'Evaluator material withheld from context, not proven inaccessible to target shell.'}
