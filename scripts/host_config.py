"""Set native concurrency limits; preserve unrelated content and recoverable originals."""

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
SUPPORTED_HOSTS = ("codex", "claude", "zcode", "kimi", "grok")


def _codex(text: str, concurrency: int) -> str:
    return _toml_limit(text, concurrency, "agents", CODEX_KEY)


def _toml_limit(text: str, concurrency: int, table: str, key: str) -> str:
    data = tomllib.loads(text)
    section = data.get(table, {})
    if not isinstance(section, dict):
        raise ValueError(f"[{table}] must be a table")
    if type(section.get(key)) is int and section[key] == concurrency:
        return text
    newline = "\r\n" if "\r\n" in text else "\n"
    assignment = f"{key} = {concurrency}"
    name = re.escape(table)
    header = rf"(?m)^(\[(?:{name}|\"{name}\"|'{name}')\][ \t]*(?:#[^\r\n]*)?)(?=\r?\n|\Z)"
    match = re.search(header, text)
    if key in section:
        if not match:
            raise ValueError(f"unsupported layout; set [{table}] {key} yourself or pass --skip-host-config")
        following = re.search(r"(?m)^[ \t]*\[", text[match.end():])
        end = match.end() + following.start() if following else len(text)
        section_text = re.sub(rf"(?m)^([ \t]*{re.escape(key)}[ \t]*=[ \t]*)[^ \t\r\n#]+",
                              lambda m: m[1] + str(concurrency), text[match.end():end], count=1)
        updated = text[:match.end()] + section_text + text[end:]
    elif match:
        updated = re.sub(header, lambda m: m[1] + newline + assignment, text, count=1)
    else:
        separator = "" if not text else newline if text.endswith("\n") else newline * 2
        updated = text + separator + f"[{table}]" + newline + assignment + newline
    parsed = tomllib.loads(updated)
    if (parsed != {**data, table: {**section, key: concurrency}}
            or type(parsed[table][key]) is not int):
        raise ValueError(f"unsupported layout; set [{table}] {key} yourself or pass --skip-host-config")
    return updated


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _claude(text: str, concurrency: int) -> str:
    return _json_limit(text, str(concurrency), "env", CLAUDE_KEY)


def _zcode(text: str, concurrency: int) -> str:
    return _json_limit(text, concurrency, "toolConcurrency", "maxConcurrency")


def _json_limit(text: str, value: int | str, section: str, key: str) -> str:
    def invalid_constant(value: str):
        raise ValueError(f"Invalid JSON constant: {value}")

    data = json.loads(text, object_pairs_hook=_unique_object, parse_constant=invalid_constant) if text.strip() else {}
    if not isinstance(data, dict) or not isinstance(data.get(section, {}), dict):
        raise ValueError(f"Settings and {section} must be JSON objects")
    values = data.setdefault(section, {})
    if type(values.get(key)) is type(value) and values[key] == value:
        return text
    values[key] = value
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _kimi(text: str, concurrency: int) -> str:
    task = tomllib.loads(text).get("task", {})
    if not isinstance(task, dict):
        raise ValueError("Kimi [task] must be a table")
    updated = _toml_limit(text, concurrency, "background", "max_running_tasks")
    # Newer Kimi versions overlay [task] on the legacy [background] section.
    if "max_running_tasks" in task:
        updated = _toml_limit(updated, concurrency, "task", "max_running_tasks")
    return updated


def _grok(text: str, concurrency: int) -> str:
    agents = tomllib.loads(text).get("subagents", {})
    if not isinstance(agents, dict) or type(agents.get("enabled")) is not bool:
        raise ValueError("Grok requires an explicit [subagents] enabled boolean before tuning; preserve the intended enabled/disabled state")
    return _toml_limit(text, concurrency, "subagents", "max_concurrent")


def _check_override(host: str, concurrency: int) -> None:
    maximum = {"zcode": 2**53 - 1, "kimi": 2**53 - 1, "grok": 2**63 - 1}.get(host)
    if maximum is not None and concurrency > maximum:
        raise ValueError(f"{host} concurrency exceeds its supported integer range")
    variable = {"zcode": "ZCODE_MAX_TOOL_CONCURRENCY", "kimi": "KIMI_CODE_BACKGROUND_MAX_RUNNING_TASKS",
                "grok": "GROK_MAX_CONCURRENT_SUBAGENTS"}.get(host)
    if variable and os.environ.get(variable, "").strip():
        try:
            matches = int(os.environ[variable]) == concurrency
        except ValueError:
            matches = False
        if not matches:
            raise ValueError(f"{variable} overrides {host} concurrency; adjust or unset it before tuning")


def _read(path: Path) -> bytes | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError(f"Host config must be an ordinary file; preserved: {path}")
    return path.read_bytes()


def prepare_host_configs(concurrency: int = 15, hosts: tuple[str, ...] = ("codex", "claude")) -> list[dict]:
    """Validate selected host files before changing them."""
    if type(concurrency) is not int or concurrency < 1:
        raise ValueError("Concurrency must be a positive integer")
    if any(host not in SUPPORTED_HOSTS for host in hosts):
        raise ValueError("No verified concurrency setting for a selected host")
    plans = []
    for host, variable, default, filename, transform, setting in (
        ("codex", "CODEX_HOME", ".codex", "config.toml", _codex, "agents." + CODEX_KEY),
        ("claude", "CLAUDE_CONFIG_DIR", ".claude", "settings.json", _claude, "env." + CLAUDE_KEY),
        ("zcode", None, ".zcode/cli", "config.json", _zcode, "toolConcurrency.maxConcurrency"),
        ("kimi", "KIMI_CODE_HOME", ".kimi-code", "config.toml", _kimi, "background.max_running_tasks"),
        ("grok", "GROK_HOME", ".grok", "config.toml", _grok, "subagents.max_concurrent"),
    ):
        if host not in hosts:
            continue
        _check_override(host, concurrency)
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
