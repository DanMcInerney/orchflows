"""Verifier for a log-triage task: the delivered `triage.json` against the failure a person marked in `build.log`.

    python tests/verify.py --task TASKDIR --workspace WORKSPACE --result FILE

Evaluator data is `tests/expected.json`: `spans`, the 1-based inclusive line ranges where the marked failure text
occurs in the delivered log (more than one when the text repeats; any occurrence counts), and the `chunk` text.
The log's line count comes from `environment/build.log` in the task, never from the workspace copy the solver
could have changed. Lines follow the public convention: a line ends at CRLF, LF or CR, and a final break does not
start another line.

Format. `triage.json` must be a regular file holding JSON (any whitespace, key order, extra keys, a byte-order mark
or escaped characters) whose `failure_lines` is two numbers with integer values, 1 <= first <= last <= line count.
Booleans, strings, fractions and other shapes earn nothing. `summary` is not graded.

Overlap. For the occurrence the range fits best, with C the marked lines, R the delivered lines and C+ the marked
lines widened by SLACK lines at each end (context lines are not an error):
    coverage = |R and C| / |C|             how much of the failure the range holds
    focus    = |R and C+| / |R|            how much of the range is the failure
Credit is 0.5 * coverage + 0.5 * focus. A range that holds no marked line, or fewer than FLOOR of whose lines lie
in C+, selects nothing: both dimensions are 0, so a dump of the whole log, or of a long stretch around the failure,
earns nothing. Full success needs coverage and focus of at least FULL.
"""
import argparse
import json
import re
from pathlib import Path

SLACK = 2
FLOOR = 0.25
FULL = 0.8
WEIGHT = 0.5
MAX_BYTES = 1 << 20
BREAK = re.compile(r"\r\n|\n|\r")


def count_lines(text: str) -> int:
    parts = BREAK.split(text)
    return len(parts) - (1 if parts[-1] == "" else 0)


def read_range(raw: bytes | None, lines: int) -> tuple[tuple[int, int] | None, str]:
    """The delivered (first, last), or None with the reason it is not a valid range."""
    if raw is None:
        return None, "triage.json is missing"
    if len(raw) > MAX_BYTES:
        return None, "triage.json is larger than 1 MiB"
    try:
        doc = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None, "triage.json is not valid JSON"
    value = doc.get("failure_lines") if isinstance(doc, dict) else None
    if not (isinstance(value, list) and len(value) == 2):
        return None, "failure_lines is not a list of two numbers"
    found = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or (isinstance(item, float) and not item.is_integer()):
            return None, "failure_lines holds a value that is not an integer"
        found.append(int(item))
    first, last = found
    if not 1 <= first <= last <= lines:
        return None, f"range {first}-{last} is not inside lines 1-{lines} in order"
    return (first, last), ""


def measure(first: int, last: int, spans: list) -> dict:
    """Coverage and focus for the best-fitting occurrence."""
    best = None
    length = last - first + 1
    for start, end in spans:
        hit = max(0, min(last, end) - max(first, start) + 1)
        near = max(0, min(last, end + SLACK) - max(first, start - SLACK) + 1)
        size = end - start + 1
        coverage, focus = hit / size, near / length
        selects = hit > 0 and focus >= FLOOR
        found = {"coverage": coverage if selects else 0.0, "focus": focus if selects else 0.0, "hit": hit, "near": near, "size": size,
                 "span": (start, end), "selects": selects}
        found["full"] = found["coverage"] >= FULL and found["focus"] >= FULL
        key = (found["full"], WEIGHT * found["coverage"] + (1 - WEIGHT) * found["focus"])
        if best is None or key > best[0]:
            best = (key, found)
    return best[1]


def grade(expected: dict, lines: int, raw: bytes | None) -> dict:
    delivered, why = read_range(raw, lines)
    coverage = focus = 0.0
    full = False
    reason = why
    if delivered:
        found = measure(*delivered, expected["spans"])
        coverage, focus, full = round(found["coverage"], 6), round(found["focus"], 6), found["full"]
        reason = (f"range {delivered[0]}-{delivered[1]}: {found['hit']} of {found['size']} marked lines (marked {found['span'][0]}-{found['span'][1]}), "
                  f"{found['near']} of {delivered[1] - delivered[0] + 1} lines on or within {SLACK} of them"
                  + ("" if found["selects"] else "; the range selects nothing"))
    return {"grading_status": "scored", "full_success": full, "credit": WEIGHT * coverage + (1 - WEIGHT) * focus,
            "dimensions": {"coverage": {"credit": coverage, "weight": WEIGHT, "required": True},
                           "focus": {"credit": focus, "weight": 1 - WEIGHT, "required": True}},
            "critical_failures": [], "reason": reason}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()
    task = Path(args.task)
    expected = json.loads((task / "tests" / "expected.json").read_text(encoding="utf-8"))
    lines = count_lines((task / "environment" / "build.log").read_bytes().decode("utf-8", errors="replace"))
    path = Path(args.workspace) / "triage.json"
    raw = path.read_bytes() if path.is_file() and not path.is_symlink() else None
    Path(args.result).write_text(json.dumps(grade(expected, lines, raw)), encoding="utf-8")


if __name__ == "__main__":
    main()
