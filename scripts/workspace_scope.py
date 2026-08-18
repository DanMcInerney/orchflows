"""Segment-exact write-scope normalization and grading for ``workspace.py``."""

from __future__ import annotations

from pathlib import Path

from workspace_git import Refused


WRITE_SCOPE_KEY = "write_scope"
UNGRADABLE_IN_SCOPE = (" ", "\t", "(", ")")
SPACING = (" ", "\t")
CONTRACT = "contracts/work-item.md"


def _exists_as_path(entry: str, root) -> bool:
    """Whether ``entry`` names something that is actually there."""

    try:
        candidate = Path(entry)
        if candidate.is_absolute():
            return candidate.exists()
        return root is not None and (Path(root) / entry).exists()
    except OSError:  # pragma: no cover - a name the filesystem rejects
        return False


def _refuse_ungradable_scope(declared, root=None) -> None:
    """Refuse a ``write_scope`` entry no path comparison can read."""

    entries = [declared] if isinstance(declared, str) else list(declared or [])
    for raw in entries:
        entry = str(raw).strip().strip("`").strip()
        for character in UNGRADABLE_IN_SCOPE:
            if character not in entry:
                continue
            if character in SPACING and _exists_as_path(entry, root):
                break
            raise Refused(
                f"{WRITE_SCOPE_KEY} entry '{entry}' contains {character!r} and "
                f"names no path here: per {CONTRACT} an entry is exactly a "
                "path this item may change, and a phrase matches none, so "
                "nothing here can grade it. Cut the scope as one bare path "
                "per entry"
            )


def _normalized_scope(declared, root: Path) -> tuple:
    """``write_scope`` as repository-relative POSIX paths."""

    if isinstance(declared, str):
        declared = [declared]
    entries = []
    for raw in declared or []:
        entry = raw.strip().strip("`").strip()
        if not entry:
            continue
        candidate = Path(entry)
        if candidate.is_absolute() or (len(entry) > 1 and entry[1] == ":"):
            try:
                entry = candidate.resolve().relative_to(root).as_posix()
            except ValueError:
                raise Refused(
                    # quoted plainly, never {!r}: a Windows entry carries
                    # backslashes, and repr doubles every one of them, so the
                    # refusal named a path the caller never wrote and could
                    # not grep its own ticket for
                    f"{WRITE_SCOPE_KEY} entry '{entry}' is an absolute path outside the main "
                    f"repository root {root}: nothing in this repository can match "
                    "it"
                )
        parts = [part for part in entry.replace("\\", "/").split("/") if part not in ("", ".")]
        if ".." in parts:
            raise Refused(
                f"{WRITE_SCOPE_KEY} entry '{entry}' escapes the repository"
            )
        if parts:
            entries.append("/".join(parts))
    return tuple(entries)


def _in_scope(name: str, scope) -> bool:
    """A path prefix compared on whole segments: `docs` never takes `docsmith`."""

    return any(name == prefix or name.startswith(prefix + "/") for prefix in scope)
