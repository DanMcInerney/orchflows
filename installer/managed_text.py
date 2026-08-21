"""Managed instruction and host-configuration text transforms."""

from __future__ import annotations

import json
import os
from pathlib import PurePath

from .foundation import (
    CLAUDE_MAX_TOOL_USE_CONCURRENCY,
    CLAUDE_SETTINGS_SCHEMA,
    CODEX_LIMITS_END,
    CODEX_LIMITS_START,
    CODEX_MAX_DEPTH,
    CODEX_MAX_THREADS,
    _AGENTS_DOTTED_LIMIT_RE,
    _AGENTS_LIMIT_RE,
    _AGENTS_TABLE_RE,
    _TOML_TABLE_RE,
    tomllib,
)

def render_host_block(
    template_text: str,
    bin_dir: PurePath,
    docs_dir: PurePath,
    skills_dir: PurePath,
    lib_dir: PurePath,
    python_interpreter: str,
) -> str:
    if os.name == "nt":
        def powershell_token(value: object) -> str:
            return "'" + str(value).replace("'", "''") + "'"

        friction_commands = "    PowerShell: & " + " ".join(
            powershell_token(value)
            for value in (
                python_interpreter,
                bin_dir / "friction.py",
                "<what happened>",
                "<what was expected or missing>",
            )
        )
    else:
        import shlex

        friction_commands = "    POSIX: " + shlex.join(
            [
                python_interpreter,
                str(PurePath(bin_dir) / "friction.py"),
                "<what happened>",
                "<what was expected or missing>",
            ]
        )
    return (
        template_text.replace("{{ORCH_BIN}}", str(bin_dir))
        .replace("{{ORCH_DOCS}}", str(docs_dir))
        .replace("{{ORCH_SKILLS}}", str(skills_dir))
        .replace("{{ORCH_LIB}}", str(lib_dir))
        .replace("{{PYTHON}}", python_interpreter)
        .replace("{{FRICTION_COMMANDS}}", friction_commands)
    )


def upsert_marked_block(text: str, block_text: str, start_marker: str, end_marker: str) -> str:
    if not block_text.endswith("\n"):
        block_text += "\n"
    if not text:
        return block_text
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == start_marker]
    ends = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == end_marker]
    if len(starts) > 1 or len(ends) > 1:
        raise ValueError(f"duplicate managed block markers in target file ({start_marker})")
    if len(starts) != len(ends):
        raise ValueError(f"unbalanced managed block markers in target file ({start_marker})")
    if not starts:
        if text.endswith("\n\n") or text.endswith("\r\n\r\n"):
            separator = ""
        elif text.endswith("\n") or text.endswith("\r\n"):
            separator = "\n"
        else:
            separator = "\n\n"
        return text + separator + block_text
    start_i, end_i = starts[0], ends[0]
    if start_i > end_i:
        raise ValueError(f"managed block markers are out of order in target file ({start_marker})")
    return "".join(lines[:start_i] + [block_text] + lines[end_i + 1 :])


def without_marked_block(text: str, start_marker: str, end_marker: str) -> str:
    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == start_marker]
    ends = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == end_marker]
    if not starts and not ends:
        return text
    if len(starts) != 1 or len(ends) != 1 or starts[0] > ends[0]:
        raise ValueError(f"invalid managed block markers in target file ({start_marker})")
    return "".join(lines[: starts[0]] + lines[ends[0] + 1 :])


def upsert_import_line(text: str, import_line: str, legacy_start_marker: str, legacy_end_marker: str) -> tuple[str, str]:
    """Idempotently ensure ``import_line`` appears as its own line in ``text``,
    after stripping any legacy inline marker block left by an older install.
    Returns ``(updated_text, install_action)`` where ``install_action`` is one
    of ``created-file`` | ``migrated-from-block`` | ``added-import`` |
    ``already-present``."""

    existed = bool(text)
    had_legacy_block = legacy_start_marker in text and legacy_end_marker in text
    cleaned = without_marked_block(text, legacy_start_marker, legacy_end_marker)
    if any(line.rstrip("\r\n") == import_line for line in cleaned.splitlines()):
        return cleaned, "already-present"
    if not cleaned:
        updated = import_line + "\n"
    elif cleaned.endswith("\n\n") or cleaned.endswith("\r\n\r\n"):
        updated = cleaned + import_line + "\n"
    elif cleaned.endswith("\n") or cleaned.endswith("\r\n"):
        updated = cleaned + "\n" + import_line + "\n"
    else:
        updated = cleaned + "\n\n" + import_line + "\n"
    action = "migrated-from-block" if had_legacy_block else ("added-import" if existed else "created-file")
    return updated, action


