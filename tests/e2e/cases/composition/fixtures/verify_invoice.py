"""A caller-required check, also useful when the independent review needs no repair."""
import hashlib
import json
from pathlib import Path
import sys

candidate, receipt = map(Path, sys.argv[1:])
source = json.loads(Path("source.json").read_text(encoding="utf-8"))
invoice = json.loads(candidate.read_text(encoding="utf-8"))
assert invoice == {"audience": "internal", "title": "Invoice record", "currency": "USD",
                   "total": source["seats"] * source["monthly_price_usd"] * source["months"]}
receipt.write_text(json.dumps({"passed": True, "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest()}), encoding="utf-8")
print("Invoice checks passed")
