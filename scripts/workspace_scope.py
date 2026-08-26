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


def _relative_to_any(entry: str, resolved: Path, roots) -> str:
    """An absolute entry as a POSIX path under the first root holding it.

    More than one root because the same repository is more than one
    directory: an item's grant may be written against the workspace it was
    cut for or against the checkout the join grades it in, and an entry
    refused for naming the wrong one of those would be refusing the host.
    """

    # deepest root first, never declaration order: a workspace of this
    # repository is a directory inside it, so the same entry is under both
    # the workspace and the checkout holding it, and the outer one answers
    # with a path naming the workspace rather than the grant it was written
    # for -- ``start`` and the join would canonicalise one entry two ways
    for root in sorted(roots, key=lambda entry: len(entry.parts), reverse=True):
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            continue
    raise Refused(
        # quoted plainly, never {!r}: a Windows entry carries backslashes,
        # and repr doubles every one of them, so the refusal named a path
        # the caller never wrote and could not grep its own ticket for
        f"{WRITE_SCOPE_KEY} entry '{entry}' is an absolute path outside the main "
        f"repository root {roots[0]}: nothing in this repository can match "
        "it"
    )


def _normalized_scope(declared, *roots) -> tuple:
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
            entry = _relative_to_any(entry, candidate.resolve(), roots)
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


def _actual_mutations(name_status: str) -> list:
    """Normalize ``git diff --name-status --no-renames -z`` rows."""

    tokens = name_status.split("\0")
    rows = []
    index = 0
    operations = {"A": "create", "D": "delete", "M": "change", "T": "change"}
    while index < len(tokens) and tokens[index]:
        status = tokens[index]
        if "\t" in status:
            status, path = status.split("\t", 1)
            index += 1
        elif index + 1 < len(tokens):
            path = tokens[index + 1]
            index += 2
        else:
            raise Refused("git name-status output ended before its path")
        operation = operations.get(status[:1])
        if operation is None:
            raise Refused(f"git name-status returned unsupported status {status!r}")
        rows.append((operation, path))
    return sorted(set(rows))


def _operation_plan_required(data) -> bool:
    """Whether the join grades operations in addition to path authority."""

    del data
    return True
