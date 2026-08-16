#!/usr/bin/env python3
"""Run an opt-in, usage-consuming routing benchmark over two adapter sets.

SPEC-ticket-set.md section 7.2 gates one decision: does Claude ship every skill
adapter, or only the four both hosts expose? This measures it. For each
adapter set the probe renders an isolated user-scope install into a fresh
temporary home, opens a plain temporary git repository as the session's
working directory -- no AGENTS.md, so the installed host block is the only
thing routing -- and launches one live `claude -p <prompt>` session per
case. It grades the *first* route-bearing event of each transcript against
the route the case expects.

It measures; it never gates. Every run exits 0, whatever the rates say.
The decision rule the rates feed is in benchmarks/routing/README.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.live_claude_profiles import (  # noqa: E402
    _captured_text,
    _claude_command,
    _json_events,
)

DEFAULT_CASES = REPO_ROOT / "benchmarks" / "routing" / "cases.json"
INSTALLER = REPO_ROOT / "install.py"
ADAPTER_SETS = ("all", "four")
ADAPTER_CHOICES = ADAPTER_SETS + ("both",)
ROUTE_CLASSES = ("answer", "ticket", "fix", "build", "named")
CASE_FIELDS = ("id", "prompt", "expected", "note")
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


# --- cases -------------------------------------------------------------


def route_class(route: str) -> str:
    """`named:evolve` is one case of the class `named`; the rest are their
    own class."""

    return route.split(":", 1)[0]


def load_cases(path) -> list:
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"routing cases must be a non-empty list: {path}")
    for case in cases:
        missing = [field for field in CASE_FIELDS if field not in case]
        if missing:
            raise ValueError(f"routing case {case.get('id')!r} is missing: {', '.join(missing)}")
        expected = case["expected"]
        if route_class(expected) not in ROUTE_CLASSES:
            raise ValueError(f"routing case {case['id']!r} expects an unknown route: {expected}")
        if route_class(expected) == "named" and not expected.partition(":")[2].strip():
            raise ValueError(f"routing case {case['id']!r} expects named with no name: {expected}")
    return cases


# --- grading -----------------------------------------------------------


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


# --- isolation ---------------------------------------------------------


def _isolated_env(home: Path) -> dict:
    """Point every root a session or an install could write at ``home``.

    HOME and USERPROFILE move ``Path.home()`` on POSIX and Windows
    respectively; CLAUDE_CONFIG_DIR and CODEX_HOME are the two host
    overrides install.py reads, and ORCHFLOWS_STATE_HOME is the state sink
    -- an inherited value for any of them would send a benchmark run's
    writes into the real home this probe must leave alone.
    """

    env = os.environ.copy()
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["CLAUDE_CONFIG_DIR"] = str(home / ".claude")
    env["CODEX_HOME"] = str(home / ".codex")
    env["ORCHFLOWS_STATE_HOME"] = str(home / ".orchflows" / "state")
    return env


def _install_command(adapter_set: str) -> list:
    return [
        sys.executable,
        str(INSTALLER),
        "--user",
        "--yes",
        "--claude-adapters",
        adapter_set,
    ]


def _render_install(adapter_set: str, home: Path, timeout: int) -> str:
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        _install_command(adapter_set),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_isolated_env(home),
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"install for adapter set {adapter_set!r} failed: {(completed.stderr or '')[-2000:]}"
        )
    return completed.stdout


def _make_repo(path: Path, timeout: int) -> Path:
    """A plain repository with no instruction files of its own, so the only
    thing routing the session is the host block the install just wrote."""

    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "--quiet", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    return path


# --- running -----------------------------------------------------------


def _case_command(claude_invocation: list, prompt: str, max_turns: int) -> list:
    return claude_invocation + [
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--no-session-persistence",
        "--max-turns",
        str(max_turns),
    ]


def _run_case(
    claude_invocation: list, prompt: str, cwd: Path, env: dict, max_turns: int, timeout: int
) -> dict:
    command = _case_command(claude_invocation, prompt, max_turns)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(cwd),
            env=env,
            timeout=timeout,
            check=False,
        )
        stdout, returncode, timed_out = completed.stdout, completed.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout, returncode, timed_out = _captured_text(exc.stdout), 124, True
    graded = grade_transcript(stdout)
    if timed_out:
        # A session killed at the timeout never got to route: it is neither a
        # route nor a misroute, which is what ERROR means here. Grading it
        # `unrouted` put it in the misroute numerator and left `errors` at 0,
        # so the "read no rate while errors is above 0" guard saw nothing.
        graded["observed"] = ERROR
        graded["first_event"] = f"timeout({timeout}s)"
    graded["returncode"] = returncode
    graded["timed_out"] = timed_out
    return graded


def run_benchmark(
    *,
    adapter_sets,
    cases,
    repeat: int,
    max_turns: int,
    timeout: int,
    claude_invocation: list,
    root: Path,
    max_budget_usd: float | None = None,
) -> list:
    records = []
    # What has been spent, across every set and repeat. The bound is money,
    # not case count: one long session is worth many short ones, and the
    # thing an opt-in usage-consuming probe has to be able to stop is the
    # next launch.
    spent = 0.0
    for adapter_set in adapter_sets:
        if max_budget_usd is not None and spent >= max_budget_usd:
            break
        home = Path(root) / f"home-{adapter_set}"
        _render_install(adapter_set, home, timeout)
        env = _isolated_env(home)
        repo = _make_repo(Path(root) / f"repo-{adapter_set}", timeout)
        for index in range(1, repeat + 1):
            for case in cases:
                if max_budget_usd is not None and spent >= max_budget_usd:
                    return records
                graded = _run_case(
                    claude_invocation, case["prompt"], repo, env, max_turns, timeout
                )
                record = {
                    "adapter_set": adapter_set,
                    "case": case["id"],
                    "repeat": index,
                    "expected": case["expected"],
                    "observed": graded["observed"],
                    "match": graded["observed"] == case["expected"],
                    "first_event": graded["first_event"],
                    "turns": graded["turns"],
                    "returncode": graded["returncode"],
                    "timed_out": graded["timed_out"],
                }
                if graded["cost_usd"] is not None:
                    record["cost_usd"] = graded["cost_usd"]
                    spent += graded["cost_usd"]
                records.append(record)
    return records


# --- reporting ---------------------------------------------------------


def _rate(counts: dict) -> float:
    """Misroutes over the sessions that ran.

    A session that failed before it could route is neither a route nor a
    misroute, so it leaves the rate rather than entering its numerator --
    otherwise the rate measures how often the CLI was reachable, which is
    not the question SPEC-ticket-set.md §7.2 asks.
    """

    ran = counts["n"] - counts["errors"]
    return round((ran - counts["matched"]) / ran, 4) if ran > 0 else 0.0


def summarize(records, max_budget_usd: float | None = None) -> dict:
    summary: dict = {}
    for record in records:
        bucket = summary.setdefault(
            record["adapter_set"],
            {"n": 0, "matched": 0, "unrouted": 0, "errors": 0, "cost_usd": 0.0, "by_class": {}},
        )
        by_class = bucket["by_class"].setdefault(
            route_class(record["expected"]), {"n": 0, "matched": 0, "unrouted": 0, "errors": 0}
        )
        for counts in (bucket, by_class):
            counts["n"] += 1
            counts["matched"] += 1 if record["match"] else 0
            counts["unrouted"] += 1 if record["observed"] == UNROUTED else 0
            counts["errors"] += 1 if record["observed"] == ERROR else 0
        bucket["cost_usd"] = round(bucket["cost_usd"] + (record.get("cost_usd") or 0.0), 6)
    spent = sum(bucket["cost_usd"] for bucket in summary.values())
    for bucket in summary.values():
        bucket["misroute_rate"] = _rate(bucket)
        for by_class in bucket["by_class"].values():
            by_class["misroute_rate"] = _rate(by_class)
        if max_budget_usd is not None:
            bucket["max_budget_usd"] = max_budget_usd
            bucket["budget_stopped"] = spent >= max_budget_usd
    return summary


def format_table(summary: dict) -> str:
    lines = [
        f"{'adapter set':<12} {'n':>4} {'matched':>8} {'misroute':>9} {'unrouted':>9} {'errors':>7}  by class"
    ]
    for adapter_set in sorted(summary):
        bucket = summary[adapter_set]
        by_class = " ".join(
            f"{name}={counts['matched']}/{counts['n']}"
            for name, counts in sorted(bucket["by_class"].items())
        )
        lines.append(
            f"{adapter_set:<12} {bucket['n']:>4} {bucket['matched']:>8} "
            f"{bucket['misroute_rate']:>9.3f} {bucket['unrouted']:>9} {bucket['errors']:>7}  {by_class}"
        )
    return "\n".join(lines)


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapters", choices=ADAPTER_CHOICES, default="both")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--max-turns", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument(
        "--max-budget-usd",
        type=float,
        default=None,
        help="Stop launching new sessions once the summed cost_usd passes this.",
    )
    parser.add_argument("--out", default=None, help="Write the full result JSON here.")
    args = parser.parse_args(argv)

    adapter_sets = ADAPTER_SETS if args.adapters == "both" else (args.adapters,)
    cases = load_cases(args.cases)
    claude_invocation = _claude_command()

    # mkdtemp + rmtree(ignore_errors=True), not TemporaryDirectory: on
    # Windows a session's child process can still hold the temp repo when
    # the last case returns, and TemporaryDirectory's cleanup then raises
    # and discards the records a paid run just produced. The directory is
    # scratch; a leftover is cheaper than a lost measurement.
    tmp = tempfile.mkdtemp(prefix="orchflows-routing-bench-")
    try:
        records = run_benchmark(
            adapter_sets=adapter_sets,
            cases=cases,
            repeat=args.repeat,
            max_turns=args.max_turns,
            timeout=args.timeout,
            claude_invocation=claude_invocation,
            root=Path(tmp),
            max_budget_usd=args.max_budget_usd,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    summary = summarize(records, max_budget_usd=args.max_budget_usd)
    print(format_table(summary))
    if args.out:
        payload = {
            "cases": str(args.cases),
            "adapter_sets": list(adapter_sets),
            "repeat": args.repeat,
            "max_turns": args.max_turns,
            "max_budget_usd": args.max_budget_usd,
            "records": records,
            "summary": summary,
        }
        # Bytes, not text: this host's default text write would emit CRLF.
        Path(args.out).write_bytes(
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
    # It measures, it does not gate.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
