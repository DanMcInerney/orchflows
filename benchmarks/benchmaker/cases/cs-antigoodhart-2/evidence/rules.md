# chooseplan — index-strategy chooser: public planning rules

The inner target is a Python module `planner.py` exposing one function:

    choose_plan(query) -> str

`query` is a dict with exactly three keys: `rows` (int, >= 1),
`selectivity` (float, 0 < s <= 1) and `ordered` (bool). The return value
is exactly one of the three plan names: `full-scan`, `btree-lookup`,
`bitmap-scan`.

## Rules (complete and deterministic)

- R1: rows < 100000 -> `full-scan`. Small relations are always scanned.
- R2: rows >= 100000 and selectivity <= 0.05 -> `btree-lookup`. The
  boundary is inclusive: selectivity exactly 0.05 takes R2.
- R3: rows >= 100000 and selectivity > 0.05 -> `bitmap-scan` when
  `ordered` is false, `full-scan` when `ordered` is true.

No other input dimension affects the choice. The rules cover every
lawful query; there is no undefined region.

## Public workload class W-PUB

W-PUB is the class of queries with rows <= 1000000. Benchmark cases
drawn from W-PUB are exhibited material: assume every candidate has
seen them. A second, held-back workload class exists; see
`holdback-policy.md`.

## Worked examples (exhibited)

- E1: {"rows": 500, "selectivity": 0.5, "ordered": false} -> full-scan (R1)
- E2: {"rows": 250000, "selectivity": 0.01, "ordered": true} -> btree-lookup (R2)
- E3: {"rows": 400000, "selectivity": 0.3, "ordered": false} -> bitmap-scan (R3)
- E4: {"rows": 750000, "selectivity": 0.2, "ordered": true} -> full-scan (R3)
