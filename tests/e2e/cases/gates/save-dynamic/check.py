"""Check public planning results and package delivery without prescribing implementation."""
EXPECTED = {
    'author': {'scheduled_ids': ['urgent', 'normal'], 'deferred_ids': ['unknown'], 'unknown_ids': ['unknown'], 'used_hours': 8},
    'changed': {'scheduled_ids': ['hot', 'tiny'], 'deferred_ids': ['large', 'mystery'], 'unknown_ids': ['mystery'], 'used_hours': 7},
    'empty': {'scheduled_ids': [], 'deferred_ids': ['next', 'unestimated'], 'unknown_ids': ['unestimated'], 'used_hours': 0},
}


def check(c):
    library = c.root / 'generated/personal'
    for name in ('plugin.json', '.claude-plugin/plugin.json', '.codex-plugin/plugin.json',
                 '.kimi-plugin/plugin.json', 'skills/weekly-plan/SKILL.md'):
        c.require((library / name).is_file(), 'Deliver a reusable personal package', str(library / name))
    for stage, expected in EXPECTED.items():
        path = c.stage(stage) / 'plan.json'
        actual = c.json(path)
        c.require(isinstance(actual, dict), 'Plan is a JSON object', str(path))
        if not isinstance(actual, dict):
            continue
        c.require(all(key in actual and actual[key] == value for key, value in expected.items())
                  and type(actual.get('used_hours')) in (int, float),
                  'Allocate capacity in the required order and preserve uncertainty', str(path))
        brief = c.stage(stage) / 'brief.md'
        c.require(brief.is_file() and bool(brief.read_text(encoding='utf-8').strip()),
                  'Deliver a human brief for this input', str(brief))