def render_claude_settings(text: str) -> tuple[str, dict]:
    if text.strip():
        try:
            settings = json.loads(text)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid Claude settings JSON: {error}") from error
        if not isinstance(settings, dict):
            raise ValueError("Claude settings must be a JSON object")
    else:
        settings = {"$schema": CLAUDE_SETTINGS_SCHEMA}
    env = settings.setdefault("env", {})
    if not isinstance(env, dict):
        raise ValueError("Claude settings 'env' must be a JSON object")
    key = "CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY"
    previous = env.get(key)
    env[key] = str(CLAUDE_MAX_TOOL_USE_CONCURRENCY)
    details = {"setting": f"env.{key}", "previous": previous, "installed": env[key]}
    return json.dumps(settings, indent=2, ensure_ascii=False) + "\n", details


def render_codex_agent_limits(text: str, toml_module=tomllib) -> tuple[str, dict]:
    cleaned = without_marked_block(text, CODEX_LIMITS_START, CODEX_LIMITS_END)
    if toml_module is not None:
        try:
            parsed = toml_module.loads(cleaned)
        except toml_module.TOMLDecodeError as error:
            raise ValueError(f"invalid Codex config TOML: {error}") from error
    else:
        parsed = {}
    agents = parsed.get("agents", {}) if isinstance(parsed, dict) else {}
    previous = {
        "agents.max_threads": agents.get("max_threads") if isinstance(agents, dict) else None,
        "agents.max_depth": agents.get("max_depth") if isinstance(agents, dict) else None,
    }

    lines = cleaned.splitlines(keepends=True)
    agents_i = next((i for i, line in enumerate(lines) if _AGENTS_TABLE_RE.match(line.rstrip("\r\n"))), None)
    if agents_i is not None:
        section_end = next(
            (i for i in range(agents_i + 1, len(lines)) if _TOML_TABLE_RE.match(lines[i].rstrip("\r\n"))),
            len(lines),
        )
        section = [line for line in lines[agents_i + 1 : section_end] if not _AGENTS_LIMIT_RE.match(line)]
        block = [
            f"{CODEX_LIMITS_START}\n",
            f"max_threads = {CODEX_MAX_THREADS}\n",
            f"max_depth = {CODEX_MAX_DEPTH}\n",
            f"{CODEX_LIMITS_END}\n",
        ]
        updated = "".join(lines[: agents_i + 1] + block + section + lines[section_end:])
    else:
        first_table = next(
            (i for i, line in enumerate(lines) if _TOML_TABLE_RE.match(line.rstrip("\r\n"))), len(lines)
        )
        top_level = [line for line in lines[:first_table] if not _AGENTS_DOTTED_LIMIT_RE.match(line)]
        if top_level and top_level[-1].strip():
            top_level.append("\n")
        block = [
            f"{CODEX_LIMITS_START}\n",
            f"agents.max_threads = {CODEX_MAX_THREADS}\n",
            f"agents.max_depth = {CODEX_MAX_DEPTH}\n",
            f"{CODEX_LIMITS_END}\n",
        ]
        if first_table < len(lines):
            block.append("\n")
        updated = "".join(top_level + block + lines[first_table:])

    if toml_module is not None:
        try:
            toml_module.loads(updated)
        except toml_module.TOMLDecodeError as error:
            raise ValueError(f"could not merge Codex agent limits: {error}") from error
    details = {
        "settings": {
            "agents.max_threads": CODEX_MAX_THREADS,
            "agents.max_depth": CODEX_MAX_DEPTH,
        },
        "previous": previous,
        # False below 3.11: the merge above ran, but nothing parsed the file
        # before or after it. The caller warns rather than letting an
        # unchecked merge read like a checked one.
        "toml_checked": toml_module is not None,
    }
    return updated, details
