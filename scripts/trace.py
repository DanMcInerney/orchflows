#!/usr/bin/env python3
"""Session trace extractor. Stdlib-only, read-only, cross-platform.

Normalizes one Claude Code session or one Codex thread tree into a
single ordered trace: ``request``, ``narration``, ``skill_invocation``,
``subagent``, and ``tool_call`` events, plus durations and token counts
where the source data carries them. ``request`` and ``narration`` carry
``text`` (user prompt / agent's user-visible explanation), clipped at
``TEXT_CLIP`` with a ``truncated`` flag; harness-injected text
(system reminders, command wrappers) is never a request. The trace also
carries top-level ``runs_touched``: run ids harvested from run-state
paths in tool calls -- the sink's and, for a session predating the
migration, the repository's -- the join key to run state. Never writes under
``~/.claude`` or
``~/.codex``. Never raises past ``main`` and always exits 0 -- host
schemas drift, and nothing downstream may depend on this parser being
perfectly current (see ``schema_confidence`` and ``parse_errors``
below).

Degradation bar: a malformed or drifted input line is skipped and
recorded in ``parse_errors``; it never aborts extraction. Records with
an unrecognized-but-valid shape (harness bookkeeping, new event kinds)
are counted as cleanly parsed but simply produce no event -- schema
drift that adds new record kinds is not an error, only a record kind we
fail to interpret at all (bad JSON, or a message/response_item missing
its required shape) is.

Usage:
    trace.py --claude <session.jsonl-or-dir>       -> trace JSON on stdout
    trace.py --codex <rollout.jsonl-or-dir>        -> trace JSON on stdout
    trace.py --claude <path> --mermaid             -> Mermaid flowchart
    trace.py --codex <path> --mermaid              -> Mermaid flowchart

``--claude PATH``: PATH is either the main transcript file (its sibling
directory ``<stem>/subagents/`` is read too, matching the live
``~/.claude/projects/<project>/<session-id>.jsonl`` +
``<session-id>/subagents/`` layout), or a self-contained directory
holding ``main.jsonl`` and ``subagents/``.

``--codex PATH``: PATH is one rollout file (one thread) or a directory
of rollout files (one thread per file; parent/child linked by
``source.subagent.thread_spawn.parent_thread_id``).

Extraction only. Findings belong to the improvement composition to synthesize from
the sink's own streams; this script mines nothing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_SIBLING_DIR = str(Path(__file__).resolve().parent)
if _SIBLING_DIR not in sys.path:
    sys.path.append(_SIBLING_DIR)

if __package__:  # in-repo package imports
    from scripts import trace_render as _trace_render_module
    from scripts.trace_render import (
        CODEX_BOILERPLATE_MARKERS,
        EXIT_CODE_RE,
        HARNESS_TEXT_MARKERS,
        HOST_CLAUDE,
        HOST_CODEX,
        RUN_ID_RE,
        SHELL_COMMAND_RE,
        STATE_ROOT_RE,
        TEXT_CLIP,
        _MERMAID_UNSAFE_RE,
        _clip,
        _duration_ms,
        _empty_trace,
        _finalize,
        _mermaid_label,
        _mermaid_sanitize,
        _parse_ts,
        _read_lines,
        _runs_touched,
        _tag_file_errors,
        _text_fields,
        render_mermaid,
    )
    from scripts.trace_claude import (
        _claude_tool_command,
        _handle_claude_assistant_line,
        _handle_claude_user_line,
        _process_claude_file,
        _resolve_claude_exit,
        extract_claude,
    )
    from scripts.trace_codex import (
        _extract_codex_command,
        _extract_codex_exit,
        _handle_codex_response_item,
        _is_codex_boilerplate,
        _process_codex_file,
        extract_codex,
    )
else:  # installed flat beside trace.py
    import trace_render as _trace_render_module
    from trace_render import (
        CODEX_BOILERPLATE_MARKERS,
        EXIT_CODE_RE,
        HARNESS_TEXT_MARKERS,
        HOST_CLAUDE,
        HOST_CODEX,
        RUN_ID_RE,
        SHELL_COMMAND_RE,
        STATE_ROOT_RE,
        TEXT_CLIP,
        _MERMAID_UNSAFE_RE,
        _clip,
        _duration_ms,
        _empty_trace,
        _finalize,
        _mermaid_label,
        _mermaid_sanitize,
        _parse_ts,
        _read_lines,
        _runs_touched,
        _tag_file_errors,
        _text_fields,
        render_mermaid,
    )
    from trace_claude import (
        _claude_tool_command,
        _handle_claude_assistant_line,
        _handle_claude_user_line,
        _process_claude_file,
        _resolve_claude_exit,
        extract_claude,
    )
    from trace_codex import (
        _extract_codex_command,
        _extract_codex_exit,
        _handle_codex_response_item,
        _is_codex_boilerplate,
        _process_codex_file,
        extract_codex,
    )

# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

_clip_impl = _clip
_extract_claude_impl = extract_claude
_extract_codex_impl = extract_codex


def _sync_render_seams() -> None:
    _trace_render_module.TEXT_CLIP = TEXT_CLIP


def _clip(text):
    _sync_render_seams()
    return _clip_impl(text)


def extract_claude(path):
    _sync_render_seams()
    return _extract_claude_impl(path)


def extract_codex(path):
    _sync_render_seams()
    return _extract_codex_impl(path)

def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--claude", metavar="PATH", help="extract a trace from one Claude Code session")
    parser.add_argument("--codex", metavar="PATH", help="extract a trace from one Codex thread tree")
    parser.add_argument("--mermaid", action="store_true", help="render the extracted trace as a Mermaid flowchart")
    return parser


def main(argv=None) -> int:
    _trace_render_module.TEXT_CLIP = TEXT_CLIP
    argv = sys.argv[1:] if argv is None else argv
    # Windows consoles default stdout to a legacy codepage (e.g. cp1252) that
    # cannot encode arbitrary transcript content (emoji, non-Latin text).
    # ensure_ascii keeps JSON output byte-safe regardless; this reconfigure
    # additionally protects the Mermaid text path.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.claude:
            trace = extract_claude(Path(args.claude))
        elif args.codex:
            trace = extract_codex(Path(args.codex))
        else:
            parser.print_usage(sys.stderr)
            return 2
        if args.mermaid:
            sys.stdout.write(render_mermaid(trace))
        else:
            print(json.dumps(trace, ensure_ascii=True, indent=2))
        return 0
    except Exception as exc:  # degradation bar: never crash, never non-zero
        host = HOST_CODEX if args.codex else HOST_CLAUDE
        session_id = Path(args.codex or args.claude or "unknown").stem
        print(json.dumps(_empty_trace(host, session_id, f"unexpected failure: {exc}"), ensure_ascii=True))
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
