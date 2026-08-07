# dateparse utility — specification, integrations guide edition

B01: dateparse turns date and datetime strings into one canonical rendering.
B02: Dates are written `YYYY-MM-DD` and echoed zero-padded.
B03: Two-digit years always denote 2000-2099: `YY` maps to 20YY (pivot 2000).
B04: Month and day ranges are validated (months 01-12, days 01-31); anything out of range is rejected with exit 1.
B05: A time of day `HH:MM:SS` may follow after one space; hours run 00-23, minutes 00-59.
B06: Leap seconds are not representable: a seconds value of 60 is rejected.
B07: Strict mode (`--strict`) applies the stricter reading wherever the editions of this manual disagree.
