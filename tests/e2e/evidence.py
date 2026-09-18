"""Freeze available native records. Collection failures remain visible gaps."""
import argparse
import json
from pathlib import Path
import shutil

from common import write_json
import native_logs


def stream(path):
    records, gaps = [], []
    if not path.exists():
        return [], ['No native event stream']
    for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        try:
            records.append(json.loads(line))
        except ValueError:
            gaps.append(f'{path.name}:{number}: malformed or incomplete event')
    return records, gaps


def collect(host, identifier, destination, home=None):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    home = native_logs.native_home(host, home)
    agents, gaps, cursor = [], [], None
    while True:
        page = native_logs.inspect(host, identifier, home, limit=100, after=cursor)
        agents.extend(page['agents'])
        gaps.extend(page['discovery_gaps'])
        cursor = page['next_cursor']
        if cursor is None:
            break
    for agent in agents:
        source = Path(agent['path'])
        raw = destination / (agent['id'] + '.raw.jsonl')
        shutil.copy2(source, raw)
        normalized = destination / (agent['id'] + '.events.jsonl')
        with normalized.open('w', encoding='utf-8') as out:
            for event, _, _ in native_logs._located_events(raw, host):
                out.write(json.dumps(event, ensure_ascii=False) + '\n')
        agent['recorded_source'] = agent.pop('path')
        agent['raw'] = str(raw)
        agent['events_path'] = str(normalized)
    result = {'host': host, 'root_id': identifier, 'agents': agents, 'gaps': gaps,
              'scope': 'Recorded native descendants; independently launched CLI trials require their own session IDs.'}
    write_json(destination / 'index.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('host', choices=('claude', 'codex'))
    parser.add_argument('identifier')
    parser.add_argument('destination', type=Path)
    parser.add_argument('--home', type=Path)
    args = parser.parse_args()
    try:
        collect(args.host, args.identifier, args.destination, args.home)
    except Exception as error:
        write_json(args.destination / 'index.json', {'host': args.host, 'root_id': args.identifier,
                   'agents': [], 'gaps': [f'{type(error).__name__}: {error}']})
        raise SystemExit(1)
