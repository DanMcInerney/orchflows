import subprocess, sys, json
from pathlib import Path
command = [sys.executable, '-m', 'unittest', '-v', *sys.argv[2:]]
result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=240)
Path('.orch-notes/' + sys.argv[1] + '.log').write_text(result.stdout + result.stderr, encoding='utf-8')
print(json.dumps({'command': command, 'exit_code': result.returncode, 'timeout_seconds':240}))
print((result.stdout + result.stderr)[-8000:])
raise SystemExit(result.returncode)
