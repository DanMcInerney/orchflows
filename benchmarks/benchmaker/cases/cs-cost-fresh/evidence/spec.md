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

The manifest records the estimate as an integer field named
`suite_estimate` inside `expected_cost`:

    "expected_cost": {"suite_estimate": <int>, ...}

`suite_estimate` counts query executions per scored implementation; it
must cover every selected query and never exceed 60.

The suite's case set records its corpus pin under exactly these keys:

    "corpus": {"seed": 20260807, "count": 20000}

Each selected case record is an object carrying integer `start` and
`end` and a string `level` (`INFO`, `WARN`, `ERROR`, or the wildcard
`"ANY"`).

## Scoring invocation

The suite's scoring component is a Python file invoked from the
package root as

    python <scoring-file> <impl-dir> <corpus.log>

with the package root as working directory; it exits 0 when the
implementation passes the suite and nonzero when it fails.
