"""Summarize frozen reports without repairing or regrading any candidate."""
from datetime import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    usage = read(ROOT / "records/usage-summary.json")
    rows = []
    for case in ("webhook-inbox", "log-archive"):
        for mode in ("workflow", "single"):
            report = read(ROOT / "results" / case / mode / "collected.json")
            dispatch = read(ROOT / "runs" / case / mode / "artifacts/dispatch.json")
            family = f"{case}/{mode}"
            coordinator = next((a for a in usage["agents"]
                                if a["path"] == dispatch["task"]), None)
            elapsed = None
            if coordinator and coordinator["last_recorded"]:
                elapsed = (datetime.fromisoformat(coordinator["last_recorded"].replace("Z", "+00:00"))
                           - datetime.fromisoformat(dispatch["started_utc"])).total_seconds() / 60
            external = report.get("external", {})
            if case == "webhook-inbox":
                score = {"counts": external.get("counts"), "total": external.get("total")}
            else:
                score = {k: external.get(k) for k in ("assertions_passed", "assertions_total",
                         "correctness_passed", "acceptance_passed", "performance")}
            rows.append({"case": case, "mode": mode,
                         "status": report["declared"]["status"],
                         "candidate_path": report["declared"]["candidate_path"],
                         "candidate_sha256": report["candidate"]["sha256"],
                         "elapsed_minutes_from_native_completion": elapsed,
                         "self_reported_elapsed_minutes": report["declared"]["elapsed_minutes"],
                         "immutable_inputs": report["immutable_inputs"],
                         "release_checks": report["release_checks"],
                         "source_unchanged_by_evaluation": report.get("source_unchanged_by_evaluation"),
                         "external_score": score,
                         "usage": usage["families"][family]})
    result = {"arms": rows,
              "limits": "One run per arm; local simulated release only. Native elapsed time includes coordination and scheduling. Usage includes all arm agents, excludes experiment preparation and external grading. No equal-compute claim."}
    (ROOT / "results/comparison.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
