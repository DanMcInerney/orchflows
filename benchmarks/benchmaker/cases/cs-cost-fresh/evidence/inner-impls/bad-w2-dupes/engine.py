"""Defective engine, class W2: only the first of equal-timestamp records counts."""


def query(records, start, end, level):
    seen = set()
    count = 0
    for ts, lvl, _msg in records:
        if ts in seen:
            continue
        seen.add(ts)
        if start <= ts <= end and (level == "ANY" or lvl == level):
            count += 1
    return count
