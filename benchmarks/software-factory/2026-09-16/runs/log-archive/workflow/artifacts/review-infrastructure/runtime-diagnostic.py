import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter
import tracemalloc

root = Path.cwd()
out = root.parent / 'artifacts' / 'review-infrastructure'
sys.path.insert(0, str(root))
import log_archive
manifest = json.loads((root.parent / 'artifacts' / 'pass1-candidate-manifest.json').read_text(encoding='utf-8-sig'))
persistent = root.parent / 'project'
ignored = {'.git', '__pycache__', '.pytest_cache', 'software-factory-runs'}
files = {p.relative_to(persistent).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in sorted(persistent.rglob('*'))
         if p.is_file() and not any(part in ignored for part in p.relative_to(persistent).parts)}
assert files == manifest['files']
archive = root.parent / 'artifacts' / 'pass1-final-benchmark.ndjson'
tracemalloc.start()
started = perf_counter()
answer = log_archive.search_logs(archive, query='error timeout', limit=10)
cold = perf_counter() - started
retained, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
started = perf_counter()
warm_answer = log_archive.search_logs(archive, query='error timeout', limit=10)
warm = perf_counter() - started
assert warm_answer == answer
report = {
    'persistent_candidate_files_match_manifest': True,
    'archive_records': 30000,
    'archive_bytes': archive.stat().st_size,
    'cold_seconds_with_tracemalloc_overhead': cold,
    'python_traced_retained_bytes': retained,
    'python_traced_peak_bytes': peak,
    'single_warm_seconds_without_tracemalloc': warm,
    'same_answers': True,
    'interpretation': 'Diagnostic only; tracing adds cold timing overhead and Python allocation totals are not process RSS. No acceptance performance claim is based on this measurement. Cache capacity is eight archive snapshots, not a byte limit.'
}
(out / 'runtime-diagnostic.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
