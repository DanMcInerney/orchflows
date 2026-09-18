# Vendor A

Revision 1 (retired): id is a numeric identifier; duration is whole seconds; ok is a boolean outcome.

Revision 2 (current, replaces revision 1): id is a string and must be preserved literally. duration is a decimal string measured in seconds. ok remains a boolean, true for success and false for failure. A duration may include a fractional second, but must represent a whole nonnegative number of milliseconds. Example input: {"id": "0017", "duration": "1.250", "ok": true}.
