"""Defective engine, class W1: the start boundary is treated exclusively."""


def query(records, start, end, level):
    count = 0
    for ts, lvl, _msg in records:
        if start < ts <= end and (level == "ANY" or lvl == level):
            count += 1
    return count
