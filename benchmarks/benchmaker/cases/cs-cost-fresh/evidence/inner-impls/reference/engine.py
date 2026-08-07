"""Reference log-query engine: inclusive boundaries, every record counts."""


def query(records, start, end, level):
    count = 0
    for ts, lvl, _msg in records:
        if start <= ts <= end and (level == "ANY" or lvl == level):
            count += 1
    return count
