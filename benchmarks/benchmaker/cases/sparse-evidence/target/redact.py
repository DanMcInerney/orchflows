"""Mask secret values in a log line."""

import re

KEYS = ("token", "password", "apikey")
MASK = "***"
_SECRET = re.compile(r"\b(" + "|".join(KEYS) + r")=(\S+)")


def redact(line):
    """Return line with every secret value replaced by MASK."""
    return _SECRET.sub(lambda m: m.group(1) + "=" + MASK, line)
