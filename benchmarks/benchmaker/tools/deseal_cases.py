#!/usr/bin/env python3
"""De-seal the JSON of a case package.

A benchmark's version is its git revision, so a package manifest carries
no whole-package identity and no digest beside a component's locator.
This tool performs that removal over a case package — the manifest and
every sibling JSON under it — and nothing else:

1. a ``benchmark_identity`` key is dropped;
2. a component reference ``{"<digest key>": ..., "locator": ...}`` loses
   its digest and keeps its locator, in both case dialects (the digest
   key is ``sha256`` or ``identity``, its value ``sha256:``-prefixed or
   bare hex);
3. a qualification ``covers`` value that addressed a component by digest
   addresses it by the locator that digest named — as a bare string, a
   list item, or a mapping value;
4. recorded audit prose describing the retired recompute is replaced
   from a fixed table, so no record claims an oracle that no longer
   exists.

Everything else is preserved byte for byte: indentation, key order,
spacing and the trailing newline. That is why this edits text rather
than reserializing. The edit is proved equivalent to the object-level
transform before it is written — ``json.loads`` of the new text must
equal the transform of ``json.loads`` of the old — so a text edit that
drifts from its meaning is refused rather than written.

Nothing is skipped silently. A file that does not parse, a cover naming
a digest no component claims, and a surviving retired token are each a
refusal naming the path and the reason.

Evidence identity is a different discipline and is left alone: a case's
``evidence@sha256:`` provenance, a provenance chain's link identities
and a held-back store's identity are not component digests, and no rule
here matches them.

Stdlib only, no network. Exit 0 and silent when there is nothing to do;
exit 1 with one line per refusal:

    ERROR <path>: <message>

Usage:

    deseal_cases.py [--cases-dir DIR] [--check] [PACKAGE ...]

With no positional argument every package under ``--cases-dir`` is
de-sealed in place. ``--check`` writes nothing and exits 1 if any file
would change, which is how idempotence is read.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CASES_DIR = HERE.parent / "cases"

IDENTITY_KEY = "benchmark_identity"
DIGEST_KEYS = ("sha256", "identity")
DIGEST_RE = re.compile(r"(?:sha256:[0-9a-f]{8,}|\b[0-9a-f]{64}\b)")

# The audit these records describe no longer exists: there is no identity
# to recompute and no digest to verify. Each replacement states what the
# surviving audit reads instead. Longest first, so a shorter rule never
# eats part of a longer match.
AUDIT_PROSE = (
    (
        "manifest canonicalization audit: recompute benchmark_identity and every "
        "component digest over the shipped bytes",
        "manifest audit: every schema field present and every component locator "
        "resolving over the shipped bytes",
    ),
    (
        "benchmark_identity recomputes from the canonical payload; all ten fields "
        "present; every component digest verified over shipped bytes",
        "all nine schema fields present; every component locator resolves over "
        "shipped bytes",
    ),
    (
        "benchmark_identity recomputed from the canonical payload; six component "
        "digests verified over shipped bytes",
        "nine schema fields present; six component locators resolved over shipped bytes",
    ),
    (
        "benchmark_identity recomputed equal; six component digests verified over "
        "shipped bytes",
        "nine schema fields present; six component locators resolved over shipped bytes",
    ),
)


class DesealError(Exception):
    """The file cannot be de-sealed mechanically, and is not skipped."""


# --------------------------------------------------------------------
# the object transform — the meaning the text edit must match
# --------------------------------------------------------------------


def objects(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            for found in objects(value):
                yield found
    elif isinstance(node, list):
        for value in node:
            for found in objects(value):
                yield found


def is_digest(value):
    return isinstance(value, str) and DIGEST_RE.fullmatch(value.strip()) is not None


def is_component_reference(node):
    """A locator with a digest beside it, in either dialect."""
    if not isinstance(node, dict) or not isinstance(node.get("locator"), str):
        return False
    return any(is_digest(node.get(key)) for key in DIGEST_KEYS)


def bare(digest):
    digest = digest.strip()
    return digest[len("sha256:") :] if digest.startswith("sha256:") else digest


def digest_to_locator(manifest):
    """Map every digest the manifest recorded to the locator it named."""
    mapping = {}
    for node in objects(manifest):
        if not is_component_reference(node):
            continue
        for key in DIGEST_KEYS:
            if is_digest(node.get(key)):
                mapping[bare(node[key])] = node["locator"]
    return mapping


def relocate(value, locators, path):
    """Swap each component digest in a cover for the locator it named."""
    out = value
    for match in sorted(set(DIGEST_RE.findall(value)), key=len, reverse=True):
        locator = locators.get(bare(match))
        if locator is None:
            raise DesealError(
                "{}: cover names digest {} that no component of this package "
                "claims".format(path, match[:24])
            )
        out = out.replace(match, locator)
    return out


def relocate_covers(value, locators, path):
    if isinstance(value, str):
        return relocate(value, locators, path)
    if isinstance(value, list):
        return [relocate(v, locators, path) if isinstance(v, str) else v for v in value]
    if isinstance(value, dict):
        return {
            key: relocate(v, locators, path) if isinstance(v, str) else v
            for key, v in value.items()
        }
    return value


def retire_prose(value):
    for retired, surviving in AUDIT_PROSE:
        value = value.replace(retired, surviving)
    return value


def deseal_object(node, locators, path):
    """The transform, as a pure function over parsed JSON."""
    if isinstance(node, list):
        return [deseal_object(v, locators, path) for v in node]
    if isinstance(node, str):
        return retire_prose(node)
    if not isinstance(node, dict):
        return node
    drop = {IDENTITY_KEY}
    if is_component_reference(node):
        drop.update(key for key in DIGEST_KEYS if is_digest(node.get(key)))
    out = {}
    for key, value in node.items():
        if key in drop:
            continue
        if key == "covers":
            out[key] = relocate_covers(value, locators, path)
        else:
            out[key] = deseal_object(value, locators, path)
    return out


# --------------------------------------------------------------------
# the text edit — the same transform, formatting preserved
# --------------------------------------------------------------------

MEMBER_RE = re.compile(r'^(\s*)"([^"]+)"\s*:\s*(.*?),?\s*$')


def drop_dangling_commas(lines):
    """A member deleted from the end of an object leaves one comma too many."""
    out = list(lines)
    for index, line in enumerate(out):
        if not line.rstrip().endswith(","):
            continue
        following = next(
            (out[j].strip() for j in range(index + 1, len(out)) if out[j].strip()), ""
        )
        if following[:1] in ("}", "]"):
            out[index] = line.rstrip()[:-1]
    return out


def indent_of(line):
    return len(line) - len(line.lstrip())


def sibling_keys(lines, index):
    """The member keys of the object the line at ``index`` belongs to."""
    depth = indent_of(lines[index])
    keys = set()
    for step in (1, -1):
        cursor = index + step
        while 0 <= cursor < len(lines):
            line = lines[cursor]
            if line.strip() and indent_of(line) < depth:
                break
            if indent_of(line) == depth:
                match = MEMBER_RE.match(line)
                if match is not None:
                    keys.add(match.group(2))
            cursor += step
    return keys


def strip_members(text):
    """Delete every ``benchmark_identity`` and component-digest member.

    A digest is a component's only when a ``locator`` sits beside it. An
    off-tree store's identity has no locator and is left alone.
    """
    lines = text.splitlines()
    kept = []
    for index, line in enumerate(lines):
        match = MEMBER_RE.match(line)
        if match is not None:
            key, value = match.group(2), match.group(3)
            quoted = value.startswith('"') and value.endswith('"')
            if key == IDENTITY_KEY and quoted:
                continue
            if (
                key in DIGEST_KEYS
                and quoted
                and is_digest(value[1:-1])
                and "locator" in sibling_keys(lines, index)
            ):
                continue
        kept.append(line)
    return drop_dangling_commas(kept)


def relocate_cover_lines(lines, locators):
    """Rewrite digests inside a ``covers`` value, and nowhere else."""
    out = []
    closing = None
    for line in lines:
        inside = closing is not None
        if inside and line.strip()[:1] in ("]", "}") and len(line) - len(line.lstrip()) <= closing:
            closing = None
        elif not inside:
            match = MEMBER_RE.match(line)
            if match is not None and match.group(2) == "covers":
                inside = True
                if match.group(3) in ("[", "{"):
                    closing = len(match.group(1))
        if inside:
            line = DIGEST_RE.sub(
                lambda m: locators.get(bare(m.group(0)), m.group(0)), line
            )
        out.append(line)
    return out


def deseal_text(text, locators, path="<text>"):
    """Rewrite the file's text, then prove the rewrite means the transform."""
    try:
        before = json.loads(text)
    except ValueError as error:
        raise DesealError("{}: does not parse as JSON: {}".format(path, error))
    expected = deseal_object(before, locators, path)
    if expected == before:
        return text

    lines = relocate_cover_lines(strip_members(text), locators)
    rewritten = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    for retired, surviving in AUDIT_PROSE:
        rewritten = rewritten.replace(retired, surviving)

    try:
        after = json.loads(rewritten)
    except ValueError as error:
        raise DesealError("{}: the rewrite does not parse: {}".format(path, error))
    if after != expected:
        raise DesealError(
            "{}: the text edit and the transform disagree; edit this file by "
            "hand".format(path)
        )
    for node in objects(after):
        for value in node.values():
            if isinstance(value, str) and IDENTITY_KEY in value:
                raise DesealError(
                    "{}: no rule covers {!r}; add it to AUDIT_PROSE rather than "
                    "leaving the token".format(path, value[:80])
                )
    return rewritten


