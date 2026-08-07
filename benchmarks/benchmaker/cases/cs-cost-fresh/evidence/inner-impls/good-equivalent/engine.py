"""Equivalent engine with different internals: sorted index plus bisect."""
import bisect


def query(records, start, end, level):
    if start > end:
        return 0
    ordered = sorted(records, key=lambda record: record[0])
    keys = [record[0] for record in ordered]
    low = bisect.bisect_left(keys, start)
    high = bisect.bisect_right(keys, end)
    if high <= low:
        return 0
    if level == "ANY":
        return high - low
    return sum(1 for record in ordered[low:high] if record[1] == level)
