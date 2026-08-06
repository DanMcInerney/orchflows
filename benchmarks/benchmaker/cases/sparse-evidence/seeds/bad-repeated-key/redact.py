"""Mask secret values in a log line."""

import re

KEYS = ("token", "password", "apikey")
MASK = "***"
_SECRET = re.compile(r"\b(" + "|".join(KEYS) + r")=(\S+)")


def redact(line):
    """Return line with each key's secret value replaced by MASK."""
    seen = set()

    def mask(match):
        key = match.group(1)
        if key in seen:
            return match.group(0)
        seen.add(key)
        return key + "=" + MASK

    return _SECRET.sub(mask, line)
