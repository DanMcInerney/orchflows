def check(c):
    w = c.stage().resolve()
    summary = c.json(w/'trial-summary.json')
    outputs = {}
    for name in ('fixture_input','rewritten_notes','captured_email','captured_invite'):
        path = (w / summary['paths'][name]).resolve()
        c.require(path.is_relative_to(w) and path.is_file(), 'Synthetic artifact exists in trial workspace', str(path))
        if not path.is_relative_to(w) or not path.is_file():
            continue
        outputs[name] = path
        text = path.read_text(encoding='utf-8')
        c.require(bool(text.strip()) and 'ORIGINAL_MEETING_7F2A' not in text, 'Use realistic synthetic data', str(path))
    c.require(outputs.get('fixture_input') == outputs.get('rewritten_notes') and 'fixture_input' in outputs, 'Actually overwrite synthetic input in place', 'trial-summary.json')
    c.require((w/'trial-report.md').is_file(), 'Report simulated effects and gaps', 'trial-report.md')