# --------------------------------------------------------------------
# packages
# --------------------------------------------------------------------


def package_roots(base):
    return sorted({path.parent for path in Path(base).rglob("manifest.json")})


def deseal_package(root, write=True):
    """De-seal one package. Returns the paths whose text changed."""
    root = Path(root)
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise DesealError("{}: no manifest.json".format(root))
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise DesealError("{}: does not parse as JSON: {}".format(manifest_path, error))
    locators = digest_to_locator(manifest)
    changed = []
    for path in sorted(root.rglob("*.json")):
        text = path.read_text(encoding="utf-8")
        rewritten = deseal_text(text, locators, path)
        if rewritten != text:
            changed.append(path)
            if write:
                path.write_text(rewritten, encoding="utf-8")
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description="De-seal benchmaker case packages.")
    parser.add_argument("packages", nargs="*", help="package roots; default is every package")
    parser.add_argument("--cases-dir", default=str(DEFAULT_CASES_DIR))
    parser.add_argument(
        "--check", action="store_true", help="write nothing; exit 1 if anything would change"
    )
    args = parser.parse_args(argv)

    roots = [Path(p) for p in args.packages] or package_roots(args.cases_dir)
    errors, changed = [], []
    for root in roots:
        try:
            changed.extend(deseal_package(root, write=not args.check))
        except DesealError as error:
            errors.append("ERROR {}".format(error))
    for line in errors:
        print(line)
    for path in changed:
        print("{} {}".format("would change" if args.check else "de-sealed", path))
    if errors:
        return 1
    return 1 if (args.check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
