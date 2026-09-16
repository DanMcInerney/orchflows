import hashlib, json, subprocess, sys
from pathlib import Path
ROOT=Path.cwd()
ART=ROOT.parent/'artifacts'
sys.path.insert(0,str(ROOT))
import log_archive, benchmark
manifest=json.loads((ART/'pass2-candidate-manifest.json').read_text())
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
for root in (ROOT, ROOT.parent/'project'):
    files={p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
           if p.is_file() and not any(x in {'.git','__pycache__','.pytest_cache','software-factory-runs'}
                                     for x in p.relative_to(root).parts)}
    assert files==manifest['files']
    assert hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()==manifest['sha256']
for row in json.loads((ART/'preserved-baseline-hashes.json').read_text(encoding='utf-8-sig')):
    assert sha(Path(row['Path']))==row['Hash'].lower()
report=json.loads((ART/'pass2-final-benchmark.json').read_text())
assert benchmark.workloads()==report['queries']
archive=Path(report['archive'])
assert sum(1 for _ in archive.open(encoding='utf-8'))==30000
answers=[log_archive.search_logs(archive,**query) for query in report['queries']]
digest=hashlib.sha256(json.dumps(answers,sort_keys=True).encode()).hexdigest()
assert all(row['answer_sha256']==digest and row['all_answers_equal'] for row in report['rounds'])
assert report['all_timed_answers_equal'] and report['target_met']
for arm in ('baseline','candidate'):
    assert sum(row[arm+'_seconds'] for row in report['rounds'])==report[arm+'_seconds']
assert subprocess.check_output(['git','status','--porcelain=v1'],text=True).strip()=='?? caller-note.txt'
print(json.dumps({'status':'passed','source_sha256':manifest['sha256'],'candidate_and_review_snapshot_match':True,
 'preserved_files':6,'archive_records':30000,'fresh_untimed_benchmark_query_answers':len(answers),
 'fresh_answer_sha256':digest,'matches_both_recorded_rounds':True,
 'ratio':report['baseline_seconds']/report['candidate_seconds'], 'source_unchanged':True},indent=2))
