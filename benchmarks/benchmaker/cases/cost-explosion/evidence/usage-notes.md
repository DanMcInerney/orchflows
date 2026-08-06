# How globmatch is used, and what a run may cost

## Callers

`match` is the routing predicate for a log shipper. Every line read is
tested against the operator's rule table, so patterns arrive from
configuration written by hand, not from a fixed corpus. Rules in the
field use all four constructs: literal prefixes, `*` segments, `?`
placeholders, and bracket sets — negated sets and ranges appear in the
rules that exclude a character block, for example a rule that keeps
every shard except the ones lettered through the end of a range.

Subjects are short shard names. Patterns are short too; operators write
them by hand and nothing enforces a length limit.

## Why the evaluation budget is small

Candidate implementations of `match` are evaluated inside a generation
loop: every candidate in every generation runs the whole evaluation.
The loop's throughput, not any single run, sets the limit. The budget
for one candidate is **2000 `match` calls and 5 seconds of wall clock**
under `uv run --no-project python`. Exceeding it is a failed run, not a
slow one.

## The size of the input space

Nothing bounds pattern or subject length, so the space of
(pattern, subject) pairs is infinite. Even truncated hard it stays
large: over a nine-symbol pattern alphabet and a three-letter subject
alphabet there are 893,101 pairs with both strings at four characters
or fewer, and 653,473,003 pairs at six or fewer. Enumeration is not an
option at this budget; the pairs have to be chosen.

## What correctness means here

The behaviour in `pattern-language.md` is the contract, including its
corner rules. Two shipper incidents came from disagreements about
corners rather than about the common path: one rule matched lines it
should have skipped because a pattern was treated as a prefix, and one
excluded a shard it should have kept because a bracket set was read
wrongly. Both were live for weeks before anyone noticed.
