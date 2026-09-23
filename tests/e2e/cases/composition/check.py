from common import children, digest


def check(c):
    w = c.stage()
    c.require(c.json(w/'invoice.json') == {'audience':'internal','title':'Invoice record','total':273,'currency':'USD'}, 'Correct internal invoice', 'invoice.json')
    c.require(c.json(w/'public.json') == {'audience':'public','title':'Invoice summary','total':273,'currency':'USD'}, 'Correct separately scoped public summary', 'public.json')
    c.require(c.json(w/'checks.json') == {'passed':True,'sha256':digest(w/'invoice.json')}, 'Required check matches candidate', 'checks.json')
    for name in ('review.md','handoff.md'):
        c.require((w/name).is_file() and bool((w/name).read_text(encoding='utf-8', errors='replace').strip()),
                  'Return review and delivery evidence', name)
    agents, evidence = children(c.stage().parent)
    c.require(len(agents) >= 2, 'Launch the invoice reviewer and the fresh public-summary maker', evidence)
