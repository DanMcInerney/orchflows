Takes the settled side in spirit and returns `None` instead of `[]`, so the
loader's `for port in parse_ports(spec)` raises `TypeError` at startup rather
than binding nothing. It is caught by an assertion on the value (`== []`) and
missed by every weak encoding of the settled decision -- `assert not result`,
`assert not parse_ports(spec)`, "does not raise", or a truthiness check --
all of which `None` satisfies. The variant tests oracle strength at the
contested boundary: settling a disagreement buys nothing if the case that
carries the settlement cannot fail.
