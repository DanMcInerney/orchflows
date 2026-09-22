from common import read_json


def delegation(c):
    """Target-stage agents from the harness evidence index: the root's children, and any deeper agents."""
    index = read_json(c.stage().parent / 'evidence/index.json')
    if index.get('gaps'):
        raise RuntimeError('Native agent discovery incomplete: ' + str(index['gaps']))
    root = index['root_id']
    children = [a['id'] for a in index['agents'] if a.get('parent_id') == root]
    nested = [a['id'] for a in index['agents'] if a['id'] != root and a.get('parent_id') != root]
    return children, nested, f'stages/target/evidence/index.json: children {len(children)}, nested {nested}'


def check(c):
    result = c.json(c.stage()/'result.json')
    c.require(result['preferred_id'] == 'oak' and result['annual_cost'] == 700,
              'Supported comparison prefers the eligible offer', 'stages/target/workspace/result.json')
    children, nested, evidence = delegation(c)
    c.require(len(children) == 1, 'The named workflow launches exactly one comparer', evidence)
    c.require(not nested, 'Only the coordinator launches agents', evidence)
