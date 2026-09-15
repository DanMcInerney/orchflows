"""Set each host's user concurrency settings; unrelated content is untouched or the file is preserved."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import tempfile
import tomllib
import uuid


CODEX_KEY = "max_threads"
CLAUDE_KEY = "CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"
ZCODE_KEY = "maxConcurrency"
HEADER = r"(?m)^(\[agents\][ \t]*(?:#[^\r\n]*)?)(?=\r?\n|\Z)"


def _codex(text: str, concurrency: int) -> str:
    data = tomllib.loads(text)
    agents = data.get("agents", {})
    if not isinstance(agents, dict):
        raise ValueError("Codex [agents] must be a table")
    if type(agents.get(CODEX_KEY)) is int and agents[CODEX_KEY] == concurrency:
        return text
    newline = "\r\n" if "\r\n" in text else "\n"
    assignment = f"{CODEX_KEY} = {concurrency}"
    if CODEX_KEY in agents:
        updated = re.sub(rf"(?m)^([ \t]*{CODEX_KEY}[ \t]*=[ \t]*)[^ \t\r\n#]+", lambda m: m[1] + str(concurrency), text, count=1)
    elif re.search(HEADER, text):
        updated = re.sub(HEADER, lambda m: m[1] + newline + assignment, text, count=1)
    else:
        separator = "" if not text else newline if text.endswith("\n") else newline * 2
        updated = text + separator + "[agents]" + newline + assignment + newline
    parsed = tomllib.loads(updated)
    if (parsed != {**data, "agents": {**agents, CODEX_KEY: concurrency}}
            or type(parsed["agents"][CODEX_KEY]) is not int):
        raise ValueError(f"unsupported layout; set [agents] {CODEX_KEY} yourself or pass --skip-host-config")
    return updated


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _claude(text: str, concurrency: int) -> str:
    def invalid_constant(value: str):
        raise ValueError(f"Invalid JSON constant: {value}")

    data = json.loads(text, object_pairs_hook=_unique_object, parse_constant=invalid_constant) if text.strip() else {}
    if not isinstance(data, dict) or not isinstance(data.get("env", {}), dict):
        raise ValueError("Claude settings and env must be JSON objects")
    env = data.setdefault("env", {})
    if env.get(CLAUDE_KEY) == str(concurrency):
        return text
    env[CLAUDE_KEY] = str(concurrency)
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _zcode(text: str, concurrency: int) -> str:
    def invalid_constant(value: str):
        raise ValueError(f"Invalid JSON constant: {value}")

    data = json.loads(text, object_pairs_hook=_unique_object, parse_constant=invalid_constant) if text.strip() else {}
    if not isinstance(data, dict) or not isinstance(data.get("toolConcurrency", {}), dict):
        raise ValueError("ZCode settings and toolConcurrency must be JSON objects")
    limits = data.setdefault("toolConcurrency", {})
    if type(limits.get(ZCODE_KEY)) is int and limits[ZCODE_KEY] == concurrency:
        return text
    limits[ZCODE_KEY] = concurrency
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _read(path: Path) -> bytes | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError(f"Host config must be an ordinary file; preserved: {path}")
    return path.read_bytes()


def prepare_host_configs(concurrency: int = 15) -> list[dict]:
    """Validate both files before setup mutates anything."""
    if type(concurrency) is not int or concurrency < 1:
        raise ValueError("Concurrency must be a positive integer")
    plans = []
    for host, variable, default, filename, transform, setting in (
        ("codex", "CODEX_HOME", ".codex", "config.toml", _codex, "agents." + CODEX_KEY),
        ("claude", "CLAUDE_CONFIG_DIR", ".claude", "settings.json", _claude, "env." + CLAUDE_KEY),
        ("zcode", None, ".zcode/cli", "config.json", _zcode, "toolConcurrency." + ZCODE_KEY),
    ):
        configured = os.environ.get(variable) if variable else None
        path = (Path(configured).expanduser() if configured else Path.home() / default).resolve() / filename
        original = _read(path)
        try:
            updated = transform(original.decode("utf-8-sig") if original is not None else "", concurrency).encode("utf-8")
        except (UnicodeError, ValueError) as exc:
            raise ValueError(f"Host configuration preserved at {path}: {exc}") from exc
        plans.append({"host": host, "path": path, "setting": setting, "value": concurrency, "original": original, "updated": updated})
    return plans


def _replace(plan: dict) -> str | None:
    """Back up the original beside it, then replace atomically; a change since planning preserves the file."""
    path, original, updated = plan["path"], plan["original"], plan["updated"]
    if original == updated:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".orchflows.lock")
    if lock.is_symlink():
        raise ValueError(f"Lock is a link; preserved: {lock}")
    with lock.open("x"):
        pass
    stage = backup = None
    try:
        if _read(path) != original:
            raise ValueError(f"Host configuration changed during setup; preserved: {path}")
        handle, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
        stage = Path(name)
        with os.fdopen(handle, "wb") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        if original is not None:
            mode = stat.S_IMODE(path.stat().st_mode)
            stage.chmod(mode)
            backup = path.with_name(f"{path.name}.orchflows-{uuid.uuid4().hex}.bak")
            backup.write_bytes(original)
            backup.chmod(mode)
        if _read(path) != original:
            raise ValueError(f"Host configuration changed during setup; preserved: {path}")
        if original is None:
            os.link(stage, path)  # Creating a new config must not replace a concurrent save.
        else:
            os.replace(stage, path)
        return str(backup) if backup else None
    except BaseException:
        if backup is not None:
            backup.unlink(missing_ok=True)
        raise
    finally:
        if stage is not None and stage.exists():
            stage.chmod(stat.S_IREAD | stat.S_IWRITE)
            stage.unlink()
        lock.unlink()


def apply_host_configs(plans: list[dict]) -> tuple[dict, list[str]]:
    results, issues = {}, []
    for plan in plans:
        report = {"setting": plan["setting"], "value": plan["value"], "path": str(plan["path"])}
        try:
            report["backup"] = _replace(plan)
            report["status"] = "unchanged" if plan["original"] == plan["updated"] else "created" if plan["original"] is None else "updated"
        except (OSError, ValueError) as exc:
            report["status"] = "unavailable"
            issues.append(f"Could not configure {plan['host']} concurrency at {plan['path']}: {exc}")
        results[plan["host"]] = report
    return results, issues
