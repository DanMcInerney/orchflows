"""Deterministic, sequential paired baseline/candidate throughput measurement."""

import argparse
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import platform
import random
import sys
import tempfile
from time import perf_counter

from baseline_reference import search_logs as baseline
from log_archive import search_logs as candidate


def prepare(path, count):
    rng = random.Random(62026)
    start = datetime(2026, 7, 1)
    messages = ["gateway timeout retry", "request ready success", "worker queue retry",
                "database connection ERROR", "user_login accepted", "cache hit ready",
                "Gateway-TIMEOUT upstream", "café request İABC", "ready", ""]
    records = []
    for i in range(count):
        stamp = (start + timedelta(milliseconds=rng.randrange(86400000))).isoformat(timespec="milliseconds") + "Z"
        records.append(dict(id=f"r{i % 29000}", timestamp=stamp,
                            service=rng.choice(["api", "gateway", "worker", "database"]),
                            level=rng.choice(["INFO", "WARN", "ERROR"]), message=rng.choice(messages),
                            extra={"row": i, "tags": ["support", i % 11]}))
    with path.open("w", encoding="utf-8") as stream:
        for item in records:
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")


def queries():
    return [
        {}, {"query": "GATEWAY timeout"}, {"query": "ready"}, {"query": "retry ERROR"},
        {"query": "request", "service": "api"}, {"level": "ERROR"},
        {"query": "user_login", "limit": 17, "offset": 7}, {"query": "gate"},
        {"query": "café İABC"}, {"query": "!!!", "limit": 0},
        {"service": "gateway", "level": "WARN", "limit": 25, "offset": 20},
        {"since": "2026-07-01T08:00:00.000Z", "until": "2026-07-01T16:00:00.000Z"},
        {"query": "ready", "since": "2026-07-01T10:00:00.000Z", "until": "2026-07-01T18:00:00.000Z"},
        {"query": "error", "level": "INFO", "service": "database", "offset": 2},
        {"query": "retry retry", "until": "2026-07-01T12:00:00.000Z"},
        {"query": "cache hit", "limit": 100, "offset": 100},
        {"service": "api", "limit": 0}, {"level": "WARN", "offset": 99999},
        {"since": "2026-07-01T12:00:00.000Z", "until": "2026-07-01T12:00:00.000Z"},
        {"service": "", "query": "ready"}, {"query": "absent_token"},
        {"limit": 250, "offset": 1000}, {"query": "ERROR-timeout"},
        {"query": "request", "service": "worker", "level": "WARN",
         "since": "2026-07-01T06:00:00.000Z", "until": "2026-07-01T22:00:00.000Z"},
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON result file outside source")
    parser.add_argument("--records", type=int, default=30000)
    args = parser.parse_args()
    if args.records < 1:
        parser.error("--records must be positive")
    requests = queries()
    durations = {"baseline": 0.0, "candidate": 0.0}
    rounds = []
    correct = True
    with tempfile.TemporaryDirectory(prefix="log-archive-benchmark-") as directory:
        path = Path(directory) / "logs.ndjson"
        prepare(path, args.records)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        # Preparation and initial warming are intentionally outside timed loops.
        baseline(path)
        candidate(path)
        for order in (("baseline", "candidate"), ("candidate", "baseline")):
            outputs, elapsed = {}, {}
            for name in order:
                search = baseline if name == "baseline" else candidate
                started = perf_counter()
                outputs[name] = [search(path, **request) for request in requests]
                elapsed[name] = perf_counter() - started
                durations[name] += elapsed[name]
            # Check every timed answer after timing, independently of the ratio.
            mismatches = [i for i, (left, right) in enumerate(zip(outputs["baseline"], outputs["candidate"])) if left != right]
            correct = correct and not mismatches
            rounds.append({"order": list(order), "seconds": elapsed, "mismatched_query_indices": mismatches})
    ratio = durations["baseline"] / durations["candidate"]
    result = dict(records=args.records, queries_per_round=len(requests), paired_rounds=rounds,
                  total_seconds=durations, throughput_ratio=ratio, target_ratio=5.0,
                  correctness_passed=correct, performance_passed=ratio >= 5.0,
                  archive_sha256=digest, python=sys.version, platform=platform.platform(),
                  queries=requests, timing="Sequential paired rounds; setup, warmup and answer comparison excluded")
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if correct and ratio >= 5.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
