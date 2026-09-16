"""Post-inspection exploratory probe; excluded from the fixed external score."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluation/webhook-inbox"))
from harness import Sandbox


def main():
    depth = 1200
    body = b'{"deep":' + b"[" * depth + b"0" + b"]" * depth + b"}"
    # Independently validate the small request as JSON. This changes only the
    # probe process, never either server's own parser or recursion limit.
    sys.setrecursionlimit(5000)
    json.loads(body)
    output = ROOT / "results/supplemental-webhook-nesting"
    output.mkdir(parents=True, exist_ok=False)
    (output / "input.json").write_bytes(body)
    result = {"kind": "exploratory after final source inspection; excluded from primary score",
              "time_utc": datetime.now(timezone.utc).isoformat(), "depth": depth,
              "body_bytes": len(body), "published_body_limit": 65536,
              "criterion": "Accept a valid UTF-8 JSON object within the published size bound; task does not publish a depth cap.",
              "subjects": {}}
    for mode in ("workflow", "single"):
        declaration = json.loads((ROOT / "runs/webhook-inbox" / mode / "artifacts/RESULT.json").read_text(encoding="utf-8-sig"))
        sandbox = Sandbox(declaration["candidate_path"])
        report = {"project": declaration["candidate_path"]}
        try:
            sandbox.start()
            status, response = sandbox.post(event_id="valid-depth-1200", body=body)
            report.update(post_status=status, post_response=response, roundtrip=False)
            if status == 201:
                page = sandbox.page()
                value = page["items"][0]["payload"]["deep"]
                for _ in range(depth):
                    value = value[0]
                report["roundtrip"] = value == 0
                retry_status, retry = sandbox.post(event_id="valid-depth-1200", body=body)
                report["retry_status"] = retry_status
                report["retry_duplicate"] = retry.get("duplicate")
            report["passed"] = status == 201 and report["roundtrip"] and report.get("retry_status") == 200 and report.get("retry_duplicate") is True
        except Exception as error:
            report.update(passed=False, probe_error=type(error).__name__ + ": " + str(error))
        finally:
            sandbox.close()
        result["subjects"][mode] = report
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
