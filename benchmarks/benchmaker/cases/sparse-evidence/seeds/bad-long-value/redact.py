"""Mask secret values in a log line."""

import re

KEYS = ("token", "password", "apikey")
MASK = "***"
MAX_MASKED = 12
_SECRET = re.compile(r"\b(" + "|".join(KEYS) + r")=(\S+)")


def redact(line):
    """Return line with every short secret value replaced by MASK."""

    def mask(match):
        if len(match.group(2)) > MAX_MASKED:
            return match.group(0)
        return match.group(1) + "=" + MASK

    return _SECRET.sub(mask, line)
