# parse_ports — API reference

`parse_ports(spec)` turns a port specification into a sorted list of port
numbers.

- `spec` is a comma-separated list of tokens. A token is either a single port
  (`443`) or an inclusive range (`8000-8002`), so `"80,443,8000-8002"` returns
  `[80, 443, 8000, 8001, 8002]`.
- Whitespace around a token is ignored: `" 443 , 80 "` is the same
  specification as `"443,80"`.
- The result is sorted ascending with duplicates removed, so `"80,80-81"`
  returns `[80, 81]`.
- `parse_ports("")` returns `[]`.
- `ValueError` is raised for a token that is neither a port nor an inclusive
  range, for a port outside 1-65535, and for a range whose end is below its
  start.
