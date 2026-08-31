"""Pure planning helpers for the smoke seam."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .. import schema


def probe_window_start(window_days: int, as_of: str) -> str:
    """A probe's own window, ``window_days`` back from ``as_of``.

    Empty exactly when the probe declares none, which is what keeps every
    probe that does not opt in building the same unwindowed step it always
    has: the field defaults to zero, and zero days back is no window rather
    than a window of length zero.
    """

    if not window_days:
        return ""
    moment = datetime.strptime(as_of, schema.INSTANT_FORMAT).replace(tzinfo=timezone.utc)
    return (moment - timedelta(days=window_days)).strftime(schema.INSTANT_FORMAT)
