"""Reproducible, sequential paired throughput measurement; standard library only."""

import argparse
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

import baseline_reference
import log_archive


RECORDS = 30_000


def prepare_archive(path):
    epoch = datetime(2026, 1, 1)
    messages = ["Gateway ERROR-timeout retry", "worker ready job_completed", "cache hit response ok",
                "gateway ready response", "worker ERROR timeout retry", "éerroré payment timeout",
                "audit login success", "disk warning queue_depth", "東京 ping pong", ""]
    with path.open("w", encoding="utf-8", newline="\n") as archive:
        for source_position in range(RECORDS):
            # A permutation gives out-of-order timestamps, with three-way ties.
            index = source_position * 15427 % RECORDS
            stamp = (epoch + timedelta(milliseconds=(index // 3) * 1000)).isoformat(timespec="milliseconds") + "Z"
            item = dict(id=f"r{index % 29791}", timestamp=stamp,
                        service=["gateway", "worker", "cache", "billing"][index % 4],
                        level=["INFO", "WARN", "ERROR"][index % 3],
                        message=messages[index % len(messages)] + f" shard_{index % 17}",
                        extra={"attempt": index % 7, "tags": ["support", {"region": index % 5}]})
            archive.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")


def workloads():
    base = [
        {}, {"query": "error timeout"}, {"query": "ERROR error"}, {"query": "gateway"},
        {"query": "error", "service": "gateway", "level": "ERROR"},
        {"query": "shard_3", "service": "worker"}, {"query": "—東京!?"},
        {"query": "missing_token"}, {"query": "err"}, {"service": "billing"},
        {"level": "WARN"}, {"service": "", "level": "INFO"},
        {"since": "2026-01-01T00:30:00.000Z", "until": "2026-01-01T01:30:00.000Z"},
        {"query": "ready", "since": "2026-01-01T01:00:00.000Z", "level": "INFO"},
        {"until": "2026-01-01T00:00:00.001Z"},
        {"since": "2026-01-01T00:00:00.000Z", "until": "2026-01-01T00:00:00.000Z"},
    ]
    queries = []
    for group in range(3):
        for index, query in enumerate(base):
            queries.append({**query, "limit": [0, 10, 50, 150][(index + group) % 4],
                            "offset": [0, 2, 25, 1500][(index + 2 * group) % 4]})
    return queries


def run_queries(function, path, queries):
    answers, seconds = [], []
    for query in queries:
        started = perf_counter()
        answer = function(path, **query)
        elapsed = perf_counter() - started
        answers.append(answer)
        seconds.append(elapsed)
    return answers, seconds


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="Scratch NDJSON path outside source")
    parser.add_argument("--output", type=Path, required=True, help="JSON measurement report outside source")
    args = parser.parse_args()
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    prepare_archive(args.archive)
    queries = workloads()
    baseline_warm = baseline_reference.search_logs(args.archive)
    candidate_warm = log_archive.search_logs(args.archive)
    if baseline_warm != candidate_warm:
        raise AssertionError("initial warmed answers differ")
    functions = {"baseline": baseline_reference.search_logs, "candidate": log_archive.search_logs}
    rounds = []
    for number, order in enumerate((("baseline", "candidate"), ("candidate", "baseline")), 1):
        measurements = {}
        for name in order:
            answers, seconds = run_queries(functions[name], args.archive, queries)
            measurements[name] = {"answers": answers, "seconds": seconds}
        for query_index, (expected, actual) in enumerate(zip(measurements["baseline"]["answers"],
                                                             measurements["candidate"]["answers"])):
            if expected != actual:
                raise AssertionError(f"round {number}, query {query_index} differs: {queries[query_index]}")
        answer_digest = hashlib.sha256(json.dumps(measurements["baseline"]["answers"],
                                                  sort_keys=True).encode()).hexdigest()
        rounds.append({"round": number, "order": list(order), "all_answers_equal": True,
                       "answer_sha256": answer_digest,
                       **{name + "_query_seconds": measurements[name]["seconds"] for name in order},
                       **{name + "_seconds": sum(measurements[name]["seconds"]) for name in order}})
    baseline_seconds = sum(row["baseline_seconds"] for row in rounds)
    candidate_seconds = sum(row["candidate_seconds"] for row in rounds)
    ratio = baseline_seconds / candidate_seconds
    root = Path(__file__).resolve().parent
    report = {"python": sys.version, "platform": platform.platform(), "records": RECORDS,
              "queries_per_round": len(queries), "queries": queries,
              "archive": str(args.archive.resolve()), "archive_sha256": sha256(args.archive),
              "source_sha256": {name: sha256(root / name)
                                for name in ("baseline_reference.py", "log_archive.py", "benchmark.py")},
              "warming": "Both arms searched the same complete archive once before timing.",
              "timing": "Sequential arms; only search calls timed; preparation, warmup, equality checks and reporting excluded.",
              "rounds": rounds, "all_timed_answers_equal": True,
              "baseline_seconds": baseline_seconds, "candidate_seconds": candidate_seconds,
              "throughput_ratio": ratio, "target_ratio": 5.0, "target_met": ratio >= 5.0}
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
