"""Session-local Claude packages; preserve configured model/effort and auth."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

from common import read_json
from evidence import stream


class Claude:
    name = 'claude'
    capabilities = {'independent-review', 'local-exec', 'no-review', 'structured-audit'}

    def __init__(self, executable=None):
        self.executable = shutil.which(executable or 'claude')
        if not self.executable:
            raise ValueError('Claude CLI is unavailable')
        self.version = subprocess.check_output([self.executable, '--version'], text=True, timeout=10).strip()
        config = Path(os.environ.get('CLAUDE_CONFIG_DIR', Path.home() / '.claude'))
        settings = read_json(config / 'settings.json') if (config / 'settings.json').exists() else {}
        # Disable ambient plugin activation and hooks for this invocation only.
        self.settings = {'disableAllHooks': True, 'enabledPlugins':
                         {name: False for name in settings.get('enabledPlugins', {})}}
        self.settings.update({key: settings[key] for key in ('model', 'effortLevel') if key in settings})

    def registration_gaps(self, native, packages):
        loaded = {p.get('name'): p.get('path') for p in native.get('plugins', [])}
        return [key for key, path in packages.items() if key not in loaded or Path(loaded[key]).resolve() != path.resolve()]

    def command(self, packages, profile='local', schema=None, allowed_root=None, directory=None):
        tools = {'local': 'Read,Write,Edit,Bash,Agent,Skill,Glob,Grep',
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
        return command

    def invocation(self, entrypoint, request):
        return ('/' + entrypoint + '\n\n' if entrypoint else '') + request

    def result(self, directory):
        records, gaps = stream(Path(directory) / 'events.jsonl')
        init = next((e for e in records if e.get('subtype') == 'init'), {})
        finals = [e for e in records if e.get('type') == 'result']
        final = finals[-1] if finals else {}
        if not init:
            gaps.append('Missing native initialization record')
        if not final or final.get('is_error'):
            gaps.append('Missing successful native terminal record')
        return {'session_id': init.get('session_id'), 'model': init.get('model'),
                'terminal_success': bool(final) and not final.get('is_error', False),
                'tools': init.get('tools', []), 'plugins': init.get('plugins', []),
                'slash_commands': init.get('slash_commands', []), 'final': final.get('result', ''),
                'structured_output': final.get('structured_output'), 'usage': final.get('usage'),
                'cost_usd': final.get('total_cost_usd'), 'gaps': gaps,
                'conditions': 'Session-local packages; user model/settings retained; user-configured plugin activations and hooks disabled. '
                              'Host built-in skills may remain advertised in native inventory. '
                              'Target shell/filesystem and network are not sandboxed by this harness; fixtures use local fakes. '
                              'Evaluator material withheld from context, not proven inaccessible to target shell.'}
