# scaffold.py — usage

    python scaffold.py <schema.json> <outdir>

Reads one schema document and writes two artifacts into `<outdir>`, creating
it when absent:

| artifact | audience |
| --- | --- |
| `validate_<record>.py` | other programs — imported and called |
| `REPORT.md` | people — read before anyone trusts the module |

`<record>` is the schema's record name lowercased with spaces replaced by
underscores; the schema `{"record": "Contact"}` yields `validate_contact.py`.

Exit codes: `0` on success, `2` on a usage error. Standard library only,
Python 3.9 or newer, no network.

## The code artifact

The generated module exposes one function:

    validate(record) -> list of error strings

`record` is a mapping. The list carries one string per rule the record breaks,
in schema field order; an empty list means the record is valid. A field that
is absent and a field set to `None` are the same thing. Every violation in the
record is reported, not only the first.

## The human artifact

`REPORT.md` describes the generated validator for a reader who will not open
the module. Its required content is in `report-contract.md`.

## Not in scope

The tool does not validate anything itself, does not read the record data it
describes, and does not import the module it generates.
