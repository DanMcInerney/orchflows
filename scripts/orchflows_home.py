#!/usr/bin/env python3
"""The home ring: its layout, its committed/regenerable boundary, its pins.

``~/.orchflows`` is meant to be the user's own git repository -- their
skills, packs, workflows, friction history and run ledgers in one place,
cloned onto the next machine.  That only works if exactly one line is
drawn and drawn here: nothing custom is ever written into ``lib/``, and
nothing regenerable is ever committed.  ``ensure`` creates the ring's
directories, records which library the ring expects, and writes the one
managed block in the ring's ``.gitignore`` that draws the line.

``add`` and ``restore`` are the other half.  An external bundle is
referenced and pinned, never copied into the home ring: a promoted copy is
outside every lockfile and becomes one version for all projects (npm's
global tier, the survey's cautionary tale).  ``imports.lock`` is the pin
and ``imports/`` is regenerable from it, which is why the lock is
committed and the clones are not.  A bundle declares what it needs in its
own ``BUNDLE.md`` (contracts/bundle.md); ``add`` pins that whole closure
and ``restore`` brings it back.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

try:
    from scripts import orchflows_bundle, rings, state_root
except ImportError:  # pragma: no cover - direct/installed flat script path
    import orchflows_bundle
    import rings
    import state_root


LIB_VERSION_NAME = "lib.version"
GITIGNORE_NAME = ".gitignore"
# The installer's freshness record, read here and by every scope-home
# consumer (`tickets_store`, and the installer's own doctor/planning/
# uninstall) instead of respelling the filename.
RECEIPT_FILENAME = "receipt.json"
GITIGNORE_START = "# BEGIN ORCHFLOWS MANAGED IGNORES"
GITIGNORE_END = "# END ORCHFLOWS MANAGED IGNORES"
# Regenerable or machine-local, in that order: the installed library and its
# runtime, the per-item environments `orchflows_envs.py` rebuilds from each
# item's committed `requirements.txt`, the browser distribution, scratch
# trees, the pinned clones the lock restores, the trust ledger that must
# never travel (P2), and the state trees that are heavy or per-run rather
# than history. `state/friction/` and
# `state/runs/` are deliberately absent: they are the sync value.
# The six sink subdirectory names are `state_root.py`'s owners -- its
# `tickets_root` function for the one with a root already, its five new
# `*_SUBPATH` constants for the rest -- imported rather than restated so
# a renamed subdirectory there cannot drift silently out of what the
# home ring ignores.
SINK_MANAGED_SUBPATHS = (
    state_root.tickets_root().name,
    state_root.LOCKS_SUBPATH,
    state_root.SCRATCH_SUBPATH,
    state_root.WORKSPACES_SUBPATH,
    state_root.MUTANTS_SUBPATH,
    state_root.DRAFTS_SUBPATH,
)
MANAGED_IGNORES = (
    "lib/",
    "runtime/",
    "envs/",
    "node_modules/",
    "ui/",
    "tmp/",
    "worktrees/",
    "imports/",
    "trust.json",
) + tuple(f"state/{name}/" for name in SINK_MANAGED_SUBPATHS)
# The project ring's half of the same line. A project's committed content is
# its bundle and its rendered adapters; the one regenerable tree `sync`
# writes inside a repository is an item's `node_modules/`, restored from the
# lockfile committed beside the manifest.
PROJECT_IGNORES = ("node_modules/",)
RING_DIRS = tuple(rings.RING_DIRS.values())
_SHA_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
_REF_SPLIT_RE = re.compile(r"^(?P<url>.+?)@(?P<pin>[^@/]+)$")
MUTABLE_REF_REFUSAL = (
    "'{pin}' is not a pin. A branch name or HEAD moves under you, which is "
    "how 23,000 repositories consumed a rewritten tag in one afternoon; only "
    "consumers naming a commit were unaffected. Name the tag or the full "
    "commit SHA you mean: orchflows add {url}@<tag-or-sha>."
)
# The two refusals a manifest's `requires` can carry, each naming the
# manifest that holds the offending line rather than the bundle the user
# typed: the author of the reference is who has to fix it.
UNPINNED_REQUIREMENT_REFUSAL = (
    "{manifest} requires '{entry}', which is not a pinned bundle: {detail} "
    "A requirement is <git-url>@<tag-or-sha>, held to the same pin law as a "
    "reference somebody types."
)
CYCLE_REQUIREMENT_REFUSAL = (
    "{manifest} requires {required}, which this import already opened: "
    "{chain}. A bundle cycle has no closure to pin; break the ring in one of "
    "those manifests."
)


def _write_lf(path: Path, text: str) -> None:
    """Write UTF-8 with LF endings on every host.

    Bytes, not `write_text(newline=...)`: that keyword arrived in 3.10 and
    `install.py`'s floor is 3.9, and a text-mode write on Windows would put
    CRLF in a file the ring owner then commits.
    """

    path.write_bytes(text.encode("utf-8"))


def upsert_block(text: str, body: str) -> str:
    """Replace this module's managed block in ``text``, or append it."""

    block = "\n".join([GITIGNORE_START, body.rstrip("\n"), GITIGNORE_END]) + "\n"
    start = text.find(GITIGNORE_START)
    end = text.find(GITIGNORE_END)
    if start == -1 or end == -1 or end < start:
        prefix = text if not text or text.endswith("\n") else text + "\n"
        return prefix + block
    return text[:start] + block + text[end + len(GITIGNORE_END) + 1:]


