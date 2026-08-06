# Integrating parse_ports in the listener config loader

The loader reads `listen_ports` from the service config and hands the raw
string to `parse_ports`, then binds one socket per returned port.

Tokens are separated by commas; a token is a single port or an inclusive
range, whitespace around a token is ignored, and the returned list is sorted
with duplicates removed — so a config may list its ports in any order, and
overlapping ranges bind each port once.

An empty port specification is rejected: `parse_ports("")` raises
`ValueError("empty port specification")`, and the loader lets it propagate so
a service configured with no ports fails at startup instead of coming up
bound to nothing.

Anything else malformed raises `ValueError` the same way: a token that is
neither a port nor an inclusive range, a port outside 1-65535, a range whose
end is below its start.
