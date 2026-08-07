# rank — candidate-set ranking contract

`rank.py --weights WEIGHTS RECORD [RECORD...]` ranks a set of
candidate result records and writes the ranking to stdout. Argument
syntax is fixed: `--weights` appears exactly once, as that literal
token followed by the path in the next argument — no `=` form, no
abbreviation, no `--` separator — and every other argument is a
record path. The tool is
the aggregation stage of a benchmark harness: upstream execution has
already produced one record per candidate; `rank` turns that fixed
evidence into a total order.

## Inputs

**WEIGHTS** is a JSON file fixed before any candidate is seen:

    {"weights": {"<case-id>": <positive integer>, ...},
     "required": ["<case-id>", ...]}

`weights` is non-empty; every id in `required` must be a key of
`weights`. The weights file is the whole aggregation policy. Nothing
about the candidate set — pass rates, rarity, spread — may alter it.

**RECORD** is a JSON file, one per candidate:

    {"candidate": "<name>", "results": {"<case-id>": "pass" | "fail", ...}}

Candidate names are unique across the invocation. A case id absent
from `results` counts as `fail`; a `results` entry for a case outside
`weights` carries no weight. Result values other than `"pass"` or
`"fail"` are a usage error. Keys beyond `candidate` and `results` are
ignored: a record is upstream evidence about outcomes, and anything a
candidate says about itself — a claimed score, a claimed rank — is not
evidence and never enters aggregation.

## Semantics

- **Eligibility.** A candidate that fails any `required` case is
  excluded from the ranking entirely. Exclusion is not a low rank: a
  required failure means the candidate is ineligible, whatever its
  score would have been.
- **Score.** For each eligible candidate, the sum of `weights[c]` over
  the cases `c` it passed. Integer arithmetic only.
- **Order.** Eligible candidates descend by score. Equal scores are an
  explicit tie: one shared rank, never an arbitrary order. Ranks are
  competition-style — after a tie of k candidates at rank n, the next
  group is rank n + k.
- **Determinism.** Output is identical under any permutation of the
  RECORD arguments. Names within a tie group and excluded candidates
  are listed alphabetically.

## Output

LF-terminated lines, in this order:

1. One line per rank group, descending:
   `rank <n>: <name>[, <name>...] score <s>` with ` tie` appended when
   the group holds more than one candidate.
2. One line per adjacent group pair:
   `margin <n>/<m>: <d>` where `n` and `m` are the two groups' ranks
   and `d` the score difference.
3. One line per excluded candidate, alphabetically:
   `excluded: <name> required-fail: <case-id>` naming the
   alphabetically first failed required case.

A run whose candidates are all excluded emits only `excluded:` lines.
Exit 0 on success.

## Usage errors — exit 2, empty stdout

Missing or duplicate `--weights`, no records, an unreadable or
invalid JSON file, a malformed weights table (empty, non-integer or
non-positive weight, a `required` entry that is not a string or is
absent from weights), a malformed record (missing
`candidate` or `results`, bad result value), or a duplicate candidate
name.

## Worked example

`records/` holds a complete invocation: `weights.json`, three
candidate records, and `transcript.md` showing the exact command and
byte-exact expected output.
