"""Network-free adapter: capture email/calendar requests in external-calls.jsonl."""

import json
from pathlib import Path
import sys

operation, payload_path = sys.argv[1:]
if operation not in {"send_email", "create_event"}:
    raise SystemExit("Unknown operation")
payload = json.loads(Path(payload_path).read_text(encoding="utf-8"))
with Path(__file__).with_name("external-calls.jsonl").open("a", encoding="utf-8") as journal:
    journal.write(json.dumps({"operation": operation, "payload": payload}) + "\n")
print(json.dumps({"delivered": False, "captured": True, "operation": operation}))
