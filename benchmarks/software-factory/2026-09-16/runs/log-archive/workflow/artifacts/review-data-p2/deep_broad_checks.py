"""Pass-two independent deep AND broad data ownership and evidence checks."""
import hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path.cwd()
OUT = ROOT.parent / 'artifacts' / 'review-data-p2'
ART = OUT.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
import log_archive as candidate
import baseline_reference as baseline

def walk(value):
    stack = [value]
    signature, containers = [], []
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            containers.append(node)
            signature.append(('dict', tuple(node.keys())))
            stack.extend(reversed(tuple(node.values())))
        elif isinstance(node, list):
            containers.append(node)
            signature.append(('list', len(node)))
            stack.extend(reversed(node))
        else:
            signature.append((type(node).__name__, repr(node)))
    ids = {id(node) for node in containers}
    assert len(ids) == len(containers), 'unexpected aliases within JSON tree'
    return signature, containers, ids

def encoded(depth, kind):
    extra = '{"leaf":[0,{"text":"original","nested":[]},null,true,1.25,"東京"]}'
    side = '[{"a":[],"b":[1,{"c":{}}]},{"a":[],"b":[2,{"c":{}}]}]'
    for index in range(depth):
        if kind == 'dict' or kind == 'mixed' and index % 2:
            extra = '{"left":' + side + ',"next":' + extra + ',"right":' + side + '}'
        else:
            extra = '[' + side + ',' + extra + ',' + side + ']'
    item = dict(id='duplicate', service='api', level='INFO', message='Deep broad', timestamp='0001-01-01T00:00:00.000Z')
    return json.dumps(item)[:-1] + ',"extra":' + extra + '}\n'

results=[]
with tempfile.TemporaryDirectory(dir=OUT, prefix='deep-') as temp:
    path=Path(temp)/'archive.ndjson'
    for depth in (550,800):
        for kind in ('list','dict','mixed'):
            line=encoded(depth,kind)
            path.write_text(line*2,encoding='utf-8')
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            reference=baseline.search_logs(path)
            first=candidate.search_logs(path)
            second=candidate.search_logs(path)
            assert first['total']==second['total']==reference['total']==2
            signature, nodes, ids=walk(first['items'][0])
            assert signature==walk(reference['items'][0])[0]
            for item in first['items'][1:]+second['items']:
                other_signature, _, other_ids=walk(item)
                assert signature==other_signature
                assert ids.isdisjoint(other_ids), 'shared mutable containers across callers or duplicate records'
            for node in nodes:
                if isinstance(node,dict): node['__caller_mutation__']=['changed']
                else: node.append({'__caller_mutation__':'changed'})
            assert signature==walk(first['items'][1])[0]
            for item in second['items']+candidate.search_logs(path)['items']:
                assert signature==walk(item)[0]
            cli=subprocess.run([sys.executable,'-B','log_archive.py','--file',str(path)],capture_output=True,text=True,encoding='utf-8',timeout=20)
            assert cli.returncode==0,cli.stderr
            assert cli.stderr==''
            cli_result=json.loads(cli.stdout)
            assert cli_result['total']==2 and len(cli_result['items'])==2
            assert all(walk(item)[0]==signature for item in cli_result['items'])
            assert hashlib.sha256(path.read_bytes()).hexdigest()==before
            results.append(dict(depth=depth,kind=kind,archive_bytes=path.stat().st_size,mutable_containers_per_item=len(nodes),mutated_containers=len(nodes),api_complete=True,duplicate_and_caller_ownership=True,cli_complete=True,archive_unchanged=True))

manifest=json.loads((ART/'pass2-candidate-manifest.json').read_text(encoding='utf-8'))
actual={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in manifest['files']}
assert actual==manifest['files']
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==manifest['commit']
evidence=json.loads((ART/'pass2-check-evidence.json').read_text(encoding='utf-8'))
for name,digest in evidence['evidence_sha256'].items():
    assert hashlib.sha256((ART/name).read_bytes()).hexdigest()==digest,name
bench=json.loads((ART/'pass2-final-benchmark.json').read_text(encoding='utf-8'))
assert bench['source_sha256']=={name:actual[name] for name in bench['source_sha256']}
assert hashlib.sha256(Path(bench['archive']).read_bytes()).hexdigest()==bench['archive_sha256']
assert bench['all_timed_answers_equal'] and bench['records']==30000 and bench['queries_per_round']==48
assert [row['order'] for row in bench['rounds']]==[['baseline','candidate'],['candidate','baseline']]
for row in bench['rounds']:
    assert row['all_answers_equal']
    for arm in ('baseline','candidate'):
        assert len(row[arm+'_query_seconds'])==48
        assert sum(row[arm+'_query_seconds'])==row[arm+'_seconds']
assert sum(row['baseline_seconds'] for row in bench['rounds'])/sum(row['candidate_seconds'] for row in bench['rounds'])==bench['throughput_ratio']
report=dict(status='passed',runtime=sys.version,commit=manifest['commit'],source_sha256=manifest['sha256'],deep_broad_results=results,manifest_files_verified=len(actual),supplied_evidence_hashes_verified=len(evidence['evidence_sha256']),benchmark_ratio_recomputed=bench['throughput_ratio'],benchmark_answers_equal=96,git_status=subprocess.check_output(['git','status','--porcelain=v1'],text=True))
(OUT/'deep-broad-checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
