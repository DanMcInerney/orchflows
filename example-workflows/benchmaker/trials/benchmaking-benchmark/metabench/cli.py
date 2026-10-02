"""`python -m metabench <command>`, run from the benchmarking-benchmark directory.

Commands (plan B.7): material fetch, pool generate, slice build, confirm, verify, refpkg assemble, selfcheck,
build, report. Model calls happen only with `--llm` (confirm, verify) and in `build` without `--plan`.
Exit codes: 0 done (and every gate passed, for verify), 1 a gate failed or a check did not pass, 2 refused or
a bad argument.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import registry, store

REFUSED = 2


def common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--store", help="the private store (default: METABENCH_STORE, else ~/.bmk-eval/meta)")
    parser.add_argument("--out-root", help="where package runs write their output (default ~/bmk-meta-out)")
    parser.add_argument("--work-root", help="where builds work (default ~/bmk-meta-work)")


def meta_task(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--meta-task", required=True, choices=sorted(registry.META_TASKS))


def build_parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog="python -m metabench", description="The benchmarking benchmark: meta-verify benchmarks.")
    sub = top.add_subparsers(dest="command", required=True, metavar="command")

    material = sub.add_parser("material", help="real material for a meta-task").add_subparsers(dest="action", required=True)
    fetch = material.add_parser("fetch", help="download the material into the store (network, no model calls)")
    meta_task(fetch)
    common(fetch)

    pools = sub.add_parser("pool", help="pools of members").add_subparsers(dest="action", required=True)
    generate = pools.add_parser("generate", help="write a pool and its ORDER.json into the store (no model calls)")
    meta_task(generate)
    generate.add_argument("--include-llm", action="store_true", help="add the paid LLM members")
    generate.add_argument("--dev", action="store_true", help="the committed development pool instead of a held-out one")
    common(generate)

    slices = sub.add_parser("slice", help="the private reference slice").add_subparsers(dest="action", required=True)
    build_slice = slices.add_parser("build", help="generate the slice package from held-out material")
    meta_task(build_slice)
    common(build_slice)

    confirm = sub.add_parser("confirm", help="run a pool on the slice; settle LLM pairs and killability")
    meta_task(confirm)
    confirm.add_argument("--pool")
    confirm.add_argument("--slice")
    confirm.add_argument("--llm", action="store_true", help="also run the LLM members (paid)")
    confirm.add_argument("--jobs", type=int, default=3)
    common(confirm)

    verify = sub.add_parser("verify", help="meta-verify a delivered package against a pool")
    meta_task(verify)
    verify.add_argument("--package", required=True, help="the delivered benchmark-run directory")
    verify.add_argument("--pool")
    verify.add_argument("--jobs", type=int, default=3)
    verify.add_argument("--llm", action="store_true", help="also run the LLM members (paid)")
    verify.add_argument("--build", default="reference", help="label for the report: a build id, reference or mutant:<op>")
    verify.add_argument("--arm", default="reference", help="label for the report: benchmaker, plain, reference or mutant")
    verify.add_argument("--member-seconds", type=float, help="wall cap per run.py invocation (default: suite deadline + 300 s)")
    common(verify)

    refpkg = sub.add_parser("refpkg", help="reference packages").add_subparsers(dest="action", required=True)
    assemble = refpkg.add_parser("assemble", help="generate a reference package and copy the kit in")
    assemble.add_argument("meta_task", choices=sorted(registry.META_TASKS))
    assemble.add_argument("--out", required=True)
    assemble.add_argument("--instances", default="offline", help="offline, public or a directory of instances")
    common(assemble)

    selfcheck = sub.add_parser("selfcheck", help="mutation matrix over the reference package (zero model calls)")
    meta_task(selfcheck)
    selfcheck.add_argument("--full", action="store_true", help="every mutant instead of the quick set")
    common(selfcheck)

    build = sub.add_parser("build", help="a builder session for one arm")
    meta_task(build)
    build.add_argument("--arm", required=True, choices=("benchmaker", "plain"))
    build.add_argument("--model", required=True)
    build.add_argument("--effort", required=True)
    build.add_argument("--budget", required=True, choices=("small", "standard"))
    build.add_argument("--plan", action="store_true", help="print the commands, workspace and budget; launch nothing")
    build.add_argument("--resume", metavar="SESSION", help="continue a build whose session hit a usage limit")
    common(build)

    report = sub.add_parser("report", help="compare meta-verification reports")
    report.add_argument("--runs", nargs="+", required=True, help="run ids, run directories or report.json files")
    common(report)
    return top


def resolve_store(args, *, create: bool = True) -> Path:
    return store.resolve(args.store, out_root=Path(args.out_root) if args.out_root else None,
                         work_root=Path(args.work_root) if args.work_root else None, create=create)


def out_root(args) -> Path | None:
    return Path(args.out_root) if args.out_root else None


def cmd_material(args) -> int:
    from . import material

    print(json.dumps(material.fetch(args.meta_task, resolve_store(args)), indent=2, default=str))
    return 0


def cmd_pool(args) -> int:
    from . import pool

    st = store.Store(resolve_store(args))
    pool_id, path = pool.generate(args.meta_task, st, dev=args.dev, include_llm=args.include_llm)
    order = pool.read_order(st, args.meta_task, pool_id)
    print(f"pool {pool_id}: {len(order['members'])} members, {len(order['known_pairs'])} known pairs, "
          f"{len(order['unconfirmed'])} unconfirmed; {path}")
    return 0


def cmd_slice(args) -> int:
    from . import refpkg

    slice_id, package = refpkg.build_slice(args.meta_task, store.Store(resolve_store(args)))
    print(f"slice {slice_id}: {package}")
    return 0


def cmd_confirm(args) -> int:
    from . import confirm

    root = resolve_store(args)
    result = confirm.confirm(args.meta_task, root, pool_id=args.pool, slice_id=args.slice, llm=args.llm, jobs=args.jobs,
                             out_root=out_root(args))
    promoted = sum(p["outcome"] == "confirmed" for p in result["pairs"])
    print(f"confirmed {promoted} pairs on slice {result['slice']}; {result['members_run']} members run; see "
          f"{store.Store(root).pool(args.meta_task, result['pool']) / 'confirmations.json'}")
    return 0


def cmd_verify(args) -> int:
    from . import verify
    from .metrics import gates_pass

    result = verify.verify(args.meta_task, Path(args.package), resolve_store(args), pool_id=args.pool, jobs=args.jobs,
                           llm=args.llm, out_root=out_root(args), build=args.build, arm=args.arm, cap=args.member_seconds)
    for name, gate in result["gates"].items():
        print(f"{name}: {'pass' if gate.get('pass') else 'FAIL'}" + ("" if gate.get("pass") else f" {gate.get('reasons') or ''}"))
    return 0 if gates_pass(result["gates"]) else 1


def cmd_refpkg(args) -> int:
    from . import refpkg

    path = refpkg.assemble(args.meta_task, Path(args.out), instances=args.instances,
                           store_root=resolve_store(args) if args.instances == "public" else None)
    print(f"assembled {args.meta_task} reference package at {path}")
    return 0


def cmd_selfcheck(args) -> int:
    try:
        from . import selfvalidate
    except ImportError:
        print("selfcheck needs metabench/selfvalidate.py (the mutation self-validation module), which is not in this tree",
              file=sys.stderr)
        return REFUSED
    result = selfvalidate.run(args.meta_task, quick=not args.full, store=resolve_store(args))
    print(json.dumps(result, indent=2, default=str))
    return 0 if isinstance(result, dict) and result.get("pass", True) else 1


def find_build(work_root: Path, session: str) -> Path:
    for path in sorted(work_root.glob("*/build.json")):
        if any(run.get("session_id") == session for run in store.read_json(path).get("runs", [])):
            return path.parent
    raise store.StoreError(f"no build under {work_root} has session {session}")


def cmd_build(args) -> int:
    from . import builders

    work_root = Path(args.work_root) if args.work_root else store.default_work_root()
    sources = builders.default_sources(args.meta_task, resolve_store(args, create=False))
    if args.plan:
        print(builders.render_plan(builders.plan(args.meta_task, args.arm, args.model, args.effort, args.budget, work_root,
                                                 sources=sources)))
        return 0
    if args.resume:
        build_dir = find_build(work_root, args.resume)
    else:
        work_root.mkdir(parents=True, exist_ok=True)
        build_dir = builders.prepare(args.meta_task, args.arm, args.budget, work_root, sources=sources)
    record = builders.run(build_dir, model=args.model, effort=args.effort, resume=args.resume)
    print(builders.render_run(record))
    print(json.dumps(builders.builder_summary(build_dir)))
    return 0 if record["status"] == "completed" else 1


def load_report(item: str, root: Path) -> dict:
    path = Path(item)
    for candidate in (path, path / "report.json", store.Store(root).run(item) / "report.json"):
        if candidate.is_file():
            return {"source": item, **store.read_json(candidate)}
    raise store.StoreError(f"no report for {item}")


def cell(value) -> str:
    return "n/a" if value is None else f"{value:.2f}" if isinstance(value, float) else str(value)


def cmd_report(args) -> int:
    root = resolve_store(args, create=False)
    head = ["run", "arm", "build", "gates", "hackable", "pair accuracy", "kill rate", "contrast recall", "TPR", "TNR", "contradicted"]
    print("| " + " | ".join(head) + " |\n|" + " --- |" * len(head))
    for item in args.runs:
        r = load_report(item, root)
        m, g = r.get("metrics", {}), r.get("gates", {})
        row = [r["source"], r.get("arm"), r.get("build"), "pass" if all(x.get("pass") for x in g.values()) else "FAIL",
               (m.get("M1_cheaters") or {}).get("hackable_task_ratio"), (m.get("M2_order") or {}).get("pair_accuracy"),
               (m.get("M3_kill") or {}).get("rate"), (m.get("M4_contrasts") or {}).get("resolution_recall"),
               (m.get("M6_verifier") or {}).get("tpr"), (m.get("M6_verifier") or {}).get("tnr"),
               len((m.get("M9_claims") or {}).get("contradicted") or [])]
        print("| " + " | ".join(cell(x) for x in row) + " |")
    return 0


HANDLERS = {"material": cmd_material, "pool": cmd_pool, "slice": cmd_slice, "confirm": cmd_confirm, "verify": cmd_verify,
            "refpkg": cmd_refpkg, "selfcheck": cmd_selfcheck, "build": cmd_build, "report": cmd_report}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.command](args)
    except (store.StoreError, KeyError, ValueError, FileExistsError, OSError) as error:
        print(f"refused: {error}", file=sys.stderr)
        return REFUSED
