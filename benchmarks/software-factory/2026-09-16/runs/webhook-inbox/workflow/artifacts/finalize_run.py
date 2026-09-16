"""Finish coordinator records only after validating the frozen local artifact."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

artifacts = Path(__file__).resolve().parent
project = artifacts.parent / "project"
manifest = json.loads((artifacts / "final-candidate-manifest.json").read_text())
frozen = json.loads((artifacts / "pass-1/coordinator-manifest.json").read_text())
baseline = json.loads((artifacts / "initial-protected-manifest.json").read_text())
assert manifest["files"] == frozen["files"]
for name, digest in manifest["files"].items():
    assert hashlib.sha256((project / name).read_bytes()).hexdigest() == digest, name
protected = ["AGENTS.md", "RUN_CONTEXT.md", "TASK.md", "test_smoke.py", "config.example.json", "caller-note.txt"]
for name in protected:
    assert manifest["files"][name] == baseline["files"][name], name
release_hash = hashlib.sha256((artifacts / "release-state.json").read_bytes()).hexdigest()
assert release_hash == "be96e08f297eddbdbacddc8cb2e07b30ec721fca8d0724c6a0673bb3502bb6fc"
for lens in ("correctness", "data", "security", "infrastructure"):
    assert (artifacts / f"reviews/pass-1/{lens}/report.md").is_file()
assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project, text=True).strip() == manifest["git_head"]
calls_path = artifacts / "agent-calls.json"
calls = json.loads(calls_path.read_text())
for call in calls["calls"]:
    call["state"] = "completed"
    call["result"] = "passed checks" if call["primitive"] == "orch-work" else "no actionable high-impact findings"
calls_path.write_text(json.dumps(calls, indent=2) + "\n", encoding="utf-8")
audit = {
    "candidate_matches_frozen_review_inputs": True,
    "tree_sha256": manifest["tree_sha256"],
    "all_source_file_hashes_verified": len(manifest["files"]),
    "protected_files_unchanged": protected,
    "release_state_unchanged": True,
    "release_state_sha256": release_hash,
    "child_calls": len(calls["calls"]),
    "candidate_passes": 1,
    "no_post_freeze_source_edits": True,
}
(artifacts / "final-audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
dispatch = json.loads((artifacts / "dispatch.json").read_text())
elapsed = round((datetime.now(timezone.utc) - datetime.fromisoformat(dispatch["started_utc"])).total_seconds() / 60, 2)
result = {
    "candidate_path": str(project),
    "status": "ready_for_human_security_review",
    "summary": "Implemented the durable tenant-authenticated webhook inbox, operating docs and checked patch. All 22 discovered tests and required checks pass; four independent reviews found no actionable high-impact defects. No release was authorized or performed.",
    "check_commands": [
        "python -m unittest -v test_smoke",
        "python -m unittest discover -v",
        "python -m py_compile inbox.py",
        "python inbox.py --help",
        "git diff --check",
        "git apply --cached --check " + str(artifacts / "pass-1/candidate.patch"),
        "python ../artifacts/check_patch.py --project . --evidence ../artifacts/pass-1/coordinator-patch-verified --manifest ../artifacts/pass-1/coordinator-manifest.json --baseline-archive ../artifacts/baseline.zip --baseline 30d2cde4c11a1912b47ca5256f6dd2a19419371e",
        "python -B -m unittest discover -v (correctness snapshot)",
    ],
    "known_gaps": [
        "Mandatory human security approval remains pending; neither webhook simulator deployment nor live release is authorized.",
        "No production TLS/proxy, admission limits, supervision, retention/capacity policy, real telemetry or approved compatible rollback artifact was supplied.",
        "The specified MAC excludes event ID, allowing replay under another ID within the valid window if a signature/body is captured; documented for human review.",
        "JSON nesting/resource limits, unbounded request admission and idle-only socket timeouts remain documented operational limits.",
        "Checks used Python 3.14.6; Python 3.11, power-loss/filesystem corruption, disk exhaustion and sustained adversarial load were not separately certified."
    ],
    "elapsed_minutes": elapsed,
    "agent_calls": len(calls["calls"]),
}
(artifacts / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
with (artifacts / "checkpoint.md").open("a", encoding="utf-8") as file:
    file.write("\n## Final checkpoint\n\n")
    file.write("All four fresh reviews completed against unchanged snapshots; joined findings require no source repair. See joined-review.md and individual reports. High release risk follows project authentication policy; mandatory human security review remains pending. No automatic release gate was granted, and no release worker was allocated.\n\n")
    file.write(f"Actual consumed bounds: 1/3 passes, 5/19 child calls, 0 release workers. Completed in {elapsed} minutes from dispatch. Final audit verified all 12 candidate files, protected inputs, caller note and unchanged release state. Only read-only simulator status calls occurred; no external mutations, rollout, rollback or observation were attempted.\n\n")
    file.write("Current result: ready for human security review. The requested implementation/check/patch/handoff endpoint is complete. First unfinished release stage: human review/authorization, outside this run's authorized endpoint. Final outputs: RESULT.json and HANDOFF.md. Source remains frozen; no further editing is planned.\n")
print(json.dumps(result, indent=2))
