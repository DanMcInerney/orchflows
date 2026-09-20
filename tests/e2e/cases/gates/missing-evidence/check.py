"""Structural decision checks; source support is assessed independently."""


def check(c):
    path = c.stage() / 'decision.json'
    value = c.json(path)
    c.require(isinstance(value, dict), 'Decision is a JSON object', str(path))
    if not isinstance(value, dict):
        return
    c.require(value.get('status') == 'insufficient_evidence' and
              'recommended_id' in value and value['recommended_id'] is None,
              'Do not recommend an unproven eligible supplier', str(path))
    gaps = value.get('gaps')
    c.require(isinstance(gaps, list) and bool(gaps) and
              all(isinstance(gap, str) and bool(gap.strip()) for gap in gaps),
              'State missing decision evidence explicitly', str(path))
    report = c.stage() / 'decision.md'
    c.require(report.is_file() and bool(report.read_text(encoding='utf-8').strip()),
              'Deliver an evidence-linked decision report', str(report))
