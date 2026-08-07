# csvmerge — interface specification

`csvmerge` merges two key-sorted CSV files on an integer key with
cross-file deduplication. Python 3.9 standard library only. stdin is
unused.

## Invocation

    csvmerge.py [--prefer a|b] A_CSV B_CSV

- Exactly two positional file arguments. Any other count is a usage
  error.
- `--prefer a|b` names the file whose row wins when the same key
  appears in both files. Default `a`. Any other value, or any unknown
  flag, is a usage error.

## Input

- Each line is `KEY,VALUE`. `KEY` is a decimal integer; `VALUE` is the
  remainder of the line after the first comma and may itself contain
  commas.
- Within one file, keys are strictly ascending. A non-integer key or a
  key out of order is a data error.
- Line terminators: input files may use LF or CRLF; the two forms are
  equivalent. A missing final newline is tolerated. Empty lines are
  ignored.

## Output

- The merged rows on stdout, exactly one row per distinct key,
  ascending by key.
- A key present in only one file contributes that file's row. A key
  present in both files contributes the preferred file's row
  (`--prefer`, default `a`).
- Rows are emitted as `KEY,VALUE` with their original value text.
- Output ordering law: strictly ascending by key, no other order is
  conforming.
- Output line terminator is LF with a trailing final newline;
  consumers must treat a CRLF-terminated but otherwise identical
  output as equivalent (terminator form is not significant).
- On any non-zero exit, stdout is empty: no partial merge is ever
  emitted.

## Exit codes

- `0` — merge written.
- `1` — data error: non-integer key, or keys not strictly ascending
  within a file.
- `2` — usage error: wrong argument count, unknown flag, bad
  `--prefer` value, or an unreadable input file.
