"""Validate loop lint, links, and contract pins."""

from __future__ import annotations

import subprocess

from tools.validate_support import common as __dep_common
BOUND_TERM_RE = __dep_common.BOUND_TERM_RE
LOOP_TRIGGER_RE = __dep_common.LOOP_TRIGGER_RE
MD_LINK_RE = __dep_common.MD_LINK_RE
ROOT = __dep_common.ROOT
SKIPPED = __dep_common.SKIPPED
TERMINAL_TERM_RE = __dep_common.TERMINAL_TERM_RE
hashlib = __dep_common.hashlib
json = __dep_common.json
re = __dep_common.re

from tools.validate_support import packages as __dep_packages
CONTRACTS_DIR = __dep_packages.CONTRACTS_DIR
Diagnostics = __dep_packages.Diagnostics
PINS_FILE = __dep_packages.PINS_FILE
PIN_MESSAGE = __dep_packages.PIN_MESSAGE
_read_source = __dep_packages._read_source
rel = __dep_packages.rel

from tools.validate_support import structure as __dep_structure
_doclint = __dep_structure._doclint

from tools.validate_support.names import _heading_slugs

def validate_loop_lint(body: str, pkg: dict, diag: Diagnostics) -> None:
    if not LOOP_TRIGGER_RE.search(body):
        return
    file_label = rel(pkg["skill_md"])
    if not BOUND_TERM_RE.search(body):
        diag.warn(file_label, "mentions iteration/loop but body lacks a 'bound' or 'budget' term")
    if not TERMINAL_TERM_RE.search(body):
        diag.warn(
            file_label,
            "mentions iteration/loop but body lacks a 'stalled'/'limited'/'exit'/'terminal' term",
        )


def validate_cross_package_links(packages, diag: Diagnostics) -> None:
    by_root = {pkg["path"].resolve(): pkg for pkg in packages}
    for pkg in packages:
        for source_file in sorted(pkg["path"].rglob("*.md")):
            text = _read_source(source_file)
            for match in MD_LINK_RE.finditer(text):
                resolved = _doclint().resolve_link(source_file, match.group(1))
                if resolved is None or "references" not in resolved.parts:
                    continue
                owner_pkg = None
                for root, candidate in by_root.items():
                    try:
                        resolved.relative_to(root)
                    except ValueError:
                        continue
                    owner_pkg = candidate
                    break
                if owner_pkg is None or owner_pkg["path"].resolve() == pkg["path"].resolve():
                    continue
                owner_text = _read_source(owner_pkg["skill_md"])
                ref_suffix = f"references/{resolved.name}"
                if ref_suffix not in owner_text:
                    diag.error(
                        rel(source_file),
                        f"cross-package link to {rel(resolved)} but owning package's "
                        f"SKILL.md does not itself cite '{ref_suffix}'",
                    )


