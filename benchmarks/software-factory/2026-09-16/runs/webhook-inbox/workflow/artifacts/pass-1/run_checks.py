import hashlib, json, os, pathlib, subprocess, sys, time
root = pathlib.Path.cwd()
evidence = root.parent / 'artifacts' / 'pass-1'
baseline = '30d2cde4c11a1912b47ca5256f6dd2a19419371e'
authored = ['.gitignore', 'inbox_store.py', 'test_inbox.py', 'RELEASE_HANDOFF.md']
subprocess.run(['git', 'add', '-N', '--', *authored], check=True)
files = sorted(set(subprocess.check_output(['git', 'ls-files'], text=True).splitlines()))
def manifest():
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
source = manifest()
identity = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
record = {'baseline': baseline, 'candidate_path': str(root), 'identity_sha256': identity, 'files': source,
          'caller_note_sha256': hashlib.sha256((root / 'caller-note.txt').read_bytes()).hexdigest()}
(evidence / 'candidate-manifest.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
checks = [(['python', '-m', 'unittest', '-v', 'test_smoke'], 'smoke.txt'),
          (['python', '-m', 'unittest', 'discover', '-v'], 'unittest.txt'),
          (['python', '-m', 'py_compile', 'inbox.py'], 'compile.txt'),
          (['python', 'inbox.py', '--help'], 'cli-help.txt'),
          (['git', 'diff', '--check'], 'diff-check.txt')]
results = []
for command, name in checks:
    started = time.monotonic()
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (evidence / name).write_bytes(completed.stdout)
    result = {'command': command, 'exit_code': completed.returncode, 'seconds': round(time.monotonic()-started, 3),
              'raw_output': name, 'candidate_sha256': identity}
    results.append(result)
    print(json.dumps(result), flush=True)
    if completed.returncode:
        print(completed.stdout.decode(errors='replace'), flush=True)
patch_bytes = subprocess.check_output(['git', 'diff', '--binary', '--no-ext-diff', '--', *files])
patch_path = evidence / 'candidate.patch'
patch_path.write_bytes(patch_bytes)
index = evidence / 'baseline-check.index'
env = os.environ.copy()
env['GIT_INDEX_FILE'] = str(index)
subprocess.run(['git', 'read-tree', baseline], env=env, check=True)
checked = subprocess.run(['git', 'apply', '--cached', '--check', str(patch_path)], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(evidence / 'patch-check.txt').write_bytes(checked.stdout)
results.append({'command': ['git', 'apply', '--cached', '--check', str(patch_path)],
                'exit_code': checked.returncode, 'baseline_index': baseline, 'raw_output': 'patch-check.txt',
                'candidate_sha256': identity})
assert manifest() == source, 'source changed during checks'
assert record['caller_note_sha256'] == '1688056b517941c9189dc5c3d646e967d90f2d26dfc3532eb5764c755a80cd15'
(evidence / 'checks.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
print('CANDIDATE_SHA256=' + identity)
print('PATCH_SHA256=' + hashlib.sha256(patch_bytes).hexdigest())
print('PATCH_CHECK=' + str(checked.returncode))
sys.exit(any(result['exit_code'] for result in results))
