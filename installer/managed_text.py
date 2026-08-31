"""Managed instruction and host-configuration text transforms."""

from __future__ import annotations

import json
import os
import re
from pathlib import PurePath
from typing import NamedTuple

from .packages import (
    FORK_ARRIVAL_CLAUSE,
    ROLE_INSTRUCTIONS,
    _role_description,
    frontmatter_field,
    host_legal_frontmatter,
)
from .foundation import (
    CLAUDE_MAX_TOOL_USE_CONCURRENCY,
    CLAUDE_SETTINGS_SCHEMA,
    CODEX_LIMITS_END,
    CODEX_LIMITS_START,
    CODEX_MAX_DEPTH,
    CODEX_MAX_THREADS,
    GROK_LIMITS_END,
    GROK_LIMITS_START,
    GROK_MAX_CONCURRENT,
    GROK_MAX_DEPTH,
    _AGENTS_DOTTED_LIMIT_RE,
    _AGENTS_LIMIT_RE,
    _AGENTS_TABLE_RE,
    _TOML_TABLE_RE,
    tomllib,
)

# Grok's own key, and the one value choice this installer makes for it: a
# spawn past the concurrent cap waits its turn rather than becoming a lost
# lane, which is what `fail` would make of it. It lives here rather than
# beside GROK_MAX_CONCURRENT in foundation.py only because foundation.py is
# outside this ticket's write scope -- see this file's callers and the
# ticket's Feedback.
GROK_LIMIT_BEHAVIOR = "queue"
_SUBAGENTS_TABLE_RE = re.compile(r"^\s*\[subagents\]\s*(?:#.*)?$")
_SUBAGENTS_LIMIT_RE = re.compile(r"^\s*(?:max_concurrent|max_depth|limit_behavior)\s*=")
_SUBAGENTS_DOTTED_LIMIT_RE = re.compile(
    r"^\s*subagents\.(?:max_concurrent|max_depth|limit_behavior)\s*="
)

# --- Grok text surfaces --------------------------------------------------
#
# The text of `$GROK_HOME/skills/<name>/SKILL.md` and `agents/<role>.md`. It
# sits here rather than beside its Claude and Codex siblings in
# installer/packages.py because that file measured 483 of its 510
# tracked-source lines before the Grok column arrived and cannot hold the
# group. See the note there.


def render_grok_agent(name: str, profile: dict) -> str:
    """YAML frontmatter, camelCase keys, exactly the fields the one role
    profile table binds. Grok's ``AgentDefinition`` also parses
    ``completionRequirement``, ``capabilityMode``, ``maxTurns`` and
    ``isolation``; none is rendered. ``isolation`` is the pointed omission --
    ``spawn_subagent`` takes it as a native argument, so a ticket carrying
    ``isolation: required`` is established per dispatch, and freezing it per
    role here would answer for every ticket that role will ever run."""

    binding = profile["grok"]
    lines = [
        "---",
        f"name: {binding['subagent_type']}",
        f"description: {json.dumps(_role_description(name))}",
        f"model: {binding['model']}",
        f"effort: {binding['effort']}",
        "---",
        "",
        ROLE_INSTRUCTIONS,
    ]
    return "\n".join(lines) + "\n"


def grok_legal_frontmatter(frontmatter: str) -> str:
    """Grok skill frontmatter from the rendered host adapter."""

    return host_legal_frontmatter(frontmatter, host="grok")


def grok_role_adapter_body(name: str, role: str, profile: dict, lib_skill_md) -> str:
    """Explicit Grok dispatch gate for one role-bearing named skill.

    The Codex gate rewritten against Grok's own dispatch tool. Grok has no
    adapter-level role binding to state this natively (see
    ``grok_legal_frontmatter``), so a role-bearing name that says nothing runs
    inline in whatever context resolved it. This body is the binding."""

    if profile["role"] != role:
        raise ValueError(
            f"cannot render {name}: declared role {role} does not match "
            f"resolved profile role {profile['role']}"
        )
    return (
        f"`{name}` requires the matching role `orch-{role}`. If this context "
        f"is already that established child, read {lib_skill_md} and follow it exactly. Execute "
        "the exact named skill directly; never redispatch it. Otherwise root "
        "must call spawn_subagent with subagent_type "
        f"`{profile['grok']['subagent_type']}`, passing the "
        "emitted launch prompt and exact named skill; refuse execution when that "
        "matching role child is missing or mismatched; there is no inline "
        f"fallback.\n\n{FORK_ARRIVAL_CLAUSE}\n"
    )


