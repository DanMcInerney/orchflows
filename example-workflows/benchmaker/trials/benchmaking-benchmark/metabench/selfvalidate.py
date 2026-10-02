"""Mutation self-validation: the meta-verifier checked against known-good and known-bad benchmarks, at zero model cost.

`run` assembles a meta-task's reference package, meta-verifies it against a scripted pool and asserts the plan's
thresholds, then meta-verifies each mutant of it (`mutate.py`) and asserts that the detection the mutant must trigger
fires. A mutant that is not caught is a finding about the meta-verifier and is reported with the metric that should
have moved and what it showed; assertions are never loosened to make a matrix pass. The kill matrix is written as
JSON and markdown beside the store's selfcheck folder.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import mutate, pool, registry, verify
from . import store as stores

stores.use_kit()

PAIR_ACCURACY_MIN = 0.9
JOBS = 8
PARALLEL = 4
CAP_FACTOR, CAP_FLOOR = 3.0, 60.0   # a capped run gets this many times the slowest member run of the reference
GENERATE_SECONDS = 600
# The scripted pool: member names as `pool.compose` writes them; quick runs the first group, full adds the rest.
CORE = ("oracle", "floor:noop", "floor:empty", "cheater:read_workspace", "cheater:tamper", "ladder:0.15", "ladder:0.7")
MORE = ("ladder:0.4", "ladder:0.4-b", "cheater:read_ancestors")
# Every pool also holds the domain's own content-blind floor (`domain.FLOORS`), which a benchmark that rewards has no headroom.
DEFECTS = {"schedule-nosolver": ("defect:ignore_offsets", "defect:always_infeasible"),
           "logtriage-llm": ("defect:shifted", "heuristic:grep_first_error"),
           "calendar-skill": ("defect:clobber", "defect:claims_done")}
# generate.py arguments for the quick and full package sizes (task ids differ by package; every group is covered).
GENERATE = {
    "schedule-nosolver": {
        True: ["--only", "xz-arch-sync,ch-exec-offsite-prep,ch-sales-qbr,rm-studio-workshop,dw-clinic-huddle,xz-apac-handover"],
        False: ["--only", "xz-arch-sync,xz-apac-handover,ch-exec-offsite-prep,ch-sales-qbr,ch-studio-interviews,dw-clinic-huddle,"
                          "dw-exec-staff,dw-sales-review,nf-last-slot,ed-night-handover,rm-eng-offsite,rm-studio-workshop"]},
    "logtriage-llm": {True: ["--tasks", "6", "--per-repo", "1"], False: ["--tasks", "12", "--per-repo", "2"]},
    "calendar-skill": {
        True: ["--only", "bo-eng-sync,fu-sales-escalation,mp-studio-offsite,mp-all-hands-prep,mp-clinic-review,pd-eng-crunch"],
        False: ["--only", "bo-eng-sync,bo-sales-call,rf-eng-demo,fu-eng-incident,fu-sales-escalation,fu-exec-normal,mp-studio-offsite,"
                          "mp-all-hands-prep,mp-clinic-review,pd-eng-crunch,pd-sales-quarter-end,rf-clinic-training,"
                          "rf-studio-workshop,nf-room-features,bo-studio-review"]},
}
SINGLE_FILE = {"scheduling", "logtriage"}   # the deliverable is one file, so a reachable answer pays out credit


def check(name: str, ok: bool, observed, need: str, required: bool = True) -> dict:
    return {"name": name, "pass": bool(ok), "observed": observed, "need": need, "required": required}


def gate(report: dict, name: str) -> dict:
    return (report.get("gates") or {}).get(name) or {}


def metric(report: dict, name: str) -> dict:
    return (report.get("metrics") or {}).get(name) or {}


def credit(report: dict, member_class: str):
    return (((metric(report, "M1_cheaters").get("credit_by_class") or {}).get(member_class) or {}).get("mean_credit"))


def positive(value) -> bool:
    return isinstance(value, (int, float)) and value > 0


def below(value, limit) -> bool:
    return isinstance(value, (int, float)) and value < limit


# ---------------------------------------------------------------- what the unmutated reference must show

def reference_checks(report: dict) -> list[dict]:
    m2, m3, m6, m9 = (metric(report, name) for name in ("M2_order", "M3_kill", "M6_verifier", "M9_claims"))
    checks = [check(f"{name} passes", gate(report, name).get("pass") is True, gate(report, name).get("reasons") or "pass", "pass")
              for name in ("G1_executability", "G2_reference_and_floor", "crosscheck", "staging")]
    accuracy = m2.get("pair_accuracy")
    checks += [
        check("M2 pair accuracy on constructed pairs", isinstance(accuracy, (int, float)) and accuracy >= PAIR_ACCURACY_MIN,
              {"pair_accuracy": accuracy, "pairs": m2.get("pairs"), "contradicted": m2.get("contradicted")}, f">= {PAIR_ACCURACY_MIN}"),
        check("M3 kill rate on killable defects", bool(m3.get("killable")) and m3.get("killed") == m3.get("killable"),
              {k: m3.get(k) for k in ("killable", "killed", "rate", "excluded_equivalent")}, "all killable defects killed"),
        check("M1 hackable task ratio", metric(report, "M1_cheaters").get("hackable_task_ratio") == 0,
              metric(report, "M1_cheaters").get("hackable_tasks"), "0"),
        check("M6 true positive rate", m6.get("tpr") == 1.0, {"tpr": m6.get("tpr"), "false_rejects": (m6.get("false_rejects") or [])[:3]}, "1"),
        check("M6 true negative rate", m6.get("tnr") == 1.0, {"tnr": m6.get("tnr"), "false_accepts": (m6.get("false_accepts") or [])[:3]}, "1"),
        check("M9 contradicted claims", not m9.get("contradicted"), m9.get("contradicted"), "none")]
    return checks


# ---------------------------------------------------------------- what each mutant must trigger

def pair_collapse(report: dict, required: bool = True) -> dict:
    m2 = metric(report, "M2_order")
    accuracy = m2.get("pair_accuracy")
    return check("M2 pair accuracy falls", below(accuracy, PAIR_ACCURACY_MIN) or bool(m2.get("contradicted")),
                 {"pair_accuracy": accuracy, "contradicted": m2.get("contradicted"), "null_p": m2.get("null_p")},
                 f"< {PAIR_ACCURACY_MIN} or contradicted pairs", required)


def flagged_tasks(m7: dict) -> set:
    """Tasks M7 flags: reference failures, floor credit, flat and inverted tasks."""
    found = set(m7.get("reference_fail") if isinstance(m7.get("reference_fail"), list) else [])
    for key in ("floor_credit", "flat", "inverted"):
        found |= {row["task"] if isinstance(row, dict) else row for row in (m7.get(key) if isinstance(m7.get(key), list) else [])}
    return found


def detections(name: str, report: dict, domain: str, context: dict | None = None) -> list[dict]:
    """The checks that must fire for `name`. `context` carries the unmutated report and the tasks the mutant replaced."""
    context = context or {}
    g1, g2, m1 = gate(report, "G1_executability"), gate(report, "G2_reference_and_floor"), metric(report, "M1_cheaters")
    m6, m7, m9 = metric(report, "M6_verifier"), metric(report, "M7_task_profile"), metric(report, "M9_claims")
    if name == "accepts_empty":
        return [check("G2 floor fails", g2.get("pass") is False, {k: g2.get(k) for k in ("noop_full_success_tasks", "noop_mean_credit")}, "fail"),
                check("M1 noop credit > 0", positive(credit(report, "noop")), credit(report, "noop"), "> 0")]
    if name == "answers_reachable":
        flags = [check("staging gate fails", gate(report, "staging").get("pass") is False,
                       len(gate(report, "staging").get("cheater_findings") or []), "findings")]
        if domain in SINGLE_FILE:
            flags.append(check("M1 read_workspace hackable ratio > 0",
                               positive(m1.get("hackable_task_ratio")) and positive(credit(report, "read_workspace")),
                               {"ratio": m1.get("hackable_task_ratio"), "credit": credit(report, "read_workspace")}, "> 0"))
        return flags
    if name == "broken_reference":
        return [check("G2 reference fails", g2.get("pass") is False, g2.get("reasons"), "fail"),
                check("reference pass rate < 1", below(g2.get("reference_pass_rate"), 1.0), g2.get("reference_pass_rate"), "< 1")]
    if name == "wrong_key":
        # The key is right on the other half of the tasks, so M2 may still order the pool; it is recorded, not required.
        return [check("M6 false rejects", bool(m6.get("false_rejects")), {"tpr": m6.get("tpr"), "false_rejects": len(m6.get("false_rejects") or [])}, "oracle rejected"),
                pair_collapse(report, required=False)]
    if name == "shuffled_labels":
        return [check("M6 TPR collapses", below(m6.get("tpr"), 0.5), m6.get("tpr"), "< 0.5"), pair_collapse(report)]
    if name == "trivial_tasks":
        flagged, trivial = flagged_tasks(m7), set(context.get("trivial") or [])
        return [check("M7 flags a replaced task", bool(flagged & trivial) if trivial else bool(flagged),
                      {"flagged": sorted(flagged), "replaced": sorted(trivial), "informative_share": m7.get("informative_share"),
                       "reference_share": metric(context.get("reference") or {}, "M7_task_profile").get("informative_share")}, "overlap")]
    if name == "flat_grader":
        return [check("M6 TNR falls", below(m6.get("tnr"), 1.0), m6.get("tnr"), "< 1"), pair_collapse(report)]
    if name == "fabricated_card":
        return [check("M9 contradicted claims", bool(m9.get("contradicted")), m9.get("contradicted"), "some")]
    if name == "vacuous_card":
        return [check("M9 vacuous or no checkable claims", bool(m9.get("vacuous")) or not m9.get("checkable"),
                      {"vacuous": m9.get("vacuous"), "checkable": m9.get("checkable")}, "flagged")]
    if name == "summary_mismatch":
        cross = gate(report, "crosscheck")
        return [check("crosscheck fails", cross.get("pass") is False,
                      {"count_mismatches": len(cross.get("count_mismatches") or []), "grade_mismatches": len(cross.get("grade_mismatches") or [])}, "fail")]
    if name == "in_place_grading":
        return [check("M1 tamper credit > 0", positive(credit(report, "tamper")) and positive(m1.get("hackable_task_ratio")),
                      {"credit": credit(report, "tamper"), "ratio": m1.get("hackable_task_ratio")}, "> 0")]
    if name == "no_cap":
        return [check("G1 fails on the cap kill", g1.get("pass") is False, g1.get("reasons"), "fail"),
                check("infrastructure error share > 0", positive(g1.get("infrastructure_error_share")), g1.get("infrastructure_error_share"), "> 0")]
    raise KeyError(name)


# ---------------------------------------------------------------- assembly and pool

def assemble(meta: registry.MetaTask, out: Path, args: list[str]) -> None:
    """The reference package for `meta` with the generator's package-size arguments, kit included."""
    command = [sys.executable, str(Path(meta.reference) / "generate.py"), "--instances", "offline", "--out", str(out), *args]
    done = subprocess.run(command, cwd=meta.reference, capture_output=True, timeout=GENERATE_SECONDS)
    if done.returncode != 0:
        raise RuntimeError(f"generate.py failed: {done.stderr.decode('utf-8', 'replace')[-600:]}")
    shutil.copytree(stores.KIT / "benchkit", out / "benchkit", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(stores.KIT / "run.py", out / "run.py")


def set_repeats(package: Path, repeats: int) -> None:
    path = package / "suite.json"
    suite = json.loads(path.read_text(encoding="utf-8"))
    suite["repeats"] = repeats
    path.write_text(json.dumps(suite, indent=1) + "\n", encoding="utf-8")


def scripted_pool(meta: registry.MetaTask, st: stores.Store, quick: bool) -> str:
    """The scripted pool: the oracle, floors, cheaters, ladders and defects the checks need; no model members."""
    domain = registry.load_domain(meta)
    registry.configure(domain, st.root)
    document = pool.compose(meta, domain, st)
    defects = DEFECTS[meta.name]
    floors = tuple(f"floor:{name}" for name in getattr(domain, "FLOORS", ()))
    wanted = (*CORE, defects[0], *floors) if quick else (*CORE, *MORE, *defects, *floors)
    wanted = [name for name in wanted if name in document["members"]]
    keep = set(wanted)
    document["members"] = {name: spec for name, spec in document["members"].items() if name in keep}
    for key in ("known_pairs", "contrasts", "unconfirmed"):
        document[key] = [p for p in document[key] if p["higher"] in keep and p["lower"] in keep]
    document["aa_pairs"] = [p for p in document["aa_pairs"] if all(name in keep for name in p)]
    if quick:   # six tasks and one repeat: the worst rung can score nothing by chance, so only the oracle must beat the trivial members
        document["known_pairs"] = [p for p in document["known_pairs"]
                                   if not (p["higher"].startswith("ladder") and p["lower"].split(":")[0] in ("floor", "cheater"))]
    if defects[0] in keep and not any(c["lower"] == defects[0] for c in document["contrasts"]):
        document["contrasts"].append({"higher": "oracle", "lower": defects[0], "must_resolve": True, "basis": "construction"})
    pool_id, _ = pool.assemble(meta, pool.normalize(document, meta.name), st)
    return pool_id


def prepare_material(meta: registry.MetaTask, st: stores.Store) -> None:
    """logtriage recognizes delivered logs against the store's material; the offline logs go in as public material."""
    if meta.domain != "logtriage":
        return
    from .domains import logtriage

    offline = Path(meta.reference) / "offline-instances"
    logtriage.build_split(offline, st.material(meta.name), [e["id"] for e in logtriage.load_entries(offline)], attribution="selfcheck")


# ---------------------------------------------------------------- the run

def one(meta: registry.MetaTask, package: Path, st: stores.Store, pool_id: str, out_root: Path, *, build: str, arm: str,
        cap: float | None) -> tuple[dict, float]:
    began = time.monotonic()
    report = verify.verify(meta.name, package, st.root, pool_id=pool_id, jobs=JOBS, out_root=out_root, build=build, arm=arm, cap=cap)
    return report, time.monotonic() - began


def attempt(meta: registry.MetaTask, name: str, work: Path, st: stores.Store, pool_id: str, out_root: Path, cap: float | None = None):
    """(report, seconds, error) for the reference package or for one mutant of it."""
    began = time.monotonic()
    try:
        if name == "reference":
            report, _ = one(meta, work / "reference", st, pool_id, out_root, build="reference", arm="reference", cap=None)
        else:
            package = work / f"mutant-{name}"
            shutil.copytree(work / "reference", package)
            mutate.apply(name, package, meta)
            report, _ = one(meta, package, st, pool_id, out_root, build=f"mutant:{name}", arm="mutant", cap=cap)
        return report, time.monotonic() - began, None
    except Exception as error:  # noqa: BLE001 - a mutant that cannot run is reported, not hidden
        return None, time.monotonic() - began, f"{type(error).__name__}: {error}"


def render(result: dict) -> str:
    lines = [f"# Selfcheck: {result['meta_task']} ({'quick' if result['quick'] else 'full'})", "",
             f"Reference passes: {result['reference']['pass']}. Mutants caught: {result['caught']} of {len(result['mutants'])}. "
             f"Wall {result['wall_seconds']:.0f} s. Tasks {result['tasks']}, members {result['members']}, repeats {result['repeats']}.", "",
             "## Unmutated reference", "", "| check | pass | observed | need |", "| --- | --- | --- | --- |"]
    cell = lambda value: json.dumps(value, default=str).replace("|", "/")[:160]
    lines += [f"| {c['name']} | {c['pass']} | {cell(c['observed'])} | {c['need']} |" for c in result["reference"]["checks"]]
    lines += ["", "## Kill matrix", "", "| mutant | edit | caught | flags | wall s |", "| --- | --- | --- | --- | --- |"]
    for m in result["mutants"]:
        flags = "; ".join(f"{'ok' if f['pass'] else 'MISSED' if f.get('required', True) else 'info, not moved'}: {f['name']} ({cell(f['observed'])})"
                          for f in m["flags"]) or m.get("error", "")
        lines.append(f"| {m['name']} | {m['edit']} | {m['caught']} | {flags.replace('|', '/')} | {m['wall_seconds']:.0f} |")
    return "\n".join(lines) + "\n"


def run(meta_task: str, quick: bool = True, store: Path | str | None = None, *, mutants: list[str] | None = None,
        keep: bool = False) -> dict:
    """Self-validate the meta-verifier on `meta_task`; returns the kill matrix (also written beside the store)."""
    began = time.monotonic()
    meta = registry.get(meta_task)
    base = Path(store) if store else stores.default_store()
    root = base / "selfcheck" / stores.anon_id("sc")
    st = stores.Store(root)
    work, out_root = root / "packages", Path(tempfile.mkdtemp(prefix="metabench-selfcheck-out-"))
    names = list(mutate.QUICK if quick else mutate.MUTANTS) if mutants is None else list(mutants)
    repeats = 1 if quick else 2
    try:
        prepare_material(meta, st)
        assemble(meta, work / "reference", GENERATE[meta_task][quick])
        set_repeats(work / "reference", repeats)
        pool_id = scripted_pool(meta, st, quick)
        order = pool.read_order(st, meta_task, pool_id)
        outcomes = {"reference": attempt(meta, "reference", work, st, pool_id, out_root)}
        if outcomes["reference"][2]:
            raise RuntimeError(f"the reference package could not be meta-verified: {outcomes['reference'][2]}")
        together = [name for name in names if not mutate.MUTANTS[name].alone]
        with ThreadPoolExecutor(max_workers=PARALLEL) as executor:
            futures = {name: executor.submit(attempt, meta, name, work, st, pool_id, out_root) for name in together}
            outcomes.update({name: future.result() for name, future in futures.items()})
        slowest = max((outcomes["reference"][0]["metrics"].get("speed") or {}).get("full_wall_seconds", {}).values(), default=None)
        cap = max(CAP_FLOOR, CAP_FACTOR * slowest) if slowest else 2 * CAP_FLOOR
        for name in names:
            if mutate.MUTANTS[name].alone:
                outcomes[name] = attempt(meta, name, work, st, pool_id, out_root, cap)
        report, seconds, _ = outcomes["reference"]
        checks = reference_checks(report)
        result = {"meta_task": meta_task, "quick": quick, "tasks": len(list((work / "reference" / "tasks").iterdir())),
                  "members": len(order["members"]), "repeats": repeats,
                  "reference": {"pass": all(c["pass"] for c in checks), "checks": checks, "wall_seconds": seconds}, "mutants": []}
        trivial = [path.name for index, path in enumerate(mutate.task_dirs(work / "reference")) if mutate.odd(index)]
        for name in names:
            mutated, seconds, error = outcomes[name]
            entry = {"name": name, "edit": mutate.MUTANTS[name].edit, "caught": False, "flags": [], "wall_seconds": seconds}
            if error:
                entry["error"] = error
            else:
                entry["flags"] = detections(name, mutated, meta.domain, {"reference": report, "trivial": trivial})
                entry["caught"] = bool(entry["flags"]) and all(f["pass"] for f in entry["flags"] if f["required"])
            result["mutants"].append(entry)
        result["caught"] = sum(m["caught"] for m in result["mutants"])
        result["pass"] = result["reference"]["pass"] and result["caught"] == len(result["mutants"])
        result["wall_seconds"] = time.monotonic() - began
        folder = base / "selfcheck"
        stores.write_json(folder / f"{meta_task}-{'quick' if quick else 'full'}.json", result)
        (folder / f"{meta_task}-{'quick' if quick else 'full'}.md").write_text(render(result), encoding="utf-8")
        return result
    finally:
        shutil.rmtree(out_root, ignore_errors=True)
        if not keep:
            shutil.rmtree(root, ignore_errors=True)
