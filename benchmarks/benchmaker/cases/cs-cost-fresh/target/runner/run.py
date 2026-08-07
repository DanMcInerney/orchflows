"""Runner: evaluates the selected query set against one engine implementation.

The corpus is supplied by the caller (regenerated deterministically from
the parameters recorded in the case set); the runner never generates it.
"""
import importlib.util
import json
from pathlib import Path


def load_engine(impl_dir):
    path = Path(impl_dir) / "engine.py"
    spec = importlib.util.spec_from_file_location("engine_under_test", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_corpus(corpus_path):
    records = []
    with open(str(corpus_path), "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            ts, level, msg = line.split(" ", 2)
            records.append((int(ts), level, msg))
    return records


def run_all(cases_path, impl_dir, corpus_path):
    """Return a list of (case_id, required, detail) failures."""
    data = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    engine = load_engine(impl_dir)
    records = read_corpus(corpus_path)
    failures = []
    for case in data["cases"]:
        try:
            got = engine.query(records, case["start"], case["end"], case["level"])
        except Exception as exc:  # a crashing engine fails the case
            failures.append((case["id"], bool(case.get("required", True)), "raised %r" % (exc,)))
            continue
        if got != case["expected"]:
            failures.append(
                (
                    case["id"],
                    bool(case.get("required", True)),
                    "query(%d, %d, %s) returned %d, expected %d"
                    % (case["start"], case["end"], case["level"], got, case["expected"]),
                )
            )
    return failures
