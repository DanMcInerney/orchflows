import json
from pathlib import Path
import re
import subprocess
import sys

from common import children, read_json

GUIDANCE = r'(?:code|research)(?:\.[a-z0-9-]+)?\.md'
# A guidance-folder path names guidance; a bare name does unless it names a workspace file, such as the research.md deliverable.
GUIDANCE_PATH = re.compile(r'(?i)guidance[\\/]+(' + GUIDANCE + r')\b')
BARE_NAME = re.compile(r'(?i)(?<![\w.\\/-])(' + GUIDANCE + r')\b')

PROGRAM = """
from vendor_a import normalize as a
from vendor_b import normalize as b
def expect(fn, record, milliseconds, outcome):
    actual = fn(record)
    assert actual == dict(id='0017', elapsed_ms=milliseconds, outcome=outcome), actual
    assert type(actual['elapsed_ms']) is int, actual
for duration, milliseconds in [('1.250', 1250), ('0', 0), ('0.001', 1)]:
    for ok in (True, False):
        expect(a, dict(id='0017', duration=duration, ok=ok), milliseconds, 'success' if ok else 'failure')
for duration, milliseconds in [(1250000, 1250), (0, 0), (1000, 1)]:
    for state in ('done', 'error'):
        expect(b, dict(key='0017', elapsed=duration, state=state), milliseconds, 'success' if state == 'done' else 'failure')
bad = [(a, dict(id='0017', duration=value, ok=True)) for value in ('-1', '0.0001')]
bad += [(a, dict(id='0017', duration='1', ok='yes'))]
bad += [(b, dict(key='0017', elapsed=value, state='done')) for value in (-1000, 999)]
bad += [(b, dict(key='0017', elapsed=1000, state=value)) for value in ('ok', 'failed')]
for fn, record in bad:
    try:
        fn(record)
    except ValueError:
        pass
    else:
        raise AssertionError(('Expected ValueError', record))
print('19 independent adapter cases passed')
"""


def text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n'.join(map(text, value))
    return text(value.get('text', '')) if isinstance(value, dict) else ''


def normal(value):
    return ' '.join(value.split())


def assignment(events):
    """The user messages that open a child transcript, before its first response or tool call."""
    opening = []
    for line in events.read_text(encoding='utf-8').splitlines():
        event = json.loads(line)
        if event.get('kind') == 'message' and event.get('role') == 'user':
            opening.append(text(event.get('data')))
        elif event.get('kind') in {'message', 'tool_call'}:
            break
    return '\n'.join(opening)


def carries_guidance(assigned, sentences, workspace_names):
    """Names an applicable core guidance file as a path or file name, or quotes one of its sentences."""
    if GUIDANCE_PATH.search(assigned):
        return True
    if any(name.lower() not in workspace_names for name in BARE_NAME.findall(assigned)):
        return True
    assigned = normal(assigned)
    return any(sentence in assigned for sentence in sentences)


def guidance_sentences(root):
    """Sentences of at least 40 characters from the run's core code and research guidance."""
    sentences = set()
    for path in (root / 'packages/orchflows/guidance').glob('*.md'):
        if re.fullmatch(GUIDANCE, path.name, re.I):
            for part in re.split(r'(?<=[.!?])\s+|\n+', path.read_text(encoding='utf-8')):
                part = normal(re.sub(r'^[\s#>*-]+', '', part))
                if len(part) >= 40:
                    sentences.add(part)
    return sentences


def check(c):
    checked = subprocess.run([sys.executable, '-B', '-c', PROGRAM], cwd=c.stage(), capture_output=True, text=True, timeout=20)
    c.require(checked.returncode == 0, 'Independent behavior cases', checked.stdout + checked.stderr)
    # Supplied inputs, including Codex's package copies under .agents/, are in the pre-run snapshot.
    before = read_json(c.stage().parent / 'before.json')['inputs']
    created = sorted(path.relative_to(c.stage()).as_posix() for path in c.stage().rglob('SKILL.md')
                     if path.is_file() and path.relative_to(c.stage()).as_posix() not in before)
    c.require(not created, 'Task does not create a reusable workflow',
              '; '.join(created) or 'stages/target/before.json: no new SKILL.md files')
    agents, evidence = children(c.stage().parent)
    c.require(1 <= len(agents) <= 6, 'Launch the required reviewers within the six-child cap', evidence)
    sentences = guidance_sentences(c.root)
    workspace_names = {path.name.lower() for path in c.stage().rglob('*.md')  # task files, not package copies
                       if not any(part.startswith('.') for part in path.relative_to(c.stage()).parts)}
    missing = []
    for agent in agents:
        events = c.stage().parent / 'evidence' / Path(agent['events_path']).name
        if not carries_guidance(assignment(events), sentences, workspace_names):
            missing.append('stages/target/evidence/' + events.name)
    c.require(not missing, 'Applicable core guidance reaches children: each assignment names or quotes code or research guidance',
              '; '.join(missing) + ': no guidance in the opening assignment' if missing else evidence)
