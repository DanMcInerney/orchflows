# The schema document

One JSON object:

    {
      "record": "Contact",
      "fields": [
        {"name": "email", "type": "str", "required": true, "max_len": 64},
        {"name": "age", "type": "int", "required": false},
        {"name": "nickname", "type": "str", "required": false, "max_len": 16}
      ]
    }

- `record` — the record's name, used for the module name and the report title.
- `fields` — declaration order is the order rules are checked and errors are
  reported.
- `name` — the record key.
- `type` — `str` or `int`. `int` excludes booleans: `True` is not an integer.
- `required` — when true, an absent or `None` value is an error.
- `max_len` — optional, meaningful only for `str`; a value longer than the
  limit is an error. An `int` field carries no limit.

## The error strings a field can produce

For a field named `f` of type `t` with limit `n`:

| condition | string |
| --- | --- |
| required and absent or `None` | `f: required` |
| present and of the wrong type | `f: expected t` |
| a `str` longer than its limit | `f: max length n` |

Checks on one field stop at its first violation — a value that is not a `str`
is never also length-checked — but every field is checked.
