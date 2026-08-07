# Planted defect: the code stops at the first bad field, the report does not

`_field_block` appends an `if errors: return errors` guard after every field's
checks, so the generated validator reports only the first field that failed
instead of every violation in field order. The report is untouched and
remains entirely accurate: its field table matches the schema, and because
each message is still reachable from some single-violation record, the message
list it prints is exactly the set the validator can emit. A benchmark that
graded only the human-readable half — read the report, check it describes the
schema, check its message list is honest — scores this seed as good. Only a
deterministic oracle that executes the generated module against a record
carrying two independent violations catches it, which is why the produced
benchmark must run the generated code as code rather than reason about it from
the report.

deviation: early-exit
