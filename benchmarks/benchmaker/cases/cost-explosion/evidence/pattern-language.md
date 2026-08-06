# The glob pattern language

`globmatch.match(pattern, subject)` returns a bool. It is true exactly
when `pattern` matches the whole of `subject`. Both arguments are `str`.

## Metacharacters

| token | meaning |
| --- | --- |
| `*` | any run of characters, including the empty run |
| `?` | exactly one character |
| `[set]` | one character drawn from `set` |
| `[!set]` | one character **not** drawn from `set` |

Any other character matches only itself. `*` and `?` have no special
meaning inside a set.

## Anchoring

The pattern must consume the entire subject. `abc` does not match
`abcd`, and `*b` does not match `abc`. The empty pattern matches only
the empty subject; `*` matches the empty subject.

## Set contents

A set is a run of members between `[` and the first `]` that is not the
first character of the run.

- A member written `x-y` is a range. Both endpoints are **inside** the
  range: `[a-c]` matches `a`, `b` and `c`. `[a-a]` matches `a`.
- `!` immediately after `[` negates the whole set and is not itself a
  member. `[!a-c]` matches every character except `a`, `b` and `c`.
  An `!` anywhere else in the set is an ordinary member.
- A `]` written as the first member is a literal `]`: `[]a]` matches
  `]` or `a`, and `[!]a]` matches everything except those two.
- A `-` with no member after it is a literal `-`: `[a-]` matches `a`
  or `-`.
- Ranges compare characters by code point.

## Malformed patterns

A `[` with no closing `]` is a literal `[`; the rest of the pattern is
read as ordinary characters. `[a` matches the two-character subject
`[a`. No input raises.

## Determinism

`match` is a pure function of its two arguments. It reads no clock, no
environment, and no filesystem, and it holds no state between calls.
