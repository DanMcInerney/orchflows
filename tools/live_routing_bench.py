#!/usr/bin/env python3
"""Run an opt-in, usage-consuming routing benchmark over two adapter sets.

benchmarks/routing/README.md's decision rule gates one question: does Claude ship every skill
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
from tools.live_routing_bench_support.execution import (  # noqa: E402
    INSTALLER,
    _case_command,
    _install_command,
    _isolated_env,
    _make_repo,
    _render_install,
    _run_case,
    run_benchmark,
)
from tools.live_routing_bench_support import execution as _execution  # noqa: E402
from tools.live_routing_bench_support.grading import (  # noqa: E402
    ANSWER_LINE_RE,
    BY_NAME_RE,
    ERROR,
    FIX_SKILL,
    ROUTE_CLASSES,
    SKILL_TOOLS,
    TEMPLATE_RE,
    TICKET_SKILLS,
    UNROUTED,
    _classify_bash,
    _classify_read,
    _classify_skill,
    _decide,
    _named_in,
    _skill_name,
    _stream_cost,
    grade_transcript,
    route_class,
)
from tools.live_routing_bench_support.reporting import (  # noqa: E402
    _rate,
    format_table,
    summarize,
)

DEFAULT_CASES = REPO_ROOT / "benchmarks" / "routing" / "cases.json"
ADAPTER_SETS = ("all", "four")
ADAPTER_CHOICES = ADAPTER_SETS + ("both",)
CASE_FIELDS = ("id", "prompt", "expected", "note")
ROLE_SKILL_ROUTES = {}

_install_command_impl = _install_command
_run_benchmark_impl = run_benchmark


def _sync_execution_seams() -> None:
    _execution.INSTALLER = INSTALLER
    _execution._render_install = _render_install
    _execution._make_repo = _make_repo
    _execution._run_case = _run_case
    _execution.grade_transcript = grade_transcript


def _install_command(adapter_set: str) -> list:
    _sync_execution_seams()
    return _install_command_impl(adapter_set)


def run_benchmark(**kwargs) -> list:
    _sync_execution_seams()
    return _run_benchmark_impl(**kwargs)


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
        required_role = case.get("required_role")
        required_skill = case.get("required_skill")
        if bool(required_role) != bool(required_skill):
            raise ValueError(
                f"routing case {case['id']!r} must pair required_role and required_skill"
            )
        required_pair = ROLE_SKILL_ROUTES.get(route_class(expected))
        if required_pair and (required_role, required_skill) != required_pair:
            raise ValueError(
                f"routing case {case['id']!r} requires role/skill {required_pair!r}"
            )
    return cases


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
