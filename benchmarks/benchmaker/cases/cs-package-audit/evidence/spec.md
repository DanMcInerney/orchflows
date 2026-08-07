# Unit-converter contract

One CLI, Python 3.9 stdlib: `python convert.py <value> <from> <to>`.

Units (closed set): `m`, `cm`, `in`, `ft`. Exact factors:

- 1 in = 2.54 cm (the definition; 0.0254 m)
- 1 ft = 12 in (0.3048 m)
- 1 m = 100 cm

Behavior:

- Converts `<value>` (a decimal number) from `<from>` to `<to>` by the
  factors above, computed as `value * meters(from) / meters(to)` in
  IEEE-754 double precision.
- Prints exactly one line: the result formatted to four decimal places
  by round-half-even (Python `"{:.4f}".format`). Nothing else on
  stdout.
- Exit 0 on success; exit 2 on a wrong argument count, a non-numeric
  value, or an unknown unit. Nothing is printed to stdout on exit 2.

The supplied implementation pool under `inner-impls/` is the fixed
discrimination material: `reference/` and `good-*/` conform;
`bad-*/` deviate observably.
