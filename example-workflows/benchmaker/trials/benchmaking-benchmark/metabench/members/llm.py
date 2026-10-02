"""LLM pool members for the shim: single Claude calls and short agent runs, optionally with a harness defect.

A spec is the `llm` entry of ORDER.json, with the I/O the domain needs:

    {"kind": "llm", "mode": "single-call" | "agent", "model": "claude-haiku-4-5", "effort": "low",
     "harness_defect": null | "truncate_busy:0.6" | "last_chars:4000" | "unnumbered_lines" | "skill:<path>" | "skill_hidden",
     "io": {"output": "output.json", "inputs": null, "number_lines": false},     # single-call
     "tools": "Read,Write,Edit,Bash,Glob,Grep", "skill": null}                   # agent

Single call: no tools, `--safe-mode`; the harness puts the input files in the prompt, asks for the output file's
content as the reply and writes it. `inputs` null means every workspace file except the output.
  truncate_busy:F   each participant of a JSON input keeps the first floor(F * n) busy intervals
  last_chars:N      each input keeps its last N characters; kept lines keep their original numbers
  unnumbered_lines  inputs listed with `number_lines` are shown without their "n: " prefixes
Agent: the model works in the workspace with `tools`. A skill (`skill:<path>`, or `skill` in the spec) is loaded
as a plugin without `--safe-mode`; `skill_hidden` loads a copy of `skill` whose descriptions never match."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re
import shutil
import tempfile

from .. import transcripts
from ..builders import claude_settings, clean_env, default_launcher

AGENT_TOOLS = 'Read,Write,Edit,Bash,Glob,Grep'
EXIT_CODES = {'completed': 0, 'refused': 0, 'cut-off': 0, 'timeout': 2, 'usage-limit': 3, 'error': 1}
HIDDEN_DESCRIPTION = 'Archive of retired tax forms, consulted only for 1998 filing questions.'
INPUT_DEFECTS = {'truncate_busy', 'last_chars', 'unnumbered_lines'}
SKILL_DEFECTS = {'skill', 'skill_hidden'}


def defect_of(spec):
    """(name, argument) of the harness defect; unknown names and names of the other mode are errors."""
    name, _, argument = (spec.get('harness_defect') or '').partition(':')
    mode = spec.get('mode', 'single-call')
    if mode not in ('single-call', 'agent'):
        raise ValueError(f'Unknown member mode {mode!r}')
    if name and name not in (INPUT_DEFECTS if mode == 'single-call' else SKILL_DEFECTS):
        raise ValueError(f'Harness defect {name!r} does not apply to {mode} members')
    return name, argument


def skill_of(spec):
    name, argument = defect_of(spec)
    return argument if name == 'skill' else spec.get('skill')


def hide_description(text):
    """SKILL.md with every description replaced by one that never matches a request."""
    match = re.match(r'---\r?\n(.*?)\r?\n---\r?\n', text, re.S)
    if not match:
        raise ValueError('SKILL.md has no frontmatter')
    kept, skipping = [], False
    for line in match.group(1).splitlines():
        if line.startswith('description:'):
            skipping = True
        elif not (skipping and line.startswith((' ', '\t'))):
            skipping = False
            kept.append(line)
    return '---\n' + '\n'.join([*kept, 'description: ' + HIDDEN_DESCRIPTION]) + '\n---\n' + text[match.end():]


def hidden_copy(skill, destination):
    shutil.copytree(skill, destination, ignore=shutil.ignore_patterns('__pycache__', '.git'))
    for path in Path(destination).rglob('SKILL.md'):
        path.write_text(hide_description(path.read_text(encoding='utf-8')), encoding='utf-8')
    return Path(destination)


def command(spec, *, skill=None, executable=None, config_dir=None):
    """The member's Claude command; the prompt goes to stdin. Without a skill it runs in safe mode."""
    tools = spec.get('tools', AGENT_TOOLS) if spec.get('mode') == 'agent' else ''
    if skill and 'Skill' not in tools.split(','):
        tools = ','.join(filter(None, [tools, 'Skill']))
    result = [executable or shutil.which('claude') or 'claude', '-p', *([] if skill else ['--safe-mode']),
              '--model', spec['model'], '--effort', spec['effort'], '--permission-mode', 'dontAsk', '--tools', tools,
              *(['--allowedTools', tools] if tools else []), '--no-session-persistence', '--output-format', 'json']
    if skill:
        result += ['--strict-mcp-config', '--setting-sources', 'user',
                   '--settings', json.dumps(claude_settings(config_dir)), '--plugin-dir', str(skill)]
    return result


def present(text, defect, argument, number_lines):
    """One input file as the member sees it, and whether the harness defect changed it."""
    offset, changed = 0, False
    if defect == 'truncate_busy':
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if isinstance(data, dict) and isinstance(data.get('participants'), list):
            for person in data['participants']:
                busy = person.get('busy') if isinstance(person, dict) else None
                if isinstance(busy, list):
                    kept = busy[:math.floor(len(busy) * float(argument) + 1e-9)]
                    changed = changed or len(kept) != len(busy)
                    person['busy'] = kept
            text = json.dumps(data, indent=2)
    elif defect == 'last_chars' and len(text) > int(argument):
        offset, text, changed = text[:len(text) - int(argument)].count('\n'), text[-int(argument):], True
    if number_lines and defect != 'unnumbered_lines':
        text = '\n'.join(f'{offset + n}: {line}' for n, line in enumerate(text.splitlines(), 1))
    return text, changed or (number_lines and defect == 'unnumbered_lines')


