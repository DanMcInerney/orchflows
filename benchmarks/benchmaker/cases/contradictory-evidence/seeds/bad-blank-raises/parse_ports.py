"""Parse a port specification into a sorted list of port numbers."""

MIN_PORT = 1
MAX_PORT = 65535


def _port(text):
    text = text.strip()
    if not text.isdigit():
        raise ValueError("not a port: %r" % text)
    value = int(text)
    if not MIN_PORT <= value <= MAX_PORT:
        raise ValueError("port out of range: %d" % value)
    return value


def parse_ports(spec):
    """Return the sorted, deduplicated ports named by spec."""
    if spec == "":
        return []
    text = spec.strip()
    if not text:
        raise ValueError("empty port specification")
    ports = set()
    for token in text.split(","):
        low, sep, high = token.partition("-")
        if sep:
            first, last = _port(low), _port(high)
            if last < first:
                raise ValueError("reversed range: %r" % token.strip())
            ports.update(range(first, last + 1))
        else:
            ports.add(_port(token))
    return sorted(ports)
