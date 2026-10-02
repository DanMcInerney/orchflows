"""Log-triage domain over LogChunks (Brandt, Panichella, Beller 2020; CC BY 4.0).

A task is a CI build log (`build.log`) and the answer is the line range that shows why the build failed
(`triage.json`). LogChunks labels the failure as chunk text, not as line numbers, and strips escape
characters and some punctuation from it. A chunk is therefore located by comparing keys that keep only
letters and digits, and it can occur more than once; every occurrence is acceptable.

Line convention (public, shared with the subject): a line ends at CRLF, LF or CR; a final line break
does not start another line. All line numbers are 1-based, inclusive, and count lines of the delivered
`build.log`. A delivered log is recognized when its lines, ignoring ANSI sequences and trailing blanks,
are one contiguous run of some labelled log (public or held-out). A task is uncovered (`recognize` returns
None) when the labelled chunk is not wholly inside the delivered lines or occurs more than MAX_OCCURRENCES times.
"""
from __future__ import annotations

import itertools
import json
import os
import re
import shutil
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from bisect import bisect_right
from pathlib import Path

NAME = "logtriage"
META_TASK = "logtriage-llm"
INPUT, OUTPUT = "build.log", "triage.json"
LENIENT = 2          # edge distance in lines still counted as close to the chunk (suboptimal, not valid)
PARTIAL = 0.5        # overlap (intersection over union) at or above which a wrong range is suboptimal
MAX_OCCURRENCES = 5  # a chunk that repeats more often inside the delivered log is too ambiguous to score
DIAGNOSTIC = frozenset({"first_line_only", "format_drift"})   # validity depends on the builder's stated contract

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b")
_BREAK = re.compile(r"\r\n|\n|\r")
_NONWORD = re.compile(r"[\W_]+")
_TOKEN = re.compile(rb"[A-Za-z][A-Za-z0-9_./-]{9,}")
_ERROR = re.compile(r"error|fail|exception", re.I)
_MATERIAL = Path(__file__).resolve().parents[2] / "meta-tasks" / META_TASK / "material.json"

_store: Path | None = None
_entries: dict[str, list[dict]] = {}


def configure(store) -> None:
    """Point the domain at a metabench store; None falls back to METABENCH_STORE, then the default."""
    global _store
    _store = Path(store) if store else None
    _entries.clear()


def store_root() -> Path:
    return _store or Path(os.environ.get("METABENCH_STORE") or Path.home() / ".bmk-eval" / "meta")


def material_dir(store=None) -> Path:
    return Path(store or store_root()) / "material" / META_TASK


# ---------------------------------------------------------------- lines and labels

def delivered_lines(text: str) -> list[str]:
    lines = _BREAK.split(text)
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _norm(line: str) -> str:
    return _ANSI.sub("", line).rstrip()


def chunk_spans(lines: list[str], chunk: str) -> list[tuple[int, int]]:
    """0-based inclusive line ranges of every non-overlapping occurrence of the chunk text."""
    want = _NONWORD.sub("", chunk)
    if not want:
        return []
    keys = [_NONWORD.sub("", line) for line in lines]
    ends = list(itertools.accumulate(len(k) for k in keys))
    big = "".join(keys)
    spans, at = [], big.find(want)
    while at >= 0:
        spans.append((bisect_right(ends, at), bisect_right(ends, at + len(want) - 1)))
        at = big.find(want, at + len(want))
    return spans


def load_entries(root: Path) -> list[dict]:
    """Labelled logs under a LogChunks-shaped tree: build-failure-reason/<lang>/<owner@repo>.xml and logs/."""
    root, found = Path(root), []
    for xml in sorted((root / "build-failure-reason").glob("*/*.xml")):
        for node in ET.parse(xml).getroot().iter("Example"):
            log = node.findtext("Log") or ""
            found.append({"log": log, "id": Path(log).stem, "language": log.split("/")[0],
                          "repo": log.split("/")[1].replace("@", "/"), "keywords": node.findtext("Keywords") or "",
                          "category": node.findtext("Category") or "", "chunk": node.findtext("Chunk") or "",
                          "path": root / "logs" / log})
    return found


def corpus(store=None) -> list[dict]:
    base = material_dir(store)
    key = str(base)
    if key not in _entries:
        _entries[key] = [dict(e, split=part) for part in ("public", "held-out")
                         for e in load_entries(base / part)]
    return _entries[key]


# ---------------------------------------------------------------- instances

def instance(lines: list[str], spans: list, **meta) -> dict:
    spans = [list(s) for s in spans]
    return {**meta, "lines": lines, "n_lines": len(lines), "spans": spans}


