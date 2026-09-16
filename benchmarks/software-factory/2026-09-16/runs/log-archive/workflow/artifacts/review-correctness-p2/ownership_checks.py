"""Independent pass-two deep/broad JSON ownership review; writes no source."""
import json
import sys
import subprocess
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
import log_archive
import baseline_reference

PREFIX = '{"id":"one","service":"api","level":"INFO","message":"ready","timestamp":"2026-01-01T00:00:00.000Z","extra":'
LEAF = '{"leaf":[1,null,true,false,-3.25,"東京",{},[]]}'

def tree(depth, style):
    wrappers = []
    for index in range(depth):
        if style == 'dict' or (style == 'mixed' and index % 2):
            wrappers.append(('{"side":[{},[],{"marker":' + str(index) + '}],"next":', '}'))
        else:
            wrappers.append(('[{"side":[{},[]]},', ',{"tail":[null,true,' + str(index) + ']}]'))
    return ''.join(x for x,y in wrappers) + LEAF + ''.join(y for x,y in reversed(wrappers))

def verify(actual, expected):
    pending = [(actual, expected)]
    containers = []
    while pending:
        left, right = pending.pop()
        assert type(left) is type(right), (type(left), type(right))
        if isinstance(left, dict):
            containers.append(left)
            assert list(left) == list(right)
            pending.extend((left[key], right[key]) for key in left)
        elif isinstance(left, list):
            containers.append(left)
            assert len(left) == len(right)
            pending.extend(zip(left, right))
        else:
            assert left == right, (left, right)
    ids = {id(value) for value in containers}
    assert len(ids) == len(containers), 'unexpected mutable aliases in result'
    return containers, ids

def mutate_all(containers):
    for item in containers:
        if isinstance(item, dict):
            item['reviewer_mutation'] = 'changed'
        else:
            item.append('changed')

rows=[]
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'owned.ndjson'
    cases = [(depth, style, tree(depth, style)) for depth in (100,550,800,950) for style in ('dict','array','mixed')]
    cases.append((0, 'broad', '[' + ','.join(tree(4, 'mixed') for _ in range(300)) + ']'))
    for depth, style, extra in cases:
        line = PREFIX + extra + '}\n'
        path.write_text(line * 2, encoding='utf-8')
        expected = baseline_reference.search_logs(path)
        actual = log_archive.search_logs(path)
        containers, identifiers = verify(actual, expected)
        second = log_archive.search_logs(path)
        _, second_identifiers = verify(second, expected)
        assert identifiers.isdisjoint(second_identifiers), 'calls shared mutable containers'
        mutate_all(containers)
        verify(second, expected)
        verify(log_archive.search_logs(path), expected)
        cli = subprocess.run([sys.executable, '-B', str(ROOT / 'log_archive.py'), '--file', str(path)],
                             capture_output=True, text=True, encoding='utf-8', timeout=15)
        assert cli.returncode == 0 and not cli.stderr, (depth, style, cli.stderr)
        verify(json.loads(cli.stdout), expected)
        rows.append({'depth':depth, 'style':style, 'containers_checked':len(containers), 'cli':'passed'})
    def concurrent_read(_):
        answer = log_archive.search_logs(path)
        containers, _ = verify(answer, expected)
        mutate_all(containers)
        return len(containers)
    with ThreadPoolExecutor(max_workers=8) as pool:
        concurrent_counts = list(pool.map(concurrent_read, range(24)))
    verify(log_archive.search_logs(path), expected)
print(json.dumps({'status':'passed', 'cases': rows, 'concurrent_owned_calls': len(concurrent_counts),
                  'total_containers_checked': sum(row['containers_checked'] for row in rows),
                  'all_complete_trees_equal_baseline': True, 'all_containers_mutated_without_leakage': True}, indent=2))
