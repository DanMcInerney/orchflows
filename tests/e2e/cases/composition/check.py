from common import digest, read_json


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
    w = c.stage()
    c.require(c.json(w/'invoice.json') == {'audience':'internal','title':'Invoice record','total':273,'currency':'USD'}, 'Correct internal invoice', 'invoice.json')
    c.require(c.json(w/'public.json') == {'audience':'public','title':'Invoice summary','total':273,'currency':'USD'}, 'Correct separately scoped public summary', 'public.json')
    c.require(c.json(w/'checks.json') == {'passed':True,'sha256':digest(w/'invoice.json')}, 'Required check matches candidate', 'checks.json')
    for name in ('review.md','handoff.md'):
        c.require((w/name).is_file() and bool((w/name).read_text(encoding='utf-8', errors='replace').strip()),
                  'Return review and delivery evidence', name)
    children, nested, evidence = delegation(c)
    c.require(len(children) >= 2, 'Launch the invoice reviewer and the fresh public-summary maker', evidence)
    c.require(not nested, 'Only the coordinator launches agents', evidence)
