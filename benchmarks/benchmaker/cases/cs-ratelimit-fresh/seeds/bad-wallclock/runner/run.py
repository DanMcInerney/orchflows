"""Real-clock runner: replays the timelines against wall-clock time.

The limiter reads time.monotonic and every scripted advance is a real
time.sleep, so a full sweep endures every traced second.
"""
import importlib.util
import json
import time
from pathlib import Path


def load_limiter(impl_dir):
    path = Path(impl_dir) / "tokenbucket.py"
    spec = importlib.util.spec_from_file_location("tokenbucket_under_test", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TokenBucket


def run_case(token_bucket_cls, case):
    """Return None on success, or a one-line failure detail."""
    bucket = token_bucket_cls(case["rate"], case["burst"], time.monotonic)
    for op in case["ops"]:
        if op["op"] == "advance":
            time.sleep(op["by"])
        elif op["op"] == "acquire":
            got = bool(bucket.acquire(op["n"]))
            if got != op["expect"]:
                return "acquire(%d) returned %s, expected %s" % (
                    op["n"], got, op["expect"],
                )
        else:
            return "unknown op %r" % (op["op"],)
    return None


def run_all(cases_path, impl_dir):
    """Return a list of (case_id, required, detail) failures."""
    data = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    token_bucket_cls = load_limiter(impl_dir)
    failures = []
    for case in data["cases"]:
        try:
            detail = run_case(token_bucket_cls, case)
        except Exception as exc:
            detail = "raised %r" % (exc,)
        if detail is not None:
            failures.append((case["id"], bool(case.get("required", True)), detail))
    return failures
