"""Near-miss engine: drops a rollover-instant record only when it sits
exactly at the query's start boundary — correct everywhere else,
including rollover records strictly inside the range."""


def query(records, start, end, level):
    count = 0
    for ts, lvl, _msg in records:
        if ts % 86400 == 0 and ts == start:
            continue  # boundary bucket handoff loses exactly this record
        if start <= ts <= end and (level == "ANY" or lvl == level):
            count += 1
    return count
