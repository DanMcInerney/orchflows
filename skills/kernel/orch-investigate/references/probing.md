# Probing guidance

Run speculative candidates as isolated dead-end probes, never in a
required-read batch.

Select only the fields the question needs and page any remainder under
an explicit per-read output bound. Never emit a complete inventory or
descriptor when one item, scope, or symbol is selected.
