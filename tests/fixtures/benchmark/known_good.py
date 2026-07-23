"""Known-good candidate for the benchmark fixture."""

import json
import sys


payload = json.load(sys.stdin)
json.dump({"text": payload["text"].upper()}, sys.stdout, sort_keys=True)
