"""Read material in the LogChunks layout: labelled logs, line splitting and chunk location.

A label is chunk text, not line numbers, with escape characters, carriage returns and some punctuation removed. A
chunk is therefore located by comparing keys that hold only letters and digits; it can occur more than once.
Standard library only; nothing here imports the meta-verifier.
"""
from __future__ import annotations

import itertools
import re
import xml.etree.ElementTree as ET
from bisect import bisect_right
from pathlib import Path

BREAK = re.compile(r"\r\n|\n|\r")
NONWORD = re.compile(r"[\W_]+")
MIN_KEY = 6    # a label with fewer letters and digits cannot be located reliably

FAMILIES = (   # a keyword guess for material without a family label; first match wins
    ("timeout", re.compile(r"timed out|no output has been received|exceeded the maximum time|time limit|killed", re.I)),
    ("dependency-resolution", re.compile(r"could not (resolve|find)|no matching distribution|resolutionimpossible|eresolve|unable to (resolve|locate)|"
                                         r"dependency|cannot find module|npm err! (code|notarget)|404", re.I)),
    ("compile-error", re.compile(r"error\W{0,8}\[|compileerror|undefined reference|cannot find symbol|compilation (error|failure)|syntaxerror|"
                                 r"fatal error: .*\.h|ld returned|expected .* before", re.I)),
    ("environment-error", re.compile(r"command not found|permission denied|cannot open shared object|no such file or directory|"
                                     r"could not read username|rake aborted", re.I)),
    ("static-analysis", re.compile(r"longer than \d+ char|\bE\d{3}\b|eslint|rubocop|flake8|pylint|phpstan|critic|shellcheck|stylelint|\blint", re.I)),
    ("test-failure", re.compile(r"assert|failures?:|\bfailed\b|expected|\bfail\b|panicked|traceback|there w(as|ere) \d+ failure", re.I)),
)


def split_lines(text: str) -> list[str]:
    parts = BREAK.split(text)
    return parts[:-1] if parts[-1] == "" else parts


def read_log(path: Path) -> tuple[str | None, str]:
    """The log text, or None with the reason it cannot be a task."""
    try:
        return path.read_bytes().decode("utf-8"), ""
    except OSError as error:
        return None, f"cannot read the log: {error}"
    except UnicodeDecodeError:
        return None, "the log is not valid UTF-8"


def find_root(directory: Path) -> Path:
    """The folder holding build-failure-reason/ and logs/ (the directory itself, or its LogChunks/ folder)."""
    directory = Path(directory)
    for candidate in (directory, directory / "LogChunks"):
        if (candidate / "build-failure-reason").is_dir() and (candidate / "logs").is_dir():
            return candidate
    raise SystemExit(f"{directory}: no build-failure-reason/ and logs/ folders (expected the LogChunks layout)")


def load_entries(root: Path) -> list[dict]:
    root, found = Path(root), []
    for xml in sorted((root / "build-failure-reason").glob("*/*.xml")):
        for node in ET.parse(xml).getroot().iter("Example"):
            log = (node.findtext("Log") or "").strip()
            if log.count("/") < 3:
                continue
            language, owner_repo = log.split("/")[:2]
            found.append({"log": log, "id": Path(log).stem, "language": language, "group": owner_repo.replace("@", "/"),
                          "keywords": node.findtext("Keywords") or "", "chunk": node.findtext("Chunk") or "", "path": root / "logs" / log})
    return found


def chunk_spans(lines: list[str], chunk: str) -> list[tuple[int, int]]:
    """1-based inclusive line ranges of the non-overlapping occurrences of the chunk text."""
    want = NONWORD.sub("", chunk)
    if len(want) < MIN_KEY:
        return []
    keys = [NONWORD.sub("", line) for line in lines]
    ends = list(itertools.accumulate(len(key) for key in keys))
    big = "".join(keys)
    spans, at = [], big.find(want)
    while at >= 0:
        spans.append((bisect_right(ends, at) + 1, bisect_right(ends, at + len(want) - 1) + 1))
        at = big.find(want, at + len(want))
    return spans


def guess_family(chunk: str) -> str:
    for name, pattern in FAMILIES:
        if pattern.search(chunk):
            return name
    return "other-failure"
