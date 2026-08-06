# dedupe — behavioural contract

`dedupe` removes repeated lines from a text stream while preserving the
order of the lines it keeps.

## Invocation

    dedupe [--window N] [--ignore-case] [FILE]

`FILE` is a path; `-` or an omitted argument reads standard input.

## Comparison key

Each input line is reduced to a comparison key. Without `--ignore-case`
the key is the line itself. With `--ignore-case` the key is the line
case-folded. The key is used only for comparison: a retained line is
always written back exactly as it was read, with its original casing.

## Retention rule

A line is *retained* (written to output) unless an equal comparison key
already appears among the `--window N` most recently retained lines.
Suppressed lines occupy no space in the window — the window is measured
over retained output lines, never over input lines.

- `--window 0` is the default and means unbounded: the key is compared
  against every previously retained line.
- `--window 1` compares against the single most recently retained line.
- `--window N` compares against the last `N` retained lines. A repeat at
  a distance of exactly `N` retained lines is suppressed; a repeat at a
  distance of `N + 1` or more has fallen out of the window and is
  retained.

## Input and output

Input bytes are decoded as UTF-8. `\r\n` is normalised to `\n`. The
stream is split on `\n`; a single trailing newline does not produce an
extra empty line. Empty input produces empty output.

An empty line is an ordinary line with the empty string as its key: the
first empty line in a window is retained, later ones are suppressed like
any other repeat.

Every retained line is written followed by a single `\n`, byte for byte
as it was read. No line terminator translation is applied on any
platform.

## Exit status

- `0` — the input was processed.
- `2` — usage error: a negative `--window`, an unknown flag, or an input
  file that cannot be read. A diagnostic goes to standard error and
  standard output stays empty.

## Examples

    $ printf 'a\nb\na\nc\nb\n' | dedupe
    a
    b
    c

    $ printf 'a\nb\na\n' | dedupe --window 1
    a
    b
    a

    $ printf 'Foo\nFOO\nbar\n' | dedupe --ignore-case
    Foo
    bar