def compute_pins(contracts_dir=None) -> dict:
    # Newlines normalized before hashing, for the reason `write_pins` gives
    # below: the tree stores LF (`.gitattributes`), so a working copy a
    # Windows tool rewrote as CRLF is the same contract, and hashing its
    # raw bytes pins a digest no other host can reproduce. That pin passes
    # `--pin`'s own author and fails every CI leg, which is the worst shape
    # a guard can have -- green where it is written, red where it is read.
    return {
        f.name: hashlib.sha256(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for f in sorted((contracts_dir or CONTRACTS_DIR).glob("*.md"))
    }


def write_pins() -> dict:
    pins = compute_pins()
    PINS_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Bytes with LF: a text-mode write on Windows would land CRLF and
    # differ from every other host's pin file.
    PINS_FILE.write_bytes((json.dumps(pins, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return pins


T0_FIELD_RE = re.compile(r"(?m)^\s*(?:[-*]\s+)?`([a-z][a-z0-9_]*)`\s*(?:—|-)")
T0_TABLE_FIELD_RE = re.compile(r"(?m)^\|\s*([a-z][a-z0-9_]*)\s*\|")


def _t0_shape(text: str) -> tuple:
    """The named-field surface whose change requires supersession."""

    fields = set(T0_FIELD_RE.findall(text)) | set(T0_TABLE_FIELD_RE.findall(text))
    enum_lines = (line for line in text.splitlines()
                  if re.search(r"\b(?:one of|enum|values?)\b", line, re.IGNORECASE))
    enums = {token for line in enum_lines
             for token in re.findall(r"`([a-z][a-z0-9_-]*)`", line)}
    return tuple(sorted(fields)), tuple(sorted(enums))


def _git(*args, text=False):
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, check=True, text=text
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def _historical_contract_text(path, digest: str):
    """Find the Git version whose normalized bytes produced `digest`."""

    relative = path.relative_to(ROOT).as_posix()
    history = _git("log", "--format=%H", "--", relative, text=True)
    if history is None:
        return None
    for revision in history.splitlines()[:100]:
        data = _git("show", f"{revision}:{relative}")
        if data is not None and hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() == digest:
            return data.decode("utf-8-sig")
    return None


def _committed_pins() -> dict:
    """The pin digests HEAD carries, empty when it carries no pins file."""

    data = _git("show", f"HEAD:{PINS_FILE.relative_to(ROOT).as_posix()}")
    if data is None:
        return {}
    try:
        committed = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return committed if isinstance(committed, dict) else {}


def validate_pin_supersessions(diag: Diagnostics) -> None:
    """Refuse a T0 shape re-pin without a record citing the old pin."""

    if not PINS_FILE.is_file():
        return
    try:
        recorded = json.loads(PINS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    current = compute_pins()
    committed = _committed_pins()
    corpus = "\n".join(_read_source(path) for path in sorted(CONTRACTS_DIR.glob("*.md")))
    for name, old_digest in recorded.items():
        path = CONTRACTS_DIR / name
        if name not in current or current[name] == old_digest or not path.is_file():
            continue
        cited = old_digest
        before = _historical_contract_text(path, old_digest)
        if before is None and committed.get(name, old_digest) != old_digest:
            # A second `--pin` inside one change: the first rewrote the
            # working-tree pins to a digest no commit carries, so there is
            # neither a `before` text to compare nor a digest any reader
            # could look up. HEAD's pin is that reader's `before`, and the
            # record cites it -- which also makes the first record still
            # good, so `--pin` is idempotent inside one change.
            cited = committed[name]
            before = _historical_contract_text(path, cited)
        if before is not None and _t0_shape(before) == _t0_shape(_read_source(path)):
            continue
        record = rf"(?im)^.*T0\s+supersess\w*.*sha256:{re.escape(cited)}.*$"
        if not re.search(record, corpus):
            diag.error(
                rel(path),
                "named-field or enum change requires an explicit T0 supersession "
                f"record citing sha256:{cited} before pins are rewritten",
            )


# --- Markdown links resolve (docs/documentation.md law 5) ---------------
#
# Every relative markdown link in every .md the library ships resolves to
# a file and, when present, a heading in that file. External URLs and
# templated paths are skipped. REVIEW-*.md are dated evidence and exempt.
LINKED_MD_ROOTS = ("rules", "contracts", "docs", "skills", "packs", "example-workflows", "templates", "benchmarks")
# Sites whose heading carries a parenthetical suffix; none currently.
MARKDOWN_ANCHOR_EXEMPT_SITES = frozenset()


def _linked_markdown_files():
    for name in sorted(ROOT.glob("*.md")):
        if not name.name.startswith("REVIEW-"):
            yield name
    for root in LINKED_MD_ROOTS:
        yield from sorted((ROOT / root).rglob("*.md"))


def _anchor_target(source, target: str):
    """Return (resolved markdown file, anchor) for an internal fragment."""

    raw = target.strip()
    raw = raw[1:raw.index(">")] if raw.startswith("<") and ">" in raw else raw.split(" ", 1)[0]
    if "#" not in raw or raw.startswith(_doclint().EXTERNAL_PREFIXES) or "{{" in raw:
        return None
    path_text, anchor = raw.split("#", 1)
    if not anchor:
        return None
    resolved = source if not path_text else _doclint().resolve_link(source, path_text, ROOT)
    if resolved is None or not resolved.is_file() or resolved.suffix.lower() != ".md":
        return None
    return resolved, anchor.lower()


def validate_markdown_links(diag: Diagnostics) -> None:
    absent = [root for root in LINKED_MD_ROOTS if not (ROOT / root).is_dir()]
    if absent:
        for root in absent:
            diag.warn(root, SKIPPED)
        return
    dangling_links = _doclint().dangling_links
    for source in _linked_markdown_files():
        text = _read_source(source)
        for target in dangling_links(source, text, ROOT):
            diag.error(rel(source), f"markdown link does not resolve: {target}")
        for match in MD_LINK_RE.finditer(text):
            if (rel(source), match.group(1)) in MARKDOWN_ANCHOR_EXEMPT_SITES:
                continue
            anchored = _anchor_target(source, match.group(1))
            if anchored and anchored[1] not in _heading_slugs(_read_source(anchored[0])):
                diag.error(rel(source), f"markdown anchor does not resolve: {match.group(1)}")


# --- §N citations name a real clause (docs/documentation.md law 5, dissolves
# report P5) -------------------------------------------------------------
#
# A `[text](path) §N` citation resolving its link and anchor (the check
# above) says nothing about whether clause N is the clause the prose
# claims it is: a citation surviving a renumbering, or copy-pasted onto
# the wrong file, is invisible to both. This check resolves N against the
# target's own numbered clause -- a top-level ordered-list item for a
# `rules/*.md` law file, or `docs/documentation.md`'s own numbered `## N.`
# headings and its nested "law N" list under `## 3. Laws` -- and refuses a
# citation whose declared expectation is not a substring of that clause's
# own text. The expectation is a short phrase already in the clause's own
# wording (never a restated sentence, so editing the clause does not by
# itself require editing this map -- only a rename or renumbering does),
# declared once here per (file, clause) rather than left for a reader to
# notice only when the fact it names turns out to be false, the way
# `README.md`, `docs/custom-workflow-authoring.md`, and
# `templates/host-block.md` each did (report P5's three sites). A citation
# to a law file with no declared expectation here fails the same way, so a
# newly authored citation must declare one rather than join that blind
# spot; `SECTION_EXPECTATIONS`/`LAW_EXPECTATIONS` cover every §N/"law N"
# citation this checkout currently makes to these nine files.
LAW_FILES = frozenset({
    "rules/verification.md", "rules/roles.md", "rules/topology.md",
    "rules/visibility.md", "rules/token-economy.md", "rules/composition.md",
    "rules/delegation.md", "rules/improvement.md", "docs/documentation.md",
})

SECTION_EXPECTATIONS = {
    ("rules/verification.md", 2): "outside the semantic seal",
    ("rules/verification.md", 3): "read-only",
    ("rules/verification.md", 6): "contradict the claim",
    ("rules/verification.md", 7): "caller's own join",
    ("rules/verification.md", 8): "artifact and dependencies it covers",
    ("rules/roles.md", 4): "Resolve role at each dispatch",
    ("rules/topology.md", 3): "Goal, Context, and optional Details",
    ("rules/topology.md", 5): "mechanically observable shape",
    ("rules/topology.md", 6): "belongs to a ticket, not a run",
    ("rules/visibility.md", 1): "Shared library packages",
    ("rules/visibility.md", 2): "never names a project package",
    ("rules/visibility.md", 3): "One owner per fact",
    ("rules/visibility.md", 4): "belongs to one package",
    ("rules/visibility.md", 6): "Run state is runtime data",
    ("rules/token-economy.md", 1): "Every sentence must change",
    ("rules/token-economy.md", 2): "cut the how",
    ("rules/token-economy.md", 6): "Placement follows",
    ("rules/token-economy.md", 8): "Models route by descriptions",
    ("rules/token-economy.md", 10): "Shape principles",
    ("rules/token-economy.md", 11): "Budgets bound what is loaded",
    ("rules/composition.md", 1): "one directory owning one",
    ("rules/composition.md", 5): "Anatomy:",
    ("rules/composition.md", 6): "Admission:",
    ("rules/composition.md", 8): "failure path returns partial results",
    ("rules/composition.md", 9): "Generic skills",
    ("rules/composition.md", 10): "named T0 carrier",
    ("rules/composition.md", 11): "binding contract",
    ("rules/delegation.md", 2): "glue-only",
    ("rules/delegation.md", 8): "closed callable registry",
    ("rules/delegation.md", 10): "Artifact primacy",
    ("rules/improvement.md", 1): "Friction law",
    ("rules/improvement.md", 4): "qualifies on recurrence",
    ("docs/documentation.md", 7): "Factories",
}

# `docs/documentation.md`'s own "law N" list, under its `## 3. Laws`
# heading -- a second, differently-spelled numbering inside the same file
# as the `§N` headings above, cited by its own vocabulary ("law 2", "laws
# 6, 9") rather than "§".
LAW_EXPECTATIONS = {
    2: "retrieval API",
    6: "implemented enforcement",
    9: "Examples execute",
    10: "human surface is separate",
}

# Horizontal whitespace only ([ \t]*, never \s*): a citation's marker and
# number sit on one visual line in this corpus, and \s* previously let a
# blank line and a heading through -- matching "Laws" in a "## 3. Laws"
# heading to a wholly unrelated later "1." list marker as "law 1".
CITE_RE = re.compile(
    r"(§+|laws?)[ \t]*(\d+(?:[ \t]*[–-][ \t]*\d+)?(?:[ \t]*,[ \t]*\d+(?:[ \t]*[–-][ \t]*\d+)?)*)",
    re.IGNORECASE,
)
NUMBERED_HEADING_RE = re.compile(r"(?m)^#{1,6}\s+(\d+)\.\s+(.+?)\s*$")
TOP_LIST_ITEM_RE = re.compile(r"(?m)^(\d+)\.\s+")
LAWS_SECTION_RE = re.compile(r"(?ms)^## 3\. Laws\s*\n(.*?)(?=\n## |\Z)")
TEMPLATE_CITE_RE = re.compile(
    r"\{\{ORCH_LIB\}\}/(rules/[a-z][a-z-]*\.md)[ \t]+(§+|laws?)[ \t]*"
    r"(\d+(?:[ \t]*[–-][ \t]*\d+)?(?:[ \t]*,[ \t]*\d+(?:[ \t]*[–-][ \t]*\d+)?)*)",
    re.IGNORECASE,
)


def _expand_citation_numbers(spec: str):
    numbers = []
    for piece in spec.split(","):
        piece = piece.strip()
        if not piece:
            continue
        bounds = re.split(r"\s*[–-]\s*", piece)
        if len(bounds) == 2:
            numbers.extend(range(int(bounds[0]), int(bounds[1]) + 1))
        else:
            numbers.append(int(bounds[0]))
    return numbers


def _ordered_list_item_text(text: str, n: int):
    """The Nth top-level (column-0) ordered-list item's own text, joined
    and whitespace-collapsed; ``None`` if the list has no item ``n``."""

    starts = [(int(m.group(1)), m.start(), m.end()) for m in TOP_LIST_ITEM_RE.finditer(text)]
    for index, (num, item_start, body_start) in enumerate(starts):
        if num != n:
            continue
        end = starts[index + 1][1] if index + 1 < len(starts) else len(text)
        return " ".join(text[body_start:end].split())
    return None


def _numbered_heading_text(text: str, n: int):
    for match in NUMBERED_HEADING_RE.finditer(text):
        if int(match.group(1)) == n:
            return match.group(2)
    return None


def _law_item_text(text: str, n: int):
    match = LAWS_SECTION_RE.search(text)
    if not match:
        return None
    return _ordered_list_item_text(match.group(1), n)


def _clause_text(target_rel: str, n: int, is_law_word: bool):
    text = _read_source(ROOT / target_rel)
    if is_law_word:
        return _law_item_text(text, n) if target_rel == "docs/documentation.md" else None
    if target_rel == "docs/documentation.md":
        return _numbered_heading_text(text, n)
    return _ordered_list_item_text(text, n)


def _citation_finding(source_label: str, target_rel: str, n: int, is_law_word: bool):
    marker = "law" if is_law_word else "§"
    expectation = (
        LAW_EXPECTATIONS.get(n) if is_law_word else SECTION_EXPECTATIONS.get((target_rel, n))
    )
    if expectation is None:
        return (
            f"citation to {target_rel} {marker}{n} has no declared expectation in "
            "tools/validate_support/lint.py's SECTION_EXPECTATIONS/LAW_EXPECTATIONS; "
            "register one or fix the citation"
        )
    actual = _clause_text(target_rel, n, is_law_word)
    if actual is None or expectation.lower() not in actual.lower():
        return (
            f"citation to {target_rel} {marker}{n} does not hold: expected a clause "
            f"containing {expectation!r}, found {actual!r}"
        )
    return None


def _citation_window(text: str, start: int) -> str:
    """The text right after one qualifying link, bounded to just its own
    citation clause: cut at the next link (a different target's own
    citation), table-cell boundary, or sentence end -- whichever comes
    first -- so a citation is never credited with a later, unrelated `§N`
    two sentences or one table row away. A soft line-wrap alone does not
    cut it: this corpus wraps a citation's marker onto the line after its
    link, and `window` must still reach it."""

    window = text[start:start + 200]
    cuts = [pos for pos in (window.find("["), window.find("|"), window.find(".")) if pos != -1]
    return window[:min(cuts)] if cuts else window


def _citations_in_window(window: str):
    for match in CITE_RE.finditer(window):
        is_law_word = match.group(1).lower().startswith("law")
        for number in _expand_citation_numbers(match.group(2)):
            yield is_law_word, number


def validate_section_citations(diag: Diagnostics) -> None:
    for source in _linked_markdown_files():
        text = _read_source(source)
        label = rel(source)
        for link in MD_LINK_RE.finditer(text):
            resolved = _doclint().resolve_link(source, link.group(1), ROOT)
            if resolved is None or not resolved.is_file():
                continue
            try:
                target_rel = resolved.relative_to(ROOT).as_posix()
            except ValueError:
                continue
            if target_rel not in LAW_FILES:
                continue
            window = _citation_window(text, link.end())
            for is_law_word, number in _citations_in_window(window):
                finding = _citation_finding(label, target_rel, number, is_law_word)
                if finding:
                    diag.error(label, finding)
        for match in TEMPLATE_CITE_RE.finditer(text):
            target_rel, marker, numbers = match.group(1), match.group(2), match.group(3)
            if target_rel not in LAW_FILES:
                continue
            is_law_word = marker.lower().startswith("law")
            for number in _expand_citation_numbers(numbers):
                finding = _citation_finding(label, target_rel, number, is_law_word)
                if finding:
                    diag.error(label, finding)


def validate_pins(diag: Diagnostics) -> None:
    current = compute_pins()
    if not PINS_FILE.is_file():
        diag.error(rel(PINS_FILE), PIN_MESSAGE)
        return
    try:
        recorded = json.loads(PINS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        diag.error(rel(PINS_FILE), f"pins.json is not valid JSON: {exc}")
        return
    for name, digest in current.items():
        if recorded.get(name) != digest:
            diag.error(rel(CONTRACTS_DIR / name), PIN_MESSAGE)
    for name in recorded:
        if name not in current:
            diag.error(rel(PINS_FILE), PIN_MESSAGE)


__all__ = (
    'validate_loop_lint', 'validate_cross_package_links', 'compute_pins', 'write_pins',
    'validate_pin_supersessions', 'LINKED_MD_ROOTS', '_linked_markdown_files',
    'validate_markdown_links', 'validate_section_citations', 'validate_pins',
)
