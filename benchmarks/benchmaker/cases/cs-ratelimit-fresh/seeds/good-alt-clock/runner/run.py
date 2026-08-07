"""Alternative scripted-clock runner: closure-injected clock, same laws.

A lawfully different harness: the injected clock is a closure over a
mutable cell rather than a callable object. Time is still owned by the
oracle; no real sleeps anywhere.
"""
import importlib.util
import json
from pathlib import Path


def make_clock():
    cell = [0.0]

    def read():
        return cell[0]

    def advance(by):
        cell[0] += by

    return read, advance


def load_limiter(impl_dir):
    path = Path(impl_dir) / "tokenbucket.py"
    spec = importlib.util.spec_from_file_location("tokenbucket_under_test", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TokenBucket


def run_case(token_bucket_cls, case):
    """Return None on success, or a one-line failure detail."""
    read, advance = make_clock()
    bucket = token_bucket_cls(case["rate"], case["burst"], read)
    for op in case["ops"]:
        kind = op["op"]
        if kind == "advance":
            advance(op["by"])
        elif kind == "acquire":
            got = bool(bucket.acquire(op["n"]))
            if got != op["expect"]:
                return "acquire(%d) at t=%.3f returned %s, expected %s" % (
                    op["n"], read(), got, op["expect"],
                )
        else:
            return "unknown op %r" % (kind,)
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