def single_call_prompt(spec, instruction, workspace):
    """The instruction, the input files and the reply format; returns the prompt and whether a defect applied."""
    workspace, io = Path(workspace), spec.get('io') or {}
    output = io.get('output', 'output.json')
    defect, argument = defect_of(spec)
    names = io.get('inputs')
    if names is None:
        names = sorted(p.relative_to(workspace).as_posix() for p in workspace.rglob('*')
                       if p.is_file() and '.git' not in p.parts and p.relative_to(workspace).as_posix() != output)
    parts, applied = [instruction.rstrip(), "The task's input files follow. You cannot read or write files."], False
    for name in names:
        text, changed = present((workspace / name).read_text(encoding='utf-8', errors='replace'), defect, argument,
                                bool(io.get('number_lines')))
        applied = applied or changed
        parts.append(f'=== {name} ===\n{text}')
    kind = 'as a single JSON value' if output.endswith('.json') else 'as plain text'
    parts.append(f'Reply with the complete content of {output} {kind} and nothing else.')
    return '\n\n'.join(parts), applied


def extract_json(text):
    """The first JSON value in a reply: the whole text, a fenced block, or the first parseable object or array."""
    text = text.strip()
    for candidate in [text, *re.findall(r'```(?:json)?\s*(.*?)```', text, re.S)]:
        try:
            return json.loads(candidate)
        except ValueError:
            pass
    for start, char in enumerate(text):
        if char in '{[':
            try:
                return json.JSONDecoder().raw_decode(text[start:])[0]
            except ValueError:
                pass
    raise ValueError('no JSON value in the reply')


def deliver(reply, output):
    """The bytes of the output file from the reply; ValueError when it holds none."""
    if output.endswith('.json'):
        return json.dumps(extract_json(reply), ensure_ascii=False).encode('utf-8')
    fenced = re.fullmatch(r'```\w*\n(.*)\n```', reply.strip(), re.S)
    return (fenced.group(1) if fenced else reply.strip()).encode('utf-8')


def run(spec, *, workspace, prompt, timeout, launcher=None, executable=None, config_dir=None, env=None):
    """Run one member on one task and return the solver-protocol fields.

    `launcher` has the signature of benchkit.launch.run_capped. The shim chooses the process exit code with
    EXIT_CODES[status]. A reply without the output's content leaves the workspace without it."""
    workspace, mode = Path(workspace), spec.get('mode', 'single-call')
    defect, argument = defect_of(spec)
    skill = skill_of(spec)
    if defect == 'skill_hidden' and not skill:
        raise ValueError('skill_hidden needs a `skill` in the spec')
    with tempfile.TemporaryDirectory(prefix='bmk-llm-', ignore_cleanup_errors=True) as scratch:
        scratch = Path(scratch)
        if defect == 'skill_hidden':
            skill = hidden_copy(skill, scratch / 'skill')
        text, applied = single_call_prompt(spec, prompt, workspace) if mode == 'single-call' else (prompt, bool(skill))
        out, err = scratch / 'out.json', scratch / 'err.txt'
        outcome = (launcher or default_launcher())(command(spec, skill=skill, executable=executable, config_dir=config_dir),
                                                   cwd=workspace, env=clean_env(env), stdout=out, stderr=err,
                                                   stdin=text.encode('utf-8'), timeout=timeout)
        raw = out.read_text(encoding='utf-8', errors='replace') if out.is_file() else ''
        stderr = err.read_text(encoding='utf-8', errors='replace') if err.is_file() else ''
    result = transcripts.parse_result(raw)
    status = 'timeout' if outcome.status == 'timeout' else transcripts.classify(result, stderr)
    if outcome.status in ('error', 'canceled') and status == 'completed':
        status = 'error'
    reply, note, wrote = str((result or {}).get('result') or ''), '', []
    if mode == 'single-call' and status == 'completed':
        output = (spec.get('io') or {}).get('output', 'output.json')
        try:
            (workspace / output).parent.mkdir(parents=True, exist_ok=True)
            (workspace / output).write_bytes(deliver(reply, output))
            wrote.append(output)
        except ValueError as error:
            note = f'No {output} written: {error}'
    models = sorted((result or {}).get('modelUsage') or {})
    draw = f"llm:{mode}:{spec['model']}:{spec['effort']}" + (f':{defect}:applied={str(applied).lower()}' if defect else '')
    return {'status': status, 'exit_code': outcome.exit_code, 'seconds': round(outcome.seconds, 2),
            'model': models[0] if len(models) == 1 else spec['model'], 'models': models,
            'cost_usd': (result or {}).get('total_cost_usd'), 'final': reply[-2000:], 'wrote': wrote, 'note': note,
            'behavior_draw': draw, 'findings': [], 'left_running': outcome.left_running,
            'stderr': stderr[-500:] if status == 'error' else ''}
