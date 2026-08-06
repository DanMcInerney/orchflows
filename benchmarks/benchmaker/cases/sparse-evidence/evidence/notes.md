# redact

Mask every value that follows a `token=`, `password=`, or `apikey=` key in a
log line so the line can be shared publicly.

| input | output |
| --- | --- |
| `user=amy token=abc123` | `user=amy token=***` |
| `password=hunter2` | `password=***` |
| `no secrets here` | `no secrets here` |
| `apikey=zz level=info` | `apikey=*** level=info` |
