"""Antigravity's shared plugin inventory and home-owned installation receipts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile


POLICY_WARNING = "Antigravity manual-only skill enforcement is unverified; use /skills and its displayed commands."


def _linked(path: Path) -> bool:
    return path.is_symlink() or bool(path.exists() and getattr(path.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _safe(path: Path, root: Path) -> None:
    for part in (path, *path.parents):
        if _linked(part):
            raise ValueError(f"Antigravity path is a link; preserved: {part}")
        if part == root:
            break


def _rows(data: object) -> list[dict]:
    if not isinstance(data, dict) or not isinstance(data.get("imports"), list):
        raise ValueError("Unsupported Antigravity inventory; no registration changed")
    rows = data["imports"]
    if any(not isinstance(row, dict) or not isinstance(row.get("name"), str)
           or not re.fullmatch(r"[a-zA-Z0-9_-]+", row["name"]) for row in rows):
        raise ValueError("Unsupported Antigravity plugin identity; no registration changed")
    return rows


def inventory(executable: str, home: Path, run) -> list[dict]:
    profile = Path.home() / ".gemini/config"
    registry = profile / "import_manifest.json"
    _safe(registry, Path.home())
    # Older agy silently treats a malformed tracking file as an empty inventory.
    if registry.exists():
        _rows(json.loads(registry.read_text(encoding="utf-8")))
    output = run(executable, "plugin", "list", cwd=home).strip()
    imports = [] if output == "No imported plugins." else _rows(json.loads(output))
    roots = profile / "plugins"
    records = [(row["name"], row) for row in imports]
    if roots.is_dir():
        records.extend((path.name, None) for path in roots.iterdir()
                       if (path.is_dir() or _linked(path)) and not any(row["name"] == path.name for row in imports))
    result = []
    for name, record in records:
        path = roots / name
        _safe(path, Path.home())
        enabled = (path / "plugin.json").is_file() and not (path / "plugin.json.disabled").exists()
        if enabled:
            identity = json.loads((path / "plugin.json").read_text(encoding="utf-8"))
            if not isinstance(identity, dict) or identity.get("name", name) != name:
                raise ValueError(f"Antigravity plugin identity conflicts with its directory: {path}")
        result.append({"name": name, "path": str(path), "scope": "user", "enabled": enabled, "record": record})
    return result


def _snapshot(root: Path) -> dict[str, str]:
    result = {}
    for path in root.rglob("*"):
        if any(part in {".git", "__pycache__"} for part in path.relative_to(root).parts) or path.suffix in {".pyc", ".pyo"}:
            continue
        if _linked(path):
            raise ValueError(f"Antigravity package contains a link; preserved: {path}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _receipts(home: Path) -> tuple[Path, dict]:
    path = home / ".local/agy-installs.json"
    _safe(path, home)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"version": 1, "installs": {}}
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("installs"), dict):
        raise ValueError(f"Unsupported Antigravity install receipts; preserved: {path}")
    return path, data


def _write_receipts(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".agy-installs-", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def package(executable: str, home: Path, package: dict, existing: dict | None, *, install: bool, run) -> dict:
    name, source = package["name"], Path(package["package_root"])
    cache = Path.home() / ".gemini/config/plugins" / name
    _safe(cache, Path.home())
    # Native names are case-sensitive, while the destination filesystem may not
    # be. A missing name match must never authorize overwriting an occupied path.
    if existing is None and cache.exists():
        return {"status": "needs_action", "message": "Antigravity destination already exists without a matching registration; preserved. Resolve the conflicting installation in agy"}
    receipt_path, receipts = _receipts(home)
    key = str(cache)
    receipt = receipts["installs"].get(key)
    expected = _snapshot(source)
    if existing:
        if (not isinstance(receipt, dict) or not isinstance(receipt.get("source"), str)
                or Path(receipt["source"]).resolve() != source.resolve()
                or receipt.get("record") != existing.get("record")
                or not existing.get("record") or existing["record"].get("source") != "antigravity"):
            return {"status": "needs_action", "message": "Existing Antigravity plugin is not tracked by this home; preserved. Keep it or uninstall it with agy before retrying"}
        actual = _snapshot(cache)
        if actual != receipt.get("files"):
            return {"status": "needs_action", "message": "Installed Antigravity files changed outside setup; preserved. Resolve the edits before retrying"}
        if actual == expected:
            return {"status": "ready", "message": "Already installed", "path": str(cache)}
    if not install:
        return {"status": "needs_action", "message": "Antigravity plugin is absent or stale; rerun setup"}

    run(executable, "plugin", "validate", str(source), cwd=home)
    if existing:
        # Older CLI installs overlay files; native removal avoids retaining deleted skills.
        run(executable, "plugin", "uninstall", name, cwd=home)
    run(executable, "plugin", "install", str(source), cwd=home)
    verified = [row for row in inventory(executable, home, run) if row["name"] == name]
    if (len(verified) != 1 or not verified[0]["enabled"] or not verified[0].get("record")
            or verified[0]["record"].get("source") != "antigravity"):
        raise ValueError("Antigravity install completed but a single enabled registration could not be verified")
    actual = _snapshot(cache)
    if not expected or actual != expected:
        raise ValueError("Antigravity installed files differ from the complete source package; inspect the native installation")
    receipts["installs"][key] = {"source": str(source.resolve()), "record": verified[0]["record"], "files": actual}
    _write_receipts(receipt_path, receipts)
    return {"status": "updated" if existing else "ready", "message": "Installation verified; start a new session", "path": str(cache)}
