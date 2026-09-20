# Beacon schema 2 reference

Published 2026-02-20. This is the original release document; later schema-specific corrections take precedence.

The required fields are key (nonempty string), elapsed (integer), and state (string). Preserve key literally. Unrelated extra fields can be ignored.

Original duration definition: elapsed is measured in milliseconds. Original status list: "done" means success and "error" means failure. Example: {"key":"0008","elapsed":1250,"state":"done"}.

Check the release correction page for changes to these two definitions. The field names and identifier rules above remain applicable.
