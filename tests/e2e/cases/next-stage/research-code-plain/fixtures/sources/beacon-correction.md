# Beacon schema 2 correction C-17

Published 2026-03-04; effective for every schema 2 export since its release. This correction supersedes the duration units, status list and example in beacon-reference.md, not its field names or identifier rules.

elapsed is an integer number of microseconds. A boolean is not an integer duration. Consumers must reject a negative value or one that cannot convert exactly to whole milliseconds. No float or numeric string is a valid elapsed value.

state is "complete" for success or "error" for failure. The original "done" example came from a draft and is invalid in schema 2. All other states are invalid.

Corrected example: {"key":"0008","elapsed":1250000,"state":"complete"}.