def grok_skill_text(frontmatter: str, lib_skill_md, profile: dict | None = None) -> str:
    """The installed Grok skill file, frontmatter and body.

    The body names its canonical library body by an explicit read instruction
    and never by an ``@`` include: Grok does not expand ``@``, so an included
    body arrives as a literal path and the canonical text never loads. A
    role-bearing name carries the dispatch gate in place of that flat pointer,
    and so needs its profile row."""

    role = frontmatter_field(frontmatter, "role")
    head = grok_legal_frontmatter(frontmatter) + "\n"
    if role in ("planner", "worker"):
        name = frontmatter_field(frontmatter, "name")
        if profile is None:
            raise ValueError(f"cannot render Grok skill {name}: role {role} needs its profile row")
        return head + grok_role_adapter_body(name, role, profile, lib_skill_md)
    return head + f"Read {lib_skill_md} and follow it exactly.\n"


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


def _marked_span(text: str, start_marker: str, end_marker: str):
    """Locate the one managed block. ``(lines, start_i, end_i)``, or ``None``
    when neither marker is present. Duplicate, unbalanced and inverted pairs
    raise -- both removals below share this one reading."""

    lines = text.splitlines(keepends=True)
    starts = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == start_marker]
    ends = [i for i, line in enumerate(lines) if line.rstrip("\r\n") == end_marker]
    if not starts and not ends:
        return None
    if len(starts) != 1 or len(ends) != 1 or starts[0] > ends[0]:
        raise ValueError(f"invalid managed block markers in target file ({start_marker})")
    return lines, starts[0], ends[0]


def without_marked_block(text: str, start_marker: str, end_marker: str) -> str:
    span = _marked_span(text, start_marker, end_marker)
    if span is None:
        return text
    lines, start_i, end_i = span
    return "".join(lines[:start_i] + lines[end_i + 1 :])


def without_owned_block(text: str, start_marker: str, end_marker: str, owned) -> str:
    """``without_marked_block`` for a file the target's own host also edits.

    There the marker pair is not a safe identity for what the installer wrote.
    A TOML editor appends a table at the end of the *document body*, and a
    trailing END comment is trivia after that body, so the appended table
    lands inside the span -- observed on ``$GROK_HOME/config.toml``, where
    grok adds ``[marketplace]`` between the markers within 0.2s of any
    subcommand. Lifting the span whole would delete the host's own key.

    The installer writes its lines first and contiguously, so ownership is
    read as that leading run: every line from the BEGIN marker down that
    ``owned`` claims, blank lines carrying no TOML meaning passed over.
    Everything from the first line ``owned`` disclaims survives verbatim --
    including a line that looks owned but sits under a table the host
    appended, where it is the host's key and not the installer's."""

    span = _marked_span(text, start_marker, end_marker)
    if span is None:
        return text
    lines, start_i, end_i = span
    body = lines[start_i + 1 : end_i]
    foreign = next(
        (i for i, line in enumerate(body) if line.strip() and not owned(line)), len(body)
    )
    return "".join(lines[:start_i] + body[foreign:] + lines[end_i + 1 :])


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


class _LimitBlock(NamedTuple):
    """One host's managed limit block in its own TOML config.

    Both hosts own a fixed set of keys inside one table of a file the user
    also writes, fenced by markers so a reinstall replaces its own block
    instead of appending a second one. Only the table, the keys, the markers
    and the refusal wording differ -- so the merge below has one owner."""

    table: str
    settings: tuple
    start: str
    end: str
    table_re: object
    limit_re: object
    dotted_limit_re: object
    parse_label: str
    merge_label: str


def _toml_scalar(value) -> str:
    """A TOML literal for an int or a string. ``json.dumps`` agrees with TOML
    on both, and disagreeing quietly is what a hand-rolled quote would risk."""

    return json.dumps(value)


def _limit_block_owns(spec: _LimitBlock, line: str) -> bool:
    """Whether this block's own render wrote ``line`` -- its keys bare under
    the table, or dotted above the first one. Nothing else inside the markers
    is the installer's, whoever put it there."""

    return bool(spec.limit_re.match(line) or spec.dotted_limit_re.match(line))


def _without_limit_block(text: str, spec: _LimitBlock) -> str:
    return without_owned_block(
        text, spec.start, spec.end, lambda line: _limit_block_owns(spec, line)
    )


