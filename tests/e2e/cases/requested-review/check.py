from common import read_json


ANSWERS = (b'42', b'42\n', b'42\r\n')  # The request allows one optional trailing line break.


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
    path = c.stage() / 'answer.txt'
    content = path.read_bytes() if path.is_file() else None
    c.require(content in ANSWERS, 'answer.txt is 42 with at most one trailing line break',
              'stages/target/workspace/answer.txt: ' + repr(content)[:60])
    children, nested, evidence = delegation(c)
    c.require(len(children) >= 1, 'The requested review launched a native child', evidence)
    c.require(not nested, 'Only the coordinator launches agents', evidence)
