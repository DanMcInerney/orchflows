"""The commands behind a package's run.py: preflight, smoke, quick, full, resume, rescore, grade and compare.

Exit codes: 0 every planned unit is terminal; 1 harness error; 2 refused (changed bytes, a held owner lock, a
staging leak, an invalid suite or card); 3 stopped by the deadline or launch budget with units not launched;
4 interrupted (usage limit or Ctrl-C), resumable.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import traceback
from pathlib import Path

from . import adapters, identity, records, runner, selfcheck, shapes, stage
from . import suite as suites
from .launch import run_capped
from .runner import HARNESS, INTERRUPTED, OK, REFUSED, STOPPED, Refused
from .schedule import Busy, LedgerError, OwnerLock

PROVISION_SECONDS = 1800


def _seconds(value) -> str:
    if value is None:
        return "unknown"
    return f"{value:.1f} s" if value < 10 else f"{value:.0f} s" if value < 120 else f"{value / 60:.1f} min"


def _rate(value) -> str:
    return "n/a" if value is None else f"{value:.3g}"


def _provision(commands: list, cwd: Path, problems: list) -> list[dict]:
    done = []
    with tempfile.TemporaryDirectory(prefix="benchkit-provision-") as scratch:
        for number, command in enumerate(commands):
            outcome = run_capped(command, cwd=cwd, stdout=Path(scratch) / f"{number}.out", stderr=Path(scratch) / f"{number}.err",
                                 timeout=PROVISION_SECONDS)
            done.append({"command": command, "status": outcome.status, "exit_code": outcome.exit_code,
                         "seconds": round(outcome.seconds, 1)})
            if outcome.status != "completed":
                tail = (Path(scratch) / f"{number}.err").read_text(encoding="utf-8", errors="replace").strip()[-300:]
                problems.append(f"provision {' '.join(command)}: {outcome.status} ({outcome.reason}) {tail}".rstrip())
    return done


def preflight(root: Path, args) -> int:
    """Validate the package, provision its environments once, run the selfchecks and show the plan. No model calls."""
    suite, problems = suites.read(root)
    notes = []
    report = {"package": str(root), "problems": problems, "notes": notes}
    card = root / "card.json"
    if card.is_file():
        try:
            problems += shapes.claims_problems(records.read_json(card))
        except ValueError as error:
            problems.append(f"card.json: {error}")
    else:
        notes.append("card.json is absent; a delivered package carries one")
    agent = None
    if suite is not None and args.agent:
        try:
            agent = adapters.resolve(args.agent, root)
        except adapters.AgentError as error:
            problems.append(str(error))
    elif suite is not None and not (root / "adapters").is_dir():
        notes.append("adapters/ is absent; a delivered package carries at least one solver adapter")
    for folder in sorted((root / "adapters").iterdir()) if (root / "adapters").is_dir() else []:
        if folder.is_dir() and not (folder / "run_agent.py").is_file():
            notes.append(f"adapters/{folder.name} has no run_agent.py")
    if suite is not None:
        problems += suites.staging_problems(list(suite.tasks.values()))
        tasks = suites.select(suite, args.profile)
        repeats = suites.repeats_for(suite, args.profile)
        report["plan"] = suites.plan(suite, tasks, repeats, jobs=suite.concurrency, deadline=suite.deadline_seconds)
        if suite.launch_budget is not None and suite.launch_budget < report["plan"]["planned_attempts"]:
            notes.append(f"launch_budget {suite.launch_budget} is below the {report['plan']['planned_attempts']} planned attempts")
        if suite.launch_budget is None:
            notes.append("suite.json declares no launch_budget")
        longest = max(report["plan"]["attempt_caps_seconds"].values())
        if suite.deadline_seconds is not None and suite.deadline_seconds < longest:
            notes.append(f"deadline_seconds {suite.deadline_seconds:g} is below the longest attempt cap {longest:g}: such attempts never start")
    if problems:
        print("preflight refused:\n  " + "\n  ".join(problems))
        return REFUSED
    report["provision"] = _provision(suite.provision, root, problems)
    if problems:
        print("preflight refused:\n  " + "\n  ".join(problems))
        return REFUSED
    report["observed_versions"] = identity.observe(suite.observe, root)
    with tempfile.TemporaryDirectory(prefix="benchkit-preflight-") as scratch:
        report["selfcheck"] = selfcheck.run(Path(scratch))
    _print_preflight(suite, report, agent, args.profile)
    if args.report:
        records.write_json(Path(args.report), report)
    return OK if all(check["passed"] for check in report["selfcheck"]["checks"]) else HARNESS


def _print_preflight(suite, report, agent, profile):
    plan = report["plan"]
    low, high = (_seconds(f(plan["attempt_caps_seconds"].values())) for f in (min, max))
    print(f"package {suite.name}: {len(suite.tasks)} tasks; the {profile} profile" + (f" with agent {agent.spec}" if agent else ""))
    print(f"planned attempts: {plan['planned_attempts']} ({len(plan['tasks'])} tasks x {plan['repeats']} repeats), "
          f"concurrency {plan['jobs']}, per-attempt cap {low if low == high else f'{low} to {high}'}")
    print(f"estimated wall time {_seconds(plan['estimated_wall_seconds'])}, upper bound {_seconds(plan['wall_upper_bound_seconds'])}"
          + (f" (deadline {_seconds(plan['deadline_seconds'])})" if plan["deadline_seconds"] else " (no deadline)"))
    spend = plan["estimated_spend_usd"]
    print(f"estimated spend {'unknown' if spend is None else f'${spend:.2f}'}: an estimate only, the kit caps launches and time, not spend")
    print(f"launch budget {plan['launch_budget'] if plan['launch_budget'] is not None else 'none declared'}, "
          f"transient retry budget {plan['transient_retry_budget']}")
    for command, seen in report["observed_versions"].items():
        print(f"observed {command}: {seen.splitlines()[0] if seen else '(no output)'}")
    checks = report["selfcheck"]["checks"]
    print(f"selfcheck: {sum(c['passed'] for c in checks)}/{len(checks)} passed on {report['selfcheck']['platform']}")
    for check in checks:
        print(f"  {'ok  ' if check['passed'] else 'FAIL'} {check['name']}: {check['detail']}")
    for note in report["notes"]:
        print(f"note: {note}")


def _finish(result: runner.Result, out: Path) -> int:
    summary = result.summary
    counts, overall = summary["counts"], summary["overall"]
    print(f"{summary['run']['profile']}: {counts['scored']}/{counts['planned']} units scored, {counts['passed']} passed, "
          f"{counts['unscored']} unscored; full_success_rate {_rate(overall['full_success_rate'])}, "
          f"mean_credit {_rate(overall['mean_credit'])}; wall {_seconds(summary['run']['wall_seconds'])}")
    print(f"state: {result.state}; summary at {out / 'summary.json'}")
    if result.code in (STOPPED, INTERRUPTED):
        by = counts["by_status"]
        print(f"{by['not-launched']} units not launched, {by['canceled'] + by['interrupted']} canceled or interrupted; "
              f"continue with: python run.py resume --output {out}")
    return result.code


def run_profile(root: Path, args) -> int:
    suite = suites.load(root)
    band = None
    if args.stop_band:
        low, high = args.stop_band
        if not 0 <= low <= high <= 1 or not 0 < args.level < 1:
            raise Refused("--stop-band needs 0 <= LOW <= HIGH <= 1 and --level in (0, 1)")
        band = (low, high, args.level)
    only = [name for name in args.tasks.split(",") if name] if args.tasks else None
    return _finish(runner.start(suite, args.output, args.agent, profile=args.command, repeats=args.repeats, jobs=args.jobs,
                                deadline=args.deadline, only=only, stop_band=band), Path(args.output).resolve())


def resume(root: Path, args) -> int:
    return _finish(runner.resume(suites.load(root), args.output, jobs=args.jobs, deadline=args.deadline), Path(args.output).resolve())


def rescore(root: Path, args) -> int:
    suite, out = suites.load(root), Path(args.output)
    if not (out / "run.json").is_file():
        raise Refused(f"{out} has no run.json; it is not a run directory")
    with OwnerLock(out):
        summary = records.rescore(out, suite, args.jobs)
    counts, overall = summary["counts"], summary["overall"]
    print(f"rescored {out}: {counts['scored']} scored, {counts['passed']} passed; full_success_rate "
          f"{_rate(overall['full_success_rate'])}, mean_credit {_rate(overall['mean_credit'])}; nothing was relaunched")
    return OK


def grade(root: Path, args) -> int:
    suite, source = suites.load(root), Path(args.input)
    if not source.is_dir():
        raise Refused(f"{source} is not a directory")
    rows = records.grade_tree(suite, source, args.jobs)
    if not rows:
        raise Refused(f"no <task-id>/<submission-id>/ directories under {source}")
    records.write_text(Path(args.output), "".join(json.dumps(row) + "\n" for row in rows))
    scored = sum(row["grading_status"] == "scored" for row in rows)
    print(f"graded {len(rows)} submissions into {args.output}: {scored} scored, "
          f"{sum(row['full_success'] is True for row in rows)} full successes")
    return OK


def compare(root: Path, args) -> int:
    try:
        result = records.compare(Path(args.a), Path(args.b), args.metric)
    except ValueError as error:
        raise Refused(str(error)) from None
    text = json.dumps(result, indent=2)
    if args.output:
        records.write_text(Path(args.output), text + "\n")
    print(text)
    return OK


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog="run.py", description="Run, grade and compare this benchmark; see benchkit/INTERFACE.md.")
    sub = top.add_subparsers(dest="command", required=True, metavar="command")

    pre = sub.add_parser("preflight", help="validate the package, provision it, run the selfchecks and show the plan; no model calls")
    pre.add_argument("--agent", help="an agent directory, @reference or @noop, to check")
    pre.add_argument("--profile", choices=shapes.PROFILES, default="full")
    pre.add_argument("--report", help="write the full preflight report here as JSON")
    pre.set_defaults(handler=preflight)

    for name in shapes.PROFILES:
        run = sub.add_parser(name, help=f"run the {name} profile")
        run.add_argument("--agent", required=True, help="an agent directory, @reference or @noop")
        run.add_argument("--output", required=True, help="a new run directory")
        run.add_argument("--repeats", type=int)
        run.add_argument("--jobs", type=int)
        run.add_argument("--deadline", type=float, help="seconds; no attempt starts whose cap would pass it")
        run.add_argument("--tasks", help="comma-separated task ids to run instead of the profile's tasks")
        run.add_argument("--stop-band", type=float, nargs=2, metavar=("LOW", "HIGH"),
                         help="stop a task's remaining repeats once its full-success interval is settled against this band")
        run.add_argument("--level", type=float, default=0.9, help="confidence level for --stop-band")
        run.set_defaults(handler=run_profile)

    cont = sub.add_parser("resume", help="continue a run from its ledger")
    cont.add_argument("--output", required=True)
    cont.add_argument("--jobs", type=int)
    cont.add_argument("--deadline", type=float)
    cont.set_defaults(handler=resume)

    again = sub.add_parser("rescore", help="grade a run's captured workspaces again with the current verifiers")
    again.add_argument("--output", required=True)
    again.add_argument("--jobs", type=int)
    again.set_defaults(handler=rescore)

    only = sub.add_parser("grade", help="grade final workspaces under <input>/<task-id>/<submission-id>/")
    only.add_argument("--input", required=True)
    only.add_argument("--output", required=True, help="JSONL file, one row per submission")
    only.add_argument("--jobs", type=int, default=4)
    only.set_defaults(handler=grade)

    pair = sub.add_parser("compare", help="paired per-task differences between two runs")
    pair.add_argument("--a", required=True)
    pair.add_argument("--b", required=True)
    pair.add_argument("--metric", choices=shapes.PRIMARY, default="full_success_rate")
    pair.add_argument("--output", help="also write the comparison here as JSON")
    pair.set_defaults(handler=compare)
    return top


def main(root: Path, argv: list[str]) -> int:
    """Run one command for the package at `root`; returns the exit code."""
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    args = parser().parse_args(argv)
    try:
        return args.handler(Path(root), args)
    except (Refused, suites.SuiteError, adapters.AgentError, Busy, LedgerError, stage.StagingError,
            identity.IdentityError) as refusal:
        print(f"refused: {refusal}", file=sys.stderr)
        return REFUSED
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return INTERRUPTED
    except Exception:  # noqa: BLE001 - any other failure is a harness error, reported with its traceback
        traceback.print_exc()
        return HARNESS
