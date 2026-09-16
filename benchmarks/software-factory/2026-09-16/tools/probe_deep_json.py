"""Exploratory review-derived probe, separate from the predeclared external score."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DEPTH = 550
API = r'''
import importlib.util,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1]).parent))
spec=importlib.util.spec_from_file_location("probe_subject",sys.argv[1])
module=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=module
spec.loader.exec_module(module)
report={}
try:
    result=module.search_logs(sys.argv[2])
    assert result["total"]==1 and len(result["items"])==1
    leaf=result["items"][0]["extra"]
    for _ in range(550): leaf=leaf[0]
    assert leaf=={"marker":"kept"}
    leaf["marker"]="changed"
    second=module.search_logs(sys.argv[2])["items"][0]["extra"]
    for _ in range(550): second=second[0]
    assert second=={"marker":"kept"}
    report={"passed":True,"deep_payload_preserved":True,"mutation_isolated":True}
except Exception as error:
    report={"passed":False,"error":type(error).__name__+": "+str(error)}
print(json.dumps(report))
'''


def main():
    output = ROOT / "results/supplemental-deep-json"
    output.mkdir(parents=True, exist_ok=False)
    environments = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    subjects = {"reference": ROOT / "evaluation/log-archive/frozen_baseline.py"}
    for mode in ("workflow", "single"):
        result = json.loads((ROOT / "runs/log-archive" / mode / "artifacts/RESULT.json").read_text(encoding="utf-8-sig"))
        subjects[mode] = Path(result["candidate_path"]) / "log_archive.py"
    reports = {}
    with tempfile.TemporaryDirectory(prefix="deep-json-probe-") as temporary:
        archive = Path(temporary) / "input.ndjson"
        body = ('{"id":"one","timestamp":"2026-01-02T03:04:05.006Z",'
                '"service":"api","level":"INFO","message":"deep record","extra":'
                + "[" * DEPTH + '{"marker":"kept"}' + "]" * DEPTH + "}\n")
        archive.write_text(body, encoding="utf-8")
        (output / "input.ndjson").write_text(body, encoding="utf-8")
        for name, subject in subjects.items():
            api = subprocess.run([sys.executable, "-B", "-c", API, str(subject), str(archive)],
                                 cwd=temporary, env=environments, capture_output=True, text=True, timeout=30)
            cli = subprocess.run([sys.executable, "-B", str(subject), "--file", str(archive)],
                                 cwd=temporary, env=environments, capture_output=True, text=True, timeout=30)
            for label, process in (("api", api), ("cli", cli)):
                (output / f"{name}-{label}-stdout.txt").write_text(process.stdout, encoding="utf-8")
                (output / f"{name}-{label}-stderr.txt").write_text(process.stderr, encoding="utf-8")
            try:
                api_result = json.loads(api.stdout)
            except ValueError:
                api_result = {"passed": False, "error": "No parseable API probe report"}
            cli_ok = False
            try:
                value = json.loads(cli.stdout)
                leaf = value["items"][0]["extra"]
                for _ in range(DEPTH):
                    leaf = leaf[0]
                cli_ok = value["total"] == 1 and leaf == {"marker": "kept"}
            except (ValueError, KeyError, IndexError, TypeError):
                pass
            reports[name] = {"subject": str(subject), "api": api_result,
                             "api_exit": api.returncode, "cli_exit": cli.returncode,
                             "cli_passed": cli.returncode == 0 and cli_ok and not cli.stderr}
    result = {"kind": "exploratory, review-derived; excluded from primary score", "depth": DEPTH,
              "criterion": "Preserve a valid nested JSON extra field and independent caller-owned results, plus successful CLI JSON output.",
              "subjects": reports}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
