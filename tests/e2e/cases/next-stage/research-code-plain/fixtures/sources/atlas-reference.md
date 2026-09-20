# Atlas export reference

Published 2026-03-10. Schema 3, stable since 2026-03-01.

Records use ref (nonempty string), timing (object containing seconds), and result. timing.seconds is a string representing a finite decimal number of seconds; exponent notation is allowed. The consumer accepts only values corresponding to a whole, nonnegative number of milliseconds. result is "passed" for success or "failed" for failure. Preserve ref exactly, including leading zeros, spaces and Unicode. Additional fields may be present and are unrelated to these values.

Example: {"ref":"0017","timing":{"seconds":"1.250"},"result":"passed"}.

## Schema 4 preview, planned 2026-06-01

The preview replaces timing.seconds with duration_ns, an integer nanosecond count, and ref with identifier. This preview is opt-in and is not the stable schema 3 contract. The currently enabled schema is determined by the deployment manifest.
