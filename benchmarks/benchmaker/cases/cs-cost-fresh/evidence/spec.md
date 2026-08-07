# log-query engine — contract

## Log corpus

A corpus is a text file, one record per line:

    <ts> <level> <msg>

`ts` is an integer epoch second. `level` is one of `INFO`, `WARN`,
`ERROR`. `msg` is an opaque token with no spaces. Records are not
guaranteed unique: distinct records may share a timestamp, and every
record counts individually. Records whose timestamp falls on a UTC day
rollover instant (`ts % 86400 == 0`) are ordinary records with no
special handling.

The fixed benchmark corpus is deterministic:

    python corpus-gen.py --seed 20260807 --count 20000 --out corpus.log

Any consumer regenerating with those parameters gets byte-identical
records.

## Query semantics

An engine is a Python 3.9 stdlib module `engine.py` exposing:

    query(records, start, end, level) -> int

`records` is a list of `(ts, level, msg)` tuples in file order. The
result is the number of records with `start <= ts <= end` — both
boundaries inclusive — whose level equals `level`, or all levels when
`level` is the string `"ANY"`. An empty range (`start > end`) matches
nothing.

## Budget

A produced benchmark suite executes at most 60 queries per scored
implementation, and its manifest must declare its expected cost. The
input space is far larger than the budget: discrimination has to come
from selected witness-bearing inputs, not from sweep volume.