def _probes(raw_lines: list[str]) -> list[bytes]:
    """Long ASCII words from up to five spread-out lines. A source log is a candidate when it holds most of them as
    bytes; ANSI sequences inside a delivered word can hide a few."""
    last = len(raw_lines) - 1
    tokens: list[bytes] = []
    for i in sorted({0, last // 4, last // 2, 3 * last // 4, last}):
        found = _TOKEN.findall(raw_lines[i].encode("utf-8", "replace"))
        if found:
            tokens.append(max(found, key=len))
    return tokens


def _runs(source: list[str], core: list[str]):
    at = -1
    while True:
        try:
            at = source.index(core[0], at + 1)
        except ValueError:
            return
        if source[at:at + len(core)] == core:
            yield at


def recognize(workspace: Path, prompt: str = "") -> dict | None:
    path = Path(workspace) / INPUT
    if not path.is_file():
        return None
    lines = delivered_lines(path.read_bytes().decode("utf-8", errors="replace"))
    keys = [_norm(line) for line in lines]
    filled = [i for i, k in enumerate(keys) if k]
    if not filled:
        return None
    lead, last = filled[0], filled[-1]
    core = keys[lead:last + 1]
    probes = _probes(lines[lead:last + 1])
    n = len(lines)
    for entry in corpus():
        data = entry["path"].read_bytes()
        if sum(p in data for p in probes) < (len(probes) + 1) // 2:
            continue
        source = delivered_lines(data.decode("utf-8", errors="replace"))
        normed = [_norm(line) for line in source]
        found = []
        for at in _runs(normed, core):
            base = at - lead                      # source index of the delivered file's first line
            for a, b in chunk_spans(source, entry["chunk"]):
                if a >= base and b < base + n and [a - base + 1, b - base + 1] not in found:
                    found.append([a - base + 1, b - base + 1])
        if found and len(found) <= MAX_OCCURRENCES:
            return instance(lines, found, id=entry["id"], log=entry["log"], repo=entry["repo"],
                            language=entry["language"], split=entry["split"], chunk=entry["chunk"])
    return None


# ---------------------------------------------------------------- outputs

def _summary(inst: dict) -> str:
    first = next((" ".join(l.split()) for l in inst.get("chunk", "").splitlines() if l.strip()), "")
    return ("Build failed: " + first[:160]) if first else "The build failed; see the selected lines."


def _dump(span, summary: str, *, indent=None, reverse=False, extra=False, ascii_only=True) -> bytes:
    doc = {"failure_lines": [span[0], span[1]], "summary": summary}
    if extra:
        doc["confidence"] = 0.8
    if reverse:
        doc = dict(reversed(list(doc.items())))
    separators = (",", ":") if indent is None else None
    text = json.dumps(doc, indent=indent, separators=separators, ensure_ascii=ascii_only)
    return (text + ("\n" if indent else "")).encode("utf-8")


def solve(inst: dict) -> list[dict[str, bytes]]:
    return [{OUTPUT: _dump(span, _summary(inst))} for span in inst["spans"]]


def apply(workspace: Path, files: dict[str, bytes]) -> None:
    for name, data in files.items():
        target = Path(workspace) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def _iou(a, b) -> float:
    inter = min(a[1], b[1]) - max(a[0], b[0]) + 1
    return max(inter, 0) / ((a[1] - a[0] + 1) + (b[1] - b[0] + 1) - max(inter, 0))


def _classify(answer, spans, n) -> tuple[str, list[str]]:
    s, e = answer
    if not 1 <= s <= e <= n:
        return "invalid", [f"range {s}-{e} is outside lines 1-{n}"]
    spans = [tuple(sp) for sp in spans]
    if tuple(answer) in spans:
        return "valid", []
    if any(abs(s - a) <= LENIENT and abs(e - b) <= LENIENT for a, b in spans):
        return "suboptimal", [f"edges within {LENIENT} lines of the labelled chunk"]
    best = max(_iou(answer, sp) for sp in spans)
    if best >= PARTIAL:
        return "suboptimal", [f"overlaps the labelled chunk (intersection over union {best:.2f})"]
    return "invalid", [f"overlap with the labelled chunk is {best:.2f}"]


def _answer(raw):
    if raw is None:
        return None, f"{OUTPUT} is missing", ""
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None, f"{OUTPUT} is not JSON", ""
    if not isinstance(doc, dict):
        return None, f"{OUTPUT} is not an object", ""
    lines = doc.get("failure_lines")
    if not (isinstance(lines, list) and len(lines) == 2 and all(type(v) is int for v in lines)):
        return None, "failure_lines is not a list of two integers", ""
    return (lines[0], lines[1]), "", "" if isinstance(doc.get("summary"), str) else "summary is not a string"


def check(inst: dict, files: dict[str, bytes]) -> dict:
    answer, problem, note = _answer(files.get(OUTPUT))
    if answer is None:
        return {"label": "unparseable", "reasons": [problem]}
    label, reasons = _classify(answer, inst["spans"], inst["n_lines"])
    return {"label": label, "reasons": reasons + ([note] if note else []), "failure_lines": list(answer)}


def labeled(inst: dict) -> list[dict]:
    """Constructed rows. 'lenient' rows are close to the chunk and excluded from TPR and TNR."""
    n, spans = inst["n_lines"], [tuple(sp) for sp in inst["spans"]]
    s, e = spans[0]
    size, summary = e - s + 1, _summary(inst)
    rows = []

    def add(files, label, kind):
        rows.append({"files": files, "label": label, "kind": kind})

    for style in ({}, {"indent": 2}, {"reverse": True}, {"extra": True}, {"indent": 4, "ascii_only": False}):
        add({OUTPUT: _dump((s, e), summary, **style)}, "valid", "json-variant")
    for span in spans[1:]:
        add({OUTPUT: _dump(span, summary)}, "valid", "alternate-occurrence")
    wrong = {"after": (e + 1, e + size), "before": (s - size, s - 1), "head": (1, size),
             "tail": (n - size + 1, n), "last-line": (n, n), "dump-all": (1, n)}
    for kind, span in wrong.items():
        if 1 <= span[0] <= span[1] <= n and _classify(span, spans, n)[0] == "invalid":
            add({OUTPUT: _dump(span, summary)}, "invalid", kind)
    add({OUTPUT: b"The build failed in the test step.\n"}, "invalid", "not-json")
    add({OUTPUT: json.dumps({"lines": [s, e], "summary": summary}).encode()}, "invalid", "wrong-schema")
    near = {(s - LENIENT, e), (s, e + LENIENT), (s - LENIENT, e + LENIENT), (s + 1, e - 1)}
    for span in sorted(near):
        if 1 <= span[0] <= span[1] <= n and span != (s, e) and _classify(span, spans, n)[0] == "suboptimal":
            add({OUTPUT: _dump(span, summary)}, "lenient", "valid-lenient")
    return rows


# ---------------------------------------------------------------- heuristics and defects

def _read_lines(workspace: Path) -> list[str]:
    path = Path(workspace) / INPUT
    return delivered_lines(path.read_bytes().decode("utf-8", errors="replace")) if path.is_file() else []


def _out(span, summary: str) -> dict[str, bytes]:
    return {OUTPUT: _dump(span, summary)}


def _tail(lines, *, count=50):
    return _out((max(1, len(lines) - count + 1), max(1, len(lines))), f"Last {count} lines of the log.")


def _match(lines, *, last):
    hits = [i for i, line in enumerate(lines, 1) if _ERROR.search(line)]
    if not hits:
        return _out((max(1, len(lines)),) * 2, "No error line found; the last line.")
    at = hits[-1 if last else 0]
    return _out((max(1, at - 2), min(len(lines), at + 2)), lines[at - 1].strip()[:160])


HEURISTICS = {
    "tail_50": lambda ws, prompt="": _tail(_read_lines(ws)),
    "grep_first_error": lambda ws, prompt="": _match(_read_lines(ws), last=False),
    "grep_last_error": lambda ws, prompt="": _match(_read_lines(ws), last=True),
    "dump_all": lambda ws, prompt="": _out((1, max(1, len(_read_lines(ws)))), "The whole log."),
}


def _shifted(inst, rng):
    n, (s, e) = inst["n_lines"], inst["spans"][0]
    size = e - s + 1
    gap = size + rng.randint(0, 5)
    if e + gap <= n and (s - gap < 1 or rng.random() < 0.5):
        start = s + gap
    elif s - gap >= 1:
        start = s - gap
    else:
        start = 1 if s - 1 > n - e else max(1, n - size + 1)
    return _out((start, min(n, start + size - 1)), "Shifted selection.")


def _first_error(inst, rng):
    return _match(inst["lines"], last=False)


def _first_line_only(inst, rng):
    return _out((inst["spans"][0][0],) * 2, "First line of the failure.")


def _format_drift(inst, rng):
    body = _dump(inst["spans"][0], _summary(inst)).decode()
    return {OUTPUT: f"Here is my analysis of the failure:\n```json\n{body}\n```\n".encode()}


DEFECTS = {"shifted": _shifted, "first_error": _first_error,
           "first_line_only": _first_line_only, "format_drift": _format_drift}


# ---------------------------------------------------------------- material (network only)

def _write_examples(root: Path, entries: list[dict]) -> None:
    by_file: dict[str, list[dict]] = {}
    for entry in entries:
        language, repo = entry["log"].split("/")[:2]
        by_file.setdefault(f"{language}/{repo}.xml", []).append(entry)
    for name, group in by_file.items():
        top = ET.Element("Examples")
        for entry in group:
            node = ET.SubElement(top, "Example")
            for tag, value in (("Log", entry["log"]), ("Keywords", entry["keywords"]),
                               ("Category", entry["category"]), ("Chunk", entry["chunk"])):
                ET.SubElement(node, tag).text = value
        ET.indent(top)
        target = root / "build-failure-reason" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(top).write(target, encoding="utf-8", xml_declaration=True)
        for entry in group:
            copy = root / "logs" / entry["log"]
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(entry["path"], copy)


def build_split(source: Path, dest: Path, public_ids: list[str], *, attribution: str = "") -> dict:
    """Write public/, held-out/ and split.json under dest from a LogChunks-shaped tree at source."""
    entries = load_entries(source)
    known = {e["id"] for e in entries}
    if missing := sorted(set(public_ids) - known):
        raise ValueError(f"public ids not in the dataset: {missing}")
    chosen = set(public_ids)
    dest = Path(dest)
    for part, group in (("public", [e for e in entries if e["id"] in chosen]),
                        ("held-out", [e for e in entries if e["id"] not in chosen])):
        shutil.rmtree(dest / part, ignore_errors=True)
        _write_examples(dest / part, group)
    (dest / "public" / "README.md").write_text(
        "# LogChunks sample\n\n" + attribution.strip() + "\n\n"
        "Layout: `logs/<language>/<owner@repo>/failed/<build_id>.log` are Travis CI logs as collected. "
        "`build-failure-reason/<language>/<owner@repo>.xml` holds one `Example` per log: `Log` (path under `logs/`), "
        "`Keywords`, `Category` (an integer code the dataset does not document) and `Chunk`, the text a person "
        "marked as the part of the log describing why the build failed. Chunks carry no line numbers.\n"
        "Logs are unchanged; the label files are filtered to this sample. The dataset has been public since 2020, "
        "so a model may have seen these logs.\n", encoding="utf-8", newline="\n")
    split = {"public": [e["id"] for e in entries if e["id"] in chosen],
             "held_out": [e["id"] for e in entries if e["id"] not in chosen],
             "logs": {e["id"]: {"repo": e["repo"], "language": e["language"]} for e in entries}}
    (dest / "split.json").write_text(json.dumps(split, indent=1), encoding="utf-8", newline="\n")
    _entries.clear()
    return split


def _extract(archive: Path, target: Path) -> Path:
    keep = ("logs/", "build-failure-reason/", "readme.md", "repositories.txt")
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            parts = Path(member.filename).parts
            if member.is_dir() or parts[0] != "LogChunks" or ".." in parts or Path(member.filename).is_absolute():
                continue
            inner = "/".join(parts[1:])
            if inner.endswith(".DS_Store") or not inner.startswith(keep):
                continue
            out = target / Path(*parts)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(bundle.read(member))
    return target / "LogChunks"


def fetch_material(store, *, material: dict | None = None) -> dict:
    """Download LogChunks from Zenodo into <store>/material/logtriage-llm/source and split it. Network only."""
    spec = material or json.loads(_MATERIAL.read_text(encoding="utf-8"))
    dest = material_dir(store)
    source = dest / "source"
    source.mkdir(parents=True, exist_ok=True)
    archive = source / spec["archive"]["file"]
    if not archive.is_file() or archive.stat().st_size != spec["archive"]["size"]:
        part = archive.with_name(archive.name + ".part")
        with urllib.request.urlopen(spec["archive"]["url"], timeout=120) as reply, part.open("wb") as out:
            shutil.copyfileobj(reply, out)
        if part.stat().st_size != spec["archive"]["size"]:
            raise ValueError(f"{archive.name}: downloaded {part.stat().st_size} bytes, expected {spec['archive']['size']}")
        part.replace(archive)
    return build_split(_extract(archive, source), dest, spec["public"], attribution=spec["attribution"])
