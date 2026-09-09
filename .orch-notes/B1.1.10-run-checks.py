import json,pathlib,subprocess,sys,time
root=pathlib.Path.cwd()
commands=[([sys.executable,'tools/run_tests.py','tests.test_benchmaker_calibration','tests.test_benchmaker_repair','tests.test_benchmaker_landing','tests.test_benchmaker_integration','--no-cache','-j','4'],360),([sys.executable,'tools/validate.py'],180)]
records=[]
for command,timeout in commands:
    started=time.monotonic()
    result=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=timeout)
    row=dict(command=command,timeout_seconds=timeout,exit_code=result.returncode,elapsed_seconds=time.monotonic()-started,stdout=result.stdout,stderr=result.stderr)
    records.append(row)
    (root/'.orch-notes/B1.1.10-checks.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in row.items() if k not in ('stdout','stderr')}),flush=True)
    print(result.stdout,flush=True)
    print(result.stderr,flush=True)
raise SystemExit(max(r['exit_code'] for r in records))
