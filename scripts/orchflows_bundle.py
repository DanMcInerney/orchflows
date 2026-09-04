#!/usr/bin/env python3
"""A bundle's own manifest: `BUNDLE.md` beside its item directories.

The file `contracts/bundle.md` owns -- a bundle's name, the revision of it
this is, and the pinned bundles it requires -- and nothing else. Reading
one fetches nothing and trusts nothing: it produces references, and
`scripts/orchflows_home.py`'s pin law decides which may be followed.

Separate from that module because this is knowledge of a file format and
that is the ring's use of it: the manifest arrives from a remote, so its
parser is small, one-directional, and readable entire.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

try:
    from scripts import rings
except ImportError:  # pragma: no cover - direct/installed flat script path
    import rings


def manifest_path(bundle: Path) -> Path:
    """One bundle directory's manifest: ``<bundle>/BUNDLE.md``."""

    return Path(bundle) / rings.BUNDLE_MANIFEST


def clone_bundle_dir(clone: Path) -> Path:
    """The bundle directory inside a cloned bundle repository."""

    return Path(clone) / rings.BUNDLE_DIR


def _scalar(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1].strip()
    return text


def _manifest_fields(text: str) -> Dict[str, object]:
    """The manifest's frontmatter: scalars, plus a list where one is written."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    end = next(
        (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
        None,
    )
    if end is None:
        return {}
    fields: Dict[str, object] = {}
    key = None
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            if isinstance(fields.get(key), list):
                fields[key].append(_scalar(stripped[2:]))
            continue
        name, separator, rest = line.partition(":")
        if not separator or line[:1].isspace():
            continue
        key = name.strip()
        rest = rest.strip()
        if rest.startswith("[") and rest.endswith("]"):
            fields[key] = [
                _scalar(part) for part in rest[1:-1].split(",") if part.strip()
            ]
        else:
            fields[key] = _scalar(rest) if rest else []
    return fields


def read_manifest(bundle: Path) -> Optional[dict]:
    """One bundle's manifest, or ``None`` where it carries none."""

    path = manifest_path(bundle)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    fields = _manifest_fields(text)
    requires = fields.get("requires", [])
    if not isinstance(requires, list):
        raise rings.RingError(
            "manifest-invalid",
            f"{path} declares requires: {requires!r}. A bundle's requires is "
            "a list of <git-url>@<pin> references.",
        )
    return {
        "path": path,
        "name": str(fields.get("name") or ""),
        "version": str(fields.get("version") or ""),
        "requires": [str(item) for item in requires],
    }


__all__ = (
    "clone_bundle_dir", "manifest_path", "read_manifest",
)
