"""Scripted-clock runner: executes the case set against one limiter implementation.

Time is injected: the limiter only ever sees the scripted clock below, so a
full sweep costs no wall-clock time beyond interpretation. No real sleeps.
"""
import importlib.util
import json
from pathlib import Path


class ScriptedClock:
    """A zero-argument callable clock whose reading advances only on demand."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def load_limiter(impl_dir):
    path = Path(impl_dir) / "tokenbucket.py"
    spec = importlib.util.spec_from_file_location("tokenbucket_under_test", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TokenBucket


def run_case(token_bucket_cls, case):
    """Return None on success, or a one-line failure detail."""
    clock = ScriptedClock()
    bucket = token_bucket_cls(case["rate"], case["burst"], clock)
    for op in case["ops"]:
        if op["op"] == "advance":
            clock.now += op["by"]
        elif op["op"] == "acquire":
            got = bool(bucket.acquire(op["n"]))
            if got != op["expect"]:
                return "acquire(%d) at t=%.3f returned %s, expected %s" % (
                    op["n"], clock.now, got, op["expect"],
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
        except Exception as exc:  # a crashing implementation fails the case
            detail = "raised %r" % (exc,)
        if detail is not None:
            failures.append((case["id"], bool(case.get("required", True)), detail))
    return failures
