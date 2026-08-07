# QML-lite configuration format — partial specification

L01: This note documents the QML-lite subset the deploy tools rely on today.
L02: It is known to be incomplete: constructs seen in the field beyond the four behaviors below are undocumented here, and this note assigns them no meaning.

## Documented behaviors

L03: Key syntax — a key is one lowercase letter followed by lowercase letters, digits or underscores, then `=`, then a value on the same line.
L04: (Rationale: keys mirror the deploy tool's environment names.)
L05: Scalar type — the only documented value type is the integer: an optional leading `-`, then decimal digits.
L06: (Rationale: every documented setting today is a count or a port.)
L07: Comment form — a line whose first non-space character is `#` is a comment and carries no configuration meaning.
L08: (Blank lines likewise carry no meaning.)
L09: Section header — a section header is a line of the form `[name]` where name is one lowercase letter followed by lowercase letters, digits or underscores.

## Examples seen in the field (not every construct below is documented above)

E11: `host = 9`
E12: `# retry budget for the ingest lane`
E13: `[ingest]`
E14: `name = "web"` — quoted string value: undocumented
E15: `enabled = true` — boolean literal: undocumented
E16: `peers = 3, 5, 9` — list value: undocumented
E17: `[db.primary]` — dotted section name: undocumented
E18: `port = 8080  # inline` — trailing inline remark: undocumented
