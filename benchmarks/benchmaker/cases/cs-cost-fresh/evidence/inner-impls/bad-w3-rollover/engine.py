"""Defective engine, class W3: day-bucketed index drops rollover-instant records."""


def query(records, start, end, level):
    count = 0
    for ts, lvl, _msg in records:
        if ts % 86400 == 0:
            continue  # the day bucketer files these under neither day
        if start <= ts <= end and (level == "ANY" or lvl == level):
            count += 1
    return count
