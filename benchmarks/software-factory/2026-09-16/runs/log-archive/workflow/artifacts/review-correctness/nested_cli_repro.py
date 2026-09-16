from pathlib import Path
import json, subprocess, sys, tempfile
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'nested.ndjson'
    prefix='{"id":"one","service":"api","level":"INFO","message":"ready","timestamp":"2026-01-01T00:00:00.000Z","extra":'
    path.write_text(prefix+'['*550+'0'+']'*550+'}\n', encoding='utf-8')
    result=subprocess.run([sys.executable, '-B', 'log_archive.py', '--file', str(path)], capture_output=True, text=True)
    print(json.dumps({'returncode':result.returncode, 'stdout':result.stdout, 'stderr':result.stderr}, indent=2))
