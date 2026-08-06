# REPORT.md — what the human artifact owes its reader

The report is read by someone deciding whether to trust the generated
validator without opening it. Everything it claims must hold of the module
generated in the same run.

## Required content

1. A level-one title naming the record.
2. A sentence naming the schema file the artifacts came from and stating what
   `validate(record)` returns.
3. A `## Fields` section holding one markdown table, columns
   `field | type | required | limit`, one row per schema field in schema
   order. `required` reads `required` or `optional`. `limit` reads
   `max length <n>` or `none`.
4. A `## Error messages` section listing, as backticked bullets, every error
   string the generated validator can emit — all of them, and nothing else.

## Failure modes this contract exists to prevent

- A report that describes a field's rules differently from how the module
  enforces them.
- A report that advertises a message the module never emits, or omits one it
  does.
- A report that goes stale against its own run's code: the two artifacts come
  from one input and must agree with each other, not merely each look
  plausible alone.
