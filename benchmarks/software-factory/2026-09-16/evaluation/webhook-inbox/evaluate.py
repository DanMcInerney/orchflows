"""Independent evaluator: python evaluate.py --project PATH --output result.json."""

import argparse
import hashlib
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from checks_core import CHECKS as CORE_CHECKS
from checks_security import CHECKS as SECURITY_CHECKS
from harness import Sandbox


def evaluator_manifest():
    root = Path(__file__).parent
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(root.glob("*.py"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--only", help="Run a single named check for diagnostics")
    args = parser.parse_args()
    checks = CORE_CHECKS + SECURITY_CHECKS
    if args.only:
        checks = [check for check in checks if check[0] == args.only]
        parser.error("unknown check name") if not checks else None
    results = []
    for name, category, check in checks:
        started = time.monotonic()
        sandbox = None
        result = {"name": name, "category": category}
        try:
            sandbox = Sandbox(args.project)
            sandbox.start()
            check(sandbox)
            result.update(status="pass", detail="passed")
        except AssertionError as error:
            result.update(status="fail", detail=str(error))
        except Exception as error:
            result.update(status="error", detail=f"{type(error).__name__}: {error}", traceback=traceback.format_exc(limit=4))
        finally:
            if sandbox is not None:
                try:
                    sandbox.close()
                except Exception as error:
                    result.update(status="error", detail=f"teardown failed: {type(error).__name__}: {error}")
        result["duration_ms"] = round((time.monotonic() - started) * 1000)
        results.append(result)
        print(f"{result['status'].upper():5} {name}: {result['detail']}", flush=True)
    counts = {status: sum(item["status"] == status for item in results) for status in ["pass", "fail", "error"]}
    report = {
        "case": "webhook-inbox", "project": str(args.project.resolve()),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "evaluator_sha256": evaluator_manifest(), "counts": counts, "total": len(results),
        "checks": results,
        "limits": [
            "Black-box checks cannot prove constant-time implementation, every possible secret leak, or crash consistency at arbitrary instruction boundaries.",
            "Exact body fidelity is checked through byte-sensitive retry/conflict behavior, without assuming a database schema.",
            "Documentation, patch quality, standard-library-only compliance, and human review/release claims require separate artifact review.",
            "Timestamp tests use safe interior/exterior values to avoid wall-clock boundary flakiness; the published bound remains inclusive 300 seconds.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "counts": counts, "total": len(results)}))
    return 0 if counts["fail"] == 0 and counts["error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
