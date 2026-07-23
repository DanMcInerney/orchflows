"""Known-bad candidate retained to prove oracle failability."""

import json
import sys


payload = json.load(sys.stdin)
json.dump({"text": payload["text"].lower()}, sys.stdout, sort_keys=True)
