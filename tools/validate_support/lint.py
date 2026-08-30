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


def validate_pin_supersessions(diag: Diagnostics) -> None:
    """Refuse a T0 shape re-pin without a record citing the old pin."""

    if not PINS_FILE.is_file():
        return
    try:
        recorded = json.loads(PINS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    current = compute_pins()
    corpus = "\n".join(_read_source(path) for path in sorted(CONTRACTS_DIR.glob("*.md")))
    for name, old_digest in recorded.items():
        path = CONTRACTS_DIR / name
        if name not in current or current[name] == old_digest or not path.is_file():
            continue
        before = _historical_contract_text(path, old_digest)
        if before is not None and _t0_shape(before) == _t0_shape(_read_source(path)):
            continue
        record = rf"(?im)^.*T0\s+supersess\w*.*sha256:{re.escape(old_digest)}.*$"
        if not re.search(record, corpus):
            diag.error(
                rel(path),
                "named-field or enum change requires an explicit T0 supersession "
                f"record citing sha256:{old_digest} before pins are rewritten",
            )


# --- Markdown links resolve (docs/documentation.md law 5) ---------------
#
# Every relative markdown link in every .md the library ships resolves to
# a file and, when present, a heading in that file. External URLs and
# templated paths are skipped. REVIEW-*.md are dated evidence and exempt.
LINKED_MD_ROOTS = ("rules", "contracts", "docs", "skills", "packs", "compositions", "templates", "benchmarks")
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
    'validate_markdown_links', 'validate_pins',
)
