def check(c):
    library = c.root / 'generated/personal'
    for relative in ('plugin.json', '.claude-plugin/plugin.json', '.codex-plugin/plugin.json',
                     '.kimi-plugin/plugin.json', 'skills/summarize-offers/SKILL.md', 'skills/decision-brief/SKILL.md'):
        c.require((library/relative).is_file(), 'Deliver a complete reusable library', 'generated/personal/'+relative)
    c.require(bool(list((library/'guidance').glob('*.md'))), 'Keep reusable taste in guidance', 'generated/personal/guidance')
    decision = c.json(c.stage('decision')/'brief.json')
    c.require(decision['recommended_id'] == 'blue' and decision['annual_cost'] == 620,
              'Fresh input selects the supported eligible supplier', 'stages/decision/workspace/brief.json')
    offers = {o['id']: o for o in c.json(c.stage('component')/'summary.json')['offers']}
    c.require(offers['green']['annual_cost'] == 730 and offers['green']['eligible'] is True,
              'Standalone component works on unfamiliar input', 'stages/component/workspace/summary.json')
    c.require(offers['unknown']['annual_cost'] is None and offers['unknown']['eligible'] is None,
              'Missing fee remains unknown', 'stages/component/workspace/summary.json')
