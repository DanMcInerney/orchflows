"""Sequential paired throughput measurement on identical deterministic inputs."""

import time

from checks import equal
from oracle import benchmark_queries, benchmark_rows, expected, write_archive


def measure(candidate, baseline, scratch, record):
    rows = benchmark_rows()
    path = scratch / "benchmark.ndjson"
    write_archive(path, rows)
    queries = benchmark_queries()
    answers = [expected(rows, **query) for query in queries]
    # One untimed search warms file pages and any candidate archive preparation.
    warm = dict(query="health", limit=1)
    candidate(path, **warm)
    baseline(path, **warm)
    rounds = []
    correct = True
    for round_number, order in enumerate((("baseline", "candidate"), ("candidate", "baseline")), 1):
        timings = {}
        results = {}
        for label in order:
            search = baseline if label == "baseline" else candidate
            start = time.perf_counter()
            results[label] = [search(path, **query) for query in queries]
            timings[label] = time.perf_counter() - start
        for label in ("baseline", "candidate"):
            def verify(label=label):
                for answer, wanted in zip(results[label], answers):
                    equal(answer, wanted)
            passed = record(f"benchmark_round_{round_number}_{label}_answers", verify)
            correct = correct and passed
        rounds.append(dict(round=round_number, order=list(order), **timings))
    baseline_seconds = sum(item["baseline"] for item in rounds)
    candidate_seconds = sum(item["candidate"] for item in rounds)
    ratio = baseline_seconds / candidate_seconds if candidate_seconds else float("inf")
    return dict(records=len(rows), queries_per_round=len(queries), rounds=rounds,
                baseline_seconds=baseline_seconds, candidate_seconds=candidate_seconds,
                baseline_queries_per_second=2 * len(queries) / baseline_seconds,
                candidate_queries_per_second=2 * len(queries) / candidate_seconds,
                throughput_ratio=ratio, required_ratio=5.0,
                answers_correct=correct, passed=correct and ratio >= 5.0,
                timing_scope="query loops only; one initial search per implementation untimed")
