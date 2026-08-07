# changelog generator — code-domain specification

`changelog.py` turns a commit log into a Markdown changelog on stdout.
Python 3.9 standard library only. stdin unused.

## Invocation

    changelog.py COMMITS_FILE

Exactly one argument. Any other count, or an unreadable file, is a
usage error.

## Input format

- One commit per line: `TYPE: SUBJECT`, where `TYPE` is one of
  `feat`, `fix`, `docs` and `SUBJECT` is non-empty text.
- The separator is a colon followed by one space.
- Blank lines are ignored.
- Input may use LF or CRLF terminators; the forms are equivalent.
- Any other line is malformed input: the program must write nothing
  to stdout and exit 1. No partial changelog is ever emitted.

## Ordering law

Within its section of the output, entries appear in input order —
the order in which their commits occur in COMMITS_FILE. No sorting,
no deduplication, no reordering of any kind.

## Exit codes

- `0` — changelog written.
- `1` — malformed input line.
- `2` — usage error: wrong argument count or unreadable file.