def lib_version(home: Optional[Path] = None) -> Dict[str, object]:
    """Which library this ring expects, read off the installer's receipt.

    A cloned home ring arrives without ``lib/``; this file is what tells the
    next ``install.py`` which library identity to regenerate there. It is a
    record of an installation, so an unreadable receipt records nulls rather
    than a guess.
    """

    root = home if home is not None else rings.home_ring()
    try:
        receipt = json.loads((root / RECEIPT_FILENAME).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError):
        receipt = {}
    if not isinstance(receipt, dict):
        receipt = {}
    version = receipt.get("version")
    commit = receipt.get("source_commit")
    return {
        "receipt_version": version if isinstance(version, int) and not isinstance(version, bool) else None,
        "source_commit": commit if isinstance(commit, str) and commit.strip() else None,
    }


def ensure(home: Optional[Path] = None) -> Dict[str, object]:
    """Create the home ring's directories and its two managed files.

    Idempotent, and it never touches committed ring content: an existing
    ``skills/`` is left exactly as it is, and the ``.gitignore`` is upserted
    as one marked block so a ring owner's own ignores survive.
    """

    root = Path(home) if home is not None else rings.home_ring()
    created = []
    for name in (*RING_DIRS, rings.IMPORTS_DIR):
        path = root / name
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))
    version_path = root / LIB_VERSION_NAME
    _write_lf(
        version_path,
        json.dumps(lib_version(root), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    ignore_path = root / GITIGNORE_NAME
    before = ignore_path.read_text(encoding="utf-8-sig") if ignore_path.is_file() else ""
    _write_lf(ignore_path, upsert_block(before, "\n".join(MANAGED_IGNORES)))
    return {
        "home": str(root),
        "created": created,
        "lib_version": str(version_path),
        "gitignore": str(ignore_path),
    }


def ensure_project_ignores(project: Path) -> Path:
    """Upsert the managed block in one project's ``.gitignore``.

    The same block, the same markers and the same upsert as the home ring's,
    because it draws the same committed/regenerable line -- one owner, so a
    ring whose ignores drift from a project's cannot happen. Only the lines
    differ, and only because the two rings hold different regenerable trees.
    """

    path = Path(project) / GITIGNORE_NAME
    before = path.read_text(encoding="utf-8-sig") if path.is_file() else ""
    _write_lf(path, upsert_block(before, "\n".join(PROJECT_IGNORES)))
    return path


# --- pinned imports ----------------------------------------------------


def _git(*args, cwd=None):
    return subprocess.run(
        ["git", *args], cwd=None if cwd is None else str(cwd),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def bundle_name(url: str) -> str:
    """The import's directory name: the repository's own, minus ``.git``."""

    tail = str(url).rstrip("/").replace("\\", "/").rsplit("/", 1)[-1]
    return rings.item_name(tail[:-4] if tail.endswith(".git") else tail)


def split_reference(reference: str):
    """``(url, pin)`` from ``<url>@<pin>``, or a refusal naming the shape."""

    match = _REF_SPLIT_RE.fullmatch(str(reference or "").strip())
    if match is None:
        raise rings.RingError(
            "reference-invalid",
            f"'{reference}' is not <git-url>@<pin>: an import is always a "
            "reference plus a pin, never a copy.",
        )
    return match.group("url"), match.group("pin")


def resolve_pin(url: str, pin: str) -> str:
    """Refuse a mutable ref, and return the pin to check out.

    A full commit SHA is a pin by construction. Anything else is one only
    when the remote publishes it as a tag; a branch, or a ref the remote
    does not publish at all, is refused naming the remedy (FM-4).
    """

    if _SHA_RE.fullmatch(pin):
        return pin
    listed = _git("ls-remote", "--tags", "--heads", url)
    if listed.returncode != 0:
        raise rings.RingError(
            "remote-unreadable", f"cannot read {url}: {listed.stderr.strip()}",
        )
    refs = {line.split("\t")[-1] for line in listed.stdout.splitlines() if "\t" in line}
    if f"refs/tags/{pin}" in refs:
        return pin
    raise rings.RingError(
        "mutable-ref", MUTABLE_REF_REFUSAL.format(pin=pin, url=url),
    )


def read_lock(home: Optional[Path] = None) -> List[dict]:
    return rings.read_imports(home)


def write_lock(entries: List[dict], home: Optional[Path] = None) -> Path:
    root = home if home is not None else rings.home_ring()
    path = rings.imports_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_lf(path, json.dumps(
        {"version": 1, "imports": sorted(entries, key=lambda item: item["name"])},
        ensure_ascii=False, indent=2, sort_keys=True,
    ) + "\n")
    return path


def clone_at(url: str, pin: str, target: Path) -> None:
    """Clone ``url`` into ``target`` and detach it at exactly ``pin``."""

    target.parent.mkdir(parents=True, exist_ok=True)
    cloned = _git("clone", "--quiet", url, str(target))
    if cloned.returncode != 0:
        raise rings.RingError("clone-failed", f"cannot clone {url}: {cloned.stderr.strip()}")
    checked = _git("-c", "advice.detachedHead=false", "checkout", "--quiet", pin, cwd=target)
    if checked.returncode != 0:
        raise rings.RingError(
            "pin-unreachable", f"{url} has no {pin}: {checked.stderr.strip()}",
        )


# --- bundle requirements and the closure ------------------------------


def _clone_manifest(target: Path) -> Optional[dict]:
    """The manifest of one cloned bundle, read where its items resolve."""

    return orchflows_bundle.read_manifest(orchflows_bundle.clone_bundle_dir(target))


def _requirement(entry: str, manifest: Path):
    """``(url, pin as written)`` for one ``requires`` line."""

    try:
        return split_reference(entry)
    except rings.RingError as error:
        raise rings.RingError("requires-unpinned", UNPINNED_REQUIREMENT_REFUSAL.format(
            manifest=manifest, entry=entry, detail=error.detail,
        ))


def _requirement_pin(url: str, requested: str, entry: str, manifest: Path) -> str:
    """The pin one ``requires`` line resolves to, or the unpinned refusal."""

    try:
        return resolve_pin(url, requested)
    except rings.RingError as error:
        if error.code != "mutable-ref":
            raise
        raise rings.RingError("requires-unpinned", UNPINNED_REQUIREMENT_REFUSAL.format(
            manifest=manifest, entry=entry, detail=error.detail,
        ))


def _discard(target: Path) -> None:
    """Remove a clone this call made, so a refused add leaves nothing pinned.

    The chmod pass is Windows: git marks its object files read-only, and
    ``rmtree`` there fails on exactly the tree an add most needs to undo.
    """

    for path in sorted(target.rglob("*"), reverse=True):
        try:
            path.chmod(0o700)
        except OSError:
            pass
    shutil.rmtree(str(target), ignore_errors=True)


def import_closure(root: Path, url: str, pin: str) -> List[dict]:
    """Every bundle one add pins: the named one, then what it requires.

    Depth-first, cloning as it goes, so each manifest is on disk before it
    is read. The path walked is the cycle check: a requirement naming a
    bundle already open on that path has no fixed point and is refused. A
    bundle reached twice off different paths is a diamond, not a cycle, and
    is cloned once. A refusal unwinds every clone this call made, so an add
    pins its whole closure or pins nothing.
    """

    locked = {entry["name"]: entry for entry in read_lock(root)}
    pinned: Dict[str, dict] = {}
    cloned: List[Path] = []

    def visit(url: str, pin: str, chain: List[str]) -> None:
        name = bundle_name(url)
        held = pinned.get(name) or locked.get(name)
        if held is not None and held["pin"] != pin:
            raise rings.RingError(
                "requires-conflict",
                f"{name} is pinned at {held['pin']} and this import needs "
                f"{pin}. One imports directory holds one clone of a bundle: "
                "re-pin the bundle that asks for the older one, or drop it.",
            )
        if name in pinned:
            return
        target = root / rings.IMPORTS_DIR / name
        if not target.is_dir():
            clone_at(url, pin, target)
            cloned.append(target)
        pinned[name] = {"name": name, "url": url, "pin": pin}
        manifest = _clone_manifest(target)
        for entry in (manifest or {}).get("requires") or ():
            required_url, requested = _requirement(entry, manifest["path"])
            required = bundle_name(required_url)
            if required in chain or required == name:
                raise rings.RingError("requires-cycle", CYCLE_REQUIREMENT_REFUSAL.format(
                    manifest=manifest["path"], required=required,
                    chain=" -> ".join(chain + [name, required]),
                ))
            visit(
                required_url,
                _requirement_pin(required_url, requested, entry, manifest["path"]),
                chain + [name],
            )

    try:
        visit(url, pin, [])
    except rings.RingError:
        for path in reversed(cloned):
            _discard(path)
        raise
    return list(pinned.values())


# --- pinned imports, the two verbs -------------------------------------


def add(reference: str, home: Optional[Path] = None) -> dict:
    """Pin one external bundle, and what it requires, into the home ring.

    Consent is the add, not the clone: an import trusted by this act needs
    no first-use prompt, and only a change to its pin puts it back in front
    of the user. A requirement is consented to by the same act, which is
    why the whole closure is reported back and not only the name typed.
    """

    root = Path(home) if home is not None else rings.home_ring()
    url, requested = split_reference(reference)
    pin = resolve_pin(url, requested)
    name = bundle_name(url)
    target = root / rings.IMPORTS_DIR / name
    if target.exists():
        raise rings.RingError(
            "import-exists",
            f"{name} is already imported at {target}: remove it, or edit "
            f"{rings.imports_lock_path(root)} and run orchflows sync.",
        )
    pinned = import_closure(root, url, pin)
    names = {entry["name"] for entry in pinned}
    entries = [item for item in read_lock(root) if item["name"] not in names]
    lock = write_lock(entries + pinned, root)
    return {
        "name": name, "url": url, "pin": pin, "path": str(target),
        "lock": str(lock),
        "required": [entry for entry in pinned if entry["name"] != name],
    }


def restore(home: Optional[Path] = None) -> List[dict]:
    """Bring ``imports/`` back to the closure ``imports.lock`` implies.

    Clone by clone, and then requirement by requirement: a lock naming one
    bundle whose manifest needs a second restores both and grows to record
    the second's pin. Restore is a recovery path, so a requirement it
    cannot pin is reported against the bundle that declared it instead of
    failing the sync, and a bundle already restored is never visited twice,
    which is what makes a cycle terminate here. Refusing one is `add`'s.
    """

    root = Path(home) if home is not None else rings.home_ring()
    queue = list(read_lock(root))
    closure = list(queue)
    known = {entry["name"] for entry in queue}
    results, grew = [], False
    while queue:
        entry = queue.pop(0)
        target = root / rings.IMPORTS_DIR / entry["name"]
        record = {**entry, "path": str(target)}
        if target.is_dir():
            record["action"] = "present"
        else:
            try:
                clone_at(entry["url"], entry["pin"], target)
            except rings.RingError as error:
                results.append({**record, "action": "failed", "detail": error.detail})
                continue
            record["action"] = "cloned"
        try:
            required = _restored_requirements(target, known)
        except rings.RingError as error:
            required, record["detail"] = [], error.detail
        for item in required:
            known.add(item["name"])
            closure.append(item)
            queue.append(item)
            grew = True
        results.append(record)
    if grew:
        write_lock(closure, root)
    return results


def _restored_requirements(target: Path, known) -> List[dict]:
    """One restored bundle's requirements that the lock does not carry yet.

    The pin is resolved only for a requirement that is new, so a settled
    closure costs no remote reads at all on the next sync.
    """

    manifest = _clone_manifest(target)
    found = []
    for entry in (manifest or {}).get("requires") or ():
        url, requested = _requirement(entry, manifest["path"])
        name = bundle_name(url)
        if name in known or any(item["name"] == name for item in found):
            continue
        found.append({
            "name": name, "url": url,
            "pin": _requirement_pin(url, requested, entry, manifest["path"]),
        })
    return found


__all__ = (
    "CYCLE_REQUIREMENT_REFUSAL", "GITIGNORE_END", "GITIGNORE_NAME",
    "GITIGNORE_START", "LIB_VERSION_NAME",
    "MANAGED_IGNORES", "MUTABLE_REF_REFUSAL", "PROJECT_IGNORES",
    "RECEIPT_FILENAME", "UNPINNED_REQUIREMENT_REFUSAL",
    "add", "bundle_name", "clone_at", "ensure", "ensure_project_ignores",
    "import_closure", "lib_version", "read_lock", "resolve_pin", "restore",
    "split_reference", "upsert_block", "write_lock",
)
