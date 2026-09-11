"""Small, conservative updates to user-owned native host concurrency settings."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import tempfile
import tomllib
import uuid


DEFAULT_CONCURRENCY = 15
CODEX_KEY = "max_concurrent_threads_per_session"
CLAUDE_KEY = "CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"


def _positive(value: int) -> None:
    if type(value) is not int or value < 1:
        raise ValueError("Concurrency must be a positive integer")


def _statements(text: str):
    """Find complete TOML statements without mistaking multiline values for keys."""
    start, pending = 0, ""
    for line in text.splitlines(keepends=True):
        pending += line
        try:
            parsed = tomllib.loads(pending)
        except tomllib.TOMLDecodeError:
            continue
        yield start, start + len(pending), pending, parsed
        start += len(pending)
        pending = ""
    if pending:
        raise ValueError("Unsupported TOML layout; move concurrency settings into a [agents] table")


def _codex(text: str, concurrency: int) -> str:
    data = tomllib.loads(text)
    agents = data.get("agents", {})
    if not isinstance(agents, dict):
        raise ValueError("Codex agents must be a table")
    keys = (CODEX_KEY, "max_threads")
    for key in keys:
        if key in agents:
            _positive(agents[key])
    if all(key in agents for key in keys) and agents[keys[0]] != agents[keys[1]]:
        raise ValueError("Conflicting Codex concurrency keys; reconcile max_threads and " + CODEX_KEY)
    if agents.get(CODEX_KEY) == concurrency and "max_threads" not in agents:
        return text

    newline = "\r\n" if "\r\n" in text else "\n"
    scope, edits, found = (), [], set()
    insertion, dotted_insertion = None, None
    for start, end, statement, parsed in _statements(text):
        if statement.lstrip().startswith("["):
            scope, branch = (), parsed
            while isinstance(branch, dict) and len(branch) == 1:
                name, branch = next(iter(branch.items()))
                scope += (name,)
            if isinstance(branch, list):
                scope += ("[]",)
            if scope == ("agents",):
                insertion = end
            continue
        values = parsed if scope == ("agents",) else parsed.get("agents", {}) if scope == () else {}
        if not isinstance(values, dict) or not values:
            continue
        if scope == ():
            # Inline tables require a structural TOML editor; preserve rather than reserialize them.
            if re.match(r"\s*(?:agents|\"agents\"|'agents')\s*=", statement):
                raise ValueError("Unsupported inline agents table; move its settings into [agents] or use --skip-host-config")
            dotted_insertion = start if dotted_insertion is None else dotted_insertion
        for key in keys:
            if key not in values:
                continue
            match = re.match(r"([^=\r\n]*=[ \t]*)([+-]?[0-9][0-9_]*)([ \t]*(?:#[^\r\n]*)?)(\r?\n)?\Z", statement)
            if not match:
                raise ValueError("Unsupported concurrency assignment; use a decimal integer in [agents]")
            found.add(key)
            prefix, _, suffix, ending = match.groups()
            if key == "max_threads" and CODEX_KEY in agents:
                comment = suffix[suffix.index("#"):] if "#" in suffix else ""
                replacement = comment + (ending or "")
            else:
                replacement = prefix.replace("max_threads", CODEX_KEY) + str(concurrency) + suffix + (ending or "")
            edits.append((start, end, replacement))
    if found != {key for key in keys if key in agents}:
        raise ValueError("Unsupported Codex concurrency layout; move settings into [agents]")
    if not found:
        assignment = f"{CODEX_KEY} = {concurrency}{newline}"
        if insertion is not None:
            separator = "" if text[:insertion].endswith("\n") else newline
            edits.append((insertion, insertion, separator + assignment))
        elif dotted_insertion is not None:
            edits.append((dotted_insertion, dotted_insertion, "agents." + assignment))
        else:
            separator = "" if not text else newline if text.endswith("\n") else newline * 2
            edits.append((len(text), len(text), separator + "[agents]" + newline + assignment))
    for start, end, replacement in sorted(edits, reverse=True):
        text = text[:start] + replacement + text[end:]
    expected = dict(agents, **{CODEX_KEY: concurrency})
    expected.pop("max_threads", None)
    if tomllib.loads(text) != dict(data, agents=expected):
        raise ValueError("Codex update would alter unrelated settings; file preserved")
    return text


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _claude(text: str, concurrency: int) -> str:
    def invalid_constant(value):
        raise ValueError("Invalid JSON constant: " + value)

    data = json.loads(text, object_pairs_hook=_unique_object, parse_constant=invalid_constant) if text else {}
    if not isinstance(data, dict) or ("env" in data and not isinstance(data["env"], dict)):
        raise ValueError("Claude settings and env must be JSON objects")
    env = data.setdefault("env", {})
    if CLAUDE_KEY in env and (not isinstance(env[CLAUDE_KEY], str) or not re.fullmatch(r"[0-9]+", env[CLAUDE_KEY]) or int(env[CLAUDE_KEY]) < 1):
        raise ValueError("Claude concurrency must be a positive integer string")
    if env.get(CLAUDE_KEY) == str(concurrency):
        return text
    env[CLAUDE_KEY] = str(concurrency)
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _read(path: Path) -> bytes | None:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError(f"Host config must be an ordinary file; preserved: {path}")
    return path.read_bytes()


def prepare_host_configs(concurrency: int = DEFAULT_CONCURRENCY) -> list[dict]:
    """Validate both files before setup mutates anything; never expose config bodies in reports."""
    _positive(concurrency)
    plans = []
    for host, variable, default, filename, transform, setting in (
        ("codex", "CODEX_HOME", ".codex", "config.toml", _codex, "agents." + CODEX_KEY),
        ("claude", "CLAUDE_CONFIG_DIR", ".claude", "settings.json", _claude, "env." + CLAUDE_KEY),
    ):
        configured = os.environ.get(variable)
        directory = Path(configured).expanduser() if configured else Path.home() / default
        path = directory.resolve() / filename
        original = _read(path)
        try:
            text = original.decode("utf-8") if original is not None else ""
            if host == "claude" and original is not None and not text.strip():
                raise ValueError("Existing Claude settings are empty, not a JSON object")
            updated = transform(text, concurrency).encode("utf-8")
        except (UnicodeError, ValueError) as exc:
            raise ValueError(f"Host configuration preserved at {path}: {exc}") from exc
        plans.append({"host": host, "path": path, "setting": setting, "value": concurrency,
                      "original": original, "updated": updated})
    return plans


def _replace(plan: dict) -> str | None:
    path, original, updated = plan["path"], plan["original"], plan["updated"]
    if _read(path) != original:
        raise ValueError(f"Host configuration changed during setup; rerun after reviewing: {path}")
    if original == updated:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".orchflows.lock")
    # Serialize other installer runs. Host editors do not share this lock; check bytes again before replacement.
    with lock.open("x"):
        pass
    stage, backup = None, None
    try:
        handle, name = tempfile.mkstemp(prefix="." + path.name + ".orchflows-", dir=path.parent)
        stage = Path(name)
        with os.fdopen(handle, "wb") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        if original is not None:
            mode = stat.S_IMODE(path.stat().st_mode)
            stage.chmod(mode)
            backup = path.with_name(path.name + ".orchflows-" + uuid.uuid4().hex + ".bak")
            descriptor = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(original)
                stream.flush()
                os.fsync(stream.fileno())
            backup.chmod(mode)
        if _read(path) != original:
            raise ValueError(f"Host configuration changed during setup; file preserved: {path}")
        if original is None:
            os.link(stage, path)  # Atomic creation that cannot overwrite a file another process just created.
        else:
            os.replace(stage, path)
        return str(backup) if backup else None
    except (OSError, ValueError) as exc:
        if backup is not None and backup.exists():
            raise ValueError(f"{exc}; original backup retained at {backup}") from exc
        raise
    finally:
        if stage is not None and stage.exists():
            stage.chmod(stat.S_IREAD | stat.S_IWRITE)
            stage.unlink()
        lock.unlink()


def apply_host_configs(plans: list[dict]) -> tuple[dict, list[str]]:
    results, issues = {}, []
    for plan in plans:
        report = {key: plan[key] for key in ("setting", "value")}
        report["path"] = str(plan["path"])
        try:
            report["backup"] = _replace(plan)
            report["status"] = "unchanged" if plan["original"] == plan["updated"] else "created" if plan["original"] is None else "updated"
        except (OSError, ValueError) as exc:
            report["status"] = "unavailable"
            issues.append(f"Could not configure {plan['host']} concurrency at {plan['path']}: {exc}")
        results[plan["host"]] = report
    return results, issues
