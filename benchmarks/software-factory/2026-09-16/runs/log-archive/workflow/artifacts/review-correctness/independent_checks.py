"""Review-only observable checks and evidence binding; no source modifications."""
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import json
import os
import random
import string
import subprocess
import sys
import tempfile

ROOT = Path.cwd()
ARTIFACTS = ROOT.parent / 'artifacts'
sys.path.insert(0, str(ROOT))
import log_archive

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

manifest = json.loads((ARTIFACTS / 'pass1-candidate-manifest.json').read_text())
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == manifest['commit']
for name, expected in manifest['files'].items():
    assert digest(ROOT / name) == expected, name
evidence = json.loads((ARTIFACTS / 'pass1-check-evidence.json').read_text())
for name, expected in evidence['evidence_sha256'].items():
    assert digest(ARTIFACTS / name) == expected, name
measurement = json.loads((ARTIFACTS / 'pass1-final-benchmark.json').read_text())
for name, expected in measurement['source_sha256'].items():
    assert digest(ROOT / name) == expected, name
assert digest(Path(measurement['archive'])) == measurement['archive_sha256']
assert [row['order'] for row in measurement['rounds']] == [['baseline', 'candidate'], ['candidate', 'baseline']]
for row in measurement['rounds']:
    for arm in ('baseline', 'candidate'):
        assert len(row[arm + '_query_seconds']) == 48
        assert sum(row[arm + '_query_seconds']) == row[arm + '_seconds']
assert measurement['baseline_seconds'] / measurement['candidate_seconds'] == measurement['throughput_ratio']

alphabet = set(string.ascii_letters + string.digits + '_')
def words(text):
    result, word = set(), []
    for char in text + '!':
        if char in alphabet:
            word.append(char)
        elif word:
            result.add(''.join(word).lower())
            word.clear()
    return result

def oracle(records, *, query='', service=None, level=None, since=None, until=None, limit=50, offset=0):
    wanted = words(query)
    selected = [item for item in records
                if (service is None or service == item['service'])
                and (level is None or level == item['level'])
                and (since is None or item['timestamp'] >= since)
                and (until is None or item['timestamp'] < until)
                and wanted <= words(item['message'])]
    selected.sort(key=lambda item: item['timestamp'])
    return {'total': len(selected), 'items': selected[offset:offset + limit]}

rng = random.Random(162026)
messages = ['\u0130ERRo\u212a', 'ERRoR-timeout', '\u00dferroR\u00e9 timeout', 'ready\\word',
            'same_same 123', '東京 a  A', 'erro\u212a error', '', 'K K k', 'token\tline\rmore']
stamps = ['0001-01-01T00:00:00.000Z', '9999-12-31T23:59:59.999Z'] + [
    (datetime(2000, 2, 29) + timedelta(milliseconds=index)).isoformat(timespec='milliseconds') + 'Z'
    for index in range(20)]
records = [dict(id=str(index % 17), service=rng.choice(['api', 'API', 'worker']),
                level=rng.choice(['INFO', 'info', 'ERROR']), timestamp=rng.choice(stamps),
                message=rng.choice(messages), extra={'a': [index, {'unicode': '東京'}]})
           for index in range(300)]
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'independent.ndjson'
    path.write_text('\n'.join(map(json.dumps, records)) + '\nnull\n{bad\n[]\n', encoding='utf-8')
    for index in range(1000):
        lower, upper = sorted(rng.sample(stamps, 2))
        query = dict(query=rng.choice(messages + ['error timeout', 'K', 'İ', '---', 'error error', 'a']),
                     service=rng.choice([None, '', 'api', 'API', 'worker']),
                     level=rng.choice([None, '', 'INFO', 'info']),
                     since=rng.choice([None, lower]), until=rng.choice([None, upper]),
                     limit=rng.choice([0, 1, 50, 1000, 10**100]),
                     offset=rng.choice([0, 1, 300, 10**100]))
        assert log_archive.search_logs(path, **query) == oracle(records, **query), (index, query)
    result = log_archive.search_logs(path, limit=1000)
    result['items'][0]['extra']['a'][1]['unicode'] = 'mutated'
    assert log_archive.search_logs(path, limit=1000) == oracle(records, limit=1000)
    original = path.stat()
    with path.open(encoding='utf-8') as handle:
        by_handle = os.fstat(handle.fileno())
    stat_fingerprint = log_archive._fingerprint(original)
    fstat_fingerprint = log_archive._fingerprint(by_handle)
    assert stat_fingerprint == fstat_fingerprint
    for number in range(100):
        # All versions retain the exact size and original modification timestamp.
        item = dict(id=f'{number:03d}', service='api', level='INFO', message='version',
                    timestamp='2026-01-01T00:00:00.000Z')
        replacement = Path(directory) / 'replace.ndjson'
        replacement.write_text(json.dumps(item), encoding='utf-8')
        os.utime(replacement, ns=(original.st_atime_ns, original.st_mtime_ns))
        os.replace(replacement, path)
        assert log_archive.search_logs(path) == {'total': 1, 'items': [item]}
    cli = subprocess.run([sys.executable, '-B', str(ROOT / 'log_archive.py'), '--file', str(path),
                          '--since', '0001-01-01T00:00:00.000Z', '--limit', str(10**100)],
                         capture_output=True, text=True, encoding='utf-8')
    assert cli.returncode == 0, cli.stderr
    assert json.loads(cli.stdout) == {'total': 1, 'items': [item]}

print(json.dumps({'status': 'passed', 'commit': manifest['commit'],
                  'manifest_files_verified': len(manifest['files']),
                  'evidence_hashes_verified': len(evidence['evidence_sha256']),
                  'independent_oracle_queries': 1000, 'preserved_mtime_replacements': 100,
                  'stat_fingerprint': stat_fingerprint, 'fstat_fingerprint': fstat_fingerprint,
                  'benchmark_evidence_ratio': measurement['throughput_ratio'],
                  'benchmark_rerun': False, 'runtime': sys.version}, indent=2))
