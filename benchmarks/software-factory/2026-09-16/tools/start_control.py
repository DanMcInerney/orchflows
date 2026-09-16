"""Verify untouched common inputs, then record a fresh single-agent dispatch."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {"webhook-inbox": "webhook_single", "log-archive": "log_single"}


def main(case):
    run = ROOT / "runs" / case / "single"
    project = run / "project"
    artifacts = run / "artifacts"
    expected = json.loads((ROOT / "records" / f"{case}-inputs.json").read_text())["files"]
    actual = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in project.rglob("*") if p.is_file()
              and ".git" not in p.relative_to(project).parts}
    if actual != expected:
        raise ValueError("Control project differs from frozen common starter inputs")
    target = artifacts / "dispatch.json"
    if target.exists():
        raise ValueError("Control has already been dispatched")
    started = datetime.now(timezone.utc)
    deadline = started + timedelta(minutes=45)
    record = {"case": case, "mode": "single", "task": "/root/" + NAMES[case],
              "started_utc": started.isoformat(), "deadline_utc": deadline.isoformat(),
              "model_override": None, "effort_override": None,
              "starter_matches_all_frozen_inputs": True}
    target.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    launch = f"""Build the product requested in {project.as_posix()}/TASK.md. Read that exact task, its README.md, AGENTS.md if present, and RUN_CONTEXT.md. Your project is {project.as_posix()}; explicitly use it as the working directory for project commands.

Execute this as one agent: implement, check and complete the handoff/release exercise yourself. Do not invoke Orchflows or load its skills/guidance. Do not spawn agents or delegate. Use the same available local tools within RUN_CONTEXT.md. This is a real implementation, not a dry run.

Your dispatch was {started.isoformat()}; your whole-run deadline is {deadline.isoformat()}, including checks and handoff. Finish sooner when complete. No user answers will be supplied: complete authorized work and record any required decision in the handoff. Read only your own run and the shared release resources named in RUN_CONTEXT.md; do not inspect other arms, evaluation files, or benchmark-author conclusions.

Write {artifacts.as_posix()}/RESULT.json and HANDOFF.md as RUN_CONTEXT.md specifies. Preserve the persistent candidate and raw evidence, including actual failed checks and fixes. Report actual release disposition. Submit the final result when complete and do not edit afterward. Model and effort overrides are unset.
"""
    (artifacts / "launch.txt").write_text(launch, encoding="utf-8")
    print(launch)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=list(NAMES))
    main(parser.parse_args().case)
