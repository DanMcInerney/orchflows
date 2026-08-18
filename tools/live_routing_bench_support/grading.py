"""Transcript grading for the live routing benchmark."""

from __future__ import annotations

import re

from tools.live_claude_profiles import _json_events

ROUTE_CLASSES = ("answer", "ticket", "fix", "build", "named")
UNROUTED = "unrouted"
# A session that failed before it could route -- an API error, an
# unauthenticated CLI -- is neither a route nor a misroute; the first
# live run graded "Not logged in" as `answer` and read 100% misroute.
ERROR = "error"

# The host block's routing table, read as transcript evidence.
TICKET_SKILLS = frozenset({"orch-frontier", "orch-spec"})
FIX_SKILL = "fix"
BUILD_SKILL = "orch-build"
SKILL_TOOLS = frozenset({"Skill", "SlashCommand"})
ANSWER_LINE_RE = re.compile(r"^ROUTE:\s*answer", re.IGNORECASE | re.MULTILINE)
# Under `--claude-adapters four` an unadapted name has no adapter to invoke,
# and the block's fallback is to read the library's own entry for it. That
# read *is* the route; grading it as no route gave `four` a structural
# misroute floor on every `named:` case however well the session behaved.
BY_NAME_RE = re.compile(r"/by-name/([a-z0-9][a-z0-9-]*)/SKILL\.md", re.IGNORECASE)
# The same name reached the other way: a template is instantiated from its
# own directory under the installed library.
TEMPLATE_RE = re.compile(r"/compositions/([a-z0-9][a-z0-9-]*)")


def route_class(route: str) -> str:
    """`named:evolve` is one case of the class `named`; the rest are their
    own class."""

    return route.split(":", 1)[0]


def _skill_name(block_input: dict) -> str | None:
    """The name a Skill or SlashCommand event invokes.

    `SlashCommand` carries the whole typed line in `command`, arguments
    included, so the first whitespace token is the name and the rest is what
    was said to it. Reading the line whole graded `/orch-build foo` as
    `named:orch-build foo` -- a route class no case can expect.
    """

    for key in ("skill", "name", "command"):
        value = block_input.get(key)
        if isinstance(value, str) and value.strip():
            return value.split()[0].strip().lstrip("/")
    return None


def _classify_skill(skill: str) -> str:
    if skill in TICKET_SKILLS:
        return "ticket"
    if skill == FIX_SKILL:
        return "fix"
    if skill == BUILD_SKILL:
        return "build"
    return f"named:{skill}"


def _named_in(text: str) -> str | None:
    """The library name a path in `text` reaches, or None.

    The host block hands the session an installed library path, and on
    Windows that path arrives with backslashes; separators are normalized so
    one rule reads both hosts.
    """

    normalized = text.replace("\\", "/")
    match = BY_NAME_RE.search(normalized)
    if match:
        return match.group(1)
    if "instantiate" in normalized:
        match = TEMPLATE_RE.search(normalized)
        if match:
            return match.group(1)
    return None


def _classify_bash(command: str) -> str | None:
    if "tickets.py new" in command.replace("\\", "/"):
        return "ticket"
    name = _named_in(command)
    return _classify_skill(name) if name else None


def _classify_read(block_input: dict) -> str | None:
    """A read of the library's own entry for a name, from any input value."""

    for value in block_input.values():
        if isinstance(value, str):
            match = BY_NAME_RE.search(value.replace("\\", "/"))
            if match:
                return _classify_skill(match.group(1))
    return None


def _stream_cost(events: list) -> float | None:
    cost = None
    for event in events:
        for key in ("total_cost_usd", "cost_usd"):
            value = event.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                cost = float(value)
    return cost


def _decide(events: list) -> tuple[str, str | None, int]:
    """The first route-bearing event of the parent session decides the route.

    Subagent events (`parent_tool_use_id` set) are a child's work, never the
    session's own routing decision, and are skipped.
    """

    turns = 0
    saw_text = False
    for event in events:
        if event.get("type") == "result" and event.get("is_error"):
            return ERROR, f"result(is_error: {str(event.get('result', ''))[:120]})", turns
        if event.get("type") != "assistant" or event.get("parent_tool_use_id") is not None:
            continue
        if event.get("is_api_error_message") or event.get("error"):
            return ERROR, f"assistant(error: {str(event.get('error', ''))[:120]})", turns
        turns += 1
        for block in (event.get("message") or {}).get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text = block.get("text", "")
                saw_text = saw_text or bool(text.strip())
                if ANSWER_LINE_RE.search(text):
                    return "answer", "text(ROUTE: answer)", turns
                continue
            if block.get("type") != "tool_use":
                continue
            name = block.get("name")
            block_input = block.get("input") or {}
            if name in SKILL_TOOLS:
                skill = _skill_name(block_input)
                if skill:
                    return _classify_skill(skill), f"Skill({skill})", turns
            elif name == "Bash":
                command = str(block_input.get("command", ""))
                observed = _classify_bash(command)
                if observed:
                    return observed, f"Bash({command[:120]})", turns
            else:
                observed = _classify_read(block_input)
                if observed:
                    return observed, f"{name}({observed})", turns
    # A read is not a route. Six of the seven `answer` cases are settled by
    # a file the block tells the session to open, so requiring an untouched
    # transcript failed the cases that most needed one; what makes an answer
    # an answer is that nothing route-bearing happened before it.
    if saw_text:
        return "answer", "text(final assistant text, no route-bearing tool use)", turns
    return UNROUTED, None, turns


def grade_transcript(stdout: str) -> dict:
    events = list(_json_events(stdout))
    observed, first_event, turns = _decide(events)
    return {
        "observed": observed,
        "first_event": first_event,
        "turns": turns,
        "cost_usd": _stream_cost(events),
    }
