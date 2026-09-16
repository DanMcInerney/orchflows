"""Independent data-lens checks. Run from frozen review-data-p2 snapshot with python -B."""
import concurrent.futures as cf
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path.cwd()
ARTIFACTS = ROOT.parent / "artifacts"
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
import log_archive as subject

report = {"snapshot": str(ROOT), "runtime": sys.version, "checks": []}
def record(ident, timestamp="2026-01-01T00:00:00.000Z", **extra):
    return dict(id=str(ident), timestamp=timestamp, service="api", level="INFO",
                message="Gateway TIMEOUT — normal_1", **extra)
def write(path, records):
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
                    encoding="utf-8")
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def check(name, fn):
    start = time.monotonic()
    detail = fn()
    report["checks"].append(dict(name=name, status="passed", seconds=time.monotonic()-start, detail=detail))

manifest = json.loads((ARTIFACTS / "pass2-candidate-manifest.json").read_text())

def all_identity():
    actual = {name: sha(ROOT/name) for name in manifest["files"]}
    assert actual == manifest["files"]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    assert commit == manifest["commit"]
    return dict(commit=commit, manifest_files=len(actual), manifest_sha256=manifest["sha256"])
check("frozen_snapshot_identity", all_identity)

with tempfile.TemporaryDirectory(dir=ARTIFACTS / "review-data-p2", prefix="fixtures-") as td:
    directory = Path(td)
    path = directory / "schema.ndjson"

    def schema():
        valid = [
            record("late", "9999-12-31T23:59:59.999Z", extra={"text":"東京", "array":[None, True, 1.25, {"values":[1,2,3]}]}),
            record("leap", "2000-02-29T23:59:59.999Z"),
            record("same", "0001-01-01T00:00:00.000Z", extra={"order":1}),
            record("same", "0001-01-01T00:00:00.000Z", extra={"order":2}),
            record("same", "0001-01-01T00:00:00.000Z", extra={"order":1}),
        ]
        invalid = ["", " \t", "{", "null", "[]", "true", "42", json.dumps({})]
        for stamp in ["0000-01-01T00:00:00.000Z", "1900-02-29T00:00:00.000Z", "2100-02-29T00:00:00.000Z",
                      "2026-04-31T00:00:00.000Z","2026-01-01T24:00:00.000Z","2026-01-01T00:00:60.000Z",
                      "2026-01-01T00:00:00.01Z","2026-01-01T00:00:00.0000Z","2026-01-01T00:00:00.000z"]:
            invalid.append(json.dumps(record("bad", stamp)))
        for field in ["id", "service", "level", "message", "timestamp"]:
            item = record("bad")
            del item[field]
            invalid.append(json.dumps(item))
            for value in [None, True, 1, [], {}]:
                item = record("bad")
                item[field] = value
                invalid.append(json.dumps(item))
        for field in ["id", "service", "level"]:
            item = record("bad")
            item[field] = ""
            invalid.append(json.dumps(item))
        lines = invalid[:20] + [json.dumps(x, ensure_ascii=False) for x in valid] + invalid[20:]
        path.write_text("\n".join(lines), encoding="utf-8")
        before = sha(path)
        ordered = sorted(valid, key=lambda r:r["timestamp"])
        result = subject.search_logs(path, limit=10**30)
        assert result == dict(total=5, items=ordered)
        result["items"][4]["extra"]["array"][3]["values"][0] = "changed"
        result["items"][0]["extra"]["order"] = "changed"
        result["items"].pop()
        result["total"] = -1
        assert subject.search_logs(path, limit=100) == dict(total=5, items=ordered)
        assert subject.search_logs(path, since="0001-01-01T00:00:00.000Z",
                                   until="2000-02-29T23:59:59.999Z") == dict(total=3, items=ordered[:3])
        assert subject.search_logs(path, since="9999-12-31T23:59:59.999Z")["items"] == [valid[0]]
        assert sha(path) == before
        return dict(valid_records=len(valid), invalid_lines=len(invalid), durable_archive_bytes_unchanged=True)
    check("schema_calendar_ties_duplicates_extras_and_ownership", schema)

    def queries():
        rng = random.Random(5277)
        rows = []
        base = datetime(2026,1,1)
        for index in range(500):
            row = record(index%17, (base+timedelta(milliseconds=rng.randrange(20))).isoformat(timespec="milliseconds")+"Z",
                         nested={"a":[index, {"b":[None,True,"é"]}]})
            row.update(message=rng.choice(["ERROR-timeOUT gateway","éerroré timeout ß","ready","error_timeOut","",
                                          "İERRK TIMEOUT","a.b/C3_4", "東京 gateway"]),
                       service=rng.choice(["api","API","worker"]), level=rng.choice(["INFO","info","ERROR"]))
            rows.append(row)
        write(path, rows)
        before = sha(path)
        sorted_rows = sorted(rows, key=lambda row:row["timestamp"])
        alphabet = re.compile("[A-Za-z0-9_]+")
        for index in range(350):
            stamps = sorted(rng.sample([r["timestamp"] for r in rows], 2))
            args = dict(query=rng.choice(["","ERROR timeout","error error","err","—東京","gateway!","C3_4","İERRK"]),
                        service=rng.choice([None,"api","API",""]), level=rng.choice([None,"INFO","info","ERROR",""]),
                        since=rng.choice([None,stamps[0]]), until=rng.choice([None,stamps[1]]),
                        offset=rng.choice([0,1,17,501,10**30]), limit=rng.choice([0,1,17,501,10**30]))
            tokens = {x.lower() for x in alphabet.findall(args["query"])}
            matched = [r for r in sorted_rows if
                       (args["service"] is None or r["service"]==args["service"]) and
                       (args["level"] is None or r["level"]==args["level"]) and
                       (args["since"] is None or r["timestamp"]>=args["since"]) and
                       (args["until"] is None or r["timestamp"]<args["until"]) and
                       tokens.issubset({x.lower() for x in alphabet.findall(r["message"])})]
            assert subject.search_logs(path, **args) == dict(total=len(matched),
                items=matched[args["offset"]:args["offset"]+args["limit"]]), (index,args)
        assert sha(path) == before
        return dict(records=500, independent_oracle_queries=350, durable_archive_bytes_unchanged=True)
    check("independent_schema_query_oracle", queries)

    def changes():
        paths = [directory / f"cache-{i}.ndjson" for i in range(20)]
        for i,p in enumerate(paths):
            write(p, [record(i)])
        for order in [list(range(20)),list(reversed(range(20))),list(range(20))]:
            for i in order:
                assert subject.search_logs(paths[i])["items"]==[record(i)]
        for i,p in enumerate(paths):
            original=sha(p)
            subject.search_logs(p)
            assert sha(p)==original
            with p.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record(f"append{i}"))+"\n")
            assert subject.search_logs(p)["total"]==2
            p.write_text("",encoding="utf-8")
            assert subject.search_logs(p)==dict(total=0,items=[])
            write(p,[record("old")])
            assert subject.search_logs(p)["items"]==[record("old")]
            stat=p.stat()
            replacement=directory / f"replacement-{i}"
            write(replacement,[record("new")])
            assert replacement.stat().st_size==stat.st_size
            os.utime(replacement,ns=(stat.st_atime_ns,stat.st_mtime_ns))
            os.replace(replacement,p)
            assert p.stat().st_mtime_ns==stat.st_mtime_ns
            assert subject.search_logs(p)["items"]==[record("new")]
        return dict(distinct_paths=20, interleaved_reads=60, append_truncate_same_size_preserved_mtime_replacements=20)
    check("path_isolation_eviction_and_completed_changes", changes)

    def concurrency():
        race=directory/"race.ndjson"
        versions=[[record(f"{v}{i:04}", extra={"generation":[v,i]}) for i in range(150)] for v in ["a","b"]]
        expected=[dict(total=150,items=rows) for rows in versions]
        write(race,versions[0])
        initial=race.stat()
        barrier=threading.Barrier(9)
        reads=[0]*8
        writes=[0]
        def reader(which):
            barrier.wait(timeout=10)
            for n in range(300):
                result=subject.search_logs(race,limit=1000)
                assert result in expected, (which,n,result)
                result["items"][0]["extra"]["generation"].append("caller mutation")
                reads[which]+=1
        def writer():
            barrier.wait(timeout=10)
            for index in range(150):
                replacement=directory/f"race-new-{index}"
                write(replacement,versions[index%2])
                os.utime(replacement,ns=(initial.st_atime_ns,initial.st_mtime_ns))
                for attempt in range(1000):
                    try:
                        os.replace(replacement,race)
                        break
                    except PermissionError:
                        time.sleep(.001)
                else:
                    raise AssertionError("Could not complete atomic replacement")
                assert subject.search_logs(race,limit=1000)==expected[index%2]
                writes[0]+=1
        with cf.ThreadPoolExecutor(max_workers=9) as pool:
            futures=[pool.submit(reader,i) for i in range(8)]+[pool.submit(writer)]
            for f in futures:
                f.result(timeout=60)
        before=sha(race)
        assert subject.search_logs(race,limit=1000)==expected[149%2]
        assert sha(race)==before
        return dict(concurrent_reads=sum(reads), complete_atomic_replacements=writes[0],
                    completed_write_freshness_checks=writes[0], returned_nested_mutations=sum(reads))
    check("concurrent_complete_versions_and_owned_results", concurrency)

check("source_unchanged_after_checks", all_identity)
report["status"]="passed"
report_path=ARTIFACTS/"review-data-p2"/"data-checks.json"
report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))



