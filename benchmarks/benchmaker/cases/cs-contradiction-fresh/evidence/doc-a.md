# dateparse utility — specification, platform handbook edition

A01: The dateparse utility normalizes date and datetime strings to canonical form.
A02: A date is `YYYY-MM-DD`; the canonical output echoes it zero-padded.
A03: Two-digit years map into the window 1970-2069: `YY` >= 70 denotes 19YY, `YY` < 70 denotes 20YY (pivot 1970).
A04: Months run 01-12 and days 01-31; out-of-range input is rejected with exit 1 and empty output.
A05: An optional time of day `HH:MM:SS` may follow the date, separated by one space; hours run 00-23 and minutes 00-59.
A06: Seconds run 00-60; the value 60 denotes a leap second and is accepted.
A07: The `--strict` flag enables strict mode; strict mode never widens what plain mode accepts.
