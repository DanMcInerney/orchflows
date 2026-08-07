#!/usr/bin/env python3
"""Case-author sanity oracle for candidate-ranking. NOT the benchmark.

Usage (from this case directory):

    uv run --no-project python probe.py [IMPLEMENTATION]

IMPLEMENTATION is a file or a directory holding ``rank.py``; it may
also arrive in the ``CASE_IMPL`` environment variable, and defaults to
``target/rank.py``. Paths resolve against the caller's directory and
then against this file's own directory, so the probe runs from the
case directory or from the repository root. Exit 0 means the
implementation satisfies every checked clause of ``evidence/spec.md``;
exit 1 names the clauses it violates.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

IMPL_NAME = "rank.py"
CASE_DIR = os.path.dirname(os.path.abspath(__file__))

WEIGHTS_MAIN = {"weights": {"r1": 1, "c1": 3, "c2": 2, "c3": 2}, "required": ["r1"]}
WEIGHTS_FLIP = {"weights": {"c1": 3, "c2": 2, "c3": 2}, "required": []}


def resolve_impl():
    raw = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL")
    if not raw:
        raw = os.path.join("target", IMPL_NAME)
    for candidate in (raw, os.path.join(CASE_DIR, raw)):
        if os.path.isdir(candidate):
            candidate = os.path.join(candidate, IMPL_NAME)
        if os.path.isfile(candidate):
            return candidate
    return None


def record(name, passes, extra=None):
    cases = set(WEIGHTS_MAIN["weights"]) | set(WEIGHTS_FLIP["weights"])
    results = {case: ("pass" if case in passes else "fail") for case in sorted(cases)}
    data = {"candidate": name, "results": results}
    if extra:
        data.update(extra)
    return data


def expected_bytes(lines):
    return "".join(line + "\n" for line in lines).encode("utf-8")


# (name, weights, records-in-argv-order, expected stdout lines)
RANKING_CHECKS = [
    (
        "total-order-distinct-scores",
        WEIGHTS_MAIN,
        [
            record("alpha", {"r1", "c1", "c2", "c3"}),
            record("beta", {"r1", "c1"}),
            record("gamma", {"r1", "c3"}),
        ],
        [
            "rank 1: alpha score 8",
            "rank 2: beta score 4",
            "rank 3: gamma score 3",
            "margin 1/2: 4",
            "margin 2/3: 1",
        ],
    ),
    (
        "explicit-tie-shared-rank-and-skip",
        WEIGHTS_MAIN,
        [
            record("alpha", {"r1", "c1", "c2", "c3"}),
            record("beta", {"r1", "c2"}),
            record("gamma", {"r1", "c3"}),
            record("delta", {"r1"}),
        ],
        [
            "rank 1: alpha score 8",
            "rank 2: beta, gamma score 3 tie",
            "rank 4: delta score 1",
            "margin 1/2: 5",
            "margin 2/4: 2",
        ],
    ),
    (
        "arrival-order-invariance",
        WEIGHTS_MAIN,
        list(
            reversed(
                [
                    record("alpha", {"r1", "c1", "c2", "c3"}),
                    record("beta", {"r1", "c2"}),
                    record("gamma", {"r1", "c3"}),
                    record("delta", {"r1"}),
                ]
            )
        ),
        [
            "rank 1: alpha score 8",
            "rank 2: beta, gamma score 3 tie",
            "rank 4: delta score 1",
            "margin 1/2: 5",
            "margin 2/4: 2",
        ],
    ),
    (
        "required-failure-excluded-not-ranked",
        WEIGHTS_MAIN,
        [
            record("omega", {"c1", "c2", "c3"}),
            record("alpha", {"r1", "c1"}),
            record("beta", {"r1", "c2"}),
        ],
        [
            "rank 1: alpha score 4",
            "rank 2: beta score 3",
            "margin 1/2: 1",
            "excluded: omega required-fail: r1",
        ],
    ),
    (
        "all-excluded-still-lawful",
        WEIGHTS_MAIN,
        [record("omega", {"c1", "c2", "c3"})],
        ["excluded: omega required-fail: r1"],
    ),
    (
        "self-reported-score-ignored",
        WEIGHTS_MAIN,
        [
            record("alpha", {"r1", "c1"}),
            record("beta", {"r1", "c2"}, {"self_score": 999}),
        ],
        [
            "rank 1: alpha score 4",
            "rank 2: beta score 3",
            "margin 1/2: 1",
        ],
    ),
    (
        "aggregation-fixed-before-candidates",
        WEIGHTS_FLIP,
        [
            record("alpha", {"c1"}),
            record("beta", {"c2", "c3"}),
            record("gamma", {"c2", "c3"}),
        ],
        [
            "rank 1: beta, gamma score 4 tie",
            "rank 3: alpha score 3",
            "margin 1/3: 1",
        ],
    ),
    (
        "single-candidate-no-margins",
        WEIGHTS_MAIN,
        [record("solo", {"r1"})],
        ["rank 1: solo score 1"],
    ),
    (
        "absent-case-id-counts-as-fail",
        WEIGHTS_MAIN,
        [
            {"candidate": "sparse", "results": {"r1": "pass"}},
            record("beta", {"r1", "c2"}),
        ],
        [
            "rank 1: beta score 3",
            "rank 2: sparse score 1",
            "margin 1/2: 2",
        ],
    ),
]


def run(impl, argv):
    proc = subprocess.run(
        [sys.executable, impl] + list(argv),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.returncode, proc.stdout


def write_json(directory, name, payload):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle)
    return path


def main():
    impl = resolve_impl()
    if impl is None:
        sys.stderr.write(
            "probe: no such implementation: %s\n"
            % (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CASE_IMPL"))
        )
        return 2

    failures = []
    workdir = tempfile.mkdtemp(prefix="candidate-ranking-probe-")
    try:
        for index, (name, weights, records, expected) in enumerate(RANKING_CHECKS):
            weights_path = write_json(workdir, "w%d.json" % index, weights)
            record_paths = [
                write_json(workdir, "r%d-%s.json" % (index, item["candidate"]), item)
                for item in records
            ]
            want = expected_bytes(expected)
            try:
                code, out = run(impl, ["--weights", weights_path] + record_paths)
            except Exception as exc:  # a crashing implementation is a failure
                failures.append("%s: raised %r" % (name, exc))
                continue
            if code != 0:
                failures.append("%s: exit %d, want 0" % (name, code))
            if out != want:
                failures.append("%s: stdout %r, want %r" % (name, out, want))

        weights_path = write_json(workdir, "w-usage.json", WEIGHTS_MAIN)
        record_path = write_json(workdir, "r-usage.json", record("alpha", {"r1"}))
        broken_path = os.path.join(workdir, "broken.json")
        with open(broken_path, "w", encoding="utf-8") as handle:
            handle.write("not json")
        zero_weight = write_json(
            workdir, "w-zero.json", {"weights": {"c1": 0}, "required": []}
        )
        orphan_required = write_json(
            workdir, "w-orphan.json", {"weights": {"c1": 1}, "required": ["zz"]}
        )
        nonstring_required = write_json(
            workdir, "w-nonstring.json", {"weights": {"c1": 1}, "required": [["x"]]}
        )
        bad_value = write_json(
            workdir, "r-badvalue.json", {"candidate": "x", "results": {"c1": "PASS"}}
        )
        usage_checks = [
            ("usage-no-records", ["--weights", weights_path]),
            ("usage-missing-weights", [record_path]),
            ("usage-duplicate-weights-flag", ["--weights", weights_path, "--weights", weights_path, record_path]),
            ("usage-no-equals-form", ["--weights=%s" % weights_path, record_path]),
            ("usage-unreadable-record", ["--weights", weights_path, os.path.join(workdir, "absent.json")]),
            ("usage-invalid-json-record", ["--weights", weights_path, broken_path]),
            ("usage-duplicate-candidate", ["--weights", weights_path, record_path, record_path]),
            ("usage-zero-weight", ["--weights", zero_weight, record_path]),
            ("usage-required-not-in-weights", ["--weights", orphan_required, record_path]),
            ("usage-required-not-a-string", ["--weights", nonstring_required, record_path]),
            ("usage-bad-result-value", ["--weights", weights_path, bad_value]),
        ]
        for name, argv in usage_checks:
            try:
                code, out = run(impl, argv)
            except Exception as exc:
                failures.append("%s: raised %r" % (name, exc))
                continue
            if code != 2:
                failures.append("%s: exit %d, want 2" % (name, code))
            if out != b"":
                failures.append("%s: stdout %r, want empty" % (name, out))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    if failures:
        sys.stderr.write("probe FAIL (%s): %d violation(s)\n" % (impl, len(failures)))
        for failure in failures:
            sys.stderr.write("  - %s\n" % failure)
        return 1
    sys.stdout.write(
        "probe PASS (%s): %d checks\n" % (impl, len(RANKING_CHECKS) + len(usage_checks))
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
