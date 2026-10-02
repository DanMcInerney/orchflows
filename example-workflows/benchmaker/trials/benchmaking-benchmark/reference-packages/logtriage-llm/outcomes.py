"""Labelled outcomes for the package's own admission evidence, and the documented grading rule restated over sets.

`expected_grade` applies the rule in `sources/verify.py` a second way (sets of line numbers instead of interval
arithmetic) so a disagreement between the two points at a bug in one of them. `labeled_outcomes` builds the
submissions a verifier must judge: valid answers in several JSON shapes, and wrong ones that a triage prompt or a
shortcut plausibly produces. Standard library only.
"""
from __future__ import annotations

import json
import re

SLACK, FLOOR, FULL = 2, 0.25, 0.8
ERROR = re.compile(r"error|fail|exception", re.I)
EXAMPLE = (212, 231)    # the range printed in the instruction


def expected_grade(first: int, last: int, spans: list, n: int) -> tuple[bool, float]:
    """(full success, credit) for a well-formed range, from the documented rule."""
    if not 1 <= first <= last <= n:
        return False, 0.0
    picked = set(range(first, last + 1))
    best = (False, 0.0)
    for start, end in spans:
        marked, near = set(range(start, end + 1)), set(range(start - SLACK, end + SLACK + 1))
        hit, close = len(picked & marked), len(picked & near)
        coverage, focus = hit / len(marked), close / len(picked)
        if hit == 0 or focus < FLOOR:
            coverage = focus = 0.0
        outcome = (coverage >= FULL and focus >= FULL, 0.5 * coverage + 0.5 * focus)
        best = max(best, outcome)
    return best


def heuristics(lines: list[str]) -> dict[str, tuple[int, int]]:
    """Ranges the obvious scripts choose: the last 50 lines, and 5 lines around the first or last error-like line."""
    n = len(lines)
    hits = [i for i, line in enumerate(lines, 1) if ERROR.search(line)]
    first = hits[0] if hits else None
    last = hits[-1] if hits else None
    window = lambda at: (n, n) if at is None else (max(1, at - 2), min(n, at + 2))
    return {"tail_50": (max(1, n - 49), n), "grep_first_error": window(first), "grep_last_error": window(last)}


def dumps(first, last, *, indent=None, reverse=False, extra=False, ascii_only=True, bom=False, crlf=False, summary="The build failed.") -> bytes:
    doc = {"failure_lines": [first, last], "summary": summary}
    if extra:
        doc["confidence"] = 0.8
    if reverse:
        doc = dict(reversed(list(doc.items())))
    text = json.dumps(doc, indent=indent, ensure_ascii=ascii_only, separators=(",", ":") if indent is None else None)
    if crlf:
        text = text.replace("\n", "\r\n")
    return (("﻿" if bom else "") + text + "\n").encode("utf-8")


def labeled_outcomes(lines: list[str], spans: list, summary: str) -> list[dict]:
    """[{kind, files, accept, credit}]: `accept` and `credit` follow the documented rule or, for malformed files, are 0."""
    n = len(lines)
    s, e = spans[0]
    size = e - s + 1
    rows, seen = [], set()

    def ranged(kind, first, last, **style):
        if (first, last) in seen or not 1 <= first <= last <= n:
            return
        seen.add((first, last))
        accept, credit = expected_grade(first, last, spans, n)
        rows.append({"kind": kind, "files": {"triage.json": dumps(first, last, summary=summary, **style)}, "accept": accept, "credit": credit})

    def malformed(kind, data):
        rows.append({"kind": kind, "files": {} if data is None else {"triage.json": data}, "accept": False, "credit": 0.0})

    ranged("exact", s, e)
    for style, kind in (({"indent": 2, "reverse": True, "extra": True}, "exact-indented-reordered-extra-key"),
                        ({"bom": True, "crlf": True, "indent": 4, "ascii_only": False}, "exact-bom-crlf-unicode"),
                        ({"ascii_only": False}, "exact-unicode-summary")):
        seen.discard((s, e))
        ranged(kind, s, e, **style)
    rows.append({"kind": "exact-integral-floats", "files": {"triage.json": json.dumps({"failure_lines": [float(s), float(e)], "summary": summary}).encode()},
                 "accept": True, "credit": 1.0})
    rows.append({"kind": "exact-without-summary", "files": {"triage.json": json.dumps({"failure_lines": [s, e]}).encode()}, "accept": True, "credit": 1.0})
    rows.append({"kind": "exact-summary-not-text", "files": {"triage.json": json.dumps({"failure_lines": [s, e], "summary": 5}).encode()}, "accept": True, "credit": 1.0})
    for other in spans[1:]:
        ranged("alternate-occurrence", *other)
    ranged("context-2", max(1, s - 2), min(n, e + 2))
    ranged("context-asymmetric", max(1, s - 1), min(n, e + 2))
    if size >= 10:
        ranged("trimmed-one-each-end", s + 1, e - 1)
    ranged("off-by-one-low", s - 1, e - 1)
    ranged("off-by-one-high", s + 1, e + 1)
    if size >= 6:
        ranged("first-half-only", s, s + size // 2 - 1)
        ranged("first-line-only", s, s)
    ranged("last-line-only", e, e)
    ranged("moved-after", e + 1, e + size)
    ranged("moved-before", s - size, s - 1)
    ranged("far-before-start", 1, size)
    ranged("far-after-end", n - size + 1, n)
    ranged("wide-context-5", s - 5, e + 5)
    ranged("wide-around-4x", max(1, s - 4 * size), min(n, e + 4 * size))
    ranged("whole-log", 1, n)
    ranged("whole-log-minus-first-line", 2, n)
    ranged("whole-log-minus-last-line", 1, n - 1)
    for name, span in heuristics(lines).items():
        ranged(f"heuristic-{name}", *span)
    ranged("instruction-example", *EXAMPLE)
    malformed("missing-file", None)
    malformed("empty-file", b"")
    malformed("prose", b"The build failed in the test step; see the traceback near the end.\n")
    malformed("fenced-json", b"```json\n" + dumps(s, e, summary=summary) + b"```\n")
    malformed("json-with-prose", b"Here is the answer: " + dumps(s, e, summary=summary))
    malformed("wrong-key", json.dumps({"lines": [s, e], "summary": summary}).encode())
    malformed("start-end-object", json.dumps({"failure_lines": {"start": s, "end": e}, "summary": summary}).encode())
    malformed("numbers-as-strings", json.dumps({"failure_lines": [str(s), str(e)], "summary": summary}).encode())
    malformed("booleans", json.dumps({"failure_lines": [True, True], "summary": summary}).encode())
    malformed("fractional", json.dumps({"failure_lines": [s + 0.5, e], "summary": summary}).encode())
    malformed("three-numbers", json.dumps({"failure_lines": [s, s + 1, e], "summary": summary}).encode())
    malformed("null", json.dumps({"failure_lines": None, "summary": summary}).encode())
    malformed("array-not-object", json.dumps([s, e]).encode())
    malformed("deeply-nested-json", b"[" * 100000)
    if e > s:
        malformed("reversed", dumps(e, s, summary=summary))
    malformed("before-first-line", dumps(0, e, summary=summary))
    malformed("past-last-line", dumps(s, n + 1, summary=summary))
    return rows
