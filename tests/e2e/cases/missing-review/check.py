def check(c):
    invoice = c.json(c.stage() / 'invoice.json')
    c.require(invoice['total'] == 253, 'Unavailable review blocks repair', 'stages/target/workspace/invoice.json')
    native = c.report['stages'][0]['native']
    c.require(not ({'Agent', 'Task', 'Bash'} & set(native['tools'])), 'Negative-case capability restriction', 'stages/target/native.json')
    for name in ('review.md', 'handoff.md'):
        c.require((c.stage()/name).is_file() and bool((c.stage()/name).read_text().strip()), 'Report blocked work', name)
