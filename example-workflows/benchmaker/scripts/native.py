"""Bounded subprocess collection. Native receipts retain bytes, never inferred model ids."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from records import require


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def run_process(command, *, cwd, stdin='', timeout=90):
    require(timeout > 0, 'timeout must be positive')
    started = time.monotonic()
    options = {'start_new_session': True} if os.name != 'nt' else {
        'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
    try:
        process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, **options)
    except (OSError, ValueError) as error:
        return dict(stdout=b'', stderr=str(error).encode(), exit_code=None,
                    timed_out=False, launch_error=type(error).__name__,
                    elapsed_seconds=time.monotonic() - started)
    timed_out = False
    try:
        stdout, stderr = process.communicate(stdin.encode('utf-8'), timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name == 'nt':
            cleanup = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                     capture_output=True, timeout=10)
            if cleanup.returncode and process.poll() is None:
                process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        stdout, stderr = process.communicate(timeout=10)
    return dict(stdout=stdout, stderr=stderr, exit_code=process.returncode,
                timed_out=timed_out, launch_error=None,
                elapsed_seconds=time.monotonic() - started)


def parse_native(raw):
    events = []
    for line in raw.decode('utf-8').splitlines():
        if line.strip():
            event = json.loads(line)
            require(isinstance(event, dict) and 'type' in event, 'invalid native event')
            events.append(event)
    require(events, 'empty native transcript')
    source, usage = None, {'unavailable_reason': 'Native transcript did not report token usage'}
    for event in events:
        if event['type'] == 'item.completed' and event.get('item', {}).get('type') == 'agent_message':
            try:
                submission = json.loads(event['item']['text'])
                if isinstance(submission, dict) and set(submission) == {'source'} and isinstance(submission['source'], str):
                    source = submission['source']
            except (ValueError, KeyError):
                pass
        if event['type'] == 'turn.completed':
            usage = event.get('usage') or {'unavailable_reason': 'Native completion did not report token usage'}
    return dict(events=events, source=source, token_usage=usage,
                established=any(e['type'] == 'turn.started' for e in events),
                completed=any(e['type'] == 'turn.completed' for e in events),
                native_error=any(e['type'] in {'error', 'turn.failed'} for e in events))



def classify_execution(result, parsed):
    if result['launch_error']:
        return 'permission_failure' if result['launch_error'] == 'PermissionError' else 'launch_failure'
    elif result['timed_out']:
        return 'task_timeout' if parsed['established'] else 'startup_timeout'
    elif parsed['native_error'] or not parsed['established']:
        return 'environment_failure'
    elif result['exit_code'] != 0 or not parsed['completed'] or parsed['source'] is None:
        return 'candidate_failure'
    else:
        return 'completed'


def collect(command, *, case_repository, prompt, output, configuration, timeout=90,
            configuration_observation=None, case_binding=None):
    """Run exactly the caller's declared argv; stores a receipt even on launch failure."""
    observed = None
    if configuration_observation:
        observed = read_json(configuration_observation)
        require(observed['configuration'] == configuration, 'configuration observation differs from requested target')
        require(Path(observed['evidence_locator']).is_file(), 'missing configuration observation evidence')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    require(command and all(isinstance(part, str) for part in command), 'command must be argv')
    executable = shutil.which(command[0])
    resolved = [executable or command[0], *command[1:]]
    prompt_text = Path(prompt).read_text(encoding='utf-8-sig')
    (output / 'prompt.txt').write_text(prompt_text, encoding='utf-8')
    from case_inputs import capture_inputs
    require(case_binding is not None, 'missing committed case binding')
    binding, inputs = capture_inputs(case_binding, case_repository, prompt, output)
    result = run_process(resolved, cwd=case_repository, stdin=prompt_text, timeout=timeout)
    (output / 'stdout.jsonl').write_bytes(result.pop('stdout'))
    (output / 'stderr.txt').write_bytes(result.pop('stderr'))
    try:
        parsed = parse_native((output / 'stdout.jsonl').read_bytes())
    except (ValueError, UnicodeError):
        parsed = dict(source=None, token_usage={'unavailable_reason': 'No parseable native completion'}, established=False, completed=False, native_error=False)
    classification = classify_execution(result, parsed)
    if parsed['source'] is not None:
        (output / 'solution.py').write_text(parsed['source'], encoding='utf-8')
    receipt = dict(result, classification=classification, case_binding=binding, input_observations=inputs, requested_command=command,
                   resolved_command=resolved, requested_configuration=configuration,
                   resolved_configuration={'unavailable_reason': 'Native JSON events do not attest the full requested configuration'},
                   prompt_locator=str(output / 'prompt.txt'), raw_transcript_locator=str(output / 'stdout.jsonl'),
                   stderr_locator=str(output / 'stderr.txt'), result_artifact_locator=(
                       str(output / 'solution.py') if parsed['source'] is not None else {'unavailable_reason': classification}),
                   token_usage=parsed['token_usage'], environment_established=parsed['established'],
                   timeout_seconds=timeout, case_repository=str(Path(case_repository).resolve()))
    if observed:
        receipt['resolved_configuration'] = observed['configuration']
        receipt['configuration_observation'] = dict(locator=str(Path(configuration_observation).resolve()),
            sha256=digest(configuration_observation), evidence_locator=observed['evidence_locator'],
            evidence_sha256=digest(observed['evidence_locator']))
    if receipt['exit_code'] is None:
        receipt['exit_code'] = {'unavailable_reason': receipt['launch_error']}
    receipt['sha256'] = {name: digest(output / name) for name in ['prompt.txt', 'stdout.jsonl', 'stderr.txt']}
    if parsed['source'] is not None:
        receipt['sha256']['solution.py'] = digest(output / 'solution.py')
    write_json(output / 'launch.json', receipt)
    return receipt


def codex_command(repository, schema, executable='codex'):
    return [executable, 'exec', '--ignore-user-config', '--ephemeral', '--json',
            '--sandbox', 'read-only', '--model', 'gpt-5.6-sol', '-c',
            'model_reasoning_effort="low"', '-C', str(Path(repository).resolve()),
            '--output-schema', str(Path(schema).resolve()), '-']