def _render_limit_block(text: str, spec: _LimitBlock, toml_module) -> tuple[str, dict]:
    cleaned = _without_limit_block(text, spec)
    had_block = cleaned != text
    if toml_module is not None:
        try:
            parsed = toml_module.loads(cleaned)
        except toml_module.TOMLDecodeError as error:
            raise ValueError(f"invalid {spec.parse_label} TOML: {error}") from error
    else:
        parsed = {}
    table = parsed.get(spec.table, {}) if isinstance(parsed, dict) else {}
    previous = {
        f"{spec.table}.{key}": table.get(key) if isinstance(table, dict) else None
        for key, _value in spec.settings
    }

    lines = cleaned.splitlines(keepends=True)
    table_i = next(
        (i for i, line in enumerate(lines) if spec.table_re.match(line.rstrip("\r\n"))), None
    )
    if table_i is not None:
        section_end = next(
            (i for i in range(table_i + 1, len(lines)) if _TOML_TABLE_RE.match(lines[i].rstrip("\r\n"))),
            len(lines),
        )
        section = [line for line in lines[table_i + 1 : section_end] if not spec.limit_re.match(line)]
        block = [f"{spec.start}\n"]
        block += [f"{key} = {_toml_scalar(value)}\n" for key, value in spec.settings]
        block.append(f"{spec.end}\n")
        updated = "".join(lines[: table_i + 1] + block + section + lines[section_end:])
    else:
        first_table = next(
            (i for i, line in enumerate(lines) if _TOML_TABLE_RE.match(line.rstrip("\r\n"))), len(lines)
        )
        top_level = [line for line in lines[:first_table] if not spec.dotted_limit_re.match(line)]
        # This branch writes a blank line after its block; removing the block
        # leaves that separator behind, and reading it back as the user's own
        # is what made a reinstall prepend one more blank line every time,
        # without bound. So take back exactly the one this branch wrote, and
        # only when there was a block to remove -- a first install has no
        # separator of its own out there, and the blank lines it finds above
        # the first table are the user's to keep.
        if had_block and top_level and not top_level[-1].strip():
            top_level.pop()
        if not any(line.strip() for line in top_level):
            top_level = []
        if top_level and top_level[-1].strip():
            top_level.append("\n")
        block = [f"{spec.start}\n"]
        block += [f"{spec.table}.{key} = {_toml_scalar(value)}\n" for key, value in spec.settings]
        block.append(f"{spec.end}\n")
        if first_table < len(lines):
            block.append("\n")
        updated = "".join(top_level + block + lines[first_table:])

    if toml_module is not None:
        try:
            toml_module.loads(updated)
        except toml_module.TOMLDecodeError as error:
            raise ValueError(f"could not merge {spec.merge_label}: {error}") from error
    details = {
        "settings": {f"{spec.table}.{key}": value for key, value in spec.settings},
        "previous": previous,
        # False below 3.11: the merge above ran, but nothing parsed the file
        # before or after it. The caller warns rather than letting an
        # unchecked merge read like a checked one.
        "toml_checked": toml_module is not None,
    }
    return updated, details


_CODEX_LIMIT_BLOCK = _LimitBlock(
    table="agents",
    settings=(("max_threads", CODEX_MAX_THREADS), ("max_depth", CODEX_MAX_DEPTH)),
    start=CODEX_LIMITS_START,
    end=CODEX_LIMITS_END,
    table_re=_AGENTS_TABLE_RE,
    limit_re=_AGENTS_LIMIT_RE,
    dotted_limit_re=_AGENTS_DOTTED_LIMIT_RE,
    parse_label="Codex config",
    merge_label="Codex agent limits",
)

_GROK_LIMIT_BLOCK = _LimitBlock(
    table="subagents",
    settings=(
        ("max_concurrent", GROK_MAX_CONCURRENT),
        ("max_depth", GROK_MAX_DEPTH),
        ("limit_behavior", GROK_LIMIT_BEHAVIOR),
    ),
    start=GROK_LIMITS_START,
    end=GROK_LIMITS_END,
    table_re=_SUBAGENTS_TABLE_RE,
    limit_re=_SUBAGENTS_LIMIT_RE,
    dotted_limit_re=_SUBAGENTS_DOTTED_LIMIT_RE,
    parse_label="Grok config",
    merge_label="Grok subagent limits",
)


def render_codex_agent_limits(text: str, toml_module=tomllib) -> tuple[str, dict]:
    return _render_limit_block(text, _CODEX_LIMIT_BLOCK, toml_module)


def render_grok_subagent_limits(text: str, toml_module=tomllib) -> tuple[str, dict]:
    """The managed ``[subagents]`` block in ``$GROK_HOME/config.toml``.

    User scope is the whole story: a project ``.grok/config.toml`` honours only
    ``mcp_servers``, ``plugins``, ``permission`` and ``mcp.max_output_bytes``,
    so these three limits have no project-local equivalent to install."""

    return _render_limit_block(text, _GROK_LIMIT_BLOCK, toml_module)


def without_codex_agent_limits(text: str) -> str:
    """The uninstall side of ``render_codex_agent_limits``: the two keys go,
    and whatever Codex appended between the markers stays.

    Its Grok twin below is the one whose host was caught appending a table in
    there, and this reads the same way for the same reason: nothing makes a
    marker pair a deed to a file the host itself edits. Both go through
    ``_without_limit_block`` so neither can drift back to a span lift."""

    return _without_limit_block(text, _CODEX_LIMIT_BLOCK)


def without_grok_subagent_limits(text: str) -> str:
    """The uninstall side of ``render_grok_subagent_limits``: the three keys
    go, and whatever grok appended between the markers stays.
    ``without_owned_block`` carries why the markers alone cannot say."""

    return _without_limit_block(text, _GROK_LIMIT_BLOCK)
