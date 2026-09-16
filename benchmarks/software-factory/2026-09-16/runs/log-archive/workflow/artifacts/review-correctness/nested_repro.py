from pathlib import Path
import json
import tempfile
import sys
sys.path.insert(0, str(Path.cwd()))
import log_archive
import baseline_reference
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/'nested.ndjson'
    prefix='{"id":"one","service":"api","level":"INFO","message":"ready","timestamp":"2026-01-01T00:00:00.000Z","extra":'
    for depth in (100, 300, 450, 499, 550, 800):
        path.write_text(prefix+'['*depth+'0'+']'*depth+'}\n', encoding='utf-8')
        row={'depth':depth,'bytes':path.stat().st_size}
        for name,module in [('baseline',baseline_reference),('candidate',log_archive)]:
            try: row[name]=module.search_logs(path)['total']
            except Exception as error: row[name]=f'{type(error).__name__}: {error}'
        print(json.dumps(row))
