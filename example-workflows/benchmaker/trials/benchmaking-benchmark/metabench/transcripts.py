"""Claude Code output: result classification, native transcript collection and the out-of-workspace scan.

Records are stream-json events or native session transcripts; both carry assistant `tool_use` blocks."""
from __future__ import annotations

import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import sys

USAGE_LIMIT = re.compile(r"hit your[\w\s-]*limit|usage limit|limit reached|\bresets \d", re.I)

# Input fields that name paths, by tool. Glob patterns and Grep globs count only because they can be absolute.
FILE_FIELDS = {'Read': ('file_path',), 'Write': ('file_path',), 'Edit': ('file_path',), 'MultiEdit': ('file_path',),
               'NotebookEdit': ('notebook_path',), 'Glob': ('path', 'pattern'), 'Grep': ('path', 'glob')}
COMMAND_TOOLS = ('Bash', 'PowerShell')
HARMLESS = {'/dev/null', '/dev/stdin', '/dev/stdout', '/dev/stderr', '/dev/tty'}
# A one-segment rooted path in a command is a path only under a top-level directory name; otherwise it is
# division, a sed or awk expression or a regular expression.
TOP_LEVEL = {'tmp', 'etc', 'home', 'usr', 'var', 'opt', 'mnt', 'root', 'bin', 'sbin', 'lib', 'lib64', 'proc', 'sys',
             'srv', 'boot', 'run', 'dev', 'Users', 'Volumes', 'Library', 'Applications', 'private'}

_TOKEN = r"[^\s\"'`|;&<>()]"
_HOMES = "|".join(map(re.escape, ('~', '$HOME', '${HOME}', '$USERPROFILE', '%USERPROFILE%', '$env:USERPROFILE', '$env:HOME')))
# Absolute Windows paths, rooted POSIX paths (URLs and relative segments excluded), `..` starts and home references.
DRIVE = re.compile(rf"(?<![\w/])[A-Za-z]:[\\/]{_TOKEN}*")
ROOTED = re.compile(rf"(?<![\w.~:/\\$-])/[^\s\"'`|;&<>()/]{_TOKEN}*")
PARENT = re.compile(rf"(?<![\w.~:/\\$-])\.\.(?:[\\/]{_TOKEN}*)?(?![\w.])")
HOME = re.compile(rf"(?<![\w.:/\\-])(?:{_HOMES})(?:[\\/]{_TOKEN}*)?(?!\w)")


def read_jsonl(path):
    """Parsed object records and gaps for malformed lines; a missing file is one gap."""
    path = Path(path)
    if not path.is_file():
        return [], [f'{path.name}: missing']
    records, gaps = [], []
    for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            gaps.append(f'{path.name}:{number}: malformed or incomplete record')
            continue
        if isinstance(value, dict):
            records.append(value)
    return records, gaps


def parse_result(text):
    """The result record of `--output-format json` output: one object, or events ending in one."""
    try:
        value = json.loads(text)
    except ValueError:
        value = []
        for line in text.splitlines():
            try:
                value.append(json.loads(line))
            except ValueError:
                pass
    if isinstance(value, list):
        results = [item for item in value if isinstance(item, dict) and item.get('type') == 'result']
        value = results[-1] if results else None
    return value if isinstance(value, dict) else None


def classify(result, stderr=''):
    """completed, usage-limit, refused, cut-off or error from a result record (stderr only when none exists)."""
    if not result:
        return 'usage-limit' if USAGE_LIMIT.search(stderr or '') else 'error'
    subtype = str(result.get('subtype') or '')
    if result.get('is_error') and USAGE_LIMIT.search(str(result.get('result') or '')):
        return 'usage-limit'
    if result.get('stop_reason') == 'max_tokens' or subtype == 'error_max_turns' or result.get('terminal_reason') == 'max_turns':
        return 'cut-off'
    if result.get('is_error') or subtype.startswith('error'):
        return 'error'
    return 'refused' if result.get('stop_reason') == 'refusal' else 'completed'


def summarize(records):
    """Identity, final result and gaps from stream-json events; the last result record is final."""
    init = next((r for r in records if r.get('type') == 'system' and r.get('subtype') == 'init'), {})
    finals = [r for r in records if r.get('type') == 'result']
    final = finals[-1] if finals else {}
    gaps = ([] if init else ['Missing native initialization record']) + ([] if final else ['Missing terminal result record'])
    return {'session_id': init.get('session_id') or final.get('session_id'), 'model': init.get('model'),
            'models': sorted(final.get('modelUsage') or {}), 'plugins': init.get('plugins', []),
            'tools': init.get('tools', []), 'slash_commands': init.get('slash_commands', []),
            'status': classify(final) if final else 'error', 'terminal_success': bool(final) and not final.get('is_error'),
            'final': final.get('result') or '', 'cost_usd': final.get('total_cost_usd'), 'results': len(finals),
            'gaps': gaps}


