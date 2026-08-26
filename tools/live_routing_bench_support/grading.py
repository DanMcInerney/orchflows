"""Transcript grading for the live routing benchmark."""

from __future__ import annotations

import re

from tools.live_claude_profiles import _json_events

ROUTE_CLASSES = (
    "answer", "single", "graph", "spec", "doctor", "fix", "build", "named",
)
UNROUTED = "unrouted"
# A session that failed before it could route -- an API error, an
# unauthenticated CLI -- is neither a route nor a misroute; the first
# live run graded "Not logged in" as `answer` and read 100% misroute.
ERROR = "error"
ROLE_AGENT_TYPES = {"planner": "orch-planner", "worker": "orch-worker"}

# The host block's routing table, read as transcript evidence.
ROUTING_SKILLS = {
    "orch-frontier": "single",
    "orch-decompose": "graph",
    "orch-spec": "spec",
}
# Compatibility export for the live harness facade; values now span the three
# executable graph shapes instead of naming one route class.
TICKET_SKILLS = frozenset(ROUTING_SKILLS)
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
    if skill in ROUTING_SKILLS:
        return ROUTING_SKILLS[skill]
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
    normalized = command.replace("\\", "/")
    if "tickets.py new" in normalized:
        return "single"
    if "install.py doctor" in normalized:
        return "doctor"
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


def _tool_blocks(event: dict):
    if event.get("type") != "assistant":
        return
    for block in (event.get("message") or {}).get("content") or []:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            yield block


def _execution_conformance(
    events: list, expected_role: str | None, expected_skill: str | None
) -> dict:
    """Grade the native child edge separately from the route classification.

    The route says *what* was selected.  This result says whether a substantive
    exact-named skill was actually executed by the one matching root child.
    Only one helper layer below a planner is accepted, and that helper may not
    execute the planner's primary skill.
    """

    if expected_role is None and expected_skill is None:
        return {
            "status": "not_applicable",
            "reasons": [],
            "primary_skill_executions": 0,
            "helper_launches": 0,
        }
    if expected_role not in ROLE_AGENT_TYPES or not expected_skill:
        raise ValueError("expected_role and expected_skill must name a planner/worker skill pair")

    expected_agent_type = ROLE_AGENT_TYPES[expected_role]
    root_launches = {}
    launch_depths = {}
    helper_launches = []
    skill_uses = []

    for event in events:
        parent_id = event.get("parent_tool_use_id")
        context_depth = launch_depths.get(parent_id, 0 if parent_id is None else None)
        for block in _tool_blocks(event):
            name = block.get("name")
            block_input = block.get("input") or {}
            tool_id = block.get("id")
            if name in {"Agent", "Task"} and tool_id:
                agent_type = block_input.get("subagent_type")
                if parent_id is None:
                    root_launches[tool_id] = agent_type
                    launch_depths[tool_id] = 1
                elif context_depth is not None:
                    launch_depths[tool_id] = context_depth + 1
                    helper_launches.append((tool_id, agent_type, context_depth + 1))
            elif name in SKILL_TOOLS:
                skill = _skill_name(block_input)
                if skill:
                    skill_uses.append((parent_id, context_depth, skill))

    reasons = []
    matching = [tool_id for tool_id, agent_type in root_launches.items()
                if agent_type == expected_agent_type]
    mismatched = [tool_id for tool_id, agent_type in root_launches.items()
                  if agent_type != expected_agent_type]
    if not matching:
        reasons.append("missing_matching_role_child")
    elif len(matching) > 1:
        reasons.append("multiple_matching_role_children")
    if mismatched:
        reasons.append("mismatched_root_role_child")

    primary_parent = matching[0] if len(matching) == 1 else None
    direct_primary = sum(
        parent_id == primary_parent and skill == expected_skill
        for parent_id, _depth, skill in skill_uses
    )
    root_primary = sum(
        parent_id is None and skill == expected_skill
        for parent_id, _depth, skill in skill_uses
    )
    all_child_primary = sum(
        parent_id is not None and skill == expected_skill
        for parent_id, _depth, skill in skill_uses
    )
    if root_primary:
        reasons.append("root_primary_skill_execution")
    if direct_primary != 1:
        reasons.append("missing_exact_primary_skill" if direct_primary == 0
                       else "duplicate_primary_skill")
    if all_child_primary > direct_primary:
        reasons.append("primary_skill_redispatched")

    primary_helpers = [launch for launch in helper_launches if launch[2] == 2]
    if expected_role != "planner" and primary_helpers:
        reasons.append("worker_helper_topology_unsupported")
    if any(depth > 2 for _tool_id, _agent_type, depth in helper_launches):
        reasons.append("nested_helper_topology_unsupported")

    return {
        "status": "failed" if reasons else "passed",
        "reasons": reasons,
        "primary_skill_executions": all_child_primary,
        "root_primary_skill_executions": root_primary,
        "helper_launches": len(primary_helpers),
    }


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


def grade_transcript(
    stdout: str,
    *,
    expected_role: str | None = None,
    expected_skill: str | None = None,
) -> dict:
    events = list(_json_events(stdout))
    observed, first_event, turns = _decide(events)
    execution_conformance = _execution_conformance(
        events, expected_role, expected_skill
    )
    if observed == UNROUTED and execution_conformance["status"] == "passed":
        observed = _classify_skill(expected_skill)
        first_event = f"ChildSkill({expected_skill})"
    return {
        "observed": observed,
        "first_event": first_event,
        "turns": turns,
        "cost_usd": _stream_cost(events),
        "execution_conformance": execution_conformance,
    }
