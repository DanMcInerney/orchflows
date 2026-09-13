"""Independent final review: read candidate, write only this review's evidence."""
import hashlib, json, statistics
from pathlib import Path
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def paths(d):
    return [p for p in (root/d).rglob('*') if p.is_file() and not any(x in ('node_modules','__pycache__') for x in p.parts) and not p.name.endswith('.blend1')]

candidate=read(root/'evidence/builds/production-candidate.json')
results=[]
source_sets=[]
for key, folder in [('release','dist'),('assistedTest','test-dist')]:
    declared=candidate[key]
    manifest=read(root/declared['manifest'])
    entries=manifest['source']+manifest['built']
    mismatches=[e['path'] for e in entries if not (root/e['path']).is_file() or sha(root/e['path'])!=e['sha256']]
    source=[]
    for d in ('src','scripts','tests','public','assets/source'): source+=paths(d)
    source += [root/p for p in ('index.html','asset-preview.html','package.json','package-lock.json','vite.config.js')]
    source_diff=sorted({p.relative_to(root).as_posix() for p in source}^{e['path'] for e in manifest['source']})
    built_diff=sorted({p.relative_to(root).as_posix() for p in paths(folder)}^{e['path'] for e in manifest['built']})
    source_hash=hashlib.sha256(json.dumps(manifest['source'],separators=(',',':')).encode()).hexdigest()[:12]
    js=''.join(p.read_text(encoding='utf-8') for p in paths(folder) if p.suffix=='.js')
    audit={'adapter': '__gameTest' in js, 'fixtures': 'boss-danger' in js}
    assert sha(root/declared['manifest'])==declared['manifestSha256']
    assert manifest['id'].endswith(source_hash)
    assert not mismatches and not source_diff and not built_diff
    assert all(v==(folder=='test-dist') for v in audit.values())
    source_sets.append(manifest['source'])
    results.append({'build':manifest['id'],'sourceFiles':len(manifest['source']),'builtFiles':len(manifest['built']),'mismatches':mismatches,'sourcePathDifference':source_diff,'builtPathDifference':built_diff,'diagnosticAudit':audit,'manifestSha256':sha(root/declared['manifest'])})
assert source_sets[0]==source_sets[1]
docs=[e['path'] for e in candidate['handoffDocuments'] if sha(root/e['path'])!=e['sha256']]
assert not docs
assert sha(root/candidate['assets']['manifest'])==candidate['assets']['sha256']
result={'checkedAt':datetime.now(timezone.utc).isoformat(),'result':'PASS','method':'Independent read-only SHA-256 and full path-set verification; no candidate rebuild or mutation','builds':results,'sourceIdentical':True,'handoffDocumentCount':len(candidate['handoffDocuments']),'handoffMismatches':docs,'assets':candidate['assets']}
(out/'integrity.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