def scripts_dir():
    for parent in Path(__file__).resolve().parents:
        if (parent / 'scripts' / 'native_logs.py').is_file():
            return parent / 'scripts'
    raise ImportError('Core scripts/native_logs.py not found above ' + __file__)


def _native_logs():
    try:
        import native_logs
    except ImportError:
        sys.path.insert(0, str(scripts_dir()))
        import native_logs
    return native_logs


def collect(session_id, destination, home=None):
    """Freeze the native transcripts of a session and its descendants as <id>.raw.jsonl with index.json.

    Discovery failures stay visible as gaps; an unreadable or missing session yields no agents."""
    logs = _native_logs()
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    home = logs.native_home('claude', home)
    agents, gaps, cursor = [], [], None
    try:
        while True:
            page = logs.inspect('claude', session_id, home, limit=100, after=cursor)
            agents.extend(page['agents'])
            gaps.extend(json.dumps(gap) for gap in page['discovery_gaps'])
            cursor = page['next_cursor']
            if cursor is None:
                break
    except (OSError, ValueError) as error:
        gaps.append(f'Native transcript unavailable: {error}')
    kept = []
    for agent in agents:
        source = Path(agent['path'])
        raw = destination / (agent['id'] + '.raw.jsonl')
        shutil.copy2(source, raw)
        kept.append({'id': agent['id'], 'parent_id': agent['parent_id'], 'name': agent.get('name'),
                     'models': agent.get('models', {}), 'efforts': agent.get('efforts', {}),
                     'tools': agent.get('tools', {}), 'launch_context': agent.get('launch_context'),
                     'error_count': agent.get('error_count', 0), 'recorded_source': str(source), 'raw': str(raw)})
    index = {'root_id': session_id, 'native_home': str(home), 'agents': kept, 'gaps': gaps}
    (destination / 'index.json').write_text(json.dumps(index, indent=2) + '\n', encoding='utf-8')
    return index


def tool_calls(path):
    """(line, parent tool-use id, tool, input) for each tool call in a stream-json or native transcript."""
    for number, line in enumerate(Path(path).read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        message = record.get('message') if isinstance(record, dict) else None
        for block in (message.get('content') if isinstance(message, dict) else None) or []:
            if isinstance(block, dict) and block.get('type') == 'tool_use' and isinstance(block.get('input'), dict):
                yield number, record.get('parent_tool_use_id'), block.get('name'), block['input']


def _key(value, cwd=None):
    """A comparable path: forward slashes, git-bash drive mounts and home references expanded, `..` collapsed."""
    text = value.strip().replace('\\', '/')
    home = re.match(rf"^(?:{_HOMES})(?=/|$)", text)
    if home:
        text = str(Path.home()).replace('\\', '/') + text[home.end():]
    drive = re.match(r'^/([A-Za-z])(?=/|$)', text)
    if drive:
        text = drive.group(1) + ':' + text[2:]
    if not re.match(r'^(?:[A-Za-z]:)?/', text):
        text = (cwd or '.') + '/' + text
    text = posixpath.normpath(text)
    return text.lower() if os.name == 'nt' else text


def _inside(key, roots):
    return any(key == root or key.startswith(root.rstrip('/') + '/') for root in roots)


def _command_paths(command):
    found = []
    for pattern in (DRIVE, ROOTED, PARENT, HOME):
        for match in pattern.finditer(command):
            path = match.group().rstrip(',.:')
            segments = path.strip('/').split('/')
            if pattern is ROOTED and len(segments) == 1 and not (segments[0] in TOP_LEVEL or len(segments[0]) == 1):
                continue
            if path and path not in HARMLESS and path not in found:
                found.append(path)
    return found


def scan(paths, allowed_roots, cwd=None):
    """Tool calls that touch paths outside the allowed roots: Read/Edit/Write/Glob/Grep path arguments and
    absolute, `..` or home paths in shell commands. Relative paths resolve against `cwd` (default: the first root).

    Findings are flags for review; nothing here prevents a read."""
    roots = [_key(str(root)) for root in allowed_roots]
    base = _key(str(cwd if cwd is not None else next(iter(allowed_roots))))
    findings = []
    for transcript in paths:
        for line, agent, tool, arguments in tool_calls(transcript):
            candidates = [(field, arguments[field]) for field in FILE_FIELDS.get(tool, ()) if isinstance(arguments.get(field), str)]
            if tool in COMMAND_TOOLS and isinstance(arguments.get('command'), str):
                candidates += [('command', path) for path in _command_paths(arguments['command'])]
            for field, value in candidates:
                key = _key(value, base)
                if not _inside(key, roots):
                    findings.append({'transcript': str(transcript), 'line': line, 'agent': agent, 'tool': tool,
                                     'field': field, 'path': value, 'resolved': key})
    return findings
