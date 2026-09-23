import json
import re

from common import children, digest

# An interpreter running the verifier, and the verifier's own success line (not its source, which prints it).
RUN = re.compile(r'(?i)\b(?:python[\d.]*|py|uv\s+run(?:\s+python[\d.]*)?)(?:\.exe)?["\']?\s[^\n;|&]*verify_invoice\.py')
PASSED = re.compile(r'(?m)^\s*Invoice checks passed\s*$')


def text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        value = list(value.values())
    return '\n'.join(map(text, value)) if isinstance(value, list) else ''


def verifier_runs(stage):
    """Recorded native commands, by any target agent, that ran verify_invoice.py and reported success."""
    found = []
    for events in sorted((stage / 'evidence').glob('*.events.jsonl')):
        calls = set()
        for number, line in enumerate(events.read_text(encoding='utf-8').splitlines(), 1):
            event = json.loads(line)
            # Delegation calls carry the command in a prompt; their results are reports, not command output.
            if (event.get('kind') == 'tool_call' and event.get('tool') not in {'Agent', 'Task'}
                    and RUN.search(text(event.get('data')))):
                calls.add(event.get('call_id'))
            elif (event.get('kind') == 'tool_result' and event.get('call_id') in calls and not event.get('is_error')
                  and PASSED.search(text([event.get('presented_output'), event.get('data')]))):
                found.append(f'stages/{stage.name}/evidence/{events.name}:{number}')
    return found


def check(c):
    w = c.stage()
    runs = verifier_runs(w.parent)
    c.require(bool(runs), 'The required check ran: verify_invoice.py reported success in a recorded command',
              runs[0] if runs else 'stages/target/evidence: no recorded successful verify_invoice.py run')
    c.require(c.json(w/'invoice.json') == {'audience':'internal','title':'Invoice record','total':273,'currency':'USD'}, 'Correct internal invoice', 'invoice.json')
    c.require(c.json(w/'public.json') == {'audience':'public','title':'Invoice summary','total':273,'currency':'USD'}, 'Correct separately scoped public summary', 'public.json')
    c.require(c.json(w/'checks.json') == {'passed':True,'sha256':digest(w/'invoice.json')}, 'Required check matches candidate', 'checks.json')
    for name in ('review.md','handoff.md'):
        c.require((w/name).is_file() and bool((w/name).read_text(encoding='utf-8', errors='replace').strip()),
                  'Return review and delivery evidence', name)
    agents, evidence = children(c.stage().parent)
    c.require(len(agents) >= 2, 'Launch the invoice reviewer and the fresh public-summary maker', evidence)
