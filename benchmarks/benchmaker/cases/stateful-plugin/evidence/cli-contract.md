# store.py — the command-line contract

    python store.py --state <path> <command> [args]

`--state <path>` is required and always comes first. `<path>` names the file
holding this store's state; it need not exist yet.

| command | effect | stdout | exit |
| --- | --- | --- | --- |
| `put <key> <value>` | store `<value>` under `<key>`, replacing any current value | nothing | 0 |
| `get <key>` | look the key up | the value and a newline | 0 |
| `get <key>` (absent) | — | nothing (message on stderr) | 1 |
| `delete <key>` | remove the key | nothing | 0 |
| `delete <key>` (absent) | — | nothing (message on stderr) | 1 |
| `list` | every pair, sorted by key | `key=value` lines | 0 |

A malformed invocation writes the usage line to stderr and exits 2.

## Value rules

Keys and values are strings, taken verbatim from the command line. The empty
string is an ordinary value: `put k ""` stores it, a later `get k` prints an
empty line and exits 0, and `list` shows `k=`. Absence and emptiness are
different states.

## Store rules

- A missing or empty state file is an empty store, not an error.
- `get` and `list` never write — not to the state file, not anywhere.
- `put` and `delete` write the whole store back to the state file.
- The store holds no in-memory state between invocations; each invocation
  reads the state file, acts, and exits.

Standard library only, Python 3.9 or newer, no network.
