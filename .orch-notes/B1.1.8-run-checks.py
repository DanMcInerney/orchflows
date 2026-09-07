import json, pathlib, subprocess, sys, time
root = pathlib.Path.cwd()
command = [sys.executable, 'tools/run_tests.py', '--scope', 'example-workflows/benchmaker,example-workflows/skill-tournament,benchmarks/benchmaker/README.md,benchmarks/benchmaker/benchmark-design.md', '--no-cache', '-j', '4']
start = time.monotonic()
result = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=600)
record = {'dispatch_id':'B1.1.8:d1','assignment_seal':'sha256:bd156c93acced54c7cbd6b6f51df33b1ba2664a21f87112f05d5e9acee33f9bc','by':'B1.1.8','command':command,'timeout_seconds':600,'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-start,'stdout':result.stdout,'stderr':result.stderr}
(root/'.orch-notes/B1.1.8-scoped-checks.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(result.stdout)
print(result.stderr)
print('OBSERVED EXIT',result.returncode)
sys.exit(result.returncode)
