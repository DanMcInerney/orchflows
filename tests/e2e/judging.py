"""Evidence review and conservative aggregation; no target retries."""
from pathlib import Path
import json
import uuid

from common import HERE, read_json, write_json
from sealing import verify

SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['assessment', 'findings', 'observations', 'gaps'],
          'properties': {'assessment': {'type': 'string', 'enum': ['acceptable', 'material_failure', 'inconclusive']},
            'findings': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
                'required': ['requirement', 'evidence', 'consequence'],
                'properties': {key: {'type': 'string'} for key in ('requirement', 'evidence', 'consequence')}}},
            'observations': {'type': 'array', 'items': {'type': 'string'}},
            'gaps': {'type': 'array', 'items': {'type': 'string'}}}}


def validate(value):
    if not isinstance(value, dict) or set(value) != set(SCHEMA['required']):
        raise ValueError('Missing or unknown audit fields')
    if value['assessment'] not in SCHEMA['properties']['assessment']['enum']:
        raise ValueError('Unknown assessment')
    for key in ('findings', 'observations', 'gaps'):
        if not isinstance(value[key], list):
            raise ValueError(f'{key} must be a list')
    for finding in value['findings']:
        if not isinstance(finding, dict) or set(finding) != {'requirement', 'evidence', 'consequence'}:
            raise ValueError('Material finding lacks required evidence')
        if any(not isinstance(v, str) or not v.strip() for v in finding.values()):
            raise ValueError('Empty finding')
    if any(not isinstance(x, str) for key in ('observations', 'gaps') for x in value[key]):
        raise ValueError('Invalid observation or gap')
    if value['assessment'] == 'acceptable' and (value['findings'] or value['gaps']):
        raise ValueError('Acceptable assessment has material findings or critical gaps')
    if value['assessment'] == 'material_failure' and not value['findings']:
        raise ValueError('Failure assessment lacks an evidenced finding')
    return value


def aggregate(target, checks, audit):
    findings = [c for c in checks.get('checks', []) if not c['passed'] and
                (target.get('completed') or c.get('invariant'))]
    findings += audit.get('findings', [])
    gaps = [*target.get('gaps', []), *checks.get('gaps', []), *audit.get('gaps', [])]
    assessment = 'material_failure' if findings else 'acceptable'
    if not findings and (gaps or not target.get('completed') or audit.get('assessment') != 'acceptable'):
        assessment = 'inconclusive'
    return {'assessment': assessment, 'findings': findings, 'observations': audit.get('observations', []), 'gaps': gaps}


def packet(root):
    """Deterministic evidence projection, with explicit pointers for every excerpt."""
    target = read_json(root / 'target.json')
    pieces = ['# Evidence packet', 'Excerpts are indexed, not complete transcripts. Expand material truncations from cited files.',
              '## Acceptance', (root / 'evaluation/expected-behavior.md').read_text(encoding='utf-8'),
              '## Execution', json.dumps({k: v for k, v in target.items() if k != 'stages'}, ensure_ascii=False),
              '## Checks', json.dumps(read_json(root / 'checks.json'), ensure_ascii=False)]
    for stage in target.get('stages', []):
        directory = root / 'stages' / stage['name']
        pieces += ['## Stage ' + stage['name'], (directory / 'request.txt').read_text(encoding='utf-8'),
                   json.dumps({'execution': stage['execution'], 'gaps': stage['gaps'],
                               'model': stage['native'].get('model'), 'tools': stage['native'].get('tools'),
                               'workspace': stage['workspace']}, ensure_ascii=False)]
        index = directory / 'evidence/index.json'
        if not index.exists():
            pieces.append('Native evidence index unavailable.')
            continue
        evidence = read_json(index)
        pieces.append(json.dumps({'root_id': evidence['root_id'], 'gaps': evidence.get('gaps', [])}))
        for agent in evidence.get('agents', []):
            pieces.append(f"### Agent {agent['id']}; parent {agent.get('parent_id')}; tools {agent.get('tools')}; "
                          f"models {agent.get('models')}; efforts {agent.get('efforts')}")
            pieces.append(json.dumps({key: agent.get(key) for key in
                ('gaps', 'error_count', 'calls_without_recorded_results')}, ensure_ascii=False))
            event_path = Path(agent['events_path'])
            for line, text in enumerate(event_path.read_text(encoding='utf-8').splitlines(), 1):
                event = json.loads(text)
                if event.get('kind') not in {'message', 'tool_call', 'tool_result', 'gap', 'unsupported'}:
                    continue
                value = {k: v for k, v in event.items() if k not in {'source', 'timestamp', 'flags'}}
                rendered = json.dumps(value, ensure_ascii=False)
                limit = 6000 if event.get('kind') == 'tool_call' or event.get('role') == 'user' else 1000
                excerpt = rendered[:limit] + (' [TRUNCATED: expand source]' if len(rendered) > limit else '')
                pieces.append(f"{event_path.relative_to(root).as_posix()}:{line}\n{excerpt}")
    return '\n\n'.join(pieces)


async def audit_run(root, host, scheduler, timeout=60):
    root = Path(root)
    directory = root / 'audits' / uuid.uuid4().hex[:12]
    directory.mkdir(parents=True)
    value = {'assessment': 'inconclusive', 'findings': [], 'observations': [], 'gaps': verify(root)}
    if value['gaps']:
        write_json(directory / 'assessment.json', value)
        return {**value, 'audit_path': str(directory), 'audit_complete': False}
    # Re-audit uses the current evaluator, with its exact brief/schema preserved separately.
    brief = (HERE / 'review.md').read_text(encoding='utf-8')
    (directory / 'review.md').write_text(brief, encoding='utf-8')
    write_json(directory / 'schema.json', SCHEMA)
    evidence_packet = packet(root)
    (directory / 'packet.md').write_text(evidence_packet, encoding='utf-8')
    request = brief + '\n\nEvidence root: ' + str(root) + '\nPackage contracts and guidance are under packages/. '
    request += 'Available time is ' + str(timeout) + ' seconds. Inspect actual output files and expand material truncated evidence as needed. '
    request += 'Return the requested structured output directly when ready. Do not write a narrative report first. '
    request += 'Observations should be brief. gaps means only critical missing evidence preventing acceptance; '
    request += 'disclosed test limitations belong in observations. Return empty findings/gaps on acceptance.\n\n'
    request += evidence_packet
    (directory / 'request.txt').write_text(request, encoding='utf-8')
    command = host.command({}, 'audit', SCHEMA, root, directory=directory)
    execution = await scheduler.process(command, cwd=root, directory=directory, prompt=request,
                                         timeout=timeout, label='audit:' + root.name)
    native = host.result(directory)
    write_json(directory / 'native.json', native)
    complete = False
    try:
        if execution['status'] != 'completed' or native['gaps']:
            raise ValueError('Audit did not complete (' + execution['status'] + '): ' + str(native['gaps'] + execution['gaps']))
        value = validate(native['structured_output'])
        complete = True
    except (ValueError, TypeError) as error:
        value['gaps'].append(str(error))
    value['gaps'].extend(verify(root))
    if value['gaps'] and value['assessment'] == 'acceptable':
        value['assessment'] = 'inconclusive'
    write_json(directory / 'assessment.json', value)
    return {**value, 'audit_path': str(directory), 'audit_complete': complete}
