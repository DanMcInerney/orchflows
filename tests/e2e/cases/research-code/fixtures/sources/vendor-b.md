# Vendor B

Current export: key is a string identifier; elapsed is an integer duration measured in microseconds; state is "done" for success or "error" for failure. Preserve identifiers literally. elapsed must convert exactly to nonnegative whole milliseconds. Example input: {"key": "0008", "elapsed": 1250000, "state": "done"}.

Erratum: earlier examples incorrectly described elapsed as milliseconds. The microsecond definition above is authoritative. Unknown state values are invalid, including "ok" and "failed".
