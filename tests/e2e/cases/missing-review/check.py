def check(c):
    invoice = c.json(c.stage() / 'invoice.json')
    c.require(invoice['total'] == 253, 'Unavailable review blocks repair', 'stages/target/workspace/invoice.json')
    native = c.report['stages'][0]['native']
    if native.get('tools') is None:  # Codex lists no tools; its launch profile carries the restriction
        launch = c.json(c.stage().parent / 'codex-launch.json')
        c.require(launch.get('profile') == 'no-review', 'Negative-case capability restriction', 'stages/target/codex-launch.json')
        index = c.json(c.stage().parent / 'evidence' / 'index.json')
        c.require(len(index['agents']) == 1, 'No delegated agents under the restriction', 'stages/target/evidence/index.json')
    else:
        c.require(not ({'Agent', 'Task', 'Bash'} & set(native['tools'])), 'Negative-case capability restriction', 'stages/target/native.json')
    for name in ('review.md', 'handoff.md'):
        c.require((c.stage()/name).is_file() and bool((c.stage()/name).read_text().strip()), 'Report blocked work', name)
