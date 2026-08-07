#!/usr/bin/env python3
"""Minimal runner for the echo-transform benchmark package."""
import json, subprocess, sys
from pathlib import Path

def main(argv):
    if len(argv) != 2:
        return 2
    root = Path(__file__).resolve().parent.parent
    cases = json.loads((root / 'cases' / 'cases.json').read_text(encoding='utf-8'))
    results = {}
    for case in cases['cases']:
        proc = subprocess.run([sys.executable, '-B', str(Path(argv[1]) / 'echo_transform.py')] + case['argv'],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        got = proc.stdout.decode('utf-8', 'replace').strip()
        if 'expect_exit' in case:
            ok = proc.returncode == case['expect_exit']
        else:
            ok = proc.returncode == 0 and got == case['expect']
        results[case['id']] = {'got': got, 'exit': proc.returncode, 'ok': ok}
    print(json.dumps(results, sort_keys=True))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
