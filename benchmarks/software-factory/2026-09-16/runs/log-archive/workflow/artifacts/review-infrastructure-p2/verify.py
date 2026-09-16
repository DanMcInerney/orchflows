import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path.cwd()
artifacts = root.parent / 'artifacts'
out = artifacts / 'review-infrastructure-p2'
manifest = json.loads((artifacts / 'pass2-candidate-manifest.json').read_text(encoding='utf-8-sig'))
checks = json.loads((artifacts / 'pass2-check-evidence.json').read_text(encoding='utf-8-sig'))
benchmark = json.loads((artifacts / 'pass2-final-benchmark.json').read_text(encoding='utf-8-sig'))
shared = Path('C:/Users/danhm/.orchflows/artifacts/software-factory-comparison-20260916-01/tools')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

ignored = {'.git', '__pycache__', '.pytest_cache', 'software-factory-runs'}
files = {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*'))
         if p.is_file() and not any(part in ignored for part in p.relative_to(root).parts)}
identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
evidence = {name: sha(artifacts / name) == expected for name, expected in checks['evidence_sha256'].items()}
benchmark_sources = {name: sha(root / name) == expected for name, expected in benchmark['source_sha256'].items()}
protected = json.loads((artifacts / 'preserved-baseline-hashes.json').read_text(encoding='utf-8-sig'))
preserved = {Path(row['Path']).name: sha(root / ('tests/test_public.py' if Path(row['Path']).name == 'test_public.py' else Path(row['Path']).name)) == row['Hash'].lower() for row in protected}
syntax = {}
for path in root.rglob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path), feature_version=(3, 11))
    syntax[str(path.relative_to(root))] = 'Python 3.11 grammar accepted'
report = {
    'python': sys.version,
    'commit': subprocess.check_output(['git', '-C', str(root.parent / 'project'), 'rev-parse', 'HEAD'], text=True).strip(),
    'git_status': subprocess.check_output(['git', '-C', str(root.parent / 'project'), 'status', '--short'], text=True).strip(),
    'source_sha256': identity,
    'source_identity_matches': identity == manifest['sha256'] == checks['candidate_sha256'],
    'manifest_files_match': files == manifest['files'],
    'protected_files_match': preserved,
    'evidence_hashes_match': evidence,
    'benchmark_sources_match': benchmark_sources,
    'benchmark_archive_matches': sha(artifacts / 'pass2-final-benchmark.ndjson') == benchmark['archive_sha256'],
    'benchmark_round_order': [r['order'] for r in benchmark['rounds']],
    'benchmark_measurement_counts': [{k:len(r[k]) for k in ('baseline_query_seconds','candidate_query_seconds')} for r in benchmark['rounds']],
    'benchmark_ratio_recomputed': sum(sum(r['baseline_query_seconds']) for r in benchmark['rounds']) / sum(sum(r['candidate_query_seconds']) for r in benchmark['rounds']),
    'all_answers_equal': benchmark['all_timed_answers_equal'] and all(r['all_answers_equal'] for r in benchmark['rounds']),
    'syntax': syntax,
}
assert report['commit'] == manifest['commit'] == checks['candidate_commit']
assert report['source_identity_matches'] and report['manifest_files_match']
assert all(evidence.values()) and all(benchmark_sources.values()) and all(preserved.values())
assert report['benchmark_archive_matches']
assert abs(report['benchmark_ratio_recomputed'] - benchmark['throughput_ratio']) < 1e-9
(out / 'identity-and-evidence.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
commands = [
    ('tests', [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']),
    ('cli-sample', [sys.executable, 'log_archive.py', '--file', 'sample.ndjson', '--query', 'gateway timeout', '--limit', '10']),
    ('simulator-status', [sys.executable, str(shared / 'release_simulator.py'), '--state', str(artifacts / 'release-state.json'), 'status']),
]
state_before = sha(artifacts / 'release-state.json')
for label, command in commands:
    completed = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', env=env, timeout=60)
    (out / (label + '.txt')).write_text('command: ' + subprocess.list2cmdline(command) + '\nexit_code: ' + str(completed.returncode) + '\nstdout:\n' + completed.stdout + '\nstderr:\n' + completed.stderr, encoding='utf-8')
    assert completed.returncode == 0, (label, completed.stderr)
    report[label + '_exit_code'] = completed.returncode
    if label == 'simulator-status':
        state = json.loads(completed.stdout)
        report['release'] = {k: state[k] for k in ('case', 'phase', 'exposure', 'candidate')}
        report['release']['baseline_identity'] = state['baseline']['sha256']
        report['release']['event_count'] = len(state['events'])
report['release_state_unchanged'] = state_before == sha(artifacts / 'release-state.json')
assert report['release_state_unchanged']
(out / 'identity-and-evidence.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))

candidate = root.parent / 'project'
candidate_files = {p.relative_to(candidate).as_posix(): sha(p) for p in sorted(candidate.rglob('*')) if p.is_file() and not any(part in ignored for part in p.relative_to(candidate).parts)}
report['persistent_candidate_manifest_match'] = candidate_files == files == manifest['files']
assert report['persistent_candidate_manifest_match']
assert report['git_status'] == '?? caller-note.txt'
report['benchmark_round_totals_match'] = all(abs(sum(r[name+'_query_seconds']) - r[name+'_seconds']) < 1e-9 for r in benchmark['rounds'] for name in ('baseline', 'candidate'))
assert report['benchmark_round_totals_match']
assert benchmark['records'] == 30000 and benchmark['queries_per_round'] == 48
assert [r['order'] for r in benchmark['rounds']] == [['baseline', 'candidate'], ['candidate', 'baseline']]
assert all(len(r[name+'_query_seconds']) == 48 for r in benchmark['rounds'] for name in ('baseline', 'candidate'))
assert report['all_answers_equal'] and report['benchmark_ratio_recomputed'] >= 5
assert all(row['exit_code'] == 0 for row in checks['required_checks'])
assert sha(artifacts / 'pass2-final-benchmark.json') == sha(artifacts / 'pass2-final-benchmark-stdout.json')
report['snapshot_after_checks_matches'] = {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*')) if p.is_file() and not any(part in ignored for part in p.relative_to(root).parts)} == files
assert report['snapshot_after_checks_matches']
(out / 'identity-and-evidence.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('Final snapshot/persistent candidate and all benchmark arithmetic checks passed.')

